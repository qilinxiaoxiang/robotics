"""Cost of namecall.py on the A7Z by --wav replay only (no capture card, no control file, no sound): any-voice and
--name mochi, each pinned to one core with taskset at nice 19, while the brain keeps running. Records per run the
replay's own cost line (CPU share of one core, per-block processing time), the pinned core's clock and the SoC
temperature, and the brain's tick intervals from its newest tick log over the same seconds (to show it was not
disturbed).

  ssh a7z 'cd ~/rt/microduck-sim/guide/firmware/mac/namecall-20261029 && \
      ~/.venvs/duck-policy/bin/python kws_a7z_cost.py ~/duck-logs/calls_201411.wav --cores 2,6 --out ~/duck-logs/kws_cost.json'

Throttled estimate: CPU share x (measured core clock / 416 MHz), the clock both clusters were pinned at in the closed
head (CURRENT-STATE a7z_closed_head_thermal_and_resets).
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
PY = sys.executable
THROTTLE_MHZ = 416.0


def read(path, default=None):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def sampler(core, stop, out):
    while not stop.is_set():
        mhz = read(f"/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_cur_freq")
        temp = read("/sys/class/thermal/thermal_zone0/temp")
        out.append((time.time(), None if mhz is None else int(mhz) / 1000.0, None if temp is None else int(temp) / 1000.0))
        time.sleep(0.25)


def brain_ticks(t0, t1):
    logs = glob.glob(os.path.expanduser("~/duck-logs/duck_wired_log_*.jsonl"))
    if not logs:
        return None
    path = max(logs, key=os.path.getmtime)
    ts = []
    with open(path, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - int(80000 * (time.time() - t0 + 5))))   # the brain writes about 67 kB/s
        for line in f:
            try:
                t = float(json.loads(line).get("t", 0))
            except ValueError:
                continue
            if t0 <= t <= t1:
                ts.append(t)
    if len(ts) < 3:
        return dict(log=os.path.basename(path), ticks=len(ts))
    d = sorted((b - a) * 1000.0 for a, b in zip(ts, ts[1:]))
    q = lambda p: round(d[min(len(d) - 1, int(p * len(d)))], 1)
    return dict(log=os.path.basename(path), ticks=len(ts), per_s=round(len(ts) / (ts[-1] - ts[0]), 1),
                dt_ms_p50=q(0.5), dt_ms_p90=q(0.9), dt_ms_p99=q(0.99), dt_ms_max=round(d[-1], 1))


def run(wav, core, extra, tag):
    log = f"/tmp/namecall_cost_{tag}_cpu{core}.jsonl"
    if os.path.exists(log):
        os.remove(log)
    cmd = ["taskset", "-c", str(core), "nice", "-n", "19", PY, os.path.join(MAC, "namecall.py"), "--wav", wav,
           "--no-head", "--mute", "--no-sound", "--log", log, "--quiet"] + extra
    stop, samples = threading.Event(), []
    th = threading.Thread(target=sampler, args=(core, stop, samples), daemon=True)
    t0 = time.time()
    th.start()
    p = subprocess.run(cmd, cwd=MAC, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    t1 = time.time()
    stop.set()
    th.join()
    rep = None
    if os.path.exists(log):
        for line in open(log):
            r = json.loads(line)
            if r.get("kind") == "replay":
                rep = r
    mhz = [s[1] for s in samples if s[1]]
    temp = [s[2] for s in samples if s[2]]
    res = dict(tag=tag, core=core, cmd=" ".join(cmd), rc=p.returncode, wall_s=round(t1 - t0, 2), replay=rep,
               core_mhz_mean=round(sum(mhz) / len(mhz)) if mhz else None, soc_temp_c_max=max(temp) if temp else None,
               brain=brain_ticks(t0, t1), tail=p.stdout.strip().splitlines()[-2:])
    if rep and mhz:
        res["cpu_share_throttled_est"] = round(rep["cpu_share"] * (sum(mhz) / len(mhz)) / THROTTLE_MHZ, 3)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--cores", default="2")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cpu_part = {}
    for line in (read("/proc/cpuinfo", "") or "").splitlines():
        if line.startswith("processor"):
            cur = int(line.split(":")[1])
        if line.startswith("CPU part"):
            cpu_part[cur] = {"0xd05": "Cortex-A55", "0xd0b": "Cortex-A76"}.get(line.split(":")[1].strip(), line)
    idle_t0 = time.time()
    time.sleep(10)
    out = dict(made=time.strftime("%Y-%m-%d %H:%M:%S"), wav=a.wav, brain_before=brain_ticks(idle_t0, time.time()),
               runs=[])
    for core in [int(c) for c in a.cores.split(",")]:
        for tag, extra in (("any_voice", []), ("name_mochi", ["--name", "mochi"])):
            r = run(a.wav, core, extra, tag)
            r["core_type"] = cpu_part.get(core)
            out["runs"].append(r)
            print(json.dumps({k: r[k] for k in ("tag", "core", "core_type", "rc", "core_mhz_mean", "soc_temp_c_max",
                                                "cpu_share_throttled_est") if k in r}),
                  json.dumps({k: (r["replay"] or {}).get(k) for k in ("audio_s", "cpu_s", "cpu_share", "block_ms_p50",
                                                                       "block_ms_p99", "block_ms_max", "kw_hits")}),
                  json.dumps(r["brain"]), flush=True)
            time.sleep(5)
    t = time.time()
    time.sleep(10)
    out["brain_after"] = brain_ticks(t, time.time())
    print("brain before", json.dumps(out["brain_before"]), "after", json.dumps(out["brain_after"]))
    if a.out:
        with open(os.path.expanduser(a.out), "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
