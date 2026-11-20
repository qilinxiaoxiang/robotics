"""Offset tolerance per variant from the grid results, and the sheet text. Tolerance on one axis = the widest run of
grid points around 0 (other axes 0) where every seed passes. Writes checks/results.json.

    python analyse.py            (MacBook, microduck-cad venv; reads checks/*.jsonl)
"""
import json, time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CK = HERE / "checks"
CHOSEN = "R1 short c3"          # drawn on the sheet: widest x/y windows of R1-R3 with sit/rise clearance >= 7 mm


def load(*files):
    rows = []
    for f in files:
        p = CK / f
        if p.exists():
            rows += [json.loads(l) for l in p.open() if l.strip()]
    return rows


def tolerance(rows, variant, axis):
    by = defaultdict(list)
    for r in rows:
        c = r["case"]
        if c["concept"] != variant or c.get("tag") or c.get("mu_rail", .35) != .35 or c.get("floor_mu", 1.0) != 1.0:
            continue
        o = c["off"]
        if any(o[k] for k in range(3) if k != axis):
            continue
        by[o[axis]].append(bool(r.get("pass_")) and "error" not in r)
    if 0 not in by:
        return None
    pts = sorted(by)
    ok = {v: all(by[v]) for v in pts}
    if not ok[0]:
        return dict(lo=None, hi=None, grid=pts, note="fails at 0", seeds=len(by[0]))
    i0 = pts.index(0); lo = hi = 0
    for v in pts[i0 + 1:]:
        if ok[v]: hi = v
        else: break
    for v in reversed(pts[:i0]):
        if ok[v]: lo = v
        else: break
    return dict(lo=lo, hi=hi, grid=pts, seeds=len(by[0]), first_fail_lo=next((v for v in reversed(pts[:i0]) if not ok[v]), None),
                first_fail_hi=next((v for v in pts[i0 + 1:] if not ok[v]), None))


def why(r):
    out = []
    for k in ("plus", "minus"):
        p = r["pads"][k]
        if p["x_margin"] < .5: out.append("x")
        if p["y_overlap_own"] < 1: out.append("y")
        if p["y_overlap_other"] > 0: out.append("short")
        if p["compression"] < 1: out.append("hung up")
    if r["fell_before_unsit"]: out.append("fell")
    if not r["rail_clear_ok"]: out.append("rail touches leg")
    return sorted(set(out))


def main():
    rows = load("axes2.jsonl", "rails3.jsonl", "check4.jsonl")
    variants = sorted({r["case"]["concept"] for r in rows})
    tol = {v: {ax: tolerance(rows, v, i) for i, ax in enumerate(("x_mm", "y_mm", "yaw_deg"))} for v in variants}
    fails = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if "error" in r or r.get("pass_"):
            continue
        for w in why(r):
            fails[r["case"]["concept"]][w] += 1
    params = next(r["case"]["params"] for r in rows if r["case"]["concept"] == CHOSEN)
    res = dict(made=time.strftime("%Y-%m-%d %H:%M"), chosen=CHOSEN, concept_params=params, tolerance=tol,
               fail_reasons={k: dict(v) for k, v in fails.items()},
               n_runs=len(rows), title="BatteryDock funnel concept (sim-tested, not CAD): side guide rails + rear lead-in + forward datum")
    for name in ("combo", "friction", "seeds"):
        sub = [r for r in rows if r["case"].get("tag") == name]
        if sub:
            res[name] = dict(n=len(sub), passed=sum(bool(r.get("pass_")) for r in sub),
                             fails=[dict(off=r["case"]["off"], seed=r["case"]["seed"], mu_rail=r["case"].get("mu_rail", .35),
                                         floor_mu=r["case"].get("floor_mu", 1.0), why=why(r)) for r in sub
                                    if not r.get("pass_") and "error" not in r])
    res["sheet_text"] = sheet_text(res)
    (CK / "results.json").write_text(json.dumps(res, indent=1))
    for v in variants:
        print(v, tol[v], dict(fails[v]))


def fmt(t, unit):
    if t is None: return "not run"
    if t.get("lo") is None: return "fails at 0"
    return f"{t['lo']:+g} .. {t['hi']:+g} {unit}"


