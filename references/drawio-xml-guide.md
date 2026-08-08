# draw.io XML 手写指南（ccfa-arch-diagram 专用）

> 本 skill **不用任何生成脚本**：你（Claude）直接手写 `.drawio` 文件。
> 本文件是语法与样式速查。**动手前先读它**；写复杂图时，打开
> `examples/` 里对应原型的 `.drawio` 成品照着写——那 8 张是
> 验证过的标准范例，所有样式串都从它们里面来。

---

## 1. 文件骨架

```xml
<mxfile host="app.diagrams.net" agent="ccfa-arch-diagram" version="24.0.0">
  <diagram name="Figure 1" id="fig1">
    <mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1"
      connect="1" arrows="1" fold="1" page="1" pageScale="1"
      pageWidth="1650" pageHeight="710" math="0" shadow="0" background="#FFFFFF">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- 你的图元：vertex 与 edge，全部 parent="1" -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**铁律：**
- `id="0"` 和 `id="1"` 是保留根节点，**你的图元 id 不许用 0/1**，也不许重复。
- 每个 **edge** 必须有 `<mxGeometry relative="1" as="geometry"/>` 子节点——
  自闭合的 edge 单元格不渲染。
- 所有坐标/尺寸用**非负整数**；`pageWidth/pageHeight` 比内容大一圈即可。
- 文本里的 `&` `<` `>` 要转义（`&amp;` `&lt;` `&gt;`）；换行写 `&lt;br&gt;`
  （`html=1` 下 `\n` 无效）。⊕ ⊗ Σ ↑ ℒ × ⁻ 等 Unicode 符号直接写。

## 2. 顶点（组件）单元格

```xml
<mxCell id="conv1" value="Conv" style="..." vertex="1" parent="1">
  <mxGeometry x="240" y="320" width="46" height="110" as="geometry"/>
</mxCell>
```

### 形状样式速查（CCF-A 图元库）

底色/描边/字色从 [palette.md](palette.md) 按 kind 查表填入。公共后缀：
`whiteSpace=wrap;html=1;fontFamily=Times New Roman;fontSize=12;verticalAlign=middle;align=center;`

| 图元 | style 前缀（在公共后缀前） | 建议尺寸 |
|---|---|---|
| 模块（默认） | `rounded=1;arcSize=8;spacing=4;` | 150×44 |
| 张量 | `shape=parallelogram;perimeter=parallelogramPerimeter;fixedSize=1;spacing=4;` | 120×44 |
| 椭圆/汇聚 | `ellipse;` | 120×44 |
| 菱形分支 | `rhombus;` | 120×56 |
| **op 操作符小圆** | `ellipse;`（fontSize 加大到 16、`fontStyle=1`，白底 `#FFFFFF` 细灰边 `#5F6368`） | 34×34 |
| **vbar 竖条**（Conv/BN/激活链） | `rounded=1;arcSize=10;spacing=3;horizontal=0;`（`horizontal=0` 让文字竖排） | 46×110 |
| **cube 图像块** | `shape=cube;size=12;direction=south;spacing=4;` | 78×62 |
| **cylinder 数据集** | `shape=cylinder3;size=11;boundedLbl=1;spacing=3;` | 68×88（字多放宽到 100+） |
| **document 文本** | `shape=document;spacing=5;` | 110×82 |
| **note 便签** | `shape=note;size=14;spacing=6;` + `align=left;spacingLeft=8;` | 120×82 |
| **arrow 大箭头** | `shape=singleArrow;direction=east;spacing=2;` | 96×40 |
| **matrix 矩阵** | 见下方"复合图元" | 96×72 |

加粗：公共后缀里加 `fontStyle=1`。虚线描边（冻结副本）：`dashed=1;`。
显式覆盖颜色：`fillColor=#RRGGBB;strokeColor=#RRGGBB;fontColor=#RRGGBB;`。

### 复合图元：matrix（相似度矩阵/蒸馏目标）

