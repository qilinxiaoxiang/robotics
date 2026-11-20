"""Round 3: follow-up of a Kaggle kernel that holds one teacher run and one student (distillation) run.

  python3 train/detach.py train/logs/<name>.out python3 train/ts3_after_pair.py <kernel run> <teacher run> <teacher tag> \
      <student run> <student tag> <name> [teacher_every=N] [hours=H]

Waits for the kernel (polls every 2 minutes, gives up after H hours, default 3.5), fetches it, stages the student
saves (ts2_stage_student.py -> ckpt/<student tag>_<iter>) and the teacher saves (ts2_stage.sh -> ckpt/<teacher
tag>_<iter>), then scores the chatter gates (ts3_gates.py, episodes on Modal):
  1. the student saves first, on ALL gates including G1 (no --teacher): the student is what goes on the robot;
  2. then the teacher saves (--teacher), every N-th save plus the last (teacher_every, default 1).
No gate batch is submitted when Modal's metered spend reads 50.00 USD or more, or cannot be read (line 51.00).
Polling and file conversion only on the MacBook. Heartbeat: train/logs/<name>_heartbeat.txt, one line per event,
"GATE PASS|FAIL <folder>" per save, last line DONE or FAILED. A teacher/student run that is absent from the kernel
output (kernel with two teachers, a failed arm) is reported and skipped.
"""
import subprocess
import sys
import time
from pathlib import Path

T = Path(__file__).resolve().parent
RL = T.parents[2] / "microduck_rl"
MODAL = "/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal"
GPY = "/Users/xiangzheng/.venvs/microduck-walk/bin/python"
STOP_USD = 50.0
sys.path.insert(0, str(T))
from gate_lock import gate_lock, run_batch  # noqa: E402

kernel, t_run, t_tag, s_run, s_tag, name = sys.argv[1:7]
opts = dict(a.split("=", 1) for a in sys.argv[7:])
EVERY = int(opts.get("teacher_every", 1))
HOURS = float(opts.get("hours", 3.5))
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


def gates(tag, dirs, teacher):
    """Gate episodes for the folders on Modal, then one score per folder. Returns the passing folders."""
    if not dirs:
        return []
    sh(["python3", "train/ts3_gates.py", "spec", tag] + dirs, cwd=T.parent, log=T / f"logs/gates_{tag}_spec.log")
    before = metered()
    try:
        usd = float(before.split()[-1])
    except ValueError:
        usd = None
    if usd is None or usd >= STOP_USD:
        hb(f"gate batch {tag} for {len(dirs)} saves NOT submitted: {before} (stop at {STOP_USD:.2f})")
        return []
    rc = run_batch(sh, [MODAL, "run", "train/flight_eval_modal.py", "--spec", f"train/eval/spec_gate_{tag}.json"],
                   cwd=T.parent, log=T / f"logs/gates_{tag}_run.log", timeout=3600, who=f"{name} batch {tag}")
    hb(f"gate episodes {tag} ({len(dirs)} saves) EXIT {rc}; {before} -> {metered()}")
    ok = []
    for d in dirs:
        log = T / f"logs/gates_{d}_score.log"
        rc, out = sh([GPY, "train/ts3_gates.py", "score", d] + (["--teacher"] if teacher else []), cwd=T.parent, log=log)
        lines = out.splitlines()
        fails = [x for x in lines if x.startswith("FAIL")]
        miss = [x for x in lines if x.startswith("MISSING") and not (teacher and "G1" in x)]
        if rc == 0:
            ok.append(d)
            hb(f"GATE PASS {d} ({'teacher, G2 to G5' if teacher else 'student, all gates'}; logs/gates_{d}_score.log)")
        else:
            first = (fails or miss or ["no verdict line"])[0][:150]
            hb(f"GATE FAIL {d} ({len(fails)} failed, {len(miss)} missing lines; first: {first})")
    return ok


