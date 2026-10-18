#!/usr/bin/env python3
"""Print-gate equivalent for the V1.9 scene: final-pose overlap and motion sweeps of every new part.

Scene = every solid in the guide audit cache (guide-data.json parts at q = 0), with head_cap replaced by the release
cap (head_cap_v19-world.stl) and rear_pack replaced by the V1.9 pack (guide/print/rear-pack-v19/rear_pack-world.stl),
plus the new parts: release cap, speaker retainer, four clips (with their screws at the new lengths), speaker,
amplifier, amp housings, Pi-end audio housings, resistor envelope (if present), the four clip screw heads lifted by
the tab, and the Pi mini-HDMI socket envelope (assumed from the Raspberry Pi drawing; not in the guide meshes).
Checks (exact manifold3d booleans and min_gap):
  1. final pose: every new part against every scene part and every other new part: overlap volume and gap;
  2. joint sweeps: each new part against every part on another body, moving only the joints between the two bodies:
     'sweep' = each of those joints alone over its full MJCF range (GRID steps: 5 deg, roll 2.5 deg, jaw 2 deg), the
     others at 0; 'grid2' = when exactly two joints lie between the bodies, their full-range product (GRID_MULTI);
  3. 'policy' box (3 levels per neck joint, jaw 0 and 40) and 'pickup' set (27 beak-pickup postures, jaw 0 and 40),
     neck-route motion.py;
  4. 'walking': every adopted phase-1 walking frame (not fallen, not a blend run), neck joints rounded to 1 deg, jaw
     closed; for new parts on trunk_base also every 20th adopted frame with the leg parts moved by MuJoCo FK
     (robot_allcollisions.xml, power-support-origin pso_lib.FK);
  5. cap descent: cap-group parts lowered 40 mm onto the lower head (0.5 mm steps) against the parts already there;
  6. screw access: every screw within 15 mm of a new part (fasteners.json plus the four new audio screws): its head and
     a straight 3 mm driver 30 mm out along its axis, against the part.
The release cap is mostly the V1.8 cap. In the motion and descent checks it is represented by its difference from the
V1.8 cap (head_cap_v19 minus the V1.8 head_cap, 'head_cap_v19_added'): any overlap the V1.9 cap has and the V1.8 cap
does not lies in that difference, so this tests exactly for new overlap. Final pose reports the whole cap and, per
part, the overlap of the V1.8 cap for comparison.
Motion poses are culled conservatively before the exact booleans: box test, then a surface-sample distance test
(samples cover every surface within SAMPLE_E / sqrt(3); 1.5 mm, 2.0 mm on the cap difference), then a winding-number containment test of one point each way.
A pose is skipped only when neither surface comes within NEAR_M + both cover radii of the other and neither part
contains a point of the other.
Intended contacts: a clip against the part its tab sits on (gap 0, no overlap), a screw in its hole.
Usage: scene_check.py [part ...]   -> ../checks/scene-check.json (merged per part)
"""
from __future__ import annotations

import itertools
import json
import sys
import time

import manifold3d as m3
import numpy as np

import ext_lib as E
from nr_lib import FK, body_of
from motion import POLICY, pose_sets  # noqa: F401  (neck-route pose sets)

D2R = np.radians
CHAIN = ['trunk_base', 'neck', 'neck_pitch', 'yaw_roll_motion', 'jaw_soft', 'jaw']
JOINT_BETWEEN = {('trunk_base', 'neck'): 'neck_pitch', ('neck', 'neck_pitch'): 'head_pitch',
                 ('neck_pitch', 'yaw_roll_motion'): 'head_yaw', ('yaw_roll_motion', 'jaw_soft'): 'head_roll',
                 ('jaw_soft', 'jaw'): 'jaw'}
GRID = {'neck_pitch': np.arange(-90, 61, 5.0), 'head_pitch': np.arange(-90, 91, 5.0), 'head_yaw': np.arange(-170, 171, 5.0),
        'head_roll': np.arange(-25, 25.1, 2.5), 'jaw': np.arange(0, 40.1, 2.0)}
GRID_MULTI = {'neck_pitch': np.arange(-90, 61, 10.0), 'head_pitch': np.arange(-90, 91, 10.0),
              'head_yaw': np.arange(-170, 171, 10.0), 'head_roll': np.arange(-25, 25.1, 5.0), 'jaw': np.array([0.0, 20.0, 40.0])}