一个直角矩形（标签放底部）+ 若干条**子边**画网格线（注意子边 parent
是该矩形 id，坐标用父相对坐标）：

```xml
<mxCell id="m1" value="M′  (BCD)" style="rounded=0;html=1;fillColor=#FDF5E4;strokeColor=#B08A2E;fontFamily=Times New Roman;fontSize=12;labelPosition=center;verticalLabelPosition=bottom;align=center;verticalAlign=bottom;" vertex="1" parent="1">
  <mxGeometry x="400" y="200" width="96" height="72" as="geometry"/>
</mxCell>
<mxCell id="m1_gh1" value="" style="endArrow=none;html=1;strokeColor=#B08A2E;strokeWidth=0.7;" edge="1" parent="m1">
  <mxGeometry relative="1" as="geometry">
    <mxPoint x="0" y="24" as="sourcePoint"/><mxPoint x="96" y="24" as="targetPoint"/>
  </mxGeometry>
</mxCell>
<!-- 3 行 4 列 → 2 条横线(y=24,48) + 3 条竖线(x=24,48,72) -->
```

## 3. 边（连线）单元格

```xml
<mxCell id="e1" value="B×h×w" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#5F6368;strokeWidth=1.2;endArrow=block;endFill=1;exitX=1;exitY=0.500;exitDx=0;exitDy=0;entryX=0;entryY=0.500;entryDx=0;entryDy=0;fontSize=10;fontColor=#5F6368;fontFamily=Times New Roman;labelBackgroundColor=#FFFFFF;" edge="1" parent="1" source="conv1" target="conv2">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

- **主线**：`strokeColor=#5F6368;strokeWidth=1.2;`（调色板 edge 色）。
- **虚线**（残差/监督/反馈）：`strokeColor=#9AA0A6;dashed=1;`（edge_dim 色）。
- **跨面板粗线**（系统主干）：`strokeColor=#C0762C;strokeWidth=2.4;`（edge_accent 色）。
- **端口**：`exitX/exitY/entryX/entryY` ∈ [0,1] 钉在图元边界上——右中 `(1,0.5)`、
  左中 `(0,0.5)`、上中 `(0.5,0)`、下中 `(0.5,1)`。
- **同侧多边槽位公式（铁律）**：某节点同一侧有 k 条边时，槽位取
  **(i+1)/(k+1)**（k=2 → 0.333/0.667；k=3 → 0.25/0.5/0.75；k=5 →
  0.167/0.333/0.5/0.667/0.833），并**按对端位置排序分配**（左侧/右侧的边
  按对端 y 从上到下，上侧/下侧的边按对端 x 从左到右）——排序分配是
  出线不交叉的关键。例外：从**相反方向**汇入同一个 op 小圆/汇聚点的边
  允许共享同一端口（合流叉），同方向并行的边**绝不允许**共享端口
  （两线全程重叠成一股）。
- **每条架构边必须"粘"在两端图元上（铁律）**：`source`/`target` 缺一不可，
  不允许存在"飘着的边"。**draw.io 桌面编辑器在打开/保存时会重写文件，且可能
  把已连好的边拆成「无 source/target 的游离线」**（geometry 里仍留着绝对
  sourcePoint/targetPoint）——手写文件时看不出，一旦被编辑器 touch 就会
  静默发生。校验器现在把「无 source/target 的边」一律判错（报 `edge … is
  detached`）；交付前跑一次 validate.py 即拦截。唯一合法的游离边是**图例短线
  样本**：必须同时有 sourcePoint+targetPoint、无拐点、无文字、长度 ≤120px
  （见 §6 图例）。
- **入口最后一段必须垂直于目标边（铁律）**：最后一个拐点必须与入口点错开，
  使最后一段沿目标边的法线方向切入——进上边则竖直向下、进下边则竖直向上、
  进左边则水平向右、进右边则水平向左。若最后一个拐点与目标边**共线**
  （例如进上边时 `last.y == box.y`），draw.io 会渲染成"箭头沿盒子边缘横滑"，
  看起来就是"没连上"。校验器对带拐点的边报 WARNING `waypoint … is
  collinear with target edge`；修法是把最后一个拐点挪到目标边之外、与入口点
  同轴（进上边时 `last.y < box.y - 1`、`last.x == 入口x`）。
