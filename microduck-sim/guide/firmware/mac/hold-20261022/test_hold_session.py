"""Tests for hold_session.py and hold_analyze.py on synthetic tick logs (no robot).

    ~/.venvs/microduck-walk/bin/python -m unittest -v      (in this folder)
"""
import gzip
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest

import hold_session as hs
import hold_analyze as ha

DT = 0.02
BASE = [10000.0, 11000.0, 9000.0, 9500.0, 10500.0]          # rest counts L1 R1 L2 R2 M
RISE = {"L1": 1000.0, "R1": 900.0, "L2": 600.0, "R2": 650.0, "M": 500.0}
NOISE = 10.0
STAND_MA, AIR_MA = 1500.0, 300.0


class Gen:
    """A 50 Hz synthetic tick log. Each trial is preceded by 1.5 s of idle standing; trials() lists
    (label, first row t, last row t) as Shawn's Enter presses would mark them."""

    def __init__(self, t=1000.0, seed=0):
        self.t, self.rows, self.trials, self.rng = t, [], [], random.Random(seed)

    def row(self, touch_add=None, legs=STAND_MA, mode="walk", faults=(), s=1.0, neck=60.0, hold_on=False):
        add = touch_add or [0.0] * 5
        touch = [round(b + a + self.rng.gauss(0, NOISE)) for b, a in zip(BASE, add)]
        cur = [legs / 10] * 10 + [-40.0, neck, 5.0, 5.0]
        r = {"t": round(self.t, 3), "mode": mode, "policy": "stand" if mode == "walk" else None, "torque": True,
             "kp": 200, "gb": [0.0, 0.0, -1.0], "gyro_body": [0.0, 0.0, 0.0], "acc": [0.0, 0.0, 9.81],
             "q": [0.0] * 14, "action": [0.01] * 14, "cur_ma": cur, "touch": touch, "touch_age": 0.01,
             "touch_seq": int(self.t * 50), "hw_faults": list(faults), "missing": [], "cmd": {"mode": "walk"},
             "hold": {"lv": [0.0] * 5, "cov": 0.0, "e": 0.0, "load": None, "h_load": 0.0, "s": s,
                      "kp_leg": 200, "kp_neck": 200}, "hold_on": hold_on, "legs_ma": legs}
        self.rows.append(r)
        self.t += DT
        return r

    def idle(self, secs, **kw):
        for _ in range(round(secs / DT)):
            self.row(**kw)

    def trial(self, label, secs, fn=lambda u: {}):
        """fn(u) -> row kwargs at u s into the trial."""
        self.idle(1.5)
        first = self.row(**fn(0.0))
        for k in range(1, round(secs / DT)):
            last = self.row(**fn(k * DT))
        self.trials.append((label, first["t"], last["t"]))


def pads(**on):
    return [on.get(p, 0.0) for p in hs.PADS]


def press(p):
    return lambda u: {"touch_add": pads(**{p: RISE[p] if 0.2 <= u <= 2.8 else 0.0})}


def grip(u):
    return {"touch_add": pads(L1=RISE["L1"], R1=RISE["R1"], M=RISE["M"]) if 0.2 <= u <= 2.8 else None}


def lift(air=AIR_MA, mode_at=None, fault_at=None, hold_on=False):
    def fn(u):
        legs = STAND_MA if u < 1.0 or u > 5.0 else air
        kw = {"touch_add": pads(L1=RISE["L1"], R1=RISE["R1"], M=RISE["M"]), "legs": legs, "neck": 60 + 200 * (legs < STAND_MA),
              "hold_on": hold_on, "s": 0.3 if hold_on and legs < STAND_MA else 1.0}
        if mode_at is not None and u >= mode_at:
            kw["mode"] = "stand"
        if fault_at is not None and u >= fault_at:
            kw["faults"] = ["left_knee"]
        return kw
    return fn


def stroke(u):
    # front to back: M first, then L1/R1, then L2/R2, each pad on for 0.4 s
    on = {"M": 0.0, "L1": 0.15, "R1": 0.15, "L2": 0.45, "R2": 0.45}
    return {"touch_add": pads(**{p: RISE[p] if on[p] + 0.2 <= u < on[p] + 0.6 else 0.0 for p in on})}


def pat(u):
    hit = any(0.2 + 0.3 * k <= u < 0.3 + 0.3 * k for k in range(3))
    return {"touch_add": pads(L1=RISE["L1"] * hit, R1=RISE["R1"] * hit, M=RISE["M"] * hit)}