CAP_GROUP = {'head_cap', 'pi'}
AT_CAP_ON = {'head_bottom', 'face_panel', 'eye_trim', 'camera_board', 'motor13', 'motor14', 'motor15', 'jaw_support',
             'mouth_sliding_ring', 'jaw_frame', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b',
             'neck_pitch_ring', 'neck_pitch'}
NEAR = 4.0           # final pose: gap search length (mm); gaps beyond it are reported as >= NEAR
NEAR_M = 1.0         # motion: gaps under this are reported
SAMPLE_E = 1.5       # motion cull: surface sample spacing (mm); cover radius SAMPLE_E / sqrt(3)


def is_cap_group(k):
    return k in CAP_GROUP or k.startswith('head_pi_')


def new_parts():
    """name -> (solid, body, capGroup, intendedContacts)"""
    A = E.AUDIO / 'study-solids'
    P = {}
    P['head_cap_v19'] = (E.stl_man(E.PARTS['head_cap_v19']), 'jaw_soft', True, [])
    P['speaker_retainer_v19'] = (E.stl_man(E.PARTS['speaker_retainer_v19']), 'jaw_soft', True, [])
    for nm in ('speaker', 'amplifier', 'amp_housings', 'amp_screws_envelope', 'speaker_screws_envelope',
               'speaker_leads_envelope', 'pi_housing_pin04', 'pi_housing_pin12', 'pi_housing_pin35', 'pi_housing_pin40'):
        P[nm] = (E.stl_man(A / f'{nm}-world.stl'), 'jaw_soft', True, [])
    # ground on Pi pin 34: the pin-14 housing moved 10 pitches along the same row (integrated/scripts/route_scene.py)
    P['pi_housing_pin34'] = (E.stl_man(A / 'pi_housing_pin14-world.stl').translate([0.0, -25.4, 0.0]), 'jaw_soft', True, [])
    for nm, body, capg in (('clip_torso_v19', 'trunk_base', False), ('clip_bracket_v19', 'neck_pitch', False),
                           ('clip_head_v19', 'jaw_soft', False), ('clip_cap_v19', 'jaw_soft', True)):
        p = E.PARTS[nm]
        if p.exists():
            P[nm] = (E.stl_man(p), body, capg, [])
    rp = E.OUT / 'resistor_envelope_v19-world.stl'
    if rp.exists():
        P['resistor_envelope_v19'] = (E.stl_man(rp), 'jaw_soft', True, [])
    # the four clip screws' heads, lifted by the 2.0 mm tab (ISO 7045 pan head: M2 4.0 x 1.6, M2.5 5.0 x 1.75)
    F = E.fasteners()
    for sid, body, capg in (('S12-horn-025', 'trunk_base', False), ('S11-horn-040', 'neck_pitch', False),
                            ('H-jaw_support-03', 'jaw_soft', False), ('E-pi-04', 'jaw_soft', True)):
        r = F[sid]
        c, ax = np.array(r['center'], float), np.array(r['axis'], float)
        ax /= np.linalg.norm(ax)
        d, h = (4.0, 1.6) if r['diameterMm'] == 2.0 else (5.0, 1.75)
        P[f'screw_head_{sid}'] = (E.cyl(c - 2.0 * ax, -ax, h, d / 2, 48), body, capg, [])
    import clips_v19 as C
    P['pi_mini_hdmi_envelope_assumed'] = (C.hdmi_envelope(), 'jaw_soft', True, [])
    return P


def new_parts_names():
    return {'head_cap_v19', 'speaker_retainer_v19', 'speaker', 'amplifier', 'amp_housings', 'amp_screws_envelope',
            'speaker_screws_envelope', 'speaker_leads_envelope', 'pi_housing_pin04', 'pi_housing_pin12', 'pi_housing_pin34',
            'pi_housing_pin35', 'pi_housing_pin40', 'clip_torso_v19', 'clip_bracket_v19', 'clip_head_v19', 'clip_cap_v19',
            'resistor_envelope_v19', 'screw_head_S12-horn-025', 'screw_head_S11-horn-040', 'screw_head_H-jaw_support-03',
            'screw_head_E-pi-04', 'pi_mini_hdmi_envelope_assumed'}


