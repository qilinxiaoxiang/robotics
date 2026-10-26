"""Take library: several ways to answer the same intent, chosen by context, jittered per sample, never repeated twice.

A take turns (intent, context) into reference setpoints on the semantic axes; spring-damper tracking of those
setpoints gives the motion. Axes:
  ATTEND.yaw, ATTEND.pitch  gaze direction, rad (+ left, + up)
  ORIENT.yaw                body heading, rad; follows the gaze only past the body's orient threshold
  POSTURE.height            -1 slumped .. +1 alert and tall (unitless)
  GESTURE.tilt              head tilt, rad (+ toward the target side)
  GESTURE.bob               nod / bounce impulse, unitless
VOCALISE is a list of events {"t", "kind": "call", "pitch", "stretch", "gain_db"} with t relative to the take start.
"""
import math
from dataclasses import dataclass, field

import numpy as np

from .intents import effort_for
from .spring import track, wn_zeta_from_effort

AXES = ("ATTEND.yaw", "ATTEND.pitch", "ORIENT.yaw", "POSTURE.height", "GESTURE.tilt", "GESTURE.bob")
SOCIAL_TAKES = ("quick_snap", "curious_turn", "double_take", "groggy", "glance")
DT = 0.02


@dataclass
class Context:
    """What the selector and the takes see. `novelty` comes from Habituation (1 fresh .. ~0.1 called a lot)."""
    novelty: float = 1.0
    distracted: bool = False      # attention was on something else when the call came
    start: dict = field(default_factory=dict)  # current axis values
    orient_threshold: float = 1.2  # |gaze yaw| beyond which the body turns too (rad)
    head_lead: float = 0.22       # s the gaze leads the body


@dataclass
class Performance:
    take: str
    intent: str
    t0: float
    axes: dict
    events: list
    params: dict
    arrival: float | None
    dt: float = DT

    @property
    def duration(self):
        return len(next(iter(self.axes.values()))) * self.dt

    def sample(self, now):
        k = int(round((now - self.t0) / self.dt))
        k = min(max(k, 0), len(self.axes["ATTEND.yaw"]) - 1)
        return {a: float(v[k]) for a, v in self.axes.items()}

    def done(self, now):
        return now - self.t0 >= self.duration - 1e-9


class Habituation:
    """Novelty drops on every call and recovers exponentially; calls close together get smaller answers."""

    def __init__(self, drop=0.75, tau_s=40.0, floor=0.1):
        self.h, self.last, self.drop, self.tau, self.floor = 1.0, None, drop, tau_s, floor

    def on_call(self, now):
        if self.last is not None:
            self.h = 1.0 - (1.0 - self.h) * math.exp(-(now - self.last) / self.tau)
        used = self.h
        self.h = max(self.floor, self.h * self.drop)
        self.last = now
        return used


def _j(rng, nominal, rel=0.15):
    """Multiplicative jitter: nominal * exp(N(0, rel))."""
    return float(nominal * math.exp(rng.normal(0.0, rel)))


def selection_weights(intent, ctx):
    a, w, h = intent.affect.arousal, intent.warmth, ctx.novelty
    eff = effort_for(intent)
    wts = {
        "quick_snap": (0.3 + a) * (0.4 + w) * h * h,
        "curious_turn": (0.5 + (1.0 - abs(a - 0.45))) * (0.6 + (1.0 - eff.space)) * h * 0.8,
        "double_take": (1.2 if ctx.distracted else 0.35) * h * (1.0 if a > 0.25 else 0.2),
        "groggy": 3.5 * max(0.0, 0.4 - a) + 0.005,
        "glance": 1.5 * (1.0 - h) ** 2,
    }
    if intent.kind == "attend":
        wts["double_take"] *= 0.5
    return wts


def choose_take(intent, ctx, rng, last=None):
    if intent.kind == "startle":
        return "startle"
    wts = selection_weights(intent, ctx)
    names = [n for n in SOCIAL_TAKES if n != last and wts[n] > 0]
    p = np.array([wts[n] for n in names])
    return names[int(rng.choice(len(names), p=p / p.sum()))]


