# Phase 1 control: walk up, stop, pick up, hold and release

**Superseded hardware and compute architecture — 8 October 2026.** The available boards are a first-generation Raspberry Pi Zero W with a soldered 40-pin header and a Pi 3 Model B V1.2. The user requires the Mac to run control/policy and the Pi to acquire and forward sensor data; see [current project context](../../../PROJECT-CONTEXT.json) and [board/32-bit compatibility decision](../../redesign-20260913/head-redesign-20261008/BOARD-CHOICE.md). The instructions below preserve the older combined Pi controller for reproducibility. Its 64-bit OS/inference installation is **not an installation procedure for the original Zero W**. The split runtime is not yet implemented or tested. A supervised manually aligned pickup is a commissioning test, not acceptance of the camera-guided learning goal.

This foreground program connects a Mac keyboard to a borrowed Raspberry Pi Zero 2 W, trunk-mounted BNO085, OpenRB and **15 XL330-M288-T servos including jaw ID15**. One process owns the motor bus. It sends body commands from the frozen 61-input policy and jaw commands from measured calibration. It also provides a slow, calibrated pickup sequence. There is no autonomous object detection or trained real-world grasp policy in this release.

Problems advanced: P5 affordable serviceable hardware, P6 measurable first-power and fault-response acceptance. Final Phase 1 acceptance is supervised walking to a prepositioned light foam object, stopping, lowering the head, closing the jaw, lifting, holding and releasing. Supported pickup is the commissioning step before that final trial.

## What was missing and what this adds

The community controller's angle mapping contains only IDs 1–14. The old supervisor reads current and requests torque-off for ID15 but cannot move its jaw. This adapter adds ID15 only to its private controller instance, preserving body offsets and the 14-output walking model. It supplies measured open/closed jaw angles, current-based position mode for the jaw, and ready/lower/carry pickup poses. Lowering the head uses those measured poses after walking stops; it does not copy simulator-only privileged object positions into hardware software.

The camera, audio system and onboard battery are unnecessary for the directly observed first trial. Pi and BNO085 remain required for the real walking model. The Pi runs inference locally; the Mac sends keyboard commands over SSH. No public server, gamepad or automatic restarting service is installed.

## 1. Build and transfer the frozen bundle

On the Mac, this command creates a new output directory and leaves all community checkouts untouched:

```sh
cd /Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/phase1/runtime
python3 prepare.py --community /Users/xiangzheng/code/robotics/microduck-sim/Microduck-build-tutorial/microduck --overlay /Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/runtime-overlay --destination /tmp/microduck-phase1
```

The prepared `bundle/` included with this delivery is equivalent and includes both ONNX models, source hashes and upstream licenses. Install Raspberry Pi OS Lite **64-bit** using Raspberry Pi Imager. Set its hostname to **microduck**, enable SSH, and configure the same 2.4GHz Wi-Fi used by the Mac. Use a club router or private hotspot that permits devices to contact each other; client-isolated campus/guest Wi-Fi can prevent SSH. Choose the Pi username in Imager; use that username in `PI_HOST` below. If `microduck.local` does not resolve, replace it with the Pi's actual IP address from the router or Pi console. A 32-bit OS will not accept these pinned ARM64 inference wheels.

On the Mac, after the Pi boots and the chosen SSH account works:

```sh
export PI_HOST='<Pi username>@microduck.local'
ssh "$PI_HOST"
```

On the Pi:

```sh
sudo apt update
sudo apt install -y python3-venv python3-pip i2c-tools
sudo raspi-config nonint do_i2c 0
sudo usermod -aG dialout,i2c "$USER"
sudo python3 - <<'PY'
from pathlib import Path
p = Path('/boot/firmware/config.txt')
if not p.exists():
    p = Path('/boot/config.txt')
old = p.read_text()
backup = p.with_name('config.txt.before-microduck')
if not backup.exists():
    backup.write_text(old)
block = '\n[all]\n# MicroDuck BNO085: Adafruit Raspberry Pi I2C recommendation\ndtparam=i2c_arm_baudrate=400000\n'
if block not in old:
    p.write_text(old + block)
print('Configured I2C clock in', p)
PY
sudo reboot
```

Back on the Mac, transfer the prepared bundle:

