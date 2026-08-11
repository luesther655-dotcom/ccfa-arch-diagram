---
name: ccfa-arch-diagram
description: 生成 CCF-A 顶会论文级模型架构图（NeurIPS/ICML/ICLR/CVPR/ICCV/ACL/EMNLP/AAAI/KDD 等），直接手写产出可编辑的 draw.io (.drawio) 文件，并用 draw.io 桌面 CLI 导出 PNG/SVG 预览。当用户描述他们的模型/算法想画架构图、粘贴模型代码要求画图、想给论文配模型图、想把手绘草图或粗糙的 draw.io 图整理成规范布局，提到"CCFA 风格架构图 / 模型结构图 / 网络结构图 / architecture diagram / model figure"，或提到"用我的 <名字> 风格 / 从这张图学习配色 / 把这张图换成 <名字> 风格"，务必使用本 skill。内置五大图型原型（流水线长条/多面板训练图/多智能体分区/推理阶段容器/横带框架）与竖条、立方体、便签、矩阵、操作符小圆等顶会图元画法，支持 (a)(b)(c) 多子图面板、左侧阶段侧栏、跨面板粗箭头与自定义图例；内置 25 个实体图标素材包（GPU/云/数据库/人/眼/大脑等内嵌 SVG 单色线稿，零外部依赖）。支持用户自定义样式预设与从现有图学习配色。通用图表（UML/ER/流程图等）请用 drawio-skill；本 skill 专精论文模型架构图。
---

# CCF-A 风格模型架构图生成

把用户对模型的口头描述 / 代码文件，变成一张**能直接投进 CCF-A 论文**的
draw.io 架构图。**布局与走线由你手算、XML 由你手写**（语法与全部
样式串见 `references/drawio-xml-guide.md`，动手前必读），draw.io 是唯一
渲染真相；写完用 `scripts/` 下三个纯标准库小工具做确定性校验与端口修复
（validate / edgeports / respread_ports，见 Step 2 末尾）。产出：

1. `<name>.drawio` — 可在 draw.io 打开、继续编辑的图表文件（主交付物）
2. `<name>.png` — draw.io CLI 导出的预览图（CLI 可用时）
3. `<name>.svg` — 最终交付导出（`-e` 嵌入，可再编辑，矢量）

## 工作流（必须按此顺序）

### Step 0 — 理解模型，建立部件清单
阅读用户的描述或代码。**先不要画**，先在心中/草稿里完成 `references/ccfa-style-guide.md`
第 2.1 节的**部件检查清单**：输入、嵌入/编码、主计算块(×N)、块内子模块、残差、
池化/上采样、任务头、损失、多分支。从 `forward()` 调用顺序核对每个模块。
**任何清单上存在且真实出现的部件，一个都不能少。**

完整性承诺按输入类型分级（诚实，不夸大）：
- **有模型代码** → 按 `forward()` 调用链逐模块登记，一个不漏；
- **详细口头描述** → 按部件清单逐项核对，缺的部件先追问；
- **含糊输入（只有模型名 / 一句话）** → **先调研再画**：查 1-2 篇权威资料
  （论文原文 / 官方文档 / arXiv 摘要），提炼主干部件后走清单核对。文献与你的
  描述冲突时**以你的描述为准**，文献只用来补漏；查不到权威资料时，按**最接近的
  知名架构**画模板，并在交付说明里**标注假设与差异**，请用户复核后再定稿。

### Step 1 — 自主设计（原型 & 配色 & 版面）
这是"不死板"的一步。

**0. 解析样式预设**（若用户明确要求）：
- 用户说"用我的 `<name>` 风格 / use my `<name>` style / 按 `<name>` 配色"→
  读 `~/.ccfa-arch-diagram/styles/<name>.json`，按里面的 fill/stroke/text
  直接套用到你写的 XML 里；
