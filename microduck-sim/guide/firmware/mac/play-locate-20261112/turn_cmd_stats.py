#!/usr/bin/env python3
"""Mac mini: does the heading hold's turn command (walk_brain: trim + KP * error + KI * integral, within +-TURN_MAX 2.0;
walk61 trained on +-1.0) separate the robot's falls from its clean walks?

Cuts every forward-walk segment (cmd vx > 0, mode walk) from the compact logs, labels it fell / up (tilt over 45 deg
during the segment or within 3 s after it), and compares the turn command the policy was fed.

  python3 turn_cmd_stats.py [--cache DIR] [--detail WHEN ...]
"""
import argparse
import glob
import json
import os
import time

import numpy as np


def tilt_deg(gb):
    g = gb / np.maximum(np.linalg.norm(gb, axis=1, keepdims=True), 1e-9)
    return np.degrees(np.arccos(np.clip(-g[:, 2], -1, 1)))


def segments(mask, t, gap=0.3):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    cuts = np.where(np.diff(t[idx]) > gap)[0]
    starts = np.r_[idx[0], idx[cuts + 1]]
    ends = np.r_[idx[cuts], idx[-1]]
    return list(zip(starts, ends))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="~/sims/fall-onset-20261112/cache")
    ap.add_argument("--out", default=None)
    ap.add_argument("--detail", type=float, nargs="*", default=[], help="epoch seconds of segment starts to print")
    ap.add_argument("--sim", nargs="*", default=None, help="sim tick-log npz files to run the same statistic on")
    a = ap.parse_args()
    files = a.sim if a.sim else sorted(glob.glob(os.path.join(os.path.expanduser(a.cache), "duck_wired_log_app*.npz")))
    rows = []
    for f in files:
        L = dict(np.load(f))
        t = L["t"]
        tot = tilt_deg(L["gb"])
        walking = (L["mode"] == 2) & (L["vx"] > 0.01) & L["torque"].astype(bool)
        for s, e in segments(walking, t):
            if t[e] - t[s] < 0.8:
                continue
            after = int(np.searchsorted(t, t[e] + 3.0))
            fell_i = np.where(tot[s:after] > 45)[0]
            fell = len(fell_i) > 0
            end = s + int(fell_i[0]) if fell else e
            # the fall's onset: last tick under 15 deg before the 45
            j = end
            while fell and j > s and tot[j] > 15:
                j -= 1
            k = slice(s, min(j, e) + 1) if fell else slice(s, e + 1)
            turn = np.nan_to_num(L["turn"][k])
            gz = L["gyro"][k, 2]
            vth = L["vth"][k]
            if len(turn) < 20:
                continue
            last = turn[-50:]
            rows.append(dict(log=os.path.basename(f)[15:-4], t0=float(t[s]), when=time.strftime("%m-%d %H:%M:%S", time.localtime(t[s])),
                             dur=float(t[e] - t[s]), fell=bool(fell), fall_after_s=float(t[j] - t[s]) if fell else None,
                             vx=float(np.median(L["vx"][k])), manual_turn=bool(np.any(np.abs(vth) > 1e-3)),
                             turn_absmax=float(np.max(np.abs(turn))), turn_absmean=float(np.mean(np.abs(turn))),
                             sat_share=float(np.mean(np.abs(turn) > 1.0)), pinned_share=float(np.mean(np.abs(turn) > 1.9)),
                             last1s_absmean=float(np.mean(np.abs(last))), last1s_sat=float(np.mean(np.abs(last) > 1.0)),
                             turn_swing=float(np.max(turn) - np.min(turn)), trim=float(np.nanmedian(np.nan_to_num(L["trim"][k]))),
                             gz_rms=float(np.sqrt(np.mean(gz ** 2))), gz_absmax=float(np.max(np.abs(gz))),
                             batt=float(np.nanmedian(L["batt"][k]))))
            if any(abs(t[s] - d) < 1.0 for d in a.detail):
                print(f"\n--- {rows[-1]['when']} {rows[-1]['log']} fell={fell}")
                print("  t   vx   vth  turn   gz(mean) gz(rms) tilt  legs_mA")
                for b in np.arange(0, t[min(after, len(t) - 1)] - t[s], 0.25):
                    m = np.where((t >= t[s] + b) & (t < t[s] + b + 0.25))[0]
                    if len(m):
                        print(f"  {b:4.2f} {np.mean(L['vx'][m]):4.2f} {np.mean(L['vth'][m]):5.2f} {np.nanmean(np.nan_to_num(L['turn'][m])):6.2f}"
                              f"  {np.mean(L['gyro'][m, 2]):7.2f} {np.sqrt(np.mean(L['gyro'][m, 2] ** 2)):6.2f} {np.max(tot[m]):5.1f} {np.nanmean(L['legs_ma'][m]):6.0f}")
    up = [r for r in rows if not r["fell"]]
    fe = [r for r in rows if r["fell"]]
    print(f"{len(rows)} forward-walk segments: {len(up)} up, {len(fe)} fell")

    def q(v):
        return "p25 %.2f  p50 %.2f  p75 %.2f  p90 %.2f" % tuple(np.percentile(v, [25, 50, 75, 90])) if len(v) else "-"
    for key in ("turn_absmax", "turn_absmean", "sat_share", "pinned_share", "last1s_absmean", "last1s_sat", "turn_swing", "gz_rms", "gz_absmax", "dur"):
        print(f"{key:15s} up   {q([r[key] for r in up])}")
        print(f"{'':15s} fell {q([r[key] for r in fe])}")
    print("\nfall rate by the largest |turn| command in the segment (before the fall's onset):")
    for lo, hi in ((0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 1.9), (1.9, 2.01)):
        g = [r for r in rows if lo <= r["turn_absmax"] < hi]
        print(f"  {lo:.1f}-{hi:.1f}: {sum(r['fell'] for r in g)} fell of {len(g)}")
    print("fall rate by share of the segment with |turn| > 1.0 (outside walk61's trained range):")
    for lo, hi in ((0, 0.01), (0.01, 0.1), (0.1, 0.3), (0.3, 0.6), (0.6, 1.01)):
        g = [r for r in rows if lo <= r["sat_share"] < hi]
        print(f"  {lo:.2f}-{hi:.2f}: {sum(r['fell'] for r in g)} fell of {len(g)}")
    print("\nfalls:")
    for r in fe:
        print(f"  {r['when']} {r['log']:16s} vx {r['vx']:.2f} dur {r['dur']:4.1f} onset {r['fall_after_s']:5.2f}s turn max {r['turn_absmax']:.2f} mean {r['turn_absmean']:.2f} "
              f">1.0 {r['sat_share']:.2f} last1s {r['last1s_absmean']:.2f} swing {r['turn_swing']:.2f} trim {r['trim']:+.2f} gz max {r['gz_absmax']:.1f} manual {r['manual_turn']}")
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
