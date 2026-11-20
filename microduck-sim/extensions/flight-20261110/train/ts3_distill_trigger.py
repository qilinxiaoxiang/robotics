"""Round 3: start the recurrent student's distillation by itself as soon as a teacher save passes the chatter gates.

  python3 train/detach.py train/logs/ts3_distill_trigger.out python3 train/ts3_distill_trigger.py <hours>

Every 60 s: read train/out/gates/gates_<folder>.json of every teacher folder (tags t3a..t3f from the Kaggle kernels,
m3p / m3q / m3w / m3g from the Modal arms; written by ts3_gates.py score, whichever watcher ran it). For the first
passing save of an arm, at most MAX_KERNELS in all, the hand-over is immediate:
  copy ckpt/<folder>/walk61.onnx (the 68-input teacher) to train/init/ts3t_<folder>.onnx (kaggle_flight.py ships
  every train/init/ts3t_*.onnx), then push one Kaggle kernel microduck-ts3s-<folder>-m with two students of that
  teacher: GPU 0 Mamba (run ts3s-<folder>-m), GPU 1 LSTM (run ts3s-<folder>-l); flight_worker.py --distill, env
  universal5 (audited with universal5t), from scratch, 160 iterations of 100 ticks, dropped ticks 0 to 0.08 (the
  round-2 scratch student's settings, RUNLOG.md 2026-11-18 18:30), saves every 20, --max-hours 2.2.
Training is on Kaggle only (Modal credit, 2026-11-19 20:50). A push is refused while both Kaggle GPU sessions are busy
or when under MIN_QUOTA_H hours of quota are left; a refused push is tried again every minute (logged every 5th time).

Heartbeat: train/logs/ts3_distill_heartbeat.txt ("STUDENT LAUNCHED <kernel> from <folder> ..." per launch, a line
every 10 min otherwise, last line DONE after <hours>). State: train/logs/ts3_distill_launched.json.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

T = Path(__file__).resolve().parent
RL = T.parents[2] / "microduck_rl"
HB = T / "logs/ts3_distill_heartbeat.txt"
STATE = T / "logs/ts3_distill_launched.json"
TAGS = ("t3a", "t3b", "t3c", "t3d", "t3e", "t3f", "m3p", "m3q", "m3w", "m3g")
MAX_KERNELS = 2
MIN_QUOTA_H = 2.4
FLAGS = ("--distill --delta universal5 --manifest /root/assets/manifests/flightpack-none.json --max-iters 160 "
         "--max-hours 2.2 --save-interval 20 --warmup-iters 2 --beta-iters 30 --bptt-steps 100 --epochs 2 "
         "--mb-envs 256 --stop-after 100 --seed 1 --drop-max 0.08").split()


def hb(msg):
    with open(HB, "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + msg + "\n")


def kaggle(*args, timeout=900):
    r = subprocess.run(["python3", "cmu/finetune/flight/kaggle_flight.py", *args], cwd=RL, capture_output=True, text=True, timeout=timeout)
    return r.stdout + r.stderr


def quota_left():
    m = re.search(r"GPU\s+([0-9.]+)h\s+([0-9.]+)h", kaggle("quota", timeout=120))
    return float(m.group(2)) if m else None


def passing():
    """{arm tag: first passing folder}, saves in iteration order"""
    out = {}
    for tag in TAGS:
        files = sorted((T / "out/gates").glob(f"gates_{tag}_*.json"), key=lambda p: int(p.stem.rsplit("_", 1)[1]))
        for p in files:
            try:
                if json.loads(p.read_text()).get("verdict") == "PASS":
                    out[tag] = p.stem[len("gates_"):]
                    break
            except Exception:  # noqa: BLE001
                continue
    return out


def launch(folder):
    base = "ts3s-" + folder.replace("_", "-")
    src = T / "ckpt" / folder / "walk61.onnx"
    if not src.exists():
        return f"teacher file missing: {src}"
    shutil.copyfile(src, T / "init" / f"ts3t_{folder}.onnx")
    q = quota_left()
    if q is None or q < MIN_QUOTA_H:
        return f"Kaggle quota left {q} h (needs {MIN_QUOTA_H}): not pushed"
    f = ["--teacher-onnx", f"/root/assets/init/ts3t_{folder}.onnx"] + FLAGS
    out = kaggle("push", "run", "--run-name", f"{base}-m", "--pair-run-name", f"{base}-l", "--", *f, "--core", "mamba",
                 "--", *f, "--core", "lstm")
    (T / f"logs/launch_{base}.log").write_text(out)
    if "successfully pushed" not in out:
        why = [x for x in out.splitlines() if re.search("error|gate|refus|maximum", x, re.I)]
        return f"push of {base} refused: {(why[0] if why else out[-160:])[:160]}"
    return (f"STUDENT LAUNCHED kernel microduck-{base}-m from {folder}: Mamba {base}-m + LSTM {base}-l, 160 iterations, "
            f"--max-hours 2.2, Kaggle quota left before {q} h")


def main():
    t_end = time.time() + float(sys.argv[1]) * 3600
    done = json.loads(STATE.read_text()) if STATE.exists() else {}
    tries = {}
    hb(f"trigger START pid {os.getpid()}, already launched {done}")
    n = 0
    while time.time() < t_end:
        n += 1
        ok = passing()
        for tag, folder in ok.items():
            if tag in done:
                continue
            if len([v for v in done.values() if v.get("launched")]) >= MAX_KERNELS:
                done[tag] = dict(folder=folder, launched=False)
                hb(f"GATE PASS {folder} seen, not distilled: {MAX_KERNELS} student kernels already launched")
            else:
                msg = launch(folder)
                tries[tag] = tries.get(tag, 0) + 1
                if msg.startswith("STUDENT LAUNCHED"):
                    hb(msg)
                    done[tag] = dict(folder=folder, launched=True, time=time.strftime("%Y-%m-%dT%H:%M:%S"))
                elif tries[tag] % 5 == 1:
                    hb(f"GATE PASS {folder}; {msg} (try {tries[tag]})")
            STATE.write_text(json.dumps(done, indent=1))
        if n % 10 == 1:
            hb(f"waiting: {len(list((T / 'out/gates').glob('gates_[tm]3?_*.json')))} teacher saves scored, passing {ok}, launched {sorted(done)}")
        time.sleep(60)
    hb("DONE")


if __name__ == "__main__":
    main()
