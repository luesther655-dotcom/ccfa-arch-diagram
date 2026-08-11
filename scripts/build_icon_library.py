#!/usr/bin/env python3
"""ccfa-arch-diagram 图标素材包生成器（纯标准库·序列化工具，不是设计者）。

读 assets/icon_defs.json（唯一事实源，SVG 由人手写），确定性派生三个产出：
  1. assets/ccfa-icons.xml      — draw.io 自定义库文件（<mxlibrary> + data entry）
  2. assets/icon_preview.drawio — 全部图标 5×5 网格预览（scripts/validate.py 应 0 error）
  3. references/icon-library.md — 把 paste-ready 片段块 splice 进
     <!-- ICON-SNIPPETS:BEGIN --> / <!-- ICON-SNIPPETS:END --> 标记之间

用法：
  python3 scripts/build_icon_library.py [--stroke #RRGGBB] [--encoding uri|base64]

编码铁律（见 references/drawio-xml-guide.md §shape=image）：
  - 默认 uri：urllib.parse.quote(svg, safe='') 全量百分号编码，data URI 内
    无裸 `; = " < > # &` 空格——同时满足 XML 属性 / draw.io style 解析器
    （按 `;` 分键、首个 `=` 分键值）/ 浏览器三方约束。
  - 禁 `;charset=utf-8` / `;base64` 后缀（`;` 会被 style 解析器截断 URI）。
  - aspect=fixed（不是 fixed1）；SVG 必须自含、带 viewBox、无 `<?xml?>` 声明。
  - base64 仅作兜底（--encoding base64），部分 draw.io 版本对 `;base64,`
    的 `;` 处理不一，默认不要用。
  - currentColor 对 shape=image 无效（经 <img> 渲染）→ 换色用 --stroke 重生成。
"""

import argparse
import base64
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import quote

# Windows 控制台默认 GBK 会把 UTF-8 中文打花；统一按 UTF-8 输出。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFS = os.path.join(ROOT, "assets", "icon_defs.json")
LIBRARY_OUT = os.path.join(ROOT, "assets", "ccfa-icons.xml")
PREVIEW_OUT = os.path.join(ROOT, "assets", "icon_preview.drawio")
MD_OUT = os.path.join(ROOT, "references", "icon-library.md")

# --- 预览网格参数（5×5，A4 横版，validate.py 约束：不重叠/唯一 id/页内）---
COLS, ROWS = 5, 5
CELL_W, CELL_H = 96, 92
PITCH_X, PITCH_Y = 136, 132
ORIGIN_X, ORIGIN_Y = 40, 40
PAGE_W, PAGE_H = 1122, 794

LABEL_STYLE = ("shape=image;verticalLabelPosition=bottom;verticalAlign=top;"
               "align=center;aspect=fixed;image=")
LIB_STYLE = "verticalLabelPosition=bottom;verticalAlign=top;align=center;"
CATEGORY_CN = {
    "data": "数据/输入",
    "hardware": "硬件/部署",
    "human": "人/生物",
    "tool": "工具/交互",
    "model": "模型/符号",
}

MD_BEGIN = "<!-- ICON-SNIPPETS:BEGIN -->"
MD_END = "<!-- ICON-SNIPPETS:END -->"


def load_defs(path=DEFS):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["stroke"], data["viewBox"], data["icons"]


def encode_svg(svg, encoding):
    if encoding == "base64":
        b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return "data:image/svg+xml;base64," + b64
    return "data:image/svg+xml," + quote(svg, safe="")


def build_cell_style(data_uri):
    return LABEL_STYLE + data_uri