def scene():
    man = E.ia_lib.manifest()
    S = {}
    for k in man:
        if k == 'head_cap':
            continue                     # replaced by head_cap_v19 (a new part)
        if k == 'rear_pack':
            S[k] = (E.stl_man(E.PACK_V19), 'trunk_base')
            continue
        S[k] = (None, body_of(k) or ('jaw' if k == 'jaw_frame' else None))
    return S


def joints_between(a, b):
    i, j = CHAIN.index(a), CHAIN.index(b)
    lo, hi = min(i, j), max(i, j)
    return [JOINT_BETWEEN[(CHAIN[k], CHAIN[k + 1])] for k in range(lo, hi)]


Q0 = dict(neck_pitch=0.0, head_pitch=0.0, head_yaw=0.0, head_roll=0.0, jaw=0.0)


def _q(j, v):
    return D2R(v) if j != 'jaw' else float(v)


def relation_poses(a, b, sets, walk):
    """Pose sets for a new part on body a against a partner on body b (deduplicated on the joints between them)."""
    js = joints_between(a, b)
    raw = {'sweep': [dict(Q0, **{j: _q(j, v)}) for j in js for v in GRID[j]]}
    if len(js) == 2:
        raw['grid2'] = [dict(Q0, **{js[0]: _q(js[0], u), js[1]: _q(js[1], v)})
                        for u, v in itertools.product(GRID_MULTI[js[0]], GRID_MULTI[js[1]])]
    raw['policy'], raw['pickup'], raw['walking'] = sets['policy'], sets['pickup'], walk
    out = {}
    for g, poses in raw.items():
        seen, keep = set(), []
        for q in poses:
            key = tuple(round(float(q.get(j, 0.0)), 6) for j in js)
            if key not in seen:
                seen.add(key)
                keep.append(q)
        out[g] = keep
    return out


def surface_samples(M, e):
    """Points covering the surface: every surface point lies within e / sqrt(3) of one. Each triangle is sampled on a
    barycentric grid with n = ceil(longest edge / e) divisions (sub-triangles have edges <= e), triangles in chunks so
    the peak memory stays small."""
    mesh = M.to_mesh()
    V = np.asarray(mesh.vert_properties, float)[:, :3]
    F = np.asarray(mesh.tri_verts, np.int64)
    T = V[F]
    L = np.linalg.norm(T - np.roll(T, 1, 1), axis=2).max(1)
    nd = np.maximum(1, np.ceil(L / e).astype(int))
    pts = [V.astype(np.float32)]
    for n in np.unique(nd):
        if n == 1:
            continue
        idx = np.flatnonzero(nd == n)
        i, j = np.meshgrid(np.arange(n + 1), np.arange(n + 1), indexing='ij')
        keep = (i + j) <= n
        a, b = (i[keep] / n), (j[keep] / n)
        W = np.stack([1 - a - b, a, b], 1)                       # (k, 3) barycentric weights
        for c0 in range(0, len(idx), 2000):
            t = T[idx[c0:c0 + 2000]]                             # (m, 3, 3)
            pts.append(np.einsum('kc,mcd->mkd', W, t).reshape(-1, 3).astype(np.float32))
    P = np.concatenate(pts)
    return np.unique(np.round(P, 4), axis=0)


def winding(p, V, F):
    """Generalized winding number of point p for the closed triangle mesh (V, F); about 1 inside, 0 outside."""
    a, b, c = V[F[:, 0]] - p, V[F[:, 1]] - p, V[F[:, 2]] - p
    la, lb, lc = (np.linalg.norm(x, axis=1) for x in (a, b, c))
    det = np.einsum('ij,ij->i', a, np.cross(b, c))
    div = la * lb * lc + (a * b).sum(1) * lc + (b * c).sum(1) * la + (c * a).sum(1) * lb
    return float(np.arctan2(det, div).sum() / (2 * np.pi))


