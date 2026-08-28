# Synthesis Research · L1 · 机器人研究兴趣发现

> Decision: 用低成本信息采样与问卷，找出最值得 Shawn 继续体验的 2–3 个机器人研究方向
> Audience: Shawn
> Date: 2026-08-28
> Confidence: high（领域覆盖）；medium（问卷只能生成兴趣假设，不能替代实际体验）
> Project link: 这是 P0–P7 的选题前置工作；目前不改变既有研究方向，除非问卷与后续体验提供连续反证

## 1. 电梯致辞

机器人研究兴趣不是一种固定“人格类型”。同一个人可能同时喜欢机器人学习的方法、医疗机器人的用途和真实部署的工作方式。最可靠的做法是先把兴趣拆成几个独立维度，用问卷产生 2–3 个候选，再让每个候选接受一次阅读、一次观察和一次小实验。**问卷负责缩小搜索空间；愿不愿意在失败后继续追，才是兴趣的证据。**

## 2. 当前领域地图：八个兴趣磁极

CMU Robotics Institute（卡内基梅隆大学机器人研究所）把研究概括为感知、思考行动、与世界交互、机器人本体四大主题，并在其完整目录中继续展开控制、学习、操作、人机交互、野外机器人、医疗机器人等大量交叉主题。IEEE Robotics and Automation Society（IEEE 机器人与自动化学会）也列出 47 个技术委员会。这说明“你属于哪一个领域”不能靠一个互斥标签回答。

本问卷把完整地图压缩成八个可操作的兴趣磁极：

| 代码 | 方向 | 它真正关心什么 | 常见研究题目 |
|---|---|---|---|
| **H** | 本体、机构与触觉 | 机器的身体怎样变得更灵巧、柔顺、耐用 | 执行器、灵巧手、触觉、软体机器人、机构设计 |
| **P** | 感知与空间智能 | 机器怎样知道自己在哪里、周围是什么、三维关系如何 | 计算机视觉、三维理解、SLAM（同时定位与建图）、状态估计 |
| **C** | 规划、动力学与控制 | 机器怎样选动作，并稳定、精确、安全地执行 | 运动规划、最优控制、接触、行走、全身控制 |
| **L** | 机器人学习 | 机器怎样从示范、数据、回报和自主经验中学会新能力 | 模仿学习、强化学习、VLA（Vision-Language-Action，视觉—语言—动作）模型、跨任务泛化 |
| **E** | 评测、数据与自我改进 | 机器怎样判断成功、诊断失败、选择数据并避免退步 | 验证器、奖励模型、失败归因、在线学习、恢复、回归测试 |
| **U** | 人机交互与辅助 | 机器怎样理解、帮助、学习自人并与人协作 | HRI（Human-Robot Interaction，人机交互）、共享控制、辅助机器人、社会机器人 |
| **D** | 野外自主与部署 | 机器人怎样在混乱环境中长期可靠、经济地运行 | 自动驾驶、无人机、矿山/农业/仓储机器人、系统集成、车队运维、安全 |
| **S** | 科学、医疗与实验室机器人 | 机器人怎样产生新的物理证据或改善健康结果 | 自主实验室、手术机器人、康复机器人、医学成像引导、实验自动化 |

组合往往比单项更像真实研究方向：`P+L` 是具身感知与世界模型，`C+L` 是学习型控制，`L+E` 是可自我改进的机器人学习，`E+D` 是可靠自主系统，`U+L` 是从人类学习与共享自主，`H+L` 是触觉灵巧操作，`S+E` 是自主实验室。

## 3. 信息源：关注时要知道它在提供哪一种证据

### 中文入口

