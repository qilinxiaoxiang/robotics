# Literature note: RL walking on low-friction ground, friction DR ranges, fine-tuning and slip-tolerant gaits

Date: 2026-10-15. Scope: published recipes relevant to the MicroDuck slip failure (14-DoF, ~0.8 kg, XL330, PLA sole on cork board, estimated sim-equivalent friction 0.15 to 0.2; community `walk61` policy trained with foot friction in [0.7, 1.3]). Read-only literature pass; no training was run.

Evidence levels used below: **[quote]** = text or number read from the primary source; **[secondary]** = taken from a search-engine summary of a source whose full text was not opened; **[inference]** = this note's reasoning, not a published claim.

---

## 1. Friction domain-randomization ranges in published recipes, and whether they reach below 0.3

Headline: the common quadruped/humanoid defaults bottom out at 0.4 to 0.5 and do not cover 0.15 to 0.2. The recipes that *were* demonstrated at or near our regime either train down to 0.05 to 0.1 or add explicit friction awareness. Our current (0.7, 1.3) is the narrowest of every recipe found, by a factor of about 4 against the measured floor.

Primary/reference ranges (sorted by lower bound):

- **RMA (Kumar et al. 2021, A1 quadruped)**: Friction training range **[0.05, 4.5]**, testing range **[0.04, 6.0]** [quote, Table I]. https://arxiv.org/html/2107.04034v1
- **RL-augmented adaptive MPC (Kamohara et al. 2025, biped, IsaacLab sim only)**: slippery sub-terrains where μ is "either a high value of 0.5 or a value sampled from a low range", "the friction range decreases monotonically with the row index", minimum **0.05** at the hardest row [quote]. Success at μ = 0.05 about 74 % vs about 5 % for baseline MPC [quote]. No hardware test. https://arxiv.org/html/2509.18466
- **Humanoid-Gym (Gu et al. 2024, XBot-L humanoid)**: Friction **[0.1, 2.0]** Uniform [quote, Table III]. https://arxiv.org/html/2404.05695
- **Lee et al. 2020 (ANYmal, Science Robotics)**: terrain-conditioned friction: Hills N(0.7, 0.2); **Slippery Hills N(0.3, 0.1)**; "The friction coefficient is clipped to be above 0.1." [quote, Table S2]. https://arxiv.org/pdf/2010.11251
- **walk-these-ways (Margolis & Agrawal 2022, Go1)**: `Cfg.domain_rand.friction_range = [0.1, 3.0]`, `restitution_range = [0.0, 0.4]`, `lag_timesteps = 6` [quote, `scripts/train.py`]. https://raw.githubusercontent.com/Improbable-AI/walk-these-ways/master/scripts/train.py
- **DreamWaQ (Nahrendra et al. 2023, A1)**: Friction coefficient **[0.2, 1.25]**, System delay [0.0, 15.0] ms [quote, Table II]. https://arxiv.org/pdf/2301.10602
- **Berkeley Humanoid (Liao et al. 2024)**: Friction **0.2 to 1.25**, Restitution 0.0 to 0.1 [quote, Table 6]. https://arxiv.org/html/2407.21781
- **A-RMA on Cassie (Kumar et al. 2022)**: Ground Friction Ratio **[0.3, 3.0]** [quote, Table I]; in a Simulink line search "RMA and A-RMA stayed stable down to 0.2", and the paper notes 0.2 "lies below the training range" [quote/paraphrase]. Real test: "a plastic sheet with water in between", with "significant slips between the robot feet and ground", policy kept tracking [quote]. https://arxiv.org/html/2205.15299
- **mjlab velocity task default (upstream of microduck_rl)**: `"foot_friction"` event, `func=dr.geom_friction`, `"operation": "abs"`, `"ranges": (0.3, 1.2)`, `"shared_random": True` [quote]. https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/tasks/velocity/velocity_env_cfg.py
- **Agile But Safe (He et al. 2024, Go1)**: Friction factor **U(0.4, 1.1)** [quote, Table II]; deployed on "slippery icy snow" [quote]. https://arxiv.org/pdf/2401.17583
- **MuJoCo Playground Berkeley Humanoid / Go1 envs**: "Floor friction: =U(0.4, 1.0)" [quote]. https://raw.githubusercontent.com/google-deepmind/mujoco_playground/main/mujoco_playground/_src/locomotion/berkeley_humanoid/randomize.py
- **Open Duck Mini v2 playground (Rhoban/apirrone)**: floor friction `jax.random.uniform(key, minval=0.5, maxval=1.0)  # was 0.4, 1.0` [quote, `playground/common/randomize.py`]. https://raw.githubusercontent.com/apirrone/Open_Duck_Playground/main/playground/common/randomize.py
- **Cassie, Li et al. 2021 (Berkeley)**: Ground friction ratio **0.5 to 3.0**, "annealed from default values over the first 2,000 training iterations" [quote, Table II]. https://arxiv.org/html/2103.14295v1
- **legged_gym (ETH/NVIDIA default)**: `friction_range = [0.5, 1.25]` [quote]. https://raw.githubusercontent.com/leggedrobotics/legged_gym/master/legged_gym/envs/base/legged_robot_config.py
- **microduck_rl velocity task (Pollen, current)**: `cfg.events["foot_friction"].params["ranges"] = (0.7, 1.3)  # Grippier footpad — narrowed from (0.3, 1.2)` [quote]. https://raw.githubusercontent.com/pollen-robotics/microduck_rl/main/src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py

