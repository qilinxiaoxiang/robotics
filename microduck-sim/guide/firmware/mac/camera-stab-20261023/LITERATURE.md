# Camera stabilization on MicroDuck: literature pass (2026-10-23)

Question: can MicroDuck get a usable head camera image while walking at 0.25 m/s, and by which route? Robot numbers below are the ones given in the brief for this pass (walk61, head_pitch joint sd 15 deg / 52 deg peak to peak, head_yaw sd 9 deg, trunk tilt sd 2-3 deg, trunk gyro sd 0.7-0.9 rad/s with dominant 5-8 Hz content, sensing-to-actuation latency estimated 40-60 ms, IMX214 camera streamed at 8-10 fps). Current measured values belong in `microduck-sim/CURRENT-STATE.json`; this file is a literature note only.

Labels used below: **[source]** is what a paper or repository states, with a quote or number. **[calc]** is arithmetic done for this note. **[inference]** is project judgment not stated by any source.

Short answer: published work supports a slow, low-bandwidth head correction (below about 2-3 Hz) and a gyro-driven electronic stabilization of the image for everything faster. No source shows a 40-60 ms servo loop cancelling 5-8 Hz jitter mechanically. Pollen's own training notes say the head swing during walking is part of how the policy balances, so overriding it is the main risk.

## 1. Head and gaze stabilization on legged and humanoid robots

### iCub gaze stabilization (neck plus eyes, inertial and kinematic feedforward)
- Source: Roncone, Pattacini, Metta, Natale, "Gaze Stabilization for Humanoid Robots: a Comprehensive Framework", Humanoids 2014. https://arxiv.org/abs/1411.3525
- DoF: 6 (3 neck, 3 eyes). Disturbance: torso moved with "velocity commands of 20 deg/s", plus manual shaking. Metric is image optical flow.
- Result **[source]**: stabilization improved on the no-compensation baseline by "68.1% on average" for the scripted torso motion and "78% on average" under external shaking. Adding the neck to the eyes improved results by 24.4% (scripted) and 21.4% (shaking).
- Not reported: control rate, latency, disturbance frequency. The robot also has fast eye DoF, which MicroDuck lacks.

### SABIAN humanoid head stabilization (vestibulocollic-style neck controller)
- Source: Falotico, Cauli, Dario, Laschi, "Head stabilization in a humanoid robot: models and implementations", Autonomous Robots 2017. https://iris.sssup.it/handle/11382/509092 (DOI 10.1007/s10514-016-9583-z)
- **[source]** (abstract): an adaptive, bio-inspired controller (feedback error learning, which learns to compensate head-motor delay) beat an inverse-kinematics controller against a sinusoidal torso disturbance, and the two "performed about equally" in step responses and real walking.
- Earlier SABIAN work: "A bio-inspired model of head stabilization implemented in a humanoid platform", HAL preprint 2015, https://hal.archives-ouvertes.fr/hal-01142703 , reports that an inverse-kinematics controller could stabilize pitch during walking.
- Not verified here: full text with residual error and frequency numbers (paywalled).
- Takeaway **[inference]**: even on a full humanoid, a learned delay-compensating controller only helps clearly for a predictable periodic disturbance; on real walking it was no better than plain inverse kinematics.

### TEO humanoid soft neck (camera on a tendon-driven neck)
- Source: Munoz, de Santos-Rico, Mena, Monje, "Humanoid Head Camera Stabilization Using a Soft Robotic Neck and a Robust Fractional Order Controller", Biomimetics 9(4):219, 2024. https://pmc.ncbi.nlm.nih.gov/articles/PMC11048281/
- DoF: 2 (pitch and roll; yaw not controllable). IMU on the head platform as feedback.
- Bandwidth **[source]**: crossover designed at 3 rad/s, closed-loop bandwidth 4.65 rad/s (about 0.74 Hz **[calc]**).
- Result **[source]**: with a 12 deg trunk tilt, "The largest error (3.5 deg) only lasts several seconds". Tested with slow trunk pose steps, not gait-frequency disturbances.

### Human head stabilization, the biological reference
- Source: Stensdotter et al., "Mechanisms controlling human head stabilization during random rotational perturbations in the horizontal plane revisited", Physiological Reports 2016. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4886158/ (replicates Keshner and Peterson 1995).
- **[source]**: fair head-in-space stabilization below 1 Hz with vision; "between 1 and 2 Hz, unity gain" between head and trunk; "above 2 Hz the head moved more than the trunk". Reviews place the vestibulocollic reflex at roughly 1-3 Hz (secondhand attribution, not checked against the 1995 original).
- Takeaway **[inference]**: humans, with a reflex loop far faster than 50 ms, do not stabilize the head mechanically above about 2 Hz either. At higher frequency they rely on the eyes (VOR) and passive neck mechanics. MicroDuck has no eyes, so the equivalent is image-side stabilization.

