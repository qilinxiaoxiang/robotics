# Thrust-assisted walking: published evidence for the MicroDuck flight pack

Question: can the four-EDF pack, run partly on while the duck walks, make walking more stable or faster, and what limits that? All sources read 2026-11-10. "Inference" marks reasoning that is ours, not the source's. "Unverified" marks a claim whose source could not be opened.

## 1. Caltech LEONARDO (LEO)

A bipedal robot with two legs of three actuated joints each and four propeller thrusters mounted at an angle on the shoulders, 2.5 ft (about 0.76 m) tall (Caltech news, 2021-10-06). Published as Kim, Spieler, Lupu, Ramezani, Chung, "A bipedal walking robot that can fly, slackline, and skateboard", Science Robotics 6(59), eabf8136, 2021.

- Thrust during walking: the propellers keep the robot upright while the leg actuators move the centre of mass forward; a person can push it hard without knocking it over. The legs carry "the bulk of the weight" (Caltech news).
- Cost: the team states that balancing with propellers during walking "uses energy fairly inefficiently", and lists stiffer legs that carry more weight and less propeller reliance as next steps (Caltech news).
- Mass 2.58 kg and the remark that the legs are "slender and underpowered" and need "constant support from the propellers" (Mintchev commentary): unverified, seen only in search snippets; the Science Robotics paper and The Engineer article returned HTTP 403. No thrust, thrust-to-weight or power figure was found in any page opened.

## 2. Northeastern Harpy and Husky Carbon (Ramezani, Sihite et al.)

Harpy is a biped with two torso-mounted ducted fans. Its stated mass differs by paper: about 4 lb with 0.8 kg in the simulation model (Dangol, Sihite, Ramezani, Frontiers in Robotics and AI, 2021-12-23), 4.5 kg (arXiv 2411.17727, 2024-11), about 7 kg with two Schubeler DS-51 90 mm EDFs (arXiv 2501.01443, 2024-12-27). The last source quotes 2.5 kg and also 5 kg maximum thrust per fan and a 1.6 thrust-to-weight ratio, figures that do not agree with each other.

- 2021 Frontiers paper (simulation only): thrusters are active mainly in double support, where nonlinear MPC uses them to steer the state back to the gait cycle; opposite left/right thrust stabilises frontal (roll/yaw) dynamics; roll and heading stayed near zero. No hardware numbers.
- 2024 capture-point paper (simulation): thrust enters as "virtual buoyancy", effective gravity g - |u_t|/m, so ω = sqrt((g - |u_t|/m)/z0); higher thrust gave a smaller capture point and more stability. Thrust was a fixed parameter, not optimised.
- 2024 thesis, hardware: Harpy trotted in place with differential thrust stabilising the frontal plane, one fan held at a 10 % base command; roll and pitch "are stable throughout". Conclusion: "the robot has enough leg joint power to walk without thrusters"; thrust was used for frontal stabilisation, not for lift.
- Husky Carbon (quadruped with EDFs): narrow-path walking with posture manipulation plus thrust vectoring (arXiv 2405.06070, 2024-05-09) and steep-slope walking (arXiv 2406.13118, 2024-06-19). Both are MATLAB simulation studies with no quantitative results on the abstract pages.

## 3. Jet-powered humanoids