- 否则查该目录里带 `default` 标记的预设；
- 都没有 → 用内置默认 `ccfa-standard`（见 `references/palette.md`，
  6 套色板的十六进制值全在里面，直接抄进 style 串）。

**1. 先选图型原型**：不同模型类型对应完全不同的顶会图型，选错原型，
画得再整齐也不像顶会图。按模型类型对号入座（配方详见
`references/ccfa-style-guide.md` 第 1 节；每个原型在 `examples/` 有
验证过的 `.drawio` 成品，**写之前打开对应范例照着写**）：

| 模型类型 | 原型 | 版面要点 | 范例 |
|---|---|---|---|
| 单一网络骨干（CNN/Transformer/超分/ViT） | A 流水线+放大 | 水平长条主干 + vbar 竖条链 + op 小圆 + 底部斜体组标题 | `examples/pipeline_zoom.drawio` |
| 训练流程 / 持续学习 / 多阶段 | B 多面板训练图 | (a)训练 (b)迁移 (c)测试 面板 + 跨面板粗箭头 | `examples/multipanel_train.drawio` |
| 多 Agent / RAG / LLM 系统 | C 系统分区图 | 2×2 淡彩面板 + 粗色跨面板箭头 + 左侧栏 + 右侧图例列 | `examples/agent_panels.drawio` |
| CoT / 推理链 / 规划 | D 推理阶段容器 | 阶段大面板 + 编号步骤模块 + note 便签产物 | `examples/reasoning_stages.drawio` |
| 多模态大模型 / 统一框架 | E 横带框架图 | 能力面板并排 + 深色标题栏分组 + 底部训练带 | `examples/framework_bands.drawio` |

经典单图参考：`examples/transformer_mt.drawio`、`vit.drawio`、`unet.drawio`。

**2. 布局方向**：序列/语言/扩散 → 从左到右；视觉金字塔 → 自下而上；
U-Net/编码器-解码器 → 对称 U 型（三段水平居中，Bottleneck 置中，见
`layout-guide.md` §3.6）；多面板图每个面板可以有自己的方向；
**3. 列带/道带**：把模型切成自然的分层，并行分支放不同道带上下对齐；
坐标按 `references/drawio-xml-guide.md` 第 7 节的网格纪律手算；
**4. 分组**：重复块/编码器/解码器用半透明容器圈起来，`×N` 写进容器标题；
流水线图用底部粗斜体组标题；框架图用深色标题栏；
**5. 强调**：本文创新模块给更醒目的配色或显式 fill/stroke，全图最多 1-2 处。
- 在输出给用户前，用一两句话说明你的设计选择（原型/方向/配色/分组理由）。

### Step 2 — 手写 .drawio XML
按 `references/drawio-xml-guide.md` 写文件。**先画主干组件，再画容器
（成员就位后算包围盒外扩），再画面板底板（压底层、XML 里排前面），
最后画边、图例、标题/图题。**

**实体图标**：需要 GPU/云/数据库/人/眼/大脑等实体图标时（系统/部署图、
多模态输入、注意力/生物医学可视化），打开 `references/icon-library.md`，
直接复制里面的 paste-ready mxCell 片段（内嵌 SVG 单色线稿，零外部依赖，
改 `x/y` 与 `id` 即用；默认 25 个，单色描边 `#5F6368`，按当前调色板换色见
该文件的「换色配方」）。**25 个不够、要新实体**（卫星/雷达/芯片/无人机等）
→ 按该文件「新图标创作规范」手写一个 24×24 单色线稿 SVG（规范 + 可直接抄的
模板都在里面），追加进 `assets/icon_defs.json` 的 `icons` 数组，跑
`python3 scripts/build_icon_library.py` 重建库/预览/文档，再
`python3 scripts/validate.py assets/icon_preview.drawio` 确认 0 error——builder
会确定性自检（颜色/线宽/越界坐标等），写错会直接报出来指给你改。

