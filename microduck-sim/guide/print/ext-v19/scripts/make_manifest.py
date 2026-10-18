#!/usr/bin/env python3
"""Write ../manifest-ext-v19.json (orientation-check input in the release-manifest part format) for the six V1.9
release parts, with their print poses:
  head_cap_v19      the V1.8 cap pose (release-V1.8/manifest-V1.8.json head_cap rotation: roof down), re-seated on
                    the bed (the V1.9 cap is in the same robot frame);
  speaker_retainer  the flat frame on its speaker-side face;
  clips             the tab's seat face on the bed (seat normal up), so every screw hole is vertical and the channels
                    print without support.
sourceToPrint maps robot-frame mm to the print frame (lowest point on the bed, part centred on the origin in x/y).
flatContact.minimumAreaMm2 is 90 % of the measured bed contact (all three vertices within 0.01 mm of the bed).
Carried over from release-V1.8 for the cap: the Bambu support blocker that keeps the E-pi-04 pilot free of internal
support (the Pi and that pilot do not move in V1.9) and the Orange 4 mm outer brim override (cap tip angle below 10
degrees). The V1.8 zip-tie slot blocker is dropped: the V1.9 cap has no rear notch.
"""
from __future__ import annotations

import json

import numpy as np
import trimesh

import ext_lib as E

COLOR = 'Orange'


def rot_to_z(v):
    """Rotation matrix taking unit vector v to +z (minimal rotation)."""
    v = np.asarray(v, float) / np.linalg.norm(v)
    z = np.array([0, 0, 1.0])
    c = float(v @ z)
    if c > 1 - 1e-12:
        return np.eye(3)
    if c < -1 + 1e-12:
        return np.diag([1.0, -1.0, -1.0])
    a = np.cross(v, z)
    s = np.linalg.norm(a)
    a /= s
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K


def seat(R, mesh):
    V = mesh.vertices @ R.T
    lo, hi = V.min(0), V.max(0)
    t = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def contact(T, mesh):
    V = mesh.vertices @ T[:3, :3].T + T[:3, 3]
    F = mesh.faces
    on = (V[F][:, :, 2] <= 0.01).all(1)
    return float(mesh.area_faces[on].sum())


def main():
    v18 = json.loads((E.GUIDE / 'print' / 'release-V1.8' / 'manifest-V1.8.json').read_text())
    cap18 = next(p for p in v18['parts'] if p['key'] == 'head_cap')
    R_cap = np.array(cap18['sourceToPrint'])[:3, :3]
    clips = json.loads((E.OUT / 'checks' / 'clips-build-v19.json').read_text())
    ret = json.loads((E.OUT / 'checks' / 'retainer-build-v19.json').read_text())
    parts = []
    for key, path in E.PARTS.items():
        m = trimesh.load(path, force='mesh')
        if key == 'head_cap_v19':
            R, why = R_cap, 'V1.8 cap pose (roof on the bed), rotation from release-V1.8/manifest-V1.8.json'
        elif key == 'speaker_retainer_v19':
            R, why = rot_to_z(-np.array(ret['speakerNormal'])), 'flat on its speaker-side face'
        else:
            n = np.array(clips[key]['n'])
            R, why = rot_to_z(n), 'tab seat face on the bed, screw hole vertical'
        T = seat(R, m)
        a = contact(T, m)
        extra = {}
        if key == 'head_cap_v19':
            extra = {'decision': 'replacement', 'replaces': 'head_cap (V1.8)',
                     'supportBlockers': [b for b in cap18.get('supportBlockers', []) if 'pi-positive-y' in b['path']]}
        else:
            extra = {'decision': 'new'}
        parts.append({'key': key, 'color': COLOR, 'quantity': 1, 'path': str(path), 'sha256': E.sha(path), **extra,
                      'sourceFrame': 'robot frame (mm, x forward, y left, z up)', 'sourceToPrint': T.round(9).tolist(),
                      'flatContact': {'minimumAreaMm2': float(np.floor(0.9 * a))}, 'poseOrigin': why,
                      'measuredContactMm2': round(a, 2)})
        print(key, why, 'contact', round(a, 1), flush=True)
    out = {'schemaVersion': 1, 'releaseKind': 'incremental-candidate', 'version': 'ext-v19 (not released, not sliced)',
           'processOverrides': {k: v for k, v in v18.get('processOverrides', {}).items() if k.startswith('Orange')},
           'processOverrideReason': ('Head cap tip angle is below the 10 degree line in '
                                     'guide/print/orientation-study/PRINT-ORIENTATION-PRACTICE.md (V1.9 cap: tipAngleDeg of the '
                                     '"current" candidate in checks/orientation-ext-v19.json); 3 to 5 mm brim, carried over '
                                     'from release-V1.8.'), 'parts': parts}
    E.jdump(out, E.OUT / 'manifest-ext-v19.json')


if __name__ == '__main__':
    main()
