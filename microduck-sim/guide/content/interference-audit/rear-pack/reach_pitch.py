"""Bend-forward reach sweep: hip pitch over its full range (2 deg steps) x knee (0/25/50/75/100 % of flexion) x ankle (0, level
with the torso floor, both range ends) x hip yaw/roll (0, +-10 deg), both legs, against (a) the Layout-L pack solid with the
plate trimmed to the original silhouette and (b) the original battery + original power_support. Usage: reach_pitch.py <left|right>"""
import sys, json, time
from pathlib import Path
import numpy as np, trimesh
import manifold3d as m3d
OUT = Path('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/e281f88a-117d-47f8-a4cc-4faadc6be94a/scratchpad/torso-fit')
PSO = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit/power-support-origin')
sys.path.insert(0, str(PSO)); import pso_lib as L
sys.path.insert(0, str(OUT)); from pack_hull import pack_mesh, box_manifold, plate_from_power_support, man_to_mesh
import mujoco
side = sys.argv[1]; SOLID_SEL = sys.argv[2] if len(sys.argv) > 2 else 'both'; t0 = time.time()
CONTACT = 1.0; STEP = np.radians(2.0)

# ---- solids ----
spec = json.load(open(OUT / 'spec_final.json'))
pack_tm, bx = pack_mesh(spec, 'finalps25'); PACK = L.mesh_to_m(pack_tm)
COMPS = {k: box_manifold(b0, b1) for k, (b0, b1) in bx.items()}; COMPS['PLATE_trimmed'] = plate_from_power_support(xs=-25.0)
COMP_BOX = {k: [np.round(b0, 2).tolist(), np.round(b1, 2).tolist()] for k, (b0, b1) in bx.items()}
pm = COMPS['PLATE_trimmed'].to_mesh(); pv = np.asarray(pm.vert_properties)[:, :3]; COMP_BOX['PLATE_trimmed'] = [np.round(pv.min(0), 2).tolist(), np.round(pv.max(0), 2).tolist()]
bat = trimesh.load(OUT / 'battery_guide_frame.stl', force='mesh'); ops = trimesh.load(OUT / 'orig_power_support_guide_frame.stl', force='mesh')
BASE = L.to_m(bat.vertices, bat.faces) + L.to_m(ops.vertices, ops.faces); base_tm = man_to_mesh(BASE)
SOLIDS = {'pack': (PACK, pack_tm), 'baseline': (BASE, base_tm)}
if SOLID_SEL != 'both': SOLIDS = {SOLID_SEL: SOLIDS[SOLID_SEL]}
print(f'[{side}] solids: pack vol {pack_tm.volume:.0f} bounds {np.round(pack_tm.bounds,1).tolist()}; baseline vol {base_tm.volume:.0f} bounds {np.round(base_tm.bounds,1).tolist()}', flush=True)

# ---- model, ranges, sign conventions ----
fk = L.FK(); M, D = fk.M, fk.D; cfg = L.SIDE[side]; J = cfg['joints']; bodies = list(cfg['parts'])
jid = {j: mujoco.mj_name2id(M, mujoco.mjtObj.mjOBJ_JOINT, j) for j in J}
RANGE = {j: M.jnt_range[jid[j]].copy() for j in J}
tb = M.body('trunk_base').id; bid = {b: M.body(b).id for b in bodies}; iT0 = {b: np.linalg.inv(fk.T0[b]) for b in bodies}
def kin(q):
    D.qpos[:] = M.qpos0
    for j, v in zip(J, q):
        D.qpos[fk.qadr[j]] = v
    mujoco.mj_kinematics(M, D)
    R0 = D.xmat[tb].reshape(3, 3); p0 = D.xpos[tb]
    return R0, p0
