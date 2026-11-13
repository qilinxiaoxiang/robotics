#!/usr/bin/env python3
"""Mac mini side of aws_train.py: push code (and resume state) into one AWS training instance, then pull its outputs.

Started by `aws_train.py launch` under nohup on the Mac mini, one process per instance. Standard library only, no AWS
credentials: it talks to the instance over SSH with the microduck-train key, and the instance's security group admits
SSH only from the Mac mini's public address.

  1. wait for SSH (the boot wrapper creates /opt/mdt/ctl), upload bundle/src.tgz and bundle/assets.tgz;
     with --resume also upload the mirror's out/ (checkpoints of the earlier attempts); then touch ctl/ready
  2. every --interval s: rsync /opt/mdt/out/ -> <dir>/out/ (no --delete: earlier attempts' files stay);
     at once when the instance reports a spot interruption notice
  3. when out/DONE arrives: final pull, touch ctl/ack (the instance then powers off), exit
  4. exit when SSH has failed for --gone-s after a first contact (instance terminated or interrupted), or at --life-s

State for aws_train.py status: <dir>/puller.json; log: <dir>/puller.log.
`--once` does a single pull and exits (used by `aws_train.py stop` before terminating).
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="run mirror directory on the Mac mini")
    ap.add_argument("--host", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--attempt", default="1")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--interval", type=float, default=60)
    ap.add_argument("--life-s", type=float, default=6 * 3600)
    ap.add_argument("--gone-s", type=float, default=600)
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    d = Path(a.dir).expanduser()
    out = d / "out"
    out.mkdir(parents=True, exist_ok=True)
    kh = d / "known_hosts"
    ssh_opt = ["-i", str(Path(a.key).expanduser()), "-o", "StrictHostKeyChecking=accept-new", "-o", f"UserKnownHostsFile={kh}",
               "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=15", "-o", "BatchMode=yes", "-o", "LogLevel=ERROR"]
    tgt = f"ubuntu@{a.host}"
    rsh = "ssh " + " ".join(ssh_opt)  # rsync splits -e on spaces; none of these paths contain one
    log_f = open(d / "puller.log", "a")
    state = dict(attempt=a.attempt, host=a.host, started=time.strftime("%FT%T"), phase="connecting", pulls=0,
                 last_pull=None, last_error=None, pid=None)

    def log(msg):
        log_f.write(f"{time.strftime('%FT%T')} [{a.attempt}] {msg}\n")
        log_f.flush()

    def save():
        if not a.once:
            (d / "puller.json").write_text(json.dumps(state, indent=1))

    def sh(cmd, timeout=600):
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()[-600:]

    def ssh(remote, timeout=60):
        return sh(["ssh", *ssh_opt, tgt, remote], timeout)

    def pull():
        rc, msg = sh(["rsync", "-a", "--partial", "-e", rsh, f"{tgt}:/opt/mdt/out/", f"{out}/"])
        if rc == 0:
            state["pulls"] += 1
            state["last_pull"] = time.strftime("%FT%T")
            state["last_error"] = None
        else:
            state["last_error"] = msg
        save()
        return rc == 0

    if a.once:
        ok = pull()
        log(f"single pull {'ok' if ok else 'failed: ' + str(state['last_error'])}")
        sys.exit(0 if ok else 1)

    import os
    state["pid"] = os.getpid()
    # markers of an earlier attempt must not end this one, and its boot records must survive the new instance's
    for stale in ("DONE", "INTERRUPTED", "events.log", "setup.log", "status.json"):
        if (out / stale).exists():
            (out / stale).rename(out / f"{stale}.before-attempt-{a.attempt}")
    t0 = time.time()
    log(f"start host {a.host} resume {a.resume}")
    save()

    # 1. first contact and code upload
    while True:
        rc, msg = ssh("test -d /opt/mdt/ctl && test -d /opt/mdt/in")
        if rc == 0:
            break
        if time.time() - t0 > 900:
            state.update(phase="never_reached", last_error=msg)
            save()
            log(f"no SSH within 15 min: {msg}")
            sys.exit(2)
        time.sleep(10)
    state["phase"] = "uploading"
    save()
    for f in ("src.tgz", "assets.tgz"):
        rc, msg = sh(["rsync", "-a", "-e", rsh, str(d / "bundle" / f), f"{tgt}:/opt/mdt/in/{f}"], 1800)
        if rc:
            state.update(phase="upload_failed", last_error=msg)
            save()
            log(f"upload {f} failed: {msg}")
            sys.exit(3)
    if a.resume:
        rc, msg = sh(["rsync", "-a", "-e", rsh, "--exclude", "DONE*", "--exclude", "INTERRUPTED*", "--exclude", "status.json",
                      "--exclude", "events.log", "--exclude", "setup.log", f"{out}/", f"{tgt}:/opt/mdt/out/"], 3600)
        if rc:
            state.update(phase="upload_failed", last_error=msg)
            save()
            log(f"resume upload failed: {msg}")
            sys.exit(3)
        log("resume state uploaded")
    ssh("touch /opt/mdt/ctl/ready")
    state["phase"] = "pulling"
    save()
    log("code ready")

    # 2-4. pull loop
    last_ok = time.time()
    next_pull = 0.0
    while True:
        now = time.time()
        if now - t0 > a.life_s:
            pull()
            state["phase"] = "life_limit"
            save()
            log("life limit reached")
            sys.exit(0)
        rc, msg = ssh("test -f /opt/mdt/out/DONE && echo done; test -f /opt/mdt/out/INTERRUPTED && echo int; true", 30)
        if rc == 0:
            last_ok = now
            state["last_contact"] = time.strftime("%FT%T")
            if "done" in msg or "int" in msg or now >= next_pull:
                if pull():
                    next_pull = now + a.interval
            if "done" in msg and (out / "DONE").exists():
                ssh("touch /opt/mdt/ctl/ack")
                state["phase"] = "finished"
                save()
                log(f"final pull done, exit code {(out / 'DONE').read_text().strip()}; ack sent")
                sys.exit(0)
        elif now - last_ok > a.gone_s:
            state.update(phase="instance_gone", last_error=msg)
            save()
            log(f"no SSH for {a.gone_s:.0f} s: {msg}")
            sys.exit(0)
        time.sleep(10)


if __name__ == "__main__":
    main()
