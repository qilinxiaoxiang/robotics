
> RAW LOOKUP OUTPUT: candidate papers only. Every claim used in the synthesis was
> rechecked against the linked paper, proceedings page, or official project page.

================================================================================
Query 1: Find primary research papers and official project reports from 2024 through August 2026 that best establish the current state of robot learning: imitation learning, reinforcement learning, vision-language-action policies, robot data scaling, world models, long-horizon planning and recovery, evaluation, and human-in-the-loop learning. Focus on what is demonstrated versus still disputed. Prefer original papers, conference proceedings, official project pages, and benchmark documentation; include direct URLs and publication dates.
Timestamp: 2026-08-28 18:52:33
Backend: perplexity | Model: perplexity/sonar-pro-search
================================================================================
Robot learning from 2024–Aug 2026 is dominated by large-scale **vision–language–action (VLA) policies**, increasingly capable long‑horizon manipulation, and emerging **world‑model–based evaluation benchmarks**, with systematic work beginning to clarify what actually works versus what fails. Across imitation and reinforcement learning, the clearest progress is in data scaling, benchmarked evaluation, and hybrid planning‑learning systems; truly general, reliable long‑horizon control remains an open challenge.

Below I organize influential, recent work by theme, prioritize top venues, and emphasize demonstrated capabilities versus unresolved issues. Citation counts are approximate and based on venue impact and early adoption.

---

## 1. Vision–Language–Action (VLA) Policies and Generalist Robots

### 1.1 What matters in VLA models for generalist robots (Nature Machine Intelligence, 2026)

- **Citation & venue:**
  Black, K. et al. **“What matters in building vision–language–action models for generalist robots.”** *Nature Machine Intelligence*, 2026. DOI: 10.1038/s42256-025-01168-7.[8]
  Tier‑1 Nature family; likely to become 100+ citations within 1–2 years.

- **Key findings:** The article synthesizes evidence from π₀ and related systems to identify **critical design choices** in VLA models for robotics: data diversity and quality, action representation, and training objectives are more important than sheer model size.[8]
- **Demonstrated:**
  - π₀, a VLA “flow” model, attains strong performance on long‑horizon, multi‑step manipulation tasks and outperforms prior open VLA baselines on **LongBench** and other benchmarks.[8][22]
  - Clear improvements over earlier VLM‑conditioned control in robustness and success rate across tasks like waste sorting, rope threading, and drawer pulling (success rates >80% on LongBench tasks).[22]
- **Limitations/controversies:**
  - Despite strong performance, π₀ and similar systems still struggle with **ambiguous, context‑dependent tasks**, and reliability across unseen environments remains open.[22]
  - The paper is more **design‑oriented** than a single benchmark study, so it guides best practices rather than proving full generality.

### 1.2 Benchmarking VLA policies: VLABench & empirical evaluation

- **VLABench (ICCV 2025, top‑tier vision conference)**
  Zhang, X. et al. **“VLABench: A Large-Scale Benchmark for Language-Conditioned Robotics Manipulation with Long-Horizon Tasks.”** *ICCV 2025*. PDF available via CVF Open Access.[16]
  - Venue tier: top‑tier conference (ICCV, h‑index 300+).
  - Defines **100 language-conditioned manipulation tasks** tailored to foundation models, spanning skills, common sense, and long‑horizon planning.[16]
  - Demonstrates that current VLA models show good **short‑horizon skill execution** but often fail at complex multi‑step reasoning and transfer of common‑sense world knowledge.[16]

- **Empirical evaluation of VLA models for manipulation (arXiv, 2024)**
  Anonymous authors. **“Towards Testing and Evaluating Vision-Language-Action Models for Robotic Manipulation: An Empirical Study.”** arXiv:2409.12894, 2024.[1]
  - Provides an **automated testing platform** and systematic stress‑tests of multiple VLA policies on diverse scenarios.[1]
  - Shows repeated failure modes: sensitivity to visual distribution shifts, over‑reliance on language priors, and brittleness in long‑horizon tasks.[1]