def body_T(q):
    R0, p0 = kin(q); out = {}
    for b in bodies:
        k = bid[b]; T = np.eye(4); T[:3, :3] = R0.T @ D.xmat[k].reshape(3, 3); T[:3, 3] = R0.T @ (D.xpos[k] - p0) * 1000.0
        out[b] = T @ iT0[b]
    return out
# joint axes in the torso frame at q = 0 (all hinges are 'axis 0 0 1' in their own body frames)
R0, p0 = kin([0] * 5)
AX = {}
for j in J:
    k = M.jnt_bodyid[jid[j]]; AX[j] = (R0.T @ D.xmat[k].reshape(3, 3) @ M.jnt_axis[jid[j]]).round(4)
hp, kn, an = J[2], J[3], J[4]
s = {j: float(np.sign(AX[j][1])) for j in (hp, kn, an)}          # pitch joints: axis = +-y
foot_b = bodies[4]
def foot_pos(q):
    kin(q); return (R0.T @ (D.xpos[bid[foot_b]] - p0) * 1000.0)
fx0 = foot_pos([0, 0, 0, 0, 0])[0]; fxp = foot_pos([0, 0, 0.2, 0, 0])[0]
NOSE_DOWN = +1.0 if fxp < fx0 else -1.0          # hip-pitch sign that moves the foot backward (-x) in the torso frame = torso pitching nose-down
Q = np.load(L.SCRATCH / 'walk_qpos.npy'); trace = np.load(L.SCRATCH / 'walk_trace.npy'); src = L.walking_sources()
adopted = np.array([not s_['fell'] and not s_['blend'] for s_ in src])[trace]
kn_walk = Q[adopted, fk.qadr[kn]]; FLEX = float(np.sign(np.median(kn_walk)))     # knee flexion direction = sign used when walking
hipfoot0 = np.linalg.norm(foot_pos([0, 0, 0, 0, 0])); hipfoot_flex = np.linalg.norm(foot_pos([0, 0, 0, FLEX * 1.0, 0]))
conv = {'joint_ranges_rad': {j: RANGE[j].round(5).tolist() for j in J}, 'joint_ranges_deg': {j: np.degrees(RANGE[j]).round(2).tolist() for j in J},
        'joint_axes_in_torso_frame_at_q0': {j: AX[j].tolist() for j in J}, 'pitch_axis_signs(y)': s,
        'nose_down_hip_pitch_sign': NOSE_DOWN, 'foot_x_at_q0_mm': round(float(fx0), 2), 'foot_x_at_hip_pitch_+0.2rad_mm': round(float(fxp), 2),
        'knee_flexion_sign': FLEX, 'knee_median_walking_rad': round(float(np.median(kn_walk)), 4), 'hip_to_foot_mm_q0': round(float(hipfoot0), 1), 'hip_to_foot_mm_knee_flex_1rad': round(float(hipfoot_flex), 1),
        'ankle_level_rule': 'ankle = -(s_hp*hip_pitch + s_kn*knee)/s_an, clipped to the ankle range (foot sole parallel to the torso-frame floor)'}
print(f'[{side}] conventions {json.dumps(conv)}', flush=True)

# ---- leg bodies as single manifolds ----
BODY_MAN = {}; BODY_TM = {}; PART_MAN = {}
for b in bodies:
    ms = []
    for k in cfg['parts'][b]:
        v, f = L.solid(k); PART_MAN[k] = L.to_m(v, f); ms.append(PART_MAN[k])
    BODY_MAN[b] = m3d.Manifold.batch_boolean(ms, m3d.OpType.Add); BODY_TM[b] = man_to_mesh(BODY_MAN[b])
