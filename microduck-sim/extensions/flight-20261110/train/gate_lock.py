"""One lock for everything that writes train/ckpt or builds the gate-episode image from it.

flight_eval_modal.py mounts the whole train directory (ckpt included) into its image; Modal aborts the build when a
mounted file changes while it is being read (2026-11-20 01:17: the Kaggle follow-up staged ckpt/t3k_* while the
Modal watcher's batch for m3s_350 / m3s_400 was building, "ckpt/t3k_175/walk61.onnx was modified during build
process", batch EXIT 1). Every watcher takes this lock around its staging step and around its `modal run`, so the two
never overlap; batches from different watchers run one after another.

    from gate_lock import gate_lock, run_batch
    with gate_lock("ts3m-b625 stage"):
        ...stage...
    rc = run_batch(sh, [MODAL, "run", ...], log=..., cwd=..., timeout=..., who="m3s_400")

The lock file is train/logs/gate_submit.lock (logs/ is not mounted); it holds the owner's label, pid and start time.
flock is released by the kernel when the holder dies, so a killed watcher cannot leave it locked.
"""
import fcntl
import os
import time
from contextlib import contextmanager
from pathlib import Path

LOCK = Path(__file__).resolve().parent / "logs/gate_submit.lock"


@contextmanager
def gate_lock(who: str):
    LOCK.parent.mkdir(exist_ok=True)
    with open(LOCK, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        f.truncate()
        f.write(f"{who} pid {os.getpid()} since {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
        f.flush()
        try:
            yield
        finally:
            f.seek(0)
            f.truncate()
            f.flush()
            fcntl.flock(f, fcntl.LOCK_UN)


def run_batch(sh, cmd, log, cwd, timeout, who: str):
    """`modal run` of one gate batch under the lock. A build that still reports a file modified under it (a writer
    outside the watchers, such as an edit of a script in train/) is repeated once."""
    with gate_lock(who):
        rc, _ = sh(cmd, log=log, cwd=cwd, timeout=timeout)
        if rc and "modified during build" in Path(log).read_text():
            Path(str(log) + ".first").write_text(Path(log).read_text())
            time.sleep(20)
            rc, _ = sh(cmd, log=log, cwd=cwd, timeout=timeout)
    return rc