```sh
scp -r /tmp/microduck-phase1 "$PI_HOST":~/microduck-phase1
ssh "$PI_HOST"
```

On the Pi:

```sh
cd ~/microduck-phase1
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
.venv/bin/python phase1.py check
cp calibration.template.json calibration.json
```

Expected output: `offline_dependency_model_check_passed`, with `stand` and `walk`. This command loads the real models and verifies driver methods without opening hardware. Python 3.11–3.13 ARM64 wheel availability was checked at package sources; actual Pi inference speed and memory remain commissioning measurements. This minimal environment does not install the unused Placo, desktop simulator or BMI088 library. The actual community BNO08x I²C driver is included.

For keyless foreground control, use an existing SSH key and `ssh-copy-id "$PI_HOST"` if the Pi does not yet trust it. `mac_control.py` uses SSH batch mode, so it fails clearly if that login has not been established. No key or password is embedded in this package.

## 1A. Measure the torso IMU axes with motor power disconnected

The rear torso clamp fixes the sensor's position but its rectangular envelope does not establish the BNO085 chip's axes. The old community mounting constant cannot be assumed correct. This procedure measures the installed board, computes the required rotation, and checks it against independent movements. It requires no guessed quaternion and no manually approved IMU flag.

Keep motor input plugs disconnected for this first calibration. For recalibration, switch the source off, disconnect all fifteen motor input plugs, then repower only Pi and its sensor. Never unplug motor connectors live. The sensor tool opens the I²C device, never OpenRB, serial transport or a motor-control object. Quit every other controller and IMU reader first.

Connect the selected Adafruit BNO085's STEMMA QT cable: **red VIN → Pi physical pin1 (3.3V); black GND → pin6; blue SDA → pin3 (GPIO2); yellow SCL → pin5 (GPIO3)**. Leave P0/P1 and DI unconnected: the default interface is I²C and default address is **0x4A**. Pulling DI high selects0x4B; do not change it for this build. The tool checks `/dev/i2c-1`, prints the responding address and requires fresh orientation plus angular-speed reports. The setup above enables I²C and sets400kHz, as recommended by Adafruit for the Pi. [Official BNO085 pinout](https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/pinouts), [official Pi wiring and clock setting](https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/python-circuitpython).

On the Pi:

```sh
cd ~/microduck-phase1
.venv/bin/python imu_calibrate.py calibrate --motor-power-disconnected
```

Use the **rigid torso**, not the feet or movable head, as the reference. At upright, keep the rear IMU clamp cover vertical and its top edge horizontal. The duck's left always means its own left when looking in the beak's direction. Support the body by hand or in a loose cradle, with motors disconnected. At each prompt, set the requested pose, let it settle, press Enter and hold still for1.5seconds:

1. **Upright:** rear cover vertical, top edge level, head raised.
2. **Forward:** tilt the entire torso about15–25° so the beak end goes down and tail end rises. Keep its left/right edges level.
3. **Left:** return upright, then lower the duck's left side15–25° and raise its right side. Do not turn it to face a different direction.
4. **Right:** return upright, then lower its right side15–25° and raise its left side.
5. **Back:** return upright, then raise the beak end15–25° and lower the tail end.
6. **Upright again:** return to the original level torso reference.
7. **Head only:** hold that torso reference fixed; gently lower only the head about20° and hold it there. The IMU reading must stay upright, because the sensor is attached to the torso. Do not force a joint.

The program fits upright/forward and checks the independent left/right/back poses. Each lean must be10–35° in the named direction with no more than5° across the other axis; upright return and head-only change must remain within3°. Each hold needs at least25 fresh reports, less than2° spread and angular speed below0.10rad/s. Stale, moving, repeated, reversed or inconsistent captures fail without overwriting the old calibration. Failure tells you which pose to repeat: fix the reference or clamp and rerun the complete command.

Successful output is **`measured_torso_axes_passed`**. It saves the computed rotation and all raw pose samples under `imu_mount` in `calibration.json`. It resets the physical gait gates because a mounting change requires renewed walking checks. Restore the head to ready, then independently check the saved mapping:

```sh
.venv/bin/python imu_calibrate.py check --motor-power-disconnected --seconds 60
```