| 来源 | 最适合用来做什么 | 使用警告 |
|---|---|---|
| [机器之心](https://www.jiqizhixin.com/) | 跟论文、模型、研究团队和技术解读 | 二手解读不能替代论文与项目页 |
| [新智元](https://aiera.com.cn/) | 发现热点、人物、融资和新发布，建立“最近大家在聊什么”的雷达 | 发布速度快、标题强；把它当线索，不当能力证明 |
| [高工机器人](https://www.gg-robot.com/) | 看中国工业机器人、零部件、供应链、落地和市场 | 行业与咨询视角强，不能代替学术证据 |
| [甲子光年](https://www.jazzyear.com/) | 看公司、商业化、访谈和中国具身智能产业叙事 | 公司案例要回到客户、产品和部署证据核验 |
| [36氪创新](https://www.36kr.com/information/innovate/) | 看融资、创业公司和产业热度 | 融资与估值不等于机器人已可靠工作 |

### 英文大众与行业媒体

| 来源 | 最适合用来做什么 |
|---|---|
| [IEEE Spectrum · Robotics](https://spectrum.ieee.org/tag/robotics) | 工程师写给大众的机器人报道；兼顾硬件、研究与真实系统 |
| [The Robot Report](https://www.therobotreport.com/) | 工业、服务机器人、软件、公司和部署动态 |
| [TechCrunch · Robotics](https://techcrunch.com/category/robotics/) | 创业公司、融资、产品和行业变化 |
| [MIT News · Robotics](https://news.mit.edu/topic/robotics) | 大学研究成果的可读入口；仍需回读论文 |
| [CMU Robotics Institute · Research](https://www.ri.cmu.edu/research-/) | 离 Shawn 最近的完整研究目录、实验室、项目与活动 |

### X 上值得先关注的人和组织

不必一次关注五十个。先用这组互相制衡的账号建立信息流：

| 视角 | 账号 | 为什么关注 |
|---|---|---|
| 通用机器人学习 | [Sergey Levine · @svlevine](https://x.com/svlevine) | 从强化学习、数据和自主经验理解机器人怎样学 |
| 通用机器人学习 | [Chelsea Finn · @chelseabfinn](https://x.com/chelseabfinn) | 模仿学习、泛化、长任务和通用策略；常附论文与演示 |
| 具身 AI 叙事与研究翻译 | [Jim Fan · @DrJimFan](https://x.com/DrJimFan) | 高频解释 NVIDIA 的具身智能、世界模型和通用智能体路线；适合激发问题 |
| CMU 机器人学习 | [Deepak Pathak · @pathak2206](https://x.com/pathak2206) | 自监督学习、泛化、世界模型和通用机器人“大脑”；同时连接本地研究生态 |
| 仿真、感知与通用智能体 | [Yuke Zhu · @yukez](https://x.com/yukez) | 机器人感知、学习、仿真和跨任务自主 |
| 触觉与灵巧操作 | [Lerrel Pinto · @LerrelPinto](https://x.com/LerrelPinto) | 触觉、灵巧操作、机器人数据与低成本开放硬件 |
| 规划与控制 | [Russ Tedrake · @RussTedrake](https://x.com/RussTedrake) | 用动力学、优化、规划和控制抵消“只要扩大模型就行”的单一路线 |
| 操作与产业现实 | [Ken Goldberg · @Ken_Goldberg](https://x.com/Ken_Goldberg) | 抓取、自动化、工业应用与机器人学习之间的桥梁 |
| 人机交互 | [Dorsa Sadigh · @DorsaSadigh](https://x.com/DorsaSadigh) | 机器人怎样从人类学习、适应人并与人协作 |
| CMU 人机交互 | [Henny Admoni · @hadmoni](https://x.com/hadmoni) | 辅助机器人、人的意图、协作与实际用户需求 |
| 本地全景 | [CMU Robotics Institute · @CMU_Robotics](https://x.com/CMU_Robotics) | 本校讲座、实验室、成果和可接近的人 |
| 论文流 | [CoRL · @corl_conf](https://x.com/corl_conf) · [RSS · @RoboticsSciSys](https://x.com/RoboticsSciSys) | 直接看到机器人学习与综合机器人研究社区在奖励什么 |
| 行业流 | [The Robot Report · @therobotreport](https://x.com/therobotreport) | 看公司、产品和真实应用，不让信息流只有论文演示 |

额外的反炒作入口是 [Rodney Brooks 的博客](https://rodneybrooks.com/)；他的 X 账号目前混有大量政治内容，若只想看机器人，直接订阅博客更干净。

## 4. Robo-Compass 24：机器人研究兴趣问卷

这不是经过心理测量学验证的人格量表，也不会给人贴终身标签。请按**真实吸引力**作答，不要按“哪个方向更前沿、薪资更高、别人更认可”作答。

### A. 吸引力评分（1–16）

每题填 `0–4`：`0 完全没感觉` · `1 略有兴趣` · `2 愿意了解` · `3 很想亲手试` · `4 即使很难也想追`

1. 我想弄清关节、执行器、机械手或材料的设计，怎样直接改变机器人的能力。
2. 在工作台前处理螺丝、线缆、传感器漂移和硬件损坏，不会很快消耗掉我的好奇心。
3. 我会被“机器人如何从相机、雷达和触觉中恢复三维世界”吸引。
4. 比起直接决定动作，我也愿意花很久处理噪声、遮挡、定位和状态估计。
5. 我会被一个让机器人稳定行走、精确接触或安全避障的漂亮控制方法吸引。
6. 即使需要动力学、优化和数学推导，我也愿意追求可解释的稳定性或约束保证。
7. 我最兴奋的画面之一，是机器人从示范、失败或自主尝试中学会新技能。
8. 比起把单一任务做到极致，我更想研究能力怎样跨物体、任务、环境或机器人迁移。
9. 我会自然追问：演示为什么有时成功、有时失败，系统到底怎样知道自己完成了任务？
10. 我愿意做基线、日志、失败分类、压力测试和回归测试，只要它们能让策略下一轮真的更好。
11. 我对“机器人怎样理解人的意图、接受纠正、建立信任并协作”有持续兴趣。
12. 我愿意观察或访谈真实用户，哪怕人的反应比机器实验更难控制。
13. 我更想看机器人走出干净实验台，在道路、仓库、农田、矿山或家庭里长期工作。
14. 可用率、人工干预、故障恢复、维护成本和现场安全，在我看来也是有意思的研究问题。
15. 我对机器人自动做生物、材料或医学实验，或直接参与诊疗与康复，很有兴趣。
16. 如果机器人本身并不炫，但能产生可靠的新科学证据或明显改善人的生活，我仍会觉得它值得研究。

### B. 强制取舍（17–24）

每题只能选 `A` 或 `B`；选你更愿意连续做三个月的那一边。

17. `A` 设计更安全、灵巧的机械手/执行器　`B` 用数据教现有机械臂学新技能
18. `A` 让机器人重建陌生环境的三维地图　`B` 让机器人理解人的意图并配合行动
19. `A` 推导带稳定性或约束的规划/控制器　`B` 把传感器、软件和硬件集成成能在现场连续运行的系统
20. `A` 做成功检测、失败分类和防退步测试　`B` 自动化一条真实的科学或临床实验流程
21. `A` 做触觉皮肤、软材料或新机构　`B` 做传感器融合、定位和 SLAM
22. `A` 保证困难接触下仍能精确运动　`B` 让一个策略适应许多物体和任务
23. `A` 为辅助机器人做用户研究和共享控制　`B` 让机器人自主选择并执行有信息量的科学实验
24. `A` 修复真实机器人车队的可用率、恢复和人工干预问题　`B` 从失败中选择下一批数据，让策略一轮轮进步

### C. 三条行为证据

- **E1**：最近半年，哪一个机器人视频、演示、课程或谈话让你主动保存、回看或继续搜索？没有也可以写“没有”。
- **E2**：如果周六有连续四小时和全部工具，你最愿意做哪种事：数学推导、写代码训练、装硬件调试、现场部署、观察/访谈用户、设计实验与指标？只能选一个并说明一句原因。
- **E3**：哪类机器人工作听起来最让你抗拒或最容易厌烦？

推荐答题格式：

```text
1= 2= 3= 4= 5= 6= 7= 8=
9= 10= 11= 12= 13= 14= 15= 16=
17A/B 18A/B 19A/B 20A/B 21A/B 22A/B 23A/B 24A/B
E1:
E2:
E3:
```

## 5. 评分与解释

基础分为对应两题之和：`H=1+2`、`P=3+4`、`C=5+6`、`L=7+8`、`E=9+10`、`U=11+12`、`D=13+14`、`S=15+16`。强制题中每次选中某方向再加 2 分：

- H：17A、21A；P：18A、21B；C：19A、22A；L：17B、22B；
- E：20A、24B；U：18B、23A；D：19B、24A；S：20B、23B。

每个方向满分 12。解释时不只看第一名：

- 第一与第二相差 `0–1`：优先解释为组合方向；
- 相差 `2–3`：有主方向，但仍需并行做两个短体验；
- 相差 `≥4`：形成较强候选，仍须经过真实任务验证；
- 所有方向都低：不是“你不适合机器人”，而可能是材料太抽象、尚未遇到具体任务，或兴趣对象其实是机器人产品/创业而非研究问题。

E1–E3 用来校正“说起来喜欢”和“愿意承受日常摩擦”的差距。最终报告应给出前三方向、组合解释、反证、三项短体验和重新判断条件，而不是只报一个字母类型。

## 6. 共识、争议与误区

| 类型 | 内容 | 依据 |
|---|---|---|
| ✅ 共识 | 机器人研究跨本体、感知、规划、控制、学习、交互和应用，多数真实课题是组合方向。 | CMU RI 研究目录；IEEE RAS 技术委员会 |
| ✅ 共识 | 新闻、公司演示和社交媒体适合发现问题，不足以证明能力或研究价值。 | 本项目 evidence ladder（证据阶梯） |
| ⚠️ 争议 | 通用学习策略能否替代显式几何、动力学、控制和模块化系统；目前没有跨任务统一赢家。 | 机器人学习与经典机器人社区持续并存 |
| ⚠️ 争议 | 人形是否会成为主导本体；这不应提前决定一个人对机器人学哪种问题感兴趣。 | 多种本体均有真实研究与部署 |
| ❌ 误区 | 喜欢看某种机器人视频，就等于喜欢该方向的研究日常。 | 演示吸引力没有覆盖调试、失败、实验设计和证据工作 |
| ❌ 误区 | 一份问卷能一次确定职业或研究方向。 | 兴趣需要在可逆体验中更新 |

## 7. 决策规则：先探索，再短期承诺

问卷完成后，只保留得分最高的三个候选。每个候选做三次低成本采样：

1. 看一位代表研究者的完整讲座或访谈；
2. 精读一个项目页/论文，并写下自己真正想追问的问题；
3. 做一个 60–120 分钟小任务，记录卡住时是想继续还是想逃开。

出现以下三种信号中的两种，才把该方向升级为一个 2–4 周的集中项目：主动继续搜索、失败后仍想回来、自然产生自己的问题或改法。如果三个候选都没有信号，就重新开放搜索，而不是把“机器人”身份硬维持下去。

**会改变当前决策的证据：** 问卷首轮高分必须与至少两次行为证据一致；若实际体验中的能量、耐烦度和问题生成持续指向另一个方向，应以行为证据覆盖问卷结果。

## Sources

- [CMU Robotics Institute Research Topics (accessed 2026-08-28)](https://www.ri.cmu.edu/research-/)
- [CMU Robotics Institute Research Overview (accessed 2026-08-28)](https://www.ri.cmu.edu/research-overview/)
- [IEEE RAS Technical Committees (accessed 2026-08-28)](https://www.ieee-ras.org/technical-committees/list-of-technical-committees/)
- [CoRL 2026](https://www.corl.org/home)
- [Robotics: Science and Systems](https://roboticsconference.org/)
- [Sergey Levine, UC Berkeley](https://people.eecs.berkeley.edu/~svlevine/)
- [Chelsea Finn, Stanford](https://profiles.stanford.edu/chelsea-finn)
- [Deepak Pathak, CMU](https://www.cs.cmu.edu/~dpathak/)
- [Yuke Zhu, UT Austin / NVIDIA](https://yukezhu.me/)
- [Jim Fan](https://jimfan.me/)
- [Russ Tedrake, MIT](https://www.csail.mit.edu/person/russ-tedrake)
- [Dorsa Sadigh](https://dorsa.fyi/)
- [Lerrel Pinto](https://www.lerrelpinto.com/)
- [Ken Goldberg, UC Berkeley](https://goldberg.berkeley.edu/)
- [Henny Admoni, CMU](https://www.ri.cmu.edu/ri-faculty/henny-admoni/)
- [机器之心](https://www.jiqizhixin.com/)
- [新智元](https://aiera.com.cn/aiera/)
- [高工机器人](https://www.gg-robot.com/about-about.html)
- [甲子光年](https://www.jazzyear.com/)
- [IEEE Spectrum Robotics](https://spectrum.ieee.org/tag/robotics)
- [The Robot Report](https://www.therobotreport.com/)
- [TechCrunch Robotics](https://techcrunch.com/category/robotics/)
