# MicroDuck 当前硬件设计入口

2026-09-12。请使用 [整机装配与仿真方案](whole-robot-20260912/README.md)。它已取代先前局部支架和外置背包方案。

- [当前设计与打印包](MicroDuck-whole-assembly-20260912.zip)
- [电池与供电支架打印盘](whole-robot-20260912/printing/MicroDuck-compact-power-X1C-CoolPlate.3mf)
- [头壳、相机、音频与躯干 IMU 打印盘](whole-robot-20260912/printing/head/MicroDuck-head-camera-IMU-X1C-CoolPlate.3mf)
- [完整模型行走仿真录像](whole-robot-20260912/dynamics/MicroDuck-full-assembly-walking.mp4)

原完整模型为43/45，两组在40ms身体与关节数据延迟下摔倒。加入延迟补偿后，相同45组、相同标准全部通过。额外0–40ms检查27/27通过；60ms的9组全部摔倒，停车阶段另有一组转偏约46°。详见 [修复与边界报告](whole-robot-20260912/delay-repair-20260912/README.md)。补偿尚未接入机载程序；实物装配、公差、供电、传感器坐标和真实延迟仍需硬件验收。

旧版 `MicroDuck-print-and-CAD.zip`、十件背包支架盘、旧头壳打印盘、曲面垫座与内压板不再是当前方案。它们保留用于追溯，不能与新设计混装。旧说明保存在 `README-local-fit-superseded.md`。

Bambu Studio 已修复为可正常运行的官方2.7.1.62版本。RoboClub打印流程和软件修复证据仍在 `roboclub/`、`bambu-repair/`。
