"""Collect every number of the power-support origin study into measurements.json (reads the study's JSON outputs;
no CAD). Each history claim carries its source path, field or line, and a short quote; inference is marked."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = '/Users/xiangzheng/code/robotics/microduck-sim'


def load(name):
    p = HERE / name
    return json.loads(p.read_text()) if p.exists() else None


history = [
    dict(claim='The integrated support was made on 2026-09-12 to replace the original power support (community a.obj = upstream power_support). '
               'It kept the battery in the original bay, put the large regulator under the battery and the small regulator between the hip servos, '
               'and replaced an earlier 69 mm rear backpack.',
         source=f'{SIM}/hardware-design-20260912/whole-robot-20260912/assembly/README.md', field='line 5',
         quote='电池留在原电池区；大稳压器在电池下方，小稳压器在两台髋关节舵机之间。此前 69 mm 外伸背包已被本方案取代。', inference=False),
    dict(claim='The design note for that version is dated 2026-09-12.',
         source=f'{SIM}/hardware-design-20260912/whole-robot-20260912/README.md', field='line 3', quote='2026-09-12。推进 P5', inference=False),
    dict(claim='Both regulators were moved into the torso so heavy power parts would not sit in the head.',
         source=f'{SIM}/hardware-design-20260912/whole-robot-20260912/README.md', field='line 24',
         quote='两块稳压器移到躯干：大板放电池下方，小板放髋部之间。避免把较重的供电部件集中到头上。', inference=False),
    dict(claim='The large regulator was the Pololu D24V150F5 (servo 5 V); the small one the S13V30F5 (Pi, camera, amplifier 5 V).',
         source=f'{SIM}/hardware-design-20260912/whole-robot-20260912/README.md', field='line 65',
         quote='Pololu D24V150F5 提供舵机侧 5V，S13V30F5 提供 Pi、相机和功放侧 5V', inference=False),
    dict(claim='The lower deck and its two hanger posts are the "vented lower shelf for motor regulator" with the D24V150F5 screw pitch.',
         source=f'{SIM}/hardware-design-20260912/whole-robot-20260912/assembly/build_compact_battery.py', field='lines 23-34',
         quote='# Vented lower shelf for motor regulator, exact screw pitch 25.4 X x 38.862 Y.', inference=False),
    dict(claim='The deck sits 13.43 mm below the original support and the rear end is 12.27 mm behind the original battery; width unchanged.',
         source=f'{SIM}/hardware-design-20260912/whole-robot-20260912/assembly/README.md', field='line 35',
         quote='底端为 Z −57.5 mm，相对原支架低 13.43 mm。支架宽度仍为 54.50 mm。', inference=False),
    dict(claim='The 43.2 x 31.8 x 11 mm regulator had no collision-free spot inside the torso search box, which is why it went under the bay.',
         source=f'{SIM}/hardware-design-20260912/whole-robot-20260912/assembly/trunk-electronics-candidates.json', field='reg1 (empty list)',
         quote='"reg1": []', inference=True,
         note='The empty candidate list is a fact; that it caused the under-bay shelf is inference from timing and the build-script comment.'),
    dict(claim='On 2026-10-09 the user rejected the central clamped battery and chose the original layout with the DFR1202 converter in the original battery location, '
               'powered from the wall charger over a tether.',
         source=f'{SIM}/PROJECT-CONTEXT.json', field='current_build.powerbank_trial_20261008.userDecision and .decision; current_build.source_location',
         quote='follow original layout and replace battery location with regulator/buck board.', inference=False),
    dict(claim='On 2026-10-09 the OpenRB-150 moved from the head onto the lower deck, held by a new printed tray.',
         source=f'{SIM}/guide/print/release-V1.6/evidence/openrb_tray-change.json', field='reason',
         quote='OpenRB-150 moves from the head to the power-support lower deck', inference=False),
    dict(claim='The current guide fits the support unchanged (10/1 print) and straps the tray to the deck with the four deck standoffs and two ties through the deck slots.',
         source=f'{SIM}/guide/content/steps.py', field="step 'power-support' line 408; step 'tray' lines 476-477",
         quote='drop it so the four round deck standoffs go into its four clearance holes', inference=False),
    dict(claim='The phase-1 walking runs removed the upstream power_support and NP-F970 collision geoms and added the integrated support as a visual only, '
               'so the simulator had no shin-to-support contact.',
         source=f'{SIM}/build-pack-20260913/phase1/evaluate_phase1.py lines 52-62 with {SIM}/build-pack-20260913/phase1/simulation/geometry-manifest.json',
         field='remove_meshes includes np_f970 and power_support; parts[0] power-support-integrated-body.stl added with contype=0, conaffinity=0 and no collision_box',
         quote="remove_meshes: ['np_f970', 'power_support', ...]", inference=False),
    dict(claim='The phase-1 mass model kept the OpenRB (13 g) in the head, not on the deck.',
         source=f'{SIM}/build-pack-20260913/phase1/simulation/mass-manifest.json', field="parts[id='openrb'] body jaw_soft, position (27.2, 0.0, -20.7) mm",
         quote='openrb jaw_soft 0.013', inference=False),
    dict(claim='The final phase-1 controller is kp 275, 20 ms action delay, prediction off; its 33 cases include one 40 ms sensor-delay case per mass.',
         source=f'{SIM}/build-pack-20260913/phase1/simulation/README.md', field='lines 10-12, 27',
         quote='BAM proportional gain is 275', inference=False),
    dict(claim='The 2026-09-12 mesh check of the new torso parts against the legs sampled 250 of 1500 frames from kp 200 trajectories and found no overlap above 0.005 mm3. '
               'It did not cover the later kp 275 / kp 300 controllers.',
         source=f'{SIM}/hardware-design-20260912/whole-robot-20260912/delay-repair-20260912/mesh-old0-sensor40/full-assembly-final-trajectory.json',
         field='sampled_frames, source_frames, cross_body_collisions; config kp in repair-final-perturb-batteryremove0-sensor40.config.json',
         quote='"sampled_frames": 250, "source_frames": 1500, "cross_body_collisions": []', inference=False),
    dict(claim='Upstream training (velocity task) penalises contact between the shin collision mesh and the upstream power_support collision mesh '
               '(weight -1.0); the upstream author expects the joint limits to keep the legs off the body.',
         source=f'{SIM}/microduck_rl/src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py lines 319-327; '
                f'{SIM}/microduck_rl/src/mjlab_microduck/robot/microduck/robot_walk.xml lines 99, 154, 309',
         field="rewards['self_collisions'] weight -1.0; geoms of class self_collision_only on mesh power_support and mesh leg",
         quote='discourages legs from crashing into the trunk battery holder', inference=False,
         note='That the frozen walking policy was trained with this exact config is inference; the policy checkpoint does not record it.'),
]

regions = [
    dict(region='original frame (x -31..-14, z -44.07..39.42), kept 10090 mm3',
         job_now='Mounts the torso to both hip-yaw motor cases and the torso base (M2 x 10 from below and above).', needed=True,
         source=f'{SIM}/guide/content/steps.py lines 405-420'),
    dict(region='battery bay: floor z -37.5..-36, top slab z 28..29.5, front posts, side lips (x -49.4..-21.8)',
         job_now='Holds the DFR1202 converter insert on four sides (foam-taped to the bay floor); J and the 10 A main fuse sit in the open rear bay; '
                 'the XT30 pigtail is tied to the support; the IMU holder rail sits 0.1 mm from the top slab.', needed=True,
         source=f'{SIM}/guide/content/steps.py lines 444, 455, 462; geometry.json mounted_parts'),
    dict(region='battery tie slots (z -30.82 and 5.88, |y| 18.365)', job_now='Made for the two battery ties. No current guide step routes a tie through them '
                                                                         '(steps.py mentions ties only through the insert, the pigtail, the deck slots and the head hood).',
         needed=False, source=f'{SIM}/guide/content/steps.py (grep "slot", "tie")', inference=True),
    dict(region='lower deck with four bosses and two vent/tie slots (x -59.1..-11.9, |y| <= 17.95, z -57.5..-53.5), 2878.5 mm3',
         job_now='Carries the OpenRB tray (seated on the deck, 0.0 mm gap) via the four standoffs and two ties through the deck slots. '
                 'The D24V150F5 it was made for is no longer in the build.', needed=True,
         source=f'{SIM}/guide/content/steps.py lines 469-477; geometry.json mounted_parts.openrb_tray'),
    dict(region='two hanger posts and cross bar (x -37.5..-33.5, |y| 18.0..20.4, z -57.5..-35.5), 2 x (129.3 + 84.3) mm3',
         job_now='The only link between the deck and the rest of the part (without them the part splits into 15516.3 + 2878.5 mm3). '
                 'This is where the shins touch.', needed=True, source='geometry.json connectivity'),
    dict(region='small regulator holder between the hip servos (x -20..9, z 3..32), 2113.3 mm3',
         job_now='Empty. The S13V30F5 and its cover are retired; no current guide part overlaps the holder box (solids-report.json bounds).',
         needed=False, source=f'{SIM}/guide/content/steps.py line 194 (small-regulator cover no longer used); ../solids-report.json'),
]

out = dict(
    about='Power-support origin study. Robot frame mm: x forward, y left, z up (MuJoCo trunk_base). Print frame = robot frame + 57.5 mm in z.',
    history=history, regions=regions,
    geometry=load('geometry.json'), walkFrames=load('walk-frames.json'), reach=load('reach-summary.json'),
    sweep=load('sweep-summary.json'), trimFeasibility=load('trim-feasibility.json'),
    candidates={p.name.replace('-build.json', ''): dict(build=json.loads(p.read_text()),
                                                         check=json.loads(p.with_name(p.name.replace('-build.json', '-check.json')).read_text())
                                                         if p.with_name(p.name.replace('-build.json', '-check.json')).exists() else None)
                for p in sorted((HERE / 'candidates').glob('*-build.json'))},
)
(HERE / 'measurements.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
print('written', len(json.dumps(out)))