What happens to a plain-DR policy below its range (the direct analogue of our failure):

- **Walking on Ice (Shen et al., IJCAI 2026, humanoid)**: the LeggedGym-style DR baseline at **μ = 0.1: survival 100.0, success 0.0, stuck 100.0**; at **μ = 0.2: success 55.1, stuck 44.9**; at μ = 0.3: success 71.3 [quote, Table 2]. The authors read this as "LeggedGym survives through conservative gaits but fails to make forward progress" and the DR baseline shows "very low tangential velocity of contact foot" [quote]. Real floors they report: wet wood μ ≈ 0.2 to 0.3, tile μ ≈ 0.3 to 0.5, ice and snow μ ≈ 0.05 to 0.15 [quote, Fig. 6 caption]. https://www.ijcai.org/proceedings/2026/0694.pdf
  - Note the baseline there *survives* at 0.1 because it was trained with friction in range; our policy spins and falls because 0.15 to 0.2 is far outside [0.7, 1.3] [inference].
- Same paper's framing: methods relying on DR "typically employ conservative gaits, or fail catastrophically when encountering slippery surfaces" [quote, intro].

Takeaway for us: every recipe that worked at μ ≤ 0.3 included that regime in training (RMA 0.05, Humanoid-Gym 0.1, Lee slippery hills ~0.3 clipped at 0.1, Kamohara 0.05) or estimated friction online. None relied on a [0.7, 1.3] policy generalizing downward.

---

## 2. Standard recipe for fine-tuning an existing locomotion policy to a new DR range

Headline: the toolchain default is "resume everything" (actor, critic, optimizer, iteration, normalizer) with the same PPO hyperparameters; the published evidence favors keeping the critic rather than resetting it; the DR widening itself is usually staged (annealed or success-gated), not switched on at once.

What `rsl_rl` / mjlab actually do on load:

