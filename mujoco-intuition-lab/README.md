# MuJoCo Intuition Lab

第一天的目标不是背接口，而是亲手确认一条因果链：

`模型参数 -> 物理状态 -> 控制输入 -> 仿真步进 -> 接触结果 -> 任务反馈`

## 最简单的入口：20 分钟 Notebook

```bash
conda activate mujoco-lab
cd mujoco-intuition-lab
jupyter lab notebooks/01_mujoco_20min_intuition.ipynb
```

浏览器打开后，右上角内核选择 `Python (MuJoCo Lab)`，然后从上到下逐格运行。它只讲一个单关节机械臂，先看动画，再看曲线，最后用滑块改变初始角度、目标角度和阻尼。

MuJoCo 官方也提供[可直接在 Google Colab 运行的完整教程](https://colab.research.google.com/github/google-deepmind/mujoco/blob/main/python/tutorial.ipynb)。官方教程更全；这份本地 Notebook 更适合第一次接触。

## 已安装环境

```bash
conda activate mujoco-lab
cd mujoco-intuition-lab
```

如果要在另一台机器重建：

```bash
conda env create -f environment.yml
```

## 完整自动实验（看完 Notebook 再用）

```bash
python day1_intuition.py
```

结果写到 `artifacts/`：

- `arm_control.png`：同一条机械臂在自由摆动和闭环控制下的角度变化。
- `ball_contact.png`：球落地时高度和法向接触力的变化。
- `arm_pd.mp4`：比例-微分反馈加重力补偿，把关节拉到目标角度。
- `ball_drop.mp4`：接触发生前后的运动。
- `reacher_random.mp4`：机器人学习任务里随机策略的观察—动作—奖励循环。
- `day1_summary.json`：可被后续实验读取的结构化结果。

## 再用鼠标摆弄

打开带控制滑块的官方查看器：

```bash
python -m mujoco.viewer --mjcf=models/one_joint_arm.xml
```

在右侧控制面板拖动 `shoulder_motor`，观察重力、阻尼和电机力矩怎样共同决定关节运动。再打开落球模型，开启接触点和接触力显示：

```bash
python -m mujoco.viewer --mjcf=models/ball_drop.xml
```

要看一个持续运行的闭环控制器，并能用鼠标施加扰动：

```bash
mjpython interactive_pd.py
```

## 验证

```bash
pytest -q
ruff check .
```

这里刻意不使用 `mujoco-py`。当前官方包名是 `mujoco`；Gymnasium 的 MuJoCo `v5` 环境是当前推荐版本。
