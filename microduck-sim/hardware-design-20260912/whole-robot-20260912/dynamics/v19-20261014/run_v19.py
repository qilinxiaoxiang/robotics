"""As-built (2026-10-14) walk check: constant-delay grid with the frozen September evaluator plus the measured-link
replay, graded by the unchanged September gate (dynamics/run_compact_suite.grade).

Writes runs/<tag>.config.json, runs/<tag>.json, runs/<tag>.log and v19-walk-summary.json in this folder.
"""
from pathlib import Path
import concurrent.futures, copy, json, subprocess, sys, time, math
import numpy as np

HERE = Path(__file__).resolve().parent
WHOLE = HERE.parents[1]
FROZEN = WHOLE / 'dynamics'; DELAY = WHOLE / 'delay-repair-20260912'
sys.path.insert(0, str(FROZEN)); sys.path.insert(0, str(DELAY))
from run_compact_suite import grade  # noqa: E402
RUNS = HERE / 'runs'; RUNS.mkdir(exist_ok=True)
PY = sys.executable
BATTERY_G = [60, 90, 120]   # assumption sweep: mass of the NP-F970 inside the official lumped trunk
SEEDS = [0, 9, 42]


def base(battery_g):
    c = json.loads((FROZEN / 'final-perturb-batteryremove0-sensor40.config.json').read_text())
    for k in ['geometry_manifest', 'name']:
        c.pop(k, None)
    c.update(mass_manifest=str(HERE / 'v19-mass-manifest.json'), mass_parts=[], remove_old_battery_kg=battery_g / 1000,
             duration=30, voltage=5, kp=200, current_limit=1.47, command=[0.3, 0, 0], action_delay_ticks=1,
             heading_hold=True, heading_gain=2, heading_rate_limit=0.8, prediction_fraction=1.0,
             predict_heading=True)
    return c


def job(tag, config, script):
    cp = RUNS / f'{tag}.config.json'; out = RUNS / f'{tag}.json'
    config['name'] = tag
    cp.write_text(json.dumps(config, indent=1) + '\n')
    p = subprocess.run([PY, str(script), str(cp), '--output', str(out)], capture_output=True, text=True)
    (RUNS / f'{tag}.log').write_text(p.stdout + p.stderr)
    if p.returncode:
        return {'tag': tag, 'error': p.stderr[-2000:], 'walking_gate_pass': False}
    raw = json.loads(out.read_text())
    r = grade(raw, config); r['tag'] = tag
    for k in ['policy_calls', 'applied_joint_age_ms', 'applied_imu_age_ms']:
        if k in raw: r[k] = raw[k]
    # failure cause: first gate item violated, with time
    rows = raw['rows']
    first_tilt30 = next((x['time'] for x in rows if x['tilt_deg'] > 30), None)
    r['first_tilt_over_30deg_s'] = first_tilt30
    r['config'] = {k: config.get(k) for k in ['remove_old_battery_kg', 'sensor_delay_ticks', 'delay_compensation',
                                               'seed', 'joint_noise', 'link_mode']}
    print(json.dumps({k: r.get(k) for k in ['tag', 'walking_gate_pass', 'fell', 'fall_time_s', 'max_tilt_deg',
                                            'mean_forward_velocity_m_s', 'max_abs_heading_deviation_deg', 'mass_kg']}),
          flush=True)
    return r


def mass_report():
    """Total mass, trunk body COM and whole-robot COM at HOME (trunk frame) for official, September and V1.9."""
    import mujoco
    sys.path.insert(0, str(DELAY)); import evaluate_delay as ev
    out = {}
    cases = {'official': dict()}
    for old in [0, 60, 120]:
        cases[f'september-full-batteryremove{old}-headremove15'] = json.loads(
            (FROZEN / f'final-perturb-batteryremove{old}-sensor40.config.json').read_text())
    for b in BATTERY_G:
        cases[f'asbuilt-batteryremove{b}'] = base(b)
    for name, cfg in cases.items():
        m, d, c, names, bam = ev.load(cfg)
        ji = np.array([m.actuator(n).trnid[0] for n in names])
        d.qpos[:7] = [0, 0, .12, 1, 0, 0, 0]; d.qpos[m.jnt_qposadr[ji]] = ev.HOME
        mujoco.mj_forward(m, d)
        tb = m.body('trunk_base').id; R = d.xmat[tb].reshape(3, 3)
        com_all = (d.subtree_com[0] - d.xpos[tb]) @ R
        out[name] = dict(total_mass_g=round(float(m.body_mass.sum()) * 1000, 1),
                         trunk_base_mass_g=round(float(m.body_mass[tb]) * 1000, 1),
                         trunk_base_body_com_mm=np.round(m.body_ipos[tb] * 1000, 2).tolist(),
                         head_jaw_soft_mass_g=round(float(m.body_mass[m.body('jaw_soft').id]) * 1000, 1),
                         whole_robot_com_at_home_in_trunk_frame_mm=np.round(com_all * 1000, 2).tolist())
    ref = out['official']
    for v in out.values():
        v['delta_total_vs_official_g'] = round(v['total_mass_g'] - ref['total_mass_g'], 1)
        v['delta_trunk_com_vs_official_mm'] = np.round(np.array(v['trunk_base_body_com_mm']) -
                                                       ref['trunk_base_body_com_mm'], 2).tolist()
        v['delta_whole_com_vs_official_mm'] = np.round(np.array(v['whole_robot_com_at_home_in_trunk_frame_mm']) -
                                                       ref['whole_robot_com_at_home_in_trunk_frame_mm'], 2).tolist()
    return out