- `rsl_rl` PPO `load()` default `load_cfg = {"actor": True, "critic": True, "optimizer": True, "iteration": True, "rnd": True}`; when the optimizer is loaded, `self.learning_rate = self.optimizer.param_groups[0]["lr"]` [quote, `rsl_rl/algorithms/ppo.py`]. So the adaptive learning rate continues from the saved value, and a `load_cfg` dict is the supported way to skip the critic or optimizer. https://raw.githubusercontent.com/leggedrobotics/rsl_rl/main/rsl_rl/algorithms/ppo.py
- mjlab RL config defaults: `learning_rate: float = 1e-3`, `schedule: Literal["adaptive", "fixed"] = "adaptive"`, `desired_kl: float = 0.01`, `resume: bool = False`, `load_checkpoint: str = "model_.*.pt"` [quote, `src/mjlab/rl/config.py`]. https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/rl/config.py
- microduck_rl training ops: resume "with `--agent.load-checkpoint model_XXXX.pt --agent.resume True`" [quote]. "**Warm start ≠ resume.** mjlab's runner stores `common_step_counter` in the checkpoint and restores it (plus the iteration) on load, so loading another task's checkpoint jumps every step-based curriculum to its final stage in iteration 1. Prefix `MICRODUCK_WARM_START=1` ... to restart both at 0 while keeping weights/normalizer/optimizer. Also collapse the inherited curricula of the SOURCE task to their final stage in the target cfg ... the loaded policy was trained under those conditions." [quote, AGENTS.md]. https://raw.githubusercontent.com/pollen-robotics/microduck_rl/develop/AGENTS.md
- microduck_rl velocity PPO config (what `walk61`-class policies were trained with): lr 1.0e-3 adaptive, desired_kl 0.01, entropy_coef 0.01, clip 0.2, 5 epochs, 4 minibatches, num_steps_per_env 24, gamma 0.99, lam 0.95, hidden (512, 256, 128) ELU, obs normalization on, init_std 1.0; max_iterations 50,000, save_interval 250 [quote of values from the cfg]. Curricula in that cfg are iteration-indexed: `action_rate_weight` -0.1 → -1.0 by iter 1500; CoM range to ±0.015 by 1500; standing envs 2 % → 25 % by 2000 [quote of values]. https://raw.githubusercontent.com/pollen-robotics/microduck_rl/main/src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py

Critic: reset or keep?

- **Pretraining in Actor-Critic RL for Locomotion (Fan et al. 2025, ANYmal D)**: warm-starting only one network "still improves mean performance, but at the cost of increased instability" due to "larger variation across runs"; warm-starting both actor and critic was best (Climb Down: +27.7 % final performance, -43.2 % iterations to converge, vs actor-only +19.0 % / -37.9 %) [quote]. They "did not tune PPO hyperparameters" and the adaptive LR is clamped to [1e-5, 1e-2] [quote]. https://arxiv.org/html/2510.12363v2
- Secondary: a 2026 preprint pretrains the critic on returns of the pretrained policy and reports +86.1 % sample efficiency vs no pretraining and +30.9 % vs actor-only [secondary, arXiv 2602.23804]; PIRL freezes the actor until the critic loss converges, with the caveat that the heuristic "can be unstable" [secondary]. https://arxiv.org/abs/2602.23804
- No legged-robot paper was found that compares critic reset vs retention specifically after a DR-range change. [gap]

Curriculum on the DR range itself:

- Li et al. 2021 (Cassie): the full DR ranges are "annealed from default values over the first 2,000 training iterations" [quote]. https://arxiv.org/html/2103.14295v1
- Kamohara et al. 2025: "if the robot can walk in the current region, it is moved to a lower-friction region" [quote]. https://arxiv.org/html/2509.18466
- RMA: penalty coefficients start "very small" and are "increased gradually to prevent the robot from learning to stay in place" [paraphrase of Sec. III-A]. https://arxiv.org/html/2107.04034v1
- REFINE-DP (humanoid fine-tuning): widens randomization ranges in 10 % steps after 90 % success [secondary]. https://arxiv.org/pdf/2603.13707
- MuJoCo Playground tech report: quadruped policy trained first on flat ground with narrow commands, then fine-tuned on rough terrain with wider ranges [secondary; full PDF exceeded fetch limit]. https://playground.mujoco.org/assets/playground_technical_report.pdf

Budget anchors:

- ABS: "each iteration of the agile policy learning takes 1.5 sec" on an RTX 4090; agile policy "needs ∼ 800 iterations (∼ 20 min) to converge", recovery policy "within 500 iterations" [quote]. https://arxiv.org/pdf/2401.17583
- microduck_rl: "A 5-iteration smoke test at 64 envs catches ~95% of config errors for cents."; "Budgets: simple episodic tricks ≈ 1000 iters at 4096 envs" [quote]. Steps are `iteration × 24`. https://raw.githubusercontent.com/pollen-robotics/microduck_rl/develop/AGENTS.md