**密度规范（防止"宽松简陋"）**：顶会图是高密度的，动笔前对照下限自查——
- 原型 A（单网络长条）：≥15 组件、≥18 条边；主链上**每个** Conv/Norm/激活都
  有独立竖条，融合点有 op 小圆，边上有特征名/张量形状标注；
- 原型 B/C/E（多面板）：主面板 ≥8 组件、全图 ≥20 组件 ≥20 条边；每个面板都是
  一个能独立读懂的小图；
- 原型 D（推理阶段）：每阶段 ≥4 组件，步骤编号（Step 1/2/3…），步骤产物用
  note 便签，连接标签就是推理链文字；
- 任何原型：残差/跳跃必有虚线，重复块必写 `×N`，图例覆盖操作符与线型。
全图只有 5-8 个大框、没有操作符、边上没标注 = 稀疏，回 Step 0 清单补料。

**页型与图框（三条硬保证）**：
- **页型**：默认 A4 横版 `pageWidth=1122 pageHeight=794`（@96dpi），竖版
  `794×1123` 也支持——先定页型再排坐标（见 §7 6b）。
- **紧凑图框**：图框**只比其字段略大**，不刻意留白、不刻意铺满整张纸
  （论文里一张图至多占一张纸的 1/3）——图框宽 ≈ 最长字段文本宽 + 16-20px，
  chip 宽 ≈ 文本宽 + 8-12px（见 §7 6c）。
- **标题净空**：带顶部标题的图框，**任何箭头不得从其顶部标题字上穿过**——
  顶部入口必须落在标题文字区间之外；边路径不得穿过其他框的标题带（见 §7
  6d）。⚠ **浮动标签陷阱**：`verticalLabelPosition=top` 写在**无子结点的
  非容器**框上时，draw.io 把标题渲染成**悬浮在框上方**的字（压住上方文字、
  撞进走廊）——图框一律 `value=""` + **框内顶部独立文字格**做标题（framework_bands
  写法），校验器对两种标题都强制顶部入口净空。

论文投稿加**底部图题** text 单元格（"Fig. 1. Overall framework of ..."）；
演示汇报加顶部标题。两者可同时存在。

**写完必做结构校验（draw.io 都不需要启动）**：

```bash
python3 scripts/validate.py <name>.drawio                 # 几何/结构：重叠/骑跨/标题带/端口堆叠/超宽/悬空边/箭头穿字/走线平直/间距均匀
python3 scripts/validate.py <name>.drawio --recipe symmetric_u --strict   # 对称 U 型图再加语义不变量，0/0 才算过
```

- **error 必须清零**才进 Step 3；warning 逐条修（它们几乎都是真实的
  走线/布局缺陷——评测事故图的全部问题都能被它提前报出）。
- **语义不变量把"以前只有目检能发现"的缺陷变成确定性检查**（validate 直接
  由几何重新推导，不依赖渲染）：① 箭头**穿自己的节点**钉在远侧端口（读起来
  像没接上）；② op 圆出边方向与 `↑`/`↓` 语义相反；③ 文字溢出 chip；
  ④ 对称 U 型：Bottleneck 不居中、两臂不镜像、跳跃线不水平、密度不达标；
  ⑤ 走线平直：共线拐点（删掉不改路由）与"本可走直却拐弯"（直连无框/无字
  阻挡）都报 warning；⑥ 间距均匀：lane/column 内中位间隙的倍数异常（图例
  列、U 型走廊、侧边栏等合法结构已豁免）与"框填充率过低=大片留白"都报
  warning；⑦ 打环：入口侧不朝向源（入口朝左则源必须在左、朝上则源必须在
  上……否则 draw.io 会绕到目标另一侧打圈）报 warning，`fix_layout.py` 会把
  entry 翻到朝向源的一侧；⑧ 对边直连端口未对齐：两框在直连轴上重叠、中间
  无遮挡、本可单线直连，却因 exit/entry 端口高度/横位不一致拐出 S 弯，报
  warning，`fix_layout.py` 自动把两端槽位对齐；⑨ cube 端口错位：
  `shape=cube;direction=south` 会重投影端口（`(1,0.5)` 渲染到底边、
  `(0.5,1)` 渲染到左边），钉了 exit/entry 也错位、路由必然绕圈，报
  warning，`fix_layout.py` 自动去掉 `direction`；⑩ 公式未加粗：单元格内容
  命中公式信号（上下标/希腊字母/数学符号，或下划线带数学语境）却没有
  `fontStyle=1`，报 warning，`fix_layout.py` 自动置粗。
  对应原型图的配方在 `scripts/recipes/<name>.json`（`symmetric_u` 已内置），
  新图画完把 ids 抄进配方即可启用 ④。
