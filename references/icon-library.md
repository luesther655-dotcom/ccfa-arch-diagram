# 图标素材包（内嵌 SVG 线条图标）

给系统图/部署图/多模态实体输入/注意力可视化提供 25 个手绘**单色矢量线稿**图标
（GPU/云/数据库/人/眼/大脑等）。**零外部依赖**——图标以 SVG 的 URL 编码
data URI 嵌进 `style`（`shape=image`），draw.io 桌面端与网页版都 100% 渲染、
导出一致；单色描边在任何调色板上都协调。布局/走线/配色仍照常手算，这里只
提供"实体图元"。

## 何时用

- **系统/部署图**（原型 C 多 Agent / E 横带框架）：硬件实体（GPU/CPU/服务器/
  云/数据库/集群）、外部数据源（图像/文本/视频/音频/文档/数据集/文件夹）；
- **多模态输入**：每种模态配一个输入图标，旁边再接它的张量/编码块；
- **注意力/生物医学可视化**：eye（注意力）、brain、cell、robot、person；
- **检索/工具链路**：search、camera、clock、globe、gear。

## 三铁律

1. **图标只作补充，永远配文字标签**——图标是识别锚点，不是唯一信息源；
   `value` 就是标签（双语），图标下方渲染。
2. **单色描边与图的描边/字色一致**——默认 `#5F6368`（default 描边）；按当前
   调色板换色用 `--stroke #RRGGBB` 重生成（见下）。**不要**在图标里用彩色。
3. **克制**——每图 ≤4–6 个图标，只在图标能增加辨识度的地方用（输入类型/
   硬件/人·生物/小工具符号）；纯计算链（Conv/Transformer 主链）不需要图标。

## 换色配方（currentColor 对 shape=image 无效）

`shape=image` 经 `<img>` 渲染，SVG 拿不到 cell 的 `fillColor`（无 CSS 继承）。
换色 = 改 SVG 内 stroke 十六进制 + 重编码，一键重生成全部三处：

```bash
python3 scripts/build_icon_library.py --stroke #3A4A5A
```

（`assets/icon_defs.json` 里的原始 `#5F6368` 不动，重跑即恢复。）

## 素材包结构

| 文件 | 作用 | 改法 |
|---|---|---|
| `assets/icon_defs.json` | 唯一事实源（SVG + 标签 + 尺寸） | 手写 |
| `scripts/build_icon_library.py` | 序列化生成器（URL 编码/JSON/网格） | 别改 |
| `assets/ccfa-icons.xml` | draw.io 自定义库文件（拖拽用） | 生成 |
| `assets/icon_preview.drawio` | 25 图标网格，打开即见全部渲染 | 生成 |
| 下方目录块 | 复制 paste-ready 片段 | 生成 |

打开库文件：桌面端 `File → Open Library from → Device…`；网页端
`File → Open Library from → URL…` 或直接把 `ccfa-icons.xml` 拖进画布/形状面板，
从图库拖图标到画布。**加/改图标**：编辑 `icon_defs.json` → 跑 builder → 重跑
`python3 scripts/validate.py assets/icon_preview.drawio` 确认 0 error。

## 新图标创作规范（25 个之外的新实体）

需要新实体图标（卫星/雷达/芯片/无人机…）时，**手写一个 24×24 单色线稿 SVG**
追加进 `assets/icon_defs.json` 的 `icons` 数组，跑 builder 重建。builder 会逐条
自检格式，违反任一铁律即构建失败并报出是哪条——按下面规范写一次就能过。

| 项 | 必须 | 为什么 |
|---|---|---|
| 根元素 | `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>` | `<img>` 渲染靠 viewBox 等比缩放 |
| 颜色 | 只用当前描边色（默认 `#5F6368`） | 换色是字符串替换，硬编码别的色重生成后不变 |
| 线宽 | 所有 `stroke-width='1.5'` | 与整包一致，放大小不突兀 |
| 填充 | 一律 `fill='none'`；仅可点缀实心点用 `fill='#5F6368'` | 线稿风格，大块实心破坏协调 |
| 范围 | 坐标全在 24×24 内、四周留 ≥2px 边距 | 贴边/越界渲染出来是裁掉的 |
| 禁止 | `<?xml?>`、`<image>`、`currentColor`、外部引用、渐变 | 前两个见换色配方，后者 `<img>` 里恒不生效 |

