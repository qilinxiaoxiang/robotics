"""Tests for a7z_cpu_compare.py on a fake sysfs tree with two clusters (policy0 = CPUs 0-5, policy6 = CPUs 6-7): the cap
and offline conditions go in and come back out (also on SIGTERM), the brain-log statistics and verdict, both
thermal.log formats, and the pick. No hardware.

Run from this folder:  python3 -m unittest test_a7z_cpu_compare -v
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import a7z_cpu_compare as C  # noqa: E402
from test_thermal_log import fake_sysfs, put  # noqa: E402

SCRIPT = os.path.join(HERE, "a7z_cpu_compare.py")


def two_cluster_tree(root):
    fake_sysfs(root)
    cpu = f"{root}/devices/system/cpu"
    put(f"{cpu}/present", "0-7")
    for c in range(1, 8):
        put(f"{cpu}/cpu{c}/online", 1)
    put(f"{cpu}/cpufreq/policy0/scaling_available_frequencies", "416000 1008000 1508000 1794000")
    put(f"{cpu}/cpufreq/policy6/scaling_available_frequencies", "416000 1008000 1416000 1800000 2002000")
    put(f"{cpu}/cpufreq/policy6/scaling_max_freq", 2002000)
    for n in (0, 6):
        put(f"{cpu}/cpufreq/policy{n}/scaling_governor", "schedutil")


def load(path):
    with open(path) as f:
        return json.load(f)


def rows(n, period=0.02, loop_ms=12.0, policy=True, t0=1000.0):
    return [(t0 + i * period, loop_ms, "walk" if policy else "monitor", policy) for i in range(n)]


class Tree(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sys = self.tmp.name + "/sys"
        self.logs = self.tmp.name + "/logs"
        os.makedirs(self.logs)
        two_cluster_tree(self.sys)
        self.cpu = f"{self.sys}/devices/system/cpu"

    def tearDown(self):
        self.tmp.cleanup()

    def start(self, *args, soak="0", window="0.03"):
        return subprocess.Popen([sys.executable, SCRIPT, "--sysfs", self.sys, "--logs", self.logs, "run", *args, "--head", "closed",
                                 "--soak-min", soak, "--window-min", window, "--no-brain-check"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def wait_for(self, path, value, timeout=5.0):
        end = time.time() + timeout
        while time.time() < end:
            if C.read(path) == value:
                return True
            time.sleep(0.02)
        return False

    def brain_writer(self, stop):
        with open(f"{self.logs}/duck_wired_log_test.jsonl", "a") as f:
            while not stop.is_set():
                f.write(json.dumps(dict(t=time.time(), loop_ms=12.5, mode="walk", action=[0.1])) + "\n")
                f.flush()
                time.sleep(0.02)

    def test_discovery(self):
        pols = C.policies(self.sys)
        self.assertEqual([p["n"] for p in pols], [0, 6])
        big = C.big_policy(pols)
        self.assertEqual((big["n"], big["cpus"], big["cpuinfo_max"]), (6, [6, 7], 2002000))
        self.assertEqual(C.pick_cap(big, 1400), 1008000)   # highest table entry at or below the request
        self.assertEqual(C.pick_cap(big, 1416), 1416000)
        self.assertEqual(C.online(self.sys), list(range(8)))

    def test_cap_goes_in_and_comes_back(self):
        stop = threading.Event()
        w = threading.Thread(target=self.brain_writer, args=(stop,))
        w.start()
        try:
            p = self.start("cap", "--cap-mhz", "1400")
            capped = self.wait_for(f"{self.cpu}/cpufreq/policy6/scaling_max_freq", "1008000")
            out, _ = p.communicate(timeout=30)
        finally:
            stop.set()
            w.join()
        self.assertEqual(p.returncode, 0, out)
        self.assertTrue(capped, "cap never seen during the run")
        self.assertEqual(C.read(f"{self.cpu}/cpufreq/policy6/scaling_max_freq"), "2002000")
        self.assertEqual(C.read(f"{self.cpu}/cpufreq/policy0/scaling_max_freq"), "1508000")  # the little cluster: untouched
        res = load(next(os.path.join(self.logs, f) for f in os.listdir(self.logs) if f.startswith("cpu_compare_cap_")))
        self.assertEqual((res["cap_khz"], res["big_policy"], res["head"]), (1008000, 6, "closed"))
        self.assertGreater(res["brain"]["policy"]["rows"], 20)
        self.assertTrue(res["verdict"].startswith("UNDECIDED"), res["verdict"])  # a 2 s window has < 500 policy rows
        self.assertFalse(load(f"{self.logs}/cpu-compare-defaults.json")["active"])

    def test_offline_goes_in_and_comes_back(self):
        p = self.start("offline")
        went = self.wait_for(f"{self.cpu}/cpu7/online", "0")
        out, _ = p.communicate(timeout=30)
        self.assertEqual(p.returncode, 0, out)
        self.assertTrue(went, "CPU 7 never went offline")
        self.assertEqual(C.online(self.sys), list(range(8)))
        self.assertIn("CPUs [6, 7] offline", out)

    def test_compare_reads_the_result_glob(self):
        """`compare ~/duck-logs/cpu_compare_*.json` as the runbook writes it: the state file is not a result."""
        p = self.start("default")
        p.communicate(timeout=30)
        res = sorted(os.path.join(self.logs, f) for f in os.listdir(self.logs) if f.startswith("cpu_compare_") and f.endswith(".json"))
        self.assertEqual(len(res), 1, os.listdir(self.logs))
        r = subprocess.run([sys.executable, SCRIPT, "--logs", self.logs, "compare", *res], capture_output=True, text=True, check=True)
        self.assertIn("PICK: no setting passes", r.stdout)

    def test_sigterm_restores(self):
        p = self.start("offline", soak="1")
        self.assertTrue(self.wait_for(f"{self.cpu}/cpu6/online", "0"))
        p.send_signal(signal.SIGTERM)
        out, _ = p.communicate(timeout=10)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("restore: cpu6 online; cpu7 online\n", out)  # and nothing else: no policy was capped
        self.assertEqual(C.online(self.sys), list(range(8)))

    def test_restore_by_hand_after_kill(self):
        p = self.start("cap", soak="1")
        self.assertTrue(self.wait_for(f"{self.cpu}/cpufreq/policy6/scaling_max_freq", "1008000"))
        p.kill()
        p.communicate(timeout=10)
        self.assertEqual(C.read(f"{self.cpu}/cpufreq/policy6/scaling_max_freq"), "1008000")
        r = subprocess.run([sys.executable, SCRIPT, "--sysfs", self.sys, "--logs", self.logs, "restore"],
                           capture_output=True, text=True, check=True)
        self.assertIn("policy6 scaling_max_freq 2002000", r.stdout)
        self.assertEqual(C.read(f"{self.cpu}/cpufreq/policy6/scaling_max_freq"), "2002000")


class Stats(unittest.TestCase):
    def test_pass(self):
        s = C.brain_stats(rows(1000) + rows(200, policy=False, t0=1100.0))
        self.assertEqual((s["policy"]["rows"], s["policy"]["loop_p90_ms"], s["policy"]["ticks_per_s"]), (1000, 12.0, 50.0))
        self.assertEqual(s["modes"], {"walk": 1000, "monitor": 200})
        self.assertTrue(C.verdict(s).startswith("PASS"))

    def test_slow_loop_fails(self):
        r = rows(800) + rows(200, loop_ms=21.0, t0=1016.0)
        self.assertEqual(C.brain_stats(r)["policy"]["loop_p90_ms"], 21.0)
        self.assertTrue(C.verdict(C.brain_stats(r)).startswith("FAIL"))

    def test_low_tick_rate_fails(self):
        s = C.brain_stats(rows(1000, period=1 / 45))
        self.assertAlmostEqual(s["policy"]["ticks_per_s"], 45.0, places=1)
        self.assertTrue(C.verdict(s).startswith("FAIL"))

    def test_policy_runs_split_at_gaps(self):
        """Two 10 s policy runs a minute apart: the gap is not counted as missing ticks."""
        self.assertEqual(C.brain_stats(rows(500) + rows(500, t0=1070.0))["policy"]["ticks_per_s"], 50.0)

    def test_too_few_policy_rows(self):
        self.assertTrue(C.verdict(C.brain_stats(rows(499))).startswith("UNDECIDED"))

    def test_thermal_both_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = tmp + "/thermal.log"
            with open(path, "w") as f:
                f.write("# boot 2026-10-20T04:21:12 zones ['a', 'b']\n"
                        "100.00 80.5 86.0 cur 416 max 416 load 1.06\n"
                        "# boot 2026-10-22T10:00:00 zones ['a', 'b'] policies ['p0 cpus 0-5 max 1794000']\n"
                        "101.00 70.0 nan load 0.40 p0 780/1508 p6 1416/1416\n"
                        "102.00 71.0 72.5 load 0.40 p0 780/1508 p6 off\n"
                        "200.00 99.0 99.0 load 0.40 p0 416/416 p6 416/416\n")
            got = C.thermal_rows(path, 0, 100.0, 103.0)
        self.assertEqual(got, [(100.0, 86.0, {0: (416, 416)}), (101.0, 70.0, {0: (780, 1508), 6: (1416, 1416)}),
                               (102.0, 72.5, {0: (780, 1508), 6: None})])
        st = C.thermal_stats(got)
        self.assertEqual(st["policies"]["p6"], dict(cur_p50_mhz=1416, max_p50_mhz=1416, off_share=0.5))
        self.assertEqual(st["hottest_zone_max_c"], 86.0)


class Pick(unittest.TestCase):
    def res(self, cond, verdict, start=55.0, head="closed"):
        return dict(condition=cond, verdict=verdict, start_hottest_c=start, head=head, cap_khz=1416000 if cond == "cap" else None)

    def test_rules(self):
        self.assertIn("keep the defaults: the heatsink alone", C.decide([self.res("default", "PASS"), self.res("cap", "PASS")])[0])
        self.assertIn("cap the big cluster at 1416 MHz (offline passes too",
                      C.decide([self.res("cap", "PASS"), self.res("offline", "PASS")])[0])
        self.assertEqual(C.decide([self.res("cap", "FAIL"), self.res("offline", "PASS")])[0], "take the big cores offline")
        self.assertIn("no setting passes", C.decide([self.res("cap", "FAIL"), self.res("offline", "UNDECIDED")])[0])

    def test_flags(self):
        flags = C.decide([self.res("cap", "PASS", start=50.0), self.res("offline", "PASS", start=58.0, head="open")])[1]
        self.assertEqual(len(flags), 2)


if __name__ == "__main__":
    unittest.main()
