# Historical Phase 2 reference — not a purchasing route

The active build is [Phase 1 single-source revision](../phase1/START-HERE.html). The battery, two-regulator, charger and related figures below are retained only as history. Do not use them to buy or wire Phase 1.

# MicroDuck power design verification

**Phase1nowuses the [current illustrated handbook](../phase1/START-HERE.html): complete15-servo tethered walking/pickup with Mean Well5V6A motor supply. Camera,audio,onboardbattery,regulatorsandcharger remainPhase2holds. The material below is earlier design/reference evidence and is not the current shopping instruction.**

Verified 2026-09-13, America/New_York. Advances P5, serviceable onboard hardware, and P6, first-power testing and failure response. **This design has 15 XL330 servos in total, including one jaw servo, ID15.**

**Earlier onboard-power design: purchasing remains deferred.** Read [PURCHASE-READINESS.md](PURCHASE-READINESS.md) for the purchasing decision and the additional software repair. Simulations, dimensions and an attractive demonstration are not electrical measurements.

- [Battery and regulator cost decision](cost-review/README.md): selected replacement, rejected alternatives and mounting comparison.
- [Wiring and soldering](WIRING.md): exact parts, eight fused groups and 15 independent power injections.
- [First-power procedure](FIRST-POWER-TEST.md): instruments, probe locations, operating cases and stop thresholds.
- [Budget](power-budget.json), [inputs and explicit assumptions](power_inputs.json), [Pi margin sensitivity](purchase-margin.json).
- [Audit of prior simulation currents](prior-simulation-electrical-audit.json), [primary-source register](source-register.json).
- [Supervised launcher](runtime-supervisor/README.md): latched software stops with an explicit hardware boundary.
- [Current electrical acceptance](electrical-acceptance-current.json): `NOT_MEASURED_OR_INCOMPLETE`. Physical readings remain empty.

## Evidence and its limits

The prior repaired 45-case gait suite controls 14 joints. Its reported current proxy is `sum(abs(actuator torque))/kt`; case peaks range from 3.790 to 7.589A. That field excludes the jaw, Pi, camera, audio, IMU, OpenRB and conversion losses. It does not include a motor-PWM-to-supply-current model, battery state, regulator electrical transients or enclosure thermal simulation. Original files are preserved; the audit records paths, hashes and individual case values.

ROBOTIS, a Korean robotics manufacturer, states that XL330 `Present Current` measures input-power current. Actual readings therefore describe servo-rail consumption, not total 2S battery current. `Current Limit` applies to modes 0 and 5; setting it in position mode 3 is not a proven hardware current cap. The overlay's `BAM_MAX_CURRENT=1.47` is a model parameter, not evidence of a firmware current limit. [XL330 control table](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/#current-limit38)

## Fixed component choices

- **Gens ace GEA8502S60E2:** 850mAh, 2S, nominal 7.4V, EC2. Gens ace is an RC battery brand of Grepow. Fully charged 2S is 8.4V and must not reach the Pi or servo rail directly. Published dimensions are 58×32×20mm with ±5/2/2mm tolerance, giving a 63×34×22mm maximum box. Published mass is 57g ±20g. The 60C label gives 51A by arithmetic; it does not establish this robot's actual pulse current, internal resistance or temperature. [Manufacturer](https://www.genstattu.com/gens-ace-850mah-2s-60c-7-4v-lipo-battery-ec2-plug-car-classic-non-g-tech/)
- **Pololu D42V110F5, #5671:** fixed 5V servo regulator, ±3%, $59.95. The manufacturer curve is approximately 15A at 6.6–8.4V input in room-temperature still air; the budget uses a conservative 14A screening ceiling. Its advertised 11A point is at 42V input. It replaces #2881 for $20 less with the same mounting pattern and lower top profile. Ground ENA to disable; leave ENB/PFM open. [Product](https://www.pololu.com/product/5671), [selection and geometry evidence](cost-review/README.md)
- **Pololu S13V30F5, #4082:** fixed 5V, ±3%, typical 3A, approximately 5.1A output limit. It supplies Pi, camera, USB-powered OpenRB and audio. Initial continuous logic-rail budget is 2.5A. Pi's worst-case endpoint voltage still requires screening. [Manufacturer](https://www.pololu.com/product/4082)
- **OpenRB-150:** USB powers its communication logic; servo power bypasses its DXL supply path. All onboard DXL power ports together are rated 3A, while the USB path has a 500mA fuse. Resetting OpenRB does not turn off this design's external servo rail. [Manual](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/)

