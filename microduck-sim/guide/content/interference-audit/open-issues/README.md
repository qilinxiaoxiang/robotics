# MicroDuck open issues before build and first run

Checked 2026-10-10 against the V1.7 guide (`guide/content/steps.py`, `guide/data/guide-data.json`) and the current interference-audit outputs. Problem IDs P5 and P6.

Five issues stop the build or the first walk, and none of them needs a new print. They need a soldering plan that keeps every Pi-end wire solder-free, a different Pi software path, a target clamp in the runtime, a solder-free Pi 5 V supply, and one cut trace on the USB-PD receiver. The Pi supply works without soldering if the 22 AWG pair runs into the head and meets one jumper end per pole in a lever connector; an all-jumper run sags below the Pi's 4.75 V floor. The jaw flex fit is marginal only when the builder spreads the arms 5 mm and 2 mm as the guide says. Spreading them with equal force keeps the layer stress below the PLA interlayer strength, so that fix is a text change too. No issue here requires reprinting a part unless a part actually cracks.

Two topics are covered elsewhere and are not studied here: the head cap and Pi header connection (including the old "pin40/cap" residual), and the printed power support versus the left shin (including tray versus leg clearance).

## Order of severity

Blocks the build or the first walk:
- **OI-01 Soldering.** The guide asks for 58 solder joints, 13 of them on wires that end at the Pi. Shawn cannot solder reliably. All 13 Pi-end joints can go; about 22 torso and board joints still need a helper.
- **OI-02 Pi software.** The software the guide tells you to install cannot run on a Pi Zero W, because ONNX Runtime has no ARMv6 build.
- **OI-03 Walking stops itself.** In all 33 simulated walks the runtime guard stops the robot 0.30 to 0.62 s after the walk command, because the policy commands hip roll beyond its ±0.384 rad limit.
- **OI-04 Pi 5 V supply.** An all-jumper supply leaves the Pi at about 4.58 to 4.69 V while walking. That is below the 4.75 V floor, and the run has unlatched joints in the moving neck loop. The guide's first-power check also fails a correct harness.
- **OI-05 USB-PD current setting.** Adafruit's wording implies the receiver ships with its ISET jumper closed, selecting 1.25 A and capping the robot at about 25 W (check the board). The guide never says to cut the jumper.

Risk of damage:
- **OI-06 Jaw flex fit.** At the guide's 5 mm and 2 mm spread, the stress across the layers in the thinnest part of the −Y arm reaches the PLA interlayer strength. Spreading both arms with equal force leaves margin.
- **OI-07 Runtime current screens.** The 1.3 A per-servo screen may stop the robot at gait start. The fused-group screen does not match the guide's fuses.

Low severity, wording or commissioning:
- **OI-08** The J12 pad labels conflict between the guide and the ROBOTIS render.
- **OI-09** The bench test asks you to "plug" a solder-cup XT30 onto bare wire.
- **OI-10** "Nothing in this guide needs a new purchase" becomes false if any solder-free part is bought.
- **OI-11** PROJECT-CONTEXT records a Pi USB motor bus; the guide uses the J12 UART.
- **OI-12** The old head residuals in PROJECT-CONTEXT are stale.
- **OI-13** A few fits are unmeasured: leg force-fits, the trimmed tray rail, the 0.2 mm cap seam and the jaw stop at 40°.

## Blocks the build or the first walk

### OI-01 The guide needs 58 solder joints; Shawn cannot solder

