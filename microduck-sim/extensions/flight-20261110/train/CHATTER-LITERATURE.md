# Action chatter that passes in simulation and fails on position-controlled servos: what published work does (2026-11-19)

Read on 2026-11-19 for flight round 3, before the training change. Failure in hand: `s2r6_4` stands and walks in every
simulated cell and falls on the robot at standstill in 4.4 s with 172 action jumps over 0.5 rad per 10 s
(`docs/PET_ROBOT_LOG.md` 2026-11-19 16:00). In simulation the same fall appears only when the position gain is doubled
(`--kp-rl 400`, RUNLOG "Round 3").

## What the sources say

1. Lipschitz-constrained policies. Chen, He, et al., "Learning Smooth Humanoid Locomotion through Lipschitz-Constrained
   Policies", arXiv 2410.11825 (IROS 2025), https://arxiv.org/html/2410.11825v2. Simulated actuation is idealised, so a
   policy can become bang-bang and command changes real actuators cannot follow; such policies often do not transfer.
   Fix: a penalty on the gradient of the action log-probability with respect to the policy input,
   lambda x E ||grad_s log pi(a|s)||^2, lambda 0.002. Action jitter in simulation: no smoothing 42.2, low-pass filter
   7.9, smoothness rewards 5.7, gradient penalty 3.2, at similar task return (28.9, 25.0, 26.6, 26.0). The penalty must
   cover the whole input including the observation history (current frame only: 7.2). lambda 0.001 still jitters,
   0.01 makes the gait sluggish (return 16.1). Real-robot numbers are given for the penalty only.
2. Smoothness as a regulariser on the policy, not on the reward. Mysore et al., "Regularizing Action Policies for
   Smooth Control with Reinforcement Learning" (CAPS), ICRA 2021, arXiv 2012.06644, https://ai.bu.edu/caps/. Two loss
   terms: temporal ||pi(s_t) - pi(s_t+1)|| and spatial ||pi(s) - pi(s + noise)|| with the noise set to the expected
   sensor noise. On a real quadrotor the power draw fell by about 80 %.
3. Action-rate and action-acceleration rewards plus a matched filter and an identified actuator model. Grandia et al.,
   "Design and Control of a Bipedal Robotic Character" (Disney BDX), RSS 2024, arXiv 2501.05204,
   https://arxiv.org/html/2501.05204v1. A small biped with Dynamixel head servos, policy at 50 Hz. Reward terms:
   leg action rate 1.5, leg action acceleration 0.45, neck 5.0 and 5.0, joint torque 1e-3, joint acceleration 2.5e-6.
   Actions pass a first-order hold and a 37.5 Hz low-pass, "identically implemented in the RL and runtime
   environments". Actuator model from bench identification: PD torque, friction, speed-dependent torque limit,
   backlash 0.002 to 0.015 rad drawn per episode, encoder offset, position noise growing with speed, reflected
   inertia +-20 %. Gains and delay are not randomised there; the actuator is identified instead.
4. Gain randomisation when the actuator is not identified that well. Li et al., "Reinforcement Learning for Versatile,
   Dynamic, and Robust Bipedal Locomotion Control" (Cassie), arXiv 2401.16889: PD gains of every joint randomised
   +-30 % to cover uncertain motor dynamics. "Sampling Strategies for Robust Universal Quadrupedal Locomotion
   Policies", arXiv 2510.07094, https://arxiv.org/html/2510.07094v1: "our results demonstrate the need for significant
   joint controller gains randomization"; policies trained with narrow gain ranges stood on the hardware and could not
   walk.
5. Servo friction. Duclusaud et al., "Extended Friction Models for the Physics Simulation of Servo Actuators", arXiv
   2410.08650 (the BAM model this project trains with): Coulomb-viscous models miss load-dependent and Stribeck
   friction of hobby servos. The Open Duck Mini project names this identification as critical for its transfer
   (https://github.com/apirrone/Open_Duck_Mini, docs/sim2real.md). No source read gives a servo-level reason for
   chatter beyond these terms.
6. Behaviour-cloning anchor during fine-tuning. Wolczyk et al., "Fine-tuning Reinforcement Learning Models is Secretly
   a Forgetting Mitigation Problem", ICML 2024 (already the source of this repository's t2 anchor,
   `microduck_rl/cmu/planning/fetch-20261103/starter/motion/reference/finetune_worker.py`): a fine-tune overwrites the
   start policy's behaviour in states it rarely visits early; a cloning loss on the start policy's actions keeps it.

## Where the current recipe differs

- Action rate: present (`action_rate_l2`, weight -1.0 at the end of its ramp). No action-acceleration term. Disney
  carries both, at about 3 to 1.
- Gain randomisation: off (`ENABLE_KP_RANDOMIZATION = False` in the base recipe; and the existing event averages its
  per-joint draws into one scale, so a wide range would collapse to its middle).
- Policy input gain is not constrained or measured in selection. Measured now on walk61's robot walks
  (`guide/firmware/mac/robot-runs-20261030-t1/sensitivity.py`, 130 states): median Jacobian norm walk61 10.7,
  ts_start 15.4; on the joint-position inputs 4.2 against 8.3, on the gyro 0.73 against 1.13. The flight lineage's
  start already feeds joint position back about twice as strongly as walk61. That is the quantity source 1 bounds,
  and it fits the matched cell: doubling the servo gain breaks ts_start (standstill 8 falls of 10) and not walk61
  (0 of 10).
- Action filter: none, and `microduck_rl/AGENTS.md` forbids adding one without a matched runtime flag and a transfer
  test. Source 3 supports a filter only when it is identical on both sides.
- Anchor: the flight lineage has none; it sits 1.1 to 1.5 rad from walk61 on walk61's own robot states (gate G1).
- Selection: on simulated falls only. Sources 1 and 2 select on jitter as well.

## What this round does with it

- Train the teacher under position-gain randomisation that spans the matched cell (one scale per env, 0.8 to 2.2;
  sources 4), with the loop delay and the load range of round 2.
- Behaviour-cloning anchor to walk61 on the states where walk61 is the proven policy: no pack (source 6, and the t2
  precedent that passed the 0.25 rad gate at 0.208).
- Add the action-acceleration term beside the action rate and raise the action-rate weight (source 3), sized by the
  incentive audit, with the chattering teacher as one of the audited policies: it must earn less than the smooth one.
- No action low-pass (AGENTS.md).
- Not in this round, next if the gates still fail: the gradient penalty of source 1. Its coefficient has to be tuned
  to this policy's input scale (0.001 too weak, 0.01 sluggish in the source), which needs runs the remaining Kaggle
  quota (5.7 h under the 26 h ceiling) does not hold. The anchor already pulls the input gain toward walk61's on the
  no-pack states, and G1 plus the gain400 cells measure whether that was enough.
