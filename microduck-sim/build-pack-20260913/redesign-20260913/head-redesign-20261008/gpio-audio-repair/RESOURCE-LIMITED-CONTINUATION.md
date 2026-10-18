# GPIO 与音频续接（P5 / P6）

本轮只整理已有结果、接插件来源和可续算代码，未启动 NumPy、Trimesh、Manifold 或任何 CAD 进程。正式发布状态不变。

## 已有证据

- 原音频候选在静止位置以及 161 个预接线整体装入位置无碰撞，但完整 229 姿态域出现新的功放、柱和螺丝碰撞，不能采用。
- 功放最严重碰撞：head_roll −15° 时对 head_yaw_link 为 126.891 mm³；head_roll −20° 时对 motor13 为 89.405 mm³。新音频壳对应两者峰值为 18.623 / 16.780 mm³。原生壳与原底壳的既存碰撞单独记录，不替新增材料免责。
- 中断前只保存到标准输出的 +X12 mm 功放候选曾通过静态筛选。它的完整关节域、柱、安装路径、预接线和工具尚未通过。不得把 `STATICCLEAR` 当成采用结论。
- 当前摄像头分支的 Pi 微移位姿已另行检查刚体母壳；这不证明线材直出。`gpio-saved-pose-departures.json` 仅按该变换生成 12 个端口、5 mm 直线及 R3 向上转弯的坐标，`collisionChecked:false`。

## 单候选检查代码

`bounded_amp_check.py` 不导入旧 `scene.py`，不建立整场景实体缓存，不缓存任何变换后的场景。它一次只保持目标、一个障碍及该障碍当前姿态。每一对几何结果写入 JSONL 并刷新到磁盘，随后原子写入 checkpoint；恢复时校验源码、几何和关节域哈希，并移除尚未提交的尾部记录。

轻量语法与帮助函数检查已执行。几何分支尚未运行，不具有验收结果。

仅由 root 获得唯一 CAD 令牌后调用现有 `H/run_bounded_cad.py`。当前执行上限为进程树 RSS 512 MiB、每次 120 秒；不采用启动器旧默认值。先做最低成本的负例筛选，不先制造柱：

```sh
python3 /Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py --max-mib 512 --seconds 120 --report /Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/gpio-audio-repair/amp12-motor13-resource.json -- /tmp/microduck-cad-venv/bin/python /Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/gpio-audio-repair/bounded_amp_check.py --placement-only --delta 12 0 0 --only-obstacle motor13 --max-pairs 80 --stop-on-hit --name amp12-motor13
```

命令使用当前工作区的绝对路径。若未检查完，原参数续跑；若出现碰撞，停止该候选并读证据。不能把改变位移后的任务写进同一个 checkpoint。

仅在功放位置本身通过后，单独 `--prepare --delta 12 0 0`。准备脚本会去掉旧柱的新增内部材料，保留原曲面，逐片合并精确局部屋顶向下的占位来限制新柱外界；不会生成一批变换场景。它另行生成新柱、新功放、新螺丝与壳候选，并保存来源哈希。准备完成不等于验收。随后用 `--target posts|screws|cap --phase static|domain` 分批逐对检查。

旧扬声器线在新功放位置不再连通，因此初步位置检查明确排除旧线并保持整机布线未完成；后续必须重做端口连接、预接线装入、约束点和关壳。不能复制旧音频线的通过结论。`integrationReady` 始终为 false，直到整个装配条件完成。

## 已购与待有的接插件

订单 101587695 的收货记录只有 **Adafruit 4397 一条**，即 4 根 28 AWG、外径 0.8 mm 的线和 4 个独立母插壳，用于 IMU 的物理针脚 1、3、5、9。厂家图给出塑料肩之间 150±10 mm；没有给出母壳自身长度。它并不提供其余 8 根 GPIO 接头，也不证明 22 AWG 电源接触件的电流能力。

原采购文档的一只 2×20 母壳、4 条 22 AWG 电源尾线和4条音频尾线均为社团供料要求，**没有库存确认**。统一壳并非已经买到的硬件。用户授权的结构修复允许改成各自绝缘的 12 个母接点，但不能把这当成 12 个已购插头。

保留已购 4397 的4个原插头是可执行的线束结构：在原线中段增加导线并分别绝缘两处接头，按成品长度验收；不必为了统一母壳丢弃原插头再假定另有4个替代品。延长导线、绝缘材料和实际完成长度仍要有现物。原要求的250 mm成品长度需由完整关节路由重新核验，不能直接说150 mm足够。

其余4个音频母接点仍需匹配2.54 mm排针的实际线端；4个电源接点仍需明确支持22 AWG、每接点至少1.5 A。不能把4397的28 AWG线或无额定散跳线替代电源接点。12个独立母壳需要连续的机械约束和清晰针位识别，不能只依靠导线拉力维持接触。

尺寸接收采用主方案18 mm PCB面至线出口；17 mm是已查同类壳14.25 mm上限加2.54 mm针座后只留0.21 mm的敏感性分支，均不是实物测量。现有独立壳只改善未使用针脚间的空隙，不会自动消除必要针脚的出线碰撞。

来源与尺寸在 `connector-dimensions.json`；原电气12条连接保持不变。没有新采购，也没有代替硬件验证。
