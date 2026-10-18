# MicroDuck 硬件核查记录

核查日期：2026-09-12。范围：AI-FanGe 社区自装版本与第一轮单目视觉扩展。问题对应：P1（真实观测与动作数据）、P5（硬件与供电）、P6（网络与控制响应）。本记录不等于真机验收。

## 当前源代码

- 已获取上游最新提交：49678215d0b40529522772a40c06c216390449dd。
- 2026-09-11 的三个提交删除了 microduck/docs、microduck/cad 和训练仓 robot 目录。未推断作者的删除原因。
- README 与此前 2026-09-09 保存版本逐字节一致；打印 3MF 也逐字节一致，仍是 2026-09-07 版本。
- walk.onnx 文件为 773115 字节，约 0.773 MB。main.py 在 Pi 上以 50Hz 调度，moves/walk.py 用 ONNX Runtime 加载模型；模型文件大小不是实测运行内存。
- main.py 和 input/keyboard_input.py 支持电脑远程终端键盘操作，不要求手柄。当前无线视频和视觉动作回传未实现或验收。

## 相机与接口

- 候选第一版：Raspberry Pi Zero 2 W + Camera Module 3 Wide + 匹配的 Zero 相机排线 + 电脑视觉计算 + 电脑键盘输入。
- 单相机使用 CSI 相机接口，OpenRB 使用 USB 数据接口，BNO085 使用 GPIO 上的 I2C，Wi-Fi 已板载；供电另行分配。这仅证明接口类别可分配。
- Camera Module 3 Wide 外形为 25 × 24 × 12.4 mm，需要 15-pin 到 22-pin 的合适相机排线。
- 检查了 3MF 的五个盘面和结构网格。未发现资料明确提供 Camera Module 3 Wide 安装支架或经过验证的安装位置；需要增加专用支架并检查镜头无遮挡、排线弯折和低头运动。
- 第一轮可在平面目标、已知相机姿态下做单目地面定位；头部运动时要更新相机姿态，不能一直使用固定头部的像素到地面映射。
- 建议起测 720p、15–30fps、H.264 目标 2–4Mbps。这是测试设置，不是本机已测吞吐量或画质保证。未压缩 RGB 720p30（每通道8位）算术数据量为 663.552Mbps。需测试曝光到电脑得到结果的整体延迟，以及视觉并发时本地控制是否按时执行。

## 电池与打印件

- 视频约 02:12 的商品图显示：19 × 37 × 66 mm、98g、1800mAh、标称6.4V、输出0–3A；README只写成品6V电池，信息不一致。
- 视频 09:27–09:32 说明其电池较大，作者因此给结构切口。video-568.png 与 video-572.png 保留了原始画面。
- 作者采用背部开放式安装与电子板捆扎布置；看到了装机实例，但未找到对该电池的封闭安装空间、间隙、托架和紧固方式的完整尺寸证明。
- 3MF 是零件打印排版，单零件外形尺寸不能当作整个装配体的可用容积。dimensions.json 保存模型尺寸，仅用于核对，不用于证明电池可装入。
- 不能承诺电池买来即可完整藏入原外壳，也不能把胶带整理线材等同于抗跌落的电池固定。建议采用贴合电池的打印托架和可拆束带；尚未完成该托架设计及试装。
- XL330官方要求3.7–6.0V，推荐5V。此前商品的6.4V标称值已超过上限，不能照视频直接接入；电源方案需按照满电电压和实际峰值电流重新核对。关闭电压错误保护不能解决过压。

## 改变当前判断的证据

- 单目方案：真实目标地面定位误差、低头遮挡、端到端延迟、并发时50Hz控制失约情况。
- 相机安装：固定支架的几何碰撞检查与真实动作范围验证。
- 电池：选定实物含插头尺寸、装配体空间、固定后移动量、稳压输出和运动峰值电流。

## 一手资料

- 社区源码：https://github.com/AI-FanGe/Microduck-build-tutorial
- Pi Zero 2 W：https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/
- 相机：https://www.raspberrypi.com/products/camera-module-3/
- 相机软件与网络传输：https://www.raspberrypi.com/documentation/computers/camera_software.html
- OpenRB：https://emanual.robotis.com/docs/en/parts/controller/openrb-150/
- DYNAMIXEL 通信：https://emanual.robotis.com/docs/en/dxl/protocol2/
- 舵机规格：https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/
- 单目平面几何：https://docs.opencv.org/4.13.0/d9/dab/tutorial_homography.html
- 视频原始本地文件：/Users/xiangzheng/code/robotics/tmp/pdfs/visual-assets/fange-tutorial.mp4