LABEL = {bodies[0]: 'hip yaw body', bodies[1]: 'hip roll body', bodies[2]: 'thigh/knee', bodies[3]: 'shin', bodies[4]: 'ankle/foot'}
# ---- leg surface sample points (per body) and distance fields of the solids (0.4 mm voxels) ----
from scipy import ndimage
from scipy.spatial import cKDTree
VS = 0.4; FMARGIN = 16.0
def leg_points(b):
    per = {}; cov = 0.0
    for k in cfg['parts'][b]:
        v, f = L.solid(k); m = trimesh.Trimesh(v, f, process=False)
        n = max(400, int(m.area / 0.16)); p, _ = trimesh.sample.sample_surface(m, n, seed=1); P = np.vstack([p, v])
        dense, _ = trimesh.sample.sample_surface(m, min(300000, n * 8), seed=7); cov = max(cov, float(cKDTree(P).query(dense)[0].max()))
        per[k] = np.unique(np.round(P / 0.2).astype(np.int64), axis=0) * 0.2      # thin to 0.2 mm
    return per, cov
LEG_P = {}; LEG_COV = {}; PART_P = {}
for b in bodies:
    per, LEG_COV[b] = leg_points(b); PART_P.update(per); LEG_P[b] = np.vstack([per[k] for k in cfg['parts'][b]])
def make_field(mesh):
    lo = mesh.bounds[0] - FMARGIN; hi = mesh.bounds[1] + FMARGIN
    sh = np.ceil((hi - lo) / VS).astype(int) + 1; g = np.ones(sh, bool)
    n = int(mesh.area / 0.01)
    for c in range(0, n, 500000):
        p, _ = trimesh.sample.sample_surface(mesh, min(500000, n - c), seed=3 + c); idx = np.round((p - lo) / VS).astype(int); g[idx[:, 0], idx[:, 1], idx[:, 2]] = False
    idx = np.round((mesh.vertices - lo) / VS).astype(int); g[idx[:, 0], idx[:, 1], idx[:, 2]] = False
    return lo, sh, ndimage.distance_transform_edt(g, sampling=VS).astype(np.float32)
def lookup(fld, X):
    lo, sh, F = fld; idx = np.round((X - lo) / VS).astype(int); ok = np.all((idx >= 0) & (idx < sh), 1)
    d = np.full(len(X), 99.0, np.float32); d[ok] = F[idx[ok, 0], idx[ok, 1], idx[ok, 2]]; return d
FIELDS = {k: make_field(v[1]) for k, v in SOLIDS.items()}
FIELD_ERR = {b: round(VS * np.sqrt(3) / 2 + LEG_COV[b], 2) for b in bodies}
def coarse_gaps(T, fld, blist):
    return {b: float(lookup(fld, LEG_P[b] @ T[b][:3, :3].T + T[b][:3, 3]).min()) for b in blist}
print(f'[{side}] fields built {time.time()-t0:.0f}s; leg points', {b: len(LEG_P[b]) for b in bodies}, 'cover', {b: round(LEG_COV[b], 2) for b in bodies}, 'field err', FIELD_ERR, flush=True)
def gaps(q, solid, blist, cutoff=25.0):
    T = body_T(q); return {b: float(BODY_MAN[b].transform(np.asarray(T[b][:3, :4])).min_gap(solid, cutoff)) for b in blist}, T
def contact_detail(q, T, b, solid_tm):
    m = BODY_TM[b].copy(); m.apply_transform(T[b])
    c, d, _ = trimesh.proximity.closest_point(solid_tm, m.vertices); i = int(np.argmin(d))
    # which part of the body
    part = min(cfg['parts'][b], key=lambda k: float(PART_MAN[k].transform(np.asarray(T[b][:3, :4])).min_gap(SOLIDS_M_CUR, 30.0)))
    return {'part': part, 'leg_point': np.round(m.vertices[i], 2).tolist(), 'solid_point': np.round(c[i], 2).tolist(), 'distance': round(float(d[i]), 3)}

