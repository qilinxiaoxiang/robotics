"""Per side: (1) exact confirmation of the baseline's first contacts at the summary rows (knee 0/50/100 %, worst and nominal);
(2) for every (knee, ankle, yaw, roll) where the pack contacts at a smaller nose-down hip pitch than the baseline: the responsible
pack component and the smallest translation up (+z) or back (-x) of that component that keeps >= 1 mm to the leg at every hip
pitch the baseline still allows (analytic point-to-box distance on the leg surface points; field lookup for the trimmed plate).
Usage: reach_shift.py <left|right>  (reads reach-pitch-<side>.json, writes reach-shift-<side>.json)"""
import sys, json
import numpy as np
src = open('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/e281f88a-117d-47f8-a4cc-4faadc6be94a/scratchpad/torso-fit/reach_pitch.py').read()
src = src[:src.index('# ---- grid ----')]
exec(compile(src, 'reach_pitch_header', 'exec'))
import os
if not os.path.exists(OUT / f'reach-pitch-{side}.json') or os.path.getmtime(OUT / f'reach-pitch-{side}-pack.json') > os.path.getmtime(OUT / f'reach-pitch-{side}.json'):
    Rp = json.load(open(OUT / f'reach-pitch-{side}-pack.json')); Rb = json.load(open(OUT / f'reach-pitch-{side}-baseline.json'))
    Rp['results']['baseline'] = Rb['results']['baseline']; Rp['solids'].update(Rb['solids']); Rp['elapsed_s'] = {'pack': Rp['elapsed_s'], 'baseline': Rb['elapsed_s']}
    json.dump(Rp, open(OUT / f'reach-pitch-{side}.json', 'w'))
R = json.load(open(OUT / f'reach-pitch-{side}.json'))
rows_p = R['results']['pack']['rows']; rows_b = R['results']['baseline']['rows']
KNEE = {k: np.radians(v) for k, v in R['knee_values_deg'].items()}
YRv = {'0': 0.0, '+10': np.radians(10), '-10': np.radians(-10)}
BODY_OF = {v: k for k, v in LABEL.items()}
def ankle_for(mode, hpv, knv):
    if mode == 'zero': return 0.0
    if mode == 'level': return float(np.clip(-(s[hp] * hpv + s[kn] * knv) / s[an], *RANGE[an]))
    if mode == 'range_lo': return float(RANGE[an][0])
    return float(RANGE[an][1])
def pose_T(rec, hp_deg):
    kv = KNEE[rec['knee']]; hv = np.radians(hp_deg); av = ankle_for(rec['ankle_mode'], hv, kv)
    return body_T([YRv[rec['yaw']], YRv[rec['roll']], hv, kv, av])
def nd_angle(rec):
    fc = rec['nose_down_first_contact']; return None if fc == 'none' else fc['hip_pitch_deg']
def point_box_dist(P, b0, b1):
    d = np.maximum(np.maximum(b0 - P, 0), np.maximum(P - b1, 0)); return np.linalg.norm(d, axis=1)

# ---- (1) baseline exact confirmation at the summary rows ----
confirm = {}
for k in ('0%', '50%', '100%'):
    rs = [(i, r) for i, r in enumerate(rows_b) if r['knee'] == k]
    cand = {'nominal': [t for t in rs if t[1]['ankle_mode'] == 'level' and t[1]['yaw'] == '0' and t[1]['roll'] == '0'][0]}
    withc = [t for t in rs if nd_angle(t[1]) is not None]
    if withc:
        cand['worst'] = min(withc, key=lambda t: abs(nd_angle(t[1])))
    for tag, (i, r) in cand.items():
        a = nd_angle(r)
        if a is None:
            # no contact in range: exact gap at the range end
            T = pose_T(r, r['nose_down_range_end_deg']); g = {b: float(BODY_MAN[b].transform(np.asarray(T[b][:3, :4])).min_gap(BASE, 30.0)) for b in bodies[2:]}
            confirm[f'{k}/{tag}'] = {'first_contact': 'none', 'exact_min_gap_at_range_end_mm': round(min(g.values()), 3), 'body': LABEL[min(g, key=g.get)], 'row': {kk: r[kk] for kk in ('knee', 'ankle_mode', 'yaw', 'roll')}}
            continue
        out = {}
        for a_ in (a - NOSE_DOWN * 2.0, a, a + NOSE_DOWN * 2.0):
            if abs(a_) > 90 + 1e-6: continue
            T = pose_T(r, a_); g = {b: float(BODY_MAN[b].transform(np.asarray(T[b][:3, :4])).min_gap(BASE, 30.0)) for b in bodies[2:]}
            out[str(round(a_, 1))] = {'exact_min_gap_mm': round(min(g.values()), 3), 'body': LABEL[min(g, key=g.get)]}
        first_exact = next((float(ang) for ang, v in sorted(out.items(), key=lambda t: abs(float(t[0]))) if v['exact_min_gap_mm'] < CONTACT), None)
        confirm[f'{k}/{tag}'] = {'field_first_contact_deg': a, 'exact_gaps_by_hip_pitch_deg': out, 'exact_first_contact_deg': first_exact if first_exact is not None else f'>= {a + NOSE_DOWN * 4.0:.1f} (not within +-2 deg of the estimate)',
                                 'row': {kk: r[kk] for kk in ('knee', 'ankle_mode', 'yaw', 'roll')}}
    print(k, json.dumps({kk: v for kk, v in confirm.items() if kk.startswith(k)}), flush=True)

