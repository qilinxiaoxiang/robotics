"""The 2026-11-01 scan offsets in the as-built sim: centre of mass, support margin and the holding load of the head joints at
the two scanned poses, then the model settled on the robot's real servo goals and compared with the robot's log.

    ~/.venvs/microduck-dyn/bin/python sim_static.py --build-manifest
    ~/.venvs/microduck-dyn/bin/python sim_static.py

Inputs: poses.json (held joint angles, IMU gravity), real_static.json (servo goal, position and current of the same
minutes). The offsets are the scan's, not fitted here. Rail voltage from CURRENT-STATE.json servo_rail_v.
"""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.join(HERE, "..", "guide", "firmware", "mac")
sys.path.insert(0, MAC)
import target_ground  # noqa: E402,F401  (sets the import paths of the sim)
import mujoco  # noqa: E402
import evaluate_delay as ev  # noqa: E402
from duck_kin import trunk_rotation  # noqa: E402
from joint_signs import MOTOR_OFFSET, MOTOR_SIGN  # noqa: E402
from static_gap import cfg, feet_flat_rot, setup, sole_points  # noqa: E402

VARIANT = os.path.join(HERE, "variant-charger-20261101.json")
MANIFEST = os.path.join(HERE, "manifest-charger-20261101.json")
TEAM_MODEL = os.path.join(HERE, "..", "microduck_rl", "cmu", "model")
ID_NAMES = ["right_ankle", "right_knee", "right_hip_pitch", "right_hip_roll", "right_hip_yaw", "left_ankle", "left_knee",
            "left_hip_pitch", "left_hip_roll", "left_hip_yaw", "head_pitch", "neck_pitch", "head_yaw", "head_roll"]
TICK = 2 * math.pi / 4096
VOLT = json.load(open(os.path.join(HERE, "..", "CURRENT-STATE.json")))["facts"]["servo_rail_v"]["value"]
POSES = json.load(open(os.path.join(HERE, "poses.json")))
REAL = json.load(open(os.path.join(HERE, "real_static.json")))
# Scan-derived hypotheses: extra forward angle the rigid chain misses, deg (chain_fit.py). The ankle case stands for play
# below the encoders: the trunk leans with every leg encoder still, feet flat.
CASES = {
    "chain as logged": {},
    "neck -10.4 deg": {"neck_pitch": -10.41},
    "ankles 9.7 deg (trunk forward)": {"ankles": 9.69},
    "ankles 5 deg + neck -5 deg": {"ankles": 5.0, "neck_pitch": -5.0},
    # Trunk at the untrimmed IMU pitch (the scan's trunk reading), the neck taking the rest of the head's angle, per pose.
    "scan best per pose": {"stand": {"ankles": 2.5, "neck_pitch": -5.0}, "bend": {"ankles": 9.0, "neck_pitch": -1.0}},
}


def build_manifest():
    from pathlib import Path
    sys.path.insert(0, TEAM_MODEL)
    import apply_masses
    import make_variants
    variant, parts, removed, added, chain = make_variants.resolve_variant(Path(VARIANT))
    base = apply_masses.load_manifest(apply_masses.BASE_MANIFEST)
    man = dict(schema=base["schema"], build=f"{variant['variant']} ({variant['describes']}); sim_static.py --build-manifest on top of {' -> '.join(chain)}",
               frame=base["frame"], excluded=base["excluded"] + ["NP-F970 battery: removed by the runner (remove_old_battery_kg)"],
               derived=dict(removed=[p["id"] for p in removed], added=[p["id"] for p in added],
                            net_delta_g=round(sum(p["mass_kg"] for p in added) * 1000 - sum(p["mass_kg"] for p in removed) * 1000, 2)),
               parts=parts)
    json.dump(man, open(MANIFEST, "w"), indent=1)
    print("wrote", MANIFEST, "net", man["derived"]["net_delta_g"], "g against", chain[0])


def load(manifest=MANIFEST, foot_play=None):
    c0 = cfg(0.09, model="asbuilt", kp=200, voltage=VOLT)
    c0["friction"] = 1.0
    if manifest:
        c0["mass_manifest"] = manifest
    if foot_play:
        c0["foot_play"] = foot_play
    m, d, c, names, bam = ev.load(c0)
    return m, d, c, names, bam


def goals(name):
    """Real servo goals of the hold in model rad: tick = 2048 + (rad * sign + offset) / tick size."""
    return {n: ((REAL[name]["j"][n]["goal"] - 2048) * TICK - MOTOR_OFFSET[n]) * MOTOR_SIGN[n] for n in ID_NAMES}