**手写要点**（与顶会图元同一审美）：一个实体一个清晰剪影，2–4 条主结构线，
不要细节堆砌——复杂度上限 ≈ `gpu`（板卡+核心）或 `brain`（轮廓+褶皱示意）。
`category` 只能取五类之一：`data / hardware / human / tool / model`；`w`×`h`
是图标在画布上的占位尺寸，整包统一 `48 × 56`。模板（卫星，可直接抄）：

```json
{ "id": "satellite", "label": "卫星 Satellite", "category": "hardware",
  "w": 48, "h": 56,
  "svg": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='7' y='8' width='10' height='8' rx='1.5' fill='none' stroke='#5F6368' stroke-width='1.5'/><rect x='4' y='9.5' width='2.5' height='5' fill='none' stroke='#5F6368' stroke-width='1.5'/><rect x='17.5' y='9.5' width='2.5' height='5' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M10 8V5.5M14 8V5.5M12 4l-1.5 1.5h3L12 4zM10 16v2.5M14 16v2.5M12 20l-1.5-1.5h3L12 20z' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linejoin='round' stroke-linecap='round'/></svg>" }
```

**流程**（全程确定性可复验）：

```bash
# 1) 编辑 assets/icon_defs.json：icons 数组追加一条（id 与现有 25 个不重复）
# 2) 重建三处产出：ccfa-icons.xml / icon_preview.drawio / 下方目录块
python3 scripts/build_icon_library.py
# 3) 校验预览图 0 error（网格不越界、id 唯一）
python3 scripts/validate.py assets/icon_preview.drawio
# 4) 新图标即进库：从 ccfa-icons.xml 拖拽，或用下方生成的 paste-ready 片段
```

> `id` 用蛇形小写英文；`label` 双语（中文 空格 英文）。builder 对每个 SVG 做
> 确定性自检（可解析/根元素/颜色/线宽/越界坐标），全部通过才产出——自检信息
> 会告诉你具体改哪里。

---

<!-- ICON-SNIPPETS:BEGIN -->
## 图标目录（生成块）

> 由 `scripts/build_icon_library.py` 从 `assets/icon_defs.json` 确定性生成，**勿手改本块**；加/改图标请编辑 manifest 后重跑。换色：`--stroke #RRGGBB`。当前描边色：`#5F6368`。

| id | 类别 | 标签 |
|---|---|---|
| `image` | 数据/输入 | image · 图像 |
| `text` | 数据/输入 | text · 文本 |
| `video` | 数据/输入 | video · 视频 |
| `audio` | 数据/输入 | audio · 音频 |
| `document` | 数据/输入 | document · 文档 |
| `dataset` | 数据/输入 | dataset · 数据集 |
| `folder` | 数据/输入 | folder · 文件夹 |
| `gpu` | 硬件/部署 | gpu · GPU |
| `cpu` | 硬件/部署 | cpu · CPU |
| `server` | 硬件/部署 | server · 服务器 |
| `cloud` | 硬件/部署 | cloud · 云 |
| `database` | 硬件/部署 | database · 数据库 |
| `hpc` | 硬件/部署 | hpc · 集群 |
| `person` | 人/生物 | person · 人 |
| `brain` | 人/生物 | brain · 大脑 |
| `eye` | 人/生物 | eye · 注意力 |
| `cell` | 人/生物 | cell · 细胞 |
| `robot` | 人/生物 | robot · 机器人 |
| `search` | 工具/交互 | search · 检索 |
| `camera` | 工具/交互 | camera · 相机 |
| `gear` | 工具/交互 | gear · 参数 |
| `clock` | 工具/交互 | clock · 时间 |
| `globe` | 工具/交互 | globe · 全球 |
| `mask` | 模型/符号 | mask · 掩码 |
| `token` | 模型/符号 | token · Token |

---

#### `image` · image · 图像（数据/输入）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_image" value="image · 图像" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Crect%20x%3D%273%27%20y%3D%274%27%20width%3D%2718%27%20height%3D%2716%27%20rx%3D%272%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Ccircle%20cx%3D%278.5%27%20cy%3D%279%27%20r%3D%271.6%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M4.5%2016.5l4.5-4.5%203.2%203.2%203-3%204.3%204.3%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linejoin%3D%27round%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='3' y='4' width='18' height='16' rx='2' fill='none' stroke='#5F6368' stroke-width='1.5'/><circle cx='8.5' cy='9' r='1.6' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M4.5 16.5l4.5-4.5 3.2 3.2 3-3 4.3 4.3' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linejoin='round' stroke-linecap='round'/></svg>
```

#### `text` · text · 文本（数据/输入）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_text" value="text · 文本" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Crect%20x%3D%273%27%20y%3D%274%27%20width%3D%2718%27%20height%3D%2716%27%20rx%3D%272%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M6%208.5h12M6%2012.5h12M6%2016.5h8%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='3' y='4' width='18' height='16' rx='2' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M6 8.5h12M6 12.5h12M6 16.5h8' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/></svg>
```

