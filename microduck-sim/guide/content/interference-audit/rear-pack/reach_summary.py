"""Assemble reach-pitch.json (both legs, pack vs baseline, shift analysis) and the figure reach-pitch.png."""
import json, os
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT = '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/e281f88a-117d-47f8-a4cc-4faadc6be94a/scratchpad/torso-fit'
os.chdir(OUT)
R = {s: json.load(open(f'reach-pitch-{s}.json')) for s in ('left', 'right')}
SH = {s: (json.load(open(f'reach-shift-{s}.json')) if os.path.exists(f'reach-shift-{s}.json') else 'not run') for s in ('left', 'right')}
KN = ['0%', '25%', '50%', '75%', '100%']
def fc_angle(rec, which='nose_down_first_contact'):
    fc = rec[which]; return None if fc == 'none' else abs(fc['hip_pitch_deg'])
def table(rows):
    """worst (smallest first-contact angle) over ankle/yaw/roll for each knee, and the nominal row (ankle level, yaw 0, roll 0)."""
    out = {}
    for k in KN:
        rs = [r for r in rows if r['knee'] == k]
        angs = [(fc_angle(r) if fc_angle(r) is not None else 999, r) for r in rs]
        worst = min(angs, key=lambda t: t[0]); nominal = [r for r in rs if r['ankle_mode'] == 'level' and r['yaw'] == '0' and r['roll'] == '0'][0]
        n_contact = sum(1 for a, _ in angs if a < 999)
        out[k] = {'knee_deg': rs[0]['knee_deg'],
                  'worst_case': {'first_contact_hip_pitch_deg': (worst[0] if worst[0] < 999 else 'none'), 'ankle_mode': worst[1]['ankle_mode'], 'yaw': worst[1]['yaw'], 'roll': worst[1]['roll'],
                                 'contact': worst[1]['nose_down_first_contact'] if worst[0] < 999 else {'min_coarse_gap_over_sweep_mm': min(r['nose_down_min_coarse_gap_mm'] for r in rs)}},
                  'nominal_level_ankle_yaw0_roll0': {'first_contact_hip_pitch_deg': (fc_angle(nominal) if fc_angle(nominal) is not None else 'none'), 'contact': nominal['nose_down_first_contact'], 'min_coarse_gap_over_sweep_mm': nominal['nose_down_min_coarse_gap_mm']},
                  'combinations_with_contact_in_range': f'{n_contact}/{len(rs)}',
                  'nose_up_any_contact': any(r['nose_up_first_contact'] != 'none' for r in rs)}
    return out
res = {'method': 'pso_lib FK of robot_allcollisions.xml; hip pitch over its full range in 2 deg steps; knee at 0/25/50/75/100 % of the flexion half-range; ankle at 0, level with the torso floor, and both range ends; '
                 'hip yaw and roll at 0 and +-10 deg; exact manifold3d min_gap of the thigh/knee, shin and ankle/foot bodies (hip yaw/roll bodies once per yaw/roll); first contact = first hip-pitch step from 0 in the nose-down direction with gap < 1 mm',
       'nose_down_definition': 'hip-pitch sign that moves the foot backward (-x) in the torso frame = torso pitching nose-down over a planted foot; with a vertical thigh the hip-pitch angle equals the torso pitch',
       'solids': {'pack': 'Layout L pack solid, plate trimmed to the original power_support silhouette (finalps25)', 'baseline': 'original battery + original power_support (union of the guide-frame meshes)'},
       'gap_estimate': R['left']['gap_estimate'], 'per_leg': {}, 'figure': f'{OUT}/reach-pitch.png'}
for s in ('left', 'right'):
    r = R[s]
    res['per_leg'][s] = {'conventions': r['conventions'], 'knee_values_deg': r['knee_values_deg'], 'hip_pitch_grid_deg': [r['hip_pitch_grid_deg'][0], r['hip_pitch_grid_deg'][-1], 2.0],
                         'component_boxes': r['component_boxes'], 'solids': r['solids'],
                         'pack': {'summary_by_knee': table(r['results']['pack']['rows']), 'hip_bodies_by_yaw_roll': r['results']['pack']['hip_bodies_by_yaw_roll']},
                         'baseline': {'summary_by_knee': table(r['results']['baseline']['rows']), 'hip_bodies_by_yaw_roll': r['results']['baseline']['hip_bodies_by_yaw_roll']},
                         'all_combinations': [{k: v for k, v in rp.items() if k != 'gap_curve_deg_mm'} | {'baseline_nose_down_first_contact': rb['nose_down_first_contact'], 'baseline_nose_down_min_coarse_gap_mm': rb['nose_down_min_coarse_gap_mm']}
                                              for rp, rb in zip(r['results']['pack']['rows'], r['results']['baseline']['rows'])],
                         'pack_more_limiting_than_baseline': (SH[s]['pack_more_limiting'] if isinstance(SH[s], dict) else SH[s]),
                         'baseline_exact_confirmation_at_summary_rows': (SH[s]['baseline_exact_confirmation'] if isinstance(SH[s], dict) else SH[s])}