class Culler:
    """Conservative pose cull for a pair (new part A in its q = 0 frame, partner B in its q = 0 frame)."""

    def __init__(self):
        self.cache = {}

    def data(self, key, M, e):
        if key not in self.cache:
            from scipy.spatial import cKDTree
            mesh = M.to_mesh()
            V = np.asarray(mesh.vert_properties, float)[:, :3]
            F = np.asarray(mesh.tri_verts, np.int64)
            P = surface_samples(M, e)
            self.cache[key] = (cKDTree(P), P, V, F, e / np.sqrt(3.0))
        return self.cache[key]

    def maybe_near(self, A, Ma, B, Mb, Ti, Tr):
        """Ti: A frame -> B frame, Tr: B frame -> A frame. False only if A and B are provably farther than NEAR_M."""
        ta, Pa, Va, Fa, ca = A
        tb, Pb, Vb, Fb, cb = B
        Pa_b = Pa @ Ti[:3, :3].T + Ti[:3, 3]
        d, _ = tb.query(Pa_b, k=1, distance_upper_bound=NEAR_M + ca + cb)
        if np.isfinite(d).any():
            return True
        if winding(Va[0] @ Ti[:3, :3].T + Ti[:3, 3], Vb, Fb) > 0.5:
            return True
        return winding(Vb[0] @ Tr[:3, :3].T + Tr[:3, 3], Va, Fa) > 0.5


def leg_walking(nm, M, solid, man):
    """Trunk-side new part against the leg parts moved by MuJoCo FK on every 20th adopted walking frame."""
    sys.path.insert(0, str(E.IA / 'power-support-origin'))
    import pso_lib
    pf = pso_lib.FK()
    _, _, Qad = walking_poses()
    rows = Qad[::20]
    hinge = [j for j in pf.jnames if pf.M.joint(j).type != 0]
    legs = [(body, k) for side in pso_lib.SIDE.values() for body, keys in side['parts'].items() for k in keys if k in man]
    bb = E.bbox(M)
    worst = {}
    for row in rows:
        T = pf.part_T({j: float(row[pf.qadr[j]]) for j in hinge})
        for body, k in legs:
            O = solid(k).transform(T[body][:3, :])
            ob = E.bbox(O)
            if np.any(ob[0] > bb[1] + NEAR_M) or np.any(ob[1] < bb[0] - NEAR_M):
                g = float(np.linalg.norm(np.maximum(0, np.maximum(np.array(ob[0]) - bb[1], np.array(bb[0]) - ob[1]))))
                cur = worst.get(k)
                if cur is None or g < cur['boxGapMm']:
                    worst[k] = {'part': k, 'body': body, 'overlapMm3': 0.0, 'boxGapMm': round(g, 2), 'exact': False}
                continue
            ov = (M ^ O).volume()
            g = float(M.min_gap(O, NEAR_M)) if ov < 1e-9 else 0.0
            cur = worst.get(k)
            if cur is None or ov > cur['overlapMm3'] or g < cur.get('gapMm', 99):
                worst[k] = {'part': k, 'body': body, 'overlapMm3': round(ov, 4), 'gapMm': round(g, 3), 'exact': True}
    near = sorted(worst.values(), key=lambda r: (-r['overlapMm3'], r.get('gapMm', r.get('boxGapMm'))))
    return {'framesChecked': int(len(rows)), 'legParts': len(legs), 'closest': near[:5],
            'overlaps': [r for r in near if r['overlapMm3'] > 1e-6]}


CLIP_SCREWS = {'S12-horn-025': 'clip_torso_v19', 'S11-horn-040': 'clip_bracket_v19', 'H-jaw_support-03': 'clip_head_v19',
               'E-pi-04': 'clip_cap_v19'}
DRIVER_R, DRIVER_L = 1.5, 30.0     # straight 3 mm driver, as fasteners.json 'driverClearAtStepMm'