- **What goes wrong.** The guide asks for 58 solder joints. The 13 in step gpio sit on wires that end at the Pi. Several of the others are hard even for a practised hand: 2.0 mm J12 pads beside 3.3 V and GND, castellated converter pads, XT30 solder cups and multi-wire 16 AWG nodes.
- **Evidence.** In `guide/content/steps.py`, the gpio step (line 794) says "strip 5 mm from the wire and from a jumper half, twist them together, solder". The other joints are in uart-wires (263), pd-tether (280, 282), dfr-leads (297 to 299), junction (315, 316), splices (332), converter-plug (454), imu-board (533), speaker (753) and amp (767, 768). The per-joint inventory is in `issues.json` under OI-01.
- **Severity.** Blocks the build for Shawn.
- **Fix.** No wire that ends at the Pi gets soldered. Each ends in a ready-made female jumper sleeve:
  - **Pins 1, 3, 5, 9 (IMU).** Do not cut the Adafruit 4397 cable. It already ends in female sockets ("premium female headers", adafruit.com/product/4397). Plug male-to-female extension jumpers into those sockets. This removes 8 mid-cable splices and 4 Pi-end joints. Stagger the extension housings so the bundle still passes the 6.7 mm notch.
  - **Pins 8, 10 (UART).** A helper solders the cut end of a female jumper half into J12, at the OpenRB end. Extend it with a male-to-female jumper.
  - **Pins 2, 6 (Pi power).** See OI-04: 22 AWG into the head, a lever connector, and one cut 26 AWG jumper end per pole.
  - **Pins 4, 12, 14, 35, 40 (amplifier).** A helper solders the 7-pin header that ships with the MAX98357A. Female-to-female jumpers then run from that header to the Pi. The other route is a Pimoroni Audio Amp SHIM (purchase, "No soldering required"). It drops the 0.5 A fuse and the gain resistor, and its fit under the 13 sleeves is unchecked.
- **What still needs a helper.** About 22 wire joints:
  - in the torso harness: the converter pads (4), the 10 A fuse (2), the J nodes and their fuses (6), the servo-link splices (6) and the XT30 male (2);
  - on the OpenRB: J12 (2).
  - Also helper work: the XT30 female on the tether (2, or buy a pre-wired pigtail), the speaker tabs (2), and the amplifier header plus gain resistor and 0.5 A fuse.
  - Lever connectors could replace the fuse and splice joints electrically. They are larger than the modelled J box (8 × 12 × 6 mm against 13.1 × 18.6 × 8.3 mm for a WAGO 221-412), so treat them as a fit trial only.
- **Per-joint inventory.** All 58 joints are listed in `evidence/solder-ops.json` and in `issues.json` under OI-01, each with its step, line, current class and solder-free route:
  - 1 is solder-free with parts Shawn has: the 5991 screw terminal takes the 5 A fuse lead.
  - 31 are solder-free with RoboClub common stock. RoboClub stock is assumed, not verified. Of these, 4 depend on a lever-connector fit that is unchecked, and 5 depend on a helper first soldering the amplifier header.
  - 6 need a purchase: pre-wired XT30 pigtails, or a speaker with a plug lead.
  - 20 need a helper.
- **Printed part.** None.

### OI-02 The guide's Pi software path cannot run on a Pi Zero W

- **What goes wrong.** Step pi-config says to flash 32-bit Raspberry Pi OS and "install its software on this OS instead". The upstream package cannot install on ARMv6, so the robot never walks under the guide's software path.
- **Evidence.**
  - `Microduck-build-tutorial/microduck/pyproject.toml` lines 6 to 10 require `requires-python = ">=3.12"`, `onnxruntime>=1.26.0` and `placo>=0.9.23`.
  - PyPI lists onnxruntime 1.26.0 wheels only for x86_64, aarch64, macOS arm64 and Windows, with no source archive.
  - piwheels records 63 onnxruntime releases with no files.
  - placo 0.10.1 has wheels for x86_64 and aarch64 only.
  - These were checked on 2026-10-10 from pypi.org/pypi/onnxruntime/1.26.0/json, pypi.org/pypi/placo/json and piwheels.org/project/onnxruntime/json.
  - `PROJECT-CONTEXT.json` phase1_compute_intent says the Mac "Runs robot control and policy computation in phase one" and the Pi "does not need to run robot-policy inference". It also says this split is "not yet migrated or physically validated".
- **Severity.** Blocks the first walk.
- **Fix (software only).**
  - Rewrite step pi-config to install the project's own Phase 1 split. The Pi forwards bus, IMU and camera data, and the Mac runs the policy and `build-pack-20260913/phase1/runtime`.
  - Add the runtime commissioning the guide lacks: fill `calibration.template.json` (joint limits, and jaw `open_rad` and `closed_rad`, which are null now).
  - Measure Wi-Fi loop timing and stale-data stopping on hardware.
  - A Pi Zero 2 W would run the upstream stack, but buying one is Shawn's decision and is not needed under the recorded Mac-inference plan.
- **Printed part.** None.

### OI-03 The runtime guard stops every simulated walk within 0.62 s