def apply_case(q, case):
    """The real joint is the reading plus the case's hidden offset. Forward lean at the ankles: the sign of each ankle
    comes from probe_ankle_sign."""
    q = dict(q)
    for k, v in case.items():
        if k == "ankles":
            q["left_ankle"] += math.radians(v) * ANKLE_SIGN["left_ankle"]
            q["right_ankle"] += math.radians(v) * ANKLE_SIGN["right_ankle"]
        else:
            q[k] += math.radians(v)
    return q


def place_flat(m, d, names, q):
    """Feet flat on the floor at joints q. Returns the trunk pitch in deg (+ forward)."""
    R = feet_flat_rot(m, d, names, q)
    quat = np.zeros(4)
    mujoco.mju_mat2Quat(quat, R.ravel())
    setup(m, d, names, q, quat)
    zmin = np.vstack(sole_points(m, d))[:, 2].min()
    d.qpos[2] -= zmin
    mujoco.mj_forward(m, d)
    trunk = m.body("trunk_base").id
    Rt = d.xmat[trunk].reshape(3, 3)
    return math.degrees(math.atan2(-Rt[2, 0], Rt[0, 0]))


def probe_ankle_sign(m, d, names):
    q = {n: POSES["stand"]["q"][i] for i, n in enumerate(ID_NAMES)}
    base = place_flat(m, d, names, q)
    out = {}
    for n in ("left_ankle", "right_ankle"):
        q2 = dict(q)
        q2[n] += 0.1
        # one ankle alone breaks flatness; feet_flat_rot follows the left sole, so judge the pair at the same sign pattern
        out[n] = q2
    # the two ankles are mirrored in this model's trained pose: find the pattern that pitches the trunk forward
    best = None
    for sl, sr in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        q2 = dict(q)
        q2["left_ankle"] += 0.1 * sl
        q2["right_ankle"] += 0.1 * sr
        p = place_flat(m, d, names, q2)
        setup_rows = sole_points(m, d)
        spread = max(float(np.ptp(s[:, 2])) for s in setup_rows)
        if best is None or (p - base, -spread) > (best[0], -best[1]):
            best = (p - base, spread, sl, sr)
    return {"left_ankle": best[2], "right_ankle": best[3]}, base, best


def support(m, d):
    """Sole extents along x in the world frame and the COM margin to them, mm."""
    pts = np.vstack(sole_points(m, d))
    low = pts[pts[:, 2] < pts[:, 2].min() + 0.003]
    com = d.subtree_com[m.body("trunk_base").id].copy()
    front, rear = low[:, 0].max(), low[:, 0].min()
    return com, front, rear, low[:, 1].min(), low[:, 1].max()


def bias(m, d, names, n):
    return float(d.qfrc_bias[m.jnt_dofadr[m.actuator(n).trnid[0]]])


def static_table(m, d, names):
    rows = {}
    for pose in ("stand", "bend"):
        logged = {n: POSES[pose]["q"][i] for i, n in enumerate(ID_NAMES)}
        for label, case in CASES.items():
            case = case.get(pose, case)
            q = apply_case(logged, case)
            pitch = place_flat(m, d, names, q)
            com, front, rear, ymin, ymax = support(m, d)
            d.qvel[:] = 0
            mujoco.mj_forward(m, d)
            rows[(pose, label)] = dict(trunk_pitch_flat_deg=pitch, com_x=com[0] * 1000, com_z=com[2] * 1000, com_y=com[1] * 1000, front=(front - com[0]) * 1000, rear=(com[0] - rear) * 1000,
                                       tau_neck=bias(m, d, names, "neck_pitch"), tau_head=bias(m, d, names, "head_pitch"))
            r = rows[(pose, label)]
            print(f"{pose:5s} {label:32s} trunk(flat) {pitch:+6.1f} deg  COM x {r['com_x']:+6.1f} z {r['com_z']:5.1f} y {r['com_y']:+5.1f} mm  margin front {r['front']:5.1f} rear {r['rear']:5.1f}  hold neck {r['tau_neck']:+.3f} head {r['tau_head']:+.3f} Nm")
    return rows