#### `video` · video · 视频（数据/输入）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_video" value="video · 视频" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Crect%20x%3D%273%27%20y%3D%275%27%20width%3D%2718%27%20height%3D%2714%27%20rx%3D%272%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M10%209.5l4.5%202.5-4.5%202.5z%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linejoin%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='3' y='5' width='18' height='14' rx='2' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M10 9.5l4.5 2.5-4.5 2.5z' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linejoin='round'/></svg>
```

#### `audio` · audio · 音频（数据/输入）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_audio" value="audio · 音频" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Cpath%20d%3D%27M4%209.5h3.5L12%205.5v13l-4.5-4H4z%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linejoin%3D%27round%27%2F%3E%3Cpath%20d%3D%27M15.5%209.5c1%201.4%201%203.6%200%205M18%207c2%202.4%202%207.6%200%2010%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M4 9.5h3.5L12 5.5v13l-4.5-4H4z' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linejoin='round'/><path d='M15.5 9.5c1 1.4 1 3.6 0 5M18 7c2 2.4 2 7.6 0 10' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/></svg>
```

#### `document` · document · 文档（数据/输入）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_document" value="document · 文档" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Cpath%20d%3D%27M6.5%203.5H14l3.5%203.5v13.5h-11z%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linejoin%3D%27round%27%2F%3E%3Cpath%20d%3D%27M14%203.5v3.5h3.5M9%2011.5h6M9%2015h4%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M6.5 3.5H14l3.5 3.5v13.5h-11z' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linejoin='round'/><path d='M14 3.5v3.5h3.5M9 11.5h6M9 15h4' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/></svg>
```

#### `dataset` · dataset · 数据集（数据/输入）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_dataset" value="dataset · 数据集" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Crect%20x%3D%273%27%20y%3D%274.5%27%20width%3D%2718%27%20height%3D%274.5%27%20rx%3D%271.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Crect%20x%3D%274.5%27%20y%3D%279.75%27%20width%3D%2715%27%20height%3D%274.5%27%20rx%3D%271.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Crect%20x%3D%276%27%20y%3D%2715%27%20width%3D%2712%27%20height%3D%274.5%27%20rx%3D%271.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='3' y='4.5' width='18' height='4.5' rx='1.5' fill='none' stroke='#5F6368' stroke-width='1.5'/><rect x='4.5' y='9.75' width='15' height='4.5' rx='1.5' fill='none' stroke='#5F6368' stroke-width='1.5'/><rect x='6' y='15' width='12' height='4.5' rx='1.5' fill='none' stroke='#5F6368' stroke-width='1.5'/></svg>
```

#### `folder` · folder · 文件夹（数据/输入）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_folder" value="folder · 文件夹" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Cpath%20d%3D%27M3.5%207.5a2%202%200%200%201%202-2h4l2%202h7a2%202%200%200%201%202%202v8a2%202%200%200%201-2%202h-13a2%202%200%200%201-2-2z%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linejoin%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M3.5 7.5a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linejoin='round'/></svg>
```

#### `gpu` · gpu · GPU（硬件/部署）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_gpu" value="gpu · GPU" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Crect%20x%3D%273%27%20y%3D%274.5%27%20width%3D%2718%27%20height%3D%2710%27%20rx%3D%271.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Crect%20x%3D%279.5%27%20y%3D%277%27%20width%3D%275%27%20height%3D%275%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Crect%20x%3D%2711%27%20y%3D%278.5%27%20width%3D%272%27%20height%3D%272%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M7%2014.5v1.5M9.5%2014.5v1.5M12%2014.5v1.5M14.5%2014.5v1.5M17%2014.5v1.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='3' y='4.5' width='18' height='10' rx='1.5' fill='none' stroke='#5F6368' stroke-width='1.5'/><rect x='9.5' y='7' width='5' height='5' fill='none' stroke='#5F6368' stroke-width='1.5'/><rect x='11' y='8.5' width='2' height='2' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M7 14.5v1.5M9.5 14.5v1.5M12 14.5v1.5M14.5 14.5v1.5M17 14.5v1.5' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/></svg>
```