---

## 3. Gait and reward terms that produce slip-tolerant gaits

Headline: the common ingredient is a contact-gated horizontal foot-velocity penalty (named `feet_slip` / `foot_slip` / "Foot Slip"), plus a clearance term weighted by foot velocity so feet do not drag. Published low-friction behavior is shorter, lower, slower-footed steps; the one biped study with a friction curriculum reports exactly "shorter steps + lower apex".

Exact reward names and weights:

- **mjlab `feet_slip`** (what microduck_rl calls `foot_slip`): `cost = torch.sum(vel_xy_norm_sq * in_contact, dim=1) * active`, i.e. squared xy site velocity of feet in contact, gated by `total_command > command_threshold`; logs `Metrics/slip_velocity_mean` [quote]. Upstream default weight -0.1 [quote]. https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/tasks/velocity/mdp/rewards.py
  - microduck_rl: "foot_slip deliberately weak (-0.1, not -1.0): -1.0 was too restrictive for this robot's pivot-heavy turning." and `command_threshold = 0.01` [quote]. https://raw.githubusercontent.com/pollen-robotics/microduck_rl/main/src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py
- **mjlab `feet_clearance`**: `cost = |foot_height - target_height| * ||foot_vel_xy||` summed over feet [quote]; default weight -2.0, microduck target 0.02 m "Increased from 0.01 to penalize dragging" [quote]. **`feet_swing_height`** default -0.25, microduck target 0.02 "to force foot lifting" [quote]. **`feet_air_time`** rewards air time inside a window; microduck weight 3.0, window 0.125 to 0.300 s [quote of values]. Same two URLs as above.
- **DreamWaQ**: Foot clearance `(p_des_f,z,k − p_f,z,k)² · v_f,xy,k` weight -0.01; Action rate `(a_t − a_{t−1})²` -0.01; Smoothness `(a_t − 2a_{t−1} + a_{t−2})²` -0.01; Joint power -2e-5; Body height -1.0 [quote, Table I]. Real-robot "adaptation to slipping, where the robot can immediately detect irregular footholds" [quote]. https://arxiv.org/pdf/2301.10602
- **walk-these-ways**: `feet_slip = -0.04`, `feet_clearance_cmd_linear = -30.0`, `raibert_heuristic = -10.0`, `action_smoothness_1 = -0.1`, `action_smoothness_2 = -0.1`, `orientation_control = -5.0` [quote]. https://raw.githubusercontent.com/Improbable-AI/walk-these-ways/master/scripts/train.py
- **RMA**: Foot Slip penalty weight 0.8, Ground Impact 0.02, Smoothness 0.001, Action Magnitude 0.07, Joint Speed 0.002 [quote of weights, Sec. III-A]. https://arxiv.org/html/2107.04034v1
- **Solo12 (Aractingi et al. 2023)**: slip penalty = squared horizontal foot velocity times a binary contact indicator ("When a foot comes in contact with the ground, its x, y velocity should be zero in order to avoid slipping") [secondary quote]. https://arxiv.org/pdf/2309.16683
- **Hierarchical quadruped (arXiv 2506.20036)**: slip term fires only when a contacting foot moves more than about 2 cm [secondary]. https://arxiv.org/pdf/2506.20036
- **legged_gym** base rewards include `feet_stumble` (default -0.0) and `stand_still` (default -0.) alongside `feet_air_time = 1.0`, `action_rate = -0.01` [quote]. https://raw.githubusercontent.com/leggedrobotics/legged_gym/master/legged_gym/envs/base/legged_robot_config.py
- **Berkeley Humanoid**: gait-quality terms described as "rewards for longer feet-in-air time, no slipping, and contact forces kept under a threshold" (no weights published) [quote]. https://arxiv.org/html/2407.21781
- **ABS Table XI** regularizers: `v_z²` "To reduce vertical oscillation", `ω_x²+ω_y²` "To reduce rotational oscillation", `‖ȧ‖²` "To encourage smooth actions", torque/velocity/position soft limits at 0.85 / 0.9 / 0.95 of limits "To avoid ... sim-to-real gaps" [quote]. https://arxiv.org/pdf/2401.17583