def settle(m, d, c, names, bam, pose, case, seconds=4.0):
    """Hold the real goals from the real pose (+ hidden case) and read what the model does."""
    g = apply_case(goals(pose), case)
    logged = {n: POSES[pose]["q"][i] for i, n in enumerate(ID_NAMES)}
    q0 = apply_case(logged, case)
    place_flat(m, d, names, q0)
    d.qvel[:] = 0
    d.qpos[2] += 0.001
    ji = np.array([m.actuator(n).trnid[0] for n in names])
    qa = m.jnt_qposadr[ji]
    c.q_target = np.array([g[n] for n in names])
    bam.actuator.kp = 200
    mujoco.mj_forward(m, d)
    for _ in range(int(seconds / m.opt.timestep)):
        c.update()
        mujoco.mj_step(m, d)
    trunk = m.body("trunk_base").id
    Rt = d.xmat[trunk].reshape(3, 3)
    gb = Rt.T @ np.array([0, 0, -1.0])
    q = {n: float(d.qpos[qa[i]]) for i, n in enumerate(names)}
    cur = {n: float(d.ctrl[i]) / float(bam.kt.value) * 1000 for i, n in enumerate(names)}
    return dict(q=q, g=g, gb=gb.tolist(), z=float(d.qpos[2]), cur=cur, moved=float(np.linalg.norm(d.qvel[:3])))


def compare(res, pose, case):
    """Sim against the log, in the servos' own signed terms: position minus goal (rad) and current (mA)."""
    out = {}
    J = ("left_ankle", "right_ankle", "left_knee", "right_knee", "left_hip_pitch", "right_hip_pitch", "neck_pitch", "head_pitch")
    logged_gb = POSES[pose]["gb"]
    errs, curs = [], []
    txt = []
    for n in J:
        sim_err = (res["q"][n] - res["g"][n]) * MOTOR_SIGN[n]
        real_err = REAL[pose]["j"][n]["err"]
        sim_cur = res["cur"][n] * MOTOR_SIGN[n]
        real_cur = REAL[pose]["j"][n]["cur"]
        errs.append(sim_err - real_err)
        curs.append(abs(sim_cur) - abs(real_cur))
        txt.append(f"{n.replace('_pitch', '').replace('left_', 'L').replace('right_', 'R')}: {sim_err:+.3f}/{real_err:+.3f}")
    out["err_rms"] = float(np.sqrt(np.mean(np.square(errs))))
    out["cur_rms"] = float(np.sqrt(np.mean(np.square(curs))))
    pitch = math.degrees(math.asin(max(-1, min(1, res["gb"][0]))))
    real_pitch = math.degrees(math.asin(logged_gb[0]))
    print(f"   {pose:5s} {str(list(case.keys()) or 'chain'):34s} trunk sim {pitch:+6.1f} deg (robot IMU {real_pitch:+6.1f}, IMU untrimmed {real_pitch + 4:+6.1f})  height {res['z'] * 1000:6.1f}  servo err rms {out['err_rms']:.3f} rad  current diff rms {out['cur_rms']:.0f} mA  fell {res['gb'][2] > -0.3}")
    print("         pos-goal sim/real rad: " + "  ".join(txt))
    return out


def main():
    global ANKLE_SIGN
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-manifest", action="store_true")
    ap.add_argument("--settle", action="store_true", help="hold the logged goals open loop. The model falls or folds: on the robot the policy keeps correcting, so this is no test of the offsets")
    args = ap.parse_args()
    if args.build_manifest:
        build_manifest()
        return
    results = {}
    for mlabel, manifest in (("charger 2026-11-01", MANIFEST), ("asbuilt default", None)):
        m, d, c, names, bam = load(manifest)
        print(f"\n=== mass model {mlabel}: total {m.body_subtreemass[m.body('trunk_base').id] * 1000:.1f} g, neck subtree {m.body_subtreemass[m.body('neck').id] * 1000:.1f} g, kt {float(bam.kt.value):.3f} Nm/A, rail {VOLT} V")
        ANKLE_SIGN, base, best = probe_ankle_sign(m, d, names)
        print("ankle pattern forward:", ANKLE_SIGN, "trunk change for 0.1 rad", round(best[0], 2), "deg")
        rows = static_table(m, d, names)
        results[mlabel] = {f"{k[0]}|{k[1]}": v for k, v in rows.items()}
        if not args.settle:
            continue
        print("settled on the robot's real servo goals:")
        for pose in ("stand", "bend"):
            for label, case in CASES.items():
                case = case.get(pose, case)
                m, d, c, names, bam = load(manifest)
                res = settle(m, d, c, names, bam, pose, case)
                results[mlabel][f"settle|{pose}|{label}"] = compare(res, pose, case)
        kt = float(bam.kt.value)
        print("real head joints (mA to Nm with kt): " + "; ".join(f"{p} neck {REAL[p]['j']['neck_pitch']['cur'] * kt / 1000:+.3f} head {REAL[p]['j']['head_pitch']['cur'] * kt / 1000:+.3f} Nm" for p in ("stand", "bend")))
    json.dump(results, open(os.path.join(HERE, "sim_static.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