- **What goes wrong.** The policy commands targets beyond the calibrated joint limits. `validate_target` raises Stop, and the runtime turns all servos off mid-step. The measured joint positions never leave the limits; only the commanded targets do.
- **Evidence.**
  - `build-pack-20260913/phase1/runtime/core.py` lines 303 to 306: "if not lo <= target[name] <= hi: raise Stop('Target exceeds calibrated joint limits: ' + name)". Line 352 then calls `self.off(str(e))`.
  - `calibration.template.json` sets hip roll to ±0.3839724354387525 rad.
  - Replaying the 33 adopted walking traces through that check (`evidence/walk-limits-final.json`):
    - every trace trips 0.30 to 0.62 s after the walk command;
    - the first offender is left hip roll in 29 traces and right hip roll in 4;
    - 3.3% to 25.5% of frames are out of range;
    - no trace has a measured joint position out of range.
  - In the baseline trace, 143 of 1500 frames are out of range, the first at t = 2.62 s against a command at 2.02 s.
- **Severity.** Blocks the first walk.
- **Fix (software only).**
  - In walk mode, clamp the policy targets to the calibrated limits and log each clamp.
  - Keep a hard stop when a measured position leaves the limits.
  - Mirror the clamp in `phase1/simulation/evaluate_phase1.py`, add a replay test, and rebuild the runtime bundle.
  - A/B with the clamp (`evidence/walk-ab-raw-clip.json`): 33 of 33 traces still walk, stop and stay upright. Speed is 0.101 to 0.180 m/s against 0.101 to 0.182 m/s without it. Maximum tilt is 4.7 to 9.6° against 4.8 to 6.8°.
  - Do not use the XL330 position-limit registers as the main fix. They clip silently, and the runtime would still stop on the target check.
- **Printed part.** None.

### OI-04 Pi 5 V supply without soldering at the Pi

- **What goes wrong.** Chaining breadboard jumpers from the torso to pins 2 and 6 leaves too much resistance in the loop. While walking, the Pi sees 4.58 to 4.69 V with rated contacts, below the 4.75 V floor. Every inline male-to-female junction is also an unlatched joint inside the moving neck loop. If one pulls apart during a walk, the Pi loses power with no warning; Raspberry Pi warns this can corrupt the SD card. Separately, the guide's first-power check fails a correctly built harness.
- **Evidence** (`evidence/pi-supply-drop.txt`, from `evidence/scripts/pi-supply-drop.py`). The model uses Littelfuse 251 fuse resistance, copper wire at the AWG table values, 10, 20 or 50 mΩ per mated contact, and 15 mΩ shared from the converter to J with 7 A of motor current. The run case draws 0.65 A at 5.00 V; the conservative case draws 0.95 A at 4.95 V. Results are for rated contacts.
  - Current guide (475 mm of 22 AWG plus a soldered tail): 4.79 V running, 4.69 V conservative.
  - All jumpers:
    - 3 × 20 cm of 26 AWG: 4.67 V;
    - 3 × 20 cm of 28 AWG: 4.60 V;
    - 5 × 10 cm of 28 AWG: 4.58 V;
    - 2 × 30 cm of 26 AWG: 4.69 V.
  - 22 AWG to a lever connector inside the head, then one 10 cm 26 AWG jumper end per pole: 4.78 V running, 4.68 V conservative. That is within 0.01 V of the current soldered design.
  - Doubling each pole (pins 2+4 and 6+14): 4.80 V. It gains 0.02 V but forces the amplifier off pin 4.
  - Load: Pi Zero W about 0.25 to 0.45 A, camera 0.25 A (Raspberry Pi), amplifier 0.095 A average and 0.19 A peak at the 3 dB gain into 8 Ω (MAX98357A datasheet), IMU about 0.02 A. That gives about 0.65 A realistic and 0.95 A conservative.
  - The pass line is 4.75 V, from 5 V ±5% at pins 2/4 in the Raspberry Pi HAT design guide.
  - First power: the guide asks for "4.95–5.10 V at J and at Pi pins 2 and 6" (`steps.py` line 866). With the Pi booting at about 0.3 A, the pins read 36 to 64 mV below J. A J reading of 4.95 V therefore gives 4.89 to 4.91 V at the pins.
- **Severity.**
  - The all-jumper supply is a run-time risk. The Zero W's own buck regulator probably keeps running at 4.6 V (inference from its schematic), so the larger practical risk is a pulled junction.
  - The first-power line is a false acceptance failure.