#### `cpu` · cpu · CPU（硬件/部署）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_cpu" value="cpu · CPU" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Crect%20x%3D%277%27%20y%3D%277%27%20width%3D%2710%27%20height%3D%2710%27%20rx%3D%271%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Crect%20x%3D%2710%27%20y%3D%2710%27%20width%3D%274%27%20height%3D%274%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M9.5%204v3M12%204v3M14.5%204v3M9.5%2017v3M12%2017v3M14.5%2017v3M4%209.5h3M4%2012h3M4%2014.5h3M17%209.5h3M17%2012h3M17%2014.5h3%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='7' y='7' width='10' height='10' rx='1' fill='none' stroke='#5F6368' stroke-width='1.5'/><rect x='10' y='10' width='4' height='4' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M9.5 4v3M12 4v3M14.5 4v3M9.5 17v3M12 17v3M14.5 17v3M4 9.5h3M4 12h3M4 14.5h3M17 9.5h3M17 12h3M17 14.5h3' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/></svg>
```

#### `server` · server · 服务器（硬件/部署）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_server" value="server · 服务器" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Crect%20x%3D%274%27%20y%3D%273%27%20width%3D%2716%27%20height%3D%2718%27%20rx%3D%271.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M7%208h10M7%2012h10M7%2016h10%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Ccircle%20cx%3D%279%27%20cy%3D%275.5%27%20r%3D%270.9%27%20fill%3D%27%235F6368%27%2F%3E%3Ccircle%20cx%3D%279%27%20cy%3D%279.5%27%20r%3D%270.9%27%20fill%3D%27%235F6368%27%2F%3E%3Ccircle%20cx%3D%279%27%20cy%3D%2713.5%27%20r%3D%270.9%27%20fill%3D%27%235F6368%27%2F%3E%3Ccircle%20cx%3D%279%27%20cy%3D%2717.5%27%20r%3D%270.9%27%20fill%3D%27%235F6368%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='4' y='3' width='16' height='18' rx='1.5' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M7 8h10M7 12h10M7 16h10' fill='none' stroke='#5F6368' stroke-width='1.5'/><circle cx='9' cy='5.5' r='0.9' fill='#5F6368'/><circle cx='9' cy='9.5' r='0.9' fill='#5F6368'/><circle cx='9' cy='13.5' r='0.9' fill='#5F6368'/><circle cx='9' cy='17.5' r='0.9' fill='#5F6368'/></svg>
```

#### `cloud` · cloud · 云（硬件/部署）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_cloud" value="cloud · 云" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Cpath%20d%3D%27M6.5%2018A4.5%204.5%200%200%201%206%209.5%206.5%206.5%200%200%201%2018.5%2010.5%204%204%200%200%201%2017.5%2018Z%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linejoin%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M6.5 18A4.5 4.5 0 0 1 6 9.5 6.5 6.5 0 0 1 18.5 10.5 4 4 0 0 1 17.5 18Z' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linejoin='round'/></svg>
```

#### `database` · database · 数据库（硬件/部署）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_database" value="database · 数据库" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Cellipse%20cx%3D%2712%27%20cy%3D%276%27%20rx%3D%278%27%20ry%3D%272.6%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M4%206v12c0%201.5%203.6%202.6%208%202.6s8-1.1%208-2.6V6%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M4%2012c0%201.5%203.6%202.6%208%202.6s8-1.1%208-2.6%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><ellipse cx='12' cy='6' rx='8' ry='2.6' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M4 6v12c0 1.5 3.6 2.6 8 2.6s8-1.1 8-2.6V6' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M4 12c0 1.5 3.6 2.6 8 2.6s8-1.1 8-2.6' fill='none' stroke='#5F6368' stroke-width='1.5'/></svg>
```