Gait adaptations on low friction (what the policies actually do):

- Kamohara et al. 2025 (biped, friction curriculum to 0.05): at the low-friction patch "the sampling-time ratio drops from 1.0 to 0.75, which shortens steps" and "reduces stride length and lateral slip"; swing apex residual "decreases to about −2.5 cm, lowering the swing foot for a faster step-down" [quote/paraphrase]. This is the clearest published support for shorter steps and lower clearance on slippery ground. https://arxiv.org/html/2509.18466
- Walking on Ice: the DR-only humanoid policy at low μ shows "very low tangential velocity of contact foot" (conservative, gets stuck); the friction-aware policy shows "low but suitable tangential velocity of contact foot" and 100 % success at μ = 0.1 to 1.0 [quote]. Reading: the slip-tolerant target is low-but-nonzero foot tangential velocity, which a strong slip penalty alone can over-shoot into standing still [inference]. https://www.ijcai.org/proceedings/2026/0694.pdf
- Jenelten et al. 2019 (ANYmal, model-based): recovery via "impedance control and friction modulation" after HMM slip detection; motivated by estimators and controllers that "suffer from the usual no-slip assumption on slippery ground" [quote, abstract]. https://research-collection.ethz.ch/handle/20.500.11850/355281
- Yaw: microduck_rl has `body_ang_vel = -0.05` and `angular_momentum = -0.02` penalties [quote of values] and a `heading_hold_reward` whose docstring argues a yaw-rate penalty "just tells the policy 'never turn'" [quote]. https://raw.githubusercontent.com/pollen-robotics/microduck_rl/main/src/mjlab_microduck/tasks/mdp.py
- Stance width, crouch, flatter foot placement: no published RL locomotion paper found that isolates these as low-friction reward terms; the microduck repo has `feet_distance_penalty` ("Not wired into velocity yet — pinned for later") and `feet_flat_penalty` [quote] which are the natural hooks if needed. [gap + pointer]

[inference] Mechanism relevant to the yaw-spin failure: at μ ≈ 0.15 the friction cone caps the total horizontal force at about 0.15 × 0.8 kg × 9.81 ≈ 1.2 N shared across the stance foot; any policy action that in sim needed > 1.2 N of tangential force (a pivot turn, a fast push-off) saturates the cone and the foot slides. A penalty on foot tangential velocity in contact during fine-tuning at low μ teaches the policy to keep requested tangential force inside the smaller cone; no reward on yaw torque itself is needed.

---

## 4. Evidence on runtime action scaling and low-pass filtering of a trained policy

Headline: filtering helps when it is part of the training environment; adding a filter (or a different action scale) only at deployment changes the closed-loop dynamics the policy was trained against, and the only measurement found of test-time filtering shows worse tracking.