def validate_svgs(icons, stroke):
    """每个 SVG 必须自含、可解析、带 viewBox、无外部引用、无 <?xml?> 声明，
    且遵守整包线稿纪律（这些约定决定了换色与缩放的正确性，违反会在画布上
    静默产出坏图标）：
    - 只用当前描边色——换色靠 `svg.replace(stroke, new_stroke)` 字符串替换，
      硬编码别的十六进制色会重生成后仍不变；
    - 无 currentColor——shape=image 经 `<img>` 渲染没有 CSS 继承，恒不生效；
    - stroke-width 统一 1.5，与整包线宽一致；
    - 全部坐标落在 24×24 viewBox 附近——越界会渲染成贴边/裁掉的图标。
    """
    problems = []
    for ic in icons:
        svg = ic["svg"]
        if "<?xml" in svg.lower():
            problems.append(f"{ic['id']}: 含 <?xml?> 声明，某些 <img> 渲染器会 0×0")
        if "<image" in svg.lower():
            problems.append(f"{ic['id']}: 含外部 <image> 引用，会渲染失败")
        if "currentcolor" in svg.lower():
            problems.append(f"{ic['id']}: 含 currentColor——shape=image 经 "
                            f"<img> 渲染无 CSS 继承，此色恒不生效，改用描边色")
        try:
            root = ET.fromstring(svg)
        except ET.ParseError as e:
            problems.append(f"{ic['id']}: SVG 解析失败 — {e}")
            continue
        tag = root.tag.split("}")[-1].lower()
        if tag != "svg":
            problems.append(f"{ic['id']}: 根元素不是 <svg>")
        elif "viewBox" not in root.attrib and "width" not in root.attrib:
            problems.append(f"{ic['id']}: 缺 viewBox/width，会渲染成 0×0")
        bad = set(re.findall(r"#[0-9A-Fa-f]{6}", svg)) - {stroke}
        if bad:
            problems.append(f"{ic['id']}: 含非描边色 {sorted(bad)}——单色线稿包"
                            f"只允许描边色 {stroke}（换色靠字符串替换，硬编码"
                            f"别的色会重生成后仍不变）")
        for num in re.findall(r"stroke-width\s*=\s*[\"']?([0-9.]+)", svg):
            if float(num) != 1.5:
                problems.append(f"{ic['id']}: stroke-width={num}≠1.5——与整包"
                                f"线宽不一致，缩放到 24×24 会明显偏粗/偏细")
                break
        # 越界扫描：剔掉十六进制色与 URL（xmlns 里带 "2000"）后，24×24 viewBox
        # 内任何坐标绝对值不应远超 24（留 6px 线宽/圆角余量）；一次扫描
        # path/rect/circle 全部数字。
        cleaned = re.sub(r"[a-zA-Z][\w+.-]*://[^\s'\"<>]*", "", svg)
        cleaned = re.sub(r"#[0-9A-Fa-f]{6}", "", cleaned)
        num_re = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
        stray = [n for n in re.findall(num_re, cleaned) if abs(float(n)) > 30]
        if stray:
            problems.append(f"{ic['id']}: 坐标 {stray[:6]}{'…' if len(stray) > 6 else ''}"
                            f"超出 24×24 viewBox——图标会渲染成贴边/裁掉，"
                            f"把内容画回 2..22 范围内")
    return problems


def recolor(svg, old_stroke, new_stroke):
    return svg.replace(old_stroke, new_stroke) if new_stroke else svg


def emit_library(icons, encoding, out):
    entries = []
    for ic in icons:
        uri = encode_svg(ic["svg"], encoding)
        entries.append({
            "title": ic["label"],
            "data": uri,
            "w": ic["w"],
            "h": ic["h"],
            "aspect": "fixed",
            "style": LIB_STYLE,
            "tags": "ccfa " + ic["category"] + " " + ic["id"],
        })
    body = json.dumps(entries, ensure_ascii=False, indent=1)
    xml = (
        '<mxlibrary title="ccfa-arch-diagram icons" tags="icons,ml,architecture">\n'
        + body
        + "\n</mxlibrary>\n"
    )
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml)
    return entries


def emit_preview(icons, encoding, out):
    rows = (len(icons) + COLS - 1) // COLS
    page_h = max(PAGE_H, ORIGIN_Y + rows * PITCH_Y + CELL_H + 2)
    cells = []
    for i, ic in enumerate(icons):
        col, row = i % COLS, i // COLS
        x = ORIGIN_X + col * PITCH_X
        y = ORIGIN_Y + row * PITCH_Y
        uri = encode_svg(ic["svg"], encoding)
        cells.append(
            f'<mxCell id="icn_{ic["id"]}" value="{ic["label"]}" '
            f'style="{build_cell_style(uri)}" vertex="1" parent="1">\n'
            f'  <mxGeometry x="{x}" y="{y}" width="{CELL_W}" height="{CELL_H}" '
            'as="geometry"/>\n</mxCell>'
        )
    body = "\n".join(cells)
    doc = (
        '<mxfile host="app.diagrams.net" agent="ccfa-arch-diagram" version="24.0.0">\n'
        '  <diagram name="icon-preview" id="iconpreview">\n'
        '    <mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" '
        'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        f'pageWidth="{PAGE_W}" pageHeight="{page_h}" math="0" shadow="0" '
        'background="#FFFFFF">\n'
        '      <root>\n'
        '        <mxCell id="0"/>\n'
        '        <mxCell id="1" parent="0"/>\n'
        f"{body}\n"
        "      </root>\n"
        "    </mxGraphModel>\n"
        "  </diagram>\n"
        "</mxfile>\n"
    )
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)


