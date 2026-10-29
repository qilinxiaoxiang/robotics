"""Run `claude -p` on the Mac that is logged in, for a runner on a machine that is not.

The Mac mini has no `claude` CLI and a non-interactive ssh shell on the MacBook cannot read its Keychain ("Not logged
in"), so a process started here from a GUI-session shell serves the calls through a spool directory:

    serve:  pet/.venv/bin/python pet/mind/claude_bridge.py serve            # on the logged-in Mac, keep it running
    call:   echo '["-p", "--model", ...]' | python3 pet/mind/claude_bridge.py call   # what the remote shim runs over ssh

`call` writes the argument list as <id>.req.json into the spool, waits for <id>.resp.json, prints claude's stdout and
exits with claude's exit code. `serve` polls the spool twice a second, runs one request at a time with cwd /tmp and
CLAUDE_CODE_ENTRYPOINT=pet-mind, niced, and removes the request when answered. Nothing persists: stop `serve` and the
bridge is gone. The remote shim (`~/sims/<dir>/bin/claude` on the Mac mini) is:

    #!/bin/zsh
    python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "$@" | \\
        ssh -o BatchMode=yes xiangzheng@<macbook> python3 /Users/xiangzheng/code/robotics/pet/mind/claude_bridge.py call
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

SPOOL = Path(os.environ.get("CLAUDE_BRIDGE_SPOOL", "/tmp/claude-bridge"))
CLAUDE = os.environ.get("CLAUDE_BRIDGE_EXE", os.path.expanduser("~/.local/bin/claude"))
CALL_TIMEOUT_S = 90.0


def serve():
    SPOOL.mkdir(parents=True, exist_ok=True)
    print(f"claude bridge serving {SPOOL} with {CLAUDE}", flush=True)
    while True:
        reqs = sorted(SPOOL.glob("*.req.json"), key=lambda p: p.stat().st_mtime)
        if not reqs:
            time.sleep(0.5)
            continue
        req = reqs[0]
        rid = req.name[: -len(".req.json")]
        try:
            args = json.loads(req.read_text())
        except (OSError, ValueError) as e:
            req.unlink(missing_ok=True)
            print(f"{rid}: bad request ({e})", flush=True)
            continue
        t0 = time.monotonic()
        try:
            r = subprocess.run(["nice", "-n", "19", CLAUDE, *args], capture_output=True, text=True,
                               timeout=CALL_TIMEOUT_S, cwd="/tmp",
                               env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "pet-mind"})
            resp = {"returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
        except (subprocess.TimeoutExpired, OSError) as e:
            resp = {"returncode": 124, "stdout": "", "stderr": f"claude bridge: {e}"}
        tmp = SPOOL / f"{rid}.resp.tmp"
        tmp.write_text(json.dumps(resp))
        os.replace(tmp, SPOOL / f"{rid}.resp.json")
        req.unlink(missing_ok=True)
        print(f"{rid}: exit {resp['returncode']} in {time.monotonic() - t0:.1f} s", flush=True)


def call() -> int:
    SPOOL.mkdir(parents=True, exist_ok=True)
    args = json.load(sys.stdin)
    rid = f"{time.time():.3f}-{uuid.uuid4().hex[:8]}"
    tmp = SPOOL / f"{rid}.req.tmp"
    tmp.write_text(json.dumps(args))
    os.replace(tmp, SPOOL / f"{rid}.req.json")
    resp_path = SPOOL / f"{rid}.resp.json"
    deadline = time.monotonic() + CALL_TIMEOUT_S + 10
    while time.monotonic() < deadline:
        if resp_path.exists():
            resp = json.loads(resp_path.read_text())
            resp_path.unlink(missing_ok=True)
            sys.stdout.write(resp["stdout"])
            sys.stderr.write(resp["stderr"])
            return int(resp["returncode"])
        time.sleep(0.2)
    (SPOOL / f"{rid}.req.json").unlink(missing_ok=True)
    sys.stderr.write("claude bridge: no server answered (is `claude_bridge.py serve` running on the logged-in Mac?)\n")
    return 125


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "serve":
        serve()
    elif len(sys.argv) == 2 and sys.argv[1] == "call":
        sys.exit(call())
    else:
        sys.exit(__doc__)
