# Company landscape: who is closing which part of the loop?

> **As of:** 2026-08-04
> **Scope:** Organizations that materially advance world models, general robot intelligence, capable bodies, deployment loops, open infrastructure, or autonomous science.
> **Caution:** A company announcement is evidence of direction, not independent proof of capability.

## 1. World models and general robot intelligence

| Organization | Problem being attacked | Current evidence | Project judgment |
|---|---|---|---|
| [World Labs](https://www.worldlabs.ai/blog) | Persistent, interactive 3D worlds and spatial intelligence; in July 2026 it added SceniX to push simulation toward robotics | Research previews and a commercial spatial-generation direction | Essential to watch for simulation and spatial representations; robotics value still depends on action grounding and transfer, not generated-world quality alone |
| [AMI Labs](https://amilabs.xyz/) | General world models that learn real-world structure beyond next-token language modeling | Official 2026 launch; Yann LeCun chairs and Saining Xie is co-founder/CSO | Frontier architecture bet. Important intellectually, but still earlier than robot companies on public action/deployment evidence |
| [Google DeepMind](https://deepmind.google/models/gemini-robotics/) | Dual-model stack: embodied reasoning plus vision-language-action control across tasks and bodies | Gemini Robotics models, developer API for ER 1.6, and partnerships with Apptronik and Boston Dynamics | One of the strongest bridges from frontier multimodal models to real robots |
| [Physical Intelligence](https://www.physicalintelligence.company/download/pistar06.pdf) | Generalist vision-language-action policies that improve from deployment data, rewards, and human corrections | π*0.6 / RECAP reports real-home and industrial tasks, with lower failures on evaluated tasks | Closest public match to this repository's self-improvement thesis |
| [Skild AI](https://www.skild.ai/blogs/building-the-general-purpose-robotic-brain) | One “omni-bodied” policy across robot morphologies, trained with simulation, internet video, and targeted real data | Cross-body demonstrations and 2026 industrial partnerships | Important test of whether body diversity creates more general physical intelligence |
| [FieldAI](https://www.fieldai.com/) | Risk-aware world models and hardware-agnostic autonomy in unknown, changing industrial environments | Named deployments and Boston Dynamics partnership | Important counterweight to clean-tabletop robotics: uncertainty, safety, and field reliability are first-class |
| [1X](https://www.1x.tech/discover/world-model-self-learning) | Video-pretrained world models used directly as policies for home humanoids, followed by deployment data and reinforcement learning | Public world-model work, NEO product program, and 2026 World Model Lab | High-value vertical experiment spanning world model, hands, home deployment, and data flywheel |

## 2. Open platforms, data, simulation, and evaluation

| Organization | Problem being attacked | Current evidence | Project judgment |
|---|---|---|---|
| [NVIDIA](https://developer.nvidia.com/blog/develop-humanoid-robot-policies-end-to-end-with-nvidia-isaac-gr00t/) | An end-to-end physical-AI stack: simulation, teleoperation, data, open GR00T models, evaluation, ROS deployment, and edge compute | Open GR00T 1.7 weights/code, Isaac stack, LeRobot format integration, and broad partner adoption | The most useful open industrial substrate for this project; strategically important for the stack, not merely for GPUs |
| [Hugging Face / LeRobot](https://huggingface.co/blog/lerobot-release-v060) | Open models, datasets, hardware adapters, rollout tools, reward models, and unified evaluation | v0.6.0 explicitly connects imagination, success detection, failure collection, and improvement | Best open entry point for a reproducible failure-to-learning loop |
| [Intrinsic](https://www.intrinsic.ai/blog) | Make AI-enabled industrial robot applications easier to build, integrate, simulate, deploy, and operate | Flowstate, robot/vision integrations, and 2026 manufacturing partnerships | Important because physical AI fails commercially when integration and operations remain artisanal |

## 3. Bodies, manufacturing, and real deployment

| Organization | Problem being attacked | Current evidence | Project judgment |
|---|---|---|---|
| [Boston Dynamics](https://bostondynamics.com/blog/boston-dynamics-unveils-new-atlas-robot-to-revolutionize-industry/) | Enterprise-grade mobility, manipulation, safety, serviceability, and fleet operation | Production Atlas announced; 2026 fleets committed to Hyundai and Google DeepMind; long Spot/Stretch deployment history | **Still highly competitive.** Its advantage is decades of body/control reliability plus an industrial owner; its open question is how quickly foundation-model intelligence becomes reliable work |
| [Tesla Optimus](https://www.tesla.com/AI) | Vertically integrated vision, planning, inference hardware, manufacturing, evaluation, and a mass-producible humanoid | Official AI stack and factory/production plans; public demonstrations | Must watch because fleet data and manufacturing can compound, but keep planned scale separate from independently verified autonomous work |
| [Figure](https://www.figure.ai/news/helix-02) | End-to-end, full-body neural control for long-horizon humanoid tasks | Helix 02 public four-minute kitchen demonstration | Important architecture and integration bet; repeated deployment reliability remains the decisive evidence gate |
| [Apptronik](https://apptronik.com/news-collection/welcome-to-robot-park-where-apptroniks-apollo-goes-to-work) | Human-safe, manufacturable humanoids plus a distributed real-world data factory | Apollo 2 fleets, Robot Park, customer sites, and Google DeepMind data partnership | Strong body–data–model partnership; especially relevant to learning-loop design |
| [Agility Robotics](https://www.agilityrobotics.com/content/digits-next-steps) | Useful bipedal work in warehouses with navigation, safety, charging, and fleet integration | Digit's full-time GXO deployment and continued production refinement | Valuable reality check: narrow work that runs daily is more informative than broad capability demos |
| [Unitree](https://www.unitree.com/about/) | Lower-cost, high-performance quadruped/humanoid bodies plus increasingly capable embodied models | Broad hardware availability, G1/H-series ecosystem, 2026 model and factory testing announcements | One of the most accessible bridges from research to capable hardware; verify autonomy separately from staged motion |
| [AgiBot / 智元](https://www.agibot.com/research/) | Full-stack bodies, large real/sim datasets, generalist policies, and fleet learning | AGIBOT World, GO-series models, Genie Studio, and commercial product line | A core Chinese player because data, model, body, and deployment are designed as one flywheel |

## 4. Autonomous science: the thesis in its strongest form

| Organization | Problem being attacked | Current evidence | Project judgment |
|---|---|---|---|
| [Lila Sciences](https://www.lila.ai/tech) | AI generates hypotheses, designs and runs physical experiments, and learns from results across science | Integrated reasoning models, AI Science Factories, and named programs in biology/materials | The clearest company-level realization of the project's end-state thesis |
| [Opentrons](https://opentrons.com/archives/news/opentrons-accelerates-the-enablement-of-ai-based-laboratory-robotics-with-nvidia) | Standardized, open, API-driven laboratory execution and closed-loop experimental data | Large deployed lab-robot network and NVIDIA physical-AI integration | A practical execution layer for autonomous biology and chemistry, with a much lower hardware entry barrier than humanoids |
| [Emerald Cloud Lab](https://www.emeraldcloudlab.com/) | Turn a broad physical laboratory into a remotely programmable, reproducible computing surface | 24/7 cloud lab with hundreds of instrument types and unified software control | Shows that “robot as API to atoms” can arrive through structured laboratories before general humanoids |

## Important alliances and fault lines

- **World model ↔ simulator:** World Labs + SceniX, NVIDIA Cosmos + Isaac, and 1X's learned simulator all attack the question of generating useful experience without paying full real-world cost.
- **Brain ↔ body:** Google DeepMind partners with Apptronik and Boston Dynamics; NVIDIA supplies a cross-company substrate; Skild deliberately avoids owning one body.
- **Vertical integration ↔ open ecosystem:** Tesla, Figure, 1X, and AgiBot optimize a closed body–data–model loop. NVIDIA and LeRobot try to make components interchangeable.
- **Humanoid ↔ task-shaped machines:** Humanoids maximize compatibility with human environments. Field robots, industrial arms, and lab workcells can reach reliability and economic value sooner.
- **Demo capability ↔ deployment reliability:** Figure and Tesla push broad end-to-end capability; Agility and Boston Dynamics emphasize daily operations, serviceability, safety, and fleet integration. The winner may need both cultures.

## Watchlist, not yet a core dependency

Sanctuary AI, UBTECH, Fourier Intelligence, Dyna Robotics, Toyota Research Institute, Covariant/Amazon, Generalist AI, and emerging Chinese embodied-AI teams remain relevant. They enter the core roster when a new public artifact changes the problem map, not simply because they raise money or publish a polished demo.