def full_session(air=AIR_MA, skip=(), lifts=None):
    g = Gen()
    g.idle(3.0)  # the live bars' 2 s baseline
    g.trial("rest", 10.0)
    for p in hs.PADS:
        for _ in range(3):
            g.trial("press_" + p, 3.0, press(p))
    if "grip" not in skip:
        for _ in range(2):
            g.trial("grip", 3.0, grip)
    for fn in lifts or [lift(air)] * 3:
        g.trial("lift_head_off", 6.0, fn)
    for _ in range(3):
        g.trial("stroke", 1.2, stroke)
        g.trial("pat", 1.2, pat)
    g.idle(1.0)
    return g


def drive(g, sess, before=None):
    """Feed the rows to a Session, pressing Enter at each trial's first and last row (stepping with n/b to its
    label); before(label) runs extra keys before a trial starts."""
    starts = {t0: (lb, t1) for lb, t0, t1 in g.trials}
    ends = {t1 for _, _, t1 in g.trials}
    labels = [s[0] for s in hs.STEPS]
    for r in g.rows:
        sess.feed(r, r["t"])
        if r["t"] in starts:
            lb = starts[r["t"]][0]
            while sess.step != labels.index(lb):
                sess.key("n" if sess.step < labels.index(lb) else "b", r["t"])
            if before:
                before(lb)
            sess.key("\n", r["t"])
        elif r["t"] in ends:
            sess.key("\n", r["t"])


class Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.labels = os.path.join(self.dir, "hold_labels_x.jsonl")
        self.holdf = os.path.join(self.dir, "duck_hold.json")

    def session(self):
        return hs.Session(self.labels, self.holdf, "duck_wired_log_x.jsonl")


class TestTail(Tmp):
    def test_partial_line_waits_for_newline(self):
        p = os.path.join(self.dir, "duck_wired_log_x.jsonl")
        with open(p, "w") as f:
            f.write(json.dumps({"t": 1.0}) + "\n")
        tail = hs.Tail(p, from_start=True)
        self.addCleanup(tail.close)
        self.assertEqual([r["t"] for r in tail.read()], [1.0])
        with open(p, "a") as f:
            f.write('{"t": 2.0, "mo')
        self.assertEqual(list(tail.read()), [])
        with open(p, "a") as f:
            f.write('de": "walk"}\n{"t": 3.0}\n')
        self.assertEqual([r["t"] for r in tail.read()], [2.0, 3.0])

    def test_from_end_skips_old_rows(self):
        p = os.path.join(self.dir, "duck_wired_log_x.jsonl")
        with open(p, "w") as f:
            f.write(json.dumps({"t": 1.0}) + "\n")
        tail = hs.Tail(p)
        self.addCleanup(tail.close)
        with open(p, "a") as f:
            f.write(json.dumps({"t": 2.0}) + "\n")
        self.assertEqual([r["t"] for r in tail.read()], [2.0])

    def test_newest_log_and_suffix(self):
        for i, name in enumerate(["duck_wired_log_a.jsonl", "duck_wired_log_hold1022b.jsonl"]):
            p = os.path.join(self.dir, name)
            open(p, "w").close()
            os.utime(p, (1000 + i, 1000 + i))
        newest = hs.newest_log(os.path.join(self.dir, "duck_wired_log_*.jsonl"))
        self.assertEqual(hs.suffix_of(newest), "hold1022b")
        self.assertEqual(hs.suffix_of("data/duck_wired_log_hold1022b.jsonl.gz"), "hold1022b")