#### `hpc` · hpc · 集群（硬件/部署）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_hpc" value="hpc · 集群" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Crect%20x%3D%274%27%20y%3D%274%27%20width%3D%277%27%20height%3D%277%27%20rx%3D%271.2%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Crect%20x%3D%2713%27%20y%3D%274%27%20width%3D%277%27%20height%3D%277%27%20rx%3D%271.2%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Crect%20x%3D%274%27%20y%3D%2713%27%20width%3D%277%27%20height%3D%277%27%20rx%3D%271.2%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Crect%20x%3D%2713%27%20y%3D%2713%27%20width%3D%277%27%20height%3D%277%27%20rx%3D%271.2%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M7.5%2011v2M11%207.5h2M11%2016.5h2M16.5%2011v2%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='4' y='4' width='7' height='7' rx='1.2' fill='none' stroke='#5F6368' stroke-width='1.5'/><rect x='13' y='4' width='7' height='7' rx='1.2' fill='none' stroke='#5F6368' stroke-width='1.5'/><rect x='4' y='13' width='7' height='7' rx='1.2' fill='none' stroke='#5F6368' stroke-width='1.5'/><rect x='13' y='13' width='7' height='7' rx='1.2' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M7.5 11v2M11 7.5h2M11 16.5h2M16.5 11v2' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/></svg>
```

#### `person` · person · 人（人/生物）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_person" value="person · 人" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Ccircle%20cx%3D%2712%27%20cy%3D%278%27%20r%3D%273.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M5%2020c0-3.6%203.1-5.6%207-5.6s7%202%207%205.6%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='8' r='3.5' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M5 20c0-3.6 3.1-5.6 7-5.6s7 2 7 5.6' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/></svg>
```

#### `brain` · brain · 大脑（人/生物）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_brain" value="brain · 大脑" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Cpath%20d%3D%27M12%2021c-4.5%200-7-2.4-7-5.5%200-1.9%201-3.6%202.6-4.6C6.9%209.3%208.2%206.7%2011%205.9%2011.4%204.3%2012.6%203.5%2014%203.5c2.6%200%204.7%202%205.6%205%20.9.4%201.6%201%202.1%201.8.9%201.3.5%203.3-1.4%204.2%201%201%201.5%202.2%201.5%203.5%200%203.1-2.5%203-5%203z%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linejoin%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M12 21c-4.5 0-7-2.4-7-5.5 0-1.9 1-3.6 2.6-4.6C6.9 9.3 8.2 6.7 11 5.9 11.4 4.3 12.6 3.5 14 3.5c2.6 0 4.7 2 5.6 5 .9.4 1.6 1 2.1 1.8.9 1.3.5 3.3-1.4 4.2 1 1 1.5 2.2 1.5 3.5 0 3.1-2.5 3-5 3z' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linejoin='round'/></svg>
```

#### `eye` · eye · 注意力（人/生物）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_eye" value="eye · 注意力" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Cpath%20d%3D%27M2.8%2012S6%205.8%2012%205.8%2021.2%2012%2021.2%2012%2018%2018.2%2012%2018.2%202.8%2012%202.8%2012z%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linejoin%3D%27round%27%2F%3E%3Ccircle%20cx%3D%2712%27%20cy%3D%2712%27%20r%3D%272.8%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M2.8 12S6 5.8 12 5.8 21.2 12 21.2 12 18 18.2 12 18.2 2.8 12 2.8 12z' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linejoin='round'/><circle cx='12' cy='12' r='2.8' fill='none' stroke='#5F6368' stroke-width='1.5'/></svg>
```

#### `cell` · cell · 细胞（人/生物）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_cell" value="cell · 细胞" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Ccircle%20cx%3D%2712%27%20cy%3D%2712%27%20r%3D%278.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Ccircle%20cx%3D%2712%27%20cy%3D%2712%27%20r%3D%274%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M12%203.5V6M12%2018v3.5M3.5%2012H6M18%2012h3.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='8.5' fill='none' stroke='#5F6368' stroke-width='1.5'/><circle cx='12' cy='12' r='4' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M12 3.5V6M12 18v3.5M3.5 12H6M18 12h3.5' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/></svg>
```

#### `robot` · robot · 机器人（人/生物）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_robot" value="robot · 机器人" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Crect%20x%3D%275%27%20y%3D%278%27%20width%3D%2714%27%20height%3D%2710%27%20rx%3D%272%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Ccircle%20cx%3D%279.5%27%20cy%3D%2713%27%20r%3D%271%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Ccircle%20cx%3D%2714.5%27%20cy%3D%2713%27%20r%3D%271%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M12%208V6M12%204.5a.75.75%200%201%200%200-1.5.75.75%200%200%200%200%201.5z%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3Cpath%20d%3D%27M8%2018v2M16%2018v2%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='5' y='8' width='14' height='10' rx='2' fill='none' stroke='#5F6368' stroke-width='1.5'/><circle cx='9.5' cy='13' r='1' fill='none' stroke='#5F6368' stroke-width='1.5'/><circle cx='14.5' cy='13' r='1' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M12 8V6M12 4.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5z' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/><path d='M8 18v2M16 18v2' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/></svg>
```