- **Demonstrated vs disputed:**
  - Demonstrated: VLA models can **execute diverse short‑horizon skills**, ground natural language commands, and transfer some pre‑trained knowledge to manipulation.[1][16]
  - Disputed: Whether current VLA policies qualify as **“generalist robots”**; evidence suggests persistent brittleness, poor calibration, and limited systematic reasoning.[16][22]

---

## 2. Long‑Horizon Planning, Hybrid Learning–Planning, and Recovery

### 2.1 LongBench: real‑world long‑horizon manipulation benchmark (2026)

- **Citation & venue:**
  LongBench authors. **“LongBench: Evaluating Robotic Manipulation Policies on Real-World Long-Horizon Tasks.”** arXiv:2604.16788, 2026.[22]
  Likely accepted in a major robotics/ML venue; early but high‑impact benchmark.

- **Key contributions:**
  - Introduces **LongBench**, >1,000 real robot episodes across **context‑independent** and **context‑dependent** regimes, capturing real‑world dynamics, partial observability, and mechanism awareness.[22]
  - Evaluates π₀, OpenVLA, SmolVLA and other methods; π₀ achieves ~86% average success across tasks, while others trail significantly (e.g., OpenVLA ~33%).[22]
- **Demonstrated:**
  - Clear evidence that **carefully designed VLA policies + data scaling + robust training** yield substantial real‑world gains in long‑horizon tasks.[22]
  - LongBench reveals systematic weaknesses (e.g., dynamic grasping and context‑dependent tasks) across different policy architectures.

### 2.2 SPIRE: Synergistic Planning, Imitation, and RL (2024)

- **Citation & venue:**
  Zhou, Z. et al. **“SPIRE: Synergistic Planning, Imitation, and Reinforcement Learning for Long-Horizon Manipulation.”** arXiv:2410.18065, 2024.[11]
  Authors from leading institutions (Garg, Fox, Garrett, Mandlekar are established robotics/ML researchers), suggesting eventual placement in RSS/ICRA/NeurIPS.

- **Methodology:**
  - Uses **Task and Motion Planning (TAMP)** to decompose long‑horizon tasks into learning‑friendly subtasks.[11]
  - Combines **imitation learning** (from few human demonstrations) with **reinforcement learning** to maximize data efficiency and performance.[11]
- **Key results:**
  - Outperforms prior integrated imitation+RL+planning baselines by **35–50%** in average task performance.[11]
  - Achieves **6× reduction** in human demonstrations needed, and **2× faster** learning to achieve proficient manipulation.[11]
- **Implications:** Demonstrates that **hybrid planning + learning** is currently one of the most reliable routes to robust long‑horizon behavior, especially for complex multi‑object tasks.

### 2.3 RoboCerebra and other long‑horizon benchmarks

- **RoboCerebra (NeurIPS 2025, Datasets & Benchmarks)**
  RoboCerebra authors. **“RoboCerebra: A Large-scale Benchmark for Long-horizon Robotic Manipulation and System-2 Reasoning.”** *NeurIPS 2025 D&B track*.[9]
  - Provides multi‑step, dynamic environment tasks designed to probe **System‑2 type reasoning** (planning, causal understanding).[9]
  - Shows that many state‑of‑the‑art policies fail on complex long‑horizon tasks, indicating large room for improvement.[9]

- **Demonstrated vs gaps:**
  - Benchmarks like LongBench, VLABench, RoboCerebra jointly establish that **evaluation for long‑horizon robotics is now systematic and multi‑dimensional**.[9][16][22]
  - Still missing: standardized metrics for **recovery after failure**, safety and robustness under adversarial perturbations, and unified cross‑embodiment evaluation.

---

## 3. World Models and Robot Data Scaling

### 3.1 WorldPrediction: high‑level world modeling & procedural planning (ICML 2025)

- **Citation & venue:**
  WorldPrediction authors. **“WorldPrediction: A Benchmark for High-level World Modeling and Long-horizon Procedural Planning.”** *ICML 2025* (top‑tier ML conference).[10]

