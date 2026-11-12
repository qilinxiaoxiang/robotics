#!/usr/bin/env python3
"""Mac mini: what the robot was doing in the seconds before each fall the sim did not reproduce.

Reads the scorecard (~/duck-walks/scorecard-auto.json) and the compact logs (compact_logs.py). For every robot-only
fall it prints, in 0.5 s bins back from the fall: the command, the policy, trunk pitch/roll, gyro rms per axis, the
action's tick-to-tick change, leg current and loop timing; then a one-line class per fall.

  python3 fall_onset.py [--cache DIR] [--back 6] [--detail]
"""
import argparse
import collections
import json
import os

import numpy as np

MODES = ["monitor", "stand", "walk", "sit", "seepick", "groundpick", "kick", "other"]
POL = {0: "-", 1: "walk61", 2: "stand61"}


def load(cache, log):
    return dict(np.load(os.path.join(cache, log + ".npz")))


def tilt(gb):
    g = gb / np.maximum(np.linalg.norm(gb, axis=1, keepdims=True), 1e-9)
    pitch = np.degrees(np.arctan2(-g[:, 0], -g[:, 2]))   # + = nose down if x is forward
    roll = np.degrees(np.arctan2(g[:, 1], -g[:, 2]))
    tot = np.degrees(np.arccos(np.clip(-g[:, 2], -1, 1)))
    return pitch, roll, tot


