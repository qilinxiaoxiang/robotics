"""walk_wired.py: the control loop never waits on the disk or on paged-out memory (the 2026-10-30 fall: a 348 ms tick
on a page fault while another process read a 671 MB log). lock_memory's flags and failure line, and LogWriter keeping a
slow disk off the caller's thread. No hardware.

  ~/.venvs/microduck-walk/bin/python -m unittest test_walk_wired_stall -v
"""
import os
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "pi"))
import walk_wired as ww  # noqa: E402


class FakeLibc:
    def __init__(self, ret):
        self.ret, self.flags = ret, None

    def mlockall(self, flags):
        self.flags = flags
        return self.ret


class SlowFile:
    """A file whose writes block until released, like a write waiting on the SD card's journal."""

    def __init__(self):
        self.gate = threading.Event()
        self.data, self.flushes = [], 0

    def write(self, s):
        self.gate.wait(5)
        self.data.append(s)

    def flush(self):
        self.flushes += 1

    def fileno(self):
        return 99


class LockMemory(unittest.TestCase):
    def test_locks_current_future_on_fault(self):
        libc = FakeLibc(0)
        self.assertIn("memory lock: on", ww.lock_memory(libc))
        self.assertEqual(libc.flags, 1 | 2 | 4)

    def test_failure_is_printed_not_fatal(self):
        msg = ww.lock_memory(FakeLibc(-1))
        self.assertIn("memory lock FAILED", msg)
        self.assertIn("memlock limit", msg)

    def test_no_mlockall(self):
        self.assertIn("not available", ww.lock_memory(object()))


class LogWriterTest(unittest.TestCase):
    def test_write_returns_while_the_disk_blocks(self):
        f = SlowFile()
        log = ww.LogWriter(f)
        t0 = time.perf_counter()
        for i in range(50):
            log.write(f"row {i}\n")
        self.assertLess(time.perf_counter() - t0, 0.05)  # 50 ticks queued while the first write is still blocked
        f.gate.set()
        deadline = time.time() + 2
        while sum(s.count("\n") for s in f.data) < 50 and time.time() < deadline:
            time.sleep(0.01)
        self.assertEqual("".join(f.data), "".join(f"row {i}\n" for i in range(50)))
        self.assertGreaterEqual(f.flushes, 1)
        self.assertEqual(log.fileno(), 99)

    def test_real_file_order_and_flush(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "log.jsonl")
            log = ww.LogWriter(open(p, "a"))
            for i in range(500):
                log.write(f'{{"n": {i}}}\n')
            deadline = time.time() + 2
            while time.time() < deadline:
                with open(p) as fh:
                    lines = fh.read().splitlines()
                if len(lines) == 500:
                    break
                time.sleep(0.01)
            self.assertEqual(lines, [f'{{"n": {i}}}' for i in range(500)])


if __name__ == "__main__":
    unittest.main()
