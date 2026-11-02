#!/usr/bin/env python3
"""Check a part set's declared mating fits against print_fit.py. Exit 1 on any failure.

Usage: fit_check.py FITS.json [--json OUT.json]

FITS.json (one file per release, next to the part scripts; the part scripts write it or it is kept by hand):
{
  "printer": "H2S" | "X1C" | "Elegoo-CC",                    # adds print_fit.PRINTER_OFFSET to pilots and clearances
  "poses": {"<part>": [[[ax, ay, az], deg], ...]},          # print_rot exactly as passed to the STL export
  "fits": [
    {"id": "...", "type": "pilot", "part": "<part>", "screw": "M2", "kind": "any",
     "d": 1.85, "axis": [x, y, z], "teardrop": null | [ux, uy, uz], "at_bed": false, "chamfer": 0.0, "engagement": 4.4,
     "depth": 7.0 | "through", "clamped": 1.6},
    {"id": "...", "type": "clear", "part": "<part>", "screw": "M3", "d": 3.4, "axis": [...], "teardrop": null, ...},
    {"id": "...", "type": "pair", "fit_class": "locating|sliding|loose|press|crush_rib",
     "female": {"part": "<part>" | null, "d": 6.1, "axis": [...], "teardrop": null, "at_bed": true, "chamfer": 0.0},
     "male":   {"part": "<part>" | null, "d": 6.0, "axis": [...], "teardrop": null, "at_bed": false, "chamfer": 0.0}}
  ]
}
Axes and teardrop vectors are in the part frame; the checker rotates them into the print pose from "poses", so a
wrong print pose cannot hide behind a hand-written "vertical". "part": null marks a bought part (no print adders).
"d" is a diameter, or a width across the fit for slots, tongues and grooves. "kind" defaults to "any" (a pilot takes
machine and thread-forming screws of its size); "tap" checks as-built evidence against the TAP-only table and warns.
"depth" (blind pilot depth below the clamped parts) and "clamped" (thickness the screw passes before the pilot) check
that the longest common length fits.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import print_fit as F  # noqa: E402


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _unit(v):
    n = _dot(v, v) ** 0.5
    return [c / n for c in v]


def teardrop_errors(feat, poses, male):
    """A teardrop (tip vector `teardrop`) must sit on a horizontal axis, perpendicular to it, pointing +Z in print for a
    hole and -Z for a male cylinder."""
    up = feat.get("teardrop")
    part = feat.get("part")
    if up is None or part is None:
        return []
    rot = poses[part]
    ax = _unit(F.to_print(feat["axis"], rot))
    tip = _unit(F.to_print(up, rot))
    errs = []
    if F.tilt_deg(ax) <= F.VERTICAL_LIMIT_DEG:
        errs.append("teardrop on an axis that is vertical in the print pose")
    if abs(_dot(ax, tip)) > 0.05:
        errs.append("teardrop tip not perpendicular to the hole axis")
    want = -1.0 if male else 1.0
    ang = F.tilt_deg(tip) if tip[2] * want > 0 else 180.0 - F.tilt_deg(tip)
    if ang > F.TEARDROP_UP_TOL_DEG:
        errs.append(f"teardrop tip points {ang:.0f} deg from {'-Z' if male else '+Z'} in the print pose")
    return errs


def orient(feat, poses):
    if feat.get("part") is None:
        return None
    return F.orientation(feat["axis"], poses[feat["part"]])


def bed_unchamfered(feat):
    return bool(feat.get("at_bed")) and float(feat.get("chamfer", 0.0)) < F.BED_CHAMFER - 1e-9


def check(fit, poses, printer=None):
    t = fit["type"]
    res = dict(id=fit["id"], type=t, fails=[], warns=[])
    if t in ("pilot", "clear"):
        o = orient(fit, poses)
        res["orientation"] = o
        res["fails"] += teardrop_errors(fit, poses, male=False)
        d = fit["d"]
        if t == "pilot":
            k = fit.get("kind", "any")
            if k in ("unknown", "machine"):
                k = "any"
            if k == "tap":
                res["warns"].append("checked against the TAP-only table: as-built evidence, not a design value")
            req = F.pilot(fit["screw"], o, k, printer)
            if bed_unchamfered(fit):
                req += 0.1
            res["required"] = round(req, 3)
            if d < req + F.PILOT_BAND[0] - 1e-9:
                res["fails"].append(f"pilot {d} under {req:.2f} ({fit['screw']} {k}, {o}{', first-layer mouth' if bed_unchamfered(fit) else ''})")
            elif d > req + F.PILOT_BAND[1] + 1e-9:
                res["fails"].append(f"pilot {d} over {req + F.PILOT_BAND[1]:.2f}: thread strips")
            dep = fit.get("depth")
            if dep is not None and dep != "through" and "clamped" in fit:
                need = F.pilot_depth(fit["screw"], fit["clamped"])
                if dep < need - 1e-9:
                    res["fails"].append(f"blind pilot {dep} mm deep, the longest common {fit['screw']} needs {need}")
            eng = fit.get("engagement")
            dia = float(fit["screw"][1:])
            if eng and eng > F.MAX_ENGAGEMENT_D[k] * dia:
                res["warns"].append(f"engagement {eng} mm over {F.MAX_ENGAGEMENT_D[k]:g} d: drive torque high")
        else:
            req = F.clear(fit["screw"], o, printer)
            res["required"] = req
            if d < req - 0.05 - 1e-9:
                res["fails"].append(f"clearance {d} under {req} ({fit['screw']}, {o})")
    elif t == "pair":
        fe, ma = fit["female"], fit["male"]
        res["fails"] += teardrop_errors(fe, poses, male=False) + teardrop_errors(ma, poses, male=True)
        gap = (fe["d"] - ma["d"]) / 2
        fo = orient(fe, poses)
        bed = any(f.get("part") is not None and bed_unchamfered(f) for f in (fe, ma))
        req = F.clearance(fit["fit_class"], fo or "vertical", at_bed=bed)
        res.update(gap_per_side=round(gap, 3), required=req, female_orientation=fo, first_layer=bed)
        if gap < req - 1e-9:
            why = [f"{fit['fit_class']} needs {req:+.2f}/side"]
            if fo == "horizontal":
                why.append("female horizontal")
            if bed:
                why.append("unchamfered first-layer edge")
            res["fails"].append(f"gap {gap:+.3f}/side; " + ", ".join(why))
    else:
        res["fails"].append(f"unknown fit type {t}")
    res["verdict"] = "FAIL" if res["fails"] else ("WARN" if res["warns"] else "OK")
    return res


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    spec = json.loads(Path(argv[1]).read_text())
    poses = {k: [(tuple(a), float(d)) for a, d in v] for k, v in spec["poses"].items()}
    printer = spec.get("printer")
    if printer:
        print(f"printer {printer}: pilot/clearance offset {F.PRINTER_OFFSET[printer]:+.2f} ({F.PRINTER_OFFSET_STATUS[printer]})")
    out = [check(f, poses, printer) for f in spec["fits"]]
    for r in out:
        detail = "; ".join(r["fails"] + r["warns"])
        print(f"{r['verdict']:4}  {r['id']:<34} {detail}")
    n_fail = sum(r["verdict"] == "FAIL" for r in out)
    print(f"{len(out)} fits, {n_fail} fail, {sum(r['verdict'] == 'WARN' for r in out)} warn")
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps(out, indent=1))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
