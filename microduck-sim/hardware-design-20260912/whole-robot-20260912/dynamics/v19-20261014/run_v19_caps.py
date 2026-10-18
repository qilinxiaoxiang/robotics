"""Counterfactual link sweep: the measured timeline with one-way Wi-Fi latency clipped at a cap (event replay),
to find which part of the measured link breaks walking. Adds `link_cap_sweep` to v19-walk-summary.json."""
import concurrent.futures, json
from run_v19 import base, job, HERE

CAPS_MS = [10, 20, 30, 50, 100]
if __name__ == '__main__':
    jobs = []
    for cap in CAPS_MS:
        for comp in ['none', 'constant_velocity']:
            for seed in [0, 9, 42]:
                c = base(90); c.update(link_mode='event', rx_lag_cap_s=cap / 1000, delay_compensation=comp, seed=seed,
                                       joint_noise=0.03 if seed else 0.0, sensor_delay_ticks=0, action_delay_ticks=0)
                jobs.append((f'linkevent-cap{cap}-bat90-{"comp" if comp != "none" else "nocomp"}-seed{seed}', c,
                             HERE / 'evaluate_link.py'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        res = list(pool.map(lambda j: job(*j), jobs))
    groups = {}
    for r in res:
        groups.setdefault(r['tag'].rsplit('-seed', 1)[0], []).append(r)
    out = {k: dict(pass_count=f"{sum(x['walking_gate_pass'] for x in v)}/{len(v)}",
                   falls=[x['fall_time_s'] for x in v],
                   applied_joint_age_ms=[x.get('applied_joint_age_ms') for x in v]) for k, v in groups.items()}
    p = HERE / 'v19-walk-summary.json'; s = json.loads(p.read_text())
    s['link_cap_sweep'] = dict(note='battery removal 90 g; event replay of the same log windows with each one-way '
                               'latency clipped at the cap (counterfactual: Wi-Fi bursts removed, Pi read time and '
                               'loop timing kept)', groups=out)
    p.write_text(json.dumps(s, indent=1) + '\n')
    print(json.dumps({k: (v['pass_count'], v['falls']) for k, v in out.items()}, indent=1))
