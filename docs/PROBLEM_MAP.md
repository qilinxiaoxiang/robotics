# Problem map: the critical path to compounding physical intelligence

The field is often organized by products—humanoid, robot arm, self-driving car. This project instead organizes it by the failure points in a self-improving loop.

## Priority map

| ID | Problem | Why it is fundamental | Representative efforts | Our position |
|---|---|---|---|---|
| **P0** | Grounded goals and verifiers | A system cannot improve if it cannot tell progress, success, harm, or uncertainty | LeRobot reward models; Gemini success detection; scientific lab verifiers | Highest-leverage entry point; a wrong verifier produces confident self-corruption |
| **P1** | Action-grounded data engine | Internet video shows what happened, but often not the actions, forces, state, and failed attempts needed to learn control | AgiBot World; DROID/OXE; Robot Park; GR00T data; teleoperation | Data quality means causal action alignment and informative failures, not just more hours |
| **P2** | Predictive world models | Robots need to compare possible futures before risking real actions | World Labs; AMI; 1XWM; NVIDIA Cosmos; FieldAI | Evaluate by decision utility and calibration, never by video realism alone |
| **P3** | Generalization across tasks and bodies | A new policy per task and robot cannot scale to the physical world's combinatorics | Skild Brain; GR00T; Gemini Robotics; GO models | Cross-embodiment transfer is a central bet, but specialization may still win at high reliability |
| **P4** | Long-horizon autonomy, memory, and recovery | Small errors compound over minutes; useful work requires detecting drift, replanning, and recovering | Gemini agentic stack; Figure Helix; Physical Intelligence RECAP; AgiBot GO | Recovery rate and intervention burden matter more than a single uninterrupted hero run |
| **P5** | Dexterous, durable, economical bodies | Intelligence cannot act through weak hands, short batteries, unsafe joints, or unserviceable hardware | Boston Dynamics; Unitree; 1X; Apptronik; Tesla; AgiBot | Hardware is not commoditized; hands, actuators, energy, safety, and manufacturing remain frontier constraints |
| **P6** | Safe deployment and fleet operations | A policy that works in a lab can fail under latency, wear, people, workflow changes, or integration errors | Boston Dynamics Orbit; Agility Arc; Intrinsic; FieldAI; Tesla evaluation infrastructure | Reliability, observability, rollback, and unit economics are part of the intelligence system |
| **P7** | Autonomous experiment and problem selection | Solving science requires turning broad goals into discriminating experiments and trustworthy physical evidence | Lila; Opentrons; Emerald Cloud Lab | This is the end-state application and the next autonomy boundary, not a reason to skip P0–P6 |

## Issue 1 — What is the gradient?

In language and code, correctness can often be checked cheaply. Physical tasks have partial observability, delayed outcomes, ambiguous progress, safety constraints, and multiple acceptable solutions. The verifier therefore needs to combine task semantics, sensor evidence, uncertainty, and human escalation.

**Consensus:** task success and progress detection are missing pieces in the learning loop.
**Dispute:** whether a general vision-language model is sufficient, or task-specific sensors and formal constraints remain necessary.
**Our bet:** use a layered verifier—general learned judgment plus task invariants and safety rules—and measure calibration under perturbations.

## Issue 2 — Where should data come from?

Real robot data is grounded but expensive. Simulation is scalable but biased. Human video is abundant but lacks robot actions. Teleoperation supplies actions but reflects operator and interface artifacts. Autonomous rollouts contain the policy's real failures but can be dangerous and low quality.

**Our bet:** no single source wins. The useful unit is a trace with provenance: source, body, controller, task, sensors, action space, intervention, outcome, and failure label.

## Issue 3 — What makes a world model useful?

A world model may represent 3D geometry, predict future frames, learn latent state transitions, or estimate a distribution over possible outcomes. These are not interchangeable.

**Our bet:** for robotics, the decisive test is counterfactual value: given candidate action chunks, does the model rank safer or more successful futures better than a simpler baseline, and does that ranking stay calibrated in the real world?

## Issue 4 — One brain or many specialists?

Cross-body training may force a model to learn deeper physical regularities and unlock more data. Yet different bodies expose different observations, action spaces, dynamics, and safety limits. A universal representation may still require specialized controllers and adapters.

**Our bet:** share representations, task semantics, and failure knowledge; keep low-level embodiment adapters and safety controllers explicit until evidence supports deeper unification.

## Issue 5 — Why do long tasks fail?

Long-horizon failure is rarely one problem. Perception drift, irreversible actions, timing errors, hidden state, gripper slip, poor success detection, and planning mistakes compound. Average task success hides where the chain breaks.

**Our bet:** evaluate subtask progress, time-to-failure, recovery rate, human interventions, and irreversible-error rate—not only final success.

## Issue 6 — Is the humanoid form necessary?

Humanoids can reuse human spaces, tools, demonstrations, and social expectations. They also inherit difficult balance, energy, cost, and safety constraints. Wheels, fixed arms, and specialized lab automation often deliver value sooner.

**Our bet:** treat humanoids as a high-upside embodiment hypothesis. Keep the learning loop hardware-agnostic so evidence, not identity, selects the body.

## Issue 7 — What counts as real deployment?

A staged demo proves that a team can make one trajectory work. Deployment proves that a system survives repeated tasks, operators, maintenance, environmental changes, and economic scrutiny.

**Our bet:** track autonomy hours, intervention rate, availability, recovery, safety incidents, maintenance burden, throughput, and cost per successful task. Do not convert “announced pilot” into “scaled deployment.”

## Issue 8 — Can robots accelerate science itself?

Autonomous labs have structured instruments, explicit protocols, and rich measurements, making them a promising early domain for closed-loop physical AI. The hard part moves upstream to hypothesis generation, experiment selection, causal interpretation, and scientific validity.

**Our bet:** laboratory robotics is not a side branch. It is a high-information proving ground for the full thesis: AI proposes, acts through instruments, receives novel physical evidence, and updates what it believes.

## Strongest objections

1. **“World models are unnecessary; scale vision-language-action data.”** Then a world model must earn its place by improving action selection, safety, or data efficiency against a no-world-model baseline.
2. **“Evaluation infrastructure is support work, not frontier work.”** A dashboard is support work. A calibrated verifier that discovers failures, chooses corrective experience, and measurably improves a policy is part of the learning algorithm.
3. **“Simulation will remove the need for real robots.”** Simulation can multiply experience, but the real world remains the acceptance surface. Every major claim must eventually survive a physical perturbation.
4. **“General robots are economically irrational; specialized automation wins.”** That may be true for many tasks. The project measures transfer and total adaptation cost rather than assuming generality is always superior.
