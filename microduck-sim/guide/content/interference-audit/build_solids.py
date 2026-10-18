#!/usr/bin/env python3
"""Step 1: build the audit solid for every guide part and compare it with the guide display mesh.

Source priority per part key (all mapped to the robot frame):
  1. print/world/*.stl for the keys in ia_lib.WORLD_FILE (notched tray, trimmed board, V1.8 head cap, face panel,
     eye trim, lower head shell and the turned camera): the current geometry, superseding any V1.6 release file
     of the same name,
  2. V1.6 release file in print/release-V1.6-final/final-V1.6.json (print-frame files are mapped back with
     inv(sourceToPrint)) when its bounds match the guide part,
  3. the full-resolution source mesh in data/sources/full-build-data-current.json (the guide decimates
     motors and other meshes above 30k triangles), moved by the part's shiftMm (the Pi group: PI_SHIFT),
  4. the exact primitives build_guide_data.py writes (XT30) and the shifted GPIO
     pin 6 socket for pins 8 and 10.
Writes CACHE/solid-<key>.npz, CACHE/solids-manifest.json and interference-audit/solids-report.json.
A part whose input meshes (audit source and guide display mesh) and this script plus ia_lib.py are byte-identical to
the last run reuses that run's record and solid file (CACHE/solids-cache.json); everything else is recomputed.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys

from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

from ia_lib import (CACHE, FINAL, HERE, SRC, V16_KEY, WORLD, WORLD_FILE, decode_guide_part, load_guide, manifold_ok,
                    rnd, solid_path, to_manifold, from_manifold)


def closed(v, f):
    """Return (v, f, how) for a manifold3d-accepted volume, or (v, f, None)."""
    m = trimesh.Trimesh(v, f, process=True)
    man = to_manifold(m.vertices, m.faces)
    if manifold_ok(man) and man.volume() > 0:
        return m.vertices, m.faces, 'as-is (merged duplicate vertices)'
    m2 = m.copy()
    m2.merge_vertices(digits_vertex=4)
    m2.update_faces(m2.nondegenerate_faces())
    m2.update_faces(m2.unique_faces())
    m2.remove_unreferenced_vertices()
    trimesh.repair.fix_normals(m2, multibody=True)
    trimesh.repair.fill_holes(m2)
    man = to_manifold(m2.vertices, m2.faces)
    if manifold_ok(man) and man.volume() > 0:
        return m2.vertices, m2.faces, 'repaired (vertex weld 1e-4 mm, degenerate/duplicate faces removed, normals fixed, holes filled)'
    # Per-body: keep the bodies manifold3d accepts, union them.
    import manifold3d as m3
    bodies = m2.split(only_watertight=False)
    good, bad = [], 0
    for b in bodies:
        mb = to_manifold(b.vertices, b.faces)
        if manifold_ok(mb) and mb.volume() > 0:
            good.append(mb)
        else:
            bad += 1
    if good and bad == 0:
        u = m3.Manifold.batch_boolean(good, m3.OpType.Add)
        vv, ff = from_manifold(u)
        return vv, ff, f'per-body union of {len(good)} closed bodies'
    return m.vertices, m.faces, None


def surface_dev(va, fa, vb, fb, n=4000, seed=0):
    """Two-sided distance: samples (plus vertices) of one surface to the exact closest point on the other."""
    ma, mb = trimesh.Trimesh(va, fa, process=False), trimesh.Trimesh(vb, fb, process=False)
    pa = np.vstack([trimesh.sample.sample_surface(ma, n, seed=seed)[0], va[:: max(1, len(va) // n)]])
    pb = np.vstack([trimesh.sample.sample_surface(mb, n, seed=seed)[0], vb[:: max(1, len(vb) // n)]])
    da = mb.nearest.on_surface(pa)[1]
    db = ma.nearest.on_surface(pb)[1]
    del ma, mb
    return {'displayToSolidMaxMm': rnd(da.max(), 3), 'displayToSolidP99Mm': rnd(np.percentile(da, 99), 3),
            'solidToDisplayMaxMm': rnd(db.max(), 3), 'solidToDisplayP99Mm': rnd(np.percentile(db, 99), 3)}


CODE_HASH = hashlib.sha256(Path(__file__).read_bytes() + (HERE / 'ia_lib.py').read_bytes()).hexdigest()


def input_hash(*arrays):
    h = hashlib.sha256(CODE_HASH.encode())
    for a in arrays:
        a = np.ascontiguousarray(a)
        h.update(str((a.dtype.str, a.shape)).encode())
        h.update(a.tobytes())
    return h.hexdigest()


def main():
    cache_file = CACHE / 'solids-cache.json'
    try:
        cache = json.loads(cache_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}
    new_cache, reused = {}, 0
    guide = load_guide()
    gparts = {p['key']: p for p in guide['parts']}
    src = json.loads(SRC.read_text())
    sparts = {p['key']: p for p in src['parts'] if p['key'] in gparts or p['key'] == 'head_pi_gpio_pin_06_receiving'}
    del src
    final = json.loads(FINAL.read_text())
    v16 = {V16_KEY.get(p['key'], p['key']): p for p in final['parts']}
    report, man = [], {}
    for key, gp in gparts.items():
        gv, gf = decode_guide_part(gp)
        gb = np.array(gp['bounds'])
        rec = {'key': key, 'name': gp['name'], 'module': gp['module'], 'status': gp['status'],
               'displayTriangles': int(len(gf))}
        alt = []
        v16_world = False
        shift = np.asarray(gp.get('shiftMm') or [0.0, 0.0, 0.0], float)
        if key in v16 and key not in WORLD_FILE:
            e = v16[key]
            m = trimesh.load(e['path'], force='mesh', process=False)
            raw = np.asarray(m.vertices, float)
            v16_world = np.abs(np.array([raw.min(0), raw.max(0)]) - gb).max() < 0.05
        if key in WORLD_FILE:
            # Tray (port notch), board, and the V1.8 head set (cap Pi seat, plate-only face, trim pilots, windowless
            # shell, turned camera): the print/world file is the current geometry, whatever V1.6 released.
            m = trimesh.load(WORLD / WORLD_FILE[key], force='mesh', process=False)
            v, f = np.asarray(m.vertices, float), np.asarray(m.faces)
            rec['source'] = {'kind': 'print/world STL' + (' (current part; supersedes the V1.6 release file of the same name)' if key in v16 else ''),
                             'path': str(WORLD / WORLD_FILE[key])}
        elif v16_world:
            v, f = raw, np.asarray(m.faces)
            rec['source'] = {'kind': 'V1.6 release (robot-frame file)', 'path': e['path'], 'v16Key': e['key']}
        elif key in sparts:
            sp = sparts[key]
            v = np.frombuffer(base64.b64decode(sp['positionB64']), '<f4').reshape(-1, 3).astype(float) + shift
            f = np.frombuffer(base64.b64decode(sp['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
            rec['source'] = {'kind': 'full-build source mesh' + (f' moved {shift.tolist()}' if shift.any() else '') + (' (V1.6 release geometry, see v16-registration.json)' if key in v16 else ''),
                             'path': sp.get('sourceFile') or sp.get('stockFile') or 'manufacturer CAD (embedded)',
                             'geometryKind': sp.get('geometryKind')}
        elif key in ('head_pi_gpio_pin_08_receiving', 'head_pi_gpio_pin_10_receiving'):
            sp = sparts['head_pi_gpio_pin_06_receiving']
            dy = -2.54 if key.endswith('08_receiving') else -5.08
            v = np.frombuffer(base64.b64decode(sp['positionB64']), '<f4').reshape(-1, 3).astype(float) + [0, dy, 0] + shift
            f = np.frombuffer(base64.b64decode(sp['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
            rec['source'] = {'kind': 'pin 06 receiving envelope shifted (as build_guide_data.py)', 'dy': dy}
        else:
            v, f = gv, gf
            rec['source'] = {'kind': 'guide primitive (build_guide_data.py box/cylinder envelope)'}
        digest = input_hash(np.asarray(v, float), np.asarray(f, np.int64), gv, gf)
        hit = cache.get(key)
        if hit and hit['hash'] == digest and solid_path(key).exists():
            rec, man[key] = hit['rec'], hit['man']
            report.append(rec)
            new_cache[key] = hit
            reused += 1
            continue
        vv, ff, how = closed(v, f)
        rec['closedVolume'] = how is not None
        rec['closure'] = how or 'NOT a closed volume: exact boolean not possible; display-mesh method only'
        if how:
            rec['volumeMm3'] = rnd(trimesh.Trimesh(vv, ff, process=False).volume, 2)
        rec['bounds'] = rnd([vv.min(0), vv.max(0)], 3)
        rec['displayVsSolid'] = surface_dev(gv, gf, vv, ff)
        for label, sp in alt:
            av = np.frombuffer(base64.b64decode(sp['positionB64']), '<f4').reshape(-1, 3).astype(float)
            af = np.frombuffer(base64.b64decode(sp['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
            rec.setdefault('alternates', []).append({'label': label, 'path': sp.get('sourceFile'),
                                                    'vsAuditSolid': surface_dev(av, af, vv, ff)})
        np.savez_compressed(solid_path(key), v=vv.astype(np.float64), f=ff.astype(np.int64))
        man[key] = {'closed': rec['closedVolume'], 'bounds': rec['bounds'], 'source': rec['source']['kind'],
                    'module': gp['module'], 'status': gp['status'], 'tris': int(len(ff))}
        report.append(rec)
        new_cache[key] = {'hash': digest, 'rec': rec, 'man': man[key]}
        import gc; gc.collect()
        print(key, rec['source']['kind'], rec['closure'][:40], rec['displayVsSolid']['displayToSolidMaxMm'],
              rec['displayVsSolid']['solidToDisplayMaxMm'], file=sys.stderr, flush=True)
    (CACHE / 'solids-manifest.json').write_text(json.dumps(man, indent=1))
    cache_file.write_text(json.dumps(new_cache))
    print(f'reused {reused} of {len(report)} parts unchanged since the last run', file=sys.stderr)
    out = {'parts': len(report), 'closed': sum(r['closedVolume'] for r in report),
           'notClosed': [r['key'] for r in report if not r['closedVolume']], 'records': report}
    (HERE / 'solids-report.json').write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ('parts', 'closed', 'notClosed')}))


if __name__ == '__main__':
    main()
