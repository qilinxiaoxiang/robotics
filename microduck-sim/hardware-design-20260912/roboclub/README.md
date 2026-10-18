# RoboClub 3D 打印：原教程核查

核查日期：2026-09-12。原件标题为 **Roboclub FDM 3D Printing Guide: BambuLabs X1C**，自标更新时间 **May 2025**，共 21 页。本文页码以本地 PDF 第 1 页为封面计算。

[Google Slides 原件](https://docs.google.com/presentation/d/1uD7Wo81Q8DFQthC9kWkNNhRoxS2q6-W2qNm7Z7F09W4/mobilepresent?slide=id.p)。本目录保留原 PDF、全部页图、逐页文字与来源清单。

## 适用的机器与配置

- 第 9 页：选择 **Bambu Lab X1 Carbon 0.4 mm**。0.4 mm 是喷嘴（nozzle）口径。
- 第 10 页：安装 **Bambu PLA Basic** 和 **Generic PLA** 的耗材预设。PLA 是聚乳酸打印塑料；本教程没有批准使用其他材料的说明。
- 第 12 页：实际准备打印时，机器为 **Bambu X1 Carbon 0.4**，打印板（build plate）为 **Cool Plate / PLA Plate**，耗材为 **PLA Basic**。
- 第 13 页：推荐 **0.20 mm Standard**，即每层 0.20 mm 的标准层高（layer height）。
- 第 14 页：悬垂约超过 45–60 度时启用支撑（support），否则不需要。原页未明确角度参照方向，不应直接把这个文字当成软件的固定阈值。
- 第 15 页：外观件或低受力件的内部填充（infill）约 10–15%；需要强度的件应提高填充。教程没有给承力支架指定壁数或确切更高比例。

这套配置来自 2025 年教程，不能证明现场任一台机器当天装的打印板与耗材。当前设计可按这个配置完成本地切片，正式输出给机器前需要与选中机器实物一致。

## 从三维模型到打印文件

1. 第 5–6 页：先在 CAD（Computer-Aided Design，计算机辅助设计）软件里建立零件，再导出 STL 三角网格模型。教程列出的 CAD 包括 SolidWorks、Fusion 360、Onshape、TinkerCAD。
2. 第 8 页：安装 **Bambu Studio**，也可以使用 RoboClub 电脑。
3. 第 16 页：Bambu Studio 可导入 3MF/STL/STEP/SVG/OBJ/AMF，调整旋转、位置、比例等。机械件应保持设计尺寸；不能为了装进打印板随意缩放。
4. 第 17 页：点击 **Slice plate**（切片整张打印板），得到逐层打印路径，并查看时间估计。
5. 第 18 页：点击 **Export plate sliced file**（导出已切片文件），保存到所用打印机的 microSD 卡。**文件名必须以本人 AndrewID 开头。**
6. 第 19–20 页：把卡插入打印机，选文件、选择 PLA 料卷并确认余量，打印前给板涂胶且 PLA 面朝上，然后开始打印。
7. 第 20 页：**必须在机器旁观察前几层，之后才可离开。**

CAD 负责形状、尺寸、螺孔和装配关系；slicer（切片软件）负责把模型变为打印机逐层运动指令。Bambu Studio 是切片与检查环节，不能凭切片成功证明装配正确或强度足够。

## 教程明确的使用要求

- 第 3 页：BioRAFT 中的 **Student Shop Safety** 和 **3D Printing Safety Training**。
- 第 18 页：AndrewID 文件名前缀。
- 第 20 页：选择足量 PLA、给正确板面涂胶、现场看前几层。
- 第 21 页：[Printertron](https://printertron.roboclub.org/) 可监视打印。
- 21 页中未给出预约方式、排队规则、打印最长时限、收费规则或上传给管理员代打的提交表单。不能从这些页推断免培训、免预约或无限量使用。

## 当前机器清单的交叉核实

2026-09-12 实时打开 Printertron，页面列出 **Ted、Po、Mei** 三台 **Bambu X1-Carbon**。同时还有 Elegoo Centauri Carbon 和 Prusa 机器。名称为 **Bamboo** 的那一台实际标作 **Prusa i3 MK3S**；选机器时以型号为准。只读页面未证明具体机器空闲或能立即开印。

## 本地原始证据

- `roboclub-3d-printing.pdf`：从用户给定同一文档导出的 21 页 PDF。
- `page-01.png` 至 `page-21.png`：每页完整截图。
- `extracted.txt`：逐页提取文字。
- `pages.json`：文字和页内链接。
- `printertron.html`：当前监控页面原件。
- `manifest.json`：原 URL、导出 URL、获取时间和 PDF SHA-256。

本次未启动打印、未发送任何消息、未修改共享文档、未操作 Bambu Studio 原生 UI。