class TestLabels(Tmp):
    def test_trials_use_log_clock_and_count(self):
        g = full_session()
        sess = self.session()
        drive(g, sess)
        trials, raw = hs.load_trials(self.labels)
        self.assertEqual(len(trials), len(g.trials))
        for tr, (lb, t0, t1) in zip(trials, g.trials):
            self.assertEqual((tr["label"], tr["t0"], tr["t1"]), (lb, t0, t1))
        self.assertEqual([tr["trial"] for tr in trials if tr["label"] == "press_L1"], [1, 2, 3])
        self.assertEqual(sess.count("lift_head_off"), 3)

    def test_x_marks_last_bad_and_drops_running(self):
        g = Gen()
        g.idle(3.0)
        g.trial("rest", 2.0)
        g.trial("rest", 2.0)
        sess = self.session()
        drive(g, sess)
        sess.key("x", g.t)
        trials, raw = hs.load_trials(self.labels)
        self.assertEqual(len(trials), 1)
        self.assertEqual(raw[-1]["kind"], "bad")
        self.assertEqual(sess.count("rest"), 1)
        sess.key("\n", g.t)           # start, then drop it
        sess.key("x", g.t)
        self.assertIsNone(sess.active)
        self.assertEqual(len(hs.load_trials(self.labels)[0]), 1)

    def test_resume_counts_and_step(self):
        g = full_session()
        drive(g, self.session())
        again = self.session()
        self.assertEqual(again.count("press_M"), 3)
        self.assertEqual(hs.STEPS[again.step][0], "pat")

    def test_no_start_on_stale_log_or_wrong_hold_state(self):
        g = Gen()
        g.idle(3.0)
        sess = self.session()
        for r in g.rows:
            sess.feed(r, r["t"])
        sess.key("\n", g.t + 5.0)
        self.assertIsNone(sess.active)
        self.assertIn("日志没有更新", sess.msg)
        sess.step = [s[0] for s in hs.STEPS].index("lift_head_on")
        sess.key("\n", g.t)
        self.assertIsNone(sess.active)
        self.assertIn("按 h", sess.msg)
        sess.key("h", g.t)
        sess.key("\n", g.t)
        self.assertIsNotNone(sess.active)


class TestCalibration(Tmp):
    def test_values_written_keeping_on_off(self):
        g = full_session()
        sess = self.session()
        drive(g, sess)
        sess.key("c", g.t)
        hf = hs.hold.read_hold_file(self.holdf)
        self.assertFalse(hf["on"], sess.msg)
        cal = hf["cal"]
        self.assertAlmostEqual(cal["legs_stand_ma"], STAND_MA, delta=1)
        self.assertAlmostEqual(cal["legs_air_ma"], AIR_MA, delta=1)
        for k, p in enumerate(hs.PADS):
            self.assertAlmostEqual(cal["pad_rise"][k], RISE[p], delta=15)
            self.assertAlmostEqual(cal["pad_lo"][k], 0.25 * RISE[p], delta=10)   # 0.25 x rise beats 5 x std (~50)
            self.assertAlmostEqual(cal["pad_hi"][k], 0.8 * RISE[p], delta=12)
            self.assertAlmostEqual(cal["pad_rest_std"][k], NOISE, delta=2)
        self.assertAlmostEqual(cal["grip_full_mm2"], 324 + 324 + 144, delta=1)   # L1 + R1 + M fully covered
        # the estimator takes it
        est = hs.hold.HoldEstimator(cal)
        self.assertEqual(est.legs_range, (cal["legs_air_ma"], cal["legs_stand_ma"]))
        # a later c keeps the hold on once it is on
        sess.key("h", g.t)
        sess.key("c", g.t)
        self.assertTrue(hs.hold.read_hold_file(self.holdf)["on"])

    def test_refuses_close_leg_current(self):
        g = full_session(air=1300.0)
        sess = self.session()
        drive(g, sess)
        sess.key("c", g.t)
        self.assertIn("校准拒绝", sess.msg)
        self.assertIn("20%", sess.msg)
        self.assertEqual(hs.hold.read_hold_file(self.holdf)["cal"], {})

    def test_refuses_missing_step(self):
        g = full_session(skip=("grip",))
        cal, problems = hs.compute_cal([dict(label=lb, t0=a, t1=b) for lb, a, b in g.trials],
                                       [hs.slim(r) for r in g.rows])
        self.assertIsNone(cal)
        self.assertTrue(any("grip" in p for p in problems), problems)

    def test_refuses_pad_without_rise(self):
        g = Gen()
        g.idle(3.0)
        g.trial("rest", 10.0)
        for p in hs.PADS:
            g.trial("press_" + p, 3.0, (lambda u: {}) if p == "L2" else press(p))
        g.trial("grip", 3.0, grip)
        g.trial("lift_head_off", 6.0, lift())
        cal, problems = hs.compute_cal([dict(label=lb, t0=a, t1=b) for lb, a, b in g.trials],
                                       [hs.slim(r) for r in g.rows])
        self.assertIsNone(cal)
        self.assertTrue(any(p.startswith("L2") for p in problems), problems)

    def test_h_toggles_and_keeps_cal(self):
        hs.hold.write_hold_file(False, {"legs_stand_ma": 1500, "legs_air_ma": 300}, self.holdf)
        sess = self.session()
        sess.key("h", 0.0)
        self.assertEqual(hs.hold.read_hold_file(self.holdf), {"on": True, "cal": {"legs_stand_ma": 1500, "legs_air_ma": 300}, "error": None})
        sess.key("h", 0.0)
        self.assertFalse(hs.hold.read_hold_file(self.holdf)["on"])


