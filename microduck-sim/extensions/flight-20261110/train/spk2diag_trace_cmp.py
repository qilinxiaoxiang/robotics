"""spk2 diagnosis: compare runtime --sp-trace files of two policies on the same seeds (spk2diag_trace.sh).

Per phase bin (seepick phase 0.20-0.60): the neck and head actions and joint positions (Brain order 5-8: neck_pitch,
head_pitch, head_yaw, head_roll), the leg actions' size, the jaw angle, pad height, pad and object in the foot frame,
the object-minus-pad offset, trunk tilt, beak-floor force and which head geom touches the ball first.
  python3 train/spk2diag_trace_cmp.py bend4 spk2_600 0 2 3 5 7
"""
import json
import statistics as st
import sys
from pathlib import Path

EV = Path(__file__).resolve().parent / "eval"
HEAD = ("neck_pitch", "head_pitch", "head_yaw", "head_roll")
BINS = [(0.20, 0.30), (0.30, 0.34), (0.34, 0.38), (0.38, 0.42), (0.42, 0.50), (0.50, 0.60)]


def rows(pol, k):
    return [json.loads(ln) for ln in (EV / f"pkt_trace_{pol}_s{k}.jsonl").read_text().splitlines() if ln.strip()]


def first_contact(rs):
    for r in rs:
        for g, o, dist, fn in r["head_contacts"]:
            if "object" in o or "ball" in o or o.startswith("g"):
                if "floor" not in o:
                    return r["phase"], g, o
    return None


def summarise(pol, seeds):
    out = {}
    for lo, hi in BINS:
        acc = {}
        for k in seeds:
            for r in rows(pol, k):
                if not lo <= r["phase"] < hi:
                    continue
                v = dict(zip([f"a_{h}" for h in HEAD], r["action"][5:9]))
                v.update(zip([f"q_{h}" for h in HEAD], r["q"][5:9]))
                v["a_leg_abs"] = st.mean(abs(x) for x in r["action"][:5] + r["action"][9:])
                v["jaw_deg"] = r["jaw_rad"] * 57.2958
                v["pad_z_mm"] = r["pad_z"] * 1000
                v["lip_low_mm"] = r["lip_low_z"] * 1000
                v["pad_x_mm"], v["pad_y_mm"] = (1000 * x for x in r["pad_foot_xy"])
                v["obj_x_mm"], v["obj_y_mm"] = (1000 * x for x in r["obj_foot_xy"])
                v["rel_x_mm"] = v["obj_x_mm"] - v["pad_x_mm"]
                v["rel_y_mm"] = v["obj_y_mm"] - v["pad_y_mm"]
                v["tilt"] = r["tilt_deg"]
                v["beak_floor_n"] = r["beak_floor_n"]
                v["pinched"] = float(r["pinched"])
                v["jaw_c"] = float(r["jaw_contact"])
                v["upper_c"] = float(r["upper_contact"])
                for kk, x in v.items():
                    acc.setdefault(kk, []).append(x)
        out[f"{lo:.2f}-{hi:.2f}"] = {kk: round(st.mean(x), 3) for kk, x in acc.items()}
    return out


def main():
    a, b, seeds = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3:]]
    sa, sb = summarise(a, seeds), summarise(b, seeds)
    res = dict(policies=[a, b], seeds=seeds, bins={})
    for bn in sa:
        print(f"phase {bn}")
        res["bins"][bn] = {}
        for kk in sa[bn]:
            x, y = sa[bn][kk], sb[bn].get(kk)
            res["bins"][bn][kk] = [x, y]
            print(f"   {kk:14s} {a} {x:9.3f}   {b} {y:9.3f}   diff {y - x:+9.3f}")
    res["first_contact"] = {p: {k: first_contact(rows(p, k)) for k in seeds} for p in (a, b)}
    for p in (a, b):
        print(p, "first head-ball contact (phase, head geom, other):", res["first_contact"][p])
    (EV / f"pkt_cmp_{a}_{b}.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