#### `search` · search · 检索（工具/交互）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_search" value="search · 检索" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Ccircle%20cx%3D%2710.5%27%20cy%3D%2710.5%27%20r%3D%276%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M15%2015l5%205%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='10.5' cy='10.5' r='6' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M15 15l5 5' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/></svg>
```

#### `camera` · camera · 相机（工具/交互）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_camera" value="camera · 相机" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Cpath%20d%3D%27M4%208a2%202%200%200%201%202-2h2l1.5-2.5h5L16%206h2a2%202%200%200%201%202%202v9a2%202%200%200%201-2%202H6a2%202%200%200%201-2-2z%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linejoin%3D%27round%27%2F%3E%3Ccircle%20cx%3D%2712%27%20cy%3D%2712.5%27%20r%3D%273.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M4 8a2 2 0 0 1 2-2h2l1.5-2.5h5L16 6h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linejoin='round'/><circle cx='12' cy='12.5' r='3.5' fill='none' stroke='#5F6368' stroke-width='1.5'/></svg>
```

#### `gear` · gear · 参数（工具/交互）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_gear" value="gear · 参数" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Ccircle%20cx%3D%2712%27%20cy%3D%2712%27%20r%3D%273.2%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M12%202.5v3.2M12%2018.3v3.2M2.5%2012h3.2M18.3%2012h3.2M5.2%205.2l2.3%202.3M16.5%2016.5l2.3%202.3M18.8%205.2l-2.3%202.3M7.5%2016.5l-2.3%202.3%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='3.2' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M12 2.5v3.2M12 18.3v3.2M2.5 12h3.2M18.3 12h3.2M5.2 5.2l2.3 2.3M16.5 16.5l2.3 2.3M18.8 5.2l-2.3 2.3M7.5 16.5l-2.3 2.3' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/></svg>
```

#### `clock` · clock · 时间（工具/交互）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_clock" value="clock · 时间" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Ccircle%20cx%3D%2712%27%20cy%3D%2712%27%20r%3D%278.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M12%207v5l3.5%202%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%20stroke-linejoin%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='8.5' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M12 7v5l3.5 2' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/></svg>
```

#### `globe` · globe · 全球（工具/交互）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_globe" value="globe · 全球" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Ccircle%20cx%3D%2712%27%20cy%3D%2712%27%20r%3D%278.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cellipse%20cx%3D%2712%27%20cy%3D%2712%27%20rx%3D%273.5%27%20ry%3D%278.5%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M3.5%2012h17%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='8.5' fill='none' stroke='#5F6368' stroke-width='1.5'/><ellipse cx='12' cy='12' rx='3.5' ry='8.5' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M3.5 12h17' fill='none' stroke='#5F6368' stroke-width='1.5'/></svg>
```

#### `mask` · mask · 掩码（模型/符号）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_mask" value="mask · 掩码" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Crect%20x%3D%273%27%20y%3D%274%27%20width%3D%2718%27%20height%3D%2716%27%20rx%3D%272%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%2F%3E%3Cpath%20d%3D%27M3%2016l6-6%204%204%208-8%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linejoin%3D%27round%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='3' y='4' width='18' height='16' rx='2' fill='none' stroke='#5F6368' stroke-width='1.5'/><path d='M3 16l6-6 4 4 8-8' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linejoin='round' stroke-linecap='round'/></svg>
```

#### `token` · token · Token（模型/符号）

**paste-ready**（改 `x/y` 与 `id` 后直接用）：

```xml
<mxCell id="icn_token" value="token · Token" style="shape=image;verticalLabelPosition=bottom;verticalAlign=top;align=center;aspect=fixed;image=data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Cpath%20d%3D%27M10%203.5L8%2020.5M16%203.5L14%2020.5M4.5%209h15M3.5%2015h15%27%20fill%3D%27none%27%20stroke%3D%27%235F6368%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="48" height="56" as="geometry"/>
</mxCell>
```

**raw SVG**（改 stroke 换色后跑 `build_icon_library.py --stroke ...` 重生成）：

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M10 3.5L8 20.5M16 3.5L14 20.5M4.5 9h15M3.5 15h15' fill='none' stroke='#5F6368' stroke-width='1.5' stroke-linecap='round'/></svg>
```

<!-- ICON-SNIPPETS:END -->
