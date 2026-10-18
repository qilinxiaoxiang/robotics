# First power-up and electrical acceptance

**Current Phase 1 build:** use the [Phase 1 handbook](../phase1/START-HERE.html). This earlier full-feature design remains a component reference. Its onboard battery, regulators, camera and audio instructions are deferred; use the Phase 1 power recipe and 85-instance print list for the current build.

**No hardware test has yet been performed. There are 15 servos total, including jaw ID15.** These are executable commissioning steps and project screening thresholds, not manufacturer certification. Printing and gait simulations do not replace electrical measurements.

## Instruments and records

- A current-limited DC bench supply covering 6.6–8.4V. Begin with the logic regulator alone at a 0.5A input limit; confirm no short, then increase deliberately. High-load tests need an adequate bench source or the real battery after preliminary checks.
- A multimeter for polarity and steady voltage. Use an oscilloscope for Pi/servo endpoint transients and a current probe or suitable shunt for battery/servo-rail current. Record at least 100kSa/s for claimed transient coverage, with probe locations, bandwidth and sample rate. A slow USB meter cannot clear startup peaks.
- Thermocouples or calibrated thermal imaging for battery, both boards, adjacent PLA, fuses, wires and connectors. Touch is not a temperature record.
- A body support/fixture allowing limited leg movement. Disable automatic restart. External supply leads must not support or pull the robot during a claimed free-walking result.

[measurements-template.json](measurements-template.json) contains six phases, all currently empty. Keep original waveforms and measurement provenance. Continuous current means a stable-segment average; record peaks and duration separately. The summary checker cannot certify probe placement, thermal stabilization or fault response.

## With the battery disconnected

1. Identify VIN, the separate VOUT rails and common ground. Verify no unintended metallic short between the two 5V outputs; disconnect loads when semiconductor paths make continuity ambiguous.
2. Verify EC2 polarity. F0 10A belongs before the split; F9 3A before small-board VIN; F1–F8 on the servo output; F10 0.5A at the small-board audio branch origin.
3. Open each motor fuse branch and confirm that group's VDD is isolated. DATA-only links must not bypass power fuses. OpenRB's reference ground is a separate intended connection.
4. Verify OpenRB DXL Pin2 is disconnected from motor power; speaker OUT− is not grounded; BNO085 VIN is Pi 3.3V.
5. Inspect insulation/strain relief. Keep solder spikes, screws and fuse leads away from the soft battery. Move each joint through the intended range without taut, pinched or rubbing cables.
6. Verify custom USB wiring: POWER has Micro Pin1 +5V / Pin5 GND only; DATA HOST additionally has D−/D+ on pins2/3 and ID pin4 joined to pin5. Preserve the C end and differential pair. Check every conductor and adjacent short.

Do not test fuses by deliberately shorting the battery. Use a controlled electronic load and the manufacturer's time-current data if characterizing protection behavior.

## Incremental power-up

1. **Regulators only:** start at 7.4V with large-board ENA disabled. Use the #5671 ENA pin, with ENB/PFM left open. Verify small-board output polarity/voltage, then enable and check the large board. Sweep 8.4/7.4/6.6V input.
2. **Logic only:** add Pi PWR IN first, without OpenRB/camera. Measure between Pi physical Pin2 and GND Pin6. Add OpenRB, IMU and camera, checking enumeration and acquisition separately, then run real 61D inference, camera compression, Wi-Fi and duck-call audio together. Complete 30 minutes of stable USB communication and record disconnects/re-enumerations/errors.
3. **One supported servo:** begin torque disabled. Read mode, ID, voltage and temperature. Use a slow small movement around the measured actual position; do not jump to an unknown zero.
4. **All 15 powered, torque off:** check every endpoint and unique ID, including ID15. The 0.255A total standby specification is a comparison point, not an assumed tolerance or a substitute for measurement.
5. **Supported startup/stop:** use the installed startup ramp and the [supervised launcher](runtime-supervisor/README.md). Record Pi and far servo voltage, rail/battery peak currents and duration. Test requested stop, program exceptions, serial disconnection, stale IMU, tilt and the physical ENA switch. A failed bus may prevent torque-off; do not depend on software alone.

The supervisor adds 10Hz current transactions. Measure their actual duration and the complete 50Hz loop before walking. The previous gait tests did not include this hardware timing. A successful write is not proof of disabled holding torque; check register 64 and observed motor effort during commissioning.

## Read-only servo snapshot

With the body supported and any controller stopped, use an independent Pi environment:

```sh
python3 -m venv .probe-venv
.probe-venv/bin/python -m pip install dynamixel-sdk
.probe-venv/bin/python probe_servos.py --port /dev/ttyACM0 --ids 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15 --output first-servo-snapshot.json
```