Read the printed degrees while repeating those motions: upright near0; **beak-end down → positive `forward_deg`; beak-end up → negative**; **left-side down → positive `left_deg`; right-side down → negative**. Holding the torso still and lowering only the head should keep both readings near0. This check loads the saved rotation without fitting a new one. Repeat it after remounting, changing wiring, or before first motor enable after setup. If a sign is wrong, return to the calibration procedure; do not compensate with an invented software sign flip.

The measured rotation is applied consistently to the real Observer's body orientation, the61-input policy's gravity and angular-speed fields, and the runtime tilt stop. Missing or modified evidence blocks motor enable. The runtime requires the same I²C bus/address as calibration. The sensor adapter also tracks quaternion and gyro receipt separately: fresh acceleration packets cannot conceal an old orientation. The100ms limit is host receipt age, not measured sensor sampling latency, and leaves prediction disabled.

## 2. Configure servos while the body is supported

Follow the main assembly guide to establish the wiring and test the **factory OpenRB USB bridge first**. Flash the documented bridge sketch only if that factory check fails or the board previously ran another sketch. Assign unique servo IDs with the concrete procedure below before joining the bus. Stop any existing controller and disable its auto-start before using this entry. On a fresh Lite image there is no such service; if using the community image, stop `microduck-gamepad.service` so it cannot compete for the motor bus or turn Wi-Fi off.

Connect **exactly one physical servo** to OpenRB for ID assignment. All factory servos can start with ID1, so do not join them together first: two devices sharing an ID can be indistinguishable electrically. With the isolated servo powered from the single-servo commissioning source, run on the Pi:

```sh
cd ~/microduck-phase1
.venv/bin/python assign_id.py --list-ports
.venv/bin/python assign_id.py --new-id 1 --one-servo-connected
```

The tool scans IDs0–252 at the factory57600baud, requires one responding model1200(XL330-M288-T), verifies torque-off, sets the requested ID, sets baud-rate register3(1,000,000bps), reopens at1Mbps and verifies ID/model/rate/torque-off. The port is selected automatically only when exactly one OpenRB USB port exists; otherwise pass the exact path from `--list-ports` in `--port`.

After success, label the servo **ID1**, switch motor power off, and disconnect it. Connect the next isolated servo, power it, and run the same command with `--new-id 2`. Repeat through **ID15 for the jaw**, replacing the connected physical servo each time. Never automate these commands as a shell loop. For an already configured servo at1Mbps, add `--initial-baud 1000000`; this is also the explicit retry after an ID change succeeded but a previous baud-rate handoff was interrupted.

Join the bus only after every servo has its unique physical label. Complete the main guide's unmounted single-servo and supported branch tests before using the full-body runtime. **The runtime's `e` command enables all15 together**; it is not the earlier staged branch test.

With the robot physically supported and a commissioned external regulated 5V motor supply, on the Pi:

```sh
cd ~/microduck-phase1
.venv/bin/python phase1.py configure --supported
```

This explicit command first requests and reads back torque-off for all 15. It writes body operating mode 3, jaw operating mode 5, servo voltage limits 3.7–6.0 V, voltage/overheating/electrical-shock/overload shutdown bits0x35 enabled, and disables automatic torque-on. Jaw `Current Limit` is150 mA and `Goal Current` is100 mA initially. Every changed setting is read back; every arm also checks these voltage limits and shutdown protections. Failure exits without enabling torque. These are conservative commissioning settings, not a claim about successful grip force. The jaw's mode 5 uses the real current control function; body mode 3 remains the gait's position control.

Configuration sets **Drive Mode0**: normal direction, velocity-based profile and automatic torque-on disabled. It restores body IDs1–14 `Profile Velocity=0` and `Profile Acceleration=0`, removing the Wizard's temporary raw5 speed setting. Here zero means no servo-generated profile limit; body motion follows the50Hz controller targets and the tested gait gains. Jaw ID15 uses `Profile Velocity=10` (about0.24rad/s) and `Profile Acceleration=0`. Every arm restores and reads back these RAM profile settings after power cycles, before torque enable; wrong Drive Mode or failed profile readback blocks arming. Slow calibrated pickup interpolation remains active.

