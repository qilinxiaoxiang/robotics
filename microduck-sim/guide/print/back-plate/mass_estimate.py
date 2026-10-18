"""Static mass and whole-robot COM estimate for layout C (no simulation). Printed parts: solid volume x 1.24 g/cm3 x the slicer
fill fraction recorded in hardware-design-20260912/whole-robot-20260912/dynamics/v19-20261014/v19-mass-items.json. Boards:
XL4015 20 g each (estimate from similar modules), 5991 3.5 g (Adafruit datasheet). Screws: 14 x M2 x 6 at 0.17 g (estimate).
The V1.8 cover (slicer mass, v19-mass-items.json) is removed. Baseline: v19-walk-summary.json mass/asbuilt-batteryremove60
(COM at HOME in the trunk frame). Wires are not included. Writes mass_estimate.json."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rear-pack'))
import pack_lib as P
DYN = Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/v19-20261014')
items = json.loads((DYN / 'v19-mass-items.json').read_text()); summ = json.loads((DYN / 'v19-walk-summary.json').read_text())
fill = items['fill_fraction_vs_PLA_1p24']; base = summ['mass']['asbuilt-batteryremove60']
M0 = base['total_mass_g']; C0 = np.array(base['whole_robot_com_at_home_in_trunk_frame_mm'])
cov = [i for i in items['bodies']['trunk_base'] if i['id'] == 'add-rear_pack_cover'][0]
B = json.loads((HERE / 'build.json').read_text())
adds = []
for nm in ('rear_frame', 'rear_lid'):
    m = P.load_stl(HERE / f'{nm}-world.stl')
    adds.append(dict(id=nm, g=round(float(m.volume) / 1000 * 1.24 * fill, 2), com=np.round(m.center_mass, 2).tolist(), label=f'CAD volume {m.volume / 1000:.2f} cm3 x 1.24 x {fill}'))
for nm in ('left', 'right'):
    m = trimesh.load(str(HERE / f'xl4015_{nm}-world.stl'), force='mesh')
    adds.append(dict(id=f'xl4015_{nm}', g=20.0, com=np.round((m.bounds[0] + m.bounds[1]) / 2, 2).tolist(), label='estimate (similar modules); COM = mesh bounding-box centre'))
pd = trimesh.load(str(HERE / 'pd5991-world.stl'), force='mesh')
adds.append(dict(id='pd5991', g=3.5, com=np.round((pd.bounds[0] + pd.bounds[1]) / 2, 2).tolist(), label='datasheet 3.5 g'))
adds.append(dict(id='screws_14xM2x6', g=round(14 * 0.17, 2), com=[-55.0, 0.0, 0.0], label='estimate'))
adds.append(dict(id='rear_pack_cover_removed', g=-cov['g'], com=cov['com_body_mm'], label='slicer (V1.8 cover)'))
dm = sum(a['g'] for a in adds); dC = sum(a['g'] * (np.array(a['com']) - C0) for a in adds) / (M0 + dm)
res = dict(method=__doc__, baseline=dict(case='asbuilt-batteryremove60', totalMassG=M0, comMm=C0.tolist()), items=adds,
           printedG=round(sum(a['g'] for a in adds if a['id'] in ('rear_frame', 'rear_lid')), 1), netAddedG=round(dm, 1), newTotalG=round(M0 + dm, 1),
           comShiftMm=np.round(dC, 2).tolist(), newComMm=np.round(C0 + dC, 2).tolist())
P.jdump(res, HERE / 'mass_estimate.json')
print(json.dumps({k: v for k, v in res.items() if k != 'method'}, indent=1))