def main():
    HB.write_text(time.strftime("%Y-%m-%dT%H:%M:%S ") + f"watch START kernel microduck-{kernel}: teacher {t_run} -> {t_tag}_*, "
                  f"student {s_run} -> {s_tag}_*, teacher every {EVERY}\n")
    end, st = time.time() + HOURS * 3600, ""
    if opts.get("modal"):
        # modal=1: the student run is a Modal app (microduck-flight-<kernel run>, Volume of the same name) instead of
        # a Kaggle kernel: wait until the app is no longer live, then download its saves to where the staging reads
        import json
        vol, dest = f"microduck-flight-{kernel}", T / "kaggle/out" / kernel / "runs" / s_run
        dest.mkdir(parents=True, exist_ok=True)
        while time.time() < end:
            rc, out = sh([MODAL, "app", "list", "--json"], timeout=300)
            try:
                live = [x for x in json.loads(out) if x.get("description") == vol and x.get("state") != "stopped"]
            except (ValueError, TypeError):
                live = None
            sh([MODAL, "volume", "get", "--force", vol, f"runs/{s_run}/progress.json", str(dest / "progress.json")])
            try:
                pr = json.loads((dest / "progress.json").read_text())
                st = f"it {pr.get('iter')} it/s {pr.get('it_per_s')} loss {pr.get('loss')} by_load {pr.get('by_load')}"
            except (OSError, ValueError):
                st = "no progress.json yet"
            hb(f"modal {vol} {'live' if live else 'not live' if live is not None else 'app list unread'}; {st}"[:600])
            if live == []:
                break
            time.sleep(300)
        else:
            hb(f"FAILED app still live after {HOURS} h")
            return 1
        rc, out = sh([MODAL, "volume", "ls", vol, f"runs/{s_run}", "--json"])
        names = sorted(Path(e["filename"]).name for e in json.loads(out)) if rc == 0 else []
        for f in [n for n in names if n.startswith("model_") or n in ("progress.json", "progress.csv", "run_record.json")]:
            sh([MODAL, "volume", "get", "--force", vol, f"runs/{s_run}/{f}", str(dest / f)])
        hb(f"downloaded {len(list(dest.glob('model_[0-9]*.onnx')))} student saves from {vol}")
    while not opts.get("modal") and time.time() < end:
        rc, out = sh(["python3", "cmu/finetune/flight/kaggle_flight.py", "status", kernel], cwd=RL, timeout=300)
        st = ([x for x in out.splitlines() if "outdated" not in x] or [""])[-1][:160]
        hb(f"kaggle {st}")
        if any(k in st for k in ("COMPLETE", "ERROR", "CANCEL")):
            break
        time.sleep(120)
    else:
        if not opts.get("modal"):
            hb(f"FAILED kernel not finished after {HOURS} h")
            return 1
    if not opts.get("modal"):
        rc, _ = sh(["python3", "cmu/finetune/flight/kaggle_flight.py", "fetch", kernel], cwd=RL, log=T / f"logs/fetch_{kernel}.log",
                   timeout=1800)
        hb(f"fetch EXIT {rc}")
        rc, out = sh(["python3", "cmu/finetune/flight/kaggle_flight.py", "quota"], cwd=RL, timeout=300)
        hb("quota after kernel: " + " ".join(([x for x in out.splitlines() if x.startswith("GPU")] or ["unread"])[0].split()))
    runs = T / "kaggle/out" / kernel / "runs"
    sdirs, tdirs = [], []
    if (runs / s_run).is_dir():
        with gate_lock(f"{name} stage student"):  # staging writes ckpt/, which every gate batch mounts (gate_lock.py)
            rc, out = sh(["python3", "train/ts2_stage_student.py", kernel, s_run, s_tag], cwd=T.parent)
        sdirs = out.split() if rc == 0 else []
        hb(f"student staged {len(sdirs)}: {' '.join(sdirs)}" if rc == 0 else f"student staging EXIT {rc}: {out[-200:]}")
    else:
        hb(f"student run {s_run} absent from the kernel output")
    if (runs / t_run).is_dir():
        with gate_lock(f"{name} stage teacher"):
            rc, out = sh(["zsh", "train/ts2_stage.sh", kernel, t_run, t_tag], cwd=T.parent, timeout=1800)
        tdirs = [x for x in out.split() if x.startswith(t_tag + "_")]
        hb(f"teacher staged {len(tdirs)}: {' '.join(tdirs)}")
    else:
        hb(f"teacher run {t_run} absent from the kernel output")
    if not sdirs and not tdirs and "student2" not in opts:
        hb("FAILED nothing staged")
        return 1
    if "student2" in opts:  # a second student run in the same kernel: student2=<run>:<tag>
        run2, tag2 = opts["student2"].split(":")
        if (runs / run2).is_dir():
            with gate_lock(f"{name} stage student 2"):
                rc, out = sh(["python3", "train/ts2_stage_student.py", kernel, run2, tag2], cwd=T.parent)
            more = out.split() if rc == 0 else []
            hb(f"student 2 staged {len(more)}: {' '.join(more)}")
            sdirs += more
        else:
            hb(f"student run {run2} absent from the kernel output")
    s_ok = gates(f"{name}_s", sdirs, teacher=False)
    tmin = int(opts.get("teacher_min", 0))  # saves below this iteration are not scored (critic warm-up: actor frozen)
    tdirs = [d for d in tdirs if int(d.rsplit("_", 1)[1]) >= tmin]
    pick = [d for i, d in enumerate(tdirs) if (i + 1) % EVERY == 0 or i == len(tdirs) - 1]
    t_ok = gates(f"{name}_t", pick, teacher=True)
    hb(f"students passing all gates: {' '.join(s_ok) or 'none'}; teachers passing: {' '.join(t_ok) or 'none'}")
    hb("DONE")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # the heartbeat must end with a verdict
        hb(f"FAILED {type(e).__name__}: {e}")
        raise
