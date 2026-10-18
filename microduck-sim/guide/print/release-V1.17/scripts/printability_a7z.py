"""V1.17 pre-slice printability check of the three A7Z head parts in their release print poses (read-only on all sources).

    /tmp/microduck-cad-venv/bin/python scripts/printability_a7z.py   (through run_bounded_cad.py)

For each new part against the part it replaces, in the same print pose:
- sha256 of every source (pinned) and, for cap and clip, that the new part is the old part with material only removed
  (new minus old has no volume; old minus new is the removed volume);
- orientation_check.metrics(): contact, height, tip angle, overhang area at 45/55/60 deg, support proxy, down-facing hole ends;
- new faces: triangles of the new part that do not lie on the old part's surface, split by print-frame normal into
  down-facing (overhang steeper than 45 / 60 deg from vertical), up-facing and side faces;
- layer islands: the mesh is cut at the middle of every 0.2 mm layer; an island is a section polygon that touches nothing of
  the layer below (it starts in mid-air and needs support or a bridge). Islands are reported with their print z, area and
  robot-frame centre; the A7Z list is compared with the V1.9 list;
- cap only: the E-pi-04 pilot (fasteners.json axis) against the V1.8 Bambu support blocker: share of the pilot's empty core
  and of a ring 2 mm round it that lies inside the blocker, before and after;
- clip only: bed contact before and after (the notch must not reach the bed face) and body count;
- face: the print file against the robot-frame twin under the V1.8 face transform (max vertex deviation).
Writes review/a7z-printability.json.
"""
import hashlib, json, math, sys
from pathlib import Path
import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
sys.path.insert(0, str(PRINT / 'orientation-study'))
from orientation_check import metrics, detect_holes, load_mesh  # noqa: E402

PIN = {
    PRINT / 'a7z-head/head_cap_a7z-world.stl': 'bbedb8044687c86906cdcf1adb82eae5c3c5f8bb84fc8bdd24f5824375b5e257',
    PRINT / 'a7z-head/clip_cap_a7z-world.stl': 'ab50937dac7f6bf43bca5eb083d28a1369cedc7a97082f6abc8ddaa85d562d21',
    PRINT / 'face-a7z/face_panel_a7z-print.stl': 'fc236c27ad3f378c2bd7d5ba690877ae2beb5ee148b38194c4e045a5bce6c3ad',
    PRINT / 'face-a7z/face_panel_a7z.stl': 'ff0fa31c726fa0bd5b8d31602126bf4995d445b7d60c0e8e7c9e634314611ef1',
    PRINT / 'ext-v19/head_cap_v19-world.stl': 'da655c657979c9290a1aa12d813901062baea2c38c0da31db085c986277976c2',
    PRINT / 'ext-v19/clip_cap_v19-world.stl': 'dc1973a6e640e730fe272ec3c3bda9202eb1ac4771636de608fba8a18231723e',
}
V19 = {p['key']: p for p in json.loads((PRINT / 'release-V1.9/manifest-V1.9.json').read_text())['parts']}
V18 = {p['key']: p for p in json.loads((PRINT / 'release-V1.8/manifest-V1.8.json').read_text())['parts']}
BLOCKER = PRINT / 'release-V1.8/blockers/pi-positive-y-upper-hole-support-blocker-v18-world.stl'
SCREW = next(s for s in json.loads((PRINT.parent / 'content/fasteners.json').read_text())['screws'] if s['id'] == 'E-pi-04')
LAYER = 0.2


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def posed(mesh, T):
    m = mesh.copy(); m.apply_transform(np.array(T, float)); dz = -m.bounds[0, 2]; m.apply_translation([0, 0, dz])
    Tf = np.array(T, float); Tf[2, 3] += dz
    return m, Tf


def islands(m, Tinv):
    zs = np.arange(LAYER / 2, m.bounds[1, 2], LAYER)
    secs = m.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=list(zs))
    prev = None; out = []
    for z, s in zip(zs, secs):
        polys = [] if s is None else [p for p in s.polygons_full if p.area > 1e-4]
        # section_multiplane returns 2D paths in the plane frame; for a z plane with origin at 0 that frame is x, y
        if prev is not None:
            for p in polys:
                if not p.intersects(prev):
                    c = p.centroid; w = Tinv @ np.array([c.x, c.y, z, 1.0])
                    out.append(dict(printZ=round(float(z), 2), areaMm2=round(p.area, 2), robotCentre=[round(float(x), 1) for x in w[:3]]))
        prev = unary_union(polys) if polys else Polygon()
    return out