- **Key findings:**
  - Introduces a **video-based benchmark** where models must discriminate correct high‑level action sequences given initial and final world states.[10]
  - Frontier models only reach **~57% accuracy** on high‑level world modeling and **~38%** on long‑horizon procedural planning, while humans solve both tasks almost perfectly.[10]
- **Implication:** High‑capacity models still **struggle with abstract, multi‑step reasoning**, confirming that world models for planning are far from human‑level.

### 3.2 GigaWorld‑1 and WMBench (2026)

- **Citation & venue:**
  Authors. **“GigaWorld‑1: A Roadmap to Build World Models for Robot Policy Evaluation.”** arXiv/ML archive, 2026.[12]

- **Contributions:**
  - Defines **WMBench**, built from real‑robot teleoperation data and matched policy rollouts across diverse manipulation tasks.[12]
  - Systematically compares world model families, action encodings, rollout horizons, and metrics for evaluating robot policies in simulation.[12]
- **Key insights:**
  - **Long‑horizon, action-faithful rollout consistency** matters more than short‑term visual realism for reliable policy evaluation.[12]
  - Pretraining benefits depend on balancing **general world knowledge** with **robot‑specific controllability**, and architectural choices in memory and action encoding critically affect alignment with real behavior.[12]
- **Demonstrated vs disputed:**
  - Demonstrated: world models can serve as **effective evaluators** and simulators when tuned for long‑horizon consistency.[12]
  - Disputed: extent to which such world models can fully replace real‑robot evaluation for safety‑critical deployment.

### 3.3 World models survey and large‑scale robot datasets (2026)

- **World models for robotic manipulation: survey (2026)**
  Authors. **“World Models for Robotic Manipulation: A Survey.”** arXiv:2606.00113, 2026.[21]
  - Catalogues major datasets such as **DROID (76k real trajectories)**, **FastUMI‑100K**, **AgiBot World (>1M trajectories)**, **Galaxea Open‑World**, and **Humanoid Everyday**.[21]
  - Shows that modern robot learning increasingly relies on **hundreds of thousands to millions of trajectories**, across simulated and real embodiments.[21]
- **Implication:** Data scaling to **foundation‑model scale** is no longer experimental; multiple projects now demonstrate that such scales are feasible and necessary for robust generalist policies.

---

## 4. Human‑in‑the‑Loop and Imitation + RL

### 4.1 Human-in-the-loop and teleoperation data

- Large‑scale teleoperation datasets like **FastUMI‑100K** and **AgiBot World** embody **human‑in‑the‑loop learning**, providing high‑quality demonstrations for imitation, VLA pretraining, and RL fine‑tuning.[21]
- Many recent generalist robot projects (e.g., Galaxea, RoboVerse, Humanoid Everyday) explicitly rely on **human teleoperation and feedback** as a key data source, indicating broad consensus that human‑in‑the‑loop data improves robustness and task diversity.[21]

### 4.2 Hybrid imitation + RL beyond SPIRE

- **Learning adaptive dexterous grasping from single demonstrations (2025)**
  Authors. **“Learning Adaptive Dexterous Grasping from Single Demonstrations.”** arXiv:2503.20208, 2025.[5]
  - Proposes **AdaDexGrasp**, learning a library of dexterous grasping skills from single human demonstration per skill, then refining via RL with trajectory-following rewards.[5]
  - Demonstrates sample‑efficient adaptation guided by vision‑language models.[5]
- **Implication:** Reinforcement learning is increasingly used as a **fine‑tuning layer** on top of imitation and VLM/VLA priors, rather than trained from scratch.

---

## 5. Evaluation, Metrics, and LLM‑based Embodied AI

### 5.1 ROS framework for LLMs in embodied AI (Nature Machine Intelligence, 2026)

- **Citation & venue:**
  Authors. **“A robot operating system framework for using large language models in embodied AI.”** *Nature Machine Intelligence*, 2026. DOI: 10.1038/s42256-026-01186-z.[20]

- **Key contributions:**
  - Proposes an **ROS-based integration framework** for LLMs with robot control stacks, standardizing interfaces for planning, perception, and dialogue.[20]
  - Demonstrates practical pipelines where LLMs orchestrate tasks but do not directly control low‑level actions, highlighting best practices for safety and modularity.[20]
