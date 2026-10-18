#!/usr/bin/env python3
"""Read back one native study slice: ETA, total grams, grams per feature (model / support / brim), layer count,
and the release pipeline's own first-layer model area.

    run_bounded_cad.py ... -- /tmp/microduck-cad-venv/bin/python scripts/slice_readback.py RUN_DIR COLOR MACHINE OUT.json

RUN_DIR is a release-pipeline preparation directory (preparation.json, <Color>_<Machine>_editable.3mf,
native/<Color>_<Machine>/sliced.3mf). Grams per feature come from the extruded filament length per G-code feature
label times the profile's filament diameter and density; the total is cross-checked against the slicer's header.
Read-only on all inputs.
"""
import json
import math
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PIPE = Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009')
sys.path.insert(0, str(PIPE))
import release_pipeline as rp  # noqa: E402


def category(kind):
    k = kind.lower()
    if 'support' in k:
        return 'supportInterface' if 'interface' in k else 'support'
    if 'brim' in k or 'skirt' in k:
        return 'brimSkirt'
    if k in ('custom', 'prime tower', 'wipe tower', '') or 'purge' in k or 'wipe' in k:
        return 'machine'
    if 'bridge' in k:
        return 'bridge'
    if 'overhang' in k:
        return 'overhangWall'
    return 'model'


def feature_lengths(g):
    kind, relative, e = 'Custom', True, 0.0
    total = {}
    for line in g.decode(errors='replace').splitlines():
        if line.startswith(('; FEATURE:', ';TYPE:')):
            kind = line.split(':', 1)[1].strip()
            continue
        if line.startswith('M82'):
            relative = False
        elif line.startswith('M83'):
            relative = True
        elif line.startswith('G92 '):
            m = re.search(r'E([-+\d.]+)', line)
            if m:
                e = float(m[1])
        if not re.match(r'^G[0123] ', line):
            continue
        body = line.split(';')[0]
        me = re.search(r'E([-+]?\d*\.?\d+)', body)
        if me:
            v = float(me[1])
            de = v if relative else v - e
            e = e + v if relative else v
            # Count only extrusion that moves the nozzle; a bare "G1 E.." is an unretract, not deposited plastic.
            if de > 0 and (re.search(r'[XY]', body) or body.startswith(('G2', 'G3'))):
                c = category(kind)
                total[c] = total.get(c, 0.0) + de
    return total


def layer_info(g):
    zs = re.findall(rb'^; Z_HEIGHT: ([\d.]+)|^;Z:([\d.]+)', g, re.M)
    vals = sorted({float(a or b) for a, b in zs})
    return len(vals), (vals[-1] if vals else None)


def main():
    run, color, machine, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    archive = run / 'native' / f'{color}_{machine}' / 'sliced.3mf'
    project = run / f'{color}_{machine}_editable.3mf'
    g, cfg, _ = rp.native_payload(archive)
    seconds = rp.time_seconds(g, machine)
    pat = r'total filament weight \[g\]\s*:\s*([\d.]+)' if machine == 'Bambu' else r'total filament used \[g\]\s*=\s*([\d.]+)'
    header_g = float(re.search(pat, g.decode(errors='replace'))[1])
    dia = float(cfg['filament_diameter'][0])
    rho = float(cfg['filament_density'][0])
    mm = feature_lengths(g)
    to_g = math.pi * (dia / 2) ** 2 * rho / 1000.0
    grams = {k: round(v * to_g, 2) for k, v in sorted(mm.items())}
    part_g = sum(v for k, v in grams.items() if k not in ('machine',))
    first, footprint = rp.first_layer(g, project, machine)
    n_layers, top = layer_info(g)
    res = dict(archive=rp.ref(archive), project=rp.ref(project), machine=machine, color=color,
               etaSeconds=seconds, etaMinutes=round(seconds / 60, 1), headerGrams=header_g,
               gramsByFeature=grams, supportGrams=round(grams.get('support', 0) + grams.get('supportInterface', 0), 2),
               partGramsFromToolpaths=round(part_g, 2), layerHeight=float(cfg['layer_height']), layers=n_layers, topZ=top,
               firstLayer=first, allLayerFootprint=footprint['allLayerModelSupportBrimBounds'],
               note='Grams per feature = extruded length x filament cross-section x density; machine/purge moves excluded.')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({k: res[k] for k in ('etaMinutes', 'headerGrams', 'supportGrams', 'partGramsFromToolpaths', 'layers')}))


if __name__ == '__main__':
    main()
