"""Read a guide (guide-data.json or a page built by build_guide.py) and place its parts as viewer/app.js does.

Project-neutral: everything comes from the guide data itself (parts, steps, approach, group, pose, flex) plus an
optional adapter JSON (see ../README.md, "Audits"):

    {"solids": {"<part key>": "/abs/path.stl"},     closed meshes to use instead of the display mesh
     "flexible": ["wire_*", "zip_*"],               fnmatch globs of parts never swept (cables, ties)
     "designedContacts": [{"a": "glob", "b": "glob", "why": "press fit"}],   final-pose overlaps that are designed
     "ignoreSteps": ["overview"],                   inventory steps that play no motion
     "apart": [["alt_a_*", "alt_b_*"]],             swap alternatives that never meet (pair audit skips them)
     "stagger": "items" | "units"}                  viewer timeline: kit default "items"

Needs numpy, trimesh and manifold3d (guide-kit/requirements-audit.txt).
"""
from __future__ import annotations

import base64
import fnmatch
import gzip
import json
import re
from pathlib import Path

import numpy as np

EASE = lambda t: 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
STAGGER_W = 0.55          # app.js buildTimeline: each staggered item moves over 55 % of the parts phase


# ----------------------------------------------------------------------------- loading
def load_guide(path: Path) -> dict:
    """guide-data.json, or the data and geometry blocks of a built page (parts get positionB64/indexB64 back)."""
    raw = Path(path).read_bytes()
    if not raw.lstrip()[:1] == b'<':
        return json.loads(raw)
    text = raw.decode('utf-8')
    block = lambda bid: re.search(r'<script[^>]*id="%s"[^>]*>([^<]*)</script>' % bid, text)
    data = json.loads(gzip.decompress(base64.b64decode(block('guide-data').group(1))))
    gm = block('guide-geometry')
    if not gm:
        raise SystemExit(f'{path}: geometry is in external scripts; pass guide-data.json instead')
    blob = gzip.decompress(base64.b64decode(gm.group(1)))
    for p in data['parts']:
        g = p.get('geom')
        if g:
            po, pb, io, ib = g
            p['_pos'] = np.frombuffer(blob[po:po + pb], '<f4').reshape(-1, 3).astype(float)
            p['_idx'] = np.frombuffer(blob[io:io + ib], '<u4').reshape(-1, 3).astype(np.int64)
    return data