# ---- (2) pack more limiting than baseline: responsible component and required shift ----
PLATE_FLD = make_field(man_to_mesh(COMPS['PLATE_trimmed']))
shift_grid = np.arange(0.0, 30.01, 0.5)
out = []
for rp, rb in zip(rows_p, rows_b):
    ap, ab = nd_angle(rp), nd_angle(rb)
    if ap is None or (ab is not None and abs(ap) >= abs(ab) - 1e-6):
        continue
    comp = rp['nose_down_first_contact']['responsible_component']
    end = abs(ab) - 2.0 if ab is not None else abs(rp['nose_down_range_end_deg'])
    angs = [a for a in R['hip_pitch_grid_deg'] if NOSE_DOWN * a >= abs(ap) - 1e-9 and NOSE_DOWN * a <= end + 1e-9]
    PTS = []
    for a in angs:
        T = pose_T(rp, a); PTS.append(np.vstack([LEG_P[b] @ T[b][:3, :3].T + T[b][:3, 3] for b in bodies[2:]]))
    req = {}
    for dname, dvec in (('up_+z', np.array([0, 0, 1.0])), ('back_-x', np.array([-1.0, 0, 0]))):
        found = None
        for d in shift_grid:
            if comp == 'PLATE_trimmed':
                ok = all(lookup(PLATE_FLD, P - dvec * d).min() >= CONTACT + max(FIELD_ERR.values()) for P in PTS)
            else:
                b0, b1 = np.array(R['component_boxes'][comp][0]) + dvec * d, np.array(R['component_boxes'][comp][1]) + dvec * d
                ok = all(point_box_dist(P, b0, b1).min() >= CONTACT + max(LEG_COV.values()) for P in PTS)
            if ok:
                found = float(d); break
        req[dname] = found if found is not None else '>30'
    other = {}
    for k2, box in R['component_boxes'].items():
        if k2 == comp: continue
        if k2 == 'PLATE_trimmed':
            other[k2] = round(min(float(lookup(PLATE_FLD, P).min()) for P in PTS), 2)
        else:
            other[k2] = round(min(float(point_box_dist(P, np.array(box[0]), np.array(box[1])).min()) for P in PTS), 2)
    nxt = min(other, key=other.get)
    out.append({'knee': rp['knee'], 'ankle_mode': rp['ankle_mode'], 'yaw': rp['yaw'], 'roll': rp['roll'], 'pack_first_contact_deg': ap, 'baseline_first_contact_deg': ab if ab is not None else 'none',
                'pack_contact': {kk: rp['nose_down_first_contact'][kk] for kk in ('body', 'part', 'leg_point', 'exact_gap_mm')}, 'baseline_contact': (None if ab is None else {kk: rb['nose_down_first_contact'][kk] for kk in ('body', 'part', 'leg_point')}),
                'responsible_component': comp, 'component_box': R['component_boxes'][comp], 'required_shift_mm': req, 'hip_pitch_angles_checked_deg': [angs[0], angs[-1]] if angs else [],
                'next_limiting_component_over_those_angles': {nxt: other[nxt]}})
    print(json.dumps(out[-1]), flush=True)
json.dump({'baseline_exact_confirmation': confirm, 'pack_more_limiting': out}, open(OUT / f'reach-shift-{side}.json', 'w'), indent=1)
print('rows', len(out))
