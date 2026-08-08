# 调色板

**使用方式**：没有加载脚本——按 kind 从下表抄 `fill / stroke / text` 的
十六进制值，直接写进你手写的 mxCell `style` 串
（`fillColor=…;strokeColor=…;fontColor=…;`）。

选哪一套：
1. 用户点名"用我的 `<name>` 风格" → 读 `~/.ccfa-arch-diagram/styles/<name>.json`
   （用户预设，同名覆盖内置），按里面的色值套；
2. 用户没点名 → 默认 `ccfa-standard`；或按模型气质从 6 套内置里挑
   （选色建议在文末）；
3. 用户给了参考图 → 你直接读图归纳色值（PNG 用视觉、.drawio 读 XML 里的
   fillColor），可以顺手存成 `~/.ccfa-arch-diagram/styles/<name>.json`
   预设供以后复用（格式见 `styles/schema.json`）。

**可用 kind：** `input` `tensor` `embedding` `positional` `attention` `module`
`feedforward` `norm` `residual` `loss` `output` `data` `default`

**字体**：每套调色板带 `font` 字段（默认 `Times New Roman`，顶会惯例）。
英文/数学符号用主字体，中文标签 draw.io 自动回退到系统中文字体。

**容器半透明**：分组容器用半透明填充（`fillOpacity=40` 左右），
复现顶会"半透明背景框"的通透质感。

> 组件可以显式覆盖颜色（style 里直接写 `fillColor`/`strokeColor`/`fontColor`），
> 但**只有在确有理由时**才覆盖——例如"强调这个 block 是本文贡献点"。
> 全部手工指定会让颜色失去体系。
> 想长期固定一套个人风格？把色板存成 `~/.ccfa-arch-diagram/styles/<name>.json`，
> 之后每张新图一句话套用（见 SKILL.md「样式预设」）。

---

## 0. `ccfa-standard`（顶会标准范式 · 默认）

从 8 份真实顶会生图提示词提炼：**低饱和半透明淡彩 + Times New Roman 黑字 +
黑色细边**。浅蓝(input/tensor)、浅紫(attention)、米黄(positional)、
橙黄(residual)、浅粉(loss)、浅绿(output)——顶会最常见的六色语言。

| kind | fill | stroke | text |
|---|---|---|---|
| input / tensor / embedding | `#DCE9F7` | `#3A5A8A` | `#1B2A3B` |
| positional | `#FBE5C6` | `#B0651A` | `#6E3D0A` |
| attention | `#E8DAEF` | `#6C4A8A` | `#3A2560` |
| module | `#FFFFFF` | `#3A4A5A` | `#202124` |
| feedforward | `#FFFFFF` | `#7A8A9A` | `#202124` |
| norm / data | `#F1F3F5` | `#7B8A9A` | `#3C4043` |
| residual | `#FAF3E3` | `#C9A06C` | `#6E4A1A` |
| loss | `#FADBD8` | `#C0392B` | `#7B241C` |
| output | `#D5F0DC` | `#1E8449` | `#145A32` |
| default | `#FFFFFF` | `#5F6368` | `#202124` |
| 容器 | `#FFFFFF`(半透明) | `#7B8A9A` | `#3A4A5A` |
| 字体 | Times New Roman | | |

---

---

## 1. `academic-blue`（学术蓝 · 默认）
NeurIPS / ICML / ICLR 最安全的选择。浅蓝作底、蓝描边、灰蓝文字，温和不抢戏。

| kind | fill | stroke | text |
|---|---|---|---|
| input / tensor / embedding | `#E8F0FE` | `#1A73E8` | `#174EA6` |
| positional | `#FEF7E0` | `#F29900` | `#8A5B00` |
| attention | `#D2E3FC` | `#1967D2` | `#0B3D7D` |
| module | `#FFFFFF` | `#4285F4` | `#202124` |
| feedforward | `#FFFFFF` | `#5F6368` | `#202124` |
| norm | `#F1F3F4` | `#80868B` | `#3C4043` |
| residual | `#F8F9FA` | `#9AA0A6` | `#3C4043` |
| loss | `#FCE8E6` | `#D93025` | `#8C1D18` |
| output | `#E6F4EA` | `#188038` | `#0D652D` |
| data | `#F8F9FA` | `#80868B` | `#202124` |
| default | `#FFFFFF` | `#5F6368` | `#202124` |
| 容器 | `#FAFBFC` | `#80868B` | `#5F6368` |

## 2. `print-grayscale`（打印灰度 · 投稿黑白版）
相机就绪。所有模块可区分度来自填充明度而非色相，色盲友好、打印安全。

