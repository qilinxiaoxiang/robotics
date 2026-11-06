#!/usr/bin/env python3
"""Exact final-pose pair audit: which parts overlap each other where the guide seats them?

    python3 pair_audit.py --guide <guide-data.json | built page.html> [--adapter adapter.json] [--out report.json]

Every pair of parts whose boxes touch (0.1 mm pad) is intersected exactly (manifold3d) at its world pose. An
overlap above VOL_TOL mm^3 with median local thickness above THICK_MM is a finding unless the adapter lists the
pair under `designedContacts` (a seam, press fit or mated plug, each with its reason) or under `apart` (swap
alternatives that are never on the robot together). Flexible parts are skipped. Exit status 1 on any finding or
any part that is not a closed volume.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guide_geom import Solids, bbox, boxes_touch, load_adapter, load_guide, matches, thickness  # noqa: E402

VOL_TOL = 0.5
THICK_MM = 0.1


def designed(adapter, a, b):
    for c in adapter['designedContacts']:
        if (matches(a, [c['a']]) and matches(b, [c['b']])) or (matches(b, [c['a']]) and matches(a, [c['b']])):
            return c.get('why', 'designed contact')
    return None


def apart(adapter, a, b):
    return any((matches(a, [x]) and matches(b, [y])) or (matches(b, [x]) and matches(a, [y])) for x, y in adapter['apart'])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--guide', required=True, type=Path)
    ap.add_argument('--adapter', type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args(argv)
    g = load_guide(a.guide)
    adapter = load_adapter(a.adapter)
    S = Solids(g, adapter)
    keys = [p['key'] for p in g['parts'] if not matches(p['key'], adapter['flexible'])]
    solids = {k: S.get(k) for k in keys}
    solids = {k: m for k, m in solids.items() if m is not None}
    boxes = {k: bbox(m) for k, m in solids.items()}
    ks = list(solids)
    findings, accepted, candidates = [], [], 0
    for i, x in enumerate(ks):
        for y in ks[i + 1:]:
            if not boxes_touch(boxes[x], boxes[y], 0.1) or apart(adapter, x, y):
                continue
            candidates += 1
            inter = solids[x] ^ solids[y]
            vol = inter.volume()
            if vol <= VOL_TOL:
                continue
            t = thickness(inter)
            if t <= THICK_MM:
                continue
            rec = {'a': x, 'b': y, 'volumeMm3': round(vol, 2), 'thicknessMedianMm': round(t, 3)}
            why = designed(adapter, x, y)
            (accepted if why else findings).append(rec | ({'why': why} if why else {}))
    findings.sort(key=lambda r: -r['volumeMm3'])
    summary = {'guide': str(a.guide), 'parts': len(ks), 'candidatePairs': candidates, 'findings': len(findings),
               'designedContacts': len(accepted), 'unaudited': S.failed}
    if a.out:
        a.out.write_text(json.dumps({'summary': summary, 'findings': findings, 'designed': accepted}, indent=1) + '\n')
    print(json.dumps(summary))
    return 1 if findings or S.failed else 0


if __name__ == '__main__':
    sys.exit(main())
