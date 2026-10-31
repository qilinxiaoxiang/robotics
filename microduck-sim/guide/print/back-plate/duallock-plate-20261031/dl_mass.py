"""Whole-robot mass and COM with the Dual Lock back plate, method of battery-backpack-20261015/bp_mass.py (baseline
layout-F/mass_estimate.json; printed parts: CAD volume x 1.24 g/cm3 x 0.851 fill). Changes against the screwed mounts:
- the plate is added (build/duallock_plate-world.stl, at its mesh centre of mass);
- every backpack item moves SHIFT_MM in x (guide-world.json): battery backpack from bp_mass.json, bench box from
  layout-F/mass_estimate.json, except the V1.8 cover removal, which stays where the cover was;
- the four M2 x 6 stay on the robot in both mounts (bp_mass counts them as already there);
- Dual Lock: not in the totals (strip size and areal mass not measured); DL_BOUND_G shows the effect of a mated pair of
  that mass at the pad centre.
Writes dl_mass.json.  /tmp/microduck-cad-venv/bin/python dl_mass.py"""
import json
from pathlib import Path
import numpy as np, trimesh

HERE = Path(__file__).resolve().parent
BPD = HERE.parent / 'battery-backpack-20261015'
F = json.loads((HERE.parent / 'layout-F' / 'mass_estimate.json').read_text()); base = F['baseline']
BP = json.loads((BPD / 'bp_mass.json').read_text())['backpack']['items']
SHIFT_MM = json.loads((HERE / 'guide-world.json').read_text())['shiftMm'][0]
DL_BOUND_G, DL_COM = 4.0, [-50.85, 0.0, -3.5]   # bound for the sensitivity line only, not a sourced mass
STAY = {'rear_pack_cover_removed'}

m = trimesh.load(str(HERE / 'build/duallock_plate-world.stl'), force='mesh')
plate = dict(id='duallock_plate', g=round(abs(m.volume) / 1000 * 1.24 * 0.851, 2), com=[round(v, 2) for v in m.center_mass],
             label=f'CAD volume {abs(m.volume) / 1000:.2f} cm3 x 1.24 x 0.851')


def com_of(items):
    M = base['totalMassG'] + sum(i['g'] for i in items)
    c = (np.array(base['comMm']) * base['totalMassG'] + sum(i['g'] * np.array(i['com']) for i in items)) / M
    return M, c


def moved(items):
    return [dict(i, com=[round(i['com'][0] + (0 if i['id'] in STAY else SHIFT_MM), 2)] + i['com'][1:]) for i in items]


out = {'method': __doc__.split('Writes')[0].strip(), 'shiftMm': SHIFT_MM, 'plate': plate,
       'baseline': dict(totalMassG=base['totalMassG'], comMm=base['comMm'])}
for name, items in (('battery_backpack', BP), ('bench_box', F['items'])):
    M0, c0 = com_of(items)
    dl = moved(items) + [plate]
    M1, c1 = com_of(dl)
    Mb, cb = com_of(dl + [dict(id='duallock_bound', g=DL_BOUND_G, com=DL_COM)])
    out[name] = dict(screwed=dict(totalG=round(M0, 1), comMm=[round(v, 2) for v in c0]),
                     duallock=dict(items=dl, totalG=round(M1, 1), comMm=[round(v, 2) for v in c1]),
                     comShiftVsScrewedMm=[round(v, 2) for v in c1 - c0], addedGVsScrewed=round(M1 - M0, 2),
                     withDualLockBound=dict(g=DL_BOUND_G, comShiftVsScrewedMm=[round(v, 2) for v in cb - c0]))
(HERE / 'dl_mass.json').write_text(json.dumps(out, indent=1) + '\n')
print('plate', plate)
for k in ('battery_backpack', 'bench_box'):
    v = out[k]
    print(k, v['screwed'], {kk: v['duallock'][kk] for kk in ('totalG', 'comMm')}, 'shift', v['comShiftVsScrewedMm'], 'with DL bound', v['withDualLockBound'])