- 报"同侧未钉端口堆叠"→ 跑 `python3 scripts/edgeports.py <name>.drawio`
  自动按对端位置分散（跳过你手钉的端口，幂等）；
  报"已钉端口撞槽"→ 跑 `python3 scripts/respread_ports.py <name>.drawio`
  按槽位公式 (i+1)/(k+1) 重铺（字节精确，不动其他内容）。
- **检测→修复→复检闭环**：validate 报居中偏移/箭头穿节点/op 方向/打环/
  对边 S 弯/cube 错位/公式未加粗 → 跑
  `python3 scripts/fix_layout.py <name>.drawio --recipe symmetric_u --apply`
  自动重算 x、翻转 entry/exit 侧、对齐对边槽位、去掉 cube 的 `direction`、
  置粗公式、拉净空（默认 dry-run 预览，`--apply` 才落盘，幂等），再跑
  validate 确认归零。
- 修完再跑一遍 validate 确认归零。**没有 Python 时**跳过本步，靠 Step 4
  视觉自检兜底（但自检轮次预算不变）。

### Step 3 — 导出预览（draw.io 桌面 CLI）
先探测 CLI（按序，任一成功即可，后续沿用该写法）：
`drawio --version` →
`"C:\Program Files\draw.io\draw.io.exe" --version` →
`"%LOCALAPPDATA%\Programs\draw.io\draw.io.exe" --version` →
macOS `.app` 全路径。然后：

```bash
drawio -x -f png --width 2000 -o <name>.png <name>.drawio
```

**预览绝不加 `-e`**（嵌入块会让视觉模型 400 拒读），**用 `--width 2000`
不用 `-s 2`**（防超 2576px 视觉上限）。

**CLI 未找到 → 先问再装**：向用户说明"未检测到 draw.io CLI，是否现在自动安装？"
——安装是系统级改动，**必须等用户明确同意才执行**，绝不擅自安装。用户同意后按平台安装，装完**重新探测**再走本步：
- Windows → `winget install --id JGraph.Drawio --source winget`
- macOS → `brew install --cask drawio`
- Linux → `snap install drawio-desktop`（或 `flatpak install flathub com.jgraph.drawio.desktop`）

用户**拒绝安装 / 安装失败 / 无包管理器**时：结构校验（Step 2 末尾的 validate.py）照跑，跳过
Step 3-4，直接交付 `.drawio`，告知用户用 draw.io 桌面端/网页版打开导出——
**不要**用 Python 库自造预览（本 skill 不含任何渲染代码，近似预览
只会误导）。

### Step 4 — 目检与迭代
**读回 `<name>.png`**，对照 `references/drawio-xml-guide.md` 第 9 节
自检清单检查：重叠、文字溢出、容器标题被压、箭头没接上、边穿图元、
同侧端口叠成一股、线条因图过宽而隐形、密度达标。
（Step 2 的 validate.py + recipe 已把结构类**和**语义类（居中/镜像/跳跃
水平/箭头穿节点/op 方向/文字溢出）清零——目检只兜底规则未覆盖的观感
边角，**不再承担发现已知缺陷类型的角色**。）
就地改 XML（单点问题）或重写（整体方向问题），重新导出，**最多 2 轮**
自检后交付用户过目；用户反馈循环最多 5 轮后建议其在 draw.io 里手动微调。
预览 PNG 每轮覆盖同名文件。**无 CLI 环境**下，validate 带 recipe 0/0
即可交付 `.drawio`（语义不变量不依赖渲染）。

