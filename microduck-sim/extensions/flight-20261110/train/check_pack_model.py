"""Smoke check 1: the training model (mjlab robot + finetune_worker.apply_asbuilt_masses + pack manifest) carries the
same mass and COM as the probe model (brain_sim_check's evaluate_delay loader + the same manifest) and as
sim/out/mass_report.json (snapshot in train/manifests/mass_report.snapshot.json).

  <microduck_rl venv python> train/check_pack_model.py [manifest ...]   -> train/out/check_pack_model.json

Compile only, no simulation (seconds). Whole-robot COM is expressed in the trunk_base frame with every joint at the
policies' default pose, so both models are compared in the same posture; the mass report's COM is at the probe's
stand keyframe, so its COM is compared with a tolerance (posture differs by the brain stand pose).
"""
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
RL = HERE.parents[2] / "microduck_rl"
sys.path.insert(0, str(RL / "cmu/finetune/modal"))
sys.path.insert(0, str(RL / "cmu/mac"))
import finetune_worker as fw  # noqa: E402

DEFAULT = dict(left_hip_yaw=0.0, left_hip_roll=-0.087, left_hip_pitch=-0.458, left_knee=-0.005, left_ankle=0.453,
               neck_pitch=0.349, head_pitch=0.349, head_yaw=0.0, head_roll=0.0, right_hip_yaw=0.0, right_hip_roll=0.087,
               right_hip_pitch=0.458, right_knee=0.005, right_ankle=-0.453)


def com_in_trunk(m):
    d = mujoco.MjData(m)
    for j, v in DEFAULT.items():
        d.qpos[m.jnt_qposadr[m.joint(j).id]] = v
    mujoco.mj_forward(m, d)
    t = m.body("trunk_base").id
    total = float(m.body_subtreemass[0])
    com_w = (d.xipos * m.body_mass[:, None]).sum(0) / total
    R = d.xmat[t].reshape(3, 3)
    return total, (R.T @ (com_w - d.xpos[t])) * 1000, float(m.body_mass[t])


def training_model(manifest):
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    cfg = load_env_cfg(fw.TASK, play=False)
    robot = fw.apply_asbuilt_masses(cfg.scene.entities["robot"], manifest,
                                    str(RL / "cmu/whole/electrical/existing-model-mass-audit.json"), 0.09)
    return robot.spec_fn().compile()


def probe_model(manifest):
    import brain_sim_check as b
    c0 = b.cfg(0.09, model="asbuilt", kp=200, voltage=7.6)
    c0["mass_manifest"] = manifest
    m, d, c, names, bam = b.ev.load(c0)
    return m


def main():
    mans = sys.argv[1:] or [str(HERE / "manifests/flightpack-nominal.json"), str(HERE / "manifests/flightpack-none.json")]
    rep = json.loads((HERE / "manifests/mass_report.snapshot.json").read_text())
    out = {}
    for man in mans:
        tm, pm = training_model(man), probe_model(man)
        t_total, t_com, t_trunk = com_in_trunk(tm)
        p_total, p_com, p_trunk = com_in_trunk(pm)
        r = dict(training=dict(total_kg=round(t_total, 4), trunk_base_kg=round(t_trunk, 4), com_trunk_mm=np.round(t_com, 1).tolist()),
                 probe=dict(total_kg=round(p_total, 4), trunk_base_kg=round(p_trunk, 4), com_trunk_mm=np.round(p_com, 1).tolist()),
                 mass_rel_diff=round(abs(t_total - p_total) / p_total, 5), com_diff_mm=round(float(np.linalg.norm(t_com - p_com)), 2))
        if "nominal" in man:
            ref = rep["duck_with_pack"]
            r["mass_report"] = dict(total_kg=ref["mass_g"] / 1000, com_trunk_mm=ref["com_trunk_mm"],
                                    mass_rel_diff=round(abs(t_total - ref["mass_g"] / 1000) / (ref["mass_g"] / 1000), 5))
        if "none" in man:
            ref = rep["duck_without_pack"]
            r["mass_report"] = dict(total_kg=ref["mass_g"] / 1000, com_trunk_mm=ref["com_trunk_mm"],
                                    mass_rel_diff=round(abs(t_total - ref["mass_g"] / 1000) / (ref["mass_g"] / 1000), 5))
        r["pass_mass_1pct"] = r["mass_rel_diff"] < 0.01 and r.get("mass_report", {}).get("mass_rel_diff", 0) < 0.01
        out[Path(man).name] = r
        print(Path(man).name, json.dumps(r), flush=True)
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out/check_pack_model.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