# headline numbers
def head(s, sol, k, key='worst_case'):
    return res['per_leg'][s][sol]['summary_by_knee'][k][key]['first_contact_hip_pitch_deg']
res['headline_max_nose_down_torso_pitch_deg'] = {
    'straight_leg_bend(knee 0%)': {s: {'pack_worst_case': head(s, 'pack', '0%'), 'pack_nominal': head(s, 'pack', '0%', 'nominal_level_ankle_yaw0_roll0'),
                                       'baseline_worst_case': head(s, 'baseline', '0%'), 'baseline_nominal': head(s, 'baseline', '0%', 'nominal_level_ankle_yaw0_roll0')} for s in ('left', 'right')},
    'crouched_bend(knee 100%)': {s: {'pack_worst_case': head(s, 'pack', '100%'), 'pack_nominal': head(s, 'pack', '100%', 'nominal_level_ankle_yaw0_roll0'),
                                     'baseline_worst_case': head(s, 'baseline', '100%'), 'baseline_nominal': head(s, 'baseline', '100%', 'nominal_level_ankle_yaw0_roll0')} for s in ('left', 'right')},
    'half_crouch(knee 50%)': {s: {'pack_worst_case': head(s, 'pack', '50%'), 'pack_nominal': head(s, 'pack', '50%', 'nominal_level_ankle_yaw0_roll0'),
                                  'baseline_worst_case': head(s, 'baseline', '50%'), 'baseline_nominal': head(s, 'baseline', '50%', 'nominal_level_ankle_yaw0_roll0')} for s in ('left', 'right')},
    'note': 'values are |hip pitch| at first contact (deg); "none" = no contact within the +-90 deg hip-pitch range'}
json.dump(res, open('reach-pitch.json', 'w'), indent=1)
# ---- figure ----
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
for ax, s in zip(axes, ('left', 'right')):
    r = R[s]; kd = [abs(r['knee_values_deg'][k]) for k in KN]
    for sol, col, ls in (('pack', '#d62728', '-'), ('baseline', '#1f77b4', '--')):
        rows = r['results'][sol]['rows']
        worst = []; nominal = []; allpts = []
        for k in KN:
            rs = [x for x in rows if x['knee'] == k]
            a = [fc_angle(x) for x in rs]; a_ = [v if v is not None else 92 for v in a]
            worst.append(min(a_)); nom = [x for x in rs if x['ankle_mode'] == 'level' and x['yaw'] == '0' and x['roll'] == '0'][0]
            v = fc_angle(nom); nominal.append(v if v is not None else 92)
            allpts += [(abs(r['knee_values_deg'][k]), v) for v in a_]
        ax.plot(kd, worst, color=col, ls=ls, lw=2.2, marker='o', label=f'{sol}: worst over ankle/yaw/roll')
        ax.plot(kd, nominal, color=col, ls=ls, lw=1.0, marker='s', ms=4, alpha=0.7, label=f'{sol}: ankle level, yaw 0, roll 0')
        ax.scatter([p[0] + (1.0 if sol == 'pack' else -1.0) for p in allpts], [p[1] for p in allpts], s=8, color=col, alpha=0.25)
    ax.axhline(90, color='grey', lw=0.8, ls=':'); ax.text(kd[0] + 2, 93.2, 'plotted at 92 = no contact within the 90 deg hip-pitch range', fontsize=7, color='grey')
    ax.set_xlabel('knee flexion (deg, 0 = straight, 90 = full flexion; right leg joint value is negative)'); ax.set_title(f'{s} leg: nose-down hip pitch at first contact (< 1 mm)')
    ax.grid(alpha=0.3); ax.set_ylim(0, 96)
axes[0].set_ylabel('hip pitch at first contact (deg)'); axes[0].legend(fontsize=7, loc='lower left')
fig.suptitle('Bend-forward reach: Layout L pack (red) vs original battery + power_support (blue); dots = every ankle/yaw/roll combination', fontsize=10)
fig.tight_layout(); fig.savefig('reach-pitch.png', dpi=130); plt.close(fig)
print('written reach-pitch.json and reach-pitch.png'); print(json.dumps(res['headline_max_nose_down_torso_pitch_deg'], indent=0)[:1500])