def sheet_text(res):
    T = res["tolerance"]
    a1, d0, ch = T.get("A1", {}), T.get("datum", {}), T.get(res["chosen"], {})
    L = []
    L.append("PROBLEMS (Shawn 2026-11-20: \"导轨倒是可以 ... 看看能不能把它对准坐下去\") AND THE FEATURE THAT ANSWERS EACH")
    L.append("1  Robot sits down off to one side: a pad misses its leaf (leaves alone take about +-6 mm)  ->  F1 two side guide rails beside the")
    L.append("   backpack's lower tier: vertical guide face to z 12.5, 60 deg lead-in to z 24, 3 mm play per side, only beside the pads (x -77..-59)")
    L.append("2  Robot sits down too far forward or back: the 8.7 mm pad misses the leaf tip  ->  F2 datum moved 3 mm forward (stop face and")
    L.append("   leaves), so the falling tail always meets the stop; leaves a further 2.5 mm forward of the stop (sim seat is 1.9 deg nose-up)")
    L.append("3  Robot too far back lands on the stop wall's relief ledge (z 14.6) or the tower top (z 22) and hangs  ->  F3 45 deg rear")
    L.append("   lead-in from the stop face's top edge over the stop wall and the tower's side walls (replaces the screw-head relief ledge)")
    L.append("4  Rails must not touch legs or feet in stand, sit and stand-up  ->  F4 rails end 8 mm behind where the left foot comes down at")
    L.append("   the end of the stand-up (x -51), stay below z 24 and inside |y| 41; the legs never come behind x -40 while standing or sitting")
    L.append("5  Dock stays put: unchanged, foam tape or Dual Lock under the (larger) plate.  One printed PLA part, no flexure, nothing to buy.")
    L.append("")
    L.append("MEASURED IN MUJOCO (real Brain sit, --model asbuilt --manifest current, --volt 7.6 --drop 0.036, 2 seeds; start offset = robot")
    L.append("standing that far off; pass = both pads over their own leaf tip with 0.5 mm x margin and 1 mm y overlap, leaf pressed >= 1 mm,")
    L.append("no short, no fall, no rail contact with any other robot part)")
    L.append(f"   released A1:          x {fmt(a1.get('x_mm'), 'mm')}   y {fmt(a1.get('y_mm'), 'mm')}   yaw {fmt(a1.get('yaw_deg'), 'deg')}")
    L.append(f"   F2+F3, no rails:      x {fmt(d0.get('x_mm'), 'mm')}   y {fmt(d0.get('y_mm'), 'mm')}   yaw {fmt(d0.get('yaw_deg'), 'deg')}")
    L.append(f"   F1+F2+F3 (drawn):     x {fmt(ch.get('x_mm'), 'mm')}   y {fmt(ch.get('y_mm'), 'mm')}   yaw {fmt(ch.get('yaw_deg'), 'deg')}")
    L.append("   5-seed recheck of F1+F2+F3: y +3 mm fails 3 of 5 seeds (backpack hangs, pads lifted), so the dependable y window is -15..0 mm;")
    L.append("   x -6 fails 1 of 5; combined x and y offsets of 6 and 9 mm fail; mu 0.2 and 0.5 rail friction each fail some cases")
    for k in ("combo", "friction", "seeds"):
        if k in res:
            L.append(f"   {k}: {res[k]['passed']}/{res[k]['n']} pass")
    L.append("   Rails clear legs and feet by >= 7 mm in stand, sit and rise; AFTER the stand-up the sim robot steps back onto the rails (-4 mm)")
    L.append("")
    L.append("WHAT THE SIM SHOWED ABOUT THE SIT: the tail drops 59 mm and moves 68 mm backward in 0.55 s, swinging up to 16 mm left and 16 deg")
    L.append("while high, within 4 mm of its end point below z 19; the robot lands on its shins, feet lift; sideways push turns the robot about")
    L.append("its knees (about 0.6 deg of yaw per mm); from +3 mm to the left the yawed backpack hangs at z 14.5 (pads lifted), the main limit.")
    return L


if __name__ == "__main__":
    main()
