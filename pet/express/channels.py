"""Semantic channels -> one body's joints and devices, read from the `channels` block of a body card.

Block format (proposed addition to pet/state body_card.json, see README.md):

  "channels": {
    "space": "delta",                     # outputs are deltas from the body's rest/look pose
    "orient_threshold": 1.2,              # |gaze yaw| past which ORIENT follows the gaze (rad)
    "head_lead_s": 0.22,                  # ORIENT starts this long after ATTEND
    "ATTEND":  {"map": [{"axis": "yaw", "to": "head_yaw", "gain": 1.0}, ...]},
    "ORIENT":  {"map": [...]}, "POSTURE": {"map": [...]}, "GESTURE": {"map": [...]},
    "VOCALISE": {"render": "call" | "clack" | "beep", ...},
    "outputs": {"head_yaw": {"limit": [-1.4, 1.4], "max_rate": 6.0}, ...}
  }

Every output is the sum of gain * axis over the map entries that name it, then clipped to its limit and rate-limited.
An output is an actuator name from the card or a device listed under the card's `devices`. A channel with an empty
map is declared but absent on that body (for example ATTEND.pitch on a vacuum robot).
"""
import json

import numpy as np

from .takes import AXES

CHANNELS = ("ATTEND", "ORIENT", "POSTURE", "GESTURE", "VOCALISE")
AXIS_OF = {"ATTEND": ("yaw", "pitch"), "ORIENT": ("yaw",), "POSTURE": ("height",), "GESTURE": ("tilt", "bob")}
RENDERS = ("call", "clack", "beep", "none")


class CardError(ValueError):
    pass


def load_card(path_or_dict):
    card = json.load(open(path_or_dict)) if isinstance(path_or_dict, str) else path_or_dict
    validate(card)
    return card


def validate(card):
    ch = card.get("channels")
    if not isinstance(ch, dict):
        raise CardError(f"{card.get('name')}: no channels block")
    known = {a["name"] for a in card.get("actuators", [])} | {d["name"] for d in card.get("devices", [])}
    outs = ch.get("outputs", {})
    for name in CHANNELS:
        if name not in ch:
            raise CardError(f"{card['name']}: channel {name} missing (use an empty map when absent)")
    for name, axes in AXIS_OF.items():
        for m in ch[name].get("map", []):
            if m.get("axis") not in axes:
                raise CardError(f"{card['name']}: {name} has no axis {m.get('axis')!r}")
            if m.get("to") not in known:
                raise CardError(f"{card['name']}: {name}.{m['axis']} maps to unknown output {m.get('to')!r}")
            if m["to"] not in outs:
                raise CardError(f"{card['name']}: output {m['to']} has no limit")
            if not isinstance(m.get("gain"), (int, float)):
                raise CardError(f"{card['name']}: {name}.{m['axis']} -> {m['to']} gain must be a number")
    v = ch["VOCALISE"]
    if v.get("render") not in RENDERS:
        raise CardError(f"{card['name']}: VOCALISE render must be one of {RENDERS}")
    for key in ("to", "device", "light"):
        if v.get(key) is not None and v[key] not in known:
            raise CardError(f"{card['name']}: VOCALISE {key} {v[key]!r} is not an actuator or device")
    for o, spec in outs.items():
        lo, hi = spec["limit"]
        if not lo < hi:
            raise CardError(f"{card['name']}: output {o} limit {spec['limit']} is empty")
    return True


def matrix(card):
    """(outputs, M) with outputs_vector = M @ axes_vector, axes in takes.AXES order."""
    ch = card["channels"]
    outs = list(ch["outputs"])
    M = np.zeros((len(outs), len(AXES)))
    for name, axes in AXIS_OF.items():
        for m in ch[name].get("map", []):
            M[outs.index(m["to"]), AXES.index(f"{name}.{m['axis']}")] += m["gain"]
    return outs, M


def present_axes(card):
    """Semantic axes this body can show (some output listens to them)."""
    _, M = matrix(card)
    return [a for k, a in enumerate(AXES) if np.any(M[:, k] != 0)]


def map_trajectory(card, axes, dt, events=()):
    """Semantic axis arrays -> {output: array} with limits and rate limits, plus device events.
    VOCALISE: 'call' passes events to the speaker; 'clack' adds a close-open pulse per event to its gripper output;
    'beep' emits beep events and a light pulse on the card's light output."""
    ch = card["channels"]
    outs, M = matrix(card)
    n = len(axes[AXES[0]])
    X = np.stack([np.asarray(axes.get(a, np.zeros(n)), float) for a in AXES])
    Y = M @ X
    res = {o: Y[i].copy() for i, o in enumerate(outs)}
    v = ch["VOCALISE"]
    dev = []
    for ev in events:
        k = int(round(ev["t"] / dt))
        if v["render"] == "call":
            dev.append(dict(ev, device=v.get("device", "speaker")))
        elif v["render"] == "clack":
            w = max(1, int(round(v.get("ms", 120) / 1000 / dt)))
            for rep in range(int(v.get("clacks", 1)) + (1 if ev.get("pitch", 1.0) > 1.1 else 0)):
                k0 = k + rep * 2 * w
                prof = np.sin(np.linspace(0, np.pi, w)) * v.get("amplitude", 0.3)
                seg = res[v["to"]][k0:k0 + w]
                seg += prof[:len(seg)]
            dev.append(dict(t=ev["t"], kind="clack", device=v["to"]))
        elif v["render"] == "beep":
            hz = v.get("base_hz", 1400) * ev.get("pitch", 1.0)
            ms = v.get("ms", 120) * ev.get("stretch", 1.0)
            dev.append(dict(t=ev["t"], kind="beep", device=v["device"], hz=round(hz), ms=round(ms)))
            if v.get("light"):
                w = max(1, int(round(ms / 1000 / dt * 2)))
                seg = res[v["light"]][k:k + w]
                seg += np.exp(-np.linspace(0, 3, w))[:len(seg)]
    for o in outs:
        spec = ch["outputs"][o]
        y = np.clip(res[o], *spec["limit"])
        mr = spec.get("max_rate")
        if mr:
            step = mr * dt
            for k in range(1, n):
                y[k] = y[k - 1] + max(-step, min(step, y[k] - y[k - 1]))
        res[o] = y
    return res, dev


def map_frame(card, values, prev=None, dt=0.02):
    """One 50 Hz frame: {axis: value} -> {output: value}, limited and rate-limited against `prev`."""
    ch = card["channels"]
    outs, M = matrix(card)
    x = np.array([values.get(a, 0.0) for a in AXES])
    y = M @ x
    out = {}
    for i, o in enumerate(outs):
        spec = ch["outputs"][o]
        val = float(np.clip(y[i], *spec["limit"]))
        if prev is not None and spec.get("max_rate"):
            step = spec["max_rate"] * dt
            val = prev[o] + max(-step, min(step, val - prev[o]))
        out[o] = val
    return out
