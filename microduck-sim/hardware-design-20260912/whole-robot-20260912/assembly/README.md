# MicroDuck 当前打印件的整机装配与紧凑电源安装

验证日期：2026-09-12。推进 P5：让感知、供电和实体安装进入可复核的机器人实验。

当前社区 3MF（3D 打印工程文件）里的 `a.obj` 与当前 `microduck_rl` 的 `power_support` 是同一几何体。已恢复它在整鸭中的位置，并做出替换原电池支架的一体打印件。电池留在原电池区；大稳压器在电池下方，小稳压器在两台髋关节舵机之间。此前 69 mm 外伸背包已被本方案取代。

- [整鸭装配图](compact-battery/whole-robot-compact-zero-pose.png)：黄色电池、绿色结构、蓝色大稳压器、红色小稳压器；灰色为保留部件。
- [安装区放大图](compact-battery/compact-battery-regulators-detail.png)与[可旋转装配模型](compact-battery/whole-robot-compact-zero-pose.glb)。
- [当前打印件到机器人刚体的坐标变换](body-transforms.json)、[部件质量和惯量](compact-battery/component-body-masses.json)。

## 几何来源与纠正

采用当前 `microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml` 与原始 STL 网格。该文件记录了 Onshape 装配来源。社区教程仓库自带的旧 URDF/MJCF 与恢复的历史 CAD 不对应这套当前打印件。

- `6.obj` → `top_head_shell`：双向最大表面误差 0.00369 mm。
- `a.obj`（object 12）→ `power_support`：双向最大表面误差 0.00335 mm。
- `h.obj`（object 24）→ 头内 `motor_support`。
- `7.obj/8.obj` → `left_shell/right_shell`；`fgb.obj/gbgb.obj` → 左右大腿，不能当作胸壳使用。
- `p.obj/q.obj` 是嘴部软零件的尺寸候选；没有将它们未经验证的变换用于本次支架设计。

匹配比较了 24 种保持左右手性的轴方向，先对齐再计算双向到三角面距离。完整结果在 [verified-rigid-matches.json](verified-rigid-matches.json)。`a.obj` 的躯干坐标为 `X = 原X−22.5；Y = −原Z；Z = 原Y−2.322742`，单位 mm。原件的正 X 面朝向躯干内部，原先局部背包方向因此不适用于整机。

## 实际打印件与安装

- [power-support-integrated-print.stl](compact-battery/power-support-integrated-print.stl)：替换原 `a.obj`，包含电池上下挡边、绑带通道、大稳压器通风底座、小稳压器支架。水密、单实体。
- [small-regulator-cover-body.stl](compact-battery/small-regulator-cover-body.stl)：小稳压器压盖。平放使薄板背面接触打印床。
- [参数化托架 STEP](compact-battery/compact-tray.step)与[压盖 STEP](compact-battery/small-regulator-cover.step)用于继续改尺寸。STEP 中的新增托架须和原支架网格合并；应打印上面的完整替换 STL。

打印材料与切片采用 RoboClub 教程中的 PLA、0.4 mm 喷嘴、0.20 mm 层高作为起点；一体支架应使用 `power-support-integrated-body.stl` 的躯干 Z 方向向上，平移 Z +57.5 mm 使稳压器底板落床，并启用树状支撑。压盖绕 X 轴旋转 90°，使 1.2 mm 厚度朝打印床法向。实际 Bambu 切片记录由整机交付包另存。本文件不把导出 STL 当作打印完成。

安装顺序由机械遮挡决定：小稳压器及飞线先装进中间支架，再装相邻舵机。电池由后方滑入上下挡边之间，两条 4.8 mm、长度至少 200 mm 的尼龙扎带经过原来的四个槽固定；模型将四槽向后贯通，清除原来挡住扎带的局部肋条。扎带扣放在后侧，电池靠挡边、角部导向和绑带承力。可在接触面加入薄软垫保护电池外皮。

