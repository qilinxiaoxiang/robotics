"""Round 2 cause study, check 3 (2026-11-18), training side: what does the actor observe on the first tick after a
dropped tick in the distillation env (distill_worker.py --drop-max, delta universal4)? 4 envs on the CPU, the teacher
drives 70 ticks; on ticks 30 and 50 the previous action is applied again (exactly what distill_worker does on a dropped
tick). Per tick, env 0: the actor observation, the applied action, the true joint positions and trunk gravity.

Run from the microduck_rl folder of the mirror (see ts2_cause_analyse.py for the reading):
  .venv/bin/python <train>/ts2_parity_env.py --teacher-onnx <teacher.onnx> --manifest <flightpack-none.json> \
      --audit <existing-model-mass-audit.json> --out <train>/eval/cz_parity_env.json
"""
import argparse
import json
import sys
from pathlib import Path

import torch

RL = Path.cwd()
sys.path.insert(0, str(RL / "cmu/finetune/flight"))

ap = argparse.ArgumentParser()
ap.add_argument("--teacher-onnx", required=True)
ap.add_argument("--manifest", required=True)
ap.add_argument("--audit", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--delta", default="universal4")
a = ap.parse_args()

import distill_worker as dw  # noqa: E402
import flight_worker as fl  # noqa: E402
import teacher as tc  # noqa: E402

fw = fl.fw
env, venv, delta = dw.build_env(fw, a.delta, a.manifest, a.audit, 0.0, 4, 1, "cpu")
obs = venv.get_observations()
teacher = tc.TorchPolicy(a.teacher_onnx)
robot = env.scene["robot"]
om = env.observation_manager
terms = list(om.active_terms["actor"])
dims = [int(d[0]) for d in om.group_obs_term_dim["actor"]]
cfgs = env.cfg.observations["actor"].terms
term_info = {n: dict(dim=dm, delay_min_lag=getattr(cfgs[n], "delay_min_lag", None), delay_max_lag=getattr(cfgs[n], "delay_max_lag", None),
                     noise=str(getattr(cfgs[n], "noise", None))[:120]) for n, dm in zip(terms, dims)}
HOLD = (30, 50)
rows, prev = [], None
with torch.no_grad():
    for t in range(70):
        o = obs["actor"]
        act = teacher(torch.cat([o, tc.priv_obs(env)], dim=1))
        held = t in HOLD and prev is not None
        applied = prev.clone() if held else act
        rows.append(dict(t=t, held=held, obs=[round(float(x), 5) for x in o[0]], applied=[round(float(x), 5) for x in applied[0]],
                         q_true=[round(float(x), 5) for x in (robot.data.joint_pos - robot.data.default_joint_pos)[0]],
                         g_true=[round(float(x), 5) for x in robot.data.projected_gravity_b[0]],
                         w_true=[round(float(x), 5) for x in robot.data.root_link_ang_vel_b[0]]))
        obs, _, dones, _ = venv.step(applied)
        rows[-1]["done_after"] = bool(dones[0])
        prev = applied
Path(a.out).write_text(json.dumps(dict(delta=a.delta, loop_delay=delta.get("loop_delay"), terms=terms, dims=dims, term_info=term_info,
                                       hold_ticks=list(HOLD), rows=rows), indent=1))
print("[parity_env] wrote", a.out, terms, dims, flush=True)
