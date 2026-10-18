"""Write open-issues/issues.json from the verified evidence (run after the jaw FE files exist)."""
import json
import os

S = '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/open-issues/'
D = '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit/open-issues/'
ACC = '2026-10-10'


def fe(name):
    p = S + name
    return json.load(open(p)) if os.path.exists(p) else None


fe66, fe75, fe35 = fe('jaw-fe-h0.5-x66.json'), fe('jaw-fe-h0.5-x75.json'), fe('jaw-fe-h0.35-x66.json')
jaw_runs = {}
for lab, r in (('h0.5_clampX66', fe66), ('h0.5_clampX75', fe75), ('h0.35_clampX66', fe35)):
    if not r:
        continue
    C = r['complianceMmPerN']
    u1, u2 = r['scenarios']['unit_1_0'], r['scenarios']['unit_0_1']
    sn, sp = u1['sigmaZZ']['sigmaZZMaxMPa'], u2['sigmaZZ']['sigmaZZMaxMPa']
    en, ep = u1['principal']['strainMaxPct'], u2['principal']['strainMaxPct']
    total = 4.739 + 1.774
    dn_eq, dp_eq = total * C[0][0] / (C[0][0] + C[1][1]), total * C[1][1] / (C[0][0] + C[1][1])
    rec = {'voxelMm': r['H'], 'clampXmm': r['XCLAMP'], 'voxels': r['voxels'],
           'earComplianceMmPerN': {'negY': round(C[0][0], 4), 'posY': round(C[1][1], 4)},
           'perMmOfSpread': {'negY': {'sigmaZZmaxMPa': sn, 'sigmaZZp999MPa': u1['sigmaZZ']['sigmaZZP999MPa'], 'principalMaxPct': en},
                             'posY': {'sigmaZZmaxMPa': sp, 'sigmaZZp999MPa': u2['sigmaZZ']['sigmaZZP999MPa'], 'principalMaxPct': ep}},
           'scenarios': {}}
    for sname, sc in r['scenarios'].items():
        if sname.startswith('unit'):
            continue
        rec['scenarios'][sname] = {'spreadMm': sc['deflectionsMm'], 'thumbForceN': sc['forcesN'],
                                   'sigmaZZmaxMPa': sc['sigmaZZ']['sigmaZZMaxMPa'], 'sigmaZZp999MPa': sc['sigmaZZ']['sigmaZZP999MPa'],
                                   'sigmaZZat': sc['sigmaZZ']['at'], 'principalMaxPct': sc['principal']['strainMaxPct'],
                                   'principalP999Pct': sc['principal']['strainP999Pct']}
    rec['scenarios']['equalForce_floating'] = {'spreadMm': [round(dn_eq, 2), round(dp_eq, 2)], 'thumbForceN': round(total / (C[0][0] + C[1][1]), 2),
                                               'sigmaZZmaxMPa': round(max(dn_eq * sn, dp_eq * sp), 2), 'sigmaZZp999MPa': round(max(dn_eq * u1['sigmaZZ']['sigmaZZP999MPa'], dp_eq * u2['sigmaZZ']['sigmaZZP999MPa']), 2), 'principalMaxPct': round(max(dn_eq * en, dp_eq * ep), 3),
                                               'note': 'Linear superposition of the unit cases; jaw held loosely so both thumbs push equally.'}
    jaw_runs[lab] = rec

src_pla = {'url': 'https://www.matterhackers.com/r/xFvGl8', 'title': 'Prusament PLA technical data sheet v1.1 (27-07-2022)', 'accessed': ACC,
           'quote': 'Horizontal ISO 527-1: yield 51 +/- 3 MPa, elongation at yield 2.9 +/- 0.3 %, modulus 2.3 +/- 0.1 GPa; interlayer adhesion 17 +/- 3 MPa (Prusa method)'}