def screw_access(nm, M, F, v18_parts=None):
    """Every screw whose seat is within 15 mm of the new part: its head (ISO 7045 pan head, M2 4.0 x 1.6, M2.5 5.0 x 1.75;
    the four clip screws at their seat lifted by the 2.0 mm tab) and a straight 3 mm driver 30 mm out along the axis,
    against the new part. A clip's own screw head is checked too (it must sit on the tab, not in the channel)."""
    bb = np.array(E.bbox(M))
    out = []
    for sid, r in F.items():
        c, ax = np.array(r['center'], float), np.array(r['axis'], float)
        ax /= np.linalg.norm(ax)
        if np.linalg.norm(np.maximum(0, np.maximum(bb[0] - c, c - bb[1]))) > 15.0:
            continue
        if sid in CLIP_SCREWS:
            c = c - 2.0 * ax
        d, h = (4.0, 1.6) if float(r.get('diameterMm', 2.0)) < 2.4 else (5.0, 1.75)
        head = E.cyl(c - 0.02 * ax, -ax, h, d / 2, 48)
        drv = E.cyl(c - h * ax, -ax, DRIVER_L, DRIVER_R, 32)
        rec = {'screw': sid, 'step': r.get('step'), 'ownClipScrew': CLIP_SCREWS.get(sid) == nm}
        for tag, S in (('head', head), ('driver', drv)):
            ov = (M ^ S).volume()
            rec[f'{tag}OverlapMm3'] = round(ov, 4)
            rec[f'{tag}GapMm'] = round(float(M.min_gap(S, NEAR)), 3) if ov < 1e-9 else 0.0
        if rec['driverOverlapMm3'] > 1e-3 and v18_parts is not None:
            # is that straight driver path already blocked on the assembled V1.8 robot (q = 0)?
            own = set(r.get('throughParts') or [r.get('throughPart')]) | {r.get('intoPart')}
            blk = {}
            db = np.array(E.bbox(drv))
            for k, (kb0, get) in v18_parts.items():
                if k in own:
                    continue
                b0 = kb0
                if np.any(b0[0] > db[1]) or np.any(b0[1] < db[0]):
                    continue
                ov = (get(k) ^ drv).volume()
                if ov > 1e-2:
                    blk[k] = round(ov, 3)
            rec['driverBlockedOnAssembledV18By'] = blk
        out.append(rec)
    return sorted(out, key=lambda r: (-(r['headOverlapMm3'] + r['driverOverlapMm3']), min(r['headGapMm'], r['driverGapMm'])))


def walking_poses():
    sys.path.insert(0, str(E.IA / 'power-support-origin'))
    import pso_lib
    Q = np.load(E.SCRATCH / 'walk_qpos.npy')
    trace = np.load(E.SCRATCH / 'walk_trace.npy')
    src = pso_lib.walking_sources()
    adopted = np.array([not s['fell'] and not s['blend'] for s in src])[trace]
    neck = np.degrees(Q[adopted][:, 12:16])
    uniq = np.unique(np.round(neck), axis=0)
    poses = [dict(neck_pitch=D2R(a), head_pitch=D2R(b), head_yaw=D2R(c), head_roll=D2R(d), jaw=0.0) for a, b, c, d in uniq]
    info = {'framesTotal': int(len(Q)), 'framesAdopted': int(adopted.sum()), 'sources': len(src),
            'sourcesAdopted': int(sum(not s['fell'] and not s['blend'] for s in src)), 'uniqueNeckPoses1deg': int(len(uniq)),
            'neckRangeDeg': [neck.min(0).round(1).tolist(), neck.max(0).round(1).tolist()]}
    return poses, info, Q[adopted]


def pair(A, B):
    ov = (A ^ B).volume()
    g = float(A.min_gap(B, NEAR)) if ov < 1e-9 else 0.0
    return ov, g


