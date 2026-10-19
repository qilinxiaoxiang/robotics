#!/usr/bin/env python3
"""Where is the first-layer brim that the pipeline's brim_review counts as inside the part's own convex outline?
Replays release_pipeline_v2.first_layer's path construction for one plate and reports the model outline, its hull,
the brim polygon and the brim-inside-hull pieces (area, bounds). Read-only.
    /tmp/microduck-cad-venv/bin/python brim_where.py RUN_DIR COLOR MACHINE
"""
import json, re, sys, zipfile, math
from pathlib import Path
from shapely.geometry import LineString
from shapely.ops import unary_union
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'); sys.dont_write_bytecode = True
import release_pipeline_v2 as r2
run, color, machine = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
g, cfg, _ = r2.native_payload(run / 'native' / f'{color}_{machine}' / 'sliced.3mf')
height = float(cfg['initial_layer_print_height'])
offset = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0., 0.]
xyz = [0., 0., 0.]; width = .4; kind = 'Custom'; relative = True; e = 0.; model = []; brim = []
for line in g.decode().splitlines():
    if line.startswith(('; FEATURE:', ';TYPE:')): kind = line.split(':', 1)[1].strip()
    elif line.startswith(('; LINE_WIDTH:', ';WIDTH:')): width = float(line.split(':', 1)[1])
    if line.startswith('M82'): relative = False
    if line.startswith('M83'): relative = True
    if line.startswith('G92 '):
        mm = re.search(r'E([-+\d.]+)', line)
        if mm: e = float(mm[1])
    if not re.match(r'^G[0123] ', line): continue
    v = {k: float(t) for k, t in re.findall(r'([XYZE])([-+]?\d*\.?\d+)', line.split(';')[0])}
    end = [v.get(k, xyz[i]) for i, k in enumerate('XYZ')]; de = v.get('E', 0) if relative else v.get('E', e) - e
    if 'E' in v: e = v['E'] if not relative else e + v['E']
    if de > 0 and kind != 'Custom' and abs(end[2] - height) < 1e-5 and end[:2] != xyz[:2]:
        seg = LineString([(xyz[0] + offset[0], xyz[1] + offset[1]), (end[0] + offset[0], end[1] + offset[1])]).buffer(width / 2)
        kl = kind.lower()
        if 'brim' in kl: brim.append((seg, width))
        elif not any(t in kl for t in ('support', 'skirt')): model.append((seg, width))
    xyz = end
M = unary_union([s for s, _ in model]); B = unary_union([s for s, _ in brim]); H = M.convex_hull
I = B.intersection(H)
print(json.dumps(dict(machine=machine, modelAreaMm2=round(M.area, 1), hullAreaMm2=round(H.area, 1), modelBounds=[round(x, 2) for x in M.bounds],
                      brimAreaMm2=round(B.area, 1), brimInsideHullMm2=round(I.area, 2), brimWidths=sorted({w for _, w in brim}), modelWidths=sorted({w for _, w in model}),
                      insidePieces=[dict(area=round(p.area, 2), bounds=[round(x, 2) for x in p.bounds]) for p in (I.geoms if hasattr(I, 'geoms') else [I]) if p.area > 0.05][:12],
                      hullMinusModelMm2=round(H.difference(M).area, 2))))