- **Fix.**
  - Run the existing 22 AWG pair through the notch into the head.
  - Inside the cap, join each conductor to one cut 26 AWG copper jumper end in a lever connector, one connector per pole.
  - Keep pins 2 and 6 for the Pi and leave the amplifier on pins 4 and 14.
  - Two caveats on the connector:
    - The WAGO 221-412 is listed for 24 to 12 AWG, with 0.14 mm² minimum fine-stranded. 26 AWG is 0.129 mm², just below that. Use a WAGO 222-412, listed for 28 to 12 AWG, if it fits: it is 12.4 × 14.5 × 20.5 mm, against 13.1 × 18.6 × 8.3 mm for the 221-412.
    - A pocket behind the Pi near (52.5, 5.5, 138) mm fits a 221-412 box in the voxel check. The 222-412 and the cap-lowering sweep with the connectors attached are unchecked.
  - Use copper jumpers, not copper-clad aluminium.
  - Replace the first-power line with three checks, all on a multimeter:
    - J reads 4.95 to 5.10 V with no load;
    - pins 2 to 6 read at least 4.85 V with the Pi idle;
    - with camera streaming, `speaker-test` and a CPU stress running, pins 2 to 6 read at least 4.75 V, and J minus that reading is at most 0.15 V.
- **Printed part.** None. The notch still passes the same 8 wires.

### OI-05 The USB-PD receiver is left at 1.25 A

- **What goes wrong.** Adafruit's 5991 guide says "When the jumper is closed, 1.25A is selected. If the jumper is cut (open), then 3.25A is selected." The pd-tether step sets the 20 V switch but never mentions ISET. At 1.25 A the input is about 25 W, or about 4.5 A at 5 V after the converter. The servo current proxy peaks at 2.7 to 5.5 A in 20 ms windows during simulated walking, before the Pi and amplifier are added. The receiver then requests less than the robot needs, and the source may cut or fold back the supply during walking (inference; the source's behaviour is untested).
- **Evidence.**
  - `build-pack-20260913/redesign-20260913/power-review.md` line 17: "The ISET jumper must be open for the documented 3.25 A selection."
  - `steps.py` lines 278 to 283 (pd-tether) have no ISET instruction.
  - `evidence/leg-current.json` all14.peak20ms is 2.717 to 5.498 A.
- **Severity.** Risk of brownout while walking. The fix is trivial.
- **Fix.**
  - Add to pd-tether: cut the ISET trace between its two pads with a hobby knife, then confirm with the meter that the pads no longer beep. No solder is needed.
  - Add a loaded check at the next bench test: source current stays below 3.25 A.
- **Printed part.** None.

## Risk of damage

### OI-06 Jaw flex fit: marginal at 5 mm and 2 mm, fine when shared

- **What goes wrong.** Step jaw-bench tells the builder to spread the −Y arm about 5 mm and the +Y arm about 2 mm.
  - Each arm narrows to a thin curved wall about 1.5 mm thick, with a 28 to 31 mm² section between x = 41 and 45 mm. It is printed with horizontal layers, so opening the arm pulls those layers apart.
  - At the guide's 5 mm, the peak stress across the layers is 15 to 18 MPa. Prusament PLA's interlayer adhesion is 17 ± 3 MPa, so the fit is marginal.
  - The in-plane strain stays near 1.1%, well inside PLA's 2.9% elongation at yield. The arm is therefore unlikely to show white stress marks before a layer cracks (inference).
  - Shared evenly, the same total opening gives about 11 to 13 MPa peak, which is likely fine.
