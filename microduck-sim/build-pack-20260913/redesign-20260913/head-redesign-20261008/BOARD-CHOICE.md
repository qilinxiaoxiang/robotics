# Board choice for the restored curved head

Problems P0/P5/P6. Verified 8 October 2026. This is an engineering selection for the next layout, not a claim of tested streaming performance.

## Decision

Prefer the existing first-generation Raspberry Pi Zero W with its soldered 40-pin header for onboard integration. Keep the available Raspberry Pi 3 Model B V1.2 as a bench/debug alternative. Do not buy Cubie A7Z on current evidence.

The MacBook Pro remains the control/policy computer. The onboard board captures sensors and forwards observations. This makes camera compatibility, sustained observation age, populated-board fit and power more relevant than peak CPU or NPU throughput.

## 32-bit compatibility and the existing model

The first-generation Zero W uses the 32-bit ARMv6 architecture; Zero 2 W and Pi 3 support 64-bit ARMv8. These describe the processor instruction set, not the precision of the model's weights. The [official architecture explanation](https://www.raspberrypi.com/news/raspberry-pi-os-64-bit/) distinguishes these families. The [current OS download page](https://www.raspberrypi.com/software/operating-systems/), checked 8 October 2026, offers a compatible 32-bit Lite image and explicitly lists Zero W for the Legacy 32-bit family.

Use a Zero-compatible 32-bit OS and compatible camera/sensor dependencies on this board. An arbitrary package labelled `armhf` can still require ARMv7; a 64-bit `aarch64` executable cannot run on the original Zero. Prefer the matching Raspberry Pi OS camera packages instead of attempting to install the old ARM64 inference environment on the board.

Our architecture decision keeps policy execution on the Mac. Consequently, changing the sensor board to Zero W does not by itself require retraining or reducing the model. It requires separating sensor acquisition/transport from the old combined Pi controller, and matching the Mac's inference environment to the Mac. `phase1/runtime/requirements.txt` still includes ONNX Runtime for the legacy combined controller; it is not a supported Zero W sensor installation recipe. That migration and actual camera latency remain unfinished and must be tested after the board is connected. Bitness alone does not establish that the visual-pickup application works.

## Evidence and limits

- **Available hardware:** the user identifies IMG_6945 as a first-generation Zero W with a soldered 40-pin header and IMG_6944 as Pi 3 Model B V1.2. Factory-installed WH branding is not established and does not change the intended functional comparison. Physical operation is not established by identification.
- **Zero W:** the [official specifications](https://www.raspberrypi.com/products/raspberry-pi-zero-w/) identify a single-core 1 GHz CPU, 512 MB RAM, CSI camera connector and onboard wireless. The [official Picamera2 project](https://github.com/raspberrypi/picamera2/blob/main/README.md) supports boards down to the original Zero, with performance limitations on lower-powered boards. Use a headless capture/encoding path and do inference on the Mac. Library support is not a measured latency result.
- **Pi 3B:** [official specifications](https://www.raspberrypi.com/products/raspberry-pi-3-model-b/) provide a 1.2 GHz quad-core CPU, 1 GB RAM, Ethernet and four USB ports. These help debugging and simultaneous processes. The larger populated board and ports require a separate mounting layout; it is not an interchangeable Zero-sized part.
- **Cubie A7Z:** [official documentation](https://docs.radxa.com/en/cubie/a7z) lists a 65 x 30 mm board with A733 CPU, Wi-Fi 6 and an NPU. Its [supported-camera list](https://docs.radxa.com/en/cubie/a7z/hardware-use/mipi-csi) lists Radxa 4K, 8M 219 and 13M 214, not the owned Camera Module 3's IMX708. The [camera connector documentation](https://docs.radxa.com/en/cubie/a7z/accessories/camera-4k) specifies 31 pins at 0.3 mm pitch. Neither compatibility with the existing camera/cable nor autofocus/streaming support has been established. Absence from this list is not proof that a driver port is impossible.
- **Power:** A7Z [official guidance](https://docs.radxa.com/en/cubie/a7z/hardware-use/type-c) recommends a 5 V supply rated at least 3 A. That is supply-sizing guidance, not a measured constant 15 W draw; the current robot's shared supply and transient budget would require a new check.

## Evidence that would change the choice

Measure capture, hardware encoding, network transport and Mac decoding together on the Zero W with the actual Camera Module 3 Wide. Retain timestamps, frame gaps, CPU/memory load, throttling and stale-frame events under simultaneous IMU and required controller traffic. A diagnostic target such as 640 x 480 at 20 fps is a test setting, not a promised result or a substitute for closed-loop pickup acceptance.

Consider replacing the board if that test exposes a sustained bottleneck that cannot meet the control application's established observation-age budget. For A7Z, first establish the exact IMX708 driver/autofocus/cable path, populated-board and antenna fit, and loaded supply behavior. Extra CPU cores or advertised NPU TOPS alone do not meet those gates. A possible few-day delivery delay is user-reported; no stock, order or delivery promise is made here.

## Mechanical acceptance

The previous 65 x 30 x 1.6 mm Zero mesh is a PCB slab only. The restored-head layout must include the soldered male header, mated female housing, component-side space, camera and USB plugs, cable exits and removal paths. Keep these fit tests separate from live streaming and physical commissioning.

AI assistance was used to draft.
