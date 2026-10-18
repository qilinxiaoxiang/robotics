# Pi相机接口邻域实际占据证据

局部轮廓依据第一代Zero W官方机械矢量图，原收到板照片仅作位置/外观对照，不从斜拍照片测高度。`local-occupancy.json`给出13个独立接收轮廓及源哈希；只允许替换官方板坐标X55.7..64.2、Y10.2..25.3的保守满盒，窗口外维持现有障碍。未修改实体/打印文件或200 mm排线路线。

CSI本体和接脚按兼容Amphenol厂家2.00 mm加0.20 mm接收裕量。主复核另有官方简化原理图J12的Molex54548-2271来源，实际连接器版本应由主复核统一绑定；这里不将兼容件当作已核实的安装件身份。

其余绘出的实际小件轮廓仍保留3.8 mm接收高度，不清空有元件的区域。官方简化原理图列出U3 PAM2306AYPKE、L1/L2 4.7u、C3/C4/C7/C8 2012及D2 GREEN1611，但没有给电感厂家料号，也没有将元件位号标在本机械图上。4×4八角件结合实拍形状很可能为电感，并不是3×3的PAM2306；这仍是身份推断，不能照搬其他Pi板的SRN4018料号和高度。

**没有证实该区域任何实际小件超过3.42 mm。** 同样，未知高度也不是超过3.42 mm的证明。保守轮廓与示例曲线有交集只表示这段软排线需要摆放余量/实际接触检查，不构成打印几何缺陷，不要求新增打印件。示例曲线是柔性余线摆放的一种参考，不是必须做出的固定形状；不能拉伸排线、折死或夹住它。

原14.05 mm³交集有部分投影落在小件轮廓，故不宜把全部交集称为空气。JSON中的顶点投影只是定位，不能替代真实实体交集；本证据也没有整根路线通过声称。

来源：

- https://pip-assets.raspberrypi.com/categories/592-raspberry-pi-zero-w/documents/RP-008367-DS-1-raspberry-pi-zero-w-mechanical-drawing.pdf
- https://datasheets.raspberrypi.com/rpizero/raspberry-pi-zero-w-reduced-schematics.pdf
- https://www.amphenol-cs.com/product/f32q1a7h111022.html

核验日期2026-10-08。JSON SHA256：`20354c4cba55b31de5b54c27b6c6ac136686db475de5bd1fb665017f6ce78003`。
