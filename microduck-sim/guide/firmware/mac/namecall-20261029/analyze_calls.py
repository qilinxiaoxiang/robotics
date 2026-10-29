"""Direction check on a robot recording of known calls (record_calls.sh): finds the N loudest voice-band events,
localises each with namecall.Localiser (planar, as deployed) and with the caller's elevation taken out, and compares
them with the expected azimuths in call order.

Elevation: the localiser assumes a horizontal source. A caller standing D m away with the mouth H m up and the head
microphones h m up arrives at elevation e = atan((H - h) / D), so every pair lag shrinks by cos(e) (microphones taken as
coplanar and level). Scaling the microphone positions by cos(e) gives the same predicted lags as the 3-D model.

  python3 analyze_calls.py recordings/calls_201411.wav --dist 2.0 --mouth 1.6 --mic 0.2 --n 8 \
      --expected 0,45,90,135,180,-135,-90,-45 --out results/calls_201411.json
"""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import namecall as nc  # noqa: E402


def wrap_deg(a):
    return (a + 180.0) % 360.0 - 180.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--n", type=int, default=8, help="number of calls in the recording")
    ap.add_argument("--min-gap", type=float, default=3.0, help="s between two calls")
    ap.add_argument("--dist", type=float, default=2.0, help="m, caller to robot, horizontal")
    ap.add_argument("--mouth", type=float, default=1.6, help="m, caller's mouth above the floor")
    ap.add_argument("--mic", type=float, default=0.2, help="m, head microphones above the floor")
    ap.add_argument("--expected", default="0,45,90,135,180,-135,-90,-45", help="deg, head frame, + left, in call order")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    src = nc.WavSource(a.wav)
    x, fs, blk = src.x, src.fs, nc.BLOCK
    n_blocks = len(x) // blk
    ears = x[: n_blocks * blk, :2].mean(axis=1).reshape(n_blocks, blk)
    e_db = np.array([nc.band_energy_db(b, fs)[0] for b in ears])  # (band, span) -> the 300-4000 Hz energy
    floor = float(np.percentile(e_db, 20))

    # the N loudest events, at least min_gap apart; each event's onset = first block 12 dB over the floor before its peak
    order = np.argsort(e_db)[::-1]
    peaks = []
    gap = int(a.min_gap * fs / blk)
    for k in order:
        if e_db[k] < floor + 12:
            break
        if all(abs(k - p) > gap for p in peaks):
            peaks.append(int(k))
        if len(peaks) == a.n:
            break
    peaks.sort()

    elev = math.atan2(a.mouth - a.mic, a.dist)
    flat = nc.Localiser(fs=fs)
    scaled = {k: (v[0] * math.cos(elev), v[1] * math.cos(elev)) for k, v in nc.MICS_MM.items()}
    tilted = nc.Localiser(fs=fs, mics_mm=scaled)
    expected = [float(v) for v in a.expected.split(",")] if a.expected else []

    rms_all = 20 * np.log10(np.sqrt((x[:, :4] ** 2).mean(axis=0)) + 1e-12)
    rows = []
    for i, p in enumerate(peaks):
        k = p
        while k > 0 and e_db[k - 1] > floor + 12 and p - k < 25:
            k -= 1
        s = max(0, k * blk - int(0.010 * fs))
        win = x[s: s + flat.window]
        lev = 20 * np.log10(np.sqrt((win[:, :3] ** 2).mean(axis=0)) + 1e-12)
        r0, r1 = flat.estimate(win), tilted.estimate(win)
        row = dict(i=i + 1, t=round(k * blk / fs, 2), peak_db=round(float(e_db[p]), 1), over_floor_db=round(float(e_db[p] - floor), 1),
                   level_db=dict(left=round(float(lev[0]), 1), right=round(float(lev[1]), 1), back=round(float(lev[2]), 1)),
                   az_planar=r0["az_deg"], az_elev=r1["az_deg"], margin_planar=r0["margin"], margin_elev=r1["margin"],
                   pairs=r1["pairs"])
        if i < len(expected):
            row["expected"] = expected[i]
            row["err_planar"] = round(wrap_deg(r0["az_deg"] - expected[i]), 1)
            row["err_elev"] = round(wrap_deg(r1["az_deg"] - expected[i]), 1)
        rows.append(row)

    def stats(key):
        v = [abs(r[key]) for r in rows if key in r]
        return dict(mean=round(float(np.mean(v)), 1), max=round(float(np.max(v)), 1)) if v else None

    side = [r for r in rows if "expected" in r and abs(r["expected"]) not in (0.0, 180.0)]
    out = dict(wav=os.path.basename(a.wav), seconds=round(len(x) / fs, 1), floor_db=round(floor, 1),
               channel_rms_dbfs=[round(float(v), 1) for v in rms_all], elevation_deg=round(math.degrees(elev), 1),
               events=len(rows), rows=rows, err_planar=stats("err_planar"), err_elev=stats("err_elev"),
               left_right_correct=sum(1 for r in side if np.sign(r["az_elev"]) == np.sign(r["expected"])),
               left_right_of=len(side),
               front_back_correct=sum(1 for r in rows if "expected" in r and abs(r["expected"]) != 90.0
                                      and (abs(r["az_elev"]) < 90) == (abs(r["expected"]) < 90)),
               front_back_of=sum(1 for r in rows if "expected" in r and abs(r["expected"]) != 90.0))
    for r in rows:
        print(f"{r['i']}: t {r['t']:6.2f} s  +{r['over_floor_db']:4.1f} dB  exp {r.get('expected', float('nan')):+6.0f}  "
              f"planar {r['az_planar']:+6.1f} ({r.get('err_planar', float('nan')):+6.1f})  "
              f"elev {r['az_elev']:+6.1f} ({r.get('err_elev', float('nan')):+6.1f})  margin {r['margin_elev']:.3f}  "
              f"L/R/B {r['level_db']['left']:.0f}/{r['level_db']['right']:.0f}/{r['level_db']['back']:.0f} dBFS")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
