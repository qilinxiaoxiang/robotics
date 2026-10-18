# Zero W software and model migration review

Verified 8 October 2026. Problems P0/P5/P6: preserve the learned-control goal while making the owned sensor board usable and keeping deployment claims measurable.

The first-generation Zero W needs a different software deployment from the historical Zero 2 W package. The current Mac-control/Pi-sensor split is recorded as the intended architecture, but the existing controller still runs inference on the Pi. CPU architecture alone does not require retraining the models.

## What changes with the board

The original Zero W uses a single-core ARM11/ARMv6 CPU and a 32-bit userland. Zero 2 W uses quad-core Cortex-A53/ARMv8-A and can run a 64-bit OS; the same 64-bit capability also applies to the owned Pi 3 Model B. Zero 2 W can also use a compatible 32-bit OS. Raspbian's ARMv6-compatible `armhf` is distinct from ordinary ARMv7-only `armhf`; a package labelled “32-bit ARM” is insufficient proof of Zero W compatibility. See the [official architecture explanation](https://www.raspberrypi.com/news/raspberry-pi-os-64-bit/), [Zero W product page](https://www.raspberrypi.com/products/raspberry-pi-zero-w/), and [Zero 2 W product brief](https://datasheets.raspberrypi.com/rpizero2/raspberry-pi-zero-2-w-product-brief.pdf).

The operating system and compiled libraries must match that architecture. Official Raspberry Pi OS offers a Lite edition suited to older boards and a 32-bit image for the original Zero. Use the supported camera stack supplied with the OS; do not carry over the historical guide's instruction to install a 64-bit image onto this board. [Raspberry Pi OS documentation](https://www.raspberrypi.com/documentation/computers/os.html)

## What the code actually does

- `../../phase1/runtime/README.md` still explicitly targets Zero 2 W, says Pi-local inference, and prescribes 64-bit OS plus binary-only dependency installation. This historical README is superseded by `PROJECT-CONTEXT.json`, but its executable architecture remains unchanged.
- `mac_control.py:24–27` builds an SSH command that launches `phase1.py run` **on the Pi**. The Mac program is currently a keyboard client.
- `phase1.py:35–46` imports the combined robot controller, Rust-based motor driver and policy loader. `policy.py:43–52` builds a float32 observation and calls the ONNX session. The old program is not a sensor-only daemon.
- The frozen `bundle/community/src/moves/walk.py` loads two CPU inference sessions and checks exact 61-input/14-output shapes, joint order and default pose. It does not call a “64-bit model.” The frozen upstream community commit is `49678215d0b40529522772a40c06c216390449dd`; the policy commit is `73a3f18a2e2e952b7de27d75ac74cbe183f28200` from `bundle-lock.json`. The prepared bundle contains a local 61-observation adapter, rather than unchanged community code.
- Existing `torso_imu.py` preserves separate quaternion/gyroscope freshness; its timestamp is the oldest required report's **Pi receipt time**, not the IMU sample time. Its `install_reader()` imports `robot_controller`, so sensor extraction must avoid that combined entry point.
- The scoped runtime search found no Camera Module 3 capture/forwarding implementation. The current handbook correctly records sensor transport, motor-bus ownership and fault-stop integration as unfinished.

## Reproduced dependency and model evidence

`check_dependency_wheels.py` queried the publisher's PyPI metadata for all six exact dependency pins. NumPy 2.2.6, ONNX Runtime 1.26.0 and rustypot 1.4.2 each have Linux AArch64 wheels, and **zero ARMv6 or universal wheels** in that index. Flatbuffers, packaging and protobuf have universal wheels. This rejects the historical publisher-wheel installation route for Zero W; it does not prove that every alternative source build is impossible. Third-party ARMv7 wheels would still not establish ARMv6 support. Full filenames, metadata hashes and fetch times are retained in [dependency-wheel-review.json](dependency-wheel-review.json). [ONNX Runtime installation documentation](https://onnxruntime.ai/docs/install/) describes installing its platform-specific runtime separately from the model.