- **microduck_rl policy contract**: "**Policies are UNFILTERED** (no action low-pass in training). Don't add EMA filtering without a matched runtime flag and a transfer test — trained-with / deployed-without (either direction) breaks transfer." [quote]. https://raw.githubusercontent.com/pollen-robotics/microduck_rl/develop/AGENTS.md
- **Cassie (Li et al. 2021)**: "the target positions are first passed through a low-pass filter" before the PD controller; the filter is inside the training loop; cutoff/order not given [quote/paraphrase]. https://arxiv.org/html/2103.14295v1 **A-RMA Cassie** likewise: actions "are first passed through a low-pass filter" [quote]. https://arxiv.org/html/2205.15299
- **Lipschitz-Constrained Policies (Chen et al. 2024, humanoid)**, Table I(a), three seeds: Low-pass filter action jitter 7.86 ± 3.00, task return 24.98 ± 1.29; LCP 3.21 ± 0.11, 26.03 ± 1.51; No smoothing 42.19 ± 4.72, 28.87 ± 0.85 [quote]. Low-pass filters "often dampen or limit exploration" and need per-robot tuning [quote]. Again the filter is trained with. https://arxiv.org/html/2410.11825v2
- **Sim2Dust (2025, rover, DreamerV3)**: filters added to an already-trained policy ("augmented with", inferred test-time): ATE at 15 cm/s Unfiltered 3.3 cm vs Butterworth 4.3 cm vs Moving Average 3.7 cm; Savitzky-Golay "failing catastrophically at 25 cm/s" (64.9 cm); moving average cut jerk by 67 % [quote]. Not legged, but it is the only measured post-hoc filter comparison found. https://arxiv.org/html/2508.11503
- **Causal filter delay**: a causal smoothing kernel of width w "incurs a group delay of (w−1)/2 steps" [quote, ZAPS-DA]. At 50 Hz a 4-step EMA-equivalent delay is ~30 ms, comparable to the whole sim delay range DreamWaQ randomizes (0 to 15 ms) [inference on the comparison]. https://arxiv.org/pdf/2605.30612
- **Open Duck Mini v2 playground**: `LowPassActionFilter` is commented out; instead a random action delay of 0 to 3 steps and a motor speed limit of 5.24 rad/s per control step are *trained in*; `action_scale = 0.25` [quote of values]. https://raw.githubusercontent.com/apirrone/Open_Duck_Playground/main/playground/open_duck_mini_v2/joystick.py
- **Action scale**: it is held constant during training in every source found (0.4 for a 12-D position policy in one paper; 0.25 position / 8.0 torque in another; legged_gym `action_scale = 0.5`; microduck `joint_pos` scale 1.0) [quote of values, secondary for the first two]. No legged-robot paper was found that measures changing the scale at inference. [gap] [inference] Scaling actions at runtime multiplies every PD target offset, so the observed joint positions and `last_action` observation leave the training distribution; expect degraded tracking rather than a graceful "smaller steps" effect.

Net: do not add a filter or rescale actions at deployment as a slip fix. If smoothing is wanted, put it in the env for the fine-tune (and set the matched runtime flag), or rely on the existing `action_rate_l2` schedule.

---

## 5. Recommended recipe for MicroDuck (5 lines) and the gap vs the current config

1. **Friction DR**: widen `cfg.events["foot_friction"].params["ranges"]` from (0.7, 1.3) to **(0.15, 1.3)** with `shared_random=True` kept, staged in two steps: stage A (0.4, 1.3) until episode length and `track_linear_velocity` recover to the walk61 level, then stage B (0.15, 1.3) [Li 2021 annealing, Kamohara success-gated lowering; RMA/Humanoid-Gym/Lee show 0.05 to 0.1 lower bounds are trainable]. Measured 0.15 to 0.2 must be inside the range, not at its edge [inference from the WoI baseline numbers at μ = 0.2].
2. **Warm start, keep everything**: `--agent.load-checkpoint model_XXXX.pt --agent.resume True` with `MICRODUCK_WARM_START=1`, curricula collapsed to their final stage (action_rate -1.0, CoM ±0.015, standing 25 %), actor + critic + optimizer + normalizer loaded, PPO hyperparameters unchanged (lr 1e-3 adaptive, desired_kl 0.01) [rsl_rl load defaults; AGENTS.md warm-start rule; Fan et al. both-network warm start best, no retuning]. Do not reset the critic.
3. **Rewards**: raise `foot_slip` from -0.1 to **-0.3** (Pollen found -1.0 too restrictive for pivot turns, so stay well under it) [inference on the number]; keep `foot_clearance` / `foot_swing_height` target 0.02 and `air_time` 3.0 unchanged; add no new terms. Watch `Metrics/slip_velocity_mean` fall while `track_linear_velocity` stays up; a stuck-but-alive policy (high episode length, low tracking) is the WoI failure mode.
4. **Budget and acceptance**: 5-iteration smoke test at 64 envs first; then about **1000 to 1500 iterations at 4096 envs** total across both stages (AGENTS.md ≈ 1000-iter rule; ABS converges in ~800) on the L4, saving every 250; accept in sim at fixed μ = 0.15 and μ = 1.0 (hold-out for forgetting) with the real 1.5 s spin/fall reproduced on the pre-fine-tune checkpoint at μ = 0.15 first.
5. **Deployment**: export via `scripts/export.py` (normalizer baked in); **no runtime low-pass filter and no action-scale change** [AGENTS.md; Sim2Dust post-hoc filter results]. If the fine-tuned policy still slips at μ ≈ 0.15, the published alternatives are friction awareness (history encoder / estimator, A-RMA, WoI) or a grippier sole; a plain MLP with only `last_action` cannot estimate μ online [inference].

