"""Print-time proxies for the two layout D options: exports the V1.9 pack with the tether opening filled, writes an
orientation_check input manifest (print poses below) and runs guide/print/orientation-study/orientation_check.py.
Option 1: V1.9 pack (tether filled) + D frame on the four cover screws + lid.  Option 2: integrated pack with bay + lid."""
import sys, json, hashlib, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent; PRINT = HERE.parent.parent
sys.path.insert(0, str(PRINT / 'rear-pack'))
import pack_lib as P
pack = P.mesh_to_m(P.load_stl(PRINT / 'rear-pack-v19' / 'rear_pack-world.stl')) + P.box((-44.5, -3.0, -44.0), (-39.5, 3.0, -42.8))
P.clean_mesh(pack).export(HERE / 'rear_pack_v19_notether-world.stl')
UP = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 44.0], [0, 0, 0, 1.0]]              # upright, floor z -44 on the bed
LID = [[0, 1.0, 0, 0], [0, 0, 1.0, 0], [1.0, 0, 0, 67.1], [0, 0, 0, 1.0]]            # outer face x -67.1 on the bed
parts = [('opt1_rear_pack_v19_notether', 'rear_pack_v19_notether-world.stl', UP, 'upright as the V1.9 pack (V1.8 print-poses.json pose)'),
         ('opt1_frame_D', 'frame_D-world.stl', UP, 'upright, bottom wall z -44 on the bed (C2 frame pose)'),
         ('opt2_pack_integrated_D', 'pack_integrated_D-world.stl', UP, 'upright, floor z -44 on the bed'),
         ('lid_solid', 'lid_solid-world.stl', LID, 'outer face down'), ('lid_skeletal', 'lid_skeletal-world.stl', LID, 'outer face down')]
man = dict(schemaVersion=1, note='layout D print-time screen (not a release manifest)', parts=[])
for key, f, M, origin in parts:
    p = HERE / f
    man['parts'].append(dict(key=key, color='Orange', quantity=1, path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), sourceFrame='robot frame (mm, x forward, y left, z up)',
                             sourceToPrint=M, flatContact=dict(minimumAreaMm2=300), poseOrigin=origin, supportBlockers=[]))
(HERE / 'orientation-input.json').write_text(json.dumps(man, indent=1))
subprocess.run([sys.executable, str(PRINT / 'orientation-study' / 'orientation_check.py'), str(HERE / 'orientation-input.json'), '--out', str(HERE / 'orientation-check.json')], check=True)
r = json.loads((HERE / 'orientation-check.json').read_text()); out = {}
for pt in r['parts']:
    c = [c for c in pt['candidates'] if c['name'] == 'current'][0]
    out[pt['key']] = dict(volumeMm3=pt['features']['volumeMm3'], heightMm=c['heightMm'], contactMm2=c['contactMm2'], overhang60Mm2=c['overhang60Mm2'],
                          supportProxyMm3=c['supportProxyMm3'], supportOnModelMm2=c['supportOnModelMm2'], bestAlternative=pt.get('bestAlternative'), currentRank=pt.get('currentRank'))
(HERE / 'print_proxies.json').write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
