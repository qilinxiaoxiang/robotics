#!/usr/bin/env python3
"""Does the running brain stall when another process floods the A7Z's memory? Run on the Mac.

The 2026-10-30 fall: a python3 in another ssh session loaded the 671 MB brain log into a list (1.4 GB), the kernel paged
walk_wired.py out, and one tick waited 348 ms on a page fault. walk_wired.py now locks its pages (lock_memory). This
check repeats that load while the brain runs and reads back what the brain did:

  1. brain pid, VmLck / VmRSS / VmSwap and major faults (/proc/<pid>/stat field 12) before
  2. on the A7Z, for --seconds: python3 loads --file line by line with json.loads into a list, capped by ulimit -v
     (--cap-mb, a MemoryError instead of the OOM killer) and restarted until the time is up
  3. major faults and memory after; the brain's ticks inside the window (a tail of its log copied to the Mac, never
     parsed on the A7Z): max loop_ms, ticks over 40 and 100 ms, and mode
  Pass: 0 brain major faults during the load and no tick over 40 ms.

  python3 brain_stall_check.py [--host a7z] [--seconds 90] [--file ~/duck-logs/<big log>] [--out result.json]
  --quiet-only: no load, just faults and ticks over the same window (the brain's own baseline)
"""
import argparse
import json
import subprocess
import sys
import time

READER = r'''
import json, sys
rows = []
try:
    for ln in open(sys.argv[1]):
        try:
            rows.append(json.loads(ln))
        except ValueError:
            pass
except MemoryError:
    pass
print(len(rows))
'''


def ssh(host, cmd, timeout=60, stdin=None):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=8", host, cmd], input=stdin, capture_output=True, text=True,
                       timeout=timeout)
    return r.stdout


def brain_state(host):
    out = ssh(host, 'p=$(pgrep -f "^/home/radxa/.venvs/duck-policy/bin/python walk_wired.py" | head -1); echo $p; '
                    'tr "\\0" " " < /proc/$p/cmdline; echo; awk "{print \\$12}" /proc/$p/stat; '
                    'grep -E "VmLck|VmRSS|VmSwap" /proc/$p/status; grep MemAvailable /proc/meminfo')
    lines = out.strip().splitlines()
    pid, cmdline, majflt = int(lines[0]), lines[1], int(lines[2])
    mem = {ln.split(":")[0]: int(ln.split()[1]) for ln in lines[3:]}
    log = cmdline.split("--log ")[1].split()[0]
    return {"pid": pid, "log": log, "majflt": majflt, "mem_kb": mem}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--host", default="a7z")
    ap.add_argument("--seconds", type=float, default=90)
    ap.add_argument("--file", default="/home/radxa/duck-logs/duck_wired_log_app1030-040713.jsonl")
    ap.add_argument("--cap-mb", type=int, default=1400)
    ap.add_argument("--quiet-only", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    before = brain_state(a.host)
    t0 = float(ssh(a.host, "date +%s.%N"))
    print(f"brain pid {before['pid']}, log {before['log']}, before: {before['mem_kb']}, majflt {before['majflt']}",
          flush=True)
    if a.quiet_only:
        time.sleep(a.seconds)
        runs = []
    else:
        loop = (f'cat > /tmp/stall_reader.py; ulimit -v {a.cap_mb * 1024}; end=$((SECONDS+{int(a.seconds)})); '
                f'while [ $SECONDS -lt $end ]; do timeout $((end-SECONDS)) python3 /tmp/stall_reader.py {a.file}; done; '
                'rm -f /tmp/stall_reader.py')
        runs = ssh(a.host, loop, timeout=a.seconds + 60, stdin=READER).split()
    t1 = float(ssh(a.host, "date +%s.%N"))
    after = brain_state(a.host)

    n_rows = int((t1 - t0) * 60) + 2000  # 50 Hz plus margin
    tail = ssh(a.host, f"tail -n {n_rows} {before['log']}", timeout=120)
    ticks = []
    for ln in tail.splitlines():
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if t0 <= r.get("t", 0) <= t1 and r.get("loop_ms") is not None:
            ticks.append((r["loop_ms"], r.get("mode")))
    ms = [x for x, _ in ticks]
    res = {"t0": t0, "t1": t1, "load": not a.quiet_only, "reader_rows_per_run": runs, "before": before,
           "after": after, "brain_majflt_during": after["majflt"] - before["majflt"], "ticks": len(ms),
           "max_loop_ms": round(max(ms), 1) if ms else None, "over_40ms": sum(x > 40 for x in ms),
           "over_100ms": sum(x > 100 for x in ms), "modes": sorted({m for _, m in ticks if m}),
           "same_brain": before["pid"] == after["pid"]}
    res["pass"] = bool(ms) and res["same_brain"] and res["brain_majflt_during"] == 0 and res["over_40ms"] == 0
    print(json.dumps({k: v for k, v in res.items() if k not in ("before", "after")}, indent=1))
    print(f"after: {after['mem_kb']}")
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