Keep the two 5V outputs separate. Grounds share a power-distribution reference. Leave regulator cooling surfaces exposed; do not heat-shrink the whole board or press the battery against a hot component.

## Load assumptions, including the jaw and simultaneous audio/video

XL330-M288 stall current at 5V is 1.47A each: **15 servos require 22.05A, or 110.25W, in the simultaneous-stall arithmetic case**. This must trigger a stop, not sustained operation. Standby is 17mA each, 0.255A total; holding an upright robot is not that standby condition. [Servo specifications](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/#specifications)

Raspberry Pi lists 350mA typical bare-board activity for Zero 2 W and a generic 250mA camera allowance. The latter is not a Camera Module 3 Wide peak measurement. Actual 50Hz inference, camera compression and Wi-Fi current remains unknown. Adapter current ratings are not device consumption. [Pi power documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply)

Adafruit, a US open-source electronics supplier, provides #3006 MAX98357A and #3923 8Ω/1W speaker. Analog Devices lists approximately 2.4mA idle and 92% efficiency at 8Ω/1W, giving about 0.217A at 5V for that output. The amplifier can exceed the speaker's rating: fit 100kΩ between GAIN and VIN for 3dB gain and limit software volume. Verify audio-equivalent differential output below 2.83Vrms. [Amplifier IC](https://www.analog.com/en/products/max98357a.html), [gain wiring](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/pinouts), [speaker](https://www.adafruit.com/product/3923)

The BNO085 chip's indexed manufacturer data gives approximately 34.41mW at 100Hz fusion, but complete breakout current is not specified. This budget instead explicitly allows 25mA at 3.3V for the breakout and folds it into logic-rail consumption. The source register records the direct-PDF access limitation. [CEVA datasheet](https://www.ceva-ip.com/wp-content/uploads/2019/10/BNO080_085-Datasheet.pdf), [breakout wiring](https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/pinouts)

The following are assumed DC rail loads, not measured runtimes. Each logic figure already includes Pi, camera, OpenRB, IMU and audio as applicable.

- Relaxed idle: servo rail 0.255A, logic 0.48A; battery 0.47–0.67A, approximately 56–78 minutes.
- Standing: 14 joints 1.5A plus jaw 0.017A, logic 0.9A; battery 1.51–2.24A, approximately 17–24 minutes.
- Light walking: 14 joints 2A plus jaw 0.1A, logic 1A; battery 1.94–2.88A, approximately 13–19 minutes.
- Design walking: 14 joints 3.5A plus jaw 0.3A, logic/audio/video 1.4A; battery 3.26–4.85A, approximately 8–11 minutes.
- Heavy load: 14 joints 6A plus jaw 0.6A, logic 2.5A; battery 5.70–8.48A, approximately 4–6 minutes. The pessimistic point exceeds the main-fuse continuous design envelope, so this is not an accepted continuous mode.
- Startup scan point: 14 joints 8A plus jaw 0.5A, logic 2.5A; battery 6.89–10.28A. Actual duration and inrush are unknown.
- All 15 blocked: servo rail 22.05A, logic 2.5A; maintaining voltage would theoretically require 15.38–23.11A at the battery. Stop instead.

Calculation uses 6.29Wh nameplate energy, 65–80% usable energy, 6.6/7.4/8.4V input, 80–95% servo-regulator efficiency and 85–95% logic-regulator efficiency. Input power is `max(Pout/efficiency, Pout + Vin*Iq)`, preventing double-counting static loss already included in efficiency. Static-current floors use a conservative 10mA servo-board allowance and a typical 20mA logic-board allowance, not guaranteed maxima. Wiring/fuse/contact losses, temperature, ageing, imbalance and remaining capacity at cutoff are excluded. Measure actual runtime using battery-side energy integration and per-cell stop voltage.

## Repairs and remaining boundaries

- Fifteen individual power tails replace power daisy-chaining through the first servo. Assessed endpoint voltage improves from 4.398V in the previous supply/wiring to 4.583V with independent tails and the new regulator tolerance; hot wiring and actual joints remain unmeasured.
- Eleven small axial fuses replace the oversized automotive holder: one 0251010.MXL 10A, nine 0251003.MXL 3A, one 0251.500MXL 0.5A. Finished insulated design envelope is 24×5×5mm each. The current assembly provides a two-level 6+5 carrier. [Fuse data](https://www.littelfuse.com/assetdocs/littelfuse_fuse_251_253_datasheet.pdf?assetguid=f47a0bb7-8ede-4679-9646-7114c3787688)
- Applying initial 75% current derating at 25°C gives 7.5A battery, 2.25A fused-group and 0.375A audio targets. Temperature and pulse duration require further assessment. Fuses protect faulted wiring; they are not instantaneous motor-current clamps. [Selection guide](https://www.littelfuse.com/assetdocs/fuseology-selection-guide?assetguid=fa4aa360-f6c4-4eec-88a6-3d7ec3fe57d5)
- At the small regulator's 4.85V tolerance floor, Pi's 4.8V requirement leaves only about 22mΩ for a 2.25A branch. The 200mm 20AWG loop alone uses approximately 13mΩ. Test a short cable and actual loaded board; do not parallel outputs. Zero models lack the usual low-voltage detection, so `get_throttled=0` is not proof of adequate voltage. [Pi documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply-warnings)
- At the design walking assumption, large-board heat is about 1–4.75W and small-board heat about 0.37–1.24W. Large-board heat can reach about 8.25W in the heavy case. Unknown enclosure thermal resistance prevents a temperature conclusion. The initial adjacent-PLA screening limit is 45°C.
- HobbyKing DL-Volt-Alarm adds a 3.3V per-cell audible backup warning, 38×25×11mm, 7g. It is not automatic cutoff, and remains connected through the balance lead after EC2 is removed. [Alarm](https://hobbyking.com/en_us/hobbykingtm-lipoly-low-voltage-alarm-2s-4s.html?___from_store=en_us), [battery care](https://genstattu.com/bw/)
- Regenerative deceleration needs a measured overshoot check below 5.5V. An arbitrary 5V TVS can clamp well above 6V. Select a precision discharge circuit only after measuring pulse energy and checking its geometry/heat. [Pololu explanation](https://www.pololu.com/category/249/shunt-regulators)

A capacitor does not fill a sustained-current deficit. Supplying an additional 5A for 20ms with at most 0.25V droop requires `C=I*dt/dV=0.4F` ideally, before ESR.

## Reproduction

From this directory:

```sh
python3 calculate.py
python3 purchase_margin.py
python3 test_design_checks.py
python3 check_power_measurements.py measurements-template.json
```

The budget and 16 synthetic design/data-gate checks run without hardware. The last command should exit 2 because physical evidence is missing. The new supervisor has a separate 19-test fault-injection result. The read-only servo probe additionally needs `dynamixel-sdk`; see the first-power procedure.

New fuses, alarm, switch, cables and supports need their own final measured mass and installed checks. Do not attribute them to the earlier 45 gait cases. Original geometry, ONNX and simulation files have not been changed by this power review.