def main():
    t0 = time.time()
    only = set(sys.argv[1:])
    fk = FK()
    NP = new_parts()
    SC = scene()
    man = E.ia_lib.manifest()
    cache = {}

    def solid(k):
        if k in NP:
            return NP[k][0]
        if k in SC and SC[k][0] is not None:
            return SC[k][0]
        if k not in cache:
            cache[k] = E.load_man(k)
        return cache[k]

    BOUNDS = {}

    def bounds(k):
        """Axis box at q = 0 without loading the solid (manifest bounds for cached guide solids)."""
        if k not in BOUNDS:
            if k in NP or (k in SC and SC[k][0] is not None) or k not in man or 'bounds' not in man[k]:
                BOUNDS[k] = np.array(E.bbox(solid(k)), float)
            else:
                BOUNDS[k] = np.array(man[k]['bounds'], float)
        return BOUNDS[k]

    from engage_check import audio_screws
    FS = dict(E.fasteners())
    FS.update(audio_screws())
    cap18 = E.load_man('head_cap')
    cap_added = NP['head_cap_v19'][0] - cap18
    sets = pose_sets(fk)
    walk, winfo, _ = walking_poses()
    out_path = E.OUT / 'checks' / 'scene-check.json'
    res = json.loads(out_path.read_text()) if out_path.exists() else {}
    res['_method'] = __doc__.strip()
    res['_walking'] = winfo
    res['_capAddedVsV18Mm3'] = round(cap_added.volume(), 3)
    allkeys = list(SC) + list(NP)
    FKC, TC = {}, {}
    CU = Culler()

    def fkq(q):
        key = tuple(round(float(q[j]), 6) for j in ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll', 'jaw'))
        if key not in FKC:
            FKC[key] = fk.part_T(q)
        return FKC[key]

    def Tcache(a, b):
        """{set: (poses, Tr (N,4,4) partner-b frame -> new-part-a frame, Ti = inv(Tr))} for the relation a-b."""
        if (a, b) not in TC:
            d = {}
            for g, poses in relation_poses(a, b, sets, walk).items():
                Tr = np.array([np.linalg.inv(fkq(q)[a]) @ fkq(q)[b] for q in poses]).reshape(-1, 4, 4)
                d[g] = (poses, Tr, np.linalg.inv(Tr) if len(Tr) else Tr)
            TC[(a, b)] = d
        return TC[(a, b)]

    for nm, (M, body, capg, _) in NP.items():
        if only and nm not in only:
            continue
        t1 = time.time()
        rec = {'body': body, 'capGroup': capg, 'volumeMm3': M.volume(), 'bounds': E.bbox(M)}
        bb = E.bbox(M)
        static, moving = [], []
        for k in allkeys:
            if k == nm:
                continue
            kb = NP[k][1] if k in NP else SC[k][1]
            if kb is None:
                kb = 'trunk_base'     # legs and unassigned parts: q = 0 here; legs again in the walking frames below
            ob = bounds(k) + [[-0.01], [0.01]]
            if kb == body:
                if np.any(ob[0] > np.array(bb[1]) + NEAR) or np.any(ob[1] < np.array(bb[0]) - NEAR):
                    continue
                O = solid(k)
                ov, g = pair(M, O)
                if ov > 1e-6 or g < NEAR:
                    r = {'part': k, 'overlapMm3': round(ov, 4), 'gapMm': round(g, 3)}
                    if nm == 'head_cap_v19' and k != 'head_cap':
                        r['overlapV18CapMm3'] = round((cap18 ^ O).volume(), 4)
                        r['newOverlapMm3'] = round((cap_added ^ O).volume(), 4)
                    static.append(r)
            else:
                moving.append((k, kb, ob))
        rec['finalPose'] = sorted(static, key=lambda r: (-r['overlapMm3'], r['gapMm']))
        if not nm.startswith('screw_head_'):
            # the cap: only its difference from the V1.8 cap can newly block a screw or driver
            v18p = {k: (bounds(k), solid) for k in SC if k != 'rear_pack'} | {'head_cap': (np.array(E.bbox(cap18)), lambda k: cap18)}
            rec['screwAccess'] = screw_access(nm, cap_added if nm == 'head_cap_v19' else M, FS, v18p)
        # motion: the cap is represented by its difference from the V1.8 cap (new overlap only)
        Mm = cap_added if nm == 'head_cap_v19' else M
        bbm = E.bbox(Mm)
        corners = np.array(list(itertools.product(*zip(bbm[0], bbm[1]))))
        A = None
        worst, counts = {}, {}
        for k, kb, ob0 in moving:
            O = None
            for gname, (poses, Trs, Tis) in Tcache(body, kb).items():
                if not len(poses):
                    continue
                cc = np.einsum('nij,kj->nki', Tis[:, :3, :3], corners) + Tis[:, None, :3, 3]
                hit = ~(np.any(cc.min(1) > np.array(ob0[1]) + NEAR_M, axis=1) | np.any(cc.max(1) < np.array(ob0[0]) - NEAR_M, axis=1))
                c = counts.setdefault(gname, {'poses': len(poses), 'pairPoses': 0, 'boxPass': 0, 'exact': 0})
                c['pairPoses'] += len(poses)
                c['boxPass'] += int(hit.sum())
                if not hit.any():
                    continue
                if A is None:
                    A = CU.data(('A', nm), Mm, 2.0 if nm == 'head_cap_v19' else SAMPLE_E)
                if O is None:
                    O = solid(k)
                B = CU.data(('B', k), O, SAMPLE_E)
                for qi in np.flatnonzero(hit):
                    if not CU.maybe_near(A, Mm, B, O, Tis[qi], Trs[qi]):
                        continue
                    c['exact'] += 1
                    Om = O.transform(Trs[qi][:3, :])
                    ov = (Mm ^ Om).volume()
                    g = float(Mm.min_gap(Om, NEAR_M)) if ov < 1e-9 else 0.0
                    key = (k, gname)
                    cur = worst.get(key)
                    if cur is None or ov > cur['overlapMm3'] or (ov == cur['overlapMm3'] and g < cur['gapMm']):
                        q = poses[qi]
                        worst[key] = {'part': k, 'body': kb, 'poseSet': gname, 'overlapMm3': round(ov, 4),
                                      'gapMm': round(g, 3),
                                      'poseDeg': {a: round(float(np.degrees(v)) if a != 'jaw' else float(v), 1) for a, v in q.items()}}
        rec['motion'] = sorted(worst.values(), key=lambda r: (-r['overlapMm3'], r['gapMm']))
        rec['motionOverlaps'] = [r for r in rec['motion'] if r['overlapMm3'] > 1e-6]
        rec['motionCounts'] = counts
        if body == 'trunk_base':
            rec['walkingLegs'] = leg_walking(nm, M, solid, man)
        # cap descent
        if capg or nm == 'clip_head_v19':
            Md = cap_added if nm == 'head_cap_v19' else M
            desc = []
            partners = [k for k in allkeys if k != nm and (
                (capg and (k in AT_CAP_ON or (k in NP and not NP[k][2] and NP[k][1] in ('jaw_soft', 'jaw')))) or
                (not capg and (is_cap_group(k) or (k in NP and NP[k][2]))))]
            for k in partners:
                O = solid(k)
                ob = E.bbox(O)
                f0 = (Md ^ O).volume()
                wex, gmin = 0.0, 99.0
                for dz in np.arange(0.0, 40.0 + 1e-9, 0.5):
                    P = Md.translate([0, 0, float(dz) if capg else -float(dz)])
                    pb = E.bbox(P)
                    if np.any(np.array(ob[0]) > np.array(pb[1]) + NEAR) or np.any(np.array(ob[1]) < np.array(pb[0]) - NEAR):
                        continue
                    ex = (P ^ O).volume() - f0
                    wex = max(wex, ex)
                    if ex <= 1e-9:
                        gmin = min(gmin, float(P.min_gap(O, NEAR)))
                if wex > 1e-6 or gmin < NEAR:
                    desc.append({'part': k, 'excessOverlapMm3': round(wex, 4), 'minGapAlongPathMm': round(gmin, 3),
                                 'overlapSeatedMm3': round(f0, 4)})
            rec['capDescent'] = sorted(desc, key=lambda r: (-r['excessOverlapMm3'], r['minGapAlongPathMm']))
        rec['elapsedS'] = round(time.time() - t1, 1)
        res[nm] = E.rnd(rec, 4)
        E.jdump(res, out_path)
        print(nm, 'static', [(r['part'], r['overlapMm3'], r['gapMm']) for r in rec['finalPose'][:4]],
              '| motion overlaps', [(r['part'], r['poseSet'], r['overlapMm3']) for r in rec['motionOverlaps'][:4]],
              '| closest', [(r['part'], r['poseSet'], r['gapMm']) for r in rec['motion'][:2]],
              '| legs', rec.get('walkingLegs', {}).get('overlaps'),
              '| screws', [(r['screw'], r['headOverlapMm3'], r['headGapMm'], r['driverOverlapMm3'], r['driverGapMm'])
                           for r in rec.get('screwAccess', [])[:3]],
              '| descent', [(r['part'], r['excessOverlapMm3'], r['minGapAlongPathMm']) for r in rec.get('capDescent', [])[:3]],
              f'{time.time() - t1:.0f}s', flush=True)


if __name__ == '__main__':
    main()
