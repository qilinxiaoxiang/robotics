"""Tests for blackbox.py: kernel record parsing and copying (fake /dev/kmsg reads), the system snapshot from a fake
/proc tree, every row reaching the file before the next one starts, and boot pruning. No hardware.

Run from this folder:  python3 -m unittest test_blackbox -v
"""
import errno
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import blackbox  # noqa: E402


def put(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(value)


def fake_proc(root, ticks=100, irq=10, cpu=(100, 0, 50, 800, 10, 5, 5, 0), dpid=False):
    put(root + "/stat", "cpu  %s 0 0\ncpu0 1 2 3 4 5 6 7 8 0 0\n" % " ".join(map(str, cpu)))
    put(root + "/loadavg", "1.93 1.10 0.50 2/150 999\n")
    put(root + "/uptime", "443.83 3000.00\n")
    put(root + "/meminfo", "MemTotal: 2000000 kB\nMemAvailable: 1566000 kB\n")
    put(root + "/pressure/cpu", "some avg10=12.50 avg60=3.00 avg300=1.00 total=1\n")
    put(root + "/interrupts", "           CPU0       CPU1\n 60:        %d          5   GICv3 2502800.uart\n"
        " 61:          0          0   GICv3 2517000.twi\nIPI0:         7          7   Rescheduling interrupts\n" % irq)
    put(root + "/net/wireless", "Inter-| sta-|   Quality        |\n face | tus | link level noise\n"
        " wlan0: 0000   55.  -55.  -256        0      0      0      0      0        0\n")
    put(root + "/net/dev", "Inter-|   Receive\n face |bytes packets\n"
        "  wlan0: 1000 10 0 0 0 0 0 0 2000 20 0 0 0 0 0 0\n")
    put(root + "/sys/kernel/random/boot_id", "f05692a9-2456-4ec8-b9eb-4e8714dcb61b\n")
    fields = ["S"] + ["0"] * 10 + [str(ticks), "0"] + ["0"] * 10
    put(root + "/943/stat", "943 (python walk_wired) " + " ".join(fields) + "\n")
    fields[0] = "D" if dpid else "S"
    put(root + "/77/stat", "77 (kworker/u16:2) " + " ".join(fields[:11] + ["1", "0"] + fields[13:]) + "\n")
    put(root + "/77/wchan", "sunxi_twi_xfer")
    put(root + "/77/stack", "[<0>] __switch_to+0x0/0x0\n[<0>] sunxi_twi_xfer+0x1a0/0x300\n")


class KmsgLine(unittest.TestCase):
    def test_record_with_continuation(self):
        rec = "3,812,117463330,-;engine-mode: xfer failed(dev addr:0x74)\n SUBSYSTEM=i2c\n"
        self.assertEqual(blackbox.kmsg_line(rec, 1792613669.33),
                         "1792613669.330 117.463330 err #812 engine-mode: xfer failed(dev addr:0x74)\n")

    def test_facility_bits_do_not_change_level(self):
        self.assertIn(" info ", blackbox.kmsg_line("30,1,5,-;systemd started", 1.0))  # facility 3, level 6

    def test_junk_is_dropped(self):
        self.assertIsNone(blackbox.kmsg_line("no separator", 1.0))
        self.assertIsNone(blackbox.kmsg_line("x,y;text", 1.0))


class KmsgCopy(unittest.TestCase):
    def test_burst_is_copied_and_fsynced_and_overwrite_marked(self):
        reads = [b"6,1,1000,-;first\n", OSError(errno.EPIPE, "overwritten"), b"4,9,2000,-;second\n",
                 BlockingIOError()]
        stop = threading.Event()

        def fake_read(fd, n):
            item = reads.pop(0) if reads else BlockingIOError()
            if isinstance(item, BaseException):
                raise item
            return item

        def fake_select(*a):
            stop.set()
            return [], [], []

        with tempfile.TemporaryDirectory() as d:
            out = open(d + "/k.log", "a")
            with mock.patch("os.open", return_value=99), mock.patch("os.close"), \
                    mock.patch("os.read", side_effect=fake_read), mock.patch("select.select", side_effect=fake_select):
                blackbox.kmsg_loop("/dev/kmsg", out, stop)
            out.close()
            text = open(d + "/k.log").read().splitlines()
        self.assertEqual(len(text), 3)
        self.assertTrue(text[0].endswith("0.001000 info #1 first"))
        self.assertIn("overwrote unread records", text[1])
        self.assertTrue(text[2].endswith("0.002000 warn #9 second"))

    def test_sync_thread_fsyncs_every_file_until_stopped(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = open(d + "/a", "a"), open(d + "/b", "a")
            stop = threading.Event()
            seen = []
            with mock.patch("os.fsync", side_effect=lambda fd: seen.append(fd) or (len(seen) >= 4 and stop.set())):
                blackbox.sync_loop([a, b], stop, period=0)
            a.close(); b.close()
        self.assertEqual(len(set(seen)), 2)

    def test_failure_leaves_its_reason(self):
        with tempfile.TemporaryDirectory() as d:
            out = open(d + "/k.log", "a")
            blackbox.kmsg_loop(d + "/missing-kmsg", out, threading.Event())
            out.close()
            self.assertIn("kernel copy stopped", open(d + "/k.log").read())


class Snapshot(unittest.TestCase):
    def test_row_reports_deltas_busiest_and_dstate(self):
        with tempfile.TemporaryDirectory() as d:
            fake_proc(d, ticks=100, irq=10)
            s = blackbox.Snapshot(d, 100)
            fake_proc(d, ticks=150, irq=60, cpu=(150, 0, 60, 820, 20, 5, 5, 0), dpid=True)
            s.t -= 1.0  # one second later
            r = s.row()
        self.assertEqual(r["top"][0]["comm"], "python walk_wired")
        self.assertAlmostEqual(r["top"][0]["cpu"], 50.0, delta=1.0)
        self.assertEqual(r["dstate"], [{"pid": 77, "comm": "kworker/u16:2", "s": 0.0, "wchan": "sunxi_twi_xfer",
                                        "stack": ["__switch_to+0x0/0x0", "sunxi_twi_xfer+0x1a0/0x300"]}])
        self.assertEqual(r["irq"], {"60 GICv3 2502800.uart": 50})
        self.assertEqual(r["cpu"], {"busy": 66.7, "iowait": 11.1, "irq": 0.0, "softirq": 0.0})  # deltas 50,0,10,20 idle,10 iowait of 90
        self.assertEqual(r["mem_avail_mb"], 1529)
        self.assertEqual(r["psi"], {"cpu": 12.5})
        self.assertEqual(r["wifi"]["wlan0"], {"link": 55.0, "level": -55.0, "rx": 1000, "tx": 2000})
        self.assertEqual(r["up"], 443.83)


class Main(unittest.TestCase):
    def test_rows_are_on_disk_with_header_and_boot_in_name(self):
        with tempfile.TemporaryDirectory() as d:
            fake_proc(d + "/proc")
            put(d + "/kmsg", "")
            with mock.patch("os.fsync") as fsync:
                blackbox.main(["--out", d + "/bb", "--period", "0", "--rows", "3", "--proc", d + "/proc",
                               "--kmsg", d + "/kmsg"])
            names = sorted(os.listdir(d + "/bb"))
            self.assertEqual(names, ["b0001-f05692a9-kmsg.log", "b0001-f05692a9-sys.jsonl"])
            with open(d + "/bb/" + names[1]) as f:
                rows = [json.loads(x) for x in f]
        self.assertEqual(rows[0]["boot"], "f05692a9")
        self.assertIn("watchdog", rows[0])
        self.assertIn("kernel/watchdog_thresh", rows[0]["sysctl"])
        self.assertEqual(len(rows), 4)
        self.assertTrue(all("kmsg_alive" in r for r in rows[1:]))
        self.assertGreaterEqual(fsync.call_count, 2)  # the sync thread plus the final close of both files

    def test_prune_keeps_newest_boots(self):
        with tempfile.TemporaryDirectory() as d:
            for stem in ("b0009-aaaaaaaa", "b0010-bbbbbbbb", "b0011-cccccccc"):
                put("%s/%s-kmsg.log" % (d, stem), "")
                put("%s/%s-sys.jsonl" % (d, stem), "")
            blackbox.prune(d, 2)
            self.assertEqual(sorted(os.listdir(d))[0], "b0010-bbbbbbbb-kmsg.log")
            self.assertEqual(len(os.listdir(d)), 4)


class Restart(unittest.TestCase):
    def test_same_boot_reuses_stem_and_skips_copied_records(self):
        with tempfile.TemporaryDirectory() as d:
            put(d + "/b0003-f05692a9-kmsg.log", "1.000 0.000001 info #0 a\n1.000 0.000002 err #41 b\n")
            put(d + "/b0002-11111111-kmsg.log", "")
            self.assertEqual(blackbox.stem_for(d, "f05692a9"), d + "/b0003-f05692a9")
            self.assertEqual(blackbox.stem_for(d, "22222222"), d + "/b0004-22222222")
            self.assertEqual(blackbox.last_seq(d + "/b0003-f05692a9-kmsg.log"), 41)
        reads = [b"6,40,1,-;old\n", b"6,42,2,-;new\n", BlockingIOError()]
        stop = threading.Event()

        def fake_read(fd, n):
            item = reads.pop(0) if reads else BlockingIOError()
            if isinstance(item, BaseException):
                raise item
            return item

        with tempfile.TemporaryDirectory() as d:
            out = open(d + "/k.log", "a")
            with mock.patch("os.open", return_value=99), mock.patch("os.close"), \
                    mock.patch("os.read", side_effect=fake_read), \
                    mock.patch("select.select", side_effect=lambda *a: stop.set() or ([], [], [])):
                blackbox.kmsg_loop("/dev/kmsg", out, stop, after=41)
            out.close()
            self.assertEqual([l.split(" ", 4)[4] for l in open(d + "/k.log").read().splitlines()], ["new"])


class Sysrq(unittest.TestCase):
    def test_long_dstate_asks_for_blocked_tasks_once_per_window(self):
        with tempfile.TemporaryDirectory() as d:
            fake_proc(d, dpid=True)
            put(d + "/sysrq-trigger", "")
            s = blackbox.Snapshot(d, 100, d + "/sysrq-trigger")
            s.d_since = {77: time.time() - 3}
            self.assertEqual(s.row()["sysrq"], "w")
            self.assertEqual(open(d + "/sysrq-trigger").read(), "w")
            self.assertIsNone(s.row()["sysrq"])  # rate limit
            s.t -= 3.0
            self.assertEqual(s.row()["sysrq"], "lw")  # a recorder gap has its own limit, not used up by the w dump

    def test_recorder_gap_asks_for_cpu_and_blocked_backtraces(self):
        with tempfile.TemporaryDirectory() as d:
            fake_proc(d)
            put(d + "/sysrq-trigger", "")
            s = blackbox.Snapshot(d, 100, d + "/sysrq-trigger")
            s.t -= 3.0
            self.assertEqual(s.row()["sysrq"], "lw")


if __name__ == "__main__":
    unittest.main()
