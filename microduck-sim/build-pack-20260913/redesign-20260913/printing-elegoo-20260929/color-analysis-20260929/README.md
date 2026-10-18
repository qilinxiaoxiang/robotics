# 原始配色与当前打印盘对照

来源为我们的社区模型原件，仓库提交 `49678215d0b40529522772a40c06c216390449dd`。未套用新版商业 Microduck 外观。原件 3MF 的盘名、耗材色值以及当前模型摆盘逐实例读取；未修改打印文件。

## 原始分组

- 原盘1：黄色的鸭嘴和脚部分，4 个实例。
- 原盘2：白色的外壳，5 个实例。
- 原盘3：灰色的结构件，19 个实例。
- 原盘4：结构件 舵机转盘 轴承，34 个实例。
- 原盘5：浅黄色的眼镜和脚掌，3 个实例。

黄色鸭嘴组的实际预设色值为 `#C85406`，浅黄色眼镜组为 `#FF9929`；盘名和色值分别记录，不能当作同一个精确色号。原始动画显示白色头顶/大腿罩、灰色脸板、橙棕色嘴部和脚踝、浅金色眼圈及浅色脚掌。

## 当前各盘

### 当前盘1（10 个实例）

- Current replacement/add-on: no exact original item color：3 个。
- 白色的外壳：2 个。
- 黄色的鸭嘴和脚部分：2 个。
- 灰色的结构件：2 个。
- 结构件 舵机转盘 轴承：1 个。

零件：power-support-integrated-print.stl、head-cap-usb-service-print.stl、community-72.stl、community-74.stl、imu_clamp_holder_print.stl、community-66.stl、community-64.stl、community-14.stl、community-16.stl、community-59.stl。

### 当前盘2（7 个实例）

- 黄色的鸭嘴和脚部分：2 个。
- 白色的外壳：2 个。
- 灰色的结构件：2 个。
- 结构件 舵机转盘 轴承：1 个。

零件：community-2.stl、community-4.stl、community-8.stl、community-10.stl、community-60.stl、community-18.stl、community-82.stl。

### 当前盘3（13 个实例）

- Current replacement/add-on: no exact original item color：3 个。
- 原灰色耗材（ID55，原件对象存在但未列入原盘实例）：2 个。
- 浅黄色的眼镜和脚掌：2 个。
- 灰色的结构件：4 个。
- 结构件 舵机转盘 轴承：2 个。

零件：motor-support-coaxial-print.stl、community-46.stl、community-44.stl、fuse-bank-print.stl、community-70.stl、community-28.stl、community-38.stl、community-36.stl、audio_carrier_print.stl、community-55.stl、community-55.stl、community-84.stl、community-86.stl。

### 当前盘4（13 个实例）

- 灰色的结构件：6 个。
- Current replacement/add-on: no exact original item color：2 个。
- 结构件 舵机转盘 轴承：5 个。

零件：community-76.stl、community-42.stl、community-40.stl、regulator-open-insert-print.stl、community-22.stl、camera_cradle.stl、community-32.stl、community-30.stl、community-50.stl、community-62.stl、community-80.stl、community-59.stl、community-59.stl。

### 当前盘5（18 个实例）

- 结构件 舵机转盘 轴承：11 个。
- 浅黄色的眼镜和脚掌：1 个。
- 灰色的结构件：3 个。
- Current replacement/add-on: no exact original item color：3 个。

零件：community-51.stl、community-48.stl、community-26.stl、camera_pitch_foot.stl、community-34.stl、community-20.stl、imu_rear_cover_print.stl、small-regulator-cover-print.stl、community-94.stl、community-95.stl、community-96.stl、community-97.stl、community-98.stl、community-93.stl、community-100.stl、community-101.stl、community-102.stl、community-59.stl。

### 当前盘6（28 个实例）

- 结构件 舵机转盘 轴承：22 个。
- 原灰色耗材（ID55/56，原件对象存在但未列入原盘实例）：6 个。

零件：community-103.stl、community-53.stl、community-87.stl、community-88.stl、community-89.stl、community-90.stl、community-91.stl、community-99.stl、community-92.stl、community-55.stl、community-55.stl、community-83.stl、community-55.stl、community-55.stl、community-85.stl、community-81.stl、community-79.stl、community-77.stl、community-57.stl、community-56.stl、community-55.stl、community-68.stl、community-59.stl、community-59.stl、community-59.stl、community-59.stl、community-59.stl、community-78.stl。

## 关键部位

- ID2：bottom_head_shell: lower head shell and fixed upper-beak region; source yellow-beak group
- ID4：jaw: moving lower jaw frame; source yellow-beak group
- ID40：soft_mouth_top: upper contact pad; source gray group
- ID42：jaw_soft: lower contact pad; source gray group
- ID48：noenoeil: circular eye outer ring; source pale-yellow group; current plate5 already black
- ID76：face_part: front face panel around eye; source gray group; current plate4
- ID8,10：left_shell/right_shell: torso side covers, both visual geoms directly under trunk_base (robot_allcollisions.xml89–106); source white group; current plate2

## 已打印颜色对原貌的影响

盘1已橙色：白色头顶与大腿罩变橙色，脚踝保持暖色；盘5已黑色：眼圈由浅金色变黑色。盘4的脸板若为白色/浅灰色，可与黑眼圈形成清楚对比。盘2黄色会同时把原白色躯干侧盖、灰色结构件改成黄色，这是整盘单色的明确取舍。

完整逐实例映射见 [JSON](original-current-colors.json)。

原件视觉证据：
- [real-robot.gif](/Users/xiangzheng/code/robotics/microduck-sim/Microduck-build-tutorial/docs/assets/real-robot.gif)
- [cad-exploded.gif](/Users/xiangzheng/code/robotics/microduck-sim/Microduck-build-tutorial/docs/assets/cad-exploded.gif)