def snippet_for(ic, data_uri):
    label = ic["label"]
    cat = CATEGORY_CN.get(ic["category"], ic["category"])
    return (
        f"#### `{ic['id']}` · {label}（{cat}）\n\n"
        f"**paste-ready**（改 `x/y` 与 `id` 后直接用）：\n\n"
        "```xml\n"
        f'<mxCell id="icn_{ic["id"]}" value="{label}" '
        f'style="{build_cell_style(data_uri)}" vertex="1" parent="1">\n'
        f'  <mxGeometry x="0" y="0" width="{ic["w"]}" height="{ic["h"]}" '
        'as="geometry"/>\n'
        "</mxCell>\n"
        "```\n\n"
        "**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` "
        "重生成）：\n\n"
        "```svg\n"
        f"{ic['svg']}\n"
        "```\n"
    )


def emit_md_block(icons, encoding, stroke):
    lines = []
    lines.append("## 图标目录（生成块）\n")
    lines.append(
        "> 由 `scripts/build_icon_library.py` 从 `assets/icon_defs.json` 确定性"
        "生成，**勿手改本块**；加/改图标请编辑 manifest 后重跑。换色："
        "`--stroke #RRGGBB`。当前描边色：`%s`。\n" % stroke
    )
    lines.append("| id | 类别 | 标签 |")
    lines.append("|---|---|---|")
    for ic in icons:
        lines.append(
            f'| `{ic["id"]}` | {CATEGORY_CN.get(ic["category"], ic["category"])}'
            f' | {ic["label"]} |'
        )
    lines.append("\n---\n")
    for ic in icons:
        uri = encode_svg(ic["svg"], encoding)
        lines.append(snippet_for(ic, uri))
    return "\n".join(lines) + "\n"


def splice_md_block(icons, encoding, stroke):
    block = MD_BEGIN + "\n" + emit_md_block(icons, encoding, stroke) + MD_END + "\n"
    try:
        with open(MD_OUT, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = None
    if content is not None and MD_BEGIN in content and MD_END in content:
        head = content.split(MD_BEGIN)[0]
        tail = content.split(MD_END)[1].lstrip("\n")
        new = head + block + tail
        with open(MD_OUT, "w", encoding="utf-8") as f:
            f.write(new)
        return True
    with open(MD_OUT, "w", encoding="utf-8") as f:
        f.write(block)
    return False


def main():
    ap = argparse.ArgumentParser(description="ccfa-arch-diagram 图标素材包生成器")
    ap.add_argument("--stroke", default=None,
                    help="整库换描边色，如 #3A4A5A（改 SVG 内 stroke/fill 十六进制）")
    ap.add_argument("--encoding", default="uri", choices=["uri", "base64"],
                    help="data URI 编码方式（默认 uri；base64 仅兜底，部分版本不稳）")
    args = ap.parse_args()

    stroke, view_box, icons = load_defs()
    if args.stroke:
        new_stroke = args.stroke.upper()
        icons = [dict(ic, svg=recolor(ic["svg"], stroke, new_stroke))
                 for ic in icons]
        stroke = new_stroke

    problems = validate_svgs(icons, stroke)
    for p in problems:
        print("WARN:", p, file=sys.stderr)
    if problems:
        print("有 %d 个 SVG 未通过自检——先修 manifest。" % len(problems),
              file=sys.stderr)
        return 1

    emit_library(icons, args.encoding, LIBRARY_OUT)
    emit_preview(icons, args.encoding, PREVIEW_OUT)
    had_markers = splice_md_block(icons, args.encoding, stroke)

    print("已生成：")
    print("  ", LIBRARY_OUT)
    print("  ", PREVIEW_OUT)
    print("  ", MD_OUT, "(spliced)" if had_markers else "(新建，含生成块)")
    print("描边色:", stroke, "| 编码:", args.encoding, "| 图标数:", len(icons))
    return 0


if __name__ == "__main__":
    sys.exit(main())
