"""replace_servo.py against a simulated bus: the whole swap, kit-ID clashes, a dead servo, a power loss midway."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replace_servo as rs  # noqa: E402


class Servo:
    def __init__(self, sid, model=1200, shutdown=52, rdt=0, volt=80, torque=0):
        self.mem = bytearray(160)
        self.mem[rs.ADDR_MODEL : rs.ADDR_MODEL + 2] = struct.pack("<H", model)
        self.mem[rs.ADDR_ID] = sid
        self.mem[rs.ADDR_BAUD] = rs.BAUD_1M
        self.mem[rs.ADDR_RDT] = rdt
        self.mem[rs.ADDR_SHUTDOWN] = shutdown
        self.mem[rs.ADDR_TORQUE] = torque
        self.mem[rs.ADDR_VOLT : rs.ADDR_VOLT + 2] = struct.pack("<H", volt)

    @property
    def sid(self):
        return self.mem[rs.ADDR_ID]


def status(sid, data=b""):
    body = bytes([0xFF, 0xFF, 0xFD, 0x00, sid]) + struct.pack("<H", len(data) + 4) + bytes([0x55, 0]) + data
    return body + struct.pack("<H", rs.crc16(body))


class FakeSerial:
    """Servos sharing an ID both take a write and their replies collide, as on the real bus."""

    def __init__(self, servos):
        self.servos, self.rx, self.writes = servos, b"", []

    def reset_input_buffer(self):
        self.rx = b""

    def read(self, n):
        out, self.rx = self.rx[:n], self.rx[n:]
        return out

    def write(self, pkt):
        sid, ins, params = pkt[4], pkt[7], pkt[8:-2]
        if sid == 0xFE and ins == 0x01:
            self.rx = b"".join(status(s.sid, bytes(s.mem[:2]) + b"\x35") for s in sorted(self.servos, key=lambda s: s.sid))
            return
        hit = [s for s in self.servos if s.sid == sid]
        if ins == 0x03:
            addr = struct.unpack("<H", params[:2])[0]
            self.writes.append((sid, addr, bytes(params[2:])))
            for s in hit:
                s.mem[addr : addr + len(params) - 2] = params[2:]
        if len(hit) != 1:
            return  # silence, or a collision no parser can read
        if ins == 0x02:
            addr, size = struct.unpack("<HH", params)
            self.rx = status(sid, bytes(hit[0].mem[addr : addr + size]))
        elif ins == 0x03:
            self.rx = status(sid)


_xfer = rs.Bus.xfer
rs.Bus.xfer = lambda self, sid, ins, params=b"", wait=0.03: _xfer(self, sid, ins, params, wait=0.0005)  # the fake bus answers at once
rs.time.sleep = lambda s: None
rs.print = lambda *a, **k: None


def robot(dead=2):
    return [Servo(i) for i in rs.ALL_IDS if i != dead]


class Swap(unittest.TestCase):
    def run_all(self, ser, spare):
        bus = rs.Bus(ser)
        rs.park(bus, 2)
        ser.servos.append(spare)
        rs.adopt(bus, 2)
        rs.unpark(bus, 2)

    def test_a_kit_servo_that_clashes_with_a_head_servo_ends_as_id2_and_no_other_changes(self):
        ser = FakeSerial(robot())
        before = {s.sid: bytes(s.mem) for s in ser.servos}
        spare = Servo(13, shutdown=53, rdt=250)
        self.run_all(ser, spare)
        self.assertEqual(sorted(s.sid for s in ser.servos), rs.ALL_IDS)
        self.assertEqual((spare.sid, spare.mem[rs.ADDR_SHUTDOWN], spare.mem[rs.ADDR_RDT], spare.mem[rs.ADDR_OPMODE]), (2, 52, 0, 3))
        for s in ser.servos:
            if s is not spare:
                self.assertEqual(bytes(s.mem), before[s.sid], f"ID{s.sid} changed")

    def test_the_spare_at_every_kit_id_works(self):
        for kit in list(range(1, 17)) + [2]:
            ser = FakeSerial(robot())
            spare = Servo(kit, shutdown=53)
            self.run_all(ser, spare)
            self.assertEqual(spare.sid, 2)

    def test_park_refuses_while_a_servo_is_missing_and_writes_nothing(self):
        ser = FakeSerial([s for s in robot() if s.sid != 7])
        with self.assertRaises(SystemExit):
            rs.park(rs.Bus(ser), 2)
        self.assertEqual(ser.writes, [])

    def test_park_refuses_on_a_flat_pack_or_torque_on_and_writes_nothing(self):
        for kw in ({"volt": 60}, {"torque": 1}):
            servos = robot()
            servos[4] = Servo(servos[4].sid, **kw)
            ser = FakeSerial(servos)
            with self.assertRaises(SystemExit):
                rs.park(rs.Bus(ser), 2)
            self.assertEqual(ser.writes, [])

    def test_park_runs_on_after_a_power_loss_midway(self):
        servos = robot()
        for s in servos[:5]:
            s.mem[rs.ADDR_ID] = s.sid + rs.PARK
        ser = FakeSerial(servos)
        rs.park(rs.Bus(ser), 2)
        self.assertEqual(sorted(s.sid for s in servos), sorted(i + rs.PARK for i in rs.ALL_IDS if i != 2))

    def test_adopt_refuses_a_different_model_or_no_servo(self):
        ser = FakeSerial(robot())
        bus = rs.Bus(ser)
        rs.park(bus, 2)
        with self.assertRaises(SystemExit):
            rs.adopt(bus, 2)
        ser.servos.append(Servo(13, model=1190))  # XL330-M077
        n = len(ser.writes)
        with self.assertRaises(SystemExit):
            rs.adopt(bus, 2)
        self.assertEqual(len(ser.writes), n)

    def test_adopt_refuses_when_nothing_was_parked(self):
        ser = FakeSerial(robot() + [Servo(16)])
        with self.assertRaises(SystemExit):
            rs.adopt(rs.Bus(ser), 2)
        self.assertEqual(ser.writes, [])

    def test_unpark_refuses_before_the_new_servo_has_the_id(self):
        ser = FakeSerial(robot())
        bus = rs.Bus(ser)
        rs.park(bus, 2)
        n = len(ser.writes)
        with self.assertRaises(SystemExit):
            rs.unpark(bus, 2)
        self.assertEqual(len(ser.writes), n)


if __name__ == "__main__":
    unittest.main()