class _Refs:
    """Piecewise-constant setpoints with per-segment spring gains on a DT grid."""

    def __init__(self, n, start, wn, zeta):
        self.n = n
        self.ref = {a: np.full(n, start.get(a, 0.0)) for a in AXES}
        self.wn = {a: np.full(n, wn) for a in AXES}
        self.zeta = {a: np.full(n, zeta) for a in AXES}

    def set(self, axis, t, value, wn=None, zeta=None):
        k = min(self.n - 1, max(0, int(round(t / DT))))
        self.ref[axis][k:] = value
        if wn is not None:
            self.wn[axis][k:] = wn
        if zeta is not None:
            self.zeta[axis][k:] = zeta

    def pulse(self, axis, t, value, width):
        base = self.ref[axis][min(self.n - 1, int(round(t / DT)))]
        self.set(axis, t, base + value)
        self.set(axis, t + width, base)

    def run(self, start, limits=None):
        out = {}
        for a in AXES:
            mr = (limits or {}).get(a)
            out[a] = track(self.ref[a], DT, self.wn[a], self.zeta[a], x0=start.get(a, 0.0), max_rate=mr)
        return out


def plan(take, intent, ctx, rng, rate_limits=None):
    """Build one Performance-ready (axes, events, params, arrival) for a take. Times relative to the take start."""
    a, v = intent.affect.arousal, intent.affect.valence
    h = ctx.novelty
    eff = effort_for(intent)
    wn0, z0 = wn_zeta_from_effort(eff, a)
    start = {ax: float(ctx.start.get(ax, 0.0)) for ax in AXES}
    ty, tp = intent.target.yaw, intent.target.pitch
    move = ty - start["ATTEND.yaw"]
    side = 1.0 if move >= 0 else -1.0
    e = intent.energy * (0.4 + 0.6 * h)          # habituated answers are smaller
    cute = intent.warmth * (1.0 - eff.space)      # indirect + warm -> head tilt
    p = dict(take=take, novelty=round(h, 3), energy=round(e, 3), effort=eff.__dict__)

    if take == "quick_snap":
        p.update(latency=_j(rng, 0.10 + 0.25 * (1 - eff.time)), antic=_j(rng, 0.08 + 0.10 * eff.time * (1 - eff.weight), 0.25),
                 antic_s=_j(rng, 0.10, 0.2), wn=_j(rng, wn0 * 1.25, 0.12), zeta=max(0.28, _j(rng, z0 * 0.85, 0.12)),
                 tilt=_j(rng, 0.05 + 0.10 * cute, 0.3), lift=_j(rng, 0.25 * e + 0.1, 0.2), bob=_j(rng, 0.10 * e + 0.04, 0.3),
                 call_off=rng.normal(0.03, 0.03), semis=1.0, stretch=0.95, amp=1.0, total=1.9)
    elif take == "curious_turn":
        p.update(latency=_j(rng, 0.30, 0.2), antic=_j(rng, 0.04, 0.4), antic_s=_j(rng, 0.12, 0.2),
                 wn=_j(rng, max(3.5, wn0 * 0.55), 0.12), zeta=min(1.0, _j(rng, 0.85, 0.08)),
                 tilt=_j(rng, 0.14 + 0.14 * cute, 0.2), tilt_delay=_j(rng, 0.25, 0.3), pitch_up=_j(rng, 0.08, 0.3),
                 lift=_j(rng, 0.15, 0.3), bob=0.0, call_off=rng.normal(0.35, 0.08), semis=2.0, stretch=1.1, amp=1.0, total=2.4)
    elif take == "double_take":
        p.update(latency=_j(rng, 0.15, 0.2), glance_frac=_j(rng, 0.45, 0.15), glance_hold=_j(rng, 0.22, 0.2),
                 back_hold=_j(rng, 0.18, 0.2), antic=0.0, antic_s=0.0, wn=_j(rng, wn0 * 1.4, 0.1),
                 zeta=max(0.28, _j(rng, z0 * 0.75, 0.12)), tilt=_j(rng, 0.06 + 0.08 * cute, 0.3),
                 lift=_j(rng, 0.35 * e + 0.1, 0.2), bob=_j(rng, 0.12 * e + 0.04, 0.3),
                 call_off=rng.normal(0.06, 0.04), semis=2.5, stretch=0.9, amp=1.0, total=2.6)
    elif take == "groggy":
        p.update(latency=_j(rng, 0.65, 0.2), antic=0.0, antic_s=0.0, wn=_j(rng, 3.0, 0.12), zeta=_j(rng, 1.15, 0.06),
                 tilt=_j(rng, 0.04, 0.4), droop=_j(rng, 0.45, 0.2), lift=-0.1, bob=0.0, amp=_j(rng, 0.85, 0.06),
                 call_off=rng.normal(0.45, 0.1), semis=-3.0, stretch=1.35, total=3.0)
    elif take == "glance":
        p.update(latency=_j(rng, 0.25, 0.25), antic=0.0, antic_s=0.0, wn=_j(rng, wn0, 0.12), zeta=min(1.0, _j(rng, max(z0, 0.6), 0.1)),
                 tilt=0.0, lift=0.0, bob=0.0, amp=_j(rng, 0.45, 0.2), hold=_j(rng, 0.6, 0.25),
                 call_off=rng.normal(0.1, 0.05), semis=0.0, stretch=0.8, total=1.9)
    elif take == "startle":
        p.update(latency=_j(rng, 0.07, 0.2), antic=0.0, antic_s=0.0, wn=_j(rng, 16.0, 0.1), zeta=_j(rng, 0.38, 0.1),
                 recoil=_j(rng, 0.8, 0.15), tilt=0.0, lift=0.0, bob=0.0, amp=1.0,
                 call_off=rng.normal(0.0, 0.03), semis=4.0, stretch=0.7, total=2.4)
    else:
        raise ValueError(take)

    n = int(round(p["total"] / DT))
    R = _Refs(n, start, p["wn"], p["zeta"])
    L = p["latency"]
    t_main = L
    if p["antic"] > 0:  # anticipation: a small counter-move and a dip before the turn
        back = start["ATTEND.yaw"] - side * max(0.03, abs(move) * p["antic"])
        R.set("ATTEND.yaw", L, back, wn=p["wn"] * 1.3, zeta=0.9)
        R.set("POSTURE.height", L, start["POSTURE.height"] - 0.6 * p["antic"] - 0.05, wn=p["wn"], zeta=0.8)
        t_main = L + p["antic_s"]
    goal_yaw = start["ATTEND.yaw"] + move * p["amp"]
    goal_pitch = start["ATTEND.pitch"] + (tp - start["ATTEND.pitch"]) * p["amp"] + p.get("pitch_up", 0.0)

    if take == "double_take":
        g = start["ATTEND.yaw"] + move * p["glance_frac"]
        R.set("ATTEND.yaw", t_main, g)
        t_back = t_main + p["glance_hold"]
        R.set("ATTEND.yaw", t_back, start["ATTEND.yaw"] + 0.1 * move)
        t_main = t_back + p["back_hold"]
        R.set("ATTEND.yaw", t_main, goal_yaw, wn=p["wn"] * 1.3, zeta=p["zeta"])
        R.set("ATTEND.pitch", t_main, goal_pitch, wn=p["wn"], zeta=p["zeta"])
    elif take == "glance":  # a look toward the caller, then back to what it was doing
        R.set("ATTEND.yaw", t_main, goal_yaw, wn=p["wn"], zeta=p["zeta"])
        R.set("ATTEND.pitch", t_main, goal_pitch, wn=p["wn"], zeta=p["zeta"])
        R.set("ATTEND.yaw", t_main + p["hold"], start["ATTEND.yaw"] + 0.1 * move, wn=p["wn"] * 0.7, zeta=1.0)
        R.set("ATTEND.pitch", t_main + p["hold"], start["ATTEND.pitch"], wn=p["wn"] * 0.7, zeta=1.0)
    elif take == "groggy":
        R.set("POSTURE.height", 0.0, start["POSTURE.height"] - p["droop"], wn=2.5, zeta=1.0)
        R.set("ATTEND.pitch", 0.0, start["ATTEND.pitch"] - 0.25 * p["droop"], wn=2.5, zeta=1.0)
        R.set("ATTEND.yaw", t_main, goal_yaw, wn=p["wn"], zeta=p["zeta"])
        R.set("ATTEND.pitch", t_main + 0.3, goal_pitch, wn=p["wn"] * 0.8, zeta=p["zeta"])
        R.set("POSTURE.height", t_main + 0.5, start["POSTURE.height"] - 0.2 * p["droop"], wn=2.0, zeta=1.0)
    elif take == "startle":
        R.set("POSTURE.height", L, start["POSTURE.height"] - p["recoil"], wn=18.0, zeta=0.5)
        R.set("ATTEND.yaw", L, goal_yaw, wn=p["wn"], zeta=p["zeta"])
        R.set("ATTEND.pitch", L, goal_pitch, wn=p["wn"], zeta=p["zeta"])
        R.set("POSTURE.height", L + 0.5, start["POSTURE.height"] + 0.2, wn=3.0, zeta=1.0)
    else:
        R.set("ATTEND.yaw", t_main, goal_yaw, wn=p["wn"], zeta=p["zeta"])
        R.set("ATTEND.pitch", t_main, goal_pitch, wn=p["wn"] * 0.9, zeta=p["zeta"])
    if p["lift"]:
        R.set("POSTURE.height", t_main, start["POSTURE.height"] + p["lift"], wn=p["wn"] * 0.7, zeta=max(0.5, p["zeta"]))

    # body follows the gaze past the threshold, starting head_lead after the gaze
    if abs(goal_yaw) > ctx.orient_threshold:
        lead = _j(rng, ctx.head_lead, 0.2)
        p["head_lead"] = lead
        R.set("ORIENT.yaw", t_main + lead, goal_yaw - math.copysign(ctx.orient_threshold * 0.5, goal_yaw),
              wn=max(2.5, p["wn"] * 0.45), zeta=0.95)

    axes0 = R.run(start, rate_limits)
    arrival = _arrival(axes0["ATTEND.yaw"], start["ATTEND.yaw"], goal_yaw, t_main)
    if arrival is None:
        arrival = t_main + 0.3
    p["arrival"] = arrival

    # tilt and bob are placed relative to the measured arrival of the gaze
    if p["tilt"]:
        t_tilt = arrival + p.get("tilt_delay", 0.0)
        R.set("GESTURE.tilt", t_tilt, side * p["tilt"] * (1 if rng.random() > 0.2 else -1), wn=6.0, zeta=0.6)
        R.set("GESTURE.tilt", t_tilt + _j(rng, 0.7, 0.25), side * p["tilt"] * 0.3, wn=3.0, zeta=0.9)
    t_call = max(0.0, arrival + p["call_off"])
    events = vocal_events(take, intent, h, t_call, p, rng)
    bob = p["bob"] or (0.08 if intent.kind == "greet" else 0.0)
    for ev in events or ([dict(t=t_call)] if bob else []):  # a bounce on each call
        if bob:
            R.pulse("GESTURE.bob", ev["t"], bob, 0.08)
    axes = R.run(start, rate_limits)
    return axes, events, p, arrival