- **写完后用工具兜底**：`python3 scripts/validate.py <file>` 会报"同侧
  端口堆叠"、detached 边、入口不垂直；未钉端口的堆叠用
  `python3 scripts/edgeports.py <file>` 自动分散；已钉但撞槽的用
  `python3 scripts/respread_ports.py <file>` 重铺。
- **箭头净空**：最后一个拐点到目标图元的直线段必须 ≥20px，否则箭头压弯角。
- **绕行**：边穿过无关图元时，在 geometry 里加拐点：
  ```xml
  <mxGeometry relative="1" as="geometry">
    <Array as="points"><mxPoint x="500" y="180"/></Array>
  </mxGeometry>
  ```
- 边标签默认落在中点；**带文字的边必须加 `labelBackgroundColor=#FFFFFF`**
  （已在模板里），否则文字悬空压线；太长就用 geometry 的 `x/y` 偏移挪到
  空白处。
- **标签必须装得进两盒之间（铁律）**：带文字的箭头，其两端盒子（source/
  target 图元）在垂直于边的方向上的间隔必须 > 标签的宽度——否则文字会
  盖到盒子上。校验器按边的主方向自动选口径：**横向为主的边比较标签宽**
  （Latin/数字 ≈0.55em、CJK/全角如 `×`/`·` ≈1.0em，加 4px 内边距），**竖向
  为主的边比较标签高**（行数 × fontSize×1.4 + 4px）；且要求两端盒在垂直
  方向上有交叠，才算是"两盒夹着这个标签"。超了怎么办：① 缩短标签
  （去掉不影响语义的词，如 "32 queries"→"32q"）；② 降 `fontSize`；
  ③ 给标签一个 `mxPoint y` 偏移挪到净空走廊（见下一条）。**不要把标签
  硬塞进更宽的盒子间隙——那会推动盒子和整条边重新排布，代价比缩字大。**
- **偏移标签必须落在净空走廊（铁律）**：带 `as="offset"` 的标签矩形
  （中点 + 偏移后 ± 标签半宽半高）**不得与任何非容器图元相交**；对容器
  则要么**整体落在容器内**（留 ≥2px），要么**整体在容器外**——骑跨容器
  边界视为非法。校验器不会自动拦这条（目检），但用它判断一个偏移是否
  可接受：先从 ±14/±28/±42… 往上找不碰任何东西的偏移，再落笔。
- **标签底色 = 所在容器填充色（铁律）**：箭头标签的中点落在哪个容器内，
  `labelBackgroundColor` 就设成该容器（最内层、面积最小者）的
  `fillColor`——否则在彩色面板（#E9F1FB/#FDF0EE/#EDF6EC/…）上，白底
  标签是一块刺眼的白斑。只有落在白色画布上时才用 `#FFFFFF`。校验器报
  WARNING `label sits on tinted container … but labelBackgroundColor is …`，
  修法就是照提示把底色改成容器 fill（如 `labelBackgroundColor=#F5E0DB`）。
- **带 `fillOpacity` 的容器：底色要用混合色（铁律）**：半透明容器实际渲染
  的底色 = 填充色与**白纸**按不透明度混合后的颜色，**不是原始 fillColor**。
  标签底色必须用混合后的颜色，否则仍是一块色差白斑。混合公式（R/G/B 每个
  通道独立）：`blend = round(fillCh × opacity/100 + 255 × (1 − opacity/100))`。
  例：`#E8DAEF` @ `fillOpacity=35` → 232×0.35+255×0.65 ≈ 247 → **`#F6F2F9`**；
  `#FAF3E3` @ 40 → `#FDFAF3`；`#F1F3F5` @ 45 → `#F8F9FA`。校验器对带
  fillOpacity 的容器**按混合色比较**，WARNING 提示里直接给出应设的十六进制值
  （如 `set labelBackgroundColor=#FDFAF3 (container 'g_dec2' renders fill
  #FAF3E3 at 40% over white = #FDFAF3)`）。容器一般开 `fillOpacity=40~70`，
  几乎所有半透明容器都触发这条——动手时先按公式把可见底色算好再填。