- **Evidence.**
  - **Geometry** (`evidence/jaw-flex-summary.json`, exact booleans on the audit solids). Raising the jaw from below, the pivot ears (x 18 to 34 mm) overlap head_bottom by up to 4.739 mm on −Y and 1.774 mm on +Y. Both overlaps last together from dz −21.5 to −5.5 mm, so the arms must open about 6.5 mm in total. The sliding ring and lip pad add nothing, and nothing overlaps in the final pose. The guide's 5 and 2 mm are these minimums plus about 0.25 mm. The −Y side needs 2.5 to 3 mm more than +Y throughout.
  - **Print orientation.** `print-manifest.json` instance 8 is "Moving jaw frame", community-4.stl, PLA, extent [91.41, 69.44, 29.04], "Retained source rotation". The robot-frame jaw is 68.7 × 91.4 × 29.4 mm, so print Z is robot Z and stress along z crosses the layers.
  - **Finite elements** (`evidence/jaw-fe-*.json`): linear, E = 2300 MPa, ν = 0.35. The jaw front is held from x = 66 mm (or 75 mm), and the push is spread over each ear's overlap patch.
    - Ear stiffness converged: 0.479 against 0.484 mm/N on −Y, and 0.356 mm/N on +Y, at 0.5 and 0.35 mm voxels.
    - Guide spread 5 mm and 2 mm: stress across the layers peaks at 15.0 MPa (0.35 mm voxels), 17.8 MPa (0.5 mm) and 15.9 MPa (front held from 75 mm). The 99.9th percentile is 9.7 to 12.3 MPa. Principal strain is 0.95 to 1.14%. Thumb force is about 10 N on −Y.
    - The peak sits at (40.7, −42.7, 110.9) mm, near the top edge of the thinnest part of the −Y arm, 7 to 10 mm behind the ear. Its value fell from 17.8 to 15.0 MPa as the voxels shrank, so it is not a sharp-corner singularity.
    - Equal thumb force (jaw free to centre itself): the arms open about 3.7 mm (−Y) and 2.8 mm (+Y). Peak stress is 11.3 to 13.3 MPa, the 99.9th percentile 7.3 to 9.2 MPa, and principal strain 0.71 to 0.86%, at about 7 to 8 N per thumb.
  - **PLA.** Prusament PLA data sheet v1.1: printed horizontal specimens yield at 51 ± 3 MPa with 2.9 ± 0.3% elongation at yield, modulus 2.3 GPa. Interlayer adhesion is 17 ± 3 MPa by Prusa's own method (matterhackers.com/r/xFvGl8, accessed 2026-10-10). The filament brand for this jaw is not recorded, and generic PLA can bond its layers more weakly.
- **Severity.** Risk of damage to a printed part. Marginal as written; likely fine with an even spread.
- **Fix (text only).**
  - Replace the spread sentence with: "Hold the jaw loosely by its front lip so it can slide sideways. Spread both arms at the same time with equal thumb pressure. The −Y arm opens about 3.7 mm and the +Y arm about 2.8 mm. Never open one arm 5 mm while the other is held."
  - Change the flex metadata `'spread': [5.0, 2.0]` (`steps.py` line 671) to `[3.7, 2.8]` so the animation matches.
  - Keep the existing stop rule, and add that a crack can follow a layer line without white marks, so stop at any click.
- **Printed part.** None as the fix. If the arm cracks anyway, reprint jaw_frame (community-4.stl, PLA). That takes about 36 min, estimated as 15.0% of the move time of the 4 h 02 min Elegoo yellow reprint plate; it was not sliced alone.

### OI-07 Runtime current screens may stop the walk; groups do not match the fuses

- **What goes wrong.**
  - Every 0.1 s, the runtime stops the robot if any one servo reads above 1.3 A or the total reads above 5.0 A.
  - It also stops on "fused-group current exceeds 2.25 A" for fixed ID pairs. Those pairs come from an older eleven-fuse layout. The V1.7 guide fuses the right leg, left leg and neck at 3 A each.
- **Evidence** (`core.py` lines 202 to 216, with `GROUPS = ((1,2),(3,4),(5,10),(6,7),(8,9),(11,12),(13,14),(15,))` at line 24). Replaying the screens on the 33 traces with the |torque|/kt proxy, sampled every 0.1 s at each of five phase offsets (`evidence/screen-trips.json`):
  - the 1.3 A screen trips in 15 of 33 traces for at least one offset, all at gait start (t 2.42 to 2.52 s);
  - the 5.0 A total trips in 1 of 33 (old120-push at 5.18 s);
  - the pair screen trips in none.
  - Per-branch load is low against the 3 A fuses. Each leg runs at most 1.51 A RMS, and the worst 1 s average is 1.44 A (`evidence/leg-current.json`).