### Step 5 — 最终导出与交付
用户认可后：

```bash
drawio -x -f svg -e -o <name>.svg <name>.drawio               # 矢量，投稿推荐
```

告知用户：
- 各产出文件路径；
- 用 draw.io 打开 `.drawio`：桌面端 `File → Open`，网页端拖进 app.diagrams.net；
- 论文一般 300 dpi PNG 或矢量 SVG；
- 若走了"按最接近架构画"的兜底（Step 0 调研查无资料），**逐条列出哪些部件是
  假设/待确认的**，请用户核对；用户确认或修正后再定稿。

## 样式预设（个人配色风格）

预设 = 一份按 kind 给 `fill/stroke/text` 十六进制值的 JSON（格式见
`styles/schema.json`）。**没有加载脚本——你读 JSON、把色值直接抄进 XML。**

**内置 6 套**（色值表见 `references/palette.md`）：
`ccfa-standard`（默认，顶会标准范式）、`academic-blue`、`print-grayscale`、
`neural-purple`、`vision-green`、`warm-paper`。

**用户预设**保存在 `~/.ccfa-arch-diagram/styles/<name>.json`，同名覆盖内置。

| 用户说 | 做法 |
|---|---|
| "用我的 `<name>` 风格 / 按 `<name>` 配色" | 读预设 JSON，色值套进 XML |
| "从这张图学习配色，存成 `<name>`" | 你直接读那张图（PNG 用视觉、.drawio 读 XML 里的 fillColor），归纳出按 kind 的色值表，写成 `~/.ccfa-arch-diagram/styles/<name>.json` |
| "把 `<name>.drawio` 换成 `<preset>` 风格" | 读该 .drawio，逐个 mxCell 把 fillColor/strokeColor/fontColor 按 kind 替换成预设色值（布局、几何、id 一律不动），另存 out.drawio |
| "列一下可用的风格" | 读用户目录 + palette.md 内置表，输出表格 |

## 规则速记

1. **先清单后画**：完整性靠 Step 0 的检查清单保证，先列全再排布。
2. **网格纪律**：列距 40 / 行距 18-40 / 边距 36 / 坐标取 10 的倍数；
   容器与面板在内容就位后再算包围盒外扩。**内容总宽 ≤ 2200px**（预览
   整体缩放会把 1.2px 主线压到近乎隐形），超宽就缩列距/换方向/拆面板。
3. **虚线=残差/侧支/训练监督/反馈，实线=主流程，粗线(2.4px 主色)=跨面板主干**；
   操作标注用 op 小圆，张量形状标注写在实线边上；**带文字的边必须
   `labelBackgroundColor=所在容器可见底色`**——容器有 `fillOpacity` 时按混合色公式算
   （见 xml-guide「标签底色」铁律），只有落在白色画布上才用 `#FFFFFF`。
4. **重复块写 ×N**，不复制 N 个真实图元。
5. **一图一调色板**；全图最多 1-2 处强调色覆盖。
6. **同侧多边槽位公式**：k 条边共享一侧 → 端口取 (i+1)/(k+1) 且**按对端
   位置排序分配**（这是出线不交叉的关键）；反方向汇入 op 圆的合流叉允许
   共享端口，同方向并行绝不允许。长边（残差/反馈/跨面板）沿外环走廊走，
   不穿图元密集区；枢纽节点放分支中间。