- **长边走外环**：跨越多个列带/道带的边（残差、反馈、跨面板），沿图的
  外圈走廊或面板缝隙走，不要从图元密集区中间穿膛。
- **箭头绝不从文字中间穿过（铁律）**：每条边的实际走向不得与任何**非自身**
  文本相交——即不能穿过**其他边的标签**（标签沿连线中点排布）和**独立的
  text 单元格**；穿过自己连的那个图元里的文字是正常的。校验器按实际走向
  判定：带拐点的边用 geometry 里存的拐点，自动路由的横平竖直边用两端盒
  中点的直线（对角线自动路由走法不可知，跳过）。报 WARNING `route passes
  through the label of edge …` / `passes through text cell …`。修法：
  ① 给被穿的标签加 `x/y` 偏移挪到净空处（见下一条）；② 给这条边加拐点
  绕到走廊走；③ 换 exit/entry 端口或槽位让整条边换一条走廊。

## 4. 容器（分组）三种标题形态

**① 顶部标题（默认）**——容器自带标签，文字在框内顶部居中：

```xml
<mxCell id="g1" value="Spatial-Spectral Prior Extraction" style="rounded=1;arcSize=4;whiteSpace=wrap;html=1;fillColor=#EAF1F9;strokeColor=#7A9BC7;fontColor=#2E4A6B;fillOpacity=70;fontFamily=Times New Roman;verticalAlign=bottom;verticalLabelPosition=top;align=center;spacingLeft=8;spacingTop=3;fontSize=11;fontStyle=1;" vertex="1" parent="1">
```

**② 底部斜体标题（原型 A 流水线惯例）**——容器无标签，标题是独立 text 单元格
贴在容器底边（`fontStyle=3` = 粗斜体）：

```xml
<mxCell id="g2" value="" style="rounded=1;arcSize=4;...fillOpacity=60;..." vertex="1" parent="1">…</mxCell>
<mxCell id="gt_g2" value="Shallow Feature Extraction" style="text;html=1;fontSize=12;fontStyle=3;align=center;verticalAlign=middle;fontColor=#7A6210;fontFamily=Times New Roman;" vertex="1" parent="1">
  <mxGeometry x="165" y="391" width="329" height="18" as="geometry"/>
</mxCell>
```

**③ 深色标题栏（原型 E 横带框架惯例）**——容器无标签，顶部叠一根 24px 高
深海军蓝条（`#2E3A4E` 白字粗体）：

```xml
<mxCell id="g3" value="" style="rounded=1;arcSize=4;...（容器填充/描边）..." vertex="1" parent="1">…</mxCell>
<mxCell id="ghdr_g3" value="Visual Encoder Stack" style="rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor=#2E3A4E;strokeColor=none;fontColor=#FFFFFF;fontFamily=Times New Roman;fontSize=12;fontStyle=1;align=center;verticalAlign=middle;" vertex="1" parent="1">
  <mxGeometry x="与容器同x" y="与容器同y" width="与容器同宽" height="24" as="geometry"/>
</mxCell>
```

容器几何 = 成员包围盒外扩 12px；顶部标题再 +16px，底部标题 +20px，
深色标题栏 +26px。容器填充用 `fillOpacity=40~70` 做出半透明背景框质感。

**标题带净空（铁律）**：顶部标题容器的**所有成员 y 必须 ≥ 容器 y + 24**
——标题带是容器顶部 24px 的专属区域，成员侵入就会把标题拦腰截断
（"GAT Layer 1 …" 被成员框压字是本 skill 的高发事故）。同理成员必须
**完全在容器内或完全在容器外**，不许骑跨容器边（>4px 的骑跨
validate.py 会报）。