def part_mesh(p: dict):
    if '_pos' in p:
        return p['_pos'], p['_idx']
    v = np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3).astype(float)
    f = np.frombuffer(base64.b64decode(p['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
    return v, f


def load_adapter(path: Path | None) -> dict:
    a = json.loads(Path(path).read_text()) if path else {}
    a.setdefault('solids', {}); a.setdefault('flexible', []); a.setdefault('designedContacts', [])
    a.setdefault('ignoreSteps', []); a.setdefault('stagger', 'items'); a.setdefault('apart', [])
    return a


def matches(key: str, globs) -> bool:
    return any(fnmatch.fnmatchcase(key, g) for g in globs)


# ----------------------------------------------------------------------------- solids
class Solids:
    """Closed manifold3d solids per part key. A part whose mesh is not a closed volume is reported, never guessed."""

    def __init__(self, guide: dict, adapter: dict):
        import manifold3d  # noqa: F401
        self.parts = {p['key']: p for p in guide['parts']}
        self.adapter = adapter
        self.cache: dict = {}
        self.failed: dict[str, str] = {}

    def get(self, key: str):
        if key in self.cache:
            return self.cache[key]
        import manifold3d as m3
        import trimesh
        src = self.adapter['solids'].get(key)
        if src:
            tm = trimesh.load(src, force='mesh', process=True)
            v, f = np.asarray(tm.vertices, float), np.asarray(tm.faces, np.int64)
        else:
            v, f = part_mesh(self.parts[key])
        man = None
        for attempt in range(2):
            mesh = m3.Mesh(vert_properties=np.ascontiguousarray(v, np.float32), tri_verts=np.ascontiguousarray(f, np.uint32))
            if attempt:
                mesh.merge()
            cand = m3.Manifold(mesh)
            if cand.status() == m3.Error.NoError and cand.volume() > 0:
                man = cand
                break
            if attempt == 0:   # weld duplicate vertices (glTF splits them at hard edges) and retry
                tm = trimesh.Trimesh(v, f, process=True)
                trimesh.repair.fix_normals(tm)
                v, f = np.asarray(tm.vertices, float), np.asarray(tm.faces, np.int64)
        if man is None:
            self.failed[key] = 'not a closed volume (give the adapter a solid for it)'
        self.cache[key] = man
        return man


def bbox(m):
    b = np.asarray(m.bounding_box(), float)
    return b[:3], b[3:]


def boxes_touch(a, b, pad=0.0) -> bool:
    return bool(np.all(a[0] - pad <= b[1]) and np.all(b[0] - pad <= a[1]))


def thickness(m) -> float:
    """Area-weighted median local thickness of an overlap solid (inward rays), as pairs.py measures depthMm."""
    import trimesh
    out = m.to_mesh()
    v, f = np.asarray(out.vert_properties)[:, :3].astype(float), np.asarray(out.tri_verts, np.int64)
    if not len(f):
        return 0.0
    tm = trimesh.Trimesh(v, f, process=False)
    if tm.area <= 0:
        return 0.0
    pts, fi = trimesh.sample.sample_surface(tm, 200, seed=0)
    nrm = tm.face_normals[fi]
    org = pts - nrm * 1e-4
    loc, ir, _ = trimesh.ray.ray_triangle.RayMeshIntersector(tm).intersects_location(org, -nrm, multiple_hits=True)
    d = np.full(len(pts), np.nan)
    if len(loc):
        dist = np.linalg.norm(loc - org[ir], axis=1)
        for r, dd in zip(ir[dist > 2e-4], dist[dist > 2e-4]):
            if np.isnan(d[r]) or dd < d[r]:
                d[r] = dd
    d = d[~np.isnan(d)]
    return float(np.median(d)) if len(d) else 0.0


# ----------------------------------------------------------------------------- steps as the viewer plays them
def to_path(v):
    if v is None:
        return None
    if len(v) == 3 and not isinstance(v[0], (list, tuple)):
        return np.array([v, [0, 0, 0]], float)
    pts = [[float(x) for x in w] for w in v]
    if any(pts[-1]):
        pts.append([0.0, 0.0, 0.0])
    return np.array(pts, float) if len(pts) > 1 else None


def path_at(path, e):
    lens = np.linalg.norm(np.diff(path, axis=0), axis=1)
    total = lens.sum()
    if total <= 0:
        return path[-1]
    d = e * total
    for k, ln in enumerate(lens):
        if d <= ln or k == len(lens) - 1:
            t = min(1.0, d / ln) if ln > 0 else 1.0
            return path[k] + (path[k + 1] - path[k]) * t
        d -= ln
    return path[-1]


def rot_about(axis, deg, pivot):
    a = np.asarray(axis, float); a = a / np.linalg.norm(a)
    t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    R = np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K
    p = np.asarray(pivot, float)
    return np.c_[R, p - R @ p]


def flex_at(f, e):
    w0, w1 = f['window']
    return 0.0 if e <= 0 or e >= 1 else e / w0 if e < w0 else 1.0 if e <= w1 else (1 - e) / (1 - w1)


def resolve_steps(g: dict) -> list[dict]:
    """Step lists resolved like app.js: modules expand, add wins over show, show over context."""
    mods: dict[str, list[str]] = {}
    for p in g['parts']:
        mods.setdefault(p.get('module'), []).append(p['key'])
    res = lambda lst: list(dict.fromkeys(k for r in (lst or []) for k in (mods[r] if r in mods else [r])))
    order = {c['id']: i for i, c in enumerate(g.get('chapters') or [])}
    out = []
    for n, s in enumerate(sorted(g['steps'], key=lambda s: order.get(s.get('chapter'), 0))):
        add = res(s.get('add'))
        show = [k for k in res(s.get('show')) if k not in add]
        ctx = [k for k in res(s.get('context')) if k not in add and k not in show]
        appr = {}
        for ref, vec in (s.get('approach') or {}).items():
            for k in res([ref]):
                if k in add:
                    appr[k] = vec
        if s.get('group'):
            appr = {k: s['group']['approach'] for k in add}
        pose = None
        if s.get('pose'):
            pr = s['pose']
            pose = {'set': res(pr.get('parts')), 'pivot': pr['pivot'], 'axis': pr['axis'], 'deg': float(pr['deg']),
                    'from': float(pr.get('from', pr['deg']))}
        flex = None
        if s.get('flex'):
            fr = s['flex']
            flex = {'set': res(fr.get('parts')), 'riders': {kk: int(np.sign(v)) for k, v in (fr.get('riders') or {}).items() for kk in res([k])},
                    'ramp': fr['ramp'], 'spread': fr['spread'], 'shift': float(fr.get('shift', 0.0)), 'window': fr['window']}
        out.append({'id': s['id'], 'title': s.get('title'), 'chapter': s.get('chapter'), 'add': add, 'show': show, 'ctx': ctx,
                    'approach': appr, 'group': bool(s.get('group')), 'pose': pose, 'flex': flex, 'bench': bool(s.get('bench'))})
    return out


def timeline(step: dict, stagger: str = 'items') -> list[dict]:
    """app.js buildTimeline: each added part gets a window [a, a + w] of the parts phase; staggered unless a group."""
    items = [{'key': k, 'path': to_path(step['approach'].get(k))} for k in step['add']]
    if stagger == 'units':
        units = list(dict.fromkeys(json.dumps(None if it['path'] is None else it['path'].tolist()) for it in items))
        idx = lambda it: units.index(json.dumps(None if it['path'] is None else it['path'].tolist()))
        n = len(units)
    else:
        idx, n = (lambda it: items.index(it)), len(items)
    stag = n > 1 and not step['group']
    w = STAGGER_W if stag else 1.0
    for it in items:
        it['a'] = idx(it) * (1 - w) / (n - 1) if stag else 0.0
        it['w'] = w
    return items


def placement(step: dict, item: dict | None, key: str, pp: float):
    """(3x4 affine or None, translation) of part key at parts-phase progress pp, plus flex warp fraction."""
    pose = step['pose']
    aff = None
    if pose and key in pose['set']:
        swing = pose['from'] != pose['deg']
        ang = pose['from'] + (pose['deg'] - pose['from']) * EASE(pp) if swing else pose['deg']
        if ang:
            aff = rot_about(pose['axis'], ang, pose['pivot'])
    off = np.zeros(3)
    if item is not None and item['path'] is not None:
        t = min(1.0, max(0.0, (pp - item['a']) / item['w']))
        off = path_at(item['path'], EASE(t))
        fl = step['flex']
        if fl and key in fl['riders']:
            sg = fl['riders'][key]
            off = off + np.array([0.0, (sg * (fl['spread'][0] if sg < 0 else fl['spread'][1]) + fl['shift']) * flex_at(fl, EASE(pp)), 0.0])
    return aff, off


def posed_solid(S: Solids, step: dict, key: str, item, pp: float):
    m = S.get(key)
    if m is None:
        return None
    aff, off = placement(step, item, key, pp)
    fl = step['flex']
    if fl and key in fl['set']:
        a = flex_at(fl, EASE(pp))
        if a:
            (r0, r1), (sn, sp), sh = fl['ramp'], fl['spread'], fl['shift']
            def warp(v, a=a):
                v = np.array(v, dtype=float, copy=True)
                w = np.clip((np.abs(v[:, 1]) - r0) / (r1 - r0), 0, 1)
                v[:, 1] += (np.where(v[:, 1] < 0, -sn, sp) * w + sh) * a
                return v
            m = m.warp_batch(warp)
    if aff is not None:
        m = m.transform(aff)
    return m.translate(list(off)) if np.any(off) else m
