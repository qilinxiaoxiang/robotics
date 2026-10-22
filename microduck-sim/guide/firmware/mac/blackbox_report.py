"""Read the A7Z flight recorder (pi/blackbox.py) after a hang or power cut and print how each boot ended.

  python3 blackbox_report.py DIR [--boots 3] [--tail 20]

DIR holds the b<NNNN>-<boot8>-kmsg.log / -sys.jsonl pairs (a7z_blackbox_collect.sh copy, or the live mirror). For the
newest boots it prints: how the boot started (SoC boot-reason: COLD-BOOT = power came back, HOT-BOOT = reset while
powered, e.g. the watchdog), the watchdog and lockup settings in force, how long it ran, whether it ended in a clean
shutdown (systemd/kernel power-off lines) or stopped dead, every stall of the recorder itself, the last sys rows before the end (CPU busy, iowait, PSI, D-state processes with their kernel wait
channel, the busiest processes, the IRQs that fired most) and the last kernel lines with any error/warning counts in
the final 10 s.
"""
import argparse, glob, json, os

CLEAN = ("reboot: Power down", "reboot: Restarting system", "systemd-shutdown", "Reached target Power-Off",
         "Reached target Reboot")


def boots(d):
    stems = sorted({os.path.basename(p).rsplit("-", 1)[0] for p in glob.glob(d + "/b[0-9][0-9][0-9][0-9]-*-kmsg.log")
                    + glob.glob(d + "/b[0-9][0-9][0-9][0-9]-*-sys.jsonl")})
    return [os.path.join(d, s) for s in stems]


def rows(path):
    out = []
    try:
        with open(path) as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    out.append({"bad": line[:80]})  # a torn last line is itself evidence of a cut mid-write
    except OSError:
        pass
    return out


def kmsg(path):
    out = []
    try:
        with open(path, errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split(" ", 4)  # seen, kernel s, level, #seq, text
                if len(p) == 5:
                    out.append([p[0], p[1], p[2], p[4]])
    except OSError:
        pass
    return out


def describe(r):
    if "bad" in r:
        return "torn row: %r" % r["bad"]
    cpu = r.get("cpu") or {}
    top = ", ".join("%s %.0f%%" % (x["comm"], x["cpu"]) for x in r.get("top", [])[:3])
    irq = sorted((r.get("irq") or {}).items(), key=lambda kv: -kv[1])[:3]
    d = "; ".join("%s %ss in %s" % (x["comm"], x.get("s"), " < ".join(x.get("stack", [])[-4:][::-1]) or x["wchan"])
                  for x in r.get("dstate", []))
    return ("up %.1f s busy %s%% iowait %s%% load %s psi %s | top %s | irq %s%s%s" % (
        r.get("up") or 0, cpu.get("busy"), cpu.get("iowait"), r.get("load"), r.get("psi"), top,
        ", ".join("%s +%d" % kv for kv in irq), " | D: " + d if d else "",
        "" if r.get("kmsg_alive", True) else " | KMSG COPY DEAD") + (" | sysrq " + r["sysrq"] if r.get("sysrq") else ""))


def report(stem, ntail):
    name = os.path.basename(stem)
    allrows = rows(stem + "-sys.jsonl")
    heads = [r for r in allrows if "start" in r]
    srows = [r for r in allrows if "start" not in r]
    klines = kmsg(stem + "-kmsg.log")
    print("=" * 100)
    reason = [x[3].split("boot-reason:", 1)[1].strip() for x in klines if "boot-reason:" in x[3]]
    print("%s  start: %s" % (name, reason[0] if reason else "boot-reason line not found"))
    for h in heads:
        print("  recorder %s: watchdog %s | sysctl %s | rcu stall %s s" % (
            "restart" if h.get("restart") else "start", h.get("watchdog"),
            {k.split("/")[1]: v for k, v in (h.get("sysctl") or {}).items()}, h.get("rcu_stall_s")))
    if not srows:
        print("  no sys rows")
    else:
        last = srows[-1]
        print("  %d sys rows, last at up %.1f s (unix %.3f)" % (len(srows), last.get("up") or 0, last.get("t") or 0))
        gaps = [(b["up"] - a["up"], a) for a, b in zip(srows, srows[1:]) if a.get("up") and b.get("up")
                and b["up"] - a["up"] > 1.0]  # uptime, not the A7Z clock, which jumps when NTP syncs
        for g, a in gaps[-5:]:
            print("  recorder stall: %.1f s without a row after up %.1f s" % (g, a.get("up") or 0))
    clean = [x for x in klines if any(c in x[3] for c in CLEAN)]
    print("  end: %s" % ("clean shutdown (%s)" % clean[-1][3] if clean else "STOPPED DEAD (no shutdown lines)"))
    print("  last sys rows:")
    for r in srows[-5:]:
        print("    " + describe(r))
    if klines:
        try:
            tend = max(float(x[1]) for x in klines if x[1] != "-")
            late = [x for x in klines if x[1] != "-" and float(x[1]) > tend - 10]
            errs = [x for x in late if x[2] in ("emerg", "alert", "crit", "err", "warn")]
            print("  kernel: %d lines, %d err/warn in the last 10 s" % (len(klines), len(errs)))
        except ValueError:
            pass
        print("  last kernel lines:")
        for x in klines[-ntail:]:
            print("    [%s] %-6s %s" % (x[1], x[2], x[3][:160]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dir")
    ap.add_argument("--boots", type=int, default=3)
    ap.add_argument("--tail", type=int, default=20)
    a = ap.parse_args(argv)
    found = boots(a.dir)
    if not found:
        raise SystemExit("no blackbox files in %s" % a.dir)
    for stem in found[-a.boots:]:
        report(stem, a.tail)


if __name__ == "__main__":
    main()