Reference: [ROBOTIS XL330 control table](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/). The source driver is pinned to [rustypot1.4.2](https://pypi.org/project/rustypot/1.4.2/); its real controller method signatures and register conversions are exercised by the offline tests.

## 3. Record actual positions

Calibration commands turn all 15 servos off. Keep the duck in its support fixture and move joints gently by hand. Never force a powered joint. Each capture asks for Enter after positioning, then reads the actual encoder positions. The body and head angles use the community coordinate mapping; jaw angles use the hardware encoder coordinate. No fabricated jaw center or assumed print tolerance is supplied.

1. Arrange the planted legs and body in the intended stable ready pose, head raised, jaw open. Capture `ready`.
2. Retain that leg pose, lower the head to the intended object height with the jaw open, and capture `lower`.
3. Retain the legs, raise the head enough to lift the selected foam object, jaw open, and capture `carry`.
4. Capture the jaw's open position and gently closed position. The allowed span is at most 30°, matching the inspected jaw geometry. Close without crushing an object or hitting a hard mechanical stop.

On the Pi, run one command for each prepared pose:

```sh
.venv/bin/python phase1.py capture --supported --name ready
.venv/bin/python phase1.py capture --supported --name lower
.venv/bin/python phase1.py capture --supported --name carry
.venv/bin/python phase1.py capture --supported --name jaw-open
.venv/bin/python phase1.py capture --supported --name jaw-closed
```

Inspect `calibration.json`. Its joint ranges start from the matching official MicroDuck model's mechanical ceilings. Narrow them wherever the assembled cable routing or prints restrict motion. The leg pose must remain within 2° across pickup poses. Record the completed physical direction, clearance, endpoint-voltage and supported-pose checks, then accept that calibration:

```sh
.venv/bin/python phase1.py accept-calibration --evidence '<completed checks and measurement/log reference>'
```

Changing poses, jaw settings, joint limits, measured IMU mounting or the current screen invalidates the saved calibration fingerprint and requires renewed acceptance. This command does not run a physical test on the operator's behalf. Its purpose is to prevent untouched placeholder calibration from enabling motion. Editing or recapturing any pose requires renewed physical checking.

## 4. Supported pickup

Keep the master USB-C plug at the external PD receiver within easy reach. Pull it to remove all robot power in an emergency; normal shutdown first stops motion, turns torque off and shuts down Pi. From a Mac terminal, use the client's real local path:

```sh
cd /Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/phase1/runtime
python3 mac_control.py --host "$PI_HOST" --supported
```

Press `e` to enable torque at the current measured positions. Then use:

- `r`: move slowly to ready.
- `n`: lower the head; `u`: lift to carry pose.
- `o` / `c`: open / close the jaw.
- `p`: ready → lower with jaw open → close gently → lift; then hold.
- `l`: open the jaw at the carry pose → return ready.
- `q`, Escape or Ctrl-C: request torque-off and end the session.

Start with an empty jaw. Next use the foam object specified by the assembly guide and place a soft receiving tray below it. Complete five observed pickup/hold/release trials before setting `physical_supported_pickup_passed` to `true` in the calibration file, with the test record retained. A current or position command is not proof the object was grasped: visually confirm lift clearance and a three-second hold.

## 5. Walking and the final combined trial

The two walking gates are separate from pickup calibration. Set `physical_supported_gait_ready` only after motor directions/zeros, the trunk IMU axes, serial timing and motor-supply tests pass. With the robot supported, `v` prepares the gait at zero command, with a1.5-second posture ramp followed by2seconds of policy settling before forward commands are applied; brief `w` commands request forward motion toward a target placed straight ahead. Backward and turning remain behind a separate directional-gait physical test gate. Each velocity request expires after250 ms; `x` sets zero velocity. Forward command is0.30 m/s, matching the tested policy input; the simulated actual speed is substantially lower. Low0.10–0.20 m/s commands are not a reliable slow-walk setting in this frozen policy. Each key request lasts at most250 ms before zero command resumes; hold/repeat only under direct observation. Backward and turning have not been accepted in the initial straight-line task.

The runner reports faults for loops slower than100 ms. Record actual50 Hz loop performance on the Pi while monitoring power; meeting the hard deadline alone does not establish gait stability. Verify the walking-to-zero-command stop before walking toward an object. Only after supported walking/stop trials pass should `physical_supported_walk_passed` become `true`.

Then launch without `--supported` for the supervised freestanding trial. Keep the same support/catch provision available, without loading it during the recorded freestanding result. Walk toward the prepositioned foam target, press `x`, wait at least one second with the robot stable, then use `r`, `p`, wait three seconds, and `l`. The calibrated pickup keeps the legs planted. Return to ready before re-entering `v`/walking. Acceptance is five complete observed repetitions with no fall, protection trip, electrical over-limit or object drop before release.

The Phase1adapter uses body position P gain 275 and retains walk61 after forward movement begins, sending zero velocity to stop. It retains heading correction at zero translation, with gain 2 and a0.8rad/s cap. It does not switch back to stand61 or blend actions. The untouched underlying61D adapter and model files remain frozen; this explicit Phase1choice is implemented in policy.py. Its compatibility tests use real ONNX execution. The optional causal predictor uses only arrived gyro/gravity/joint data. Its latency fields default to `unknown`, so it is disabled until actual sample-age evidence exists. Host receipt age alone is insufficient; a validated device timestamp or latency estimate in the 0–40 ms tested window is required. The final simulation record identifies which delayed cases used this predictor. Mass changes, the walking-to-stop transition and the pickup pose balance still require the current geometry's simulation and physical tests in the main acceptance guide. Do not mark either physical test gate true based on offline tests alone.

## Stop behavior

The Mac sends numbered heartbeats10 times/s. EOF, malformed/replayed packets,600 ms without input, invalid/stale IMU,45° tilt, failed servo reads/writes, voltage outside4.0–5.5 V, excessive measured current, a100 ms loop deadline, device watchdog fault or the session limit ends the session and requests torque-off for **all 15 including the jaw**. Re-enable is latched off until a new session. Target angles are finite and bounded before writes.

Every goal write, including the present-position preload at `e`, passes the shared jaw and head limits in `jaw_limits.py`, `jaw_limits.json` and `jaw_pose_caps.json` (canonical copies in `guide/firmware/pi/`, copied into the bundle by `prepare.py`). head_pitch never goes above 65° (head tipped forward) while the jaw is open by more than 2°, using the larger of the commanded and the measured jaw opening. The jaw opening from the calibrated closed position never exceeds the pose cap: 25°, or 2° short of the CAD first-contact angle where the head pose brings the jaw closer to the neck, motors or torso. The cap uses the smallest table value around every pose between the commanded head pose and the measured one (neck_pitch, head_pitch, head_yaw and head_roll, IDs 12, 11, 13 and 14, read with the jaw every 100 ms); without a measured or commanded value for one of these joints, it uses that joint's worst case. Where the cap would leave less than 5°, the jaw is held closed (`jaw_closed_zone`; the event also records the measured head pose). A clamped write keeps running; the session log records each change in the clamped set as a `goal_limits` event, and the status line shows `limit_clamps`.

Servo bus-watchdog register 10 is set and read back before torque enable, corresponding to 200 ms without bus traffic. That firmware behavior stops commanded motion; it does not prove power disconnection or remove all holding torque. Software torque-off is still a bus request, and the launcher's final readback can report failure. The operator's accessible master USB-C disconnect and support fixture remain the independent stop. Closing a laptop window is not the sole emergency stop.

The runtime's summed servo-current screen remains 5.0A, with 2.25A per group. Those sampled winding-current readings are distinct from total supply current and are not an electronic current limiter. The current source design separately allocates 4A measured motor supply plus 1A logic, at most 5A combined. All fifteen motors are required by this runner. Physical source-current and endpoint-voltage tests in the active power guide remain mandatory.

## Verification records

`offline-results.json` reports the actual software checks. The test builds a fresh bundle and uses real community classes, actual community controller conversions over a substituted Rust transport, real Observation/UserInput/MotorCommand, and both real ONNX models. Device I/O is substituted; physical robot tests remain zero. Calibration and session logs are intentionally separate from source integrity hashes.

The active power source is the existing bank through a 12V receiver and common 5V regulator. The 5A whole-source screen includes logic; measured motor allocation initially allows 4A plus 1A logic. Runtime summed motor-current values are a separate sampled winding-current proxy, not an electronic supply limiter or a measurement of total source current. See the current power recipe for physical release.
