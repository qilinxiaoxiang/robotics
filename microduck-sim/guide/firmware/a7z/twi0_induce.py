"""Induce a touch-bus wedge on purpose (FAULTS.json touch-twi0-jam, T2 and the H2/H3 mechanism test). Runs on the A7Z as
root with no brain running (unbinding TWI0 would leave a brain's /dev/i2c-0 handle dead):

  ssh a7z 'sudo -n python3 - --trials 5' < twi0_induce.py

Each trial unbinds the TWI0 driver, bit-bangs a read of the XIAO on gpiochip0 lines 34 (PB2, SCL) / 35 (PB3, SDA) and
abandons it partway through a byte with SCL high (what a glitch or a long master pause leaves behind), rebinds the
driver, then reads at 50 Hz through the kernel for --watch seconds and reports how long until a valid block returns.
The old firmware is expected to stay wedged; touch_main.cpp since 2026-10-31 restarts its slave once a line stays low
30 ms. Prints one JSON line."""
import argparse
import ctypes
import fcntl
import glob
import json
import os
import random
import struct
import time

DEV = "2510000.twi"
CHIP, SDA, SCL, ADDR = "/dev/gpiochip0", 35, 34, 0x2A


class Req(ctypes.Structure):
    _fields_ = [("lineoffsets", ctypes.c_uint32 * 64), ("flags", ctypes.c_uint32),
                ("default_values", ctypes.c_uint8 * 64), ("consumer_label", ctypes.c_char * 32),
                ("lines", ctypes.c_uint32), ("fd", ctypes.c_int)]


class Data(ctypes.Structure):
    _fields_ = [("values", ctypes.c_uint8 * 64)]


GET_HANDLE = (3 << 30) | (ctypes.sizeof(Req) << 16) | (0xB4 << 8) | 0x03
GET_VALUES = (3 << 30) | (ctypes.sizeof(Data) << 16) | (0xB4 << 8) | 0x08
SET_VALUES = (3 << 30) | (ctypes.sizeof(Data) << 16) | (0xB4 << 8) | 0x09


def line(chip, off):
    r = Req(); r.lineoffsets[0] = off; r.lines = 1; r.flags = (1 << 1) | (1 << 3)  # output, open drain
    r.default_values[0] = 1; r.consumer_label = b"induce"
    fcntl.ioctl(chip, GET_HANDLE, r)
    return r.fd


def put(fd, v):
    d = Data(); d.values[0] = v; fcntl.ioctl(fd, SET_VALUES, d)


def get(fd):
    d = Data(); fcntl.ioctl(fd, GET_VALUES, d); return d.values[0]


def driver_dir():
    return os.path.realpath(f"/sys/bus/platform/devices/{DEV}/driver")


def kernel_bus():
    for n in glob.glob("/sys/bus/i2c/devices/i2c-*/of_node"):
        if os.path.realpath(n).endswith("/twi@2510000"):
            return "/dev/" + n.split("/")[-2]
    return None


def aborted_read(bits):
    """START, address + read, `bits` data bits clocked in, then stop clocking with SCL high and no STOP."""
    chip = os.open(CHIP, os.O_RDWR)
    try:
        sda, scl = line(chip, SDA), line(chip, SCL)
    finally:
        os.close(chip)
    try:
        put(sda, 1); put(scl, 1); time.sleep(0.001)
        put(sda, 0); put(scl, 0)                       # START
        b = (ADDR << 1) | 1
        for i in range(8):
            put(sda, (b >> (7 - i)) & 1); put(scl, 1); put(scl, 0)
        put(sda, 1); put(scl, 1); ack = get(sda) == 0; put(scl, 0)
        for _ in range(bits):                          # data bits from the slave
            put(scl, 1); put(scl, 0)
        put(scl, 1)                                    # abandon mid-byte: SCL high, the slave drives SDA with its bit
        sda_after = get(sda)
    finally:
        os.close(sda); os.close(scl)
    return ack, sda_after


def watch(seconds):
    """(seconds until the first valid read or None, failed reads) reading the kernel bus at 50 Hz."""
    path = kernel_bus()
    if not path:
        return None, "no kernel bus after rebind"
    fd = os.open(path, os.O_RDWR)
    fcntl.ioctl(fd, 0x0703, ADDR)
    t0, fails = time.monotonic(), 0
    try:
        while time.monotonic() - t0 < seconds:
            try:
                raw = os.read(fd, 24)
                for block in (raw, raw[1:] + b"\0"):
                    v = struct.unpack("<6I", block)
                    if len(raw) == 24 and max(v[1:]) <= 0x3FFFFF:
                        return round(time.monotonic() - t0, 2), fails
            except OSError:
                pass
            fails += 1
            time.sleep(0.02)
    finally:
        os.close(fd)
    return None, fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--watch", type=float, default=10.0, help="seconds to wait for reads to come back per trial")
    args = ap.parse_args()
    out = {"start": time.strftime("%Y-%m-%d %H:%M:%S"), "trials": []}
    if os.system("pgrep -f walk_wired.py >/dev/null") == 0:
        raise SystemExit("a brain is running: stop it first (unbinding TWI0 would kill its touch handle)")
    drv = driver_dir()
    out["baseline"] = watch(2.0)
    for k in range(args.trials):
        bits = random.randint(9, 8 * 23 - 1)          # somewhere inside bytes 2..23 of the block
        with open(f"{drv}/unbind", "w") as f:
            f.write(DEV)
        try:
            ack, sda_after = aborted_read(bits)
        finally:
            with open(f"{drv}/bind", "w") as f:
                f.write(DEV)
        time.sleep(0.3)
        back_s, fails = watch(args.watch)
        out["trials"].append({"bits": bits, "addr_ack": ack, "sda_after_abort": sda_after,
                              "reads_back_after_s": back_s, "failed_reads": fails})
    out["end"] = time.strftime("%Y-%m-%d %H:%M:%S")
    print(json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
