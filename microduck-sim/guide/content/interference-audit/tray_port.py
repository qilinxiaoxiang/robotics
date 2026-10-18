#!/usr/bin/env python3
"""Step 5: the OpenRB side DYNAMIXEL ports against the tray side rails (exact, manifold3d).

The OpenRB-150 side-entry 3-pin headers are read from the board solid: each housing spans x -64.7..-54.7,
|y| 4.6..12.7 (mouth at the board edge, |y| = 12.7), z -48.85..-44.65 (sections in README). The tray side rails
(print/tray/tray.py: rails_x -85.5..-58.4, rail_y 13.3..15.3, top z -43.5) stand 0.6 mm outside that mouth.
A mated plug must stand out of the mouth; PLUG_OUT is the assumed plug-plus-wire-exit envelope beyond the
board edge (inference: JST EHR-3 housing body and the bend of three 0.6 mm wires, not measured on a part).
The script intersects that envelope with the V1.6 tray, cuts the proposed rail notch from the tray, and
re-checks the envelope and the dxl-r5 / dxl-l10 first cable segment against the notched tray.
Writes tray-port.json and the notched-tray mesh to the cache for render.py.
"""
from __future__ import annotations

import json

import manifold3d as m3d
import numpy as np
import trimesh

from cables import spline_samples
from ia_lib import CACHE, HERE, from_manifold, load_guide, load_solid, manifest, rnd, to_manifold

HOUSING_X = (-64.7, -54.7)
HOUSING_Z = (-48.85, -44.65)
MOUTH_Y = 12.7
PLUG_OUT = 10.0          # assumed envelope beyond the board edge, mm (inference)
NOTCH = {'x': (-66.2, -58.0), 'absY': (13.0, 15.7), 'z': (-49.4, -43.0)}   # proposed cut, each side


def box(x, y, z):
    return m3d.Manifold.cube([x[1] - x[0], y[1] - y[0], z[1] - z[0]]).translate([x[0], y[0], z[0]])


def main():
    man = manifest()
    tray = to_manifold(*load_solid('openrb_tray'))
    res = {'housingFromBoardSolid': {'x': HOUSING_X, 'z': HOUSING_Z, 'mouthAbsY': MOUTH_Y},
           'plugEnvelopeBeyondEdgeMm': PLUG_OUT, 'plugEnvelopeIsInference': True, 'notch': NOTCH, 'sides': {}}
    notched = tray
    for s in (-1, 1):
        y0, y1 = sorted((s * NOTCH['absY'][0], s * NOTCH['absY'][1]))
        notched = notched - box(NOTCH['x'], (y0, y1), NOTCH['z'])
    for s, name in ((-1, '-Y port (link R, dxl-r5)'), (1, '+Y port (link L, dxl-l10)')):
        y0, y1 = sorted((s * MOUTH_Y, s * (MOUTH_Y + PLUG_OUT)))
        plug = box(HOUSING_X, (y0, y1), HOUSING_Z)
        inter = plug ^ tray
        v, f = from_manifold(inter)
        # gap from the mouth plane to the rail inner face, and the rail's share of the mouth width
        rec = {'plugEnvelopeVsTrayMm3': rnd(inter.volume(), 2),
               'overlapBounds': rnd([v.min(0), v.max(0)], 2) if len(v) else None,
               'mouthToRailInnerFaceMm': rnd(13.3 - MOUTH_Y, 2),
               'mouthWidthBlockedByRailMm': rnd(max(0.0, min(HOUSING_X[1], -58.4) - HOUSING_X[0]), 2),
               'plugEnvelopeVsNotchedTrayMm3': rnd((plug ^ notched).volume(), 3)}
        # anything else in the plug envelope (final scene)
        others = {}
        pb = np.array([[HOUSING_X[0], min(y0, y1), HOUSING_Z[0]], [HOUSING_X[1], max(y0, y1), HOUSING_Z[1]]])
        for k, m in man.items():
            if k in ('openrb_tray', 'openrb_board'):
                continue
            b = np.array(m['bounds'])
            if np.any(b[0] > pb[1]) or np.any(b[1] < pb[0]):
                continue
            vol = (plug ^ to_manifold(*load_solid(k))).volume()
            if vol > 0.01:
                others[k] = rnd(vol, 2)
        rec['plugEnvelopeVsOtherPartsMm3'] = others
        res['sides'][name] = rec
    # the drawn first segment of each side link against the original and the notched tray
    g = load_guide()
    tm0 = trimesh.Trimesh(*load_solid('openrb_tray'), process=False)
    tm1 = trimesh.Trimesh(*from_manifold(notched), process=False)
    for c in g['cables']:
        if c['id'] not in ('dxl-r5', 'dxl-l10'):
            continue
        r = float(c.get('radius') or 0.9)
        x, seg = spline_samples(c['path'])
        x = x[seg == 0]
        d0 = trimesh.proximity.signed_distance(tm0, x) + r
        d1 = trimesh.proximity.signed_distance(tm1, x) + r
        res['sides'][f"{'-Y' if c['id'] == 'dxl-r5' else '+Y'} port (link {'R' if c['id'] == 'dxl-r5' else 'L'}, {c['id']})"]['cableSeg0DepthMm'] = {
            'current': rnd(float(d0.max()), 3), 'notched': rnd(float(d1.max()), 3)}
    res['trayVolumeMm3'] = {'current': rnd(tray.volume(), 1), 'notched': rnd(notched.volume(), 1)}
    # remaining rail section at the notch (cantilever stiffener root) - geometry only, stiffness not computed
    res['railAtNotch'] = {'zFrom': -54.3, 'zTo': NOTCH['z'][0], 'heightMm': rnd(NOTCH['z'][0] + 54.3, 2), 'fullRailHeightMm': rnd(-43.5 + 54.3, 2)}
    v, f = from_manifold(notched)
    np.savez_compressed(CACHE / 'tray-notched.npz', v=v, f=f)
    (HERE / 'tray-port.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