def vocal_events(take, intent, novelty, t_call, p, rng):
    if intent.kind == "attend":
        return []
    a, v = intent.affect.arousal, intent.affect.valence
    prob = {"glance": 0.3, "groggy": 0.65, "startle": 0.5}.get(take, 0.95) * (0.5 + 0.5 * novelty)
    if intent.kind == "greet":
        prob = 1.0
    if rng.random() > prob:
        return []
    semis = 1.5 * v + 2.5 * (a - 0.5) + p["semis"] + rng.normal(0.0, 0.7)
    out = []
    n = 2 if intent.kind == "greet" else 1
    for i in range(n):
        out.append(dict(t=round(t_call + i * _j(rng, 0.38, 0.15), 3), kind="call",
                        pitch=round(float(np.clip(2 ** ((semis + 1.0 * i) / 12), 0.8, 1.35)), 3),
                        stretch=round(float(np.clip(p["stretch"] * (1 + 0.35 * (0.5 - a)) * math.exp(rng.normal(0, 0.08)), 0.7, 1.5)), 3),
                        gain_db=round(float(-8.0 * (1.0 - novelty)), 1)))
    return out


def _arrival(x, x0, goal, t_from, frac=0.88):
    move = goal - x0
    if abs(move) < 1e-6:
        return t_from
    k0 = int(round(t_from / DT))
    prog = (x[k0:] - x0) / move
    i = np.flatnonzero(prog >= frac)
    return None if not i.size else (k0 + int(i[0])) * DT
