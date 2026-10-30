#!/usr/bin/env python3
"""Keep the A7Z card from filling: move old duck logs to the Mac, clear caches nobody reads. Runs hourly on the
MacBook (launchd com.shawn.a7z-offload); also by hand: python3 a7z_offload.py [--dry-run].

Each run, when the A7Z answers ssh:
- every file under ~/duck-logs older than AGE_MIN minutes moves to the Mac (rsync, then the A7Z copy is removed only
  after that file transferred): life log segments (life/<day>/*.wav) go to namecall-20261029/recordings/life/<day>/,
  where mine_life.py reads them; everything else goes to ~/Backups/a7z-duck-logs/ under the same relative path.
  Kept on the A7Z: life/life_index.jsonl (copied, the life log appends to it) and the newest brain tick log
  (namecall and the restart check read it), whatever their age.
- caches nobody reads are cleared without a copy: the systemd journal is vacuumed to JOURNAL_MAX, pip and apt
  download caches are emptied.

Every run appends one record to ~/Backups/a7z-duck-logs/offload-runs.jsonl (time, status ok / offline / failed,
files and bytes moved, free space before and after, error text) and rewrites offload-status.json (last success, last
failure, consecutive failures). A failure, or free space under LOW_FREE_GB after a run, raises a macOS notification.
An offline duck is recorded as offline, not as a failure.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HOST = os.environ.get("A7Z_HOST", "a7z")
HERE = os.path.dirname(os.path.abspath(__file__))
LIFE_DST = os.path.join(HERE, "namecall-20261029", "recordings", "life")
BACKUP = os.path.expanduser("~/Backups/a7z-duck-logs")
RUNS = os.path.join(BACKUP, "offload-runs.jsonl")
STATUS = os.path.join(BACKUP, "offload-status.json")
AGE_MIN = 360            # files untouched this long are finished (a brain run writes every 20 ms; segments close in s)
JOURNAL_MAX = "100M"
LOW_FREE_GB = 3.0
SSH = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", "-o", "LogLevel=ERROR"]


def ssh(cmd, timeout=120):
    return subprocess.run(SSH + [HOST, cmd], capture_output=True, text=True, timeout=timeout)


def free_gb():
    r = ssh("df -B1 --output=avail / | tail -1")
    return round(int(r.stdout.strip()) / 1e9, 2) if r.returncode == 0 and r.stdout.strip().isdigit() else None


def candidates():
    """(life_files, other_files) relative to ~/duck-logs, older than AGE_MIN, minus the kept ones."""
    r = ssh(f"cd ~/duck-logs && find . -type f -mmin +{AGE_MIN} -printf '%P\\t%s\\n'; "
            "echo '#NEWEST'; ls -t duck_wired_log_*.jsonl 2>/dev/null | head -1")
    if r.returncode != 0:
        raise RuntimeError(f"listing failed: {r.stderr.strip()[:300]}")
    body, _, newest = r.stdout.partition("#NEWEST")
    newest = newest.strip()
    life, other, size = [], [], 0
    for line in body.splitlines():
        if "\t" not in line:
            continue
        p, s = line.rsplit("\t", 1)
        if p in ("life/life_index.jsonl", newest):
            continue
        size += int(s)
        (life if p.startswith("life/") and p.endswith(".wav") else other).append(p)
    return life, other, size, newest


def move(files, src, dst, dry):
    """rsync these relative paths from HOST:src to dst, removing each source after its transfer."""
    if not files:
        return 0
    os.makedirs(dst, exist_ok=True)
    lst = os.path.join(BACKUP, ".offload-files.txt")
    with open(lst, "w") as f:
        f.write("\n".join(files) + "\n")
    # sudo on the A7Z side: blackbox/ files are written by a root service and only root may remove them
    cmd = ["rsync", "-a", "--remove-source-files", "--rsync-path=sudo -n rsync", f"--files-from={lst}", "-e", " ".join(SSH),
           f"{HOST}:{src}", dst + "/"]
    if dry:
        cmd.insert(1, "--dry-run")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3 * 3600)
    if r.returncode != 0:
        raise RuntimeError(f"rsync {src} -> {dst} exit {r.returncode}: {r.stderr.strip()[-400:]}")
    return len(files)


def clear_caches(dry):
    if dry:
        return "dry run"
    r = ssh(f"sudo -n journalctl --vacuum-size={JOURNAL_MAX} 2>&1 | tail -1; rm -rf ~/.cache/pip; sudo -n apt-get clean")
    if r.returncode != 0:
        raise RuntimeError(f"cache clear failed: {(r.stderr or r.stdout).strip()[-300:]}")
    return r.stdout.strip()[-200:]


def notify(msg):
    subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "Duck log offload"'], capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    os.makedirs(BACKUP, exist_ok=True)
    lock = os.path.join(BACKUP, ".offload.lock")
    try:
        os.mkdir(lock)
    except FileExistsError:
        if time.time() - os.path.getmtime(lock) < 4 * 3600:
            return 0                     # a previous run is still moving files
        os.rmdir(lock)
        os.mkdir(lock)
    rec = dict(t=time.strftime("%Y-%m-%dT%H:%M:%S%z"), dry_run=a.dry_run)
    try:
        if ssh("true", timeout=30).returncode != 0:
            rec["status"] = "offline"
        else:
            rec["free_gb_before"] = free_gb()
            life, other, size, newest = candidates()
            rec["kept_newest"] = newest
            rec["moved_life"] = move(life, "duck-logs/", os.path.dirname(LIFE_DST), a.dry_run) if life else 0
            rec["moved_other"] = move(other, "duck-logs/", BACKUP, a.dry_run)
            rec["moved_mb"] = round(size / 1e6, 1)
            rec["caches"] = clear_caches(a.dry_run)
            rec["free_gb_after"] = free_gb()
            rec["status"] = "ok"
    except Exception as e:           # noqa: BLE001 - every failure is recorded and surfaced
        rec["status"], rec["error"] = "failed", repr(e)[:600]
    finally:
        os.rmdir(lock)
    with open(RUNS, "a") as f:
        f.write(json.dumps(rec) + "\n")
    try:
        st = json.load(open(STATUS))
    except Exception:            # noqa: BLE001 - first run or unreadable status: start fresh
        st = {}
    st["last_run"] = rec
    if rec["status"] == "ok":
        st["last_success"], st["consecutive_failures"] = rec["t"], 0
    elif rec["status"] == "failed":
        st["last_failure"] = rec["t"]
        st["consecutive_failures"] = st.get("consecutive_failures", 0) + 1
    with open(STATUS, "w") as f:
        json.dump(st, f, indent=1)
    if rec["status"] == "failed":
        notify(f"failed ({st['consecutive_failures']} in a row): {rec['error'][:120]}")
    elif rec.get("free_gb_after") is not None and rec["free_gb_after"] < LOW_FREE_GB:
        notify(f"A7Z card still low after offload: {rec['free_gb_after']} GB free")
    print(json.dumps(rec))
    return 1 if rec["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