# ---- grid ----
hp_lo, hp_hi = RANGE[hp]; hp_vals = np.arange(np.ceil(hp_lo / STEP) * STEP, hp_hi + 1e-9, STEP); hp_vals = np.unique(np.r_[hp_vals, 0.0]); hp_vals.sort()
nd_end = hp_hi if NOSE_DOWN > 0 else hp_lo
kn_end = RANGE[kn][1] if FLEX > 0 else RANGE[kn][0]
KNEE = {f'{p}%': float(p / 100.0 * kn_end) for p in (0, 25, 50, 75, 100)}
YR = {'0': 0.0, '+10': np.radians(10), '-10': np.radians(-10)}
def ankle_for(mode, hpv, knv):
    if mode == 'zero': return 0.0
    if mode == 'level': return float(np.clip(-(s[hp] * hpv + s[kn] * knv) / s[an], *RANGE[an]))
    if mode == 'range_lo': return float(RANGE[an][0])
    return float(RANGE[an][1])
ANK = ['zero', 'level', 'range_lo', 'range_hi']
def exact_gap(T, b, solid, cutoff=25.0):
    return float(BODY_MAN[b].transform(np.asarray(T[b][:3, :4])).min_gap(solid, cutoff))
def contact_detail(T, b, solid_tm, fld):
    P = LEG_P[b] @ T[b][:3, :3].T + T[b][:3, 3]; d = lookup(fld, P); i = int(np.argmin(d))
    c, dd, _ = trimesh.proximity.closest_point(solid_tm, P[i:i + 1])
    return {'leg_point': np.round(P[i], 2).tolist(), 'solid_point': np.round(c[0], 2).tolist(), 'point_distance_mm': round(float(dd[0]), 3)}
def part_of(T, b, fld):
    return min(cfg['parts'][b], key=lambda k: float(lookup(fld, PART_P[k] @ T[b][:3, :3].T + T[b][:3, 3]).min()))
