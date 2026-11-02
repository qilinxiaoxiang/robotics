#!/usr/bin/env python3
"""Screwdriver and finger access for every screw of a build, at the moment it is driven. Exit 1 on any blocked screw
(with --strict, also on any awkward screw).

Usage: access_check.py SCREWS.json [--json OUT.json] [--strict]
       access_check.py examples/access-selftest/selftest.screws.json      (self-test: exit 0 when every verdict matches)

The rules are in PRINT-FIT.md, section "Access". SCREWS.json:
{
  "mesh_dir": "<dir>",                       # relative to the spec file or absolute
  "meshes": {"<key>": "<path>.stl", ...},    # every solid in the assembly frame, relative to mesh_dir
  "screws": [
    {"id": "...", "step": "...", "spec": "M3 x 10 button", "where": "...",
     "seat": [x, y, z],                      # centre of the head's underside when seated
     "axis": [x, y, z],                      # head -> tip; the tool comes in from -axis
     "head_d": 5.7, "head_h": 1.65, "length": 10, "through_mm": 3.0,   # through_mm: clearance-hole length before the pilot
     "drive": "hex" | "phillips",           # tilt a straight bit tolerates in the head: hex 10 deg, Phillips 5 deg
     "present": ["<key>", ...],              # rigid solids in place when this screw is driven (they decide)
     "movable": ["<key>", ...],              # in place but can be moved or bent out of the way (reported, not deciding)
     "table_z": 0.0 | null}                  # the assembly sits on a table at this Z (nothing passes below); null = bench part held freely
  ]
}
For each screw the checker samples the present solids (about 4 points per mm^2) and the table plane (1 mm grid) and
reports, measured from the seated head top along the approach direction:
  r_free_60      largest radius free of every solid over 0.5-60 mm (the precision-driver corridor)
  h_r4           how far a 4 mm radius cylinder stays free (capped at 200 mm)
  r_handle       free radius over 60-120 mm (where a precision driver's handle and fingers are)
  finger_r       free radius around the head where fingers hold it to start (head top lifted by length - through_mm, +10 mm)
  head_room      radial room around the seated head (negative = the head itself hits something)
  tools          which tools reach straight along the axis (TOOLS below), with the limiting solid and shortfall
  t1_tilt_deg    smallest tilt of T1 about the head top (any azimuth, 2.5 deg steps to 45) that clears everything
  verdict        OK: T1 straight, r_free_60 >= 4, r_handle >= 15, finger_r >= 8, head fits
                 awkward: some tool reaches straight, or T1 within the drive's tilt limit, but a rule above fails
                 blocked: no tool reaches straight and T1 needs more tilt than the drive takes, or the head does not fit
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

# tool name: list of (t0, t1, radius) along the axis from the head top, mm. L-keys: (shaft, arm_at, arm_len).
TOOLS = {
    "T1 2 mm hex precision driver (3 x 60 shaft, 20 x 60 handle)": [(0, 60, 1.5), (60, 120, 10.0)],
    "T2 precision screwdriver (3 x 100 shaft, 10 x 90 handle)": [(0, 100, 1.5), (100, 190, 5.0)],
    "T3 PH0 precision driver (3 x 50 shaft, 10 x 90 handle)": [(0, 50, 1.5), (50, 140, 5.0)],
    "T5 stubby / ratchet driver (3 x 25 shaft, 25 x 40 handle)": [(0, 25, 1.5), (25, 65, 12.5)],
}
LKEYS = {   # short arm in the socket, long arm swings at its end; and the reverse
    "T4a L-key short arm in (2 x 50, 100 lever)": (1.0, 50.0, 100.0),
    "T4b L-key long arm in (2 x 100, 50 lever)": (1.0, 100.0, 50.0),
}
T1 = next(iter(TOOLS))
RULE = dict(r_shaft=4.0, shaft_zone=60.0, r_handle=15.0, handle_zone=(60.0, 120.0), finger_r=8.0, finger_h=10.0,
            skip=0.5, contact=0.25, tilt_max={"hex": 10.0, "phillips": 5.0}, lkey_sector_deg=60.0)
_cache = {}


def cloud(path):
    if path not in _cache:
        m = trimesh.load(str(path), force="mesh")
        n = int(min(600000, max(5000, m.area * 4)))
        _cache[path] = np.vstack([m.sample(n, seed=11), m.vertices]).astype(np.float64)
    return _cache[path]


def table_pts(top, z, reach=215.0, step=1.0):
    g = np.arange(-reach, reach + step / 2, step)
    X, Y = np.meshgrid(top[0] + g, top[1] + g)
    keep = (X - top[0]) ** 2 + (Y - top[1]) ** 2 <= reach ** 2
    return np.column_stack([X[keep], Y[keep], np.full(keep.sum(), float(z))])


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def tp(P, top, u):
    rel = P - top
    t = rel @ u
    perp = np.linalg.norm(rel - np.outer(t, u), axis=1)
    return t, perp


def min_perp(t, perp, lo, hi):
    s = (t > lo) & (t <= hi)
    return float(perp[s].min()) if s.any() else math.inf


def tool_clear(t, perp, segs, margin):
    """Smallest (perp - radius) over the tool's segments; > margin means it fits."""
    worst, where = math.inf, None
    for t0, t1, r in segs:
        s = (t > max(t0, 0.05)) & (t <= t1)
        if s.any():
            i = np.argmin(perp[s] - r)
            c = float((perp[s] - r)[i])
            if c < worst:
                worst, where = c, np.flatnonzero(s)[i]
    return worst, where