class TestView(Tmp):
    def test_live_view_stale_and_mode_change(self):
        g = Gen()
        g.idle(3.0)
        g.idle(0.5, mode="stand")
        g.idle(0.2, mode="stand", faults=["left_knee"])
        sess = self.session()
        for r in g.rows:
            sess.feed(r, r["t"])
        text = "\n".join(sess.render(g.rows[-1]["t"]))
        self.assertNotIn("日志没有更新", text)
        for p in hs.PADS:
            self.assertIn(f" {p:>2} ", text)
        self.assertIn("walk → stand", text)
        self.assertIn("护栏", text)
        self.assertIn("left_knee", text)
        self.assertIn("步骤 0：rest", text)
        self.assertIn("日志没有更新", "\n".join(sess.render(g.rows[-1]["t"] + 1.5)))
        self.assertIsNotNone(sess.base)
        sess.msg = "校准拒绝：" + "；".join(["腿电流站立 1500 mA，提起 1300 mA，差不到 20%，分不出离地"] * 3)
        for step in range(len(hs.STEPS)):  # every step's screen fits an ssh terminal 100 columns wide
            sess.step = step
            lines = sess.render(g.rows[-1]["t"])
            self.assertIn(f"步骤 {hs.step_no(hs.STEPS[step][0])}：", "\n".join(lines))
            for ln in lines:
                self.assertLessEqual(hs.width(ln), 100, ln)


class TestAnalyze(Tmp):
    def test_lockup_verdicts_and_leg_separation(self):
        g = full_session(lifts=[lift(), lift(mode_at=3.0), lift(fault_at=2.0)])
        trials = [dict(label=lb, t0=a, t1=b, trial=i + 1) for i, (lb, a, b) in enumerate(g.trials)]
        text, cal, problems = ha.report(g.rows, trials)
        verdicts = [ln for ln in text.splitlines() if ln.startswith("    -> ")]
        self.assertEqual([v.split(":")[0] for v in verdicts], ["    -> neither", "    -> guard", "    -> hw"])
        self.assertIn("80 % below standing", text)
        self.assertIn("mode walk -> stand at +3.00 s", text)
        self.assertIsNotNone(cal, problems)

    def test_stroke_walks_across_pads_pat_does_not(self):
        g = full_session()
        slim = hs.Rows([hs.slim(r) for r in g.rows])
        full = hs.Rows(g.rows)
        tr = {lb: dict(label=lb, t0=a, t1=b) for lb, a, b in g.trials}
        fs = ha.gesture_features(full, slim, tr["stroke"], [NOISE] * 5)
        fp = ha.gesture_features(full, slim, tr["pat"], [NOISE] * 5)
        self.assertEqual(fs["pads_on"], 5)
        self.assertTrue(fs["order"].startswith("M"), fs["order"])
        self.assertTrue(fs["order"].endswith("R2") or fs["order"].endswith("L2"), fs["order"])
        self.assertGreater(fs["spread"], 0.3)
        self.assertEqual(fs["rises"], 1)
        self.assertLess(fp["spread"], 0.05)
        self.assertEqual(fp["rises"], 3)

    def test_hold_on_track(self):
        g = Gen()
        g.idle(3.0)
        g.trial("lift_head_on", 6.0, lift(hold_on=True))
        lb, a, b = g.trials[0]
        g.idle(1.0)
        h = ha.hold_track(hs.Rows(g.rows), dict(label=lb, t0=a, t1=b))
        self.assertEqual((h["s0"], h["s_min"], h["s_end"]), (1.0, 0.3, 1.0))
        self.assertAlmostEqual(h["t_min"], 1.0, delta=0.05)

    def test_main_reads_gzip_and_writes_cal(self):
        g = full_session()
        drive(g, self.session())
        log = os.path.join(self.dir, "duck_wired_log_x.jsonl.gz")
        with gzip.open(log, "wt") as f:
            for r in g.rows:
                f.write(json.dumps(r) + "\n")
            f.write('{"t": 9')  # a half-written last line
        out = subprocess.run([sys.executable, ha.__file__, log, self.labels], capture_output=True, text=True,
                             check=True).stdout
        self.assertIn("== lifts", out)
        with open(os.path.join(self.dir, "hold_cal_x.json")) as f:
            cal = json.load(f)
        self.assertAlmostEqual(cal["legs_air_ma"], AIR_MA, delta=1)


if __name__ == "__main__":
    unittest.main()
