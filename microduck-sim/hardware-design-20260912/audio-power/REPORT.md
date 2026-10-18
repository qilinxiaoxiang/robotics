# MicroDuck 音频与供电方案核查

核验日期：2026-09-12。问题：P5（可靠、可维修的身体与供电）和 P6（部署可靠性）。这份方案给出具体器件、连接方法和验收条件；电脑上没有连接真实 MicroDuck，未声称已经完成焊接、真机声学或运动供电测试。

## 先纠正购买清单

社区自装方案遗漏了扬声器（speaker）和音频功率放大器（audio power amplifier，简称功放）。Pi Zero 2 W、OpenRB-150、BNO085 都不能凭空发出鸭叫。

三个版本必须分开：

- **官方成品 Microduck**：Pollen 官方规格明确有麦克风和扬声器；当前电子、机械设计并未完整开源。不能把成品配置当作 AI-FanGe 的自装清单。官方软件提交 `6507d2e960417aaa4ecd38eccf59b2dcf586ecd2` 中，`deploy/audio/aic3104-init.sh` 配置 TLV320AIC3104 音频编解码器（audio codec），第 13 行说明扬声器功放连接其模拟线路输出；`robotd/src/sound.rs` 选择声音文件并交给 Linux 的 `aplay` 播放。具体功放与喇叭料号未由这份代码确定。[官方规格](https://pollen-robotics.com/microduck/press-kit/)、[官方声音实现](https://github.com/pollen-robotics/microduck/blob/6507d2e960417aaa4ecd38eccf59b2dcf586ecd2/robotd/src/sound.rs)、[音频电路初始化](https://github.com/pollen-robotics/microduck/blob/6507d2e960417aaa4ecd38eccf59b2dcf586ecd2/deploy/audio/aic3104-init.sh)
- **AI-FanGe 自装版**：最新 README 的零件表没有扬声器或功放；对 `microduck/src` 的 Python 文件搜索未发现音频播放实现。缺少完整的发声硬件与软件集成。
- **我们的浏览器仿真**：`microduck-simulator/app/src/game/game.js:1431` 的 `playChirp()` 创建浏览器 `Audio` 对象播放 `.wav` 文件；声音由运行浏览器的电脑音频设备发出。它不证明真机已经装有喇叭。

## 选定的声音硬件

采用 **Adafruit #3006 MAX98357A 单声道 I²S 功放板 + Adafruit #3923 8Ω、1W 椭圆喇叭**。Adafruit 是提供开源电子模块与接线教程的美国厂商。MAX98357A 把数字音频转成可推动喇叭振膜的电信号；这不是供舵机使用的 OpenRB。

- 功放板：官网标记外形 19.4×17.8×3mm，1.2g。2024 年后版本预焊了接线端子，3mm 不能当作含端子的完整装配高度；设计先留 **22×21×12mm** 的占位，焊线和端子需继续留通道。该占位是设计余量，不是原厂包络认证。
- 喇叭：30×20×5mm，3g；2025 年后引线缩短到约 30mm，必要时加延长线。支架可先留 **31×21×6mm** 腔体，固定外框，不能挤压振膜；朝外开出声孔。
- 两件标价共 $7.90，未含运费、税、线与固定件，未购买。[功放](https://www.adafruit.com/product/3006)、[喇叭](https://www.adafruit.com/product/3923)

连接五根线，GPIO 编号与实体针脚位置不要混用：

- 功放 VIN → 独立电子设备 5V 电源。
- 功放 GND → 共地。
- DIN（音频数据输入）→ Pi GPIO21，实体针脚 40。
- BCLK（位时钟）→ Pi GPIO18，实体针脚 12。
- LRCLK（左右声道时钟）→ Pi GPIO19，实体针脚 35。
- 喇叭两根线分别接功放的两个扬声器输出端；**两根都不能接 GND**，因为这是桥接输出（bridge-tied output）。[厂商接线教程](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/raspberry-pi-wiring)

I²S（Inter-IC Sound，芯片间数字音频）与 BNO085 的 I²C（Inter-Integrated Circuit，芯片间通信总线）是两种不同接口。BNO085 使用 GPIO2/3（实体针脚 3/5），所以不与音频冲突；相机接 CSI、OpenRB 接 USB，均不占这三根音频引脚。

软件准备：在 Pi OS 的 `/boot/firmware/config.txt`（旧系统为 `/boot/config.txt`）启用 `dtoverlay=max98357a`，按 Adafruit 的安装流程设置 ALSA（Advanced Linux Sound Architecture，Linux 音频系统）和软件音量，重启后用 `aplay -l` 确认音频设备，再播放 WAV。先使用衰减的短声音，从低音量开始。功放在 5V 下能向 8Ω 输出超过 1W，故不能把这只 1W 喇叭长期满音量使用；验收时把有效输出功率限制在喇叭额定内。播放需异步执行，不能让播放函数阻塞 50Hz 关节循环。[安装方法](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/raspberry-pi-usage)

验收：同一动作连续叫 20 次没有漏播；播放期间视频正常、本地循环继续；无喇叭碰振膜、功放过热或电源跌落。以上尚需真机测量。

## 原电源方案的三个实际问题

1. 视频商品图的电池为 6.4V、1800mAh、0–3A，19×37×66mm。6.4V 标称已经超出 XL330 的最高工作电压 6.0V，不能直接接。采用该包的既有结构设计，仅代表机械尺寸候选；不应继续把它作为整机电源首选。
2. **OpenRB-150 的官方 DYNAMIXEL 端口供电规格为总计 3000mA。**USB 入口限制为 500mA；新板的 5V 引脚上限仅 150mA。它不能当作 15 个大负载舵机的任意电流分配板，也不能从那个 5V 针脚给 Pi 供电。[OpenRB 官方规格](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/)
3. 单个 XL330 在 5V 时堵转电流为 1.47A；15 个算术总和为 **22.05A**。这不是正常步行电流，也不要求按此连续运行；它说明不能靠“电池有 3A”就保证机器人跌倒、关节受阻或同时启动时不断电。[舵机官方规格](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/)

源码还存在需修正的部署参数：`constants.py:56` 的电机模型电压为 7.5V；`:65` 总电流阈值为 15A；`observer.py:54` 默认不读取实际电流，只使用模型估计。这些不能保护一个只有 3A 额定值的板内供电路径。模型用电压不等于真实允许输入电压，但会影响保护估计，必须按新 5V 方案检查。这里未修改这些运行文件。

## 具体电源器件与布线

推荐机械占位与后续装配基准：

- **电池：Gens ace GEA8502S60E2**，850mAh、2S（两节串联）、7.4V 标称 LiPo（lithium-polymer，锂聚合物）、60C 标签、EC2 放电插头。官方尺寸 58×32×20mm，但规格同时给出 ±5/±2/±2mm，因此托架按最大 **63×34×22mm** 再加软垫和打印间隙；线缆和插头另留出口。标称重 57g（网页容差 ±20g）。60C 是厂家标签，850mAh×60=51A 仅为标签换算，不作为已验证 51A 输出能力。它比 0–3A 包更适合作为高放电候选。需要支持普通 2S LiPo 的平衡充电器（balance charger）与匹配充电线；不能使用 LiFePO4 充电模式。[已打开的厂家页](https://www.genstattu.com/gens-ace-850mah-2s-60c-7-4v-lipo-battery-ec2-plug-car-classic-non-g-tech/)
- **舵机稳压：Pololu D24V150F5**，固定 5V、标称典型 15A；43.2×31.8×11mm，M2 四角孔中心距 38.862×25.4mm。真实持续输出随输入电压、通风和散热变化，15A 不是封闭塑料壳内保证值；不能宣称可持续承担全部 22.05A 堵转负载。[厂商规格](https://www.pololu.com/product/2881)
- **电子设备稳压：Pololu S13V30F5**，固定 5V、典型约 3A；22.9×22.9×9.7mm。独立供给 Pi、相机与功放，避免舵机电源直接承担电子设备压降预算。它的输出能力也需按真实温升检查。[厂商规格](https://www.pololu.com/product/4082)

布线原则明确到连接路径：

1. 电池 EC2 → 匹配插头及带保险的电源线 → 总电源开关 → 分为两个稳压器输入。电池裸电压不接 Pi、功放或 XL330。
2. 电子设备 5V → Pi 的 PWR IN 供电口；功放从同一电子设备电源分支取电。Pi 的 USB 数据口接 OpenRB，OpenRB 的逻辑电源由该连接提供。BNO085 按其模块标识接 Pi 3.3V。
3. 舵机 5V → 独立电源分配线束（power distribution harness）→ 舵机 VDD。OpenRB 通往舵机的线束仅保留 DATA 与 GND，**VDD 引脚不连接**，避免把大电流倒灌进 OpenRB。所有设备共地；两个稳压器的 5V 输出彼此不相连。
4. 不能让 15 个舵机的所有电流都流过第一个小插头。动力线需要分段注入，短分支每组至多两个 XL330；DATA/GND 仍可贯通。对应 JST 插头、线规、焊点与保险必须按分支额定选择。普通杜邦跳线和无焊面包板不作为总动力线路。
5. 保留可以直接切断舵机稳压器输入或 EN 的物理急停。保险保护导线，软件电流监测保护动作；二者不能互相替代。保险额定不能从电池 60C 标签推导，应按实际线束、插头额定和测得运动峰值定值。

这是完整的连接拓扑与具体主要器件选择；**线束、保险和急停器件的型号/几何尚未定稿，不能把整个清单称作免调试的成套采购包。**之所以明确这一项，是因为否则仍会把未解决的高电流接线问题藏在“加一个电源模块”里。

## 能改变方案的真机证据

先在有电流限制的台式电源上验证：5V 空载正确、电子设备与动力电源没有被错误并联、OpenRB 不承载舵机动力电流。接一个舵机检查通信，再逐步增加。

正式放地前，使用机械支撑检查启停、抬腿和轻微外力扰动，测 **每个供电分支的峰值、舵机端最低电压、Pi 端最低电压和稳压器温升**。软件 50Hz 读数捕不到很短的电流尖峰，不能代替外部电源测量。再进行相机串流和叫声同时工作的重复步行测试。

如果这些测量超出具体稳压器、线材或插头的额定值，就调整供电分支或选更高能力器件；如果 5V 改变了步态表现，还需重新标定控制/电机模型。不能为保持原教程表现把电压升回超额定范围。

## 可继续落地的线束与停机附件

已进一步查到具体器件，供完成整机配电设计使用，尚未作为经测量验收的最终保险值：

- 电池匹配连接线：Gens ace `GEAX6F2E2M`（XT60 female 到 EC2 male）。厂商标重 21g±5g，作为充电/桌面连接可直接匹配；若追求轻量机身，直接制作 EC2 对接线更合适，不能把长适配器的全部体积塞进电池外形里。[厂家页面](https://www.genstattu.com/gens-ace-xt60-female-to-ec2-male-adapter/)
- 保险座：Littelfuse `0FHM0003ZXJB`，MINI 插片保险座，自带 16 AWG 导线，座额定 20A。先用 `0297010.L` 10A MINI 保险做有支撑的受限试机；10A 是保守起测选择，需核对真实输入峰值与各段额定，不能靠反复换更大保险解决动作电流过大。[保险座原厂资料](https://www.littelfuse.com/assetdocs/mini-fhm-datasheet?assetguid=339fa35e-eabc-45c5-9093-8abceaa8a2cf)、[原厂保险资料](https://www.littelfuse.com/assetdocs/automotive-passenger-car-catalog?assetguid=455de39d-b1d0-41f5-bcdc-c08d0451fa9c)
- 软件以外的舵机停机：Pololu `#1408` SPDT（单刀双掷）小滑动开关只连接 **舵机稳压器 EN 与 GND**，让 EN 在停止位置拉低；另一个档位悬空，由稳压器内部上拉恢复。此开关仅通过微小控制电流，绝不串进舵机总电源。它是硬件运行/停止控制，不能称为具有安全认证的急停。彻底断电仍拔掉可触及的电池连接器。[小开关](https://www.pololu.com/product/1408)、[稳压器 EN 定义](https://www.pololu.com/product/2881)
- 动力总线采用短粗双线、焊接分支与热缩绝缘；分支使用 ROBOTIS 标准 Robot Cable-X3P/JST EH 接头。先按每两只一组布置供电输入，组与组之间断开 VDD，只保持 DATA 和 GND 连通。具体线长由装配体里的走线确定；不得让多余线圈干扰腿或头部关节。

未选择 Pololu 标称“16A”的小 MOSFET 电源开关作为无条件替代：其原厂注释是在 12V、允许器件温度到 150°C 时的值，55°C 温升边界仅 6A；把标题里的数字直接当作塑料机壳内持续能力会重演原清单问题。