def lkey_ok(top, u, P, shaft_r, arm_at, arm_len, margin, sector):
    t, perp = tp(P, top, u)
    if tool_clear(t, perp, [(0, arm_at, shaft_r)], margin)[0] <= margin:
        return False, 0.0
    s = (np.abs(t - arm_at) <= shaft_r + margin) & (perp <= arm_len + shaft_r)
    if not s.any():
        return True, 360.0
    a = np.cross(u, [1.0, 0, 0] if abs(u[0]) < 0.9 else [0, 1.0, 0]); a /= np.linalg.norm(a)
    b = np.cross(u, a)
    rel = P[s] - top
    phi = np.degrees(np.arctan2(rel @ b, rel @ a)) % 360.0
    half = np.degrees(np.arcsin(np.clip((shaft_r + margin) / np.maximum(perp[s], 1e-6), 0, 1)))
    blocked = np.zeros(360, bool)
    for p, h in zip(phi, half):
        lo, hi = int(math.floor(p - h)), int(math.ceil(p + h))
        blocked[np.arange(lo, hi + 1) % 360] = True
    if not blocked.any():
        return True, 360.0
    free = np.concatenate([~blocked, ~blocked])
    best = run = 0
    for f in free:
        run = run + 1 if f else 0
        best = max(best, run)
    best = min(best, 360)
    return best >= sector, float(best)


def tilt_dirs(u, theta):
    a = np.cross(u, [1.0, 0, 0] if abs(u[0]) < 0.9 else [0, 1.0, 0]); a /= np.linalg.norm(a)
    b = np.cross(u, a)
    th = math.radians(theta)
    for az in range(0, 360, 10):
        p = math.radians(az)
        yield az, unit(math.cos(th) * u + math.sin(th) * (math.cos(p) * a + math.sin(p) * b))


