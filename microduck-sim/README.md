# MicroDuck 本地仿真环境

Read [PROJECT-CONTEXT.json](PROJECT-CONTEXT.json) before hardware, training or scope work. It defines the visual-pickup goal, links the completed training and distinguishes component bring-up from project completion. The procurement entry runs the same goal check.

这台 MacBook 已经可以直接运行官方 MicroDuck Sandbox。它在浏览器中用 MuJoCo 做物理仿真，并以 50 Hz 运行官方训练好的 ONNX 策略。

## 直接玩

双击 [`Play-MicroDuck.command`](Play-MicroDuck.command)。脚本会启动本地服务并打开：

<http://127.0.0.1:5173/?boot=1>

第一次启动如果尚未安装网页依赖，脚本会自动安装。退出时回到启动脚本所在的终端，按 `Control-C`。

## 键盘控制

- `W / S` 或上下方向键：前进、后退
- `A / D` 或左右方向键：左转、右转
- `Q / E`：左脚、右脚踢球
- `R`：坐下；再按一次站起；轮滑模式下是蹲伏滑行
- `G`：低头做 GroundPick（贴地拾取）动作
- `B`：叫一声；按住时保持张嘴
- `V`：按住持续发出 Wheee 声，同时张嘴
- `X`：翻滚
- `M`：双腿与轮滑模式切换
- `C`：切换跟随相机
- `Space`：重置
- 鼠标拖动：旋转视角；滚轮：缩放

左下角也可以直接切换颜色和 `FEET / ROLLERS` 模式。

## 本机能做什么

- 已可运行：官方浏览器沙盒、真实策略推理、MuJoCo 物理、GroundPick、踢球、坐立和轮滑模式。
- 已保存：完整的 `microduck_rl` 训练源码、机器人模型、任务配置和策略导出代码。
- 新增本地训练案例：已在 M1 Pro 的 CPU 上完成嘴部 PPO 训练，同条件测试由训练前 0/12 提升到 12/12。双击 [`Play-Jaw-RL.command`](microduck-simulator/Play-Jaw-RL.command)查看；范围与证据见[结果说明](microduck-simulator/rl/RESULTS.md)。
- 当前硬件边界：官方整机训练器依赖 NVIDIA CUDA 显卡，不能直接在这台 M1 Pro 上运行；上面的嘴部案例使用独立的本地 CPU 训练入口，不受这个限制。
- 有 CUDA 机器时，先跑官方最小冒烟训练：

  ```bash
  cd microduck_rl
  uv run train Mjlab-Velocity-Flat-MicroDuck \
    --env.scene.num-envs 64 \
    --agent.max_iterations 5
  ```

  这只验证环境、观测、奖励和导出链路能否正常工作。通过后再增加并行环境数量和训练轮数。

官方也支持 Hugging Face Jobs 云端 GPU。提交会使用账户令牌并可能产生费用，所以当前只保留代码，没有发起云端任务。

## 用 Modal 训练

这台电脑已有可用的 Modal 凭据。Modal Starter 当前每月包含 30 美元计算额度；本月已用额度为 0 美元。仓库中的 [`modal_train.py`](modal_train.py)使用一张 L4 GPU，并把训练日志和 checkpoint（训练检查点）持久化到 `microduck-rl-output` Volume（云端持久化目录）。

第一次只跑 64 个并行环境、5 轮 PPO 冒烟训练：

```bash
cd /Users/xiangzheng/code/robotics/microduck-sim
uvx modal run modal_train.py
```

脚本在训练前会检查 `nvidia-smi` 和 PyTorch CUDA；任一步失败都会停止，不会进入长训练。单次运行最长限制为 3 小时，只启动一个远程训练调用，Weights & Biases（实验记录平台）保持离线模式。

训练产物保存在 Modal Volume 中。下载到当前目录：

```bash
uvx modal volume get microduck-rl-output / modal-output
```

当前只完成本地入口和静态验收，尚未启动 Modal 容器或消耗额度。

## 环境边界

本地网页资源和策略已经下载到电脑，但 MuJoCo WebAssembly 和 ONNX Runtime Web 会在启动时从 jsDelivr 加载，因此仍需联网。多人幽灵使用公共中继；中继连接警告不会影响单人仿真。

## 当前快照与验收

- 浏览器沙盒：`pollen-robotics/microduck-simulator`，commit `1261013e7e28ba2a6878bd76ae573751c0e4b457`
- 强化学习环境：`pollen-robotics/microduck_rl`，commit `5946fd9cdbc58956424420153e51975af3b30d77`
- 本机：macOS 26.6.2、Apple M1 Pro、Node.js 20.19.6
- 已通过：Git LFS 资源校验、`npm ci`、生产构建、浏览器加载、50 Hz 控制循环、GroundPick 和轮滑模式切换
