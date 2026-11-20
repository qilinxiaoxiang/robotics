"""Round 3, 2026-11-20: watcher of one Modal student run that scores every save AS IT LANDS (ts3_after_pair.py modal=1
scores only after the app has ended).

  python3 train/detach.py train/logs/<name>.out python3 train/ts3_rl_watch.py <run> <tag> <name> [hours=4] [start_falls=<f>]

Every 3 minutes: is the app microduck-flight-<run> live; the run's progress.json; the saves on its Volume. A new save
(model_<it>.onnx and .pt) is downloaded to kaggle/out/<run>/runs/<run>/, staged as ckpt/<tag>_<it> (ts2_stage_student.py,
under the gate lock) and scored on all gates including G1 (ts3_gates.py; episodes on Modal through gate_lock.run_batch,
which holds the gate lock and the container cap). No gate batch at metered 50.00 USD or more, or when the bill
cannot be read. Stop rule (reported, the stop itself is done by hand): "ALERT" when the student's falls per env-minute
at a save are above the start's (start_falls, default: the first reading) for two saves in a row.
Polling and file conversion only on the MacBook. Heartbeat train/logs/<name>_heartbeat.txt, "GATE PASS|FAIL <folder>"
per save, last line DONE or FAILED.
"""
import json
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

run, tag, name = sys.argv[1:4]
opts = dict(a.split("=", 1) for a in sys.argv[4:])
HOURS = float(opts.get("hours", 4))
HB = T / f"logs/{name}_heartbeat.txt"
VOL = f"microduck-flight-{run}"
DEST = T / "kaggle/out" / run / "runs" / run


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


def score(d):
    """gate episodes for one folder on Modal, then its score"""
    gtag = f"{name}_{d.rsplit('_', 1)[1]}"
    sh(["python3", "train/ts3_gates.py", "spec", gtag, d], cwd=T.parent, log=T / f"logs/gates_{gtag}_spec.log")
    before = metered()
    try:
        usd = float(before.split()[-1])
    except ValueError:
        usd = None
    if usd is None or usd >= STOP_USD:
        hb(f"gate batch {gtag} NOT submitted: {before} (stop at {STOP_USD:.2f})")
        return
    rc = run_batch(sh, [MODAL, "run", "train/flight_eval_modal.py", "--spec", f"train/eval/spec_gate_{gtag}.json"],
                   cwd=T.parent, log=T / f"logs/gates_{gtag}_run.log", timeout=3600, who=f"{name} batch {gtag}")
    hb(f"gate episodes {gtag} EXIT {rc}; {before} -> {metered()}")
    rc, out = sh([GPY, "train/ts3_gates.py", "score", d], cwd=T.parent, log=T / f"logs/gates_{d}_score.log")
    lines = out.splitlines()
    fails = [x for x in lines if x.startswith("FAIL")]
    miss = [x for x in lines if x.startswith("MISSING")]
    if rc == 0:
        hb(f"GATE PASS {d} (student, all gates; logs/gates_{d}_score.log)")
    else:
        hb(f"GATE FAIL {d} ({len(fails)} failed, {len(miss)} missing lines): " + " | ".join(x[:110] for x in (fails or miss)[:6]))


def main():
    HB.write_text(time.strftime("%Y-%m-%dT%H:%M:%S ") + f"watch START Modal run {run} -> {tag}_*, every save scored as it lands\n")
    DEST.mkdir(parents=True, exist_ok=True)
    end, done, falls, start_falls = time.time() + HOURS * 3600, set(), [], float(opts["start_falls"]) if "start_falls" in opts else None
    dead = 0
    while time.time() < end:
        rc, out = sh([MODAL, "app", "list", "--json"], timeout=300)
        try:
            live = [x for x in json.loads(out) if x.get("description") == VOL and x.get("state") != "stopped"]
        except (ValueError, TypeError):
            live = None
        sh([MODAL, "volume", "get", "--force", VOL, f"runs/{run}/progress.json", str(DEST / "progress.json")])
        try:
            pr = json.loads((DEST / "progress.json").read_text())
            st = f"it {pr.get('iter')} it/s {pr.get('it_per_s')} loss {pr.get('loss')} student {pr.get('student')} rl {pr.get('rl')}"
        except (OSError, ValueError):
            pr, st = {}, "no progress.json yet"
        hb(f"modal {VOL} {'live' if live else 'not live' if live is not None else 'app list unread'}; {st}"[:900])
        rc, out = sh([MODAL, "volume", "ls", VOL, f"runs/{run}", "--json"])
        try:
            names = sorted(Path(e["filename"]).name for e in json.loads(out)) if rc == 0 else []
        except (ValueError, TypeError, KeyError):
            names = []
        its = sorted(int(n[6:-5]) for n in names if n.startswith("model_") and n.endswith(".onnx") and n[6:-5].isdigit()
                     and f"model_{n[6:-5]}.pt" in names)
        new = [i for i in its if i not in done and i > 0 and i <= int(pr.get("iter") or 0)]
        for it in new:
            for f in (f"model_{it}.onnx", f"model_{it}.pt", "progress.csv", "run_record.json"):
                sh([MODAL, "volume", "get", "--force", VOL, f"runs/{run}/{f}", str(DEST / f)])
            if not (DEST / f"model_{it}.onnx").exists() or not (DEST / f"model_{it}.pt").exists():
                hb(f"save {it} not downloaded yet")
                continue
            with gate_lock(f"{name} stage {it}"):  # staging writes ckpt/, which every gate batch mounts
                rc, out = sh(["python3", "train/ts2_stage_student.py", run, run, tag], cwd=T.parent)
            d = f"{tag}_{it}"
            if rc != 0 or d not in out.split():
                hb(f"staging of save {it} EXIT {rc}: {out[-200:]}")
                continue
            done.add(it)
            f_now = (pr.get("student") or {}).get("falls_per_env_min")
            hb(f"save {it} staged as {d}; student falls per env-minute at the last reading {f_now}")
            if f_now is not None:
                if start_falls is None:
                    start_falls = f_now
                falls.append(f_now)
                if len(falls) >= 2 and falls[-1] > start_falls and falls[-2] > start_falls:
                    hb(f"ALERT falls per env-minute above the start ({start_falls}) for two saves in a row: {falls[-2]}, {falls[-1]}")
            score(d)
        if live == []:
            dead += 1
            if dead >= 2 and not [i for i in its if i not in done and i > 0]:
                hb(f"app ended; saves scored: {sorted(done)}")
                hb("DONE")
                return 0
        else:
            dead = 0
        time.sleep(180)
    hb(f"FAILED still waiting after {HOURS} h; saves scored: {sorted(done)}")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # the heartbeat must end with a verdict
        hb(f"FAILED {type(e).__name__}: {e}")
        raise