## 5. 多面板子图（(a)(b)(c)）

每个子图 = 一块淡彩圆角大底板 + 左上角粗体标题 text；子图内部图元正常画，
全部 `parent="1"`（不要用 draw.io 的 container 嵌套，平铺即可，坐标全自己算）：

```xml
<mxCell id="panel_a" value="" style="rounded=1;arcSize=3;whiteSpace=wrap;html=1;fillColor=#E9F1FB;strokeColor=#7A9BC7;fillOpacity=55;dashed=0;fontFamily=Times New Roman;" vertex="1" parent="1">…</mxCell>
<mxCell id="ptitle_a" value="(a) Candidate Generation &amp; Evaluation" style="text;html=1;fontSize=13;fontStyle=1;align=left;verticalAlign=middle;fontColor=#233047;fontFamily=Times New Roman;" vertex="1" parent="1">
  <mxGeometry x="面板x+12" y="面板y+3" width="面板宽-24" height="20" as="geometry"/>
</mxCell>
```

- 面板底板**先画**（XML 里排在前面 = 压在底层），面板内边距 10px +
  顶部标题带 26px；面板间距 26px。
- 6 套面板淡彩循环（fill/stroke）：`#E9F1FB/#7A9BC7`、`#FDF0EE/#C78B85`、
  `#EDF6EC/#82B27E`、`#FDF5E4/#C7A661`、`#F3EEF9/#9B86C4`、`#E8F4F4/#7FB3B3`。
- **跨面板边**用第 3 节的粗线模板（2.4px、`#C0762C`）；反馈回路粗线 +
  `dashed=1`。方向按两端面板相对位置选 exit/entry（右→左或下→上）。
- **左侧阶段侧栏**（每排一条，竖排文字）：
  `rounded=1;arcSize=12;horizontal=0;fillColor=<该行面板色>;fontStyle=1;`，
  宽 40、高 = 该排面板高度，x = 面板x − 40 − 10。

## 6. 标题 / 图题 / 图例

```xml
<!-- 顶部标题（演示用；fontStyle=1） -->
<mxCell id="diagram_title" value="..." style="text;html=1;fontSize=15;fontStyle=1;align=center;verticalAlign=middle;fontColor=#202124;fontFamily=Times New Roman;" vertex="1" parent="1">…</mxCell>
<!-- 底部图题（投稿用："Fig. 1. ..."） -->
<mxCell id="diagram_caption" value="..." style="text;html=1;fontSize=13;fontStyle=0;align=center;verticalAlign=middle;fontColor=#202124;fontFamily=Times New Roman;" vertex="1" parent="1">…</mxCell>
```

**图例**三种摆法：
- **底部横贯栏（bar，默认）**：一根全宽虚线圆角长条（`legend_box` 样式：
  `rounded=1;arcSize=4;fillColor=#FFFFFF;strokeColor=#B8C2CC;dashed=1;`，高 44），
  里面等距摆"色样 + 文字"对。
- **右下角小框（box）**：同上，缩小放右下角。
- **右侧竖列（column，多面板系统图惯例）**：画布右侧加宽 200px，
  色样/文字逐行竖排。