def dist(mesh, P, chunk=1500):
    """Unsigned distance to the surface, in chunks (keeps the rtree candidate lists small)."""
    q = trimesh.proximity.ProximityQuery(mesh)
    return np.concatenate([q.on_surface(P[i:i + chunk])[1] for i in range(0, len(P), chunk)]) if len(P) else np.zeros(0)


def contains(mesh, P, chunk=800):
    return np.concatenate([mesh.contains(P[i:i + chunk]) for i in range(0, len(P), chunk)]) if len(P) else np.zeros(0, bool)


def new_faces(new, old, Tp):
    """Triangles of new (print frame) whose centroid is more than 0.005 mm from the old surface (print frame)."""
    d = dist(old, new.triangles_center); print('  new faces measured', flush=True)
    sel = d > 0.005; n = new.face_normals[sel]; a = new.area_faces[sel]
    down45 = -n[:, 2] > math.sin(math.radians(45)); down60 = -n[:, 2] > math.sin(math.radians(60))
    up = n[:, 2] > math.sin(math.radians(45))
    c = new.triangles_center[sel][down45]
    Tinv = np.linalg.inv(Tp); w = (np.c_[c, np.ones(len(c))] @ Tinv.T)[:, :3] if len(c) else np.zeros((0, 3))
    return dict(newFaceAreaMm2=round(float(a.sum()), 1), downFacingOver45degMm2=round(float(a[down45].sum()), 2),
                downFacingOver60degMm2=round(float(a[down60].sum()), 2), upFacingMm2=round(float(a[up].sum()), 1),
                sideMm2=round(float(a[~down45 & ~up].sum()), 1),
                downFacingPrintZ=[round(float(c[:, 2].min()), 2), round(float(c[:, 2].max()), 2)] if len(c) else None,
                downFacingRobotBox=[np.round(w.min(0), 1).tolist(), np.round(w.max(0), 1).tolist()] if len(w) else None)


def pick(mt):
    return {k: mt[k] for k in ('heightMm', 'footprintMm', 'contactMm2', 'firstLayerSectionMm2', 'tipAngleDeg', 'overhang45Mm2',
                               'overhang55Mm2', 'overhang60Mm2', 'supportProxyMm3', 'supportOnModelMm2', 'holeEndsFacingDown',
                               'bossFacesFacingDown', 'holesVertical', 'holesInclined', 'holesHorizontal')}


def blocker_cover(cap_world):
    b = trimesh.load(BLOCKER, force='mesh')
    a = np.asarray(SCREW['axis'], float); a /= np.linalg.norm(a); c0 = np.asarray(SCREW['center'], float)
    u = np.cross(a, [0, 0, 1.0]); u /= np.linalg.norm(u); v = np.cross(a, u)
    out = {}
    for name, r0, r1 in (('pilotCore', 0.0, 0.8), ('ring2mm', 0.8, 2.8)):
        pts = []
        for t in np.arange(-10, 10.01, 0.5):
            for r in np.arange(r0, r1 + 1e-9, 0.4):
                for th in np.arange(0, 2 * math.pi, math.pi / 8 if r > 0 else 7):
                    pts.append(c0 + t * a + r * (math.cos(th) * u + math.sin(th) * v))
        P = np.array(pts); empty = ~contains(cap_world, P)
        # keep only the empty points next to the cap (within 3 mm of its surface): the pilot void and the air at its ends
        d = dist(cap_world, P[empty]); E = P[empty][d < 3.0]
        inside = contains(b, E)
        out[name] = dict(emptyPoints=int(len(E)), insideBlocker=int(inside.sum()), share=round(float(inside.mean()), 3) if len(E) else None)
    return out