issues = [
    {'id': 'OI-01', 'rank': 1, 'severity': 'blocks-build', 'problemIds': ['P5', 'P6'],
     'title': 'The guide needs 58 solder joints, 13 at the Pi end; Shawn cannot solder reliably',
     'whatGoesWrong': 'Every wire to the Pi is finished by soldering a cut jumper half (step gpio), and 45 more joints sit in the harness, board and head. Several are hard even for a practised hand (2.0 mm J12 pads, castellated converter pads, XT30 cups, multi-wire 16 AWG nodes).',
     'evidence': [{'path': 'guide/content/steps.py', 'line': 794, 'quote': 'strip 5 mm from the wire and from a jumper half, twist them together, solder'},
                  {'path': 'guide/content/steps.py', 'lines': [263, 280, 282, 297, 298, 299, 315, 316, 332, 454, 533, 753, 767, 768], 'quote': 'other solder instructions'}],
     'fix': ['Pins 1, 3, 5, 9: keep the Adafruit 4397 uncut; M-F extension jumpers into its female sockets.',
             'Pins 8, 10: helper solders the cut end of a F-F jumper half at J12 (OpenRB end); M-F extension to the Pi.',
             'Pins 2, 6: 22 AWG into the head, lever connector, one cut 26 AWG jumper end per pole (OI-04).',
             'Pins 4, 12, 14, 35, 40: helper solders the MAX98357A 7-pin header; F-F jumpers to the Pi. Alternative purchase: Pimoroni Audio Amp SHIM (drops fuse and gain resistor; fit unchecked).',
             'Helper still makes about 22 torso and board joints (DFR1202 pads 4, 10 A fuse 2, J nodes and fuses 6, servo-link splices 6, XT30 male 2, J12 2) plus the tether XT30 female (2, or buy a pre-wired pigtail), speaker tabs (2) and the amplifier header, gain resistor and 0.5 A fuse.'],
     'solderOperations': json.load(open(S + 'solder-ops.json')),
     'solderSummary': {'total': 58, 'atPiEnd': 13, 'atPiEndAfterFix': 0,
                       'alternativeSourceCounts': {'shawn-parts': 1, 'roboclub-stock': 31, 'purchase': 6, 'helper-only': 20},
                       'caveats': ['RoboClub stock is assumed, not verified (procurement README does not assert bin stock).',
                                   'Ops 11, 12, 44, 45 depend on a lever-connector fit that is unchecked.',
                                   'Ops 39 to 43 become solder-free only after a helper solders the amplifier header.']},
     'touchesPrintedPart': False, 'printTime': None,
     'verified': ['58 joints counted from steps.py', '4397 ends in female sockets', '5991 output is a screw terminal', 'DFR1202 has castellated pads only', 'MAX98357A 3006 header needs soldering', 'OpenRB variant.h defines Serial3 on D13/D14'],
     'inferred': ['Serial3 socket route will not fit (CAD headroom 4.4 / 9.3 mm against ~14 mm housing)', 'X3P conductor gauge'],
     'sources': [{'url': 'https://www.adafruit.com/product/4397', 'accessed': ACC}, {'url': 'https://www.adafruit.com/product/5991', 'accessed': ACC},
                 {'url': 'https://www.dfrobot.com/product-2907.html', 'accessed': ACC}, {'url': 'https://www.adafruit.com/product/3006', 'accessed': ACC},
                 {'url': 'https://shop.pimoroni.com/products/audio-amp-shim-3w-mono-amp', 'accessed': ACC},
                 {'url': 'https://www.adafruit.com/product/824', 'accessed': ACC}]},
    {'id': 'OI-02', 'rank': 2, 'severity': 'blocks-run', 'problemIds': ['P5', 'P6'],
     'title': "The guide's Pi software path cannot run on a Pi Zero W",
     'whatGoesWrong': 'Step pi-config installs the upstream microduck software on 32-bit Raspberry Pi OS; its onnxruntime dependency has no ARMv6 build, so the robot never walks on that path.',
     'evidence': [{'path': 'guide/content/steps.py', 'line': 853, 'quote': 'The upstream microduck image targets the Pi Zero 2 W; install its software on this OS instead.'},
                  {'path': 'Microduck-build-tutorial/microduck/pyproject.toml', 'lines': [6, 9, 10], 'quote': 'requires-python = ">=3.12"; "onnxruntime>=1.26.0"; "placo>=0.9.23"'},
                  {'url': 'https://pypi.org/pypi/onnxruntime/1.26.0/json', 'number': 'wheels: macosx_14_0_arm64, manylinux aarch64, manylinux x86_64, win_amd64, win_arm64; no sdist'},
                  {'url': 'https://www.piwheels.org/project/onnxruntime/json/', 'number': '63 releases, none with files'},
                  {'url': 'https://pypi.org/pypi/placo/json', 'number': 'placo 0.10.1 wheels x86_64 and aarch64 only (sdist exists)'},
                  {'path': 'PROJECT-CONTEXT.json', 'key': 'phase1_compute_intent', 'quote': 'Runs robot control and policy computation in phase one. / not yet migrated or physically validated'}],
     'fix': ['Rewrite pi-config for the recorded split: Pi forwards bus, IMU and camera; the Mac runs the policy and phase1/runtime.',
             'Add the runtime commissioning the guide lacks: fill calibration.template.json (joint limits; jaw open_rad and closed_rad are null).',
             'Measure Wi-Fi loop timing and stale-data stopping on hardware.',
             'Buying a Pi Zero 2 W is optional and Shawn\'s decision.'],
     'touchesPrintedPart': False, 'printTime': None,
     'verified': ['wheel platforms on PyPI and piwheels', 'upstream dependency pins', 'compute intent text'], 'inferred': ['building placo from source on ARMv6 is impractical'],
     'sources': [{'url': 'https://pypi.org/pypi/onnxruntime/1.26.0/json', 'accessed': ACC}, {'url': 'https://www.piwheels.org/project/onnxruntime/json/', 'accessed': ACC}, {'url': 'https://pypi.org/pypi/placo/json', 'accessed': ACC}]},
    {'id': 'OI-03', 'rank': 3, 'severity': 'blocks-run', 'problemIds': ['P6'],
     'title': 'The runtime target guard stops every simulated walk within 0.62 s',
     'whatGoesWrong': 'Policy targets for hip roll exceed the calibrated +/-0.384 rad; validate_target raises Stop and the runtime torques off all servos mid-step. Measured positions never leave the limits.',
     'evidence': [{'path': 'build-pack-20260913/phase1/runtime/core.py', 'lines': [303, 306, 352], 'quote': "raise Stop('Target exceeds calibrated joint limits: ' + name) ... self.off(str(e))"},
                  {'path': 'build-pack-20260913/phase1/runtime/calibration.template.json', 'number': 'hip roll +/-0.3839724354387525 rad'},
                  {'path': 'guide/content/interference-audit/open-issues/evidence/walk-limits-final.json', 'number': '33/33 traces trip 0.30 to 0.62 s after the walk command; first offender left hip roll 29, right hip roll 4; 3.3 to 25.5 % of frames out of range; measured qpos never out of range'},
                  {'path': 'guide/content/interference-audit/open-issues/evidence/walk-ab-raw-clip.json', 'number': 'with clamp 33/33 walk, stop and stay up; speed 0.101 to 0.180 m/s (0.101 to 0.182 without); tilt 4.7 to 9.6 deg (4.8 to 6.8 without)'}],
     'fix': ['Clamp walk-mode policy targets to the calibrated limits and log each clamp; keep a hard stop on measured positions outside the limits.',
             'Mirror the clamp in phase1/simulation/evaluate_phase1.py, add a replay test, rebuild the runtime bundle.',
             'Do not rely on XL330 position-limit registers as the main fix.'],
     'touchesPrintedPart': False, 'printTime': None,
     'verified': ['guard code path', 'replay on 33 traces', 'clamp A/B in simulation'], 'inferred': ['hardware will behave like the simulation traces']},
    {'id': 'OI-04', 'rank': 4, 'severity': 'risk-of-brownout-and-false-acceptance', 'problemIds': ['P5', 'P6'],
     'title': 'Pi 5 V supply without soldering at the Pi',
     'whatGoesWrong': 'An all-jumper supply gives 4.58 to 4.69 V at the Pi while walking (rated contacts), below the 4.75 V floor, and adds unlatched male-female junctions in the moving neck loop. The first-power check (4.95 to 5.10 V at pins 2 and 6) fails a correct harness.',
     'evidence': [{'path': 'guide/content/interference-audit/open-issues/evidence/pi-supply-drop.txt', 'number': 'run case (0.65 A, motors 7 A, DFR 5.00 V), rated contacts: current guide 4.79 V; 3x20 cm 26 AWG 4.67 V; 3x20 cm 28 AWG 4.60 V; 5x10 cm 28 AWG 4.58 V; 2x30 cm 26 AWG 4.69 V; 22 AWG + lever connector + 10 cm 26 AWG end 4.78 V (4.68 V conservative); doubled 4.80 V'},
                  {'path': 'guide/content/steps.py', 'line': 866, 'quote': 'Measure 4.95–5.10 V at J and at Pi pins 2 and 6.'},
                  {'path': 'guide/content/interference-audit/open-issues/evidence/pi-supply-drop.txt', 'number': 'J 4.95 V at 0.3 A boot load gives 4.886 to 4.914 V at pins 2 to 6'},
                  {'path': 'build-pack-20260913/redesign-20260913/power-review.md', 'quote': 'earlier review specified doubled pins 2+4 / 6+14 with 22 AWG and screened 4.818 V at 1.5 A'}],
     'fix': ['Run the existing 22 AWG pair through the notch into the head; inside the cap join each conductor to one cut 26 AWG copper jumper end in a lever connector; pins 2 and 6 only; amplifier stays on pins 4 and 14.',
             'WAGO 221-412 is listed 24 to 12 AWG (0.14 mm2 fine-stranded minimum); 26 AWG is 0.129 mm2. Prefer WAGO 222-412 (28 to 12 AWG, 12.4 x 14.5 x 20.5 mm) if it fits; its fit and the cap-lowering sweep with connectors are unchecked. A 221-412 box fits a pocket near (52.5, 5.5, 138) mm in a 1 mm voxel check.',
             'Use copper jumpers, not CCA.',
             'Replace the first-power line: J 4.95 to 5.10 V unloaded; pins 2 to 6 at least 4.85 V with the Pi idle; at least 4.75 V with camera stream, speaker-test and CPU stress, and J minus pins at most 0.15 V; multimeter only.'],
     'touchesPrintedPart': False, 'printTime': None,
     'verified': ['fuse resistance (Littelfuse 251)', 'AWG resistance', 'Pi, camera, MAX98357A, BNO085 currents from official datasheets', 'route length 285 + 190 mm', '4.75 V HAT floor', 'WAGO 221/222 listed ranges and sizes (distributor data)'],
     'inferred': ['contact resistance 10/20/50 mOhm', 'Wi-Fi allowance 0.10 A', '7 A motor allocation as load', 'Zero W keeps running below 4.75 V', 'voxel fit of the connector'],
     'sources': [{'url': 'https://github.com/raspberrypi/hats/blob/master/designguide.md', 'accessed': ACC},
                 {'url': 'https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/power-supplies.adoc', 'accessed': ACC},
                 {'url': 'https://cdn-shop.adafruit.com/product-files/3006/MAX98357A-MAX98357B.pdf', 'accessed': ACC},
                 {'url': 'https://www.ceva-ip.com/wp-content/uploads/BNO080_085-Datasheet.pdf', 'accessed': ACC},
                 {'url': 'https://datasheets.raspberrypi.com/rpizero/raspberry-pi-zero-w-reduced-schematics.pdf', 'accessed': ACC},
                 {'url': 'https://tw.element14.com/en-TW/wago/221-412/terminal-block-pluggable-2pos/dp/2534732', 'accessed': ACC},
                 {'url': 'https://sg.element14.com/wago/222-412/terminal-block-pluggable-2pos/dp/1300511', 'accessed': ACC},
                 {'url': 'https://www.pololu.com/category/66/female-female-premium-jumper-wires', 'accessed': ACC}]},
    {'id': 'OI-05', 'rank': 5, 'severity': 'risk-of-brownout', 'problemIds': ['P5'],
     'title': 'The USB-PD receiver is left at its 1.25 A ISET default',
     'whatGoesWrong': 'With ISET closed the 5991 selects 1.25 A, about 25 W at 20 V or about 4.5 A at 5 V after the converter. Simulated walking peaks at 2.7 to 5.5 A for the servos alone, before the Pi and amplifier. The source may limit or drop the supply mid-walk (inference).',
     'evidence': [{'path': 'build-pack-20260913/redesign-20260913/power-review.md', 'line': 17, 'quote': 'The ISET jumper must be open for the documented 3.25 A selection.'},
                  {'url': 'https://learn.adafruit.com/adafruit-usb-type-c-power-delivery-switchable-breakout', 'quote': 'When the jumper is closed, 1.25A is selected. If the jumper is cut (open), then 3.25A is selected.'},
                  {'path': 'guide/content/steps.py', 'lines': [278, 283], 'quote': 'pd-tether has no ISET instruction'},
                  {'path': 'guide/content/interference-audit/open-issues/evidence/leg-current.json', 'number': 'all14.peak20ms 2.717 to 5.498 A'}],
     'fix': ['Add to pd-tether: cut the ISET trace between its pads with a hobby knife and confirm with the meter that the pads no longer beep.', 'At the loaded bench test confirm source current stays below 3.25 A.'],
     'touchesPrintedPart': False, 'printTime': None, 'verified': ['ISET behaviour', 'guide omission'], 'inferred': ['source enforcement behaviour at the requested current']},
    {'id': 'OI-06', 'rank': 6, 'severity': 'risk-of-damage', 'problemIds': ['P5'],
     'title': 'Jaw flex fit: marginal at the guide spread of 5 mm and 2 mm, likely fine when both arms share the spread',
     'verdict': 'Marginal as written; likely fine with equal thumb force (jaw held loosely so it centres itself).',
     'whatGoesWrong': 'Step jaw-bench tells the builder to open the -Y arm about 5 mm and the +Y arm about 2 mm. The arm is a thin curved wall (about 1.5 mm thick, 28 to 31 mm2 section between x 41 and 45 mm) printed with horizontal layers, so opening it pulls the layers apart near its thinnest point. At 5 mm the peak layer-normal stress is 15 to 18 MPa against an interlayer adhesion of 17 +/- 3 MPa for Prusament PLA. In-plane strain stays near 1.1 %, well inside the 2.9 % elongation at yield, so the arm is unlikely to whiten before a layer crack (inference).',
     'evidence': [{'path': 'guide/content/steps.py', 'line': 679, 'quote': 'Spread the arms with your thumbs as they pass the walls: the −Y arm (with the ring) about 5 mm, the +Y arm about 2 mm.'},
                  {'path': 'guide/content/steps.py', 'line': 671, 'quote': "'spread': [5.0, 2.0]"},
                  {'path': 'guide/content/interference-audit/open-issues/evidence/jaw-flex-summary.json', 'number': 'ear overlap with head_bottom up to 4.739 mm (-Y) and 1.774 mm (+Y) at x 18 to 34 mm; both present together from dz -21.5 to -5.5 mm (total about 6.5 mm); ring and lip pad add nothing; no final-pose overlap'},
                  {'path': 'build-pack-20260913/redesign-20260913/print-manifest.json', 'quote': 'Moving jaw frame, community-4.stl, PLA, extent [91.41, 69.44, 29.04], "Retained source rotation"; robot-frame extent 68.7 x 91.4 x 29.4 mm, so print Z is robot Z and layers are horizontal'},
                  {'path': 'guide/content/interference-audit/open-issues/evidence/jaw-fe-h0.35-x66.json', 'number': 'guide 5/2: sigma_zz peak 15.0 MPa, 99.9th percentile 12.3 MPa, principal strain 1.14 %, thumb force 10.3 N (-Y) and 5.6 N (+Y); ear compliance 0.484 / 0.356 mm/N'},
                  {'path': 'guide/content/interference-audit/open-issues/evidence/jaw-fe-h0.5-x66.json', 'number': 'guide 5/2: sigma_zz peak 17.8 MPa, 99.9th percentile 11.6 MPa, principal 1.07 %'},
                  {'path': 'guide/content/interference-audit/open-issues/evidence/jaw-fe-h0.5-x75.json', 'number': 'longer free arm (clamp x >= 75): guide 5/2 sigma_zz peak 15.9 MPa, principal 0.95 %'}],
     'fix': ['Rewrite the jaw-bench spread instruction: hold the jaw loosely by its front lip so it can slide sideways, and spread both arms at the same time with equal thumb pressure. The jaw centres itself and the arms open about 3.7 mm (-Y) and 2.8 mm (+Y), about 6.5 mm in total, with about 7 to 8 N per thumb.',
             'Change the flex metadata spread [5.0, 2.0] to [3.7, 2.8] so the animation matches.',
             'Keep the stop rule and add: a crack can follow a layer line without white marks, so stop at any click.',
             'Equal-force result: sigma_zz peak 11.3 to 13.3 MPa, 99.9th percentile 7.3 to 9.2 MPa, principal strain 0.71 to 0.86 % across the three models.'],
     'jawFE': jaw_runs,
     'verified': ['overlap geometry from exact booleans', 'layer direction from print manifest and extents', 'FE stiffness converged (0.479 vs 0.484 mm/N between 0.5 and 0.35 mm voxels)', 'Prusament values'],
     'inferred': ['jaw printed in PLA with Prusament-like interlayer adhesion (brand unknown)', 'hands act as a rigid clamp at x >= 66 or 75 mm', 'linear isotropic model; layer weakness enters only through the strength comparison', 'no whitening before a layer crack'],
     'touchesPrintedPart': False,
     'printTimeIfCracked': 'jaw_frame (community-4.stl, PLA): about 36 min, estimated as 15.0 % of the move time of the 4 h 02 min Elegoo yellow reprint plate (09-REPRINT-READY-20260930/Elegoo/yellow); not sliced alone. About 4.74 m of 1.75 mm filament (11.4 cm3).',
     'sources': [src_pla]},
    {'id': 'OI-07', 'rank': 7, 'severity': 'risk-of-nuisance-stop', 'problemIds': ['P6'],
     'title': 'Runtime current screens may stop the walk; fused groups do not match the guide fuses',
     'whatGoesWrong': 'The 1.3 A per-servo screen may trip at gait start; GROUPS pairs come from an older fuse layout and do not match the guide\'s right-leg, left-leg and neck 3 A fuses.',
     'evidence': [{'path': 'build-pack-20260913/phase1/runtime/core.py', 'lines': [24, 202, 216], 'quote': 'GROUPS = ((1,2),(3,4),(5,10),(6,7),(8,9),(11,12),(13,14),(15,)); 1.3 A per servo; total limit from calibration (5.0 A)'},
                  {'path': 'guide/content/interference-audit/open-issues/evidence/screen-trips.json', 'number': '1.3 A screen trips in 15/33 traces for at least one of five 0.1 s sampling phases, all at t 2.42 to 2.52 s; 5.0 A total trips 1/33 (old120-push, t 5.18 s); 2.25 A pairs 0/33'},
                  {'path': 'guide/content/interference-audit/open-issues/evidence/leg-current.json', 'number': 'per-leg RMS at most 1.51 A, worst 1 s mean 1.44 A against 3 A fuses'}],
     'fix': ['Log the screens without stopping during the first supported walks, then set limits from measured data with 2 to 3 consecutive samples.', 'Replace GROUPS with the real fuse branches: IDs 1 to 5, 6 to 10, 11 to 14, each under 3 A.'],
     'touchesPrintedPart': False, 'printTime': None, 'verified': ['screen code', 'proxy replay'], 'inferred': ['proxy |tau|/kt approximates XL330 present current']},
    {'id': 'OI-08', 'rank': 8, 'severity': 'low', 'problemIds': ['P5'], 'title': 'J12 pad labels conflict between the guide and the ROBOTIS render',
     'evidence': [{'path': 'guide/content/steps.py', 'line': 261, 'quote': 'Pad 1 is the square pad (+3.3 V)'}, {'note': 'ROBOTIS e-manual render shows J12 as Tx, Rx, V, G with the square pad labelled G; data pads agree'}],
     'fix': ['Meter-check which pad beeps to GND before soldering; never connect the 3.3 V pad.'], 'touchesPrintedPart': False, 'printTime': None},
    {'id': 'OI-09', 'rank': 9, 'severity': 'wording', 'problemIds': ['P5'], 'title': 'Bench test asks to plug a solder-cup XT30 onto bare wire',
     'evidence': [{'path': 'guide/content/steps.py', 'line': 342, 'quote': 'Plug it onto the bare pigtail ends only for this test, or clip them with insulated hooks.'}],
     'fix': ['Use insulated hook clips or a pre-wired pigtail; drop the plug wording.'], 'touchesPrintedPart': False, 'printTime': None},
    {'id': 'OI-10', 'rank': 10, 'severity': 'wording', 'problemIds': ['P5'], 'title': '"Nothing in this guide needs a new purchase" may become false',
     'evidence': [{'path': 'guide/content/steps.py', 'line': 167, 'quote': 'Nothing in this guide needs a new purchase.'}],
     'fix': ['List any purchase (40 cm M-F jumpers, WAGO 222-412, pre-wired XT30 pigtails, Audio Amp SHIM) or confirm RoboClub stock first.'], 'touchesPrintedPart': False, 'printTime': None},
    {'id': 'OI-11', 'rank': 11, 'severity': 'documentation', 'problemIds': ['P5', 'P6'], 'title': 'PROJECT-CONTEXT records a Pi USB motor bus; the guide uses the J12 UART',
     'evidence': [{'path': 'PROJECT-CONTEXT.json', 'key': 'phase1_compute_intent.motor_bus_design_choice', 'quote': 'Preserve internal Pi USB to OpenRB during the enclosed-head repair'},
                  {'path': 'guide/content/steps.py', 'line': 140, 'quote': 'The Pi talks to the OpenRB over two UART wires.'}],
     'fix': ['Record which bus is current; the UART route is what needs the two J12 joints.'], 'touchesPrintedPart': False, 'printTime': None},
    {'id': 'OI-12', 'rank': 12, 'severity': 'documentation', 'problemIds': ['P5'], 'title': 'Stale head residuals in PROJECT-CONTEXT',
     'evidence': [{'path': 'PROJECT-CONTEXT.json', 'key': 'current_build.staged_review_20261009.routingTrial.headProgress', 'quote': 'Residual pin40/cap contact, speaker/keeper contact, and power/IMU interference remain.'},
                  {'path': 'guide/content/interference-audit/findings.json', 'number': 'only intended engagements: head_cap/speaker_mount_screw 0.199 mm, imu_board/imu_sh4_receiving 0.35 mm'},
                  {'path': 'guide/content/interference-audit/cables-raw.json', 'number': 'cable contacts only at intended end terminations'}],
     'fix': ['Update the context line; pin40/cap is covered elsewhere. Cable-to-cable crossings and the bundle in neck motion stay with the guide hand check in bundle-run.'], 'touchesPrintedPart': False, 'printTime': None},
    {'id': 'OI-13', 'rank': 13, 'severity': 'commissioning-or-cosmetic', 'problemIds': ['P5'], 'title': 'Unmeasured fits to check by hand',
     'evidence': [{'path': 'guide/content/interference-audit/README.md', 'quote': 'Inference and limits'},
                  {'path': 'guide/content/interference-audit/open-issues/evidence/jaw-flex-summary.json', 'number': 'jaw meets head_bottom at 40 deg; motor11 43 deg; neck_pitch 45 deg; no contact with moved Pi rails or cap through 60 deg'}],
     'fix': ['Confirm leg force-fit and knee press-fit free motion by hand', 'Tray rail stiffness after the notch not computed', 'Cap seam up to 0.2 mm proud (cosmetic)', 'Jaw stop at 40 deg is the intended stop'],
     'touchesPrintedPart': False, 'printTime': None},
]
coveredElsewhere = ['Head cap and Pi header connection, including residual pin40/cap contact', 'Printed power support versus left shin, including tray versus leg clearance']
out = {'checked': ACC, 'guideRevision': 'V1.7 (guide/content/steps.py, guide/data/guide-data.json)', 'problemIds': ['P5', 'P6'],
       'issues': issues, 'coveredElsewhere': coveredElsewhere}
json.dump(out, open(D + 'issues.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps(jaw_runs, indent=1))
