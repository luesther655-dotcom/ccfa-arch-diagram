# ccfa-arch-diagram · CCF-A 风格模型架构图生成

生成 **CCF-A 顶会论文级**模型架构图（NeurIPS / ICML / ICLR / CVPR /
ICCV / ACL / EMNLP / AAAI / KDD 等）。输入模型的描述或代码，**Claude 直接
手写**一份布局整齐、无重叠、部件完整、配色专业的 `.drawio` 文件，
并用 draw.io 桌面 CLI 导出 PNG/SVG 预览（没有 CLI 也能交付 .drawio 本身）。

**专精论文模型架构图**；UML/ER/流程图等通用图表请用 drawio-skill。

## 它能做什么

| 输入 | 输出 |
|---|---|
| 一句话模型描述 | 手写排版的 `.drawio` 图表文件 |
| PyTorch / TF 模型代码 | draw.io CLI 导出的 `.png` 预览 / `.svg` 矢量图 |
| 已存在的粗糙 draw.io 草图 | 按顶会规范重排的 `.drawio` |
| 一张喜欢的论文图 | 归纳配色存成个人风格预设 |

## 目录结构

```
drawskill/
├── SKILL.md                  # 主指令（Claude 遵循的工作流）
├── references/
│   ├── ccfa-style-guide.md   # CCF-A 风格指南（五大图型原型/部件清单/密度基准/铁律）
│   ├── drawio-xml-guide.md   # 手写 .drawio XML 速查（骨架/样式串/面板/图例/CLI 导出）
│   ├── palette.md            # 调色板（内置 6 套色值表 + 用户预设机制）
│   └── layout-guide.md       # 手工布局的坐标带纪律与各模型类型画法
├── scripts/
│   ├── validate.py           # 结构 lint：重叠/骑跨/标题带侵入/端口堆叠/超宽/悬空边
│   ├── edgeports.py          # 同侧未钉端口的多条边 → 自动按对端位置分散（移植自 drawio-skill）
│   └── respread_ports.py     # 已钉但撞槽的端口 → 按槽位公式重铺（字节精确改写）
├── styles/
│   ├── schema.json           # 样式预设字段说明
│   └── built-in/             # 6 套内置调色板 JSON（色值数据）
├── examples/                 # 五大原型 + 经典单图的 .drawio 验证范例（照着写）
├── ccfa_png/                 # 10 张真实 CCF-A 论文图（风格来源；版权原因仅本地使用，不上传）
└── evals/                    # 测试用例
```

**生成全手写、校验有工具**——所有 .drawio 由 Claude 按
`references/drawio-xml-guide.md` 手写，draw.io 是唯一渲染真相；
`scripts/` 三个小工具（纯 Python 标准库，可选）在导出前做确定性
结构校验与端口修复，把"走线交叉、图元重叠、标题压字"拦截在肉眼自检之前。

## 五大图型原型

不同模型类型对应不同顶会图型（详见 `references/ccfa-style-guide.md` 第 1 节）：

| 原型 | 适用模型 | 范例 |
|---|---|---|
| A 流水线+子模块放大 | 单一网络骨干（CNN/Transformer/ViT/超分） | `examples/pipeline_zoom.drawio` |
| B 多面板训练图 | 训练流程/持续学习（(a)(b)(c) 子图） | `examples/multipanel_train.drawio` |
| C 多智能体/系统分区图 | 多 Agent/RAG/LLM 系统（2×2 面板+粗箭头+侧栏） | `examples/agent_panels.drawio` |
| D 推理阶段容器图 | CoT/推理链（阶段容器+步骤便签） | `examples/reasoning_stages.drawio` |
| E 横带框架图 | 多模态大模型/统一框架（深色标题栏+训练带） | `examples/framework_bands.drawio` |

经典单图范例：`transformer_mt.drawio` / `vit.drawio` / `diffusion.drawio`。

顶会图元画法（竖条 vbar、立方体 cube、圆柱 cylinder3、便签 note、
矩阵网格、op 操作符小圆、大箭头、面板底板、深色标题栏、三种图例摆法）
全部收录在 `references/drawio-xml-guide.md`。

## 安装为 Claude Code skill

本目录本身就是 skill 文件夹。两种使用方式：

1. **直接使用**：告诉 Claude "使用本目录下的 ccfa-arch-diagram skill"，
   或在对话里粘贴 `/ccfa-arch-diagram` 的描述需求。
2. **注册到全局/项目**（推荐，自动触发）：
   - 全局：把本文件夹复制到 `~/.claude/skills/ccfa-arch-diagram/`
   - 项目：复制到 `<项目>/.claude/skills/ccfa-arch-diagram/`

## 打开与导出

- 打开 `.drawio`：draw.io 桌面端 `File → Open`，或把文件拖进网页版
  https://app.diagrams.net
- 导出论文图：draw.io 里 `File → Export as → PNG/SVG`。论文投稿一般
  300 dpi PNG 或矢量 SVG。
- 有桌面 CLI 时 Claude 会直接导出预览并自检：
  `drawio -x -f png --width 2000 -o fig.png fig.drawio`

## 依赖

- draw.io 桌面端（预览/导出需要；没有也能交付 .drawio 本身）：
  https://github.com/jgraph/drawio-desktop/releases
- Python 3（可选，仅标准库）：跑 `scripts/` 的结构校验与端口修复工具。

## 质量保证

- **完整性**（按输入类型分级承诺）：代码输入按 `forward()` 调用链逐模块登记；
  含糊输入（只有模型名/一句话）先调研 1-2 篇权威资料（论文/官方文档/arXiv）
  再画；查无资料按最接近的知名架构画模板并标注假设，请用户复核。
- **无重叠、不交叉**：坐标带手算纪律（列距/行距/边距规范 + 10 的倍数取整 +
  容器/面板包围盒外扩 + 24px 标题带净空 + 同侧端口槽位公式）+
  `scripts/validate.py` 确定性 lint（重叠/骑跨/标题带侵入/端口堆叠/超宽/
  悬空边）+ `edgeports.py` / `respread_ports.py` 端口自动分散 +
  导出 PNG 后视觉自检（≤2 轮修复）。
- **美观**：五大图型原型配方 + 密度基准（组件/边数下限）+ 内置学术调色板 +
  顶会装裱规范（Times New Roman、半透明容器、底部图题与图例栏）。