Use the actual enumerated port. This tool writes no torque, target, ID or mode. It reads mode, limits, startup configuration, shutdown mask, P gain, watchdog, input current, voltage, temperature and torque-enable state. Exit 0 means all requested registers were read; any communication/device error returns 2. Sequential reads cannot capture current peaks and must not compete with the walking program for the serial port.

Verify all 15 IDs, 0.1V voltage units and signed 16-bit 1mA current units. Walking uses P gain 200; startup/shutdown may restore a different gain, so label each snapshot's phase. Mode3 does not make `Current Limit` an active hardware clamp. Changing to mode5 changes control behavior and requires separate motor/gait validation. Verify watchdog and startup behavior physically instead of inferring torque-off from the presence of a register. The old scheduler's 15A current proxy is not measured battery current.

## Six load phases

- `logic_boot`: all electronics fitted; at least ten cold starts. Record inrush and resets.
- `idle_torque_off`: all 15 servos unpowered in torque terms, for five minutes; camera/audio as documented in the record. Measure idle current and regulator self-heating.
- `supported_start`: at least ten startup/stand/stop cycles under support. Exercise head and jaw separately through small approved movements; capture peaks and timing.
- `stand_10min`: weight-bearing standing for ten minutes in the actual enclosure. Stop early for the battery limit and record duration; do not merge separated runs into a continuous thermal-stability claim.
- `walk_camera_audio_10min`: approved speed command plus compressed single-camera Wi-Fi video, audio and a documented small jaw cycle. Stop at the battery threshold or ten minutes, whichever occurs first. Record thermal trend and control timing.
- `controlled_obstruction`: supported, one servo, low output and a controlled fixture. Begin with an event shorter than 100ms; verify response before increasing. Do not hand-grip the shaft or block all 15 servos. Record threshold, physical response delay and residual effort. The software's slower current polling is not an instantaneous protection limit.

Capture Pi and all 15 servo endpoints, moving probes and repeating controlled events if needed. Avoid creating an unintended current path through oscilloscope grounds; use suitable differential probes or an explicit single reference.

## Pass and stop thresholds

- Pi endpoint **4.8–5.25V**, including transients; no reset, camera interruption or USB re-enumeration. Zero's lack of a low-voltage flag does not clear voltage.
- Servo endpoints **4.5–5.5V**. These are project margins inside the manufacturer's 3.7–6.0V range. Inspect deceleration overshoot; stop immediately near or beyond 6.0V.
- Each battery cell **3.3–4.2V**. Plan to stop around 3.5V per cell under load; the fixed 3.3V alarm is backup. Total voltage alone does not expose imbalance. Do not proceed with abnormal cell imbalance or a damaged/swollen pack.
- Initial continuous limits: battery input≤7.5A, logic output≤2.5A, each 3A motor group≤2.25A, fused audio≤0.375A. Temperature may require more derating. Evaluate pulses by magnitude, width and energy; continuous limits alone do not classify them.
- Initial temperature screen: battery≤45°C, nearest PLA≤45°C, wire/connector/fuse area≤45°C, regulator hotspot≤70°C, servo reported temperature≤60°C. Stop for rapidly increasing temperature, repetitive protection resets, odor or deformation.
- Actual stop: ENA must remove servo output. A fault must not automatically re-enable torque. Record physical response delay for disconnect, overload and tilt, and distinguish a sent torque-off request from actual response. The current launcher has no independent watchdog or per-cell cutoff.

The numerical checker evaluates declared summaries only:

```sh
python3 check_power_measurements.py actual-measurements.json --output power-acceptance.json
```

An observed violation returns `FAIL`; missing evidence returns `NOT_MEASURED_OR_INCOMPLETE`; complete summaries within limits return `PASS_DECLARED_MEASUREMENTS`. Review original waveforms, stop behavior and wiring photos separately. Synthetic test records must never be submitted as physical results.

## Charging and measured runtime

Use the selected adjustable HOTA T6 balance charger with its external DC/USB-C PD supply. For this ordinary 2S LiPo select **0.8A**, no more than 1C=0.85A, and 8.4V final voltage. Connect the intact GEAX6F2E2M to the main charging output and connect the 2S balance lead. Do not use LiFePO4/LiHV mode, reverse-charge through Pi/regulators, or charge the installed robot. [Battery instructions](https://genstattu.com/bw/)

Remove the battery, disconnect onboard wiring and remain present during charging. Follow manufacturer storage instructions afterward. For runtime testing, start with verified charge/balance and record workload, duration, battery-side Wh, maximum temperature and per-cell stopping voltage. A supervised alarm and a session timer do not make unattended battery depletion acceptable.