7. **打环铁律（入口侧必须朝向源）**：pin 了 entry 时，入口朝左 → 源必须
   整体在入口左侧；入口朝上 → 源必须在上；否则 draw.io 会绕到目标另一侧
   打圈（`orthogonalLoop=1` 也拦不住）。对边直连（出右进左）天然满足；
   邻边组合或"入口朝源却隔得近"务必检查。**对边直连共享槽位**：出右进左
   两框在直连轴上重叠、中间无遮挡时，两端端口高度必须一致（H 向）或横位
   一致（V 向），否则白拐 S 弯。**cube 一律 `direction=north`**：需要立
   box 时用 `direction=south`，但**只要它上面钉了 exit/entry 端口，就不能
   带 `direction`**——cube 外框会重投影端口导致路由绕圈，钉了等于没钉。
   **公式一律加粗**：数学变量/表达式所在 cell 必须 `fontStyle=1`（公式
   信号见 xml-guide §3.4）。这四条 validate 都能确定性报出，`fix_layout.py
   --apply` 直接修。
8. **写完先跑 `scripts/validate.py`**：error 清零才导出；语义不变量用
   `--recipe`（对称 U 型 → `symmetric_u`），报居中/穿节点/op 方向 →
   `fix_layout.py --apply` 自动修复复检；端口问题用 `edgeports.py` /
   `respread_ports.py` 兜底。**走线平直/间距均匀/打环/S 弯/cube 错位/
   公式未加粗也是确定性 warning**（见 Step 2 ⑤–⑩）：报"共线拐点"就删掉
   那个 `<mxPoint>`，"可走直却拐弯"就换端口侧或删拐点，报打环就翻 entry
   侧，报"uneven spacing"就挪框补间隙——这些都是实打实的观感缺陷，不是
   噪音。**draw.io CLI 导出 = 唯一预览真相**；自检 ≤2 轮，
   用户反馈 ≤5 轮。无 CLI 时 validate+recipe 0/0 即交付。
8. **顶会装裱**：Times New Roman + 半透明容器 + 底部虚线图例栏（多面板系统图
   用右侧图例列）；论文投稿底部图题（"Fig. N. ..."）。
9. **先选原型再动手**：单一网络→水平长条；训练流程→(a)(b)(c) 面板；
   多 Agent→分区面板+粗箭头；推理链→阶段容器+便签；多模态框架→深色标题栏
   横带（Step 1 表格）。密度下限见 Step 2。

## 常见问题

- **用户说"按这个代码文件画"** → 读代码，用 Step 0 清单逐模块登记，
  并注意代码里张量形状/`num_layers`/`num_heads` 等数字，用作标注。
- **用户给的是已存在的 draw.io 草图** → 读它的 XML，保留语义、按本 skill 的
  网格纪律和原型配方重排重写；若只是想换配色 → 按"样式预设"表逐格替换色值。
- **用户说"配色要跟我上次那篇论文一样"** → 引导他给出那张图（PNG 或 .drawio），
  你归纳色值存成预设，之后永远按名字复用。
- **图太宽** → 减小列距或组件宽度，或改自下而上方向，或拆 (a)(b) 面板。
- **中文标签** → 结构标注（loss、×N、形状）保留英文；模块名可用中文，
  draw.io 里中文自动用系统字体回退，不会缺字。
- **要 UML/ER/流程图等通用图** → 那不是本 skill 的射程，改用 drawio-skill。

## 依赖
- **draw.io 桌面端**（预览/导出需要；没有也能交付 .drawio 本身）：
  https://github.com/jgraph/drawio-desktop/releases 或网页 app.diagrams.net。
  探测路径含 `%LOCALAPPDATA%\Programs\draw.io\draw.io.exe`（Windows 按用户安装）；
  检测不到时 Step 3 会在**征得你同意后**用包管理器自动安装
  （Windows `winget install --id JGraph.Drawio`、macOS `brew install --cask drawio`、
  Linux `snap install drawio-desktop`）。
- **Python 3**（可选，仅标准库）：跑 `scripts/` 下的 validate / edgeports /
  respread_ports 结构校验与端口修复。**生成仍然全手写**——这三个是
  校验/修复工具，不是生成脚本；没有 Python 就靠视觉自检兜底。
