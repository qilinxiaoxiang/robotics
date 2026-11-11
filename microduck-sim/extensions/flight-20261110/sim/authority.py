"""Control authority of the fan layout about the with-pack COM, from the geometry in flight.py and out/mass_report.json.

For each thrust level (fraction of the vendor 950 g per fan, at the nominal 16.2 V reference):
  - pitch/roll/yaw moment of equal fan thrust at hover (should be ~0: the layout is balanced if it is),
  - largest moment the mixer can add about each axis while keeping the hover collective (each fan between 3 % and 100 %),
  - demand: weight x 10 mm COM offset (the perturbation set's largest offset) for pitch and roll,
    and for yaw the thrust set needed with one fan 15 % weak (does an exact solution stay inside the limits?),
  - margin = authority / demand, and the fan fore-aft spacing that would give 2x pitch margin.
Writes out/authority.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

import flight as F

FAN = sys.argv[1] if len(sys.argv) > 1 else "areswei"   # vendor point (fan change 2026-11-10: ARESWEI HDS001)
F.set_fan(FAN)
H = Path(__file__).resolve().parent
full_rep = json.loads((H / "out" / "mass_report.json").read_text())
rep = full_rep["duck_with_pack"]
m = rep["mass_g"] / 1000
com = np.array(rep["com_trunk_mm"]) / 1000
W = m * F.G
DRAG = 0.3 * F.ETA_MOTOR * F.P_REF / F.W_REF / F.T_REF   # body yaw torque per N of thrust (resid 0.3)


def bmat(fans, c):
    B = np.zeros((4, 4))
    for i, f in enumerate(fans):
        r = f["p"] - c
        Mm = np.cross(r, f["a"]) + (-f["spin"]) * DRAG * f["a"]
        B[:, i] = [f["a"][2], *Mm]
    return B


def fans_with(dx_front=0.0, dx_rear=0.0, dx_all=0.0):
    out = []
    for f in F.FANS:
        g = dict(f); p = f["p"].copy()
        p[0] += dx_all + (dx_front if "F" in f["name"].split()[1] else dx_rear)
        g["p"] = p; out.append(g)
    return out


def authority(fans, thrust, c=com):
    B = bmat(fans, c)
    tmax = F.T_REF * thrust; tmin = 0.03 * tmax
    base = np.linalg.solve(B, [W, 0, 0, 0])
    res = dict(hover_thrust_per_fan_n=[round(float(x), 3) for x in base],
               equal_thrust_moment_nm=[round(float(x), 4) for x in (B @ np.full(4, W / B[0].sum()))[1:]])
    for k, ax in ((1, "roll"), (2, "pitch"), (3, "yaw")):
        e = np.zeros(4); e[k] = 1.0
        d = np.linalg.solve(B, e)                        # thrust change per N m about this axis, collective unchanged
        up = min((tmax - base[i]) / d[i] if d[i] > 0 else (base[i] - tmin) / -d[i] for i in range(4) if abs(d[i]) > 1e-12)
        res[f"{ax}_authority_nm"] = round(float(up), 3)
    dem = W * 0.010
    res["pitch_roll_demand_nm"] = round(dem, 3)
    res["pitch_margin"] = round(res["pitch_authority_nm"] / dem, 2)
    res["roll_margin"] = round(res["roll_authority_nm"] / dem, 2)
    weak = []
    for i in range(4):
        s = np.ones(4); s[i] = 0.85
        Bt = B * s                                       # fan i gives 85 % of its commanded thrust
        T = np.linalg.solve(Bt, [W, 0, 0, 0])
        weak.append(dict(fan=F.FANS[i]["name"], cmd_thrust_n=[round(float(x), 2) for x in T],
                         peak_frac=round(float(T.max() / tmax), 3), feasible=bool(T.max() <= tmax and T.min() >= tmin)))
    res["one_fan_15pct_weak"] = weak
    return res


out = dict(fan=FAN, com_mm=rep["com_trunk_mm"], mass_g=rep["mass_g"], weight_n=round(W, 3),
           fan_x_mm={k: v * 1000 for k, v in F.FAN_X.items()}, cant_deg=6.0, fan_y_mm=F.FAN_Y * 1000,
           pitch_arm_per_fan_mm=round(float(abs(bmat(F.FANS, com)[2, 0])) * 1000, 1),
           roll_arm_per_fan_mm=round(float(abs(bmat(F.FANS, com)[1, 0])) * 1000, 1),
           yaw_arm_per_fan_mm=round(float(abs(bmat(F.FANS, com)[3, 0])) * 1000, 1),
           now={str(t): authority(F.FANS, t) for t in (1.0, 0.8)})
# fore-aft spacing for a 2x pitch margin: spread front and rear symmetrically about their mean
spread = {}
for t in (1.0, 0.8):
    for s in np.arange(0, 0.081, 0.002):
        a = authority(fans_with(dx_front=s / 2, dx_rear=-s / 2), t)
        if a["pitch_margin"] >= 2.0:
            spread[str(t)] = dict(extra_spacing_mm=round(s * 1000, 1), fan_x_front_mm=round((F.FAN_X["front"] + s / 2) * 1000, 1),
                                  fan_x_rear_mm=round((F.FAN_X["rear"] - s / 2) * 1000, 1), pitch_margin=a["pitch_margin"])
            break
out["spacing_for_2x_pitch_margin"] = spread
# battery (both packs + straps) shift in x for a 2x pitch margin, fans where they are: the whole COM moves by
# dx * m_batt / m_total (mass and inertia otherwise unchanged)
parts = json.loads((H / "out" / "pack_parts.json").read_text())["parts"]
m_batt = sum(p["mass_kg"] for p in parts if p["id"].startswith(("battery-", "strap-")))
bshift = {}
for t in (1.0, 0.8):
    best = None
    for dx in sorted(np.arange(-0.040, 0.0401, 0.0005), key=abs):
        c = com + np.array([dx * m_batt / m, 0, 0])
        if authority(F.FANS, t, c)["pitch_margin"] >= 2.0:
            best = dx; break
    if best is not None:
        c = com + np.array([best * m_batt / m, 0, 0])
        bshift[str(t)] = dict(battery_dx_mm=round(best * 1000, 1), com_x_mm=round(c[0] * 1000, 2),
                              pitch_margin=authority(F.FANS, t, c)["pitch_margin"])
out["battery_x_shift_for_2x_pitch_margin"] = dict(battery_mass_g=round(m_batt * 1000, 1), by_thrust=bshift)
(H / "out" / "authority.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
