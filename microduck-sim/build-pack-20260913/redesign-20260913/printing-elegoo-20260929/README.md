> Updated 2026-09-29: use `../PRINTING/README.md` for the organized handoff. `USB-PRINT` now matches the six GUI-exported files with embedded thumbnails in `../PRINTING/03-PRINT/Elegoo`. The previous CLI files are retained under `CLI-GCODE-NO-PREVIEWS` for diagnosis only. The CLI export script now writes intermediate files there and cannot overwrite final USB files.

# MicroDuck — Elegoo Centauri Carbon / OrcaSlicer

2026-09-29，按用户指定的 Centauri Carbon 准备；标准 0.4 mm 喷嘴。此文件夹独立于原 Bambu 文件，原文件保持不变。

先打印 `USB-PRINT/MicroDuck_Elegoo_plate_5.gcode`。在 OrcaSlicer 按 ⌘O 打开 `MicroDuck-Centauri-Carbon-sliced.3mf` 查看项目；打印时复制普通 `.gcode` 到 U 盘，在 Centauri Carbon 的文件菜单中选择。无需再切片。不要把 Bambu `.gcode.3mf` 放到这台机器打印。

全部六盘为 `USB-PRINT/MicroDuck_Elegoo_plate_1.gcode` 至 `6.gcode`，89 个零件，原位置及方向保持不变，包含修正后的第三处头盖固定柱。

修改模型或参数时打开 `MicroDuck-Centauri-Carbon-Orca.3mf`；`MicroDuck-Centauri-Carbon-sliced.3mf` 是 Orca 原生六盘已切项目。

机器参数已设置：Centauri Carbon、0.4 mm 喷嘴、Textured PEI Plate（纹理 PEI 面），普通 PLA；喷嘴 220°C、热床 55°C，0.2 mm 层高，4 层墙，30% gyroid 填充，自动混合树状支撑，12 mm³/s 最大流量。起止指令来自 Orca 2.4.2 自带的 Centauri Carbon 专用配置。请在现场确认使用纹理 PEI 面和普通 PLA；不同喷嘴、板面、PETG/特殊PLA需修改相应配置重新切片。任意普通 PLA 颜色均可，绿色仅为预览。

Orca 默认树状支撑在首次切片报告了 potentially lost branch。已明确改为混合树状支撑并重新导出；验收要求原生日志无此错误。`handoff-verification.json` 记录六盘耗时、重量、哈希、89件几何对照和 Bambu 文件保持证据。

现场选择标准速度，观察前几层；第一盘完成后先检查孔位与配合，再打印其余盘。实际打印及试装尚未开始。

官方操作来源：https://elegoo-downloads.oss-us-west-1.aliyuncs.com/tutorials/Centauri%20Carbon/Accompanying/Centauri%20Carbon%20User%20Manual-EN-V1.2.pdf
