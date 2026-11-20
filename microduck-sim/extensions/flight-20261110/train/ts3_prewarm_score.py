"""Round 3: a second, separately named gate reading of student saves with self-prewarm (2026-11-20).

  python3 train/detach.py train/logs/<name>.out python3 train/ts3_prewarm_score.py <name> <N> <wait heartbeat | -> \
      <src folder under ckpt>=<dst folder> [...]
  e.g. ... ts3_prewarm_score.py s3aw 10 - s3a_60=s3aw_60

Each <dst> is a copy of <src> plus a file "prewarm" holding N: flight_eval then steps the student's empty recurrent
state N times on the entry observation (actions discarded) before the first action, in every gate cell. The folders
go through the same gate path as the standard score (ts3_gates.py spec / flight_eval_modal.py / ts3_gates.py score,
the gate lock, 60 containers). G1 is the gate's own computation on the robot states and is not prewarmed.
THE PREWARMED TABLE IS EVIDENCE ABOUT A LOADER CHANGE, NOT A GATE PASS: the verdict of record is the standard score
of <src>. The heartbeat writes "PREWARM READING", never "GATE PASS".
<wait heartbeat>: a heartbeat file whose last line must be DONE before anything is staged (the standard follow-up of
the same run); sources that do not exist then are skipped. No batch is submitted at 50.00 USD metered or more, or
when the bill cannot be read. Heartbeat train/logs/<name>_heartbeat.txt, last line DONE or FAILED.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

T = Path(__file__).resolve().parent
MODAL = "/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal"
GPY = "/Users/xiangzheng/.venvs/microduck-walk/bin/python"
STOP_USD = 50.0
sys.path.insert(0, str(T))
from gate_lock import gate_lock, run_batch  # noqa: E402

name, n, wait = sys.argv[1], int(sys.argv[2]), sys.argv[3]
pairs = [a.split("=", 1) for a in sys.argv[4:]]
HB = T / f"logs/{name}_heartbeat.txt"


def hb(msg):
    with open(HB, "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + msg + "\n")


def sh(cmd, cwd=None, log=None, timeout=900):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, ""
    if log:
        Path(log).write_text(r.stdout + r.stderr)
    return r.returncode, r.stdout + r.stderr


def metered():
    rc, out = sh([MODAL, "billing", "summary"], timeout=120)
    for line in out.splitlines():
        if "Metered" in line:
            return " ".join(line.split())
    return "metered unread"


def main():
    hb(f"START prewarm {n} reading (evidence, not a gate pass) for {[p[0] for p in pairs]}; waiting on {wait}")
    end = time.time() + 5 * 3600
    while wait != "-":
        lines = Path(wait).read_text().splitlines() if Path(wait).exists() else []
        if lines and lines[-1].split(" ", 1)[-1].startswith(("DONE", "FAILED")):
            break
        if time.time() > end:
            hb("FAILED: the awaited heartbeat did not end in 5 h")
            return
        time.sleep(120)
    dirs = []
    with gate_lock(f"{name} staging"):   # train/ckpt is inside the gate image's mount
        for src, dst in pairs:
            if not (T / "ckpt" / src / "walk61.onnx").exists():
                hb(f"skipped {src}: no such save")
                continue
            if (T / "ckpt" / dst).exists():
                shutil.rmtree(T / "ckpt" / dst)
            shutil.copytree(T / "ckpt" / src, T / "ckpt" / dst)
            (T / "ckpt" / dst / "prewarm").write_text(str(n))
            dirs.append(dst)
    if not dirs:
        hb("FAILED: nothing to score")
        return
    sh(["python3", "train/ts3_gates.py", "spec", name] + dirs, cwd=T.parent, log=T / f"logs/gates_{name}_spec.log")
    before = metered()
    try:
        usd = float(before.split()[-1])
    except ValueError:
        usd = None
    if usd is None or usd >= STOP_USD:
        hb(f"FAILED: batch NOT submitted: {before} (stop at {STOP_USD:.2f})")
        return
    rc = run_batch(sh, [MODAL, "run", "train/flight_eval_modal.py", "--spec", f"train/eval/spec_gate_{name}.json"],
                   cwd=T.parent, log=T / f"logs/gates_{name}_run.log", timeout=3600, who=f"{name} prewarm batch")
    hb(f"gate episodes {name} ({len(dirs)} folders) EXIT {rc}; {before} -> {metered()}")
    for d in dirs:
        rc, out = sh([GPY, "train/ts3_gates.py", "score", d], cwd=T.parent, log=T / f"logs/gates_{d}_score.log")
        fails = [x for x in out.splitlines() if x.startswith("FAIL")]
        miss = [x for x in out.splitlines() if x.startswith("MISSING")]
        hb(f"PREWARM READING {d} (prewarm {n}; evidence about a loader change, not a gate pass): {len(fails)} failed, "
           f"{len(miss)} missing lines; logs/gates_{d}_score.log" + (f"; first: {(fails or miss)[0][:150]}" if fails or miss else ""))
    hb("DONE")


if __name__ == "__main__":
    main()
