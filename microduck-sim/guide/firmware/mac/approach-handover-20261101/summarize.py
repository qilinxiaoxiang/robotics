"""Stop positions of the approach batch against the T2 bite window (landing spot 8.7 cm ahead, polar window w:
|r - 0.087| <= w and |bearing| <= w / 0.087 rad). Writes summary.json in the run folder (argument, default runs)."""
import glob, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, sys.argv[1] if len(sys.argv) > 1 else "runs")
SPOT = 0.087
rows = []
for f in sorted(glob.glob(os.path.join(RUNS, "r*.json"))):
    d = json.load(open(f))
    tag = os.path.basename(f)[:-5]
    r, b = d.get("true_r"), d.get("true_bearing_deg")
    w = None if r is None else round(max(abs(r - SPOT), abs(math.radians(b)) * SPOT), 4)
    rows.append(dict(case=tag, ok=d["ok"], why=d["why"], fell=d["fell_at"], r=r, bearing=b, need_w=w,
                     elapsed=d["elapsed_s"], approaches=d["approaches"], max_tilt=d.get("max_tilt")))
arr = [x for x in rows if x["ok"] and x["need_w"] is not None]
def frac(w): return round(sum(x["need_w"] <= w for x in arr) / len(rows), 3)
summ = dict(cases=len(rows), arrived=len(arr), fell=sum(bool(x["fell"]) for x in rows),
            within_w1=frac(0.01), within_w3=frac(0.03), within_w8=frac(0.08), rows=rows)
json.dump(summ, open(os.path.join(RUNS, "summary.json"), "w"), indent=1)
for x in rows:
    print(x["case"], x["ok"], x["why"][:30], "r", x["r"], "b", x["bearing"], "need_w", x["need_w"], "t", x["elapsed"])
print({k: v for k, v in summ.items() if k != "rows"})
