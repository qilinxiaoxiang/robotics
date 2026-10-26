"""Expressor: the one object between the mind and a body.

  ex = Expressor(load_card("pet/express/cards/duck.json"), seed=1)
  ex.submit(acknowledge(Target(0.8, 0.2), warmth=0.8, energy=0.7, affect=Affect(0.6, 0.6)), now)   # mind, any time
  frame = ex.step(now)    # body loop, 50 Hz: frame["outputs"] -> joints/devices, frame["events"] -> speaker etc.

Between intents the axes hold where the last take left them, with Perlin idle on top (smaller during a take).
"""
import numpy as np

from .channels import load_card, map_frame
from .idle import Idle
from .intents import Affect
from .takes import AXES, DT, Context, Habituation, Performance, choose_take, plan
from .spring import track


class Expressor:
    def __init__(self, card, seed=0, dt=DT):
        self.card = load_card(card) if isinstance(card, str) else card
        ch = self.card["channels"]
        self.orient_threshold = float(ch.get("orient_threshold", 1.2))
        self.head_lead = float(ch.get("head_lead_s", 0.22))
        self.motion_lag = float(ch.get("motion_lag_s", 0.0))  # body lag behind the command; calls wait for it
        self.rng = np.random.default_rng(seed)
        self.hab = Habituation()
        self.idle = Idle(seed)
        self.dt = dt
        self.state = {a: 0.0 for a in AXES}
        self.affect = Affect(0.4, 0.4)
        self.perf = None
        self.last_take = None
        self.history = []
        self._prev_out = None
        self._last_now = None
        self._limits = {}
        self._idle_scale = 1.0

    def submit(self, intent, now, force_take=None):
        """Start the response to an intent now. Returns the Performance (take, params, events).
        force_take is for evaluation only (the duck tilt table); the mind never passes it."""
        cur = self.current(now)
        self.affect = intent.affect
        if intent.kind == "content_idle":
            self.perf = self._settle(cur, now, intent)
            return self.perf
        novelty = 1.0 if intent.kind == "startle" else self.hab.on_call(now)
        ctx = Context(novelty=novelty, distracted=abs(cur["ATTEND.yaw"] - intent.target.yaw) > 0.6 and novelty > 0.3,
                      start=cur, orient_threshold=self.orient_threshold, head_lead=self.head_lead)
        take = force_take or choose_take(intent, ctx, self.rng, last=self.last_take)
        axes, events, params, arrival = plan(take, intent, ctx, self.rng, self._limits)
        events = [dict(e, t=round(e["t"] + self.motion_lag, 3)) for e in events]
        self.perf = Performance(take, intent.kind, now, axes, events, params, arrival, self.dt)
        if take != "startle":
            self.last_take = take
        self.history.append(dict(t=round(now, 3), intent=intent.kind, take=take, novelty=round(novelty, 3),
                                 arrival=None if arrival is None else round(arrival, 3), events=events,
                                 params={k: (round(v, 4) if isinstance(v, float) else v) for k, v in params.items()}))
        return self.perf

    def _settle(self, cur, now, intent):
        """content_idle: drift back toward rest (gaze ahead, posture neutral) slowly."""
        n = int(round(2.5 / self.dt))
        axes = {a: track(np.full(n, 0.0 if a != "ORIENT.yaw" else cur[a]), self.dt, 2.5, 1.0, x0=cur[a]) for a in AXES}
        return Performance("settle", intent.kind, now, axes, [], {}, None, self.dt)

    def current(self, now):
        if self.perf is not None:
            return self.perf.sample(now)
        return dict(self.state)

    def step(self, now):
        vals = self.current(now)
        events = []
        if self.perf is not None:
            lo = -1e9 if self._last_now is None else self._last_now - self.perf.t0
            hi = now - self.perf.t0
            events = [dict(e, t_abs=round(self.perf.t0 + e["t"], 3)) for e in self.perf.events if lo < e["t"] <= hi + 1e-9]
            if self.perf.done(now):
                self.state = vals
                self.perf = None
        busy = self.perf is not None and self.perf.take != "settle"
        self._idle_scale += ((0.25 if busy else 1.0) - self._idle_scale) * min(1.0, self.dt / 0.4)  # no step at take ends
        idle = self.idle.sample(now, self.affect.arousal, scale=self._idle_scale)
        shown = {a: vals[a] + idle.get(a, 0.0) for a in AXES}
        out = map_frame(self.card, shown, self._prev_out, self.dt)
        self._prev_out, self._last_now = out, now
        return dict(t=now, axes=shown, outputs=out, events=events, take=None if self.perf is None else self.perf.take)

    def run(self, schedule, until, t0=0.0):
        """Offline timeline: schedule = [(t, intent) or (t, intent, force_take), ...]. Returns t, axes {a: array}, outputs {o: array},
        events [...], takes [...] (the history entries of this run)."""
        sched = sorted(schedule, key=lambda s: s[0])
        n = int(round((until - t0) / self.dt)) + 1
        t = t0 + np.arange(n) * self.dt
        axes = {a: np.zeros(n) for a in AXES}
        outs, events, j = None, [], 0
        h0 = len(self.history)
        for k, now in enumerate(t):
            while j < len(sched) and sched[j][0] <= now + 1e-9:
                self.submit(sched[j][1], now, *sched[j][2:3])
                j += 1
            f = self.step(now)
            if outs is None:
                outs = {o: np.zeros(n) for o in f["outputs"]}
            for a in AXES:
                axes[a][k] = f["axes"][a]
            for o, v in f["outputs"].items():
                outs[o][k] = v
            events += f["events"]
        return dict(t=t, axes=axes, outputs=outs, events=events, takes=self.history[h0:])
