"""spk2 diagnosis: the robot body the runtime sim's no-pack case uses (brain_sim_check --model asbuilt --manifest
train/manifests/flightpack-none.json, through evaluate_delay.load) against the training env's s = 0 body
(cmu_seeing_pick_pack_env_cfg base "none", the robot entity's spec compiled by MuJoCo; the s-scaled pack adds nothing
at s = 0). Both at qpos0: total mass, the whole robot's COM in the trunk_base frame, every body's mass and the trunk's
inertia. The seeing-pick jaw split (10 g moved from jaw_soft to a jaw body) exists only in training here; the
comparison folds jaw into jaw_soft.
  runtime: <guide venv python> train/spk2diag_body.py runtime OUT.json      (run from anywhere)
  train:   <grasp venv python> train/spk2diag_body.py train OUT.json
  compare: python3 train/spk2diag_body.py compare RUNTIME.json TRAIN.json"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[2]


def summary(m, d):
    import mujoco
    import numpy as np
    mujoco.mj_resetData(m, d)
    mujoco.mj_forward(m, d)
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, i) for i in range(m.nbody)]
    tb = names.index("trunk_base")
    root = m.body_rootid[tb]
    ids = [i for i in range(m.nbody) if m.body_rootid[i] == root]
    mass = {names[i]: float(m.body_mass[i]) for i in ids}
    if "jaw" in mass:
        mass["jaw_soft"] = mass.get("jaw_soft", 0.0) + mass.pop("jaw")
    tot = sum(float(m.body_mass[i]) for i in ids)
    com_w = sum(float(m.body_mass[i]) * d.xipos[i] for i in ids) / tot
    R, p = d.xmat[tb].reshape(3, 3), d.xpos[tb]
    com_t = R.T @ (com_w - p)
    tcom = R.T @ (d.xipos[tb] - p)
    return dict(total_kg=round(tot, 5), com_trunk_m=[round(float(v), 5) for v in com_t],
                trunk_com_m=[round(float(v), 5) for v in tcom], trunk_inertia=[float(v) for v in m.body_inertia[tb]],
                body_mass_kg={k: round(v, 5) for k, v in sorted(mass.items())})


def runtime(out):
    sys.path.insert(0, str(SIM / "microduck_rl" / "cmu" / "mac"))   # the copy flight_eval.py / style_eval.py run
    sys.path.insert(0, str(SIM / "microduck_rl" / "cmu" / "model"))
    import brain_sim_check as B  # noqa: F401  (sets the loader paths)
    c0 = B.cfg(0.09, model="asbuilt", kp=200, voltage=7.6)   # flight_eval.py runs --volt 7.6
    c0["friction"] = 1.0
    c0["mass_manifest"] = str(HERE / "manifests" / "flightpack-none.json")
    m, d, c, names, bam = B.ev.load(c0)
    Path(out).write_text(json.dumps(summary(m, d), indent=1))


def train(out):
    import mujoco
    sys.path.insert(0, str(SIM / "microduck_rl-grasp" / "cmu" / "grasp"))
    from mjlab_microduck.tasks import cmu_seeing_pick_pack_env_cfg as pk
    cfg = pk.make_seeing_pick_pack_env_cfg(base="none", weights=pk.pin_weights("none"), window_start=0.0, scale=0.0,
                                           fall_penalty=0.0)
    spec = cfg.scene.entities["robot"].spec_fn()
    m = spec.compile()
    Path(out).write_text(json.dumps(summary(m, mujoco.MjData(m)), indent=1))


def compare(a, b):
    r, t = json.loads(Path(a).read_text()), json.loads(Path(b).read_text())
    print(f"total kg runtime {r['total_kg']} train {t['total_kg']} diff {round(t['total_kg'] - r['total_kg'], 5)}")
    print(f"robot COM in trunk frame runtime {r['com_trunk_m']} train {t['com_trunk_m']} diff (mm) "
          f"{[round(1000 * (x - y), 2) for x, y in zip(t['com_trunk_m'], r['com_trunk_m'])]}")
    print(f"trunk body COM runtime {r['trunk_com_m']} train {t['trunk_com_m']}; inertia runtime "
          f"{[round(v, 7) for v in r['trunk_inertia']]} train {[round(v, 7) for v in t['trunk_inertia']]}")
    keys = sorted(set(r["body_mass_kg"]) | set(t["body_mass_kg"]))
    for k in keys:
        x, y = r["body_mass_kg"].get(k), t["body_mass_kg"].get(k)
        if x is None or y is None or abs(x - y) > 1e-4:
            print(f"  body {k}: runtime {x} train {y}")


if __name__ == "__main__":
    {"runtime": runtime, "train": train}[sys.argv[1]](sys.argv[2]) if sys.argv[1] != "compare" else compare(*sys.argv[2:4])