- **Severity.** Risk of nuisance stops. These are proxy currents and real XL330 readings will differ, so this is not a confirmed failure.
- **Fix (software only).**
  - Log the screens without stopping during the first supported walks.
  - Then set each limit from measured data, requiring two or three consecutive samples over the limit.
  - Replace GROUPS with the guide's real fuse branches: right leg IDs 1 to 5, left leg IDs 6 to 10, neck IDs 11 to 14, each under 3 A.
- **Printed part.** None.

## Low severity: wording, documentation and commissioning

- **OI-08 J12 pad labels conflict.**
  - The guide (`steps.py` line 261) says the square pad is +3.3 V and pad 2 is GND.
  - The ROBOTIS e-manual render labels J12 left to right as Tx, Rx, V, G, with the square pad G.
  - The two data pads agree; only the power pads disagree. The guide's continuity check on pad 2 already protects the build.
  - Fix: add "confirm with the meter which pad beeps to GND before soldering; never connect the 3.3 V pad". Risk if ignored: shorting 3.3 V. Printed part: none.
- **OI-09 Bench test asks for the impossible.**
  - Step bench-test says to plug a temporary XT30 male "onto the bare pigtail ends". The XT30 has solder cups.
  - Fix: use the step's own alternative, insulated hook clips, or a pre-wired pigtail. Wording only.
- **OI-10 The "no purchase" line.**
  - `steps.py` line 167 says "Nothing in this guide needs a new purchase."
  - That line becomes false if Shawn buys any of: 40 cm male-to-female jumpers, WAGO 222-412, pre-wired XT30 pigtails, or the Audio Amp SHIM.
  - Fix: list the purchase, or confirm RoboClub stock first. Wording only.
- **OI-11 Bus decision drift.**
  - `PROJECT-CONTEXT.json` phase1_compute_intent.motor_bus_design_choice (2026-10-09) says "Preserve internal Pi USB to OpenRB".
  - The V1.7 guide uses the J12 UART bridge (`steps.py` line 140) and retired the cap with the USB window (line 194).
  - The UART route is what needs the two J12 joints. Fix: record which bus is current. Documentation only.
- **OI-12 Stale head residuals.**
  - `PROJECT-CONTEXT.json` routingTrial.headProgress still says "Residual pin40/cap contact, speaker/keeper contact, and power/IMU interference remain". That text came from the frozen 2026-10-09 wire stage.
  - In the current audit, those contacts are intended engagements only. For example, `findings.json` lists head_cap to speaker_mount_screw at 0.199 mm (screw thread) and imu_board to imu_sh4_receiving at 0.35 mm (plug). `cables-raw.json` reports cable contacts only at intended end terminations.
  - The pin40/cap part is covered elsewhere.
  - Fix: update the context line. Cable-to-cable crossings and the bundle during neck motion are not modelled; the guide's hand range check in bundle-run covers them.
- **OI-13 Unmeasured fits to check by hand at assembly.**
  - Leg force-fits and the knee press-fit: confirm free motion by hand.
  - Trimmed OpenRB tray rail: stiffness after the notch was not computed.
  - Cap seam: up to 0.2 mm proud, cosmetic.
  - Jaw stop: the jaw meets head_bottom at 40° of opening. That is the guide's intended stop. Through 60° it touches neither the moved Pi rails nor the cap. Other first contacts are motor11 at 43° and neck_pitch at 45°, which head_bottom blocks first (`evidence/jaw-flex-summary.json`).

## Covered elsewhere

- The head cap and Pi header connection, including the residual pin40/cap contact.
- The printed power support versus the left shin, including tray versus leg clearance.

## Method and limits

- All geometry jobs ran through `run_bounded_cad.py` (1536 MiB, one job at a time) using the audit solid cache from `ia_lib.py`. Nothing in the guide, audit or runtime was edited.
- Currents are a torque/kt proxy from MuJoCo traces (kt 0.36601 N·m/A, BAM xl330 m6). They are not measured servo currents.
- Pi supply figures are a resistance model with assumed contact resistance. Measure them on the built harness with the acceptance in OI-04.
- The jaw model is linear-elastic and isotropic, using voxels; the 1.5 mm arm wall is 3 to 4 voxels thick. It treats the hands as a rigid clamp and the ear contact as a distributed patch load. Peaks at voxel corners overstate sharp-edge stress; the 99.9th percentile is the steadier figure.
- Verification date for all web sources: 2026-10-10. Sources are listed per issue in `issues.json`.