if __name__ == '__main__':
    started = time.time()
    jobs = []
    # environment check: one frozen September case must reproduce exactly
    sept = json.loads((DELAY / 'grid-old60-sensor40-seed0.config.json').read_text())
    jobs.append(('repro-sept-grid-old60-sensor40-seed0', sept, DELAY / 'evaluate_delay.py'))
    for b in BATTERY_G:
        for delay in [0, 1, 2, 3]:
            for comp in ['none', 'constant_velocity']:
                for seed in SEEDS:
                    c = base(b); c.update(sensor_delay_ticks=delay, delay_compensation=comp, seed=seed,
                                          joint_noise=0.03 if seed else 0.0)
                    jobs.append((f'const-bat{b}-sensor{delay * 20}-{"comp" if comp != "none" else "nocomp"}-seed{seed}',
                                 c, DELAY / 'evaluate_delay.py'))
        for mode in ['event', 'tick']:
            for comp in ['none', 'constant_velocity']:
                for seed in SEEDS:
                    c = base(b); c.update(link_mode=mode, delay_compensation=comp, seed=seed,
                                          joint_noise=0.03 if seed else 0.0, sensor_delay_ticks=0, action_delay_ticks=0)
                    jobs.append((f'link{mode}-bat{b}-{"comp" if comp != "none" else "nocomp"}-seed{seed}', c,
                                 HERE / 'evaluate_link.py'))
    val = []
    for comp in ['none', 'constant_velocity']:
        for sd in [0, 2]:
            c = base(90); c.update(sensor_delay_ticks=sd, delay_compensation=comp, seed=0, joint_noise=0.0)
            val.append((f'val-const-{comp}-{sd}', c, DELAY / 'evaluate_delay.py'))
            c = base(90); c.update(link_mode='tick', fixed_age_s=0.02 * (sd + 1), delay_compensation=comp, seed=0,
                                   joint_noise=0.0, sensor_delay_ticks=0, action_delay_ticks=0)
            val.append((f'val-tick-{comp}-{sd}', c, HERE / 'evaluate_link.py'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda j: job(*j), jobs))
        list(pool.map(lambda j: job(*j), val))
    validation = {}
    for comp in ['none', 'constant_velocity']:
        for sd in [0, 2]:
            A = json.loads((RUNS / f'val-const-{comp}-{sd}.json').read_text())['rows']
            B = json.loads((RUNS / f'val-tick-{comp}-{sd}.json').read_text())['rows']
            validation[f'{comp}-sensor{sd * 20}'] = dict(
                same_length=len(A) == len(B),
                max_abs_x_difference_m=max(abs(a['x'] - b['x']) for a, b in zip(A, B)))
    frozen = json.loads((DELAY / 'grid-old60-sensor40-seed0.json').read_text())
    repro = json.loads((RUNS / 'repro-sept-grid-old60-sensor40-seed0.json').read_text())
    repro_ok = frozen['rows'][-1]['qpos'] == repro['rows'][-1]['qpos']

    groups = {}
    for r in results[1:]:
        key = r['tag'].rsplit('-seed', 1)[0]
        groups.setdefault(key, []).append(r)
    summary = dict(
        gate='Unchanged September gate (run_compact_suite.grade): 30 s completed, no fall, no MuJoCo warning, no '
             'non-foot ground contact, mean world-x velocity 3-28 s >= 0.03 m/s, max trunk tilt <= 30 deg, heading '
             'deviation in 3-28 s <= 30 deg.',
        link_evaluator_validation=dict(note='evaluate_link tick mode with a constant age reproduces evaluate_delay '
                                       'trajectories (sensor delay = age - 20 ms, 20 ms action queue)', **validation),
        reproduction_check=dict(case='delay-repair grid-old60-sensor40-seed0', final_qpos_identical=repro_ok,
                                walking_gate_pass=results[0].get('walking_gate_pass')),
        mass=mass_report(),
        pass_counts={k: f"{sum(x['walking_gate_pass'] for x in v)}/{len(v)}" for k, v in sorted(groups.items())},
        cases=[{k: r.get(k) for k in ['tag', 'walking_gate_pass', 'fell', 'fall_time_s', 'first_tilt_over_30deg_s',
                                      'max_tilt_deg', 'mean_forward_velocity_m_s', 'max_abs_heading_deviation_deg',
                                      'nonfoot_ground_contact_samples', 'mass_kg', 'peak_summed_motor_current_proxy_a',
                                      'policy_calls', 'applied_joint_age_ms', 'applied_imu_age_ms', 'error', 'config']}
               for r in results[1:]],
        link=json.loads((HERE / 'link-timeline-summary.json').read_text()),
        wall_seconds=round(time.time() - started, 1))
    (HERE / 'v19-walk-summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps({'repro': repro_ok, 'pass_counts': summary['pass_counts']}, indent=1))