results = {}
for sname, (SOL, SOL_TM) in SOLIDS.items():
    fld = FIELDS[sname]; rows = []; hip_rows = {}
    for yk, yv in YR.items():
        for rk, rv in YR.items():
            q = [yv, rv, 0, 0, 0]; T = body_T(q)
            g = coarse_gaps(T, fld, bodies[:2]); hb = min(g, key=g.get)
            rec = {'coarse_min_gap_mm': round(g[hb], 2), 'body': LABEL[hb]}
            if g[hb] < 6: rec['exact_min_gap_mm'] = round(exact_gap(T, hb, SOL), 3); rec.update(contact_detail(T, hb, SOL_TM, fld)); rec['part'] = part_of(T, hb, fld)
            hip_rows[f'yaw{yk}_roll{rk}'] = rec
            for kk, kv in KNEE.items():
                for am in ANK:
                    curve = []
                    for hv in hp_vals:
                        av = ankle_for(am, hv, kv); T = body_T([yv, rv, hv, kv, av])
                        g = coarse_gaps(T, fld, bodies[2:]); b = min(g, key=g.get)
                        curve.append((float(hv), g[b], b, av))
                    arr = np.array([c[1] for c in curve]); hv_arr = np.array([c[0] for c in curve])
                    def first(direction, confirm):
                        idx = np.where(hv_arr * direction >= -1e-9)[0]; order = idx[np.argsort(np.abs(hv_arr[idx]))]
                        attempts = 0
                        for n_, i in enumerate(order):
                            if arr[i] >= CONTACT:
                                continue
                            cands = [i]
                            if confirm and n_ > 0:
                                cands = [order[n_ - 1], i]          # also the step before (field error ~1 mm)
                            chosen = None; ge = None
                            for c_ in cands:
                                hv_, g_, b_, av_ = curve[c_]; T = body_T([yv, rv, hv_, kv, av_])
                                if confirm:
                                    attempts += 1; ge = exact_gap(T, b_, SOL)
                                    if ge < CONTACT:
                                        chosen = c_; break
                                else:
                                    chosen = c_; break
                            if chosen is None:
                                if attempts >= 6:                  # give up confirming: report the field estimate
                                    chosen = i; hv_, g_, b_, av_ = curve[i]; T = body_T([yv, rv, hv_, kv, av_]); ge = exact_gap(T, b_, SOL); unconfirmed = True
                                else:
                                    continue
                            else:
                                unconfirmed = False
                            hv_, g_, b_, av_ = curve[chosen]; T = body_T([yv, rv, hv_, kv, av_])
                            rec = {'hip_pitch_deg': round(float(np.degrees(hv_)), 1), 'coarse_gap_mm': round(float(g_), 2), 'exact_gap_mm': (round(ge, 3) if ge is not None else None), 'body': LABEL[b_], 'ankle_deg': round(float(np.degrees(av_)), 1),
                                   'part': part_of(T, b_, fld), **contact_detail(T, b_, SOL_TM, fld), 'last_clear_hip_pitch_deg': round(float(np.degrees(hv_ - direction * STEP)), 1) if abs(hv_) > 1e-9 else None}
                            if confirm and unconfirmed: rec['note'] = 'field estimate < 1 mm but exact gap >= 1 mm here; reported angle is the field estimate (exact gap given)'
                            if sname == 'pack':
                                cg = {k: float(BODY_MAN[b_].transform(np.asarray(T[b_][:3, :4])).min_gap(c, 30.0)) for k, c in COMPS.items()}
                                rec['responsible_component'] = min(cg, key=cg.get); rec['component_gaps_mm'] = {k: round(v, 2) for k, v in sorted(cg.items(), key=lambda t: t[1])[:3]}
                            return rec
                        return 'none'
                    nd = first(NOSE_DOWN, confirm=(sname == 'pack')); nu = first(-NOSE_DOWN, confirm=False)
                    sel_nd = hv_arr * NOSE_DOWN >= -1e-9
                    rows.append({'knee': kk, 'knee_deg': round(float(np.degrees(kv)), 1), 'ankle_mode': am, 'yaw': yk, 'roll': rk,
                                 'nose_down_first_contact': nd, 'nose_down_min_coarse_gap_mm': round(float(arr[sel_nd].min()), 2), 'nose_down_range_end_deg': round(float(np.degrees(nd_end)), 1),
                                 'nose_up_first_contact': nu, 'nose_up_min_coarse_gap_mm': round(float(arr[~sel_nd | (hv_arr == 0)].min()), 2),
                                 'gap_curve_deg_mm': [[round(float(np.degrees(c[0])), 1), round(float(c[1]), 2)] for c in curve]})
            print(f'[{side}/{sname}] yaw {yk} roll {rk} done {time.time()-t0:.0f}s', flush=True)
    results[sname] = {'hip_bodies_by_yaw_roll': hip_rows, 'rows': rows}
json.dump({'side': side, 'conventions': conv, 'hip_pitch_grid_deg': np.degrees(hp_vals).round(1).tolist(), 'knee_values_deg': {k: round(float(np.degrees(v)), 1) for k, v in KNEE.items()},
           'ankle_modes': ANK, 'yaw_roll_deg': list(YR), 'contact_threshold_mm': CONTACT, 'gap_estimate': {'voxel_mm': VS, 'error_bound_mm_by_body': FIELD_ERR, 'pack_first_contacts_confirmed_exact': True, 'baseline_first_contacts': 'field estimate (exact at the summary rows in reach-pitch.json)'},
           'component_boxes': COMP_BOX, 'solids': {k: {'volume_mm3': round(float(v[1].volume)), 'bounds': np.round(v[1].bounds, 2).tolist()} for k, v in SOLIDS.items()},
           'results': results, 'elapsed_s': round(time.time() - t0, 1)}, open(OUT / (f'reach-pitch-{side}.json' if SOLID_SEL == 'both' else f'reach-pitch-{side}-{SOLID_SEL}.json'), 'w'))
print(f'[{side}] DONE {time.time()-t0:.0f}s', flush=True)