- **Implications:** Confirms a shift toward **LLM-as-planner / orchestrator**, with low‑level control handled by learned or classical controllers, and emphasizes the need for robust evaluation of language‑conditioned behavior.

### 5.2 VLA surveys and taxonomies

- **Vision–Language–Action in Robotics: A Survey of Datasets, Models, and Evaluation (2026)**
  Authors. **“Vision-Language-Action in Robotics: A Survey of Datasets, Models, and Evaluation.”** arXiv:2604.23001, 2026.[17]
  - Provides a structured taxonomy of VLA datasets and evaluation protocols.[17]
  - Identifies persistent gaps: long‑horizon reasoning, compositional generalization, and standardized failure/recovery metrics.[17]

---

## 6. Overall State and Research Gaps (2024–Aug 2026)

**What is clearly demonstrated (consensus):**

- **Data scale and diversity** (hundreds of thousands to millions of trajectories) are crucial for robust generalist manipulation and VLA policies.[8][21]
- Carefully designed **VLA architectures** (π₀ and similar) plus strong datasets and training pipelines can achieve **high success rates on long‑horizon real‑world benchmarks**, surpassing earlier baselines substantially.[8][22]
- **Hybrid planning + imitation + RL** (e.g., SPIRE) substantially improves data efficiency and long‑horizon task success, particularly in multi‑step manipulation.[11]
- **World models** are becoming practical tools for **policy evaluation and simulation**, with long‑horizon consistency and action‑faithfulness recognized as key design goals.[12][21]
- Evaluation has moved from ad‑hoc tasks to structured benchmarks (VLABench, LongBench, RoboCerebra, WorldPrediction, WMBench), clarifying where current methods fail.[9][10][12][16][22]

**What remains disputed or open:**

- Whether current VLA and world‑model systems truly constitute **“generalist robots”**; benchmarks show large gaps in compositional reasoning, recovery from errors, and robust operation in open‑world settings.[10][16][22]
- The degree to which **simulator‑based evaluation** via world models can safely replace real‑robot testing, especially for safety‑critical applications.[12]
- Best practices for **human‑in‑the‑loop learning**, including optimal mixtures of teleoperation data, preference feedback, and on‑robot RL, are still evolving across projects.[21]

**Key future directions and research gaps:**

- **Robust long‑horizon reasoning and recovery:** Improving planning and error recovery in dynamic, partially observable environments, as highlighted by LongBench, RoboCerebra, and WorldPrediction.[9][10][22]
- **Standardized failure, safety, and reliability metrics:** Current benchmarks emphasize success rates, but less on safety violations, calibration, and robustness under distribution shifts.[1][16]
- **Cross‑embodiment and multi‑modal generalization:** Extending generalist policies and world models across different robot platforms (arms, mobile manipulators, humanoids) and sensor modalities (vision + touch).[7][21]
- **Tighter integration of LLM planners with VLA policies:** Frameworks like the ROS‑LLM integration point toward modular architectures; the challenge is joint training and evaluation across all levels.[17][20]

These 2024–2026 works collectively define the current frontier: **scaled VLA policies + hybrid planning/learning + world‑model‑based evaluation**, with clear benchmarks now revealing how far we still are from fully reliable, general robotic intelligence.

Additional References (2):
  [1] DOI: 10.1038/s42256-025-01168-7 - https://doi.org/10.1038/s42256-025-01168-7
  [2] DOI: 10.1038/s42256-026-01186-z - https://doi.org/10.1038/s42256-026-01186-z

Usage: {'prompt_tokens': 615, 'completion_tokens': 3753, 'total_tokens': 4368, 'cost': 0.07614, 'is_byok': False, 'prompt_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0, 'audio_tokens': 0, 'video_tokens': 0}, 'cost_details': {'upstream_inference_cost': 0.07614, 'upstream_inference_prompt_cost': 0.001845, 'upstream_inference_completions_cost': 0.074295}, 'completion_tokens_details': {'reasoning_tokens': 0, 'image_tokens': 0, 'audio_tokens': 0}}
