"""The real camera pose in the bow, measured, not modelled (Shawn 2026-10-30: 既然这个模型说得不准，那就以实际的为准).

For every held bow pose with legible ruler ticks (bend_ticks.json), fit where the camera really is: a height shift
(dz, foot frame) and a pitch turn of the chain's camera pose, by least squares on the tick pixels.
No chain parameter is blamed; the table of (neck_pitch, head_pitch) -> (dz, dpitch) is the correction duck_kin
applies between the standing fit (zero correction) and the bow. Held-out check: fit on half the frames of a pose,
project the other half's ticks to the floor, report the x error.

    python3 empirical_pose.py            writes bow_correction.json and prints the table
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, MAC)
import cam_calib  # noqa: E402
import duck_kin  # noqa: E402

W, H = 640, 360
Z_TICK = 0.0016   # the ruler's board top
EDGE_Y = {"sweep1": -0.0093, "sweep2": -0.0093 - 0.0056, "sweep3": -0.0093 + 0.0028}   # cm scale edge, foot frame y
#          (sweep1 measured with the far fit; sweeps 2-3 from bendfit.py's fitted RULER_Y, +-0.6 mm)


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def corrected(pos, R, d):
    """Camera pose with the correction d = (dz, dpitch_rad): height shift in the foot frame, pitch about image-left.
    (A forward shift is not separable from these on ticks that lie along one line; the scale finding is a height.)"""
    return pos + np.array([0.0, 0.0, d[0]]), R @ ry(d[1])


def project(kin, pos, R, X):
    return kin.K.project(R.T @ (np.asarray(X) - pos))


def floor_x(kin, pos, R, u, v):
    g = kin.pixel_to_ground_pose(u, v, pos, R, W, H, z=Z_TICK)
    return None if g is None else float(g[0])


DZ_ONLY = "--dz-only" in sys.argv


def fit_group(kin, obs, d0=(0.0, 0.0), iters=40):
    """Damped Gauss-Newton on (dz, dpitch) over all ticks of the group."""
    poses = [kin.camera_pose(o["q"], o["gb"]) for o in obs]
    d = np.array(d0, float)

    def resid(d):
        r = []
        for o, (pos, R) in zip(obs, poses):
            p2, R2 = corrected(pos, R, d)
            uv = project(kin, p2, R2, (o["x"], o["y"], Z_TICK))
            r.extend([0.0, 0.0] if uv is None else [uv[0] - o["u"], uv[1] - o["v"]])
        return np.array(r)

    lam = 1e-3
    for _ in range(iters):
        r0 = resid(d)
        J = np.zeros((r0.size, 2))
        for i, eps in enumerate((1e-4, 1e-4)):
            dp = d.copy()
            dp[i] += eps
            J[:, i] = (resid(dp) - r0) / eps
        A = J.T @ J
        step = np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), -J.T @ r0)
        step = np.clip(step, [-0.01, -0.05], [0.01, 0.05])   # at most 1 cm / 3 deg per step
        if DZ_ONLY:
            step[1] = 0.0
        if (resid(d + step) ** 2).sum() < (r0 ** 2).sum():
            d, lam = d + step, max(lam / 3, 1e-6)
        else:
            lam *= 10
        if np.abs(step).max() < 1e-7:
            break
    r = resid(d)
    cov = np.linalg.pinv(J.T @ J) * (r @ r / max(1, r.size - 2))
    return d, r, np.sqrt(np.diag(cov)), poses


def x_errors(kin, obs, poses, d):
    out = []
    for o, (pos, R) in zip(obs, poses):
        p2, R2 = corrected(pos, R, d)
        fx = floor_x(kin, p2, R2, o["u"], o["v"])
        out.append(None if fx is None else (fx - o["x"]) * 1000)
    return out


def main():
    kin = duck_kin.DuckKin()
    t = json.load(open(os.path.join(HERE, "bend_ticks.json")))
    obs = [o for o in t["obs"] if o.get("cm") is not None]
    for o in obs:
        o["x"] = cam_calib.toe_x(kin, o["q"], o["gb"]) + o["cm"] / 100.0
        o["y"] = EDGE_Y[o["sweep"]]
    groups = {}
    for o in obs:
        key = (o["sweep"], round(o["q"]["neck_pitch"], 1), round(o["q"]["head_pitch"], 1))
        groups.setdefault(key, []).append(o)
    table = []
    for key in sorted(groups):
        g = groups[key]
        frames = sorted({o["frame"] for o in g})
        d, r, sd, poses = fit_group(kin, g)
        before = x_errors(kin, g, poses, (0.0, 0.0))
        after = x_errors(kin, g, poses, d)
        # held-out: fit on the even frames, test on the odd ones (each frame has 2-3 ticks)
        ho = None
        if len(frames) >= 2:
            fit_set = [o for o in g if frames.index(o["frame"]) % 2 == 0]
            test_set = [o for o in g if frames.index(o["frame"]) % 2 == 1]
            dh, _, _, _ = fit_group(kin, fit_set)
            tp = [kin.camera_pose(o["q"], o["gb"]) for o in test_set]
            ho = x_errors(kin, test_set, tp, dh)
        neck = float(np.mean([o["q"]["neck_pitch"] for o in g]))
        head = float(np.mean([o["q"]["head_pitch"] for o in g]))
        row = dict(sweep=key[0], neck_pitch=round(neck, 4), head_pitch=round(head, 4), frames=len(frames), ticks=len(g),
                   cm=sorted({o["cm"] for o in g}), dz_mm=round(d[0] * 1000, 2), dpitch_deg=round(math.degrees(d[1]), 3),
                   sd=dict(dz_mm=round(sd[0] * 1000, 2), dpitch_deg=round(math.degrees(sd[1]), 3)),
                   px_rms=round(float(np.sqrt(np.mean(r ** 2))), 2),
                   x_err_before_mm=[round(e, 1) for e in before], x_err_after_mm=[round(e, 1) for e in after],
                   x_err_heldout_mm=None if ho is None else [round(e, 1) for e in ho])
        table.append(row)
        print(f"{key[0]} neck {neck:+.3f} head {head:+.3f} ({len(frames)} frames, ticks {row['cm']}): "
              f"dz {row['dz_mm']:+.1f} mm pitch {row['dpitch_deg']:+.2f} deg "
              f"(sd {row['sd']['dz_mm']} mm, {row['sd']['dpitch_deg']} deg) px rms {row['px_rms']}")
        print(f"   x err before {np.round(np.abs(before).max(), 1)} max -> after {np.round(np.abs(after).max(), 1)} max"
              + ("" if ho is None else f", held-out frames {np.round(np.abs(ho).max(), 1)} max"))
    out = dict(note=__doc__.strip().split("\n")[0], z_tick_m=Z_TICK, edge_y=EDGE_Y, groups=table)
    name = "bow_correction_dz.json" if DZ_ONLY else "bow_correction.json"
    out["mode"] = "height only (dpitch fixed 0)" if DZ_ONLY else "height and pitch"
    json.dump(out, open(os.path.join(HERE, name), "w"), indent=1)
    print("wrote", name)


if __name__ == "__main__":
    main()