def check(sc, root, meshes):
    seat, ax = np.asarray(sc["seat"], float), unit(sc["axis"])
    u = -ax                                             # approach direction (from the head outward)
    hh, hr = float(sc["head_h"]), float(sc["head_d"]) / 2
    top = seat + u * hh
    names, clouds = [], []
    for k in sc["present"]:
        names.append(k); clouds.append(cloud(root / meshes[k]))
    if sc.get("table_z") is not None:
        names.append("table"); clouds.append(table_pts(top, sc["table_z"]))
    lab = np.concatenate([np.full(len(c), i) for i, c in enumerate(clouds)])
    P = np.vstack(clouds)
    near = np.linalg.norm(P - top, axis=1) <= 215.0
    P, lab = P[near], lab[near]
    t, perp = tp(P, top, u)
    m = RULE["contact"]

    def limiting(lo, hi):
        s = (t > lo) & (t <= hi)
        if not s.any():
            return None
        i = np.flatnonzero(s)[np.argmin(perp[s])]
        return dict(part=names[lab[i]], r=round(float(perp[i]), 2), at_t=round(float(t[i]), 1),
                    point=np.round(P[i], 1).tolist())

    r60 = min_perp(t, perp, RULE["skip"], RULE["shaft_zone"])
    rh = min_perp(t, perp, *RULE["handle_zone"])
    s4 = (perp < RULE["r_shaft"]) & (t > RULE["skip"])
    h4 = float(t[s4].min()) if s4.any() else 200.0
    lift = max(0.0, float(sc["length"]) - float(sc.get("through_mm", 0.0)))
    f_lo, f_hi = max(0.3, lift - hh), lift + RULE["finger_h"]
    fr = min_perp(t, perp, f_lo, f_hi)
    sh = (t > -hh + 0.15) & (t < -0.05)
    head_room = float(perp[sh].min() - hr) if sh.any() else math.inf

    tools = {}
    for name, segs in TOOLS.items():
        c, i = tool_clear(t, perp, segs, m)
        tools[name] = dict(ok=bool(c > m), clearance=None if math.isinf(c) else round(c, 2),
                           limit=None if i is None else dict(part=names[lab[i]], at_t=round(float(t[i]), 1),
                                                             point=np.round(P[i], 1).tolist()))
    for name, (r, at, ln) in LKEYS.items():
        ok, sec = lkey_ok(top, u, P, r, at, ln, m, RULE["lkey_sector_deg"])
        tools[name] = dict(ok=bool(ok), free_swing_deg=sec)

    tilt, tilt_az = None, None
    if tools[T1]["ok"]:
        tilt = 0.0
    else:
        for th in np.arange(2.5, 45.01, 2.5):
            for az, d in tilt_dirs(u, th):
                tt, pp = tp(P, top, d)
                if tool_clear(tt, pp, TOOLS[T1], m)[0] > m:
                    tilt, tilt_az = float(th), az
                    break
            if tilt is not None:
                break

    mov = {}
    for k in sc.get("movable", []):
        c = cloud(root / meshes[k])
        c = c[np.linalg.norm(c - top, axis=1) <= 215.0]
        if len(c):
            tt, pp = tp(c, top, u)
            mov[k] = dict(r_free_60=round(min_perp(tt, pp, RULE["skip"], RULE["shaft_zone"]), 2),
                          t1_clearance=round(tool_clear(tt, pp, TOOLS[T1], m)[0], 2))

    straight = [k.split()[0] for k, v in tools.items() if v["ok"]]
    fails = []
    if r60 < RULE["r_shaft"]:
        fails.append(f"free radius {r60:.1f} < {RULE['r_shaft']} within 60 mm")
    if rh < RULE["r_handle"]:
        fails.append(f"free radius {rh:.1f} < {RULE['r_handle']} at the handle (60-120 mm)")
    if fr < RULE["finger_r"]:
        fails.append("needs the screw started on the driver tip")
    if not tools[T1]["ok"]:
        fails.append(f"T1 needs {tilt} deg tilt" if tilt is not None else "T1 cannot reach at any tilt to 45 deg")
    if head_room < -0.05:
        verdict = "blocked"
        fails.append(f"head hits a solid ({head_room:.2f} mm)")
    elif not fails:
        verdict = "OK"
    elif straight or (tilt is not None and tilt <= RULE["tilt_max"][sc.get("drive", "phillips")]):
        verdict = "awkward"
    else:
        verdict = "blocked"
    fin = lambda v: None if math.isinf(v) else round(v, 2)
    return dict(id=sc["id"], step=sc["step"], spec=sc["spec"], where=sc.get("where", ""),
                head_top=np.round(top, 2).tolist(), approach=np.round(u, 3).tolist(),
                r_free_60=fin(r60), h_r4=round(h4, 1), r_handle=fin(rh), finger_r=fin(fr),
                finger_start=bool(fr >= RULE["finger_r"]), head_room=fin(head_room),
                limit_60=limiting(RULE["skip"], RULE["shaft_zone"]), limit_r4=limiting(RULE["skip"], h4 + 0.01) if h4 < 200 else None,
                limit_finger=limiting(f_lo, f_hi), limit_handle=limiting(*RULE["handle_zone"]),
                tools=tools, straight=straight, t1_tilt_deg=tilt, t1_tilt_azimuth=tilt_az,
                movable=mov, fails=fails, verdict=verdict, note=sc.get("note", ""))


def line(r):
    return (f"[{r['verdict']}] {r['step']} | {r['id']} | {r['spec']} | free r={r['r_free_60']} over 60 mm, "
            f"4 mm cyl {r['h_r4']} mm | straight: {','.join(r['straight']) or 'none'} | T1 tilt {r['t1_tilt_deg']} | "
            f"finger {'yes' if r['finger_start'] else 'no'} ({r['finger_r']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--json")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    spec_path = Path(a.spec).resolve()
    spec = json.loads(spec_path.read_text())
    root = Path(spec["mesh_dir"])
    root = root if root.is_absolute() else spec_path.parent / root
    res = [check(sc, root, spec["meshes"]) for sc in spec["screws"]]
    for r in res:
        print(line(r))
    counts = {v: sum(r["verdict"] == v for r in res) for v in ("OK", "awkward", "blocked")}
    print(json.dumps(counts))
    if a.json:
        Path(a.json).write_text(json.dumps(dict(rule=RULE, tools={**TOOLS, **LKEYS}, counts=counts, screws=res), indent=1))
    if "expect" in spec:      # self-test: every listed screw must get its expected verdict
        miss = [f"{r['id']}: {r['verdict']} != {spec['expect'][r['id']]}" for r in res
                if r["id"] in spec["expect"] and r["verdict"] != spec["expect"][r["id"]]]
        print("SELFTEST " + ("PASS" if not miss else "FAIL " + "; ".join(miss)))
        sys.exit(1 if miss else 0)
    bad = counts["blocked"] + (counts["awkward"] if a.strict else 0)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
