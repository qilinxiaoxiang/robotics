import json
import os
import time

import namecall_boot as nb


def write(tmp_path, **row):
    p = tmp_path / "duck_wired_log_a.jsonl"
    p.write_text("x" * 20000 + "\n" + json.dumps(row) + "\n")
    return str(tmp_path)


def test_ready_only_at_walk_zero_on_a_fresh_log(tmp_path):
    logs = write(tmp_path, mode="walk", cmd=dict(vx=0.0, vy=0.0, vtheta=0.0))
    assert nb.brain_ready(logs=logs)
    assert not nb.brain_ready(now=time.time() + 5, logs=logs)
    assert not nb.brain_ready(logs=write(tmp_path, mode="monitor", cmd={}))
    assert not nb.brain_ready(logs=write(tmp_path, mode="stand", cmd={}))
    assert not nb.brain_ready(logs=write(tmp_path, mode="walk", cmd=dict(vx=0.2)))


def test_no_brain_log_is_not_ready(tmp_path):
    assert not nb.brain_ready(logs=str(tmp_path))