### Walking-robot image stabilization with gyros (the closest legged precedent)
- Source: Kurazume, Hirose, "Development of image stabilization system for remote operation of walking robots", ICRA 2000. https://robotics.ait.kyushu-u.ac.jp/kurazume/en/papers/ICRA00.pdf
- Method: no camera motion; the displayed image window is shifted using gyro estimates plus template matching, output every 12 ms.
- Result **[source]**: image tracking alone held "5 degrees of amplitude, 1.5 [Hz]" and "47 [deg./sec.]"; gyro-guided search held "up to 4 [Hz] and 126 [deg./sec.]".
- Takeaway **[inference]**: electronic (window-shift) stabilization on a walking robot reached 4 Hz in 2000 hardware; the gyro is what extends the frequency range.

### Quadruped camera heads and gimbals
- HyQ: Bazeille et al., "Active Camera Stabilization to Enhance the Vision of Agile Legged Robots", Robotica 35(4):942-960, 2017 (online 2015). https://www.cambridge.org/core/product/F9422BD5D9066968BD46F2C6218DCE72 . Fast pan-tilt unit with IMU feedback **[source]**: outdoor stabilization improved "3D maps by 25%, with a decrease of 50% of mapping failures". Pan-tilt bandwidth and frequencies not verified (full text not read).
- MIT Mini Cheetah: Papalia, "Mini Cheetah Sensor Suite for Visual Perception", MIT thesis 2022. https://dspace.mit.edu/handle/1721.1/143286 . **[source]**: "the rigid mounted camera performed better than the current gimbal configuration" by AprilTag detection. This is the small-legged-robot case closest in scale to MicroDuck: a gimbal that cannot keep up made things worse.
- Lund thesis on a 4-DoF quadruped gimbal (https://lup.lub.lu.se/student-papers/record/9234102) and a BYU thesis (https://physics.byu.edu/docs/thesis/400) both suggest passive spring-damper isolation for high-frequency content alongside active control for low frequency **[source, summary level only]**.

### Head or camera stability inside an RL locomotion policy
- SoFTA: Li, Zhang, Xiao, Pan, Weng, He, He, Shi, "Hold My Beer: Learning Gentle Humanoid Locomotion and End-Effector Stabilization Control", CMU, 2025. https://lecar-lab.github.io/SoFTA/
  - Two agents with separate rewards and rates **[source]**: "upper-body actions at 100 Hz for precise EE control and lower-body actions at 50 Hz for robust gait". It "reduces EE acceleration by 2-5x to baselines" and was used to record steady video ("Humanoid as Camera Stabilizer").
  - Baselines **[source]**: "Lower-body RL + IK performs the worst due to lack of dynamics awareness"; single whole-body RL "improves but struggles" under pushes. The stabilized limb was trained together with the legs, so the gait knows about it.
  - Rewards **[source]**: penalties on end-effector linear and angular acceleration plus an end-effector gravity-alignment term.
- Disney BDX: Grandia et al., "Design and Control of a Bipedal Robotic Character", 2025. https://arxiv.org/abs/2501.05204 . **[source]**: walking policy at 50 Hz takes head commands as "offsets relative to a nominal head motion that the animator specifies as part of the periodic walk cycle"; imitation reward on "Neck joint positions" (weight 100) plus neck action-rate and acceleration penalties. No separate head-stability reward and no external controller overriding the head.
- LIPM-guided bipedal RL (arXiv 2509.09106, 2025, https://arxiv.org/abs/2509.09106): regulates COM height and torso orientation in the reward, motivated by "a stable camera viewpoint" **[source, abstract]**.
- I found no paper that overrides a trained locomotion policy's neck outputs with an external stabilizer and reports gait robustness. The closest evidence is SoFTA's finding that a kinematic stabilizer bolted onto a learned gait (RL + IK) was the worst option.

## 2. Gyro-based electronic video stabilization

### Karpenko et al. 2011 (the base method)
- Source: Karpenko, Jacobs, Baek, Levoy, "Digital Video Stabilization and Rolling Shutter Correction using Gyroscopes", Stanford Tech Report CSTR 2011-03. https://graphics.stanford.edu/papers/stabilization/ (read via the Wayback copy of karpenko_gyro.pdf)
- Model: rotation only, integrated gyro, per-row rolling-shutter warp on the GPU.
- Hardware **[source]**: iPhone 4 gyro "at a (maximum) frequency of 100Hz", 720p at 30 fps.
- Time sync **[source]**: the gyro-to-frame delay td and rolling-shutter duration ts are estimated from one ~10 s calibration clip ("shake the camera while pointing at a building"); "a small misalignment in td or ts would cause rolling shutter rectification to fail". Calibrated reprojection error "typically around 1 pixel".
- Crop **[source]**: "We crop video frames in order to hide these empty areas"; no percentage given.
- Motion blur **[source]**: "motion blur in low-illumination videos ... significantly degrade[s] the quality"; the method does not remove blur.
- Live preview **[source]**: a "truncated causal low-pass filter" attenuates shake but does not remove it. Offline smoothing can look ahead; live cannot.

### Successors with numbers
- Google Pixel 2 fused video stabilization, Google Research blog, 2017. https://research.google/blog/fused-video-stabilization-on-the-pixel-2-and-pixel-2-xl/ . **[source]**: gyro at "200 Hz"; rolling-shutter readout takes "tens of milliseconds"; a timestamp error of about 3 ms already causes visible jitter (the blog's example); frames are queued so the filter sees future motion; per-frame blur is estimated from the rotation between exposure start and end and cannot be removed afterwards.
- Jia, Evans, "Online Camera-Gyroscope Auto-Calibration for Cellphones", IEEE Trans. Image Processing 2015. https://users.ece.utexas.edu/~bevans/papers/2015/autocalibration/ . **[source]**: estimates td online with an EKF, initialized over "+-30ms"; tested on a running sequence with "very high frequency shake". Shows that a running (impact-heavy) gait is within reach of gyro-based calibration.
- Ovren, Forssen, ICRA 2015 (https://people.isy.liu.se/cvl/perfo/abstracts/ovren15.html): joint calibration of time offset, time scale, relative pose and gyro bias for a rolling-shutter camera with an external gyro (site unreachable during this pass; summary level only).

### Motion blur at 0.8 rad/s on the IMX214
- Lens **[source]**: Radxa Camera 13M 214, horizontal FOV 66.2 deg, EFL 3.57 mm. https://docs.radxa.com/en/accessories/camera_13m_214
- **[calc]** focal length in pixels f = (W/2) / tan(33.1 deg): about 490 px at a 640 px wide stream, about 980 px at 1280 px. Blur length = omega x exposure x f.
- At omega = 0.8 rad/s and 640 px wide: 1 px blur at 2.5 ms exposure, 2 px at 5 ms, 4 px at 10 ms, 13 px at 33 ms.
- At 1280 px wide: 1 px at 1.3 ms, 4 px at 5 ms, 8 px at 10 ms.
- A common working limit is 1-2 px of blur for feature tracking or detection **[inference; no single source fixes this threshold]**. That means exposures of about 2.5-5 ms at 640 px. Indoor light usually forces longer exposures or high gain, so blur, not the warp, is the likely limit.
- Caveat **[inference]**: 0.8 rad/s is the trunk gyro. The head camera also carries the policy's own head_pitch swing, so the camera's angular rate is probably higher. A head-mounted IMU, or trunk gyro plus head joint velocities, gives the real figure. Electronic stabilization needs the camera's rotation, so the A7Z IMU in the head is the right sensor if it rotates with the camera.

### Crop margin needed
- **[calc]** At 640 px and 66 deg HFOV, one degree is about 8.6 px at image centre. Removing a +-5 deg residual rotation needs about 43 px on each side, roughly 13 % of the width each side. The head_pitch joint swing (52 deg peak to peak) is far larger than any crop can absorb, so electronic stabilization can only handle the residual after the head's slow motion is dealt with.

## 3. Pollen Robotics, Open Duck Mini and BDX-style robots

- Pollen MicroDuck training repo (local fork `microduck-sim/microduck_rl`, file `src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py`, last change 2026-08-25 per git log):
  - Head commands are policy inputs **[source]**: a 4-D head_pose command (neck_pitch, head_pitch, head_yaw, head_roll deltas from HOME) is part of the 61-D observation ("48 proprio + twist(3) + head(4) + body(6)"), and the policy outputs the head joints itself.
  - Reward **[source]**: head_pose_tracking, weight 2.0, Gaussian std 0.5 rad per joint.
  - The key finding, in the repo's own comments **[source]**: tightening head tracking to std 0.1 made "the policy stopped walking entirely by iter 300"; "a 280 g head (38% of robot mass) must oscillate while stepping. Standing still scored higher, so it stood still." Their fix penalizes only the slow (1 s EMA) head bias, which "At the optimum ... costs a walking policy nothing".
  - Our runtime (`guide/firmware/mac/walk_brain.py`) records walk61 as Pollen BEST_alpha_walking with command names twist, head_pose, and smooths the head command with an EMA of 0.2 per tick as Pollen's runtime does. Whether BEST_alpha_walking was trained with exactly this config is **[inference]** from the shared 61-D layout.
- Open Duck Mini v2 (Antoine Pirrone, Open_Duck_Playground, `playground/open_duck_mini_v2/joystick.py`, https://github.com/apirrone/Open_Duck_Playground): **[source]** the command is 7-D (3 velocity + neck_pitch, head_pitch, head_yaw, head_roll) and goes into the observation; the line that would force head targets from the command is commented out ("# motor_targets.at[5:9].set(state.info["command"][3:])  # head joints"), so the policy drives the head. No head-stability reward found.
- Disney BDX (above): head commands are offsets on an animated nominal walk-cycle head motion, tracked inside the 50 Hz policy. The head moves during the walk by design.
- Common pattern **[source, all three]**: the head is commanded through the policy, never held fixed by a separate controller. None of them adds a camera-stability reward.

## Implications for MicroDuck

(a) Slow head and trunk motion (gait-cycle swing, drift, the 52 deg head_pitch swing).
- Published support: low-bandwidth head control below about 1-3 Hz works (TEO at 0.74 Hz bandwidth, humans below 1-2 Hz, SABIAN on real walking).
- On this robot the slow head motion is produced by the policy itself, so the supported route is to shape it through the policy. One option is to send a head_pose command that offsets the measured trunk pitch and yaw drift, within the trained ranges (+-1.10 / 1.10 / 1.40 / 0.31 rad). Another is retraining with a head-stability term in Pollen's escapable style, priced on slow error only. **[inference]**
- What stays in the image after that goes to gyro-based electronic stabilization (Karpenko-style rotation warp plus crop).

(b) 5-8 Hz jitter.
- Published support: image-side stabilization driven by a gyro (Kurazume to 4 Hz in 2000; phone EIS with 100-200 Hz gyros). No source shows mechanical cancellation at these frequencies with 40-60 ms loop delay.
- **[calc]** A feedback canceller with pure delay d leaves a residual of 2 sin(pi f d) of the original disturbance. With d = 50 ms that is 0.62 at 2 Hz, 0.91 at 3 Hz, 1.41 at 5 Hz and 1.62 at 6 Hz. Break-even, where cancellation stops helping, is about 3.3 Hz at 50 ms (2.8 Hz at 60 ms, 4.2 Hz at 40 ms). Above that, a servo correction amplifies the jitter. Servo small-step deadband would make it worse **[inference]**.
- Practical requirements from the EIS papers: camera-rate gyro on the head (100 Hz or more), timestamped frames, td calibrated to a few ms (Google: 3 ms is already visible), short exposure (about 2.5-5 ms at 640 px wide for at most 2 px blur), about 10-15 % crop per side. At 8-10 fps a live, causal filter cannot look ahead, so expect attenuation, not removal (Karpenko's live mode). For detection on single frames, short exposure plus rotation correction matters more than smooth playback. **[inference]**
- A passive compliant element between neck and camera, as the Lund and BYU theses and the swan-neck work suggest, is a mechanical option for this band. No source tests it at this scale. **[inference]**

Main risk of overriding the policy's head outputs.
- Pollen's own training shows the head swing is part of the gait: a 280 g head is 38 % of robot mass, and forcing it steady made the policy stop walking. Replacing walk61's head goals with a stabilizer moves that mass in a way the policy never saw. The likely effects are a shifted COM trajectory, out-of-distribution joint_pos and joint_vel observations for the four head joints (the policy reads its own head state), and falls. **[inference, grounded in the repo comment]**
- SoFTA's result points the same way: a kinematic stabilizer added to a learned gait (RL + IK) performed worst. The two working designs it compares were both trained together with the legs.
- Lower-risk order **[inference]**: (1) electronic stabilization only, no change to actuation; (2) small head_pose command offsets inside the trained range, so the policy still produces the motion; (3) retraining with a slow-error head term, checked in sim against the stand-still degenerate policy as in the Pollen note.

## Sources not fully read in this pass
- Falotico et al. 2017 full text (residual error and frequencies).
- Bazeille et al. 2017 full text (pan-tilt bandwidth).
- Ovren and Forssen 2015 (host unreachable).
