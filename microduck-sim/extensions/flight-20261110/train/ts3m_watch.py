"""Round 3 parallel arms: score the chatter gates on every save of the Modal teacher arms while they still train.

  python3 train/detach.py train/logs/ts3m_watch.out python3 train/ts3m_watch.py <hours> <arm>=<tag> [...]

Every 4 minutes, for each arm (Modal run name = Volume microduck-flight-<arm>): list the Volume, download each new
model_<n>.pt (and model_0.onnx, progress.json) to train/kaggle/out/<arm>/runs/<arm>/ (the layout ts2_stage.sh reads),
stage it as ckpt/<tag>_<n>, write the gate spec for the new folders, run the episodes on Modal CPU
(flight_eval_modal.py) and score them (ts3_gates.py score --teacher). Polling, downloads and file conversion only on
the MacBook. Ends when every arm's iteration has stood still for 15 min and all of its saves are scored, or after <hours>.

Heartbeat: train/logs/ts3m_heartbeat.txt, one line per event; a save that passes writes "GATE PASS <folder>", a save
that fails "GATE FAIL <folder> <n> lines"; last line DONE or FAILED.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

T = Path(__file__).resolve().parent
MODAL = "/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal"
GPY = "/Users/xiangzheng/.venvs/microduck-walk/bin/python"
HB = T / "logs/ts3m_heartbeat.txt"


def hb(msg):
    with open(HB, "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + msg + "\n")


def sh(cmd, log=None, cwd=None, timeout=1500):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, ""
    if log:
        Path(log).write_text(r.stdout + r.stderr)
    return r.returncode, r.stdout


def metered():
    rc, out = sh([MODAL, "billing", "summary"])
    for line in out.splitlines():
        if "Metered" in line:
            return " ".join(line.split())
    return "metered unread"


def main():
    hours = float(sys.argv[1])
    arms = dict(a.split("=") for a in sys.argv[2:])
    t_end = time.time() + hours * 3600
    scored = {a: set() for a in arms}   # iterations already scored
    stopped = {a: False for a in arms}
    last = {a: (None, time.time()) for a in arms}  # last iteration seen and when it changed
    hb(f"watch START arms {arms} for {hours} h")
    rnd = 0
    while time.time() < t_end:
        rnd += 1
        for arm, tag in arms.items():
            vol = f"microduck-flight-{arm}"
            rc, out = sh([MODAL, "volume", "ls", vol, f"runs/{arm}", "--json"])
            if rc:
                continue
            names = {Path(e["filename"]).name for e in json.loads(out)}
            dest = T / f"kaggle/out/{arm}/runs/{arm}"
            dest.mkdir(parents=True, exist_ok=True)
            its = sorted(int(n[6:-3]) for n in names if n.startswith("model_") and n.endswith(".pt") and n[6:-3].isdigit())
            new = [i for i in its if i > 0 and i not in scored[arm]]
            for f in ["model_0.onnx", "progress.json"] + [f"model_{i}.pt" for i in new]:
                if f in names and (f == "progress.json" or not (dest / f).exists()):
                    sh([MODAL, "volume", "get", "--force", vol, f"runs/{arm}/{f}", str(dest / f)])
            try:
                pr = json.loads((dest / "progress.json").read_text())
                # progress.json has no end flag: an arm counts as stopped when its iteration has not moved for 15 min
                if pr.get("iter") != last[arm][0]:
                    last[arm] = (pr.get("iter"), time.time())
                stopped[arm] = time.time() - last[arm][1] > 900
                state = (f"it {pr.get('iter')} track_err {pr.get('track_err')} (base {pr.get('track_base')}) "
                         f"it/s {pr.get('it_per_s')} ${pr.get('dollars')}")
            except Exception:  # noqa: BLE001
                state = "no progress.json"
            new = [i for i in new if (dest / f"model_{i}.pt").exists()]
            if not new:
                if rnd % 5 == 1:
                    hb(f"{arm} {state}; saves {its}; nothing new")
                continue
            if not (dest / "model_0.onnx").exists():
                hb(f"{arm} model_0.onnx missing on the Volume, cannot stage {new}")
                continue
            sh(["zsh", str(T / "ts2_stage.sh"), arm, arm, tag], log=T / f"logs/ts3m_stage_{arm}.log")
            dirs = [f"{tag}_{i}" for i in new if (T / f"ckpt/{tag}_{i}/walk61.onnx").exists()]
            if not dirs:
                hb(f"{arm} staging failed for {new} (logs/ts3m_stage_{arm}.log)")
                continue
            stamp = f"{tag}_{new[-1]}"
            sh(["python3", "train/ts3_gates.py", "spec", stamp] + dirs, log=T / f"logs/gates_{stamp}_spec.log", cwd=T.parent)
            before = metered()
            rc, _ = sh([MODAL, "run", "train/flight_eval_modal.py", "--spec", f"train/eval/spec_gate_{stamp}.json"],
                       log=T / f"logs/gates_{stamp}_run.log", cwd=T.parent, timeout=2400)
            hb(f"{arm} {state}; gate episodes for {dirs} EXIT {rc}; {before} -> {metered()}")
            if rc:
                continue
            for d in dirs:
                rc, out = sh([GPY, "train/ts3_gates.py", "score", d, "--teacher"], log=T / f"logs/gates_{d}_score.log", cwd=T.parent)
                fails = sum(1 for line in out.splitlines() if line.startswith("FAIL"))
                hb(f"GATE {'PASS' if rc == 0 else 'FAIL'} {d}" + ("" if rc == 0 else f" {fails} lines") + f" (logs/gates_{d}_score.log)")
                scored[arm].add(int(d.rsplit("_", 1)[1]))
        if all(stopped.values()):
            hb("every arm stopped and scored")
            hb("DONE")
            return
        time.sleep(240)
    hb("FAILED time limit reached with arms still running: " + ", ".join(a for a in arms if not stopped[a]))


if __name__ == "__main__":
    main()
