"""One seat and stand-up through the runner's brain-in-sim path: fake_pi.py (MuJoCo duck behind the Pi UDP protocol)
and walk_brain.py's own main loop, launched as pet/mind/runner.py's SimBrain does (the as-built 10-15 config with the
10-15 manifest, KP 200, the rail voltage), driven by a control-file script instead of the mind. Mac mini only.

  ~/.venvs/microduck-dyn/bin/python fakepi_seat.py LABEL [--reps 4] [--port 9900] [--no-compensation] [--refit]
      [--manifest PATH] [--volt 7.0] [--to-stand] [--seated-s 8] [--after-s 10]

Script: monitor 1 s, walk at zero command, {"mode": "sit"} 4 s later, a walk at zero command (or {"mode": "stand"}
with --to-stand) --seated-s later, then --after-s of standing. Appends one row per seat to results/fakepi_seats.jsonl:
the brain's rise (knee path, the 1.0 rad crossings), the hand-over tick, and the true trunk tilt from fake_pi's trace.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(MAC, "..", "..", "..", ".."))
WHOLE = os.path.join(ROOT, "microduck-sim", "hardware-design-20260912", "whole-robot-20260912")
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
WALK = os.path.expanduser("~/.venvs/microduck-walk/bin/python")
sys.path.insert(0, MAC)
from walk_brain import NAMES, SIT_KNEE_MIN  # noqa: E402

LK, RK = NAMES.index("left_knee"), NAMES.index("right_knee")

ap = argparse.ArgumentParser()
ap.add_argument("label")
ap.add_argument("--reps", type=int, default=4)
ap.add_argument("--port", type=int, default=9900)
ap.add_argument("--no-compensation", action="store_true", help="walk_brain.py --no-compensation (walk_wired.py's default)")
ap.add_argument("--refit", action="store_true", help="fake_pi's evaluate.load followed by evaluate_delay.refit_body_bvh")
ap.add_argument("--manifest", default=None, help="mass manifest (default: the 10-15 asbuilt one, as the runner)")
ap.add_argument("--volt", type=float, default=7.0)
ap.add_argument("--to-stand", action="store_true")
ap.add_argument("--seated-s", type=float, default=8.0)
ap.add_argument("--after-s", type=float, default=10.0)
a = ap.parse_args()

REFIT_SHIM = """import os, runpy, sys
mac, whole = sys.argv[1], sys.argv[2]
sys.path[:0] = [os.path.join(whole, "dynamics"), os.path.join(whole, "delay-repair-20260912"), mac]
import evaluate, evaluate_delay
_load = evaluate.load
def load(cfg):
    out = _load(cfg)
    print("refit:", sorted(evaluate_delay.refit_body_bvh(out[0])), flush=True)
    return out
