"""Touch-bus onset cells (FAULTS.json touch-twi0-jam T1): with the brain as the only touch reader, run timed cells with
microphone capture on or off while Shawn grips the head or not, and count TWI0 kernel error lines and 'Arbitration
lost' onsets per cell. Runs on the A7Z as root:

  ssh a7z 'sudo -n python3 -u - --start HH:MM:SS' < twi0_cells_test.py

Cells, 2 min each from --start: 1 capture off / hands off, 2 capture off / grip, 3 capture on / grip,
4 capture on / hands off. Capture is what namecall runs: a silent aplay keepalive, then arecord 4 ch 48 kHz on hw:0,0.
Prints one line per cell and a JSON summary."""
import argparse
import json
import os
import subprocess
import time

CELLS = [("capture off, hands off", False), ("capture off, grip", False), ("capture on, grip", True),
         ("capture on, hands off", True)]


def drain(fd, counts):
    while True:
        try:
            rec = os.read(fd, 8192)
        except BlockingIOError:
            return
        except OSError:  # EPIPE when the ring overwrote unread records
            continue
        if b"2510000" in rec and b"probe success" not in rec and b"dummy regulator" not in rec:
            counts["lines"] += 1
            counts["arbitration"] += b"Arbitration lost" in rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="wall-clock HH:MM:SS for cell 1")
    ap.add_argument("--cell-s", type=float, default=120.0)
    args = ap.parse_args()
    t0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d ") + args.start, "%Y-%m-%d %H:%M:%S"))
    fd = os.open("/dev/kmsg", os.O_RDONLY | os.O_NONBLOCK)
    os.lseek(fd, 0, os.SEEK_END)
    while time.time() < t0:
        time.sleep(0.2)
    procs, out = [], []
    try:
        for i, (name, capture) in enumerate(CELLS):
            if capture and not procs:
                procs.append(subprocess.Popen(["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-c", "2", "-r", "48000",
                                               "/dev/zero"]))
                time.sleep(0.3)
                procs.append(subprocess.Popen(["arecord", "-q", "-D", "hw:0,0", "-c", "4", "-r", "48000", "-f",
                                               "S32_LE", "-t", "raw", "/dev/null"]))
            os.lseek(fd, 0, os.SEEK_END)
            counts = {"lines": 0, "arbitration": 0}
            end = t0 + (i + 1) * args.cell_s
            while time.time() < end:
                drain(fd, counts)
                time.sleep(0.2)
            drain(fd, counts)
            row = {"cell": i + 1, "name": name, "from": time.strftime("%H:%M:%S", time.localtime(end - args.cell_s)),
                   "capture_running": capture and all(p.poll() is None for p in procs), **counts}
            out.append(row)
            print(json.dumps(row), flush=True)
    finally:
        for p in procs:
            p.terminate()
    print(json.dumps({"cells": out}), flush=True)


if __name__ == "__main__":
    main()
