# 树莓派已经能发舵机数据，为什么这套方案还接 OpenRB？

核验：2026-09-12。推进 P5（可维护、能真实工作的机器人本体）。这里纠正的是接口机制；不把几何仿真当作实际电气验证。

**树莓派自己能生成舵机所需的串口位流。OpenRB 在这套方案里主要是 USB 转舵机总线的接口，不是因为树莓派缺算力、缺引脚，也不是走路控制必须再经过一个独立大脑。**

可以把“给 3 号舵机一个目标角度”分成三件事：

1. Pi 上的程序算出目标角度，并由通信库组织指令字节。
2. UART（Universal Asynchronous Receiver-Transmitter，通用异步收发器）把字节按波特率转换成引脚上的高低电压。Pi 芯片已经有这个硬件；它能自己准确产生每一位，普通 Linux 程序不需要逐微秒翻转引脚。
3. XL330 使用一根 DATA 数据线轮流收、发。Pi 普通 UART 则有分开的 TX（发送）与 RX（接收）引脚。这里缺的是收发连接与切换电路。

[Pi 官方 UART 配置](https://www.raspberrypi.com/documentation/computers/configuration.html#configure-uarts)明确给出 GPIO14/实体针脚 8 为 TX，GPIO15/针脚 10 为 RX。Zero 2 W 可把 PL011 UART 分配到这些引脚，关闭串口登录控制台，避开蓝牙占用。硬件串口的逐位时钟与 Linux 何时开始下一包数据，是两个问题。

## 缺的不是“产生 0 和 1”，而是“轮到别人说话时松开这根线”

UART 发送完之后，TX 通常仍主动维持空闲高电平，**并没有自动变成断开状态**。如果把 Pi TX、Pi RX、舵机 DATA 三根线直接拧在一起，舵机回复一个低电平时，Pi TX 还在把同一根线拉高，两个输出端便互相冲突。

需要让发送端变成 high impedance（高阻态，近似从总线上电气退出），此时舵机才可以把 DATA 拉高或拉低，Pi RX 读取回复。这叫 half-duplex（半双工：同一通道轮流双向通信）。将 TX 切为低电平不等于释放总线；把 TX 切成输入虽能改变电气状态，但每次切换引脚功能与串口时序也要正确处理。

XL330 官方规格为 **3.3 V TTL，兼容 5 V TTL**。因此不能把 OpenRB 的必要性解释成“Pi 的 3.3 V 必须升到 5 V”。Pi 的接收端不能直接接未经限制的 5 V 输出；接口应按实际总线电平设计。[XL330 官方通信说明](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/)

## OpenRB 的原理图与固件实际做了什么

已下载并打开官方原理图：`sources/openrb-schematic.pdf` 第 3 页，右侧电路名字就是 **TTL with Auto TX Enable**（自动启用发送的 TTL 接口）。

- U4：74HC2G14，加 D2 二极管、R16/C7 电阻电容，从 TXD 信号产生 TTL_TXEN。它是板上的自动电路。
- U3：74LVC1G126，带输出使能的三态发送缓冲器，将串口发送端接入或移出 DATA 总线。
- U7：74LVC1G125，接收缓冲器，输出使能的有效方向与发送端相反；接收侧输出供电为 3.3 V。
- 四个 DYNAMIXEL 插口共用 DXL_TTL 网络，并非四路独立控制大脑。

[ROBOTIS 官方原理图下载入口](https://www.robotis.com/service/download.php?no=2117)。本地保存的原图有 3 页，第 3 页落款 2025-03-06；下载文件名中的 20231130 不能用作唯一版本日期。

官方 `usb_to_dynamixel.ino` 的实际流程是：USB 有字节，就逐个写到 `Serial1`；Serial1 收到字节，就读出并发回 USB；USB 设置的波特率变化时重新配置 Serial1。**此示例没有计算姿态、行走轨迹或关节力矩，也没有程序控制 DIR 引脚的代码；板上的自动切换电路承担这件事。**[固件固定版本](https://github.com/ROBOTIS-GIT/OpenRB-150/blob/3e2b07eb676097503d443f702d2a64519e7ae8f8/libraries/OpenRB-150/examples/usb_to_dynamixel/usb_to_dynamixel.ino)

社区程序也在 Pi 一侧调用 `Xl330PyController` 和 `sync_write_goal_position`。舵机收到目标以后，电机内部的控制电路负责实际转动和保持位置。这与 OpenRB USB 转接器是不同层的控制。

## 可以具体用什么代替 OpenRB

**电路上可以用 Pi UART + 两个三态缓冲芯片替代。**下面是针对 XL330 的 3.3 V 逻辑参考接法；这是基于芯片规格成立的设计，当前没有在实物 Pi/XL330 上验收，不能当作已经焊好可用的成品模块。

- 发送缓冲器：Nexperia 74LVC1G126。A 接 Pi GPIO14/TX；Y 经串联电阻接 DATA；OE 接方向信号 DIR。
- 接收缓冲器：Nexperia 74LVC1G125。A 接 DATA；Y 接 Pi GPIO15/RX；低有效的 OE 接同一个 DIR。
- 两颗芯片都用 3.3 V 供电，各放 100 nF 去耦电容，Pi 与舵机电源共地。DATA 上拉接 3.3 V；串联/上拉阻值需结合总线长度和波形确认，不能只靠原理图承诺长线多舵机效果。
- DIR 可接空闲的 Pi GPIO17；加下拉使开机默认处于接收状态。DIR 高时，126 发送而 125 停止向 RX 输出；DIR 低时，126 高阻退出，125 让舵机回复进入 RX。
- 5 V 电机动力电源仍单独进入舵机 VDD；不能从 Pi GPIO 给电机供电。

[74LVC1G126 数据资料](https://www.nexperia.com/products/analog-logic-ics/logic/buffers-inverters-transceivers/buffers/series/74LVC1G126.html)、[74LVC1G125 数据资料](https://www.nexperia.com/products/analog-logic-ics/logic/buffers-inverters-transceivers/buffers/series/74LVC1G125.html)确认两者三态功能、1.65–5.5 V 供电和输入耐压范围。它们承担接口功能，无需第二颗执行行走策略的处理器。

软件要在最后一位真正离开 UART 后再把 DIR 拉低，并在舵机回复前完成切换。XL330 默认回复延迟为 500 μs，最大 508 μs；不能凭一次 Python 测试就宣称在相机编码、Wi-Fi 与系统负载下始终满足这个时间。可走两条工程路径：使用驱动支持并验证过的硬件方向控制；或参考 OpenRB 使用自动收发电路，让电路从发送波形触发切换。[回复延迟寄存器](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/#return-delay-time9)

这说明了“能不能省”：**能省 OpenRB 这块板，但需要把它已经提供的接口电路和验证工作补上。**本次整机基准保留 OpenRB，理由是复用现成接口。更换为小接口板是后续可实施的体积/重量优化，不是 Pi 能力的物理上限。

真正的替代验收应包括：在 1 Mbps 下看 TX/DATA/RX 波形，确认最后停止位完整、发送端及时高阻、回复没有冲突；同时开启相机与 Wi-Fi，反复读取全部舵机状态，记录校验错误和超时。MuJoCo 机械仿真不能验证这些电气时序。