大稳压器采用四个 M2 孔，孔距 X 38.862 mm × Y 25.4 mm；底板、2 mm 隔柱、PCB 合计厚度与 M2×8 螺丝和螺母配合。电池底板和元件最高处留 5 mm 空气层。小稳压器不用猜 PCB 孔距，装在有通风开口的盒内，压盖四个 M2×12 螺丝拧入 1.6 mm 塑料导孔。两块 Pololu 均按直接焊接飞线安装，额外排针或螺丝端子不在本次包络中。

原 NP 电池底部卡扣在躯干 Z < −38 mm 的部分被移除，原电机配合面和螺丝孔保留。新支架后端为 X −59.1 mm，相对原电池后端 −46.83 mm 多 12.27 mm；底端为 Z −57.5 mm，相对原支架低 13.43 mm。支架宽度仍为 54.50 mm。支架净增材料约 10.335 g，压盖约 0.609 g，合计净增约 10.944 g，均按实心 PLA 1.24 g/cm³估算，切片耗材量和实物称重优先。

## 验证结论与运动范围

[静态及关节极限检查](compact-battery/verification.json)保留了全部碰撞记录。新增零件相互之间、与其电池/电路板包络，以及零姿态下其余原件之间没有新增相交。原支架本身和 `banana_pcb_locker` 的 14.6247 mm³、与左壳的 0.0292 mm³相交在修改前已存在。

[原模型成功行走轨迹检查](compact-battery/gait-mesh-check-baseline-5v-walking-video.json)：12 秒轨迹每三帧取样，共 200 个实际姿态、72,000 对网格检查，新增结构、电池、两稳压器和绑带与全部运动部件的相交为 0。此检查使用 MuJoCo 的实际关节状态与刚体变换，而非凭图片判断。

[新质量原型轨迹检查](compact-battery/gait-mesh-check-compact-prototype.json)：15 秒轨迹共 250 个采样姿态、90,000 对网格检查，相交为 0。对应动力学参数、是否摔倒及速度由 `../dynamics/compact-prototype.json` 保存。

[最高载重代表轨迹](compact-battery/gait-mesh-check-compact-old0-head45-battery77.json)通过 500 个姿态、180,000 对网格检查，相交 0。30 秒外力推动代表轨迹也通过 500 个姿态、180,000 对网格检查，见[推动扰动检查](compact-battery/gait-mesh-check-compact-perturb-old60-push.json)。40 ms 传感延迟的失败轨迹在 4.16–4.40 秒出现 6 条电池或绑带与左小腿相交记录，动力学在 4.40 秒判定摔倒，见[失败证据](compact-battery/gait-mesh-check-compact-perturb-old0-sensor40.json)。这说明当前方案对失稳时的剧烈内收运动仍有限制。

另对 XML 中每个关节的完整范围各取 17 点，共 238 个姿态，发现 35 条部件相交记录：腿大幅向内拧、向内倾时会碰底座，头极度俯折时会碰中间支架。该检查单独改变一个关节，其他关节为零，没有同时求解闭链（closed-loop linkage，多个连杆构成封闭回路）的约束，因此它是极限干涉筛查，不能代表这些组合都可实际到达。原 NP 电池在同一极限筛查中已有 8 条腿部相交记录，见[基线对照](compact-battery/sweep-baseline-and-alternatives.json)。正常行走的已采样轨迹通过，不能将所有关节开到极限也描述为通过。

模型验证覆盖刚体装配与已采样动作。电池软包形变、扎带扣和线束的实际走线、螺丝强度、打印层间强度、稳压器散热及供电负载需要实体试装与测量；它们不由网格相交计算证明。

## 复现

`build_compact_battery.py` 是参数化源码，原 `a.obj` 网格副本在 `compact-battery/source-frame-12.npz`。从本目录运行：

```sh
python build_compact_battery.py
python export_component_masses.py
python verify_compact.py
python verify_gait_meshes.py ../dynamics/compact-prototype.json
python render_compact.py
```

环境：Python 3.11、CadQuery 2.8、trimesh、manifold3d、NumPy、SciPy、rtree、Matplotlib、MuJoCo 3.13。FK 辅助脚本从同一仓库当前官方模型读取装配，输出变换单位始终是 mm；质量文件单独使用 m/kg。