`inspect_models.py` loaded the actual frozen `walk61.onnx` and `stand61.onnx`. Both have float32 inputs `[1,61]`, float32 outputs `[1,14]`, and ten FLOAT initializers; both returned finite values for a single zero observation on the Mac CPU. The local test used ONNX Runtime 1.24.4 and is a model-loading smoke test, not qualification of the pinned 1.26.0 deployment or a walking trial. Hashes and exact results are in [model-inspection.json](model-inspection.json). ONNX represents typed tensors and computation graphs; those tensor types are separate from the CPU instruction-set width. [ONNX concepts](https://onnx.ai/onnx/intro/concepts.html)

Moving unchanged actors onto the Mac therefore preserves their weights, observation ordering, units and action scaling. Numerical regression on recorded observations is still required when changing runtime versions. Retraining becomes relevant if observations, robot dynamics, action definitions or sensing delay change enough to violate the trained contract. The jaw experiment already uses privileged simulation target/contact/support/lift state; replacing those with real camera/state estimates requires observation adaptation and possibly new training regardless of whether the Pi has a 32- or 64-bit CPU.

## Concrete sensor-only preparation

[sensor-profile.json](sensor-profile.json) separates the Pi dependency set from policy and actuator dependencies. [check_sensor_environment.py](check_sensor_environment.py) reads board identity, Python pointer width and module availability without opening any devices. It deliberately returns failure on the current Mac. It does not install software or open the camera, IMU or motor port.

For the original Zero W, use Raspberry Pi OS Lite 32-bit and install the matching `python3-picamera2`/`python3-numpy` OS packages. A Python environment with `--system-site-packages` can reuse the matching libcamera bindings. The manufacturer supports Picamera2 on 32- and 64-bit Raspberry Pi OS and down to the original Zero, while explicitly noting lower performance on less powerful boards. It recommends APT so Picamera2 and libcamera versions agree. [Picamera2 installation documentation](https://github.com/raspberrypi/picamera2#installation)

The configuration records a provisional 640×480, 15 fps H.264 measurement profile. Hardware H.264 encoding is available through the Raspberry Pi camera software when supported; this profile has not been measured on the user's board. Frame sequence, capture timestamp and its clock domain, exposure duration, Pi send time, Mac receive/decode time and dropped-frame counts must be carried through the real forwarder. Pi and Mac monotonic clocks cannot be subtracted directly. [Official camera software and encoding documentation](https://www.raspberrypi.com/documentation/computers/camera_software.html#rpicam-vid)

This review implements the dependency split profile and preflight, **not the missing sensor forwarder or motor-control migration**. The remaining implementation is concrete:

1. Extract the existing BNO085 reader and mount-calibration transform into a sensor-only process, with no `robot_controller`, `rustypot` or policy imports; preserve separate gyro/quaternion freshness.
2. Add camera capture and bounded latest-frame transport, associate camera metadata with decoded frames, and establish clock mapping rather than treating receipt time as capture time.
3. Run the existing policy adapter on the Mac with the exact observation/action contract. Choose one motor-bus owner and implement the command/observation protocol and local expired-command stopping; remote computation must not remove local bus safety.
4. Measure sustained capture/encode/transfer/decode latency, observation age and jitter alongside IMU traffic. Test delayed frames, stopped camera/IMU and lost commands before motors are enabled for policy trials.

No live Zero W has been connected for this review. Camera acquisition, transport timing, physical sensor orientation, motor access, stop behavior and real visual pickup remain unvalidated. The review is not a complete-project or hardware commissioning acceptance.

## Reproduce without hardware

From the MicroDuck repository root:

```sh
python3 build-pack-20260913/redesign-20260913/software-board-review-20261008/check_dependency_wheels.py
microduck_rl/.venv/bin/python build-pack-20260913/redesign-20260913/software-board-review-20261008/inspect_models.py
python3 build-pack-20260913/redesign-20260913/software-board-review-20261008/check_sensor_environment.py
```

The first command reads public package metadata; the second uses the existing local ONNX environment; the third is expected to exit 2 on a Mac or incomplete Pi setup. None opens robot hardware. A passing preflight only establishes its software checks, not streaming or control performance.
