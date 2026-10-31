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


def paused_read(bits, pause_ms, glitch=None):
    """START, address + read, `bits` data bits, SCL held low `pause_ms` (a master whose interrupt runs late), then the
    rest of the 24-byte block with ACKs, NACK on the last byte and STOP. Returns (address acked, bytes read).
    glitch "scl": at that bit one extra SCL pulse the master does not count (a noise edge on a slow line), so the slave
    runs one bit ahead; "sda": a low pulse on SDA while SCL is high (a false START then STOP for the slave)."""
    chip = os.open(CHIP, os.O_RDWR)
    try:
        sda, scl = line(chip, SDA), line(chip, SCL)
    finally:
        os.close(chip)
    data, cur = bytearray(), 0

    def rise():                                        # release SCL and honour the slave's clock stretching
        put(scl, 1)
        t = time.monotonic()
        while not get(scl) and time.monotonic() - t < 1.0:
            pass
    try:
        put(sda, 1); put(scl, 1); time.sleep(0.001)
        put(sda, 0); put(scl, 0)
        b = (ADDR << 1) | 1
        for i in range(8):
            put(sda, (b >> (7 - i)) & 1); rise(); put(scl, 0)
        put(sda, 1); rise(); ack = get(sda) == 0; put(scl, 0)
        for n in range(24 * 8):
            if n == bits:
                time.sleep(pause_ms / 1000)            # SCL low the whole pause
                if glitch == "scl":
                    rise(); put(scl, 0)
                elif glitch == "sda":
                    rise(); put(sda, 0); put(sda, 1); put(scl, 0)
            rise(); cur = (cur << 1) | get(sda); put(scl, 0)
            if n % 8 == 7:
                data.append(cur); cur = 0
                put(sda, 1 if n == 24 * 8 - 1 else 0); rise(); put(scl, 0); put(sda, 1)
        put(sda, 0); rise(); put(sda, 1)               # STOP
    finally:
        os.close(sda); os.close(scl)
    return ack, bytes(data)


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


def send(cmd):
    """Write a two-byte command to the XIAO through the kernel bus; True when it was acked."""
    fd = os.open(kernel_bus(), os.O_RDWR)
    try:
        fcntl.ioctl(fd, 0x0703, ADDR)
        return os.write(fd, cmd) == len(cmd)
    except OSError:
        return False
    finally:
        os.close(fd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--watch", type=float, default=10.0, help="seconds to wait for reads to come back per trial")
    ap.add_argument("--recovery-off", action="store_true",
                    help="send RD first: the XIAO's line watchdog stays off 20 s, so the wedge itself shows, then lifts")
    ap.add_argument("--pause-ms", type=float, default=None,
                    help="instead of abandoning the read, pause it this long with SCL low, then finish it")
    ap.add_argument("--glitch", choices=("scl", "sda"), default=None, help="with --pause-ms: inject this noise edge")
    args = ap.parse_args()
    out = {"start": time.strftime("%Y-%m-%d %H:%M:%S"), "trials": []}
    if os.system("pgrep -f '[w]alk_wired.py' >/dev/null") == 0:  # the bracket keeps pgrep off this shell's own line
        raise SystemExit("a brain is running: stop it first (unbinding TWI0 would kill its touch handle)")
    drv = driver_dir()
    out["baseline"] = watch(2.0)
    for k in range(args.trials):
        bits = random.randint(9, 8 * 23 - 1)          # somewhere inside bytes 2..23 of the block
        rd = send(b"RD") if args.recovery_off else None
        with open(f"{drv}/unbind", "w") as f:
            f.write(DEV)
        try:
            if args.pause_ms is None:
                ack, sda_after = aborted_read(bits)
            else:
                ack, got = paused_read(bits, args.pause_ms, args.glitch)
                sda_after = got.hex()
        finally:
            with open(f"{drv}/bind", "w") as f:
                f.write(DEV)
        time.sleep(0.3)
        back_s, fails = watch(args.watch)
        out["trials"].append({"bits": bits, "rd_acked": rd, "addr_ack": ack, "sda_after_abort": sda_after,
                              "reads_back_after_s": back_s, "failed_reads": fails})
    out["end"] = time.strftime("%Y-%m-%d %H:%M:%S")
    print(json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
