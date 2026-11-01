"""Every real sit-down in the backed-up A7Z brain logs: read drops during the sit-down, peak tilt, seated pitch, supply.
Streams grep output (sit-mode rows only), never loads a log whole."""
import json, math, subprocess, sys, os

D = os.path.expanduser("~/Backups/a7z-duck-logs")
files = sys.argv[1:]
out = []
for f in files:
    p = subprocess.Popen(["grep", "-F", '"mode": "sit"', os.path.join(D, f)], stdout=subprocess.PIPE,
                         env=dict(os.environ, LC_ALL="C"), text=True, bufsize=1 << 20)
    ep = None
    def close(ep):
        if ep and ep["n"] > 10:
            out.append(ep)
    for line in p.stdout:
        try:
            r = json.loads(line)
        except Exception:
            continue
        t = r.get("t")
        ph = r.get("sit_phase")
        if ep is None or t - ep["t_last"] > 1.0 or (ph in ("prep", "down") and ep["last_ph"] in ("seated", "rise")):
            close(ep)
            ep = dict(file=f, t0=t, t_last=t, n=0, down_n=0, down_stale=0, down_peak=0.0, down_peak_back=0.0,
                      seated_pitch=[], seated_t=None, phases=[], last_ph=None, dv=set(), knees_max=0.0)
        ep["t_last"] = t
        ep["n"] += 1
        if ph != ep["last_ph"]:
            ep["phases"].append(ph)
        ep["last_ph"] = ph
        gb = r.get("gb") or [0, 0, -1]
        tilt = math.degrees(math.acos(max(-1, min(1, -gb[2]))))
        pitch = math.degrees(math.atan2(gb[0], -gb[2]))  # sign as logged
        in_down = (ph in ("prep", "down")) if ph is not None else (t - ep["t0"] < 3.0)
        if ph == "seated" and ep["seated_t"] is None:
            ep["seated_t"] = t - ep["t0"]
        if in_down or (ph == "seated" and t - ep["t0"] < 4.0):
            ep["down_n"] += 1
            ep["down_stale"] += int((not r.get("fresh", True)) or bool(r.get("missing")))
            ep["down_peak"] = max(ep["down_peak"], tilt)
        if ph == "seated" or (ph is None and 2.0 < t - ep["t0"] < 4.0):
            ep["seated_pitch"].append(pitch)
        if r.get("battery_dv") is not None:
            ep["dv"].add(r["battery_dv"])
        q = r.get("q") or []
        if len(q) > 8:
            ep["knees_max"] = max(ep["knees_max"], abs(q[1]), abs(q[6]))
    close(ep)
    p.wait()

for e in out:
    sp = e["seated_pitch"]
    print(f'{e["file"][15:]:28s} t0 {e["t0"]:.0f} rows {e["n"]:5d} phases {"/".join(str(x) for x in e["phases"][:5]):28s} '
          f'seated_at {e["seated_t"] if e["seated_t"] is None else round(e["seated_t"], 2)} '
          f'down stale {e["down_stale"]}/{e["down_n"]} ({100 * e["down_stale"] / max(1, e["down_n"]):.1f} %) '
          f'peak tilt {e["down_peak"]:.1f} seated pitch {(sum(sp) / len(sp)) if sp else float("nan"):+.1f} '
          f'knee max {e["knees_max"]:.2f} dv {sorted(e["dv"])[:3]}')