图例条目三种色样：
```xml
<!-- 色块：24×16 圆角小矩形 -->
<mxCell id="lg1" value="" style="rounded=1;arcSize=10;fillColor=#D9C7E8;strokeColor=#7A5C9E;" vertex="1" parent="1">…</mxCell>
<!-- 操作符：20×20 白底圆圈，value 写符号，fontStyle=1 -->
<mxCell id="lg2" value="⊕" style="ellipse;fillColor=#FFFFFF;strokeColor=#5F6368;fontColor=#5F6368;fontSize=11;fontStyle=1;fontFamily=Times New Roman;" vertex="1" parent="1">…</mxCell>
<!-- 线样：40px 长边（实线/虚线/粗线对应第 3 节三种线型） -->
<mxCell id="lg3" value="" style="endArrow=block;endFill=1;html=1;strokeColor=#C0762C;strokeWidth=2.4;" edge="1" parent="1">
  <mxGeometry relative="1" as="geometry"><mxPoint x="0" y="0" as="sourcePoint"/><mxPoint x="40" y="0" as="targetPoint"/></mxGeometry>
</mxCell>
<!-- 文字标签 -->
<mxCell id="lg4" value="3×3 Conv" style="text;html=1;fontColor=#3C4043;fontFamily=Times New Roman;fontSize=11;align=left;verticalAlign=middle;" vertex="1" parent="1">…</mxCell>
```

## 7. 手工布局纪律（替代原引擎的坐标带）

没有引擎帮你算坐标了，**自己按网格算**，这是"不重叠"的唯一保障：

1. **列带/道带思维**：先在草稿里给每个组件定 (layer, lane)。
   第 i 列 x = 边距 + Σ(前列宽 + 列距)；第 j 行 y = 顶距 + Σ(前行高 + 行距)。
   **列距 40、行距 18-40、整图边距 36**——这是顶会紧凑密度的默认值。
2. 所有坐标取 **10 的倍数**（draw.io 网格），同列上下对齐、同行左右对齐。
3. 容器在成员就位**之后**再算：成员包围盒 + 对应标题形态的外扩量（第 4 节）。
4. 面板在全部内容就位**之后**再算：内容包围盒 + 10px 边距 + 26px 标题带。
5. 写完心算一遍包围盒相交检查：任何两个非容器图元的 (x,y,w,h) 不得相交；
   或者更省事——直接跑 `python3 scripts/validate.py <file>`，重叠/骑跨/
   标题带侵入/端口堆叠/超宽全部报出来。
6. **宽度硬上限**：内容总宽 ≤ 2200px。预览导出 `--width 2000` 会整体
   缩放，图越宽线越细字越小——2700px 宽的图缩完 1.2px 主线只剩 0.9px、
   近乎隐形（GAT 评测图的事故）。超宽必须缩列距、换方向或拆 (a)(b) 面板，
   不许硬扛。画布页宽 ≈ 内容宽 + 72。
6b. **A4 适配（铁律）**：交付前先定页型，把 `mxGraphModel` 的
   `pageWidth/pageHeight` 声明成目标纸张——**A4 竖版 = 794×1123**、
   **A4 横版 = 1122×794**（@96dpi）。skill 同时支持两种页型，**默认横版
   = 1122×794**。校验器把内容包围盒与声明页比较：内容必须**整体落在
   页面内**（±2px 容差）；纵横比（高/宽）偏差 ≤30% 的检查**只对铺满型图
   生效**——即内容同时在两个方向都 ≥70% 页宽/页高时才检查，防止"声明一个
   巨大页面骗过适配"或"横版图被误标成竖版页"，紧凑图豁免。报 WARNING
   `overflows the declared page` 时：横向已到顶就**沿纵向展开**（竖版页的
   合法扩容方向）——加行/加层、把横排改蛇形折行、拉长页面内的有效高度；
   套用：横版大图改竖版 = 列→行折叠 + 左侧/右侧边距变供给通道。
6c. **紧凑图框（铁律）**：图框**只比其字段略大**，不刻意留白、不刻意铺满
   整张纸——实际论文里一张图至多占一张纸的 1/3。图框宽 = 最长字段（顶部
   标题或最宽 chip）的文本宽 + 约 16-20px 余量；chip 宽 = 文本宽 + 约
   8-12px；行距/列距只留走线走廊（40px 列距 / 18-40px 行距），不要为了凑
   满页面而加空档。报 `content aspect … deviates` 且图并非铺满型时，说明
   还有压缩空间，先按"字段宽 + 小余量"收窄图框再谈扩容。