IIT iRonCub3 (Pucci's AMI lab): about 70 kg with four jet turbines (two on the arms, two on a back jetpack), maximum thrust above 1000 N; lifted about 50 cm off the floor (IIT Opentalk, 2025-06-18). Turbine exhaust is reported at 700 to 800 °C by different outlets. Nothing was found on walking with the jets running; the work is about take-off, hover and landing. No other jet-powered walker was found.

## 4. Reduced-gravity gait science and the Froude limit

- Kram, Domingo, Ferris 1997 (J Exp Biol 200:821-826, NASA NTRS abstract): a near-constant upward force at the centre of mass simulated reduced gravity. In normal gravity bipeds switch from walking to running near Froude number Fr = v²/(gL) = 0.5. In reduced gravity the transition came at progressively slower absolute speeds but at about the same Fr. The gravity levels and speeds are in the full text, which was not opened (unverified).
- Donelan and Kram 1997 (J Exp Biol 200:3193-3201, full PDF read): 10 subjects walked at 0.25 g to 1.0 g. At equal Fr, duty factor matched but relative stride length differed by up to 67 %, so dynamic similarity was rejected. At equal absolute speed, lower gravity gave 10 % lower duty factor and 16 % shorter relative stride. Their device loaded only the torso, as a top-mounted thrust pack would.
- What this means for "faster with offload" (inference): an inverted-pendulum walker loses ground contact when v²/L exceeds g, and the walk-run transition sits near Fr 0.5. With thrust T carrying part of weight W, effective gravity is g(1 - T/W). At a fixed Froude number, the walking speed ceiling scales with sqrt(1 - T/W). At 30 % offload the ceiling falls to sqrt(0.7) ≈ 0.84 of its 1 g value. Vertical offload therefore lowers the maximum walking speed for the same leg length. It does not raise it. Friction is proportional to normal force, so foot traction falls by the same factor. Any speed gain has to come from a forward thrust component (tilting the pack) or from lighter leg load letting a torque-limited joint move faster, never from the vertical offload itself.

## 5. Thrust assist on other small legged robots

Salto-1P (Haldane, Yim, Fearing, IROS 2017; IEEE Spectrum): 0.098 kg monopod, 14.4 cm leg, standing vertical leap of 1.25 m. Two thrusters control yaw (opposed) and roll (together) while airborne about 92 % of the time; pitch uses an inertial tail. Here thrust gives attitude authority, not weight support.

## 6. Controls notes for the ArduPilot flight controller

(a) Ground behaviour, from ArduCopter source (master, read 2026-11-10):

- Land detector (`ArduCopter/land_detector.cpp`, `config.h`): land_complete is set only after all conditions hold for LAND_DETECTOR_TRIGGER_SEC = 1.0 s: motors at the lower throttle limit, throttle mix at minimum, requested lean under 15°, attitude error under 30°, filtered acceleration ≤ 1.0 m/s², vertical speed < 1.0 m/s. "Landed maybe" uses 0.2 s. Once the copter is landed, land_complete clears when throttle leaves the lower limit with the motors in THROTTLE_UNLIMITED.
- Spool states (`AP_Motors_Class.h`): SHUT_DOWN, GROUND_IDLE, SPOOLING_UP, THROTTLE_UNLIMITED, SPOOLING_DOWN. In Stabilize (`mode_stabilize.cpp`), zero throttle requests GROUND_IDLE, where rate-controller I terms are reset smoothly and throttle output is 0. Any throttle above zero requests THROTTLE_UNLIMITED.
- While landed, rate gains scale by ATC_LAND_R_MULT / _P_MULT / _Y_MULT (range 0.25 to 1.0, default 1.0) to curb ground oscillation (`AC_AttitudeControl.cpp`). ATC_RAT_RLL/PIT/YAW_IMAX (range 0 to 1) cap each I term. The PID stops the integrator growing only when the output is flagged as limited (`AC_PID.cpp`).
- Consequence for "half open" walking (inference): with throttle above idle the controller treats the duck as flying, so integrators run and landed gain reduction is off. If the feet hold the body at an attitude the controller does not want, the attitude error persists and the I terms wind up toward IMAX. When a foot lifts, that stored command is released as a roll or pitch kick. The land detector cannot help, because by design it never declares landed at part throttle.

(b) Companion-computer interfaces:

- SET_ATTITUDE_TARGET (MAVLink id 82): quaternion, body rates in rad/s, thrust normalised 0..1 (mavlink.io). In ArduPilot Guided or Guided_NoGPS (the only message Guided_NoGPS accepts), thrust is a climb-rate demand by default (0.5 = hold). With GUID_OPTIONS bit 3 (value 8) it is raw thrust 0..1. If commands stop for GUID_TIMEOUT (default 3 s) the vehicle holds a level hover (ArduPilot Guided docs).
- MAV_CMD_DO_MOTOR_TEST (id 209): per-motor instance, throttle type (percent, PWM, pilot pass-through), value, timeout, count (mavlink common.xml). In ArduPilot it refuses unless land_complete is set, outputs open-loop PWM with no attitude control, and its timeout is capped at 600 s (`ArduCopter/motor_test.cpp`).
- RC_CHANNELS_OVERRIDE (id 70): channel values in µs; UINT16_MAX ignores a channel and 0 releases it to the radio (mavlink.io).
- Lua scripting (SCR_ENABLE = 1): `SRV_Channels:set_output_pwm_chan_timeout(chan, pwm, ms)` overrides autopilot output until the timeout expires. Outputs can be assigned to Script Out 1-16 via SERVOx_FUNCTION 94-109 (ArduPilot Lua docs). A scripted custom mixer is built with `MotorsMatrix:add_motor_raw` (`AP_Scripting/examples/MotorMatrix_setup.lua`).

## Sources (all read 2026-11-10)

- Caltech news, LEO: https://ese.caltech.edu/news/leonardo-the-bipedal-robot-can-ride-a-skateboard-and-walk-a-slackline
- Caltech CAST LEONARDO page (citation only): https://aerospacerobotics.caltech.edu/leonardo
- ScienceDaily, LEO: https://www.sciencedaily.com/releases/2021/10/211006160052.htm
- Unverified (HTTP 403): https://www.science.org/doi/10.1126/scirobotics.abf8136 ; https://www.theengineer.co.uk/robot-leo-demonstrates-hybrid-locomotion/
- Dangol, Sihite, Ramezani 2021, Harpy: https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2021.770514/full
- Harpy capture point: https://arxiv.org/html/2411.17727v1
- Harpy/thrust-vectoring thesis: https://arxiv.org/html/2501.01443v1
- Husky narrow path: https://arxiv.org/abs/2405.06070v1
- Husky slope: https://arxiv.org/abs/2406.13118
- iRonCub3: https://opentalk.iit.it/en/iit-demonstrates-that-a-humanoid-robot-can-fly/
- Kram, Domingo, Ferris 1997 abstract: https://ntrs.nasa.gov/citations/20040173033
- Donelan and Kram 1997: https://www.sfu.ca/locomotionlab/assets/dynsimwalk1997.pdf
- Salto-1P: https://spectrum.ieee.org/salto1p-is-the-most-amazing-jumping-robot-weve-ever-seen
- ArduCopter land detector: https://github.com/ArduPilot/ardupilot/blob/master/ArduCopter/land_detector.cpp
- ArduCopter config constants: https://github.com/ArduPilot/ardupilot/blob/master/ArduCopter/config.h
- AP_Motors spool states: https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Motors/AP_Motors_Class.h
- Stabilize mode: https://github.com/ArduPilot/ardupilot/blob/master/ArduCopter/mode_stabilize.cpp
- Attitude control (LAND_*_MULT, IMAX): https://github.com/ArduPilot/ardupilot/blob/master/libraries/AC_AttitudeControl/AC_AttitudeControl.cpp ; https://github.com/ArduPilot/ardupilot/blob/master/libraries/AC_AttitudeControl/AC_AttitudeControl_Multi.cpp
- PID integrator limit: https://github.com/ArduPilot/ardupilot/blob/master/libraries/AC_PID/AC_PID.cpp
- Motor test: https://github.com/ArduPilot/ardupilot/blob/master/ArduCopter/motor_test.cpp
- Guided mode commands: https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html ; https://ardupilot.org/copter/docs/ac2_guidedmode.html
- MAVLink common messages: https://mavlink.io/en/messages/common.html ; https://github.com/mavlink/mavlink/blob/master/message_definitions/v1.0/common.xml
- ArduPilot Lua scripts: https://ardupilot.org/copter/docs/common-lua-scripts.html ; https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Scripting/examples/MotorMatrix_setup.lua
