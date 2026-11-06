import json
import math

import walk_ledger as wl


def rows(n=200, lag=4, sag=0.2, t0=1000.0):
    """Synthetic walk: every leg joint swings 0.3 rad at 2 Hz; present follows the goal `lag` ticks late.
    The left knee additionally sits `sag` rad off its goal while the left leg carries the load."""
    out = []
    goal_hist = []
    for i in range(n + 60):
        t = t0 + i * 0.02
        moving = i < n
        left_stance = (i // 25) % 2 == 0
        goal = {}
        for k, name in enumerate(wl.NAMES):
            q = 0.3 * math.sin(2 * math.pi * 2 * i * 0.02) if moving else 0.0
            goal[name] = q
        goal_hist.append(goal)
        past = goal_hist[max(0, i - lag)]
        pos = []
        for name in wl.NAMES:
            q = past[name] + (sag if name == "left_knee" and left_stance else 0.0)
            pos.append(round(2048 + (q * wl.MOTOR_SIGN[name] + wl.MOTOR_OFFSET[name]) / wl.TICK))
        cur = [0] * 14
        for j in wl.LOAD_JOINTS:
            cur[wl.NAMES.index(("left_" if left_stance else "right_") + j)] = 300
            cur[wl.NAMES.index(("right_" if left_stance else "left_") + j)] = 50
        out.append(dict(t=t, mode="walk", cmd=dict(vx=0.25 if moving else 0, vy=0, vtheta=0),
                        pos_tick=pos, cur_ma=cur, gb=[0.0, 0.0, -1.0], gyro_body=[0.0, 0.0, 0.0], imu_valid=True,
                        goal_tick={str(wl.IDS[k]): round(2048 + (goal[nm] * wl.MOTOR_SIGN[nm] + wl.MOTOR_OFFSET[nm])
                                                         / wl.TICK) for k, nm in enumerate(wl.NAMES)},
                        loop_ms=12.0))
    return out


def test_lag_bias_and_stance_split():
    segs = wl.segments(rows())
    assert len(segs) == 1
    rec = wl.analyse_segment(*segs[0], "synthetic")
    knee_l, knee_r = rec["joints"]["left_knee"], rec["joints"]["right_knee"]
    assert knee_l["lag_ticks"] == 4 and knee_r["lag_ticks"] == 4
    assert abs(knee_l["bias_stance"] - 0.2) < 0.01 and abs(knee_l["bias_swing"]) < 0.01
    assert abs(knee_r["bias"]) < 0.01 and abs(knee_r["amp"] - 1.0) < 0.05
    assert not rec["fell"] and rec["ended_in"] == "walk"


def test_report_flags_the_sagging_knee(tmp_path, monkeypatch):
    log = tmp_path / "duck_wired_log_x.jsonl"
    log.write_text("".join(json.dumps(r) + "\n" for r in rows()))
    monkeypatch.setattr(wl, "LEDGER_DIR", str(tmp_path))
    monkeypatch.setattr(wl, "LEDGER", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(wl, "REPORT", str(tmp_path / "REPORT.md"))
    wl.analyse_logs([str(log)], "test")
    wl.report(10)
    text = (tmp_path / "REPORT.md").read_text()
    assert "left knee sags more under its own stance" in text
    assert "right knee" not in text.split("## Flags")[1].split("\n- falls")[0]


def test_log_ending_mid_walk_counts_as_incident(tmp_path, monkeypatch):
    log = tmp_path / "duck_wired_log_y.jsonl"
    log.write_text("".join(json.dumps(r) + "\n" for r in rows()[:150]))
    monkeypatch.setattr(wl, "LEDGER_DIR", str(tmp_path))
    monkeypatch.setattr(wl, "LEDGER", str(tmp_path / "ledger.jsonl"))
    wl.analyse_logs([str(log)], None)
    rec = wl.load_jsonl(str(tmp_path / "ledger.jsonl"))[0]
    assert rec["fell"] and rec["ended_in"] == "log-end"