def main():
    res = dict(sources={str(p): dict(sha256=sha(p), pinned=h, ok=sha(p) == h) for p, h in PIN.items()})
    assert all(v['ok'] for v in res['sources'].values()), 'source drift'
    pairs = [('head_cap_a7z', PRINT / 'a7z-head/head_cap_a7z-world.stl', 'head_cap_v19', PRINT / 'ext-v19/head_cap_v19-world.stl', V19['head_cap_v19']['sourceToPrint']),
             ('clip_cap_a7z', PRINT / 'a7z-head/clip_cap_a7z-world.stl', 'clip_cap_v19', PRINT / 'ext-v19/clip_cap_v19-world.stl', V19['clip_cap_v19']['sourceToPrint'])]
    for key, newp, oldk, oldp, T in pairs:
        new_w, old_w = load_mesh(newp), load_mesh(oldp)
        add = trimesh.boolean.difference([new_w, old_w], engine='manifold'); rem = trimesh.boolean.difference([old_w, new_w], engine='manifold')
        print(key, 'boolean done', flush=True)
        new_p, Tp = posed(new_w, T); old_p, _ = posed(old_w, T)
        mn, mo = metrics(new_w, np.array(T, float), detect_holes(new_w)), metrics(old_w, np.array(T, float), detect_holes(old_w))
        print(key, 'metrics done', flush=True)
        isl_n, isl_o = islands(new_p, np.linalg.inv(Tp)), islands(old_p, np.linalg.inv(Tp))
        key_o = {(i['printZ'], round(i['robotCentre'][0]), round(i['robotCentre'][1]), round(i['robotCentre'][2])) for i in isl_o}
        added = [i for i in isl_n if (i['printZ'], round(i['robotCentre'][0]), round(i['robotCentre'][1]), round(i['robotCentre'][2])) not in key_o]
        print(key, 'islands done', flush=True)
        rec = dict(sourceToPrint=T, samePoseAs=f'release-V1.9 {oldk}', watertight=bool(new_w.is_watertight), bodies=int(new_w.body_count),
                   volumeMm3=round(float(new_w.volume), 1), oldVolumeMm3=round(float(old_w.volume), 1),
                   materialAddedMm3=round(float(add.volume), 4) if not add.is_empty else 0.0,
                   materialRemovedMm3=round(float(rem.volume), 1) if not rem.is_empty else 0.0,
                   printBoundsMm=np.round(new_p.bounds, 2).tolist(), oldPrintBoundsMm=np.round(old_p.bounds, 2).tolist(),
                   metricsNew=pick(mn), metricsOld=pick(mo), newFaces=new_faces(new_p, old_p, Tp),
                   islandsNew=len(isl_n), islandsOld=len(isl_o), islandsAddedByChange=added, islandListNew=isl_n)
        if key == 'head_cap_a7z':
            rec['eiPi04SupportBlocker'] = dict(blocker=dict(path=str(BLOCKER), sha256=sha(BLOCKER)), screw=SCREW['id'],
                                               new=blocker_cover(new_w), old=blocker_cover(old_w))
        res[key] = rec
    # face: print file vs robot-frame twin under the V1.8 face transform
    fp = load_mesh(PRINT / 'face-a7z/face_panel_a7z-print.stl'); tw = load_mesh(PRINT / 'face-a7z/face_panel_a7z.stl')
    twp, _ = posed(tw, V18['face_panel']['sourceToPrint'])
    A = np.array(sorted(map(tuple, np.round(fp.vertices, 4)))); B = np.array(sorted(map(tuple, np.round(twp.vertices, 4))))
    dev = float(np.abs(A - B).max()) if A.shape == B.shape else None
    I = np.eye(4); mf = metrics(fp, I, detect_holes(fp)); fpp, _ = posed(fp, I)
    res['face_panel_a7z'] = dict(printFileVsTwinUnderV18Transform=dict(maxVertexDeviationMm=dev, v18Transform=V18['face_panel']['sourceToPrint']),
                                 watertight=bool(fp.is_watertight), bodies=int(fp.body_count), volumeMm3=round(float(fp.volume), 1),
                                 printBoundsMm=np.round(fpp.bounds, 2).tolist(), metrics=pick(mf), islands=islands(fpp, np.eye(4)))
    out = REL / 'review/a7z-printability.json'; out.write_text(json.dumps(res, indent=1))
    for k in ('head_cap_a7z', 'clip_cap_a7z'):
        r = res[k]
        print(k, 'added', r['materialAddedMm3'], 'removed', r['materialRemovedMm3'], 'bodies', r['bodies'], 'wt', r['watertight'])
        print('  old', r['metricsOld']); print('  new', r['metricsNew']); print('  newFaces', r['newFaces'])
        print('  islands old/new', r['islandsOld'], r['islandsNew'], 'added', r['islandsAddedByChange'])
    print('blocker', json.dumps(res['head_cap_a7z']['eiPi04SupportBlocker']['new']), json.dumps(res['head_cap_a7z']['eiPi04SupportBlocker']['old']))
    f = res['face_panel_a7z']; print('face', f['printFileVsTwinUnderV18Transform']['maxVertexDeviationMm'], f['metrics'], 'islands', f['islands'])


if __name__ == '__main__':
    main()
