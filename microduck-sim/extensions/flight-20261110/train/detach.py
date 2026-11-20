"""Start a command in its own session, detached from the calling shell (parent becomes launchd), output to a log.

  python3 train/detach.py <log file> <command> [args ...]

For light watchers on the MacBook that must outlive a session's turn (2026-11-19: a session's background shells are
stopped about five minutes after the turn ends). Prints the pid.
"""
import subprocess
import sys

log = open(sys.argv[1], "ab")
p = subprocess.Popen(sys.argv[2:], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
print(p.pid)