evaluate.load = load
sys.argv = [os.path.join(mac, "fake_pi.py")] + sys.argv[3:]
os.chdir(mac)
runpy.run_path(sys.argv[0], run_name="__main__")
"""


def seat(rep):
    d = tempfile.mkdtemp(prefix=f"seat-{a.label}-", dir=os.path.expanduser("~/sims/sit-rise-20261029"))
    cfg = json.load(open(os.path.join(WHOLE, "dynamics", "asbuilt-20261015", "asbuilt.config.json")))
    cfg["mass_manifest"] = a.manifest or os.path.join(WHOLE, "dynamics", "asbuilt-20261015", "asbuilt-mass-manifest.json")
    cfg.update(remove_old_battery_kg=0.09, kp=200, voltage=a.volt)
    json.dump(cfg, open(os.path.join(d, "sim_config.json"), "w"), indent=1)
    cmd, log, trace = os.path.join(d, "cmd.json"), os.path.join(d, "brain_log.jsonl"), os.path.join(d, "trace.jsonl")
    json.dump({"mode": "monitor"}, open(cmd, "w"))
    total = 1 + 4 + a.seated_s + a.after_s
    port = a.port + rep
    fake_args = ["--udp", str(port), "--duration", str(total + 12), "--trace", trace, "--config",
                 os.path.join(d, "sim_config.json")]
    if a.refit:
        shim = os.path.join(d, "refit_shim.py")
        open(shim, "w").write(REFIT_SHIM)
        fake_cmd = [PY, shim, MAC, WHOLE] + fake_args
    else:
        fake_cmd = [PY, os.path.join(MAC, "fake_pi.py")] + fake_args
    fake = subprocess.Popen(fake_cmd, stdout=open(os.path.join(d, "fake_pi.out"), "w"), stderr=subprocess.STDOUT, cwd=MAC)
    time.sleep(4.0)
    walk = WALK if os.path.exists(WALK) else PY
    brain = subprocess.Popen([walk, os.path.join(MAC, "walk_brain.py"), "--pi", "127.0.0.1", "--udp", str(port),
                              "--cmd", cmd, "--log", log] + (["--no-compensation"] if a.no_compensation else []),
                             stdout=open(os.path.join(d, "brain.out"), "w"), stderr=subprocess.STDOUT, cwd=MAC)

    def write(c):
        tmp = cmd + ".tmp"
        json.dump(c, open(tmp, "w"))
        os.replace(tmp, cmd)
        return time.time()

    time.sleep(1.0)
    write({"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0})
    time.sleep(4.0)
    t_sit = write({"mode": "sit"})
    time.sleep(a.seated_s)
    t_up = write({"mode": "stand"} if a.to_stand else {"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0})
    time.sleep(a.after_s)
    for p in (brain, fake):
        p.terminate()
        p.wait(timeout=10)
    rows = [json.loads(l) for l in open(log) if l.startswith("{")]
    tr = [json.loads(l) for l in open(trace)]
    rise = [r for r in rows if r.get("sit_phase") == "rise"]
    hand = next((r["t"] for r in rows if rise and r["t"] > rise[0]["t"] and r.get("mode") != "sit"), None)
    knee = [(r["t"], max(abs(r["q"][LK]), abs(r["q"][RK])), r["gyro_body"][1]) for r in rise]
    up_t, run = None, 0
    for t, k, gy in knee:
        run = run + 1 if k < SIT_KNEE_MIN and abs(gy) < 1.0 else 0
        if run >= 15 and up_t is None:
            up_t = round(t - knee[0][0], 2)
    t0_trace = os.path.getmtime(trace) - tr[-1]["t"] if tr else 0.0  # wall time of trace t = 0
    tilt_up = [r["tilt"] for r in tr if r["t"] + t0_trace >= t_up]
    seated = [r["tilt"] for r in tr if t_sit + 3.0 <= r["t"] + t0_trace < t_up]
    out = dict(label=a.label, rep=rep, compensation=not a.no_compensation, refit=a.refit, volt=a.volt,
               manifest=os.path.basename(cfg["mass_manifest"]), to_stand=a.to_stand,
               stalled=any("STALLED" in l for l in open(os.path.join(d, "brain.out"))),
               rise_s=None if hand is None or not rise else round(hand - rise[0]["t"], 2),
               knee_min=round(min(k for _, k, _ in knee), 3) if knee else None,
               knee_up_crossings=sum(1 for (_, k0, _), (_, k1, _) in zip(knee, knee[1:]) if k0 >= 1.0 > k1),
               knee_at_handover=round(knee[-1][1], 3) if knee else None, evidence_up_s=up_t,
               seated_tilt_max=round(max(seated), 1) if seated else None,
               peak_tilt_after_up=round(max(tilt_up), 1) if tilt_up else None,
               fell=bool(tilt_up) and max(tilt_up) > 60.0,
               trace_knee=[(round(t - knee[0][0], 2), round(k, 2)) for t, k, _ in knee[::5]] if knee else [],
               dir=d)
    with open(os.path.join(HERE, "results", "fakepi_seats.jsonl"), "a") as f:
        f.write(json.dumps(out) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("trace_knee", "dir")}), flush=True)


os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
for rep in range(a.reps):
    seat(rep)