| kind | fill | stroke | text |
|---|---|---|---|
| input / tensor / embedding | `#E0E0E0` | `#000000` | `#000000` |
| positional | `#BDBDBD` | `#000000` | `#000000` |
| attention | `#F5F5F5` | `#000000` | `#000000` |
| module | `#FFFFFF` | `#000000` | `#000000` |
| feedforward | `#FFFFFF` | `#424242` | `#000000` |
| norm / data | `#EEEEEE` | `#616161` | `#000000` |
| residual | `#F5F5F5` | `#9E9E9E` | `#000000` |
| loss | `#9E9E9E` | `#000000` | `#FFFFFF` |
| output | `#757575` | `#000000` | `#FFFFFF` |
| default | `#FFFFFF` | `#424242` | `#000000` |
| 容器 | `#FAFAFA` | `#9E9E9E` | `#424242` |

## 3. `neural-purple`（紫罗兰 · 现代方法）
扩散模型、生成模型、强调新颖性的工作常用。比蓝色更"潮"、更有记忆点。

| kind | fill | stroke | text |
|---|---|---|---|
| input / tensor / embedding | `#EDE7F6` | `#5E35B1` | `#311B92` |
| positional | `#FFF8E1` | `#F9A825` | `#7D5700` |
| attention | `#D1C4E9` | `#4527A0` | `#2A1966` |
| module | `#FFFFFF` | `#7E57C2` | `#1A1A2E` |
| feedforward | `#FFFFFF` | `#9575CD` | `#1A1A2E` |
| norm | `#F3E5F5` | `#AB47BC` | `#6A1B9A` |
| residual | `#F8F8FB` | `#B39DDB` | `#3A3A55` |
| loss | `#FCE4EC` | `#C2185B` | `#880E4F` |
| output | `#E0F7FA` | `#00838F` | `#004D57` |
| data | `#F5F5F5` | `#9E9E9E` | `#1A1A2E` |
| default | `#FFFFFF` | `#7E57C2` | `#1A1A2E` |
| 容器 | `#FAF8FD` | `#9575CD` | `#5E35B1` |

## 4. `vision-green`（青绿 · 计算机视觉）
CVPR / ICCV / ECCV 视觉稿件常见。青绿主色与"图像、特征图"的直觉贴合。

| kind | fill | stroke | text |
|---|---|---|---|
| input / tensor / embedding | `#E0F2F1` | `#00796B` | `#004D40` |
| positional | `#FFF8E1` | `#F9A825` | `#7D5700` |
| attention | `#B2DFDB` | `#00695C` | `#00352E` |
| module | `#FFFFFF` | `#00897B` | `#102027` |
| feedforward | `#FFFFFF` | `#4DB6AC` | `#102027` |
| norm / data | `#ECEFF1` | `#78909C` | `#37474F` |
| residual | `#F5F5F5` | `#B0BEC5` | `#37474F` |
| loss | `#FFEBEE` | `#D32F2F` | `#8B0000` |
| output | `#E8F5E9` | `#388E3C` | `#1B5E20` |
| default | `#FFFFFF` | `#00897B` | `#102027` |
| 容器 | `#FBFEFE` | `#80CBC4` | `#00695C` |

## 5. `warm-paper`（暖纸 · 极简）
解释性方法、推荐系统、偏向阅读体验的图。低饱和、暖底，安静耐看。

| kind | fill | stroke | text |
|---|---|---|---|
| input / tensor / embedding | `#FDEBD0` | `#E67E22` | `#7D3C00` |
| positional | `#F5E1C8` | `#C07B30` | `#6E4A1A` |
| attention | `#FAD7A0` | `#D35400` | `#6E2C00` |
| module | `#FFF9F0` | `#E67E22` | `#3D2B1F` |
| feedforward | `#FFF9F0` | `#D6A87E` | `#3D2B1F` |
| norm / data | `#F5EFE6` | `#A0866C` | `#5C4630` |
| residual | `#F8F2EA` | `#C9B7A3` | `#5C4630` |
| loss | `#FADBD8` | `#C0392B` | `#7B241C` |
| output | `#D5F0DC` | `#1E8449` | `#145A32` |
| default | `#FFF9F0` | `#C98A5A` | `#3D2B1F` |
| 容器 | `#FFFBF5` | `#C9A06C` | `#7D5A32` |

---

## 选色建议

- **不确定 / 顶会论文投稿** → `ccfa-standard`（默认，与真实顶会提示词的
  配色语言一致，永不犯错）。
- **偏经典蓝的安全牌** → `academic-blue`。
- **黑白打印投稿** → `print-grayscale`。
- **生成/扩散/很新的方法** → `neural-purple`。
- **视觉任务** → `vision-green`。
- **追求极简阅读感** → `warm-paper`。

如果你对模型的理解表明某类部件值得强调（如本文的创新模块），
直接在该组件的 style 里显式覆盖 `fillColor/strokeColor`——但全图最多 1-2 处，
否则会破坏"一图一体系"。