Gap vs current config (`walk61` / microduck velocity cfg):

- Friction range (0.7, 1.3) vs measured 0.15 to 0.2: floor is ~4x below the trained minimum; every recipe that walked at μ ≤ 0.3 trained there or estimated μ.
- `foot_slip` -0.1 with `command_threshold` 0.01: same as mjlab default; weaker than RMA (0.8) and the upstream -1.0 Pollen rejected; no slip-specific shaping beyond it.
- No friction curriculum exists in the cfg (curricula cover action_rate, CoM, standing envs, head pose only).
- Policy is unfiltered, action scale 1.0, 50 Hz, obs = gyro, gravity, joint pos/vel, last action, commands: matches the Pollen contract; keep as is.
- Open items not resolved by literature: exact `foot_slip` weight for this robot (-0.3 is a guess bounded by -0.1 and -1.0), and whether stage A can be skipped under budget (Li 2021 annealed over 2000 iterations; Kamohara gated on success; no paper reports a one-shot jump from 0.7 to 0.15).

---

### Source index

- legged_gym config: https://raw.githubusercontent.com/leggedrobotics/legged_gym/master/legged_gym/envs/base/legged_robot_config.py
- walk-these-ways train.py: https://raw.githubusercontent.com/Improbable-AI/walk-these-ways/master/scripts/train.py
- RMA: https://arxiv.org/html/2107.04034v1
- DreamWaQ: https://arxiv.org/pdf/2301.10602
- Agile But Safe: https://arxiv.org/pdf/2401.17583
- Lee et al. 2020: https://arxiv.org/pdf/2010.11251
- Cassie Li 2021: https://arxiv.org/html/2103.14295v1
- A-RMA Cassie: https://arxiv.org/html/2205.15299
- Humanoid-Gym: https://arxiv.org/html/2404.05695
- Berkeley Humanoid: https://arxiv.org/html/2407.21781
- Walking on Ice (IJCAI 2026): https://www.ijcai.org/proceedings/2026/0694.pdf
- RL-augmented adaptive MPC: https://arxiv.org/html/2509.18466
- Lipschitz-Constrained Policies: https://arxiv.org/html/2410.11825v2
- Sim2Dust: https://arxiv.org/html/2508.11503
- ZAPS-DA: https://arxiv.org/pdf/2605.30612
- Pretraining in Actor-Critic RL: https://arxiv.org/html/2510.12363v2
- Jenelten 2019: https://research-collection.ethz.ch/handle/20.500.11850/355281
- MuJoCo Playground randomize.py: https://raw.githubusercontent.com/google-deepmind/mujoco_playground/main/mujoco_playground/_src/locomotion/berkeley_humanoid/randomize.py
- Open Duck Playground: https://raw.githubusercontent.com/apirrone/Open_Duck_Playground/main/playground/common/randomize.py and .../open_duck_mini_v2/joystick.py
- mjlab velocity cfg / rewards / rl config: https://raw.githubusercontent.com/mujocolab/mjlab/main/src/mjlab/tasks/velocity/velocity_env_cfg.py , .../tasks/velocity/mdp/rewards.py , .../rl/config.py
- rsl_rl PPO load: https://raw.githubusercontent.com/leggedrobotics/rsl_rl/main/rsl_rl/algorithms/ppo.py
- microduck_rl AGENTS.md (develop branch): https://raw.githubusercontent.com/pollen-robotics/microduck_rl/develop/AGENTS.md
- microduck_rl velocity cfg: https://raw.githubusercontent.com/pollen-robotics/microduck_rl/main/src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py
- microduck_rl mdp.py: https://raw.githubusercontent.com/pollen-robotics/microduck_rl/main/src/mjlab_microduck/tasks/mdp.py
