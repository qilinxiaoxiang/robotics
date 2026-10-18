> 当前整机使用此目录的 `camera_pitch_foot.stl` 与 `camera_cradle.stl`，安装方向、底座螺丝与新头壳接口以 [最终头部说明](../whole-robot-20260912/electrical/head-layout/README.md) 为准。下文保留单件设计记录，不覆盖最终装配定义。

# Camera Module 3 Wide 可调俯仰安装支架

这套支架包含两个可打印实体：相机后托架（camera cradle）和俯仰脚座（pitch foot）。相机用四颗 M2 螺丝固定；脚座用两个 M3 孔与机器人头壳的匹配垫块连接。铰链允许先实际看画面，再调整向下看的角度并锁紧，避免在没有头壳装配方向证据时猜测。

已生成 STEP、STL、带相机参考占位的装配 STEP，并完成几何验证。相机本体、排线、金属螺丝和头壳匹配垫块不属于这里的两个打印零件。

## 文件

- `camera_cradle.stl`：相机后托架，30×41×9mm，带四根隔柱和背面 M2 六角螺母窝。
- `camera_pitch_foot.stl`：脚座，30×16×16mm；其中底板厚度 3mm，其余高度来自铰链耳。
- 同名 `.step`：可在 CAD 软件继续编辑的实体文件。
- `camera_mount_assembly.step`：装配参考。名称以 `PRINT_` 开头的两件才打印；`REFERENCE_` 是相机与排线的尺寸占位，不能拿去打印。
- `camera_mount_assembly.png` 和 `camera_mount_print_parts.png`：装配外观及打印摆放示意。
- `interface.json`：头壳匹配接口、光轴和安装坐标。
- `verification.json`：闭合网格、实体数量、体积、与相机占位及脚座的碰撞检查。
- `build_camera_mount.py`：CadQuery 参数化源文件；关键尺寸在 `PARAMS`，改相机孔位/隔柱间隙后必须重新运行验证并核对螺丝长度。

## 固定接口

脚座底面为局部 Z=0，X 为相机左右方向，零俯仰时光轴朝局部 -Y。两个 M3 通孔中心为 **(-11,0,0)** 和 **(+11,0,0)**，孔径 3.4mm，孔距 22mm。

俯仰轴沿 X，经过 (0,0,11)。相机 PCB 底边高度为 Z=20.5mm；零俯仰时镜头前端中心为 (0,-12.12,34.9)mm。原头壳需要匹配这两个孔或以贴合垫块/内部背板夹持，不能从这份独立支架推断原头壳已经有现成安装孔。

## 紧固件与装配

- 相机：M2×8mm 盘头或圆柱头螺丝 4 颗，标准 M2 六角螺母 4 颗。螺母对边约 4mm、高约 1.6mm；打印窝对边 4.1mm、深 1.65mm。使用螺母锁紧，不能将螺丝硬拧进相机 PCB。
- 俯仰轴：M3×20mm 螺丝 1 颗、M3 垫圈 2 片、M3 六角螺母 1 颗。先让相机轻松转动，定角度后夹紧。脚座双耳间隙 8.5mm，托架中间耳宽 8mm。
- 脚座到头壳：M3 圆头螺丝 2 颗、M3 垫圈 2 片与螺母；螺丝长度由头壳垫块和内部背板的总厚度决定。脚座顶部对直径 7mm 垫圈/圆头螺丝留了直径 7.4mm、高 3.2mm 的避让。

装配顺序：先把四个 M2 螺母压入托架背面窝；把 15→22 针排线插入相机背部插座并锁好；将 PCB 四孔放在四根隔柱上，用 M2×8 固定；把托架中间耳放进脚座双耳，用 M3×20 作转轴；最后把脚座固定到匹配头壳垫块。不要压镜头或弯相机板来补偿孔位不合。

四个相机孔中心按官方图核读为 (2,2)、(23,2)、(2,14.5)、(23,14.5)mm，孔距 21×12.5mm。后方隔柱净高 4.8mm，覆盖官方图中约 2.75mm 的背部连接器高度；上边保持开放，排线可以从上方离开。正面没有遮挡框，所有打印实体均留在相机镜头后方。

## 打印与验证边界

两件 STL 已按各自平底放在 Z=0。后托架背面朝下，隔柱朝上；脚座底板朝下，双耳朝上。铰链横孔做成带尖顶的圆孔，以降低孔顶悬空；螺母窝仍有短距离桥接，切片后要看这些位置是否连续。打印摆放图仅是几何示意，不能代替 Bambu Studio 的切片结果。

建议先用标准 0.4mm 喷嘴、0.2mm 层高检查切片，四层外墙；材料与温度遵循 RoboClub 批准的打印机/材料配置。两件按完全实心 PETG 密度 1.27g/cm³ 计算共约 5.8g，这不是打印机给出的实际耗材重量。

计算检查已通过：两件均为单个实体、网格闭合、三角面方向一致；相机 PCB、镜头、背面连接器和排线占位与后托架交集为 0；托架在 -45° 至 +45°、每 5° 一档的 19 个姿态与脚座交集为 0。这是支架内部的离散几何检查，未覆盖整只鸭子的头颈、嘴、线缆弯曲或动态受力。

实物验收仍需确认 M2 螺母能平放入窝、螺丝不顶到相机器件、排线不夹住、俯仰锁紧后不滑动。最终固定相机后还需做相机标定（camera calibration）；支架角度变化会改变相机相对地面的关系。

## 可复现生成

本机已安装环境：`/tmp/microduck-cad-venv/bin/python`，其中有 CadQuery 2.8、trimesh、numpy 与 matplotlib；无需密钥或在线服务。运行：

```sh
/tmp/microduck-cad-venv/bin/python /Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/camera/build_camera_mount.py
/tmp/microduck-cad-venv/bin/python /Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/camera/render_camera_mount.py
```

成功信号：命令退出码 0；两件 STL/STEP 与装配 STEP 更新；`verification.json` 两件 `watertight=true`、`connected_bodies=1`，所有交集检查为 0。

几何来源：相邻 `reference/camera-wide.pdf` 官方尺寸图，2026-09-12 已渲染逐项核读。这里的相机模型是用于检查空间的近似占位，不是原厂完整电子元件 CAD。