6d. **标题净空（铁律）**：带顶部标题的图框，**任何箭头不得从其顶部标题
   字上穿过**。规范：① 从目标框顶部进入的边，入口 x 必须落在标题文字
   横向区间**之外**（把连接点挪到标题净空处，或让标题偏置）；② 任何可达
   路径不得穿过其他框的标题带；③ 带文字的边一律加 `labelBackgroundColor`
   （见 §3），且路径拐点避开所有文字。校验器对 `verticalLabelPosition=top`
   且有文字的图框计算标题矩形，报 `enters titled box … beneath its own
   title` / `route passes through the top title of box …`，按 ① 修正到清零。
   **浮动标签陷阱**：`verticalLabelPosition=top` 只在**容器**（框内有子结点）
   上把标题画进框内顶带；画在**无子结点的非容器**上时，draw.io 会把标题渲染成
   **悬浮在框上方**的独立文本——它压住上方的东西（主标题/上一行）、塞进走廊
   里撞线和标签，`validate` 因几何上框内并无标题而报不出这些视觉重叠。**本 skill
   的正规写法（framework_bands 等范例通用）**：图框 `value=""`，标题画成独立
   文字格 `text;html=1;fontSize=…;fontStyle=1;…` 贴进框内顶部（宽 = 标题字形宽
   ≈ latin 0.55em/CJK 1.0em + 6px，居中或左对齐，y ≈ 框顶+2，框顶到 chip 留
   ≥8px）；这样的文字格被 `validate` 视为文字单元参与箭头穿字检查，且框内文字
   格标题同样享有顶部入口净空（`text_cell_titles`）。**浮动标签一旦出现**
   （图里某个框标题肉眼上浮、压字），就地改为"value='' + 框内标题格"。
7. **走线走廊**：列距/行距不只是隔离图元，也是走线通道。规划长边
   （残差、反馈、跨面板）时先想好它走哪条走廊，**走廊里不放图元**；
   多入多出的枢纽节点（融合层、op 圆）放中心，让边辐射状散开而不是
   横跨全图。

## 8. 结构校验与导出（draw.io 桌面 CLI）

**写完 XML 先做结构校验（不依赖 draw.io，Python 3 标准库即可）**：

```bash
python3 scripts/validate.py figure.drawio            # 结构 lint：悬空边/入口不垂直/重复id/重叠/标题带/端口堆叠/超宽/标签超宽/标签底色/贴边/A4适配/箭头穿标题/箭头穿字
python3 scripts/edgeports.py figure.drawio           # 同侧未钉端口的多条边 → 自动按对端位置分散
python3 scripts/respread_ports.py figure.drawio      # 已钉但撞槽的端口 → 按槽位公式重铺
```

validate.py 报 **error 必须修完再导出**；warning 逐条过一遍（多为真实的
走线/布局缺陷）。标签/子框/A4/穿字相关的警告都是确定性规则，修法见 §3
铁律：`label is ~Npx wide but the gap is only Mpx`（标签超宽→缩字/降字号/
偏移）、`label sits on tinted container`（底色=容器 fill）、`touches
container's … border`（子框留 ≥4px 边距）、`route passes through the label
of edge …` / `passes through text cell …`（箭头穿字→偏移标签/边加拐点，
见 §3）、`overflows the declared page` / `content aspect … deviates`
（A4 适配→横向到顶就沿纵向展开，见 §7）。edgeports.py 跳过你手钉的端口、幂等；respread_ports.py
是字节精确改写，只动撞槽边的 exit/entry 值。三个脚本都是纯标准库，
没有 Python 时跳过此步、靠第 9 节视觉自检兜底。

**先探测 CLI**（任一能打印版本号即为可用，后续命令沿用该写法）：

```bash
drawio --version                                   # PATH 里（macOS Homebrew/Linux）
"C:\Program Files\draw.io\draw.io.exe" --version   # Windows
/Applications/draw.io.app/Contents/MacOS/draw.io --version  # macOS 直装
```

**预览导出（自检用，不要 `-e`，宽度限制 2000）**：

