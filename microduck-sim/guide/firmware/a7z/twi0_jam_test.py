"""Touch bus (TWI0) onset test, FAULTS.json touch-twi0-jam T1 and T2. Runs on the A7Z as root, piped over ssh:

  ssh a7z 'sudo -n python3 - --condition capture --minutes 5' < twi0_jam_test.py

Conditions: idle (nothing added), capture (4-channel microphone capture as namecall runs it), load (four busy
processes at nice 0, about namecall's CPU), both. With no brain running it reads the XIAO itself at the brain's 50 Hz;
with a brain running it only watches, so the brain's own reads are the traffic. It counts TWI0 kernel error lines
(/dev/kmsg from now on), failed reads and wedges (10 failed reads in a row), and at each wedge records the line state
register (TWI_LCR, base 0x02510000 + 0x20: bit 4 SDA, bit 5 SCL, per the Allwinner TWI register map; the first idle
sample checks the reading). --restart writes "RS" at a wedge (touch_main.cpp since 2026-10-31) and times the recovery.
Prints one JSON summary line and never reads the brain's log (2026-10-30: parsing it here stalled the brain)."""
import argparse
import fcntl
import glob
import json
import mmap
import os
import struct
import subprocess
import time

ADDR, BLOCK, PERIOD, WEDGE = 0x2A, 24, 0.02, 10
TWI0_BASE, LCR = 0x02510000, 0x20


def bus_path():
    for n in glob.glob("/sys/bus/i2c/devices/i2c-*/of_node"):
        if os.path.realpath(n).endswith("/twi@2510000"):
            return "/dev/" + n.split("/")[-2]
    raise SystemExit("no TWI0 bus (twi@2510000)")


def line_state():
    """(raw LCR, SDA high, SCL high) or the error text."""
    try:
        fd = os.open("/dev/mem", os.O_RDONLY | os.O_SYNC)
        try:
            m = mmap.mmap(fd, 4096, mmap.MAP_SHARED, mmap.PROT_READ, offset=TWI0_BASE)
            v = struct.unpack_from("<I", m, LCR)[0]
            m.close()
        finally:
            os.close(fd)
        return {"lcr": hex(v), "sda_high": bool(v & 0x10), "scl_high": bool(v & 0x20)}
    except OSError as e:
        return {"error": str(e)}


class Kmsg:
    """TWI0 error lines in the kernel log from the moment this opens."""

    def __init__(self):
        self.fd = os.open("/dev/kmsg", os.O_RDONLY | os.O_NONBLOCK)
        os.lseek(self.fd, 0, os.SEEK_END)
        self.count = 0

    def poll(self):
        while True:
            try:
                rec = os.read(self.fd, 8192)
            except BlockingIOError:
                return self.count
            except OSError:  # EPIPE: records overwritten while we were away; keep reading
                continue
            if b"2510000.twi" in rec:
                self.count += 1


def start_condition(cond):
    procs, notes = [], []
    if cond in ("capture", "both"):
        p = subprocess.Popen(["arecord", "-q", "-D", "hw:0,0", "-c", "4", "-r", "48000", "-f", "S32_LE", "-t", "raw",
                              "/dev/null"], stderr=subprocess.PIPE)
        time.sleep(1.0)
        if p.poll() is not None:
            notes.append("capture not started (device busy: namecall holds it, so capture is on anyway): "
                         + p.stderr.read().decode(errors="replace").strip()[:120])
        else:
            procs.append(p)
    if cond in ("load", "both"):
        procs += [subprocess.Popen(["python3", "-c", "while True: pass"]) for _ in range(4)]
    return procs, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=("idle", "capture", "load", "both"), required=True)
    ap.add_argument("--minutes", type=float, default=5.0)
    ap.add_argument("--restart", action="store_true", help="write RS to the XIAO at a wedge and time the recovery")
    args = ap.parse_args()
    path = bus_path()
    brain = subprocess.run(["pgrep", "-f", "walk_wired.py"], stdout=subprocess.DEVNULL).returncode == 0
    out = {"condition": args.condition, "minutes": args.minutes, "bus": path, "brain_running": brain,
           "namecall_running": subprocess.run(["pgrep", "-f", "namecall.py"], stdout=subprocess.DEVNULL).returncode == 0,
           "idle_line_state": line_state(), "start": time.strftime("%Y-%m-%d %H:%M:%S")}
    kmsg = Kmsg()
    procs, out["notes"] = start_condition(args.condition)
    fd = None
    if not brain:
        fd = os.open(path, os.O_RDWR)
        fcntl.ioctl(fd, 0x0703, ADDR)
    reads = fails = in_row = 0
    wedges, wedged_at = [], None
    end = time.monotonic() + args.minutes * 60
    try:
        while time.monotonic() < end:
            t = time.monotonic()
            if fd is not None:
                reads += 1
                try:
                    ok = len(os.read(fd, BLOCK)) == BLOCK
                except OSError:
                    ok = False
                if ok:
                    if wedged_at is not None:
                        wedges[-1]["recovered_after_s"] = round(t - wedged_at, 2)
                        wedged_at = None
                    in_row = 0
                else:
                    fails += 1
                    in_row += 1
                    if in_row == WEDGE:
                        wedged_at = t
                        w = {"t": time.strftime("%H:%M:%S"), "line_state": line_state(), "kernel_lines": kmsg.poll()}
                        if args.restart:
                            try:
                                os.write(fd, b"RS")
                                w["restart_sent"] = True
                            except OSError as e:
                                w["restart_sent"] = f"refused: {e}"
                        wedges.append(w)
            else:
                kmsg.poll()
            time.sleep(max(0.0, PERIOD - (time.monotonic() - t)))
    finally:
        for p in procs:
            p.terminate()
    out.update(reads=reads, failed_reads=fails, wedges=wedges, still_wedged=wedged_at is not None,
               kernel_twi0_lines=kmsg.poll(), end=time.strftime("%Y-%m-%d %H:%M:%S"))
    line = json.dumps(out)
    os.makedirs("/home/radxa/duck-logs", exist_ok=True)
    with open(f"/home/radxa/duck-logs/twi0_test_{time.strftime('%m%d-%H%M%S')}_{args.condition}.json", "w") as f:
        f.write(line + "\n")
    print(line, flush=True)


if __name__ == "__main__":
    main()
