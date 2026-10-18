# Supervised bench-run launcher

This optional entry wraps the existing community program without editing it. It requires the previously delivered **official 61D overlay, KP=200 and 5V model constants**. It includes all **15 servo IDs, including jaw ID15**, when reading current and requesting torque-off. It does not enable or move ID15 on its own; the walking model still outputs 14 joint commands.

## Behavior

Before position reads, torque enable and goal-position writes, the wrapper checks actual community IMU data and polls current at up to 10Hz. A 60° body tilt, invalid/nonfinite quaternion, invalid IMU state, host-receipt age above 100ms, current-read failure or session timeout latches a stop. Current screening trips after a 200ms observed dwell above 5.0A total, 2.25A in any fused group, or 1.3A in one servo. All 15 current samples are required. A serial library's unsigned 16-bit current representation is normalized before magnitude comparison.

A trip requests torque-off for IDs 1–15 and rejects subsequent enables/goals. The outer `finally` also requests torque-off after startup, model-loading and cleanup exceptions. SIGTERM is routed through that cleanup. A normal exit still requires the operator to switch EN off and disconnect the battery as appropriate.

These current limits are engineering screening values. They do not change operating mode or `Current Limit`, do not clamp current instantaneously, do not measure pack current, and do not guarantee detection of every blocked joint. A 100ms poll plus 200ms dwell has substantial software latency; blocking I/O can make it longer without a bound. The 5.0A total threshold corresponds to about 6.96A battery input only under the stated 6.6V / 80% servo efficiency / 2.5A logic / 85% logic efficiency assumptions, excluding wiring loss.

## Install and run on the Pi

Copy this whole `runtime-supervisor` directory next to the already-installed project. Do not overlay or delete community files. Stop any existing gamepad/keyboard service before starting a second controller. Set the community path to the directory containing its `src/` folder and use the project's existing Python environment:

```sh
python guarded_main.py --community /path/to/Microduck-build-tutorial/microduck --max-session-seconds 120
```

Run from this directory or use an absolute path to the launcher. The launcher rejects a walk source other than the frozen 61D adapter before opening hardware; do not bypass that check after an unreviewed source update. The original input selection and motor offsets remain unchanged. For keyboard input, set `MICRODUCK_INPUT=keyboard` in the environment as supported by the community application.

The 120-second limit is a supervised session limit, **not** a prediction of safe battery runtime. Do not configure a service to automatically restart the launcher after a trip. If IMU startup cannot produce valid data within two seconds, startup fails with a torque-off request instead of enabling motion.

To remove the overlay, stop this launcher and stop invoking it. No source restoration is needed because it changes no project file. The old entry does not acquire these checks automatically; returning to it restores the documented old behavior.

## Offline verification

Using an environment with the community Python dependencies, including NumPy and ONNX Runtime:

```sh
python test_runtime_guard.py /path/to/Microduck-build-tutorial/microduck
```

The test imports the real Observer, Scheduler, main and IMU conversion. It substitutes the hardware-opening class and the unused `placo` import; it does not open serial, I²C or GPIO. Nineteen tests cover tilt, stale/invalid IMU, time limit, jaw/group/total current, signed current, missing readings, failed stop transmission, latched re-enable, actual scheduler cleanup, and a model-load exception after the actual main has enabled torque. Results are in [offline-checks.json](offline-checks.json).

No additional ONNX forward or physical gait claim is made by this test; the earlier overlay's separate ONNX validation is unchanged.

## Limits to verify physically

- The IMU age is the host's receipt age, not sensor sampling latency. Body orientation still depends on correct trunk placement and the mount quaternion.
- Extra current reads can increase the 50Hz control-loop delay. Record transaction duration, actual loop timing and the original gait-delay acceptance before walking; current register reads are not oscilloscope peak measurements.
- A torque-off write is a request, without a guaranteed acknowledgment. Check register 64 and actual effort during commissioning. A bus failure, SIGKILL, process hang or Pi power failure may prevent delivery. This is not an independent watchdog or EN driver.
- There is no raw battery-cell input or automatic low-voltage disconnection. Wi-Fi connection loss is not separately detected by this wrapper. The physical EN switch and EC2 remain necessary for the attended bench workflow.

The new wrapper source is MIT licensed. It imports, rather than copies, the community GPL-licensed implementation; the community project retains its own license. This does not alter the prior overlay or policy licenses.