def dom_freq(x, dt=0.0208):
    x = x - np.mean(x)
    if len(x) < 16 or np.std(x) < 1e-6:
        return 0.0, 0.0
    f = np.fft.rfftfreq(len(x), dt)
    p = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    p[0] = 0
    k = int(np.argmax(p))
    return float(f[k]), float(p[k] / max(p.sum(), 1e-12))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="~/sims/fall-onset-20261112/cache")
    ap.add_argument("--back", type=float, default=6.0)
    ap.add_argument("--detail", action="store_true")
    ap.add_argument("--all-robot-falls", action="store_true", help="also falls the sim reproduced")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cache = os.path.expanduser(a.cache)
    res = json.load(open(os.path.expanduser("~/duck-walks/scorecard-auto.json")))["results"]
    falls = [r for r in res if r["robot"] != "up" and (a.all_robot_falls or r["sim"] == "up")]
    logs = {}
    rows = []
    seen = []
    for r in falls:
        log, start, kind = r["id"].rsplit("-", 2)
        start = float(start)
        if log not in logs:
            logs[log] = load(cache, log)
        L = logs[log]
        t = L["t"]
        tf = start + (r["robot_fell_at"] or 0.0)
        pitch, roll, tot = tilt(L["gb"])
        # the real onset: first time total tilt passes 20 deg and keeps rising to 45, searched back from tf+0.5
        i1 = int(np.searchsorted(t, tf + 0.5))
        i0 = int(np.searchsorted(t, tf - 8.0))
        over = np.where(tot[i0:i1] > 45)[0]
        i45 = i0 + (int(over[0]) if len(over) else (i1 - i0 - 1))
        j = i45
        while j > i0 and tot[j] > 15:
            j -= 1
        t15 = t[j]
        if any(abs(t15 - s) < 1.0 for s in seen):
            dup = True
        else:
            dup = False
            seen.append(t15)
        ia = int(np.searchsorted(t, t15 - a.back))
        sl = slice(ia, i45 + 1)
        tt = t[sl] - t15
        # classify
        pre = slice(int(np.searchsorted(t, t15 - 2.0)), j + 1)
        vx, vth = L["vx"][pre], L["vth"][pre]
        mode = L["mode"][pre]
        cmd_moving = (np.abs(vx) > 0.01) | (np.abs(vth) > 0.01)
        last_move = np.where((np.abs(L["vx"][ia:j + 1]) > 0.01) | (np.abs(L["vth"][ia:j + 1]) > 0.01))[0]
        since_stop = (t15 - t[ia + last_move[-1]]) if len(last_move) else None
        last_kind = None
        if len(last_move):
            k = ia + last_move[-1]
            last_kind = "walk" if abs(L["vx"][k]) > 0.01 else "turn"
        gz = L["gyro"][pre, 2]
        gx = L["gyro"][pre, 0]
        gy = L["gyro"][pre, 1]
        fz, cz = dom_freq(gz)
        fx, cx = dom_freq(gx)
        fy, cy = dom_freq(gy)
        direction = ("fwd" if pitch[i45] > 0 else "back") if abs(pitch[i45]) > abs(roll[i45]) else ("R" if roll[i45] > 0 else "L")
        row = dict(when=r["when"], kind=r["kind"], log=log, t15=round(float(t15), 2), dup=dup,
                   policy=POL[int(np.median(L["policy"][pre]))], mode=MODES[int(np.median(mode))],
                   cmd_at_onset=[round(float(L["vx"][j]), 2), round(float(L["vth"][j]), 2)],
                   moving_cmd_share=round(float(np.mean(cmd_moving)), 2),
                   since_last_move_cmd=None if since_stop is None else round(float(since_stop), 2), last_move=last_kind,
                   gyro_rms=[round(float(np.sqrt(np.mean(v ** 2))), 2) for v in (gx, gy, gz)],
                   gyro_peak_z=round(float(np.max(np.abs(gz))), 2),
                   dom=[[round(fx, 1), round(cx, 2)], [round(fy, 1), round(cy, 2)], [round(fz, 1), round(cz, 2)]],
                   dir=direction, pitch45=round(float(pitch[i45]), 0), roll45=round(float(roll[i45]), 0),
                   legs_ma_peak=round(float(np.nanmax(L["legs_ma"][pre])), 0),
                   loop_ms_max=round(float(np.nanmax(L["loop_ms"][pre])), 1),
                   miss_ticks=int(np.sum(~L["fresh"][pre].astype(bool))), batt=float(np.nanmedian(L["batt"][pre])),
                   turn_cmd_abs_max=round(float(np.nanmax(np.abs(np.nan_to_num(L["turn"][pre])))), 2),
                   trim=round(float(np.nanmedian(np.nan_to_num(L["trim"][pre]))), 2),
                   hold_s_min=round(float(np.nanmin(np.nan_to_num(L["hold_s"][pre], nan=1.0))), 2))
        rows.append(row)
        if a.detail and not dup:
            print(f"\n=== {r['when']} {r['kind']} {log} onset(15deg) t={t15:.2f} fell {direction} pitch {pitch[i45]:.0f} roll {roll[i45]:.0f}")
            print("  t_rel  mode   policy   vx   vth  turn | pitch  roll | gyro rms x  y  z | dAct  legs_mA loop_max miss")
            b = -a.back
            while b < (t[i45] - t15) + 0.01:
                m = (tt >= b) & (tt < b + 0.5)
                if m.sum() > 2:
                    idx = np.where(m)[0] + ia
                    act = L["action"][idx]
                    dact = np.nanmean(np.abs(np.diff(act, axis=0))) if np.isfinite(act).any() else float("nan")
                    print(f"  {b:5.1f}  {MODES[int(np.median(L['mode'][idx]))]:6s} {POL[int(np.median(L['policy'][idx]))]:8s}"
                          f" {np.mean(L['vx'][idx]):4.2f} {np.mean(L['vth'][idx]):5.2f} {np.nanmean(np.nan_to_num(L['turn'][idx])):5.2f} |"
                          f" {np.mean(pitch[idx]):5.1f} {np.mean(roll[idx]):5.1f} |"
                          f" {np.sqrt(np.mean(L['gyro'][idx, 0] ** 2)):5.2f} {np.sqrt(np.mean(L['gyro'][idx, 1] ** 2)):5.2f} {np.sqrt(np.mean(L['gyro'][idx, 2] ** 2)):5.2f} |"
                          f" {dact:5.3f} {np.nanmean(L['legs_ma'][idx]):6.0f} {np.nanmax(L['loop_ms'][idx]):6.1f} {int(np.sum(~L['fresh'][idx].astype(bool))):3d}")
                b += 0.5
    uniq = [r for r in rows if not r["dup"]]
    print(f"\n{len(rows)} scorecard fall actions = {len(uniq)} distinct falls")
    print("when                kind     policy  cmd@onset   since_stop last  dir  gyro_rms(x,y,z)      peak_z dom_f(x,y,z)        legsmA loopmax miss turn| trim hold")
    for r in uniq:
        print(f"{r['when']} {r['kind']:8s} {r['policy']:7s} {str(r['cmd_at_onset']):12s} {str(r['since_last_move_cmd']):>6s} {str(r['last_move']):5s} {r['dir']:4s} "
              f"{str(r['gyro_rms']):20s} {r['gyro_peak_z']:5.1f} {str([d[0] for d in r['dom']]):18s} {r['legs_ma_peak']:6.0f} {r['loop_ms_max']:6.1f} {r['miss_ticks']:3d} {r['turn_cmd_abs_max']:5.2f} {r['trim']:5.2f} {r['hold_s_min']:4.2f}")
    c = collections.Counter()
    for r in uniq:
        if r["cmd_at_onset"] != [0.0, 0.0]:
            c["moving command at onset (" + ("walk" if r["cmd_at_onset"][0] else "turn") + ")"] += 1
        elif r["since_last_move_cmd"] is not None and r["since_last_move_cmd"] < 3.0:
            c[f"zero command, within 3 s after a {r['last_move']} ended"] += 1
        else:
            c["zero command, quiet before"] += 1
    print(dict(c))
    c2 = collections.Counter(r["dir"] for r in uniq)
    print("direction", dict(c2))
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