```bash
drawio -x -f png --width 2000 -o figure.png figure.drawio
```

**最终导出（交付用，`-e` 嵌入 XML 保持可编辑，`-s 2` 高清）**：

```bash
drawio -x -f png -e -s 2 -o figure.drawio.png figure.drawio
drawio -x -f svg -e -o figure.svg figure.drawio     # 矢量，投稿推荐
```

关键坑：
- **`-e` 的 PNG 不要把给视觉模型读**——draw.io CLI 的 `-e` PNG 截断 IEND 块，
  视觉 API 会 400。预览永远用无 `-e` 的版本。
- 预览图必须 ≤ 2576×2576px（视觉模型上限）——用 `--width 2000`，**不要** `-s 2`，
  也不要用 `-w`（不存在，静默破坏参数解析）。
- `--layout` 标志只在 CLI ≥ v30 存在且会重排节点——**不要用**，布局你自己算。
- **CLI 不存在时**：直接交付 `.drawio` 文件，告诉用户用 draw.io 桌面端
  （File→Open）或网页版 app.diagrams.net 打开并导出（File→Export as→PNG/SVG，
  300 dpi）。不要尝试用 Python 库自己渲染预览。

## 9. 自检清单（先 validate.py，后导出 PNG 视觉检查，≤2 轮）

**第 0 步（确定性检查）**：`python3 scripts/validate.py <file> --score`——
重叠、骑跨、标题带侵入、端口堆叠、标签超宽、标签底色、贴边、超宽、
**A4 适配、箭头穿字**在这一步就该清零，不要留给肉眼。

**第 1 步（视觉检查）**，导出预览 PNG 后逐项对照：

| 检查 | 修复 |
|---|---|
| 图元重叠/堆叠 | 拉开间距（≥40px 列距） |
| 文字溢出/被裁 | 加宽加高图元，或缩短 label |
| 容器标题被成员压字 | 成员下移出 24px 标题带，或加高容器 |
| 箭头没接上/游离线 | 核对 source/target id 存在；游离线是编辑器拆的——补回 source+target（见 §3 铁律），validate.py 已报 `detached` |
| 箭头沿盒子边横滑（看似没连上） | 最后一个拐点与目标边共线——把拐点挪到目标边之外、与入口点同轴（见 §3 入口垂直铁律） |
| 边穿过无关图元 | 加 `<Array as="points">` 拐点沿走廊绕行 |
| 同侧箭头叠成一股 | 按槽位公式 (i+1)/(k+1) 分散端口；或跑 edgeports.py / respread_ports.py |
| 边标签悬空压线 | 补 `labelBackgroundColor=#FFFFFF` + x/y 偏移 |
| 箭头标签被两端盒子挤/盖到盒子上 | 盒间隔 > 标签宽（横向比宽、竖向比高，见 §3 铁律）——缩短标签/降 fontSize/加 x/y 偏移 |
| 标签白底在彩色面板上突兀 | 标签中点所在最内层容器的 fillColor 就是 `labelBackgroundColor`（见 §3 铁律） |
| 子框贴大框边界、像粘在边沿 | 子框距容器边框 ≥4px 内边距（校验器报 `touches container's … border`） |
| 箭头从文字中间穿过 | 校验器报 `route passes through …`——给被穿的标签加 x/y 偏移挪到净空处，或给边加拐点绕走廊走（见 §3） |
| 内容溢出纸面 / 图上留一条横幅空白 | 校验器报 `overflows the declared page` / `content aspect … deviates`——横向到顶就沿纵向展开：加行/蛇形折行/拉长页内高度，同时缩间距去空挡（见 §7 6b） |
| 预览里线条细得快看不见 | 图太宽（>2200px）——缩列距/换方向/拆面板，不是加粗能救的 |

改单点问题就**就地改 XML**（保留已调好的布局）；改整体方向才重写整文件。
预览 PNG 每轮覆盖同名文件，不留 v1/v2/v3。
