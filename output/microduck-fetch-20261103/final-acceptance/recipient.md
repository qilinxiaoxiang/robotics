# 独立收件人验收 v4

结论：启动通过；任务说明可理解；协议执行验收需要修复 R1。

## 隔离执行证据

- 干净副本：`/var/folders/qc/v7_v9gkn7xb_3rpvz7h0n8ph0000gn/T/microduck-recipient-v4-neabdgkk/fetch-package`。排除 .venv/out/archive/.git/缓存；未编辑候选。
- 新建 Python 3.12 虚拟环境，严格按 starter/requirements.txt 安装固定版本成功；pip check 无冲突。
- check_all 六项全部通过：interaction、interaction_sources、vision、gaze、motion、composed。
- 另跑实际事件输出命令和默认 rehearse，均通过。所有打印/模型/输入从收件人副本读取；只用作者环境定位 Python；没有机器人、网络服务或付费计算。
- 单次安装从公开 wheel 来源下载/缓存；启动之后离线。

## 阻塞 R1：过期目标遇到干扰人物帧时不停止

- P1；属于可执行协议承诺错误，非安装失败，也非未来训练能力缺口。
- 独立序列：call t=0 → request .1 → settled .2 → 球 t=.3/capture=.28 → 干扰 person-B t=2/capture=1.98。
- 实际：仍为 approaching，最后输出 ignore_other_identity，继续保留此前 follow_target；没有新 controlled_stop。所选球已旧 1.72 秒，超过 .25 秒。
- 原因：coordinator.handle 对所有 track 跳过超时检查；错 ID 分支不检查先前选中 track 的年龄。
- 预期：停止接近并进入 seeking_ball；返程原人过期同理。回归需加入这种组合情况，而不只单独 tick 或单独错人。
- 证据：recipient.counterexample.json。

## 收件人对每项工作的复述

### A

目的：把呼唤、取球请求和取消绑定到原始呼唤者。
改动：单一音频源分流给唤醒/转写，再接已有解析器；逐步接入真实身份线索。
第一步：从 starter/interaction 运行 python3 run.py；再运行 python3 run.py --events call_then_fetch。
输出：共享音频适配器、带来源的录音/转写标签、JSON 事件和分项错误计数。
验收：既定正负例无错误启动，取消匹配原始用户；两个消费者收到相同块/时间；真实身份不得用 fixtures 冒充。
依赖：解析器可独立开始；真实 caller binding 依赖 B，动作/cancel 依赖 E/身体执行器。

### B

目的：出程盯住所选球，返程重认原始呼唤者，向 C 请求视线和速度。
改动：在现有橙色检测上加稳定目标选择/跟踪、人物重认、年龄和丢失处理；保留错例。
第一步：在已装依赖环境中从 starter/vision 运行 python run.py --out out，查看图片、tracks 和已知橙色矩形误检。
输出：回放命令、视频叠加、带 identity/capture_t 的轨迹和 gaze/velocity 请求。
验收：冻结正负片段后报告 recall/误选/ID 切换/旧指令时长；错人、身份不明、过期时停止接近。
依赖：图像/协议独立；身体映射需要 F0/C，取球入口依赖 D，人物身份依赖 A，阶段选择依赖 E。

### C

目的：边看地面边走/转/停，随后接 D 的负载状态运输。
改动：先重现低头抖动，再比较一个腿部参考约束改动；不靠拒走或不低头获得平滑。
第一步：从 starter/motion 运行 python replay.py locomotion --out out/gait.json。
输出：历史失败诊断、双条件评估代码/配置、一个明确比较、支持的视线/速度/负载范围及模型适配说明。
验收：当前增量复现真实 trace 指标；F0 后改善预先选择的故障指标同时保留视线/速度跟踪和稳定停步，经过受保护实机试验才接 B/D。
依赖：CPU 诊断独立；新机体训练和实机依赖 F0；加载步行依赖 D 的实际负载出口。

### D

目的：从真实接近状态连续取球、起身并交付可运输的稳定负载出口。
改动：把任务延长到含球起身/下游准入，保留姿态/速度/动作/视觉历史，增加有效 lift/hold/exit 判定和退出路径。
第一步：从 starter/motion 运行 python replay.py pickup --out out/handoff.json，查看弯颈差异和 pick→stand 后跌倒时间线。
输出：连续过渡评估、单变量训练比较、入口/出口区域、负载证据、失败与 abort。
验收：F0 后由 B/C 实际出口起步，无 reset 完成离地、保留、起身、C 搬运/停步；空咬、跌落和跌倒分开计数。
依赖：历史诊断独立；新训练依赖 F0；开发可用共享 baseline，不先等新 C；最终要 B/C 连续入口、C 出口联合验收。

### E

目的：把 A/B/C/D 连成一项任务，返回原人、等待取走，掌握 authority 和失败恢复。
改动：把具名意图接既有单一电机执行器，逐个用验证后的真实 readback 替换 fixtures，保留任务 epoch 和独占身体控制。
第一步：从 starter/ 运行 python3 rehearse.py；读 out/rehearsal.json 和 coordinator.py。
输出：观察模式适配器、完整 transition 日志、authority/readback 测试、不能恢复旧任务的 restart。
验收：保留 18 个回归，再加真实 producer replay；旧指令/错人/过期图像/咬合取消都正确，实机不中断串完整链及失败分支。
依赖：无电机协议可以独立；真实 settled/entry/hold/exit/wait/take 依赖对应生产任务与 F0。

## 范围裁决

F0、新音频/身份、人物数据、完整训练环境、真实 readback 与实机连续验收都明确列为后续输入或实现任务，不能当作此次收件人启动失败。当前包足够独立运行 parser/图像/真实模型 CPU 诊断/协议检查，任务角色与上下游关系有明确说明。但完整协议停止承诺被 R1 反例推翻，不能只以 18/18 现有案例通过宣称该边界已验收。

输入哈希在 recipient.inputs.json 和 recipient.json；完整结果在 recipient.outputs/；所有独立 stdout 为 recipient.*.stdout.txt。
