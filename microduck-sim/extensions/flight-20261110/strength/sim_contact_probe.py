"""Where do the simulated impact peaks enter the duck: through the feet or through a nacelle?

Runs sim/flight.py unchanged (imported, its argparse main reused) and wraps mujoco.mj_step to log, every physics step,
the normal contact force between floor/table and (a) the nacelle collision boxes, (b) the feet, (c) any other duck geom,
plus the nacelle-box contact point velocity at first touch. One JSON per case in strength/out/sim_probe/.

Run on the Mac mini (the flight sim venv there):
    zsh sim/mini.sh push && rsync strength/ ... ; $PY strength/sim_contact_probe.py <case> [flight.py args...]
The cases used in strength/README.md are listed in CASES below (they reproduce sim/out/cut/cut03.json and the batch
rows with the largest trunk peaks).
"""
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

H = Path(__file__).resolve().parent
SIM = H.parent / "sim"
sys.path.insert(0, str(SIM))
import flight  # noqa: E402

FIX = ["--com-est", "true", "--ground-pitch", "level", "--takeoff-twr", "1.6", "--takeoff-ramp", "0.1"]
CASES = {
    "cut03": ["--scenario", "cut", "--cut-alt", "0.3"],
    "ARE_thrust80_table_down_s2": ["--scenario", "table_down", "--seed", "2", *FIX, "--fan", "areswei", "--thrust", "0.8"],
    "comx+10_table_up_s2_air": ["--scenario", "table_up", "--seed", "2", *FIX, "--start-air", "0.3", "--air-level",
                                "--mass-variant", "comx+10"],
    "hover_nominal": ["--scenario", "hover", "--spool-down", "0.6", "--flare-h", "0"],
}

REC = dict(t=[], nac=[], feet=[], other=[], first_nac=None)
_orig_step = mujoco.mj_step
_ids = {}
_f6 = np.zeros(6)


def _step(m, d):
    _orig_step(m, d)
    if not _ids:
        _ids["nac"] = {m.geom("nacelle_box_L").id, m.geom("nacelle_box_R").id}
        _ids["feet"] = {m.geom("left_foot_collision").id, m.geom("right_foot_collision").id}
        _ids["env"] = {m.geom("floor").id, m.geom("table").id}
    fn = dict(nac=0.0, feet=0.0, other=0.0)
    for j in range(d.ncon):
        c = d.contact[j]
        g1, g2 = c.geom1, c.geom2
        if g1 in _ids["env"]:
            o = g2
        elif g2 in _ids["env"]:
            o = g1
        else:
            continue
        mujoco.mj_contactForce(m, d, j, _f6)
        k = "nac" if o in _ids["nac"] else "feet" if o in _ids["feet"] else "other"
        fn[k] += abs(float(_f6[0]))
        if k == "nac" and REC["first_nac"] is None:
            v6 = np.zeros(6)
            mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_GEOM, o, v6, 0)
            REC["first_nac"] = dict(t=float(d.time), geom=m.geom(o).name, pos=c.pos.tolist(),
                                    box_centre_vel_mps=v6[3:].tolist(), box_ang_vel=v6[:3].tolist())
    REC["t"].append(float(d.time))
    for k in fn:
        REC[k].append(fn[k])


mujoco.mj_step = _step


def main():
    name = sys.argv[1]
    args = CASES[name] + sys.argv[2:]
    out = H / "out" / "sim_probe"
    out.mkdir(parents=True, exist_ok=True)
    sys.argv = ["flight.py", *args, "--out", str(out / f"{name}_row.json")]
    flight.main()
    t = np.array(REC["t"])
    res = dict(case=name, args=args, first_nacelle_contact=REC["first_nac"])
    dt = float(np.median(np.diff(t))) if len(t) > 2 else None
    w = max(1, int(round(0.010 / dt))) if dt else 1           # 10 ms mean, as flight.py's trunk peak
    for k in ("nac", "feet", "other"):
        f = np.array(REC[k])
        fm = np.convolve(f, np.ones(w) / w, mode="same") if len(f) else f
        i = int(np.argmax(f)) if len(f) else 0
        res[k] = dict(peak_N=round(float(f.max()), 1) if len(f) else 0.0, peak_t=round(float(t[i]), 4) if len(f) else None,
                      peak_10ms_mean_N=round(float(fm.max()), 1) if len(f) else 0.0,
                      impulse_Ns=round(float(np.trapezoid(f, t)), 3) if len(f) else 0.0)
    row = json.loads((out / f"{name}_row.json").read_text())
    res["row"] = {k: row.get(k) for k in ("mass_g", "trunk_acc_peak_g", "fell_at", "nacelle_hit_at", "landing_vz_mps", "max_tilt_deg")}
    res["dt_s"] = dt
    (out / f"{name}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
