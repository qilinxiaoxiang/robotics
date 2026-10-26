"""Primitive backends. The mind hands them validated primitive steps only, never joint values.

SimExecutor: logs the step and lets simulated time pass; posture and room changes come from the card and the world.
DuckCommandStub: documents and produces the mapping onto walk_brain.py's control file (/tmp/duck_cmd.json, see the
mode list at the top of microduck-sim/guide/firmware/mac/walk_brain.py). By default it only returns the commands;
with write_path it writes them as walk_brain expects (one JSON object, replaced atomically). Timing between the
commands of one primitive belongs to a live runner, which this stub does not provide.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

WALK_ZERO = {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0}


class SimExecutor:
    def __init__(self, world):
        self.world = world

    def start(self, step: dict) -> float:
        return float(step["seconds"])

    def finish(self, step: dict, body) -> str | None:
        posture = body.primitives[step["primitive"]].get("effects", {}).get("posture")
        if posture:
            self.world.posture = posture
        return self.world.move_pet(step["primitive"], step["params"])


def duck_commands(step: dict, posture: str = "standing") -> list[tuple[float, dict]]:
    """(seconds after the step starts, control-file JSON) for one validated duck primitive.

    stand        -> walk mode at zero command (walk_brain runs stand61 until the first step; the policy balances)
    sit          -> {"mode": "sit"} (Pollen sitstand61)
    walk         -> walk mode at (vx, vtheta), then zero command after `seconds`
    approach_owner / wander -> walk mode; heading from perception (owner bearing, as approach.py does) or a slow
                   random arc; here vtheta 0 / +-0.2 as placeholders, zero command at the end
    turn_head    -> zero-command walk (or sit) with a head pose: {"head": {"head_yaw", "head_pitch"}}
    look_around, nod -> the same head command at a few yaw / pitch points
    bow          -> {"mode": "groundpick", "phase": 0.4}, then phase 1.0 (rises and returns to stand61)
    rest         -> {"mode": "sit", "head": {"head_pitch": -0.3}}
    wait         -> nothing (walk_brain keeps the last command)
    stop         -> zero-command walk, or sit when already seated
    """
    name, p = step["primitive"], step["params"]
    base = {"mode": "sit"} if posture == "sitting" else dict(WALK_ZERO)

    def head(yaw=0.0, pitch=0.0):
        return {**base, "head": {"head_yaw": round(yaw, 3), "head_pitch": round(pitch, 3)}}

    secs = float(step.get("seconds", 0))
    if name == "stand":
        return [(0, dict(WALK_ZERO))]
    if name == "sit":
        return [(0, {"mode": "sit"})]
    if name == "walk":
        return [(0, {"mode": "walk", "vx": p["vx"], "vy": 0.0, "vtheta": p["vtheta"]}), (secs, dict(WALK_ZERO))]
    if name == "approach_owner":
        return [(0, {"mode": "walk", "vx": 0.25, "vy": 0.0, "vtheta": 0.0}), (secs, dict(WALK_ZERO))]
    if name == "wander":
        cmds, t, turn = [], 0.0, 0.2
        while t < secs:
            cmds.append((t, {"mode": "walk", "vx": 0.2, "vy": 0.0, "vtheta": turn}))
            t, turn = t + 3.0, -turn
        return cmds + [(secs, dict(WALK_ZERO))]
    if name == "turn_head":
        return [(0, head(p["yaw"], p["pitch"]))]
    if name == "look_around":
        pts = [-0.8, 0.0, 0.8, 0.0]
        return [(secs * i / len(pts), head(y, 0.1)) for i, y in enumerate(pts)]
    if name == "nod":
        out = []
        for i in range(int(p["times"])):
            out += [(i * 0.8, head(0, 0.3)), (i * 0.8 + 0.4, head(0, -0.1))]
        return out + [(int(p["times"]) * 0.8, head(0, 0))]
    if name == "bow":
        return [(0, {"mode": "groundpick", "phase": 0.4}), (3.5, {"mode": "groundpick", "phase": 1.0})]
    if name == "rest":
        return [(0, {"mode": "sit", "head": {"head_pitch": -0.3}})]
    if name == "wait":
        return []
    if name == "stop":
        return [(0, base)]
    raise ValueError(f"no duck mapping for primitive {name}")


class DuckCommandStub:
    def __init__(self, write_path: str | None = None):
        self.write_path = Path(write_path) if write_path else None
        self.sent: list[dict] = []

    def send(self, cmd: dict):
        self.sent.append(cmd)
        if self.write_path:
            tmp = self.write_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(cmd))
            os.replace(tmp, self.write_path)
