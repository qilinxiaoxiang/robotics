"""Copy of the as-built (2026-10-15) mass manifest updated to the robot of 2026-10-20 where a sourced value exists.

Run: ~/.venvs/microduck-dyn/bin/python build_manifest_copy.py   (writes asbuilt-20261020-manifest.json and
lid-entry.json here; the original in hardware-design-20260912/.../asbuilt-20261015/ is not touched)

Changes (sources in part_masses.json, from the released Elegoo G-code via dynamics/v19-20261014/gcode_part_masses.py):
  add-head_cap_v19 40.40 g -> add-head_cap_a7z 41.68 g (V1.17 White head_cap_a7z_1, printed 2026-10-15, D-011). Its
      COM is kept at the V1.9 cap COM: same outer shell, rails cut back to pads (assumption, < 1.3 g moved).
  add-face_panel 5.00 g -> 4.79 g (V1.17 White face_panel_a7z_1), same position.
Not changed, bounded instead by sensitivity cases in stand_sim.py:
  add-pi (Pi Zero W 9.3 g) + add-pi-gpio-header 2.5 g + add-camera_board 4.0 g: the Radxa Cubie A7Z and the Radxa
      Camera 13M 214 have no published mass (memory microduck-sim-model-first, read 2026-10-19), so the head is run at
      the manifest value and at +-20 g at the Pi position (sole_thickness_sim.PI_POS).
  Box lid (rear_lid, V1.20 Orange 7.80 g): fitted state after 2026-10-15 is not recorded (the manifest says not fitted);
      lid-entry.json holds its slicer mass at its mesh COM for a +lid case. Leaving it off is the forward-heavy side.
"""
import copy, json
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent
SIM = HERE.parents[3]
SRC = SIM / 'hardware-design-20260912/whole-robot-20260912/dynamics/asbuilt-20261015/asbuilt-mass-manifest.json'
pm = json.loads((HERE / 'part_masses.json').read_text())
cap_g = pm['V1.17-White']['objects']['head_cap_a7z_1_id_0_copy_0']
face_g = pm['V1.17-White']['objects']['face_panel_a7z_1_id_5_copy_0']
lid_g = next(v for k, v in pm.items() if k.startswith('V1.20'))['objects']['rear_lid_1_id_0_copy_0']

man = json.loads(SRC.read_text())
new = copy.deepcopy(man)
for p in new['parts']:
    if p['id'] == 'add-head_cap_v19':
        s = cap_g / (p['mass_kg'] * 1000)
        p.update(id='add-head_cap_a7z', mass_kg=cap_g / 1000, basis='slicer',
                 source='release-V1.17 White G-code object head_cap_a7z_1 %.2f g; COM kept at the V1.9 cap COM (assumption)' % cap_g)
        if 'inertia_about_com_kg_m2' in p:
            p['inertia_about_com_kg_m2'] = (np.array(p['inertia_about_com_kg_m2']) * s).tolist()
    if p['id'] == 'add-face_panel':
        s = face_g / (p['mass_kg'] * 1000)
        p.update(mass_kg=face_g / 1000, source='release-V1.17 White G-code object face_panel_a7z_1 %.2f g' % face_g)
        if 'inertia_about_com_kg_m2' in p:
            p['inertia_about_com_kg_m2'] = (np.array(p['inertia_about_com_kg_m2']) * s).tolist()
new['build'] = man['build'] + '; 2026-10-20 study copy: A7Z head cap and face (V1.17) masses; Pi/camera entries kept (A7Z, 13M 214 unpublished)'
(HERE / 'asbuilt-20261020-manifest.json').write_text(json.dumps(new, indent=1))

# lid entry for the +lid sensitivity case; guide frame == trunk_base frame at qpos0 (build_asbuilt_manifest.to_body
# with POSE['trunk_base'] = (I, 0)), so the mesh COM in m is the body position
t = trimesh.load(str(SIM / 'guide/print/back-plate/layout-F/rear_lid-world.stl'), force='mesh')
lid = dict(body='trunk_base', mass_kg=lid_g / 1000, position_m=(t.center_mass / 1000.0).tolist(),
           source='release-V1.20 Orange rear_lid_1 %.2f g at layout-F/rear_lid-world.stl COM' % lid_g)
(HERE / 'lid-entry.json').write_text(json.dumps(lid, indent=1))
print('cap', cap_g, 'face', face_g, 'lid', lid)
