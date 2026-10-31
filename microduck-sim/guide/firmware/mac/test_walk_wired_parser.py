"""walk_wired.py Link._reader: a lost byte costs one status packet, not 6 s of servo reads (2026-10-31 16:35:10: a
header read with the next header's bytes as its length waited for 65 kB and the duck fell). No hardware.

  ~/.venvs/microduck-walk/bin/python -m unittest test_walk_wired_parser -v
"""
import collections
import os
import struct
import sys
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "pi"))
import walk_wired as ww  # noqa: E402
from dxl_fast import crc16  # noqa: E402


class Done(Exception):
    pass


class FakeSerial:
    """Hands the reader the stream in fixed chunks, then stops its loop."""

    def __init__(self, data, chunk=7):
        self.chunks = [data[i:i + chunk] for i in range(0, len(data), chunk)]

    @property
    def in_waiting(self):
        return len(self.chunks[0]) if self.chunks else 0

    def read(self, n):
        if not self.chunks:
            raise Done
        return self.chunks.pop(0)


def status(dxl_id, params, err=0):
    body = bytes([0xFF, 0xFF, 0xFD, 0x00, dxl_id]) + struct.pack("<H", len(params) + 4) + bytes([0x55, err]) + params
    return body + struct.pack("<H", crc16(body))


def parse(data):
    link = object.__new__(ww.Link)
    link.ser = FakeSerial(data)
    link.status = collections.deque()
    link.imu, link.imu_count, link.imu_bad = None, 0, 0
    link.lock = threading.Lock()
    try:
        link._reader()
    except Done:
        pass
    return [p[4] for p in link.status]


class ReaderResync(unittest.TestCase):
    def test_whole_frame_parses(self):
        frame = b"".join(status(i, bytes(10)) for i in range(1, 16))
        self.assertEqual(parse(frame), list(range(1, 16)))

    def test_a_lost_length_byte_costs_one_packet_not_the_rest(self):
        # drop the first length byte of servo 3's reply: its header now reads 0xFD.. as length; the old reader waited
        # for that many bytes and every later reply (this frame and the next 200 ticks) was swallowed
        frames = [status(i, bytes(10)) for i in range(1, 16)]
        broken = frames[2][:5] + frames[2][6:]
        data = b"".join(frames[:2]) + broken + b"".join(frames[3:]) + b"".join(status(i, bytes(10)) for i in range(1, 16))
        got = parse(data)
        self.assertEqual(got[:2], [1, 2])
        self.assertNotIn(3, got[:3])
        self.assertEqual(got[-15:], list(range(1, 16)))  # the next tick's frame arrives whole

    def test_a_corrupted_reply_is_dropped_by_its_crc(self):
        bad = bytearray(status(4, bytes(10)))
        bad[10] ^= 0x40  # a flipped bit in the position bytes
        data = status(3, bytes(10)) + bytes(bad) + status(5, bytes(10))
        self.assertEqual(parse(data), [3, 5])

    def test_an_implausible_length_resyncs_at_once(self):
        junk = bytes([0xFF, 0xFF, 0xFD, 0x00, 7, 0xFF, 0xFD])  # LEN 0xFDFF, the 16:35 pattern
        self.assertEqual(parse(junk + status(8, bytes(10))), [8])


class TouchJamBackoff(unittest.TestCase):
    """A jammed touch bus is tried once every TOUCH_JAM_RETRY_S, not 50 times a second (2026-10-31 16:33:35)."""

    def test_backs_off_after_a_run_of_failures_and_returns_on_the_first_good_read(self):
        state = {"ok": False}

        def read():
            if not state["ok"]:
                raise OSError(22, "Invalid argument")
            return bytes(ww.TOUCH_BLOCK)

        pads = ww.TouchPads(read, start=False)
        for _ in range(ww.TOUCH_JAM_FAILS - 1):
            pads.poll()
        self.assertEqual(pads.period(), ww.TOUCH_PERIOD)  # a few failures keep the scan rate
        pads.poll()
        self.assertEqual(pads.period(), ww.TOUCH_JAM_RETRY_S)
        state["ok"] = True
        self.assertTrue(pads.poll())
        self.assertEqual(pads.period(), ww.TOUCH_PERIOD)


if __name__ == "__main__":
    unittest.main()
