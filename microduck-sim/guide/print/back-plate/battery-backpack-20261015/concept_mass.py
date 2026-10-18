"""Rough whole-robot mass and COM for the two backpack drafts, same baseline and method as layout-F/mass_estimate.py
(printed parts: CAD volume x 1.24 g/cm3 x 0.851 fill; V1.8 cover removed). Bought-part masses: battery 43 g (Tattu
listing); switch with its two 12 cm XT30 leads, DFR1202, XT30/MR30 halves and box wires are estimates, marked so.
Writes concept_mass.json."""
import json
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent
F = json.loads((HERE.parent / 'layout-F' / 'mass_estimate.json').read_text())
B = F['baseline']; out = {}
for name in ('L1', 'L2'):
    c = json.loads((HERE / 'concepts.json').read_text())[name]; items = []
    for k in ('frame', 'cap'):
        m = trimesh.load(str(HERE / name / f'{k}-world.stl'), force='mesh')
        items.append(dict(id=k, g=round(abs(m.volume) / 1000 * 1.24 * 0.851, 2), com=[round(v, 2) for v in m.center_mass], label='CAD volume x 1.24 x 0.851'))
    ctr = lambda d: [round((a + b) / 2, 2) for a, b in zip(d['lo'], d['hi'])]
    items += [dict(id='battery', g=43.0, com=ctr(c['battery']), label='Tattu listing 43 g'),
              dict(id='switch_with_leads', g=14.0, com=[-54.3, 0, -15.0] if name == 'L1' else [-62.0, 0, -3.0], label='estimate'),
              dict(id='dfr1202', g=6.0, com=ctr(c['dfr1202']), label='estimate'),
              dict(id='plugs_and_wires', g=10.0, com=[-55.0, 0, 5.0], label='estimate: 4 XT30 halves, 1 MR30 half, 22 AWG leads'),
              dict(id='rear_pack_cover_removed', g=-6.304, com=[-45.8, 0, -5.3], label='slicer (V1.8 cover)')]
    added = sum(i['g'] for i in items); M = B['totalMassG'] + added
    com = (np.array(B['comMm']) * B['totalMassG'] + sum(i['g'] * np.array(i['com']) for i in items)) / M
    out[name] = dict(items=items, netAddedG=round(added, 1), newTotalG=round(M, 1), newComMm=[round(v, 2) for v in com],
                     comShiftMm=[round(v, 2) for v in com - np.array(B['comMm'])])
out['F_bench_box'] = dict(netAddedG=F['netAddedG'], newTotalG=F['newTotalG'], newComMm=F['newComMm'], comShiftMm=F['comShiftMm'])
(HERE / 'concept_mass.json').write_text(json.dumps(out, indent=1))
for k, v in out.items():
    print(k, v['netAddedG'], v['newTotalG'], v['newComMm'], v['comShiftMm'])
