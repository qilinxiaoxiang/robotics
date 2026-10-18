# Motor-bus ownership and the crown USB opening

Reviewed 2026-10-09. Scope: P5/P6 architecture and assembly dependency review. Read-only investigation; no wiring, firmware, runtime, CAD, procurement, or hardware changes were made.

The Pi-to-OpenRB USB link is part of the older implemented controller arrangement, but it is **not an established requirement of the user-confirmed phase-one architecture**. The confirmed arrangement puts control and policy on the Mac and sensor acquisition/forwarding on the Pi. Its motor-bus owner is explicitly still to be defined. The crown opening must therefore not be justified as an unavoidable requirement merely by citing the old wiring ledger.

## Canonical intent versus implemented behavior

`microduck-sim/PROJECT-CONTEXT.json`, `phase1_compute_intent`, records the user's 2026-09-29 clarification: the Mac runs control and policy; the Pi acquires and forwards sensor measurements. Its `precedence` explicitly supersedes the earlier Pi-local inference / Mac keyboard-client split. Its `implementation_status` says migration and physical validation remain incomplete. Its `acceptance_needed` explicitly includes selecting the motor-bus owner, sensor transport, observation-age/jitter/loop timing, and stale-data/lost-command stopping.

The existing executable arrangement is different:

- `build-pack-20260913/phase1/runtime/mac_control.py:24–27` starts `phase1.py run` on the Pi through SSH. The Mac process sends keyboard commands and heartbeats; it does not itself open the motor serial port.
- `phase1/runtime/phase1.py:35–39,78` installs the IMU reader and creates `RobotController(serial_port=a.port, timeout=.03)` in that remotely launched process.
- `phase1/runtime/bundle/community/src/robot_controller.py:29–36` creates `rustypot.Xl330PyController` and starts a local `ThreadedIMUReader`. Its automatic port resolver at lines 13–23 searches Linux device names. Explicit serial-port selection is supported, but it does not decouple the local IMU or implement remote sensor transport.
- `phase1/runtime/README.md:3` already marks the older architecture as superseded and says the split runtime is not implemented/tested.

Thus the existing combined runtime has a Pi-side bus owner. The desired migrated phase-one runtime has no accepted owner yet. Simulation training acceptance does not establish ownership or timing on real hardware.

## Direct OpenRB-to-Mac USB: supported for commissioning, not yet a migrated control runtime

This direct connection is an existing project configuration, rather than a newly invented electrical capability. `phase1/assembly-audit.md:57–65` and `phase1/START-HERE.md:125` instruct connecting OpenRB directly to the Mac for DYNAMIXEL Wizard, disconnecting the Pi USB connection, and avoiding competing bus owners. Those instructions distinguish Wizard commissioning from the older walking runtime and tell the operator to reconnect to the Pi afterward. `phase1/runtime/assign_id.py:15` also recognizes macOS `/dev/cu.usbmodem*` ports.

The manufacturer's [OpenRB-150 manual](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/) documents the factory `usb_to_dynamixel` bridge and operation up to 1 Mbps. [DYNAMIXEL Wizard 2.0 documentation](https://emanual.robotis.com/docs/en/software/dynamixel/dynamixel_wizard2/) explicitly supports macOS. These sources were checked on 2026-10-09. Neither establishes that this project's complete real-time Mac-policy/Pi-sensor stack has been migrated or commissioned.

Using the Mac as the operational bus owner is consequently a plausible continuation of an already documented commissioning connection. It still requires a deliberate software change: separate the controller from local Pi I2C access, provide timestamped sensor transport, resolve the Mac serial device, preserve one bus owner, and validate stopping and timing. An explicit-port argument alone is not sufficient. No device was connected or commanded during this review.

## What the head USB currently serves

`redesign-20260913/design-contract.json`, `connections` entries `pi_usb` and `openrb_usb`, describes Pi Micro-B **USB/data** port → SC0727 Micro-B male / USB-A female OTG adapter → Adafruit 4472 USB-A male / OpenRB USB-C cable. The recorded role is motor commands/feedback plus OpenRB logic power.

This is separate from the other head connections:

- Camera: SC1892 CSI cable carries camera data and power.
- Audio: Pi physical pins 12/35/40/20 feed MAX98357A BCLK/LRCLK/DIN/GND. Two amplifier output wires feed the speaker. Audio does not require this USB adapter.
- Pi input power: the ledger uses header pins 2/4 and 6/14; this OTG cable is not the Pi's own power input.

The same contract records a `[25,18,8]` mm USB receiving envelope and `usb_plug_vendor_dimensions_verified:false`. That ledger is a conservative packaging assumption, not exact SC0727 connector CAD. The separate roof-geometry review owns whether that envelope or the actual plug requires the opening; this software review does not certify connector fit.

## Consequence for the opening decision

If the Mac is chosen as motor-bus owner while the Pi remains a sensor forwarder, the Pi-to-OpenRB USB link is no longer required for motor transport. That removes the architectural reason for its Pi-side crown exit; it does not by itself prove the final replacement cable path or release a CAD revision. OpenRB would instead retain a direct USB connection to the Mac, with its logic power, common reference, external cable/service access, and single-owner behavior checked under that arrangement. Motor power remains a separate supply requirement; the manufacturer's USB capability is not evidence that Mac USB can drive the motor load.

Do not confuse this hybrid arrangement with the old `compute-review.md` **no-Pi** alternative. Retaining the Pi for CSI camera and I2C sensor forwarding does not require replacing those sensors with USB devices or moving IMU firmware onto OpenRB. The old no-Pi rejection therefore does not rule out Mac-owned motor USB.

Decision-changing evidence would be a current, accepted runtime/transport contract selecting the Pi as motor-bus owner, or a measured constraint that requires it. Neither was found in the current canonical context and implemented sources. Until an owner is selected and its migration checked, label Pi-to-OpenRB USB as a legacy implementation dependency, not a phase-one architectural necessity.

No battery decision was reconsidered. No physical-fit, electrical commissioning, or full-project acceptance is claimed.
