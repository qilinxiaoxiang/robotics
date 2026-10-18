# 官方 61 维策略与社区运行程序兼容层

这个覆盖包（runtime overlay）把官方行走和站立 ONNX 策略接到社区 `WalkMove` 接口。它不是只替换 `walk.onnx`：输入构造、传感器坐标、策略选择与航向反馈也一起适配。原社区仓库没有被修改，模型文件随包提供，不需要临时联网下载。

## 具体改变

- 输入为 61 维：身体角速度 3、身体重力方向 3、相对默认姿态的关节位置 14、关节速度 14、上一帧动作 14、速度指令 3、头部指令 4、身体指令 6。最后 10 维明确置零；此版本不提供单独头／身体姿态指令。
- 重力从躯干 `body_quat` 计算 `R_body⁻¹ × [0,0,-1]`，不再使用社区旧的安装后 IMU 坐标与正 Z 重力字段。角速度从传感器坐标通过 `IMU_MOUNT_QUAT` 逆旋转回身体坐标。四元数顺序为 w、x、y、z，速度用 m/s 和 rad/s。
- 有运动指令时运行 `walk61.onnx`，无运动指令时运行 `stand61.onnx`；均真实核对了模型元数据中的关节顺序、61 维输入、14 维输出和 action_scale=1。
- 航向反馈比例系数为 2，转速限制为 0.8 rad/s。主动转向输入优先；松开转向后，沿刚才达到的方向前进。误差跨 ±π 正确回绕。也提供 `set_heading(yaw_radians)`，角度基准是 BNO 身体四元数当前使用的世界参考。
- 保留 1.5 秒平滑进入默认姿态的流程。策略开始时写入 `KP_RL=200`，退出时恢复原 `KP_DEFAULT`。`main.py` 的上电、初始姿态、服务和调度流程不改。
- 保留原 `MOTOR_OFFSET`、`MOTOR_SIGN` 与原 IMU 安装四元数。膝关节的 ±45° 偏移不会丢失。默认关节姿态采用本交付 5 V 仿真中的精确数值，并与 ONNX 舍入后的元数据核对。
- BAM／电流代理参数设为 `BAM_VIN=5.0`、`BAM_VIN_MIN=4.0`、`BAM_MAX_CURRENT=1.47`。**这些软件常数不会把实物电源变成 5 V，也不会写入舵机的电流上限寄存器。** 实物仍靠独立 5 V 稳压电路供电，舵机寄存器配置应按整机电气说明完成。

本覆盖包只接受 61 维策略。原 51／53 维行走模型保留在原路径；通过卸载恢复原 `WalkMove` 即可继续原流程，不在同一输入构造器里猜测模型维度。

## 在 Pi 上安装

先把完整 `runtime-overlay` 文件夹复制到 Pi，例如 `~/runtime-overlay`。目标参数必须指向含有 `src/` 的社区部署目录，例如 `~/microduck`。停止当前运行程序后执行：

```sh
sudo systemctl stop microduck-gamepad.service
python3 ~/runtime-overlay/install.py install ~/microduck
```

安装程序仅写四个文件：`src/moves/walk.py`、`src/constants.py`、`src/agents/walk61.onnx`、`src/agents/stand61.onnx`。原文件保存在目标目录的 `.runtime-overlay61-backup/`。安装程序不会启动服务，不连接串口／I²C，也不访问舵机。它核对原 `WalkMove` 的 SHA256；若 Pi 上版本不同，会停止并保留原文件，需要先比较该版本接口，不能强行覆盖。

在确认供电、IMU 朝向和电机零位后，继续使用原运行入口；例如手柄服务仍是：

```sh
sudo systemctl start microduck-gamepad.service
```

如果此前不用该服务，则沿用原来的手动入口，不需要另开第二个控制进程。原输入源的速度上限没有悄悄改掉：本交付最终整机验证使用 **0.3 m/s 的前进指令**，模型实际前进约 0.10–0.15 m/s；指令与实际速度不能混为一谈。原程序最高 0.7 m/s 未被当前完整装配仿真验证。

IMU 必须固定在躯干。新托架的实际板件方向应与 `IMU_MOUNT_QUAT` 一致；更换安装方向时，先用社区 `imu_orientation_check.py` 确认身体四元数和三轴方向，再进入策略。这里保留该常数，不推测实物传感器的安装校准结果。

## 卸载与恢复

停止正在运行的程序，再执行：

```sh
sudo systemctl stop microduck-gamepad.service
python3 ~/runtime-overlay/install.py uninstall ~/microduck
```

卸载按备份逐字恢复原文件，并移除原来不存在的两个 61 维模型。若覆盖后的文件又被人工修改，卸载会停止，避免抹掉后续编辑；原文件仍在备份目录。恢复后按原入口启动即可。

## 已通过的离线检查

`offline-verification.json` 记录了实际结果。测试复制真实社区 `src/` 到临时目录，在副本安装覆盖包，直接构造原 `observer.Observation`、`RobotState`、`UserInput`，并调用两个真实 ONNX 模型。它没有替造观测类或模拟神经网络输出。

测试覆盖：全部 61 个字段的独立数值对照、非平凡四元数下的重力和角速度、上一帧动作、行走输出与 ONNX 直接前向逐值一致、站立切换、启动阶段与 KP 写入记录、膝关节偏移保留、航向反馈增益／限幅／主动转向／跨 π、跌倒时保持目标、无效四元数拒绝，以及安装后卸载的字节级恢复。测试控制器只记录 KP 调用，不创建真实机器人控制器。

本机复现：

```sh
/tmp/microduck-cad-venv/bin/python test_offline.py /Users/xiangzheng/code/robotics/microduck-sim/Microduck-build-tutorial/microduck
```

依赖是 Python 3.10+、NumPy 和 ONNX Runtime；运行程序继续使用社区已经安装的依赖。覆盖包使用单线程 CPU 推理。未在 Pi 上测量 50 Hz 控制周期、内存峰值、USB／I²C 延迟，也没有完成机载走路、电流或跌倒保护实测。离线通过说明接口一致，不能写成真机已通过。

## 来源

社区控制接口来自 [AI-FanGe/Microduck-build-tutorial](https://github.com/AI-FanGe/Microduck-build-tutorial)，本包保留 GPL-3.0-or-later 标注和启动代码来源署名。官方策略来自 [pollen-robotics/microduck-simulator](https://github.com/pollen-robotics/microduck-simulator)，观测结构与 [microduck_rl](https://github.com/pollen-robotics/microduck_rl) 的速度任务一致。源文件和模型哈希写在 `source-lock.json`，实际模型留在 `models/`。
