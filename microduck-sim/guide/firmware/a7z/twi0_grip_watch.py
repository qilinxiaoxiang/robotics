"""Touch-bus watch while Shawn grips the duck's head (FAULTS.json touch-twi0-jam, H1 hand-on-head trigger). Runs on the
A7Z as root with no brain running, until stopped:

  ssh a7z 'sudo -n python3 -u - [--seconds S]' < twi0_grip_watch.py > watch.txt

Reads the 24-byte block through the kernel driver at 50 Hz, as the brain does, and prints one line a second: valid
reads, reads shifted by the 0x55 filler, invalid blocks, failed reads (OSError), the largest pad count (a grip raises
it), the sequence number and the kernel's new TWI0 lines. A run of 10 failed reads prints WEDGE with the line state."""
import argparse
import fcntl
import glob
import mmap
import os
import struct
import time

ADDR = 0x2A


def kernel_bus():
    for n in glob.glob("/sys/bus/i2c/devices/i2c-*/of_node"):
        if os.path.realpath(n).endswith("/twi@2510000"):
            return "/dev/" + n.split("/")[-2]
    raise SystemExit("no kernel bus for twi@2510000")


def lcr():
    fd = os.open("/dev/mem", os.O_RDONLY | os.O_SYNC)
    try:
        m = mmap.mmap(fd, 4096, mmap.MAP_SHARED, mmap.PROT_READ, offset=0x02510000)
        v = struct.unpack_from("<I", m, 0x20)[0]
        m.close()
        return f"LCR {v:#x} SDA {(v >> 4) & 1} SCL {(v >> 5) & 1}"
    finally:
        os.close(fd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=0, help="0 runs until stopped")
    args = ap.parse_args()
    if os.system("pgrep -f '[w]alk_wired.py' >/dev/null") == 0:
        raise SystemExit("a brain is running: stop it first")
    fd = os.open(kernel_bus(), os.O_RDWR)
    fcntl.ioctl(fd, 0x0703, ADDR)
    kmsg = os.open("/dev/kmsg", os.O_RDONLY | os.O_NONBLOCK)
    os.lseek(kmsg, 0, os.SEEK_END)
    t_end = time.monotonic() + args.seconds if args.seconds else None
    run_fail = 0
    while t_end is None or time.monotonic() < t_end:
        c = {"ok": 0, "shift": 0, "bad": 0, "err": 0}
        top, seq, t1 = 0, None, time.monotonic() + 1.0
        while time.monotonic() < t1:
            try:
                raw = os.read(fd, 24)
                v = struct.unpack("<6I", raw)
                s = struct.unpack("<6I", raw[1:] + b"\0")
                if max(v[1:]) <= 0x3FFFFF:
                    c["ok"] += 1; top = max(top, *v[1:]); seq = v[0]; run_fail = 0
                elif raw[0] == 0x55 and max(s[1:]) <= 0x3FFFFF:
                    c["shift"] += 1; top = max(top, *s[1:]); seq = s[0]; run_fail = 0
                else:
                    c["bad"] += 1; run_fail += 1
            except OSError:
                c["err"] += 1; run_fail += 1
            if run_fail == 10:
                print(time.strftime("%H:%M:%S"), "WEDGE", lcr(), flush=True)
            time.sleep(0.02)
        klines = 0
        while True:
            try:
                rec = os.read(kmsg, 4096)
            except BlockingIOError:
                break
            except OSError:  # EPIPE when the ring overwrote unread records
                continue
            if b"2510000" in rec:
                klines += 1
        print(time.strftime("%H:%M:%S"), f"ok {c['ok']:2d} shift {c['shift']:2d} bad {c['bad']:2d} err {c['err']:2d}",
              f"max pad {top:7d} seq {seq} kernel {klines}", flush=True)


if __name__ == "__main__":
    main()
