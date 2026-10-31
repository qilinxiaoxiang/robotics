"""XIAO-side wedge injection (FAULTS.json touch-twi0-jam T2). Runs on the A7Z with no brain running:

  ssh a7z 'sudo -n python3 - --line D --trials 3 [--recovery-off]' < twi0_hold_test.py

Reads the touch block through the bound kernel driver at 50 Hz, as the brain does, and per trial writes "HD" (or "HC")
so the XIAO holds SDA (or SCL) low the way a slave out of step does. With --recovery-off it writes "RD" first, so the
hold lasts the XIAO's 20 s RD window, as on the old firmware; otherwise the line watchdog restarts the XIAO after 30 ms.
Nothing is unbound or rebound: the kernel driver must recover by itself. Reports per trial the outage (first failed or
invalid read to the next valid one), the kernel's TWI0 lines meanwhile and whether the XIAO restarted (sequence reset).
Prints one JSON line."""
import argparse
import fcntl
import glob
import json
import os
import struct
import subprocess
import time

ADDR = 0x2A


def kernel_bus():
    for n in glob.glob("/sys/bus/i2c/devices/i2c-*/of_node"):
        if os.path.realpath(n).endswith("/twi@2510000"):
            return "/dev/" + n.split("/")[-2]
    raise SystemExit("no kernel bus for twi@2510000")


def block(raw):
    """(seq, pads) or None; accepts the one-byte 0x55 shift the brain's parser accepts."""
    if len(raw) != 24:
        return None
    for b in (raw, raw[1:] + b"\0"):
        v = struct.unpack("<6I", b)
        if max(v[1:]) <= 0x3FFFFF:
            return v[0], v[1:]
    return None


def kmsg_count():
    return len(subprocess.run(["dmesg"], capture_output=True, text=True).stdout.splitlines())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", choices="DC", default="D")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--watch", type=float, default=30.0, help="seconds to wait for valid reads per trial")
    ap.add_argument("--recovery-off", action="store_true")
    args = ap.parse_args()
    if subprocess.run("pgrep -f '[w]alk_wired.py'", shell=True, capture_output=True).returncode == 0:
        raise SystemExit("a brain is running: stop it first")
    fd = os.open(kernel_bus(), os.O_RDWR)
    fcntl.ioctl(fd, 0x0703, ADDR)

    def read():
        try:
            return block(os.read(fd, 24))
        except OSError:
            return None

    def write(cmd):
        try:
            return os.write(fd, cmd) == len(cmd)
        except OSError:
            return False

    out = {"start": time.strftime("%Y-%m-%d %H:%M:%S"), "line": args.line, "recovery_off": args.recovery_off,
           "trials": []}
    for _ in range(args.trials):
        ok_before = sum(read() is not None for _ in range(10) if not time.sleep(0.02))
        seq_before = (read() or (None,))[0]
        rd = write(b"RD") if args.recovery_off else None
        k0 = kmsg_count()
        t_cmd = time.monotonic()
        hold = write(b"H" + args.line.encode())
        t_fail = t_back = None
        fails, seq_after = 0, None
        while time.monotonic() - t_cmd < args.watch:
            v = read()
            now = time.monotonic()
            if v is None:
                fails += 1
                t_fail = t_fail or now
            elif t_fail:
                t_back, seq_after = now, v[0]
                break
            elif now - t_cmd > 2.0:  # two seconds of valid reads after the command: no outage at all
                seq_after = v[0]
                break
            time.sleep(0.02)
        lines = subprocess.run(["dmesg"], capture_output=True, text=True).stdout.splitlines()[k0:]
        twi = [l.split("]: ", 1)[-1] for l in lines if "2510000" in l]
        out["trials"].append({
            "ok_before_of_10": ok_before, "rd_acked": rd, "hold_acked": hold,
            "outage_s": round(t_back - t_fail, 2) if t_fail and t_back else None,
            "back": bool(t_back) or not t_fail, "failed_reads": fails,
            "xiao_restarted": seq_after is not None and seq_before is not None and seq_after < seq_before,
            "kernel_twi_lines": len(twi), "kernel_first": twi[:4]})
        time.sleep(1.0)
    os.close(fd)
    out["end"] = time.strftime("%Y-%m-%d %H:%M:%S")
    print(json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
