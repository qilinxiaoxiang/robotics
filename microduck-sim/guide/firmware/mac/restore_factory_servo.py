"""Restore a MicroDuck servo that fell back to factory settings (ID 1, 57600), alone on a separate OpenRB on the Mac.

The duck's own OpenRB (openrb_dual_host) fixes the bus at 1 Mbaud, so it cannot reach such a servo; a separate board follows USB baud.
Each write is read back, the baud goes last, then the servo is checked at 1 Mbaud. Never sets torque.
Run with ~/.venvs/microduck-dyn/bin/python restore_factory_servo.py --id 2
"""
import argparse, glob, json, struct, sys, time, serial
ap = argparse.ArgumentParser()
ap.add_argument("--id", type=int, required=True, choices=range(1, 16), help="the ID this servo has on the robot")
TARGET = ap.parse_args().id
DEV = glob.glob("/dev/cu.usbmodem*")[0]
F = {"model": (0, 2), "id": (7, 1), "baud": (8, 1), "rdt": (9, 1), "drive": (10, 1), "opmode": (11, 1), "homing": (20, 4), "shutdown": (63, 1), "torque": (64, 1), "hw": (70, 1), "pos": (132, 4), "volt": (144, 2)}
def crc(data):
    c = 0
    for x in data:
        c ^= x << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x8005) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    return c
def pkt(sid, ins, params=b""):
    body = bytes([0xFF, 0xFF, 0xFD, 0x00, sid]) + struct.pack("<H", len(params) + 3) + bytes([ins]) + params
    return body + struct.pack("<H", crc(body))
class Bus:
    def __init__(self, baud):
        self.s = serial.Serial(DEV, baud, timeout=0)
    def xfer(self, p, wait=0.12):
        self.s.reset_input_buffer(); self.s.write(p)
        t0, buf = time.time(), b""
        while time.time() - t0 < wait:
            buf += self.s.read(512); time.sleep(0.002)
        return buf
    def scan(self):
        for _ in range(20):
            time.sleep(0.1)
            buf = self.xfer(pkt(0xFE, 1), 0.2)
            ids = sorted({buf[i + 4] for i in range(len(buf) - 5) if buf[i : i + 4] == b"\xff\xff\xfd\x00"})
            if ids:
                return ids
        return []
    def read(self, sid, name):
        a, n = F[name]
        for _ in range(5):
            buf = self.xfer(pkt(sid, 2, struct.pack("<HH", a, n)))
            i = buf.find(b"\xff\xff\xfd\x00" + bytes([sid]))
            if i >= 0 and len(buf) >= i + 7:
                m = struct.unpack("<H", buf[i + 5 : i + 7])[0]
                p = buf[i : i + 7 + m]
                if len(p) == 7 + m and struct.unpack("<H", p[-2:])[0] == crc(p[:-2]) and p[7] == 0x55 and m == n + 4:
                    return int.from_bytes(p[9:-2], "little")
        return None
    def write(self, sid, name, value):
        a, n = F[name]
        return self.xfer(pkt(sid, 3, struct.pack("<H", a) + value.to_bytes(n, "little")))
b = Bus(57600)
ids = b.scan()
print("at 57600:", ids)
if ids != [1] or b.read(1, "model") != 1200 or b.read(1, "torque") != 0:
    sys.exit("not one model 1200 at ID 1 with torque off; nothing written")
for name, value in (("rdt", 0), ("drive", 0), ("opmode", 3), ("homing", 0), ("shutdown", 52)):
    if b.read(1, name) != value:
        b.write(1, name, value)
    got = b.read(1, name)
    print(name, got)
    if got != value:
        sys.exit(f"{name} did not read back {value}; ID and baud not changed")
if TARGET != 1:
    b.write(1, "id", TARGET)
if b.read(TARGET, "id") != TARGET:
    sys.exit(f"ID {TARGET} did not read back; baud not changed")
print("id", TARGET)
b.write(TARGET, "baud", 3)
b.s.close()
time.sleep(0.3)
b = Bus(1000000)
ids = b.scan()
print("at 1 Mbaud:", ids)
print(json.dumps({k: b.read(TARGET, k) for k in F}))
