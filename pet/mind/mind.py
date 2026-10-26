"""The mind loop: drives every second, reflexes at once, an intention every 10-30 s.

Mind.tick() advances one simulated second. Percepts (from the world or, later, the robot's perception) go through
Mind.perceive(): the drives react, pavlovian rules add expectations, a reflex from reflex.py preempts the current
intention, and salient events make the intention layer re-plan as soon as the reflex is done; minor ones let the
interrupted intention resume where it stopped.
"""
from __future__ import annotations

import random
import time

from .backends import BackendError, CallLog, api_cost_usd, parse_json_answer
from .body import BodyCard, check_condition
from .drives import DRIVES, Drives
from .executors import SimExecutor
from .fallback import FallbackPolicy
from .prompt import system_prompt, user_prompt
from .reflex import is_salient, reflex_steps
from .state import SharedState
from .validator import usable_skills, validate
from .world import clock, period

OFFLINE_RETRY_S = 300


def direction_word(d) -> str:
    if d is None:
        return ""
    return " from the left" if d > 0.3 else " from the right" if d < -0.3 else " ahead"


def fmt_step(s: dict) -> str:
    args = ", ".join(f"{k}={v:g}" for k, v in s["params"].items())
    return f"{s['primitive']}({args})"


def percept_text(p: dict) -> str:
    k = p["kind"]
    if k == "sound":
        return f"heard {p.get('label', 'a sound')}{direction_word(p.get('direction'))}"
    if k == "face":
        return "saw the owner" if p.get("who") == "owner" else f"saw a {p.get('who', 'stranger')}"
    if k == "face_lost":
        return "lost sight of the owner"
    if k == "touch":
        return f"touched on the {p.get('where', 'head')}"
    if k == "stranger_leaves":
        return "the stranger went away"
    if k == "expect":
        return f"expect: {p['outcome']} (w={p['weight']:.2f})"
    if k == "lights":
        return "lights dimmed" if p.get("level", 1) < 0.5 else "lights on"
    return k


class Mind:
    def __init__(self, body: BodyCard, shared: SharedState, world, backend=None, rng=None, call_log=None,
                 executor=None, today="2026-10-27", round_min=10.0):
        self.body, self.shared, self.world, self.backend = body, shared, world, backend
        self.rng = rng or random.Random(0)
        self.call_log = call_log or CallLog()
        self.executor = executor or SimExecutor(world)
        self.today, self.round_min = today, round_min
        self.skills = usable_skills(shared.skills, body)
        self.drives = Drives(shared.personality)
        self.fallback = FallbackPolicy(body, self.rng)
        self.system = system_prompt(body, self.skills)
        self.current = None        # running intention: dict with steps, idx, step_end, ...
        self.paused = None         # intention interrupted by a reflex
        self.reflex = []           # queued reflex steps
        self.reflex_end = None
        self.salient = False
        self.interrupted_note = None
        self.next_round_t = world.t
        self.backend_down_until = -1.0
        self.history: list[dict] = []   # every intention started (for the rigidity check)
        self.lines: list[str] = []      # readable behaviour log
        self.trace: list[dict] = []     # drives/mood per tick (for plots)

    # ----- logging -----
    def log(self, text: str):
        self.lines.append(f"{clock(self.world.t)}  {text}")

    # ----- perception and reflexes -----
    def perceive(self, percepts: list[dict]):
        for p in percepts:
            self._perceive_one(p)

    def _perceive_one(self, p: dict):
        w = self.world
        if p["kind"] == "sound":
            w.sound_direction = p.get("direction")
        text = percept_text(p)
        w.note(text)
        self.drives.apply_event(p)
        self.log(f"[{p['kind']}] {text}")
        for exp in self.shared.expectations(p):
            w.note(percept_text(exp))
            self.drives.apply_event(exp)
            self.log(f"  [rule {exp['rule']}] {percept_text(exp)}")
            self.salient = True
        if is_salient(p):
            self.salient = True
        steps = reflex_steps(p, self.body)
        if not steps:
            if self.salient and not self.reflex:
                self._replan_now("event")
            return
        facts = w.facts(self.drives.snapshot())
        intent, errs, _ = validate({"steps": steps}, self.body, {}, facts)
        if not intent:
            self.log(f"  reflex rejected: {'; '.join(errs)}")
            return
        if self.current and not self.paused:
            self.paused = self.current
            self.current = None
        self.reflex = intent["steps"]
        self.reflex_end = None
        self.log(f"  reflex: {' -> '.join(fmt_step(s) for s in self.reflex)}")

    def _replan_now(self, why: str):
        if self.paused:
            p = self.paused
            self.interrupted_note = (f"'{p['intention_text']}' at step {p['idx'] + 1}/{len(p['steps'])} "
                                     f"({why}); you may continue it or do something else")
            self.paused = None
        if self.current:
            self.current = None
        self.salient = False
        self.next_round_t = self.world.t

    # ----- time -----
    def tick(self, dt: float = 1.0):
        w = self.world
        w.t += dt
        self.perceive(w.visibility_changes())
        active = self._active_step()
        tags = set(self.body.tags(active["primitive"])) if active else set()
        snap = self.drives.snapshot()
        self.drives.update(dt, tags, w.owner_visible, w.owner_home, w.hour, w.charging)
        self.trace.append({"t": w.t, **self.drives.snapshot()})
        if self.reflex:
            self._run_reflex()
            return
        if self.current:
            self._run_current(snap)
        if not self.current and not self.reflex and w.t >= self.next_round_t:
            self.compose()

    def sleep(self, until_t: float, dt: float = 60.0, on_dock: bool = True):
        """Asleep (reflex layer only): drives integrate, no intentions, no calls. Long sleeps happen on the dock."""
        self.log(f"asleep{' on the charger' if on_dock else ''} until {clock(until_t)[:5]}")
        self.current = self.paused = None
        self.reflex = []
        w = self.world
        while w.t < until_t:
            step = min(dt, until_t - w.t)
            w.t += step
            self.drives.update(step, {"sleep"}, w.owner_visible, w.owner_home, w.hour, w.charging or on_dock)
            self.trace.append({"t": w.t, **self.drives.snapshot()})
        w.recent_events.clear()
        w.recent_behaviours.clear()
        self.next_round_t = w.t
        self.log("wakes up")

    def _active_step(self):
        if self.reflex:
            return self.reflex[0]
        if self.current:
            return self.current["steps"][self.current["idx"]]
        return None

    def _run_reflex(self):
        w = self.world
        step = self.reflex[0]
        if self.reflex_end is None:
            self.reflex_end = w.t + self.executor.start(step)
        if w.t < self.reflex_end:
            return
        self._finish_step(step)
        self.reflex.pop(0)
        self.reflex_end = None
        if self.reflex:
            return
        if self.salient:
            self._replan_now("interrupted by an event")
        elif self.paused:
            self.current, self.paused = self.paused, None
            self.current["step_end"] = None
            self.log(f"  resumes '{self.current['intention_text']}' at step {self.current['idx'] + 1}")

    def _run_current(self, prev_snap: dict):
        w, cur = self.world, self.current
        facts = w.facts(self.drives.snapshot())
        for cond in cur["abort_if"]:
            if check_condition(cond, facts) and not cur["abort_init"].get(cond):
                self.log(f"  aborts '{cur['intention_text']}': {cond}")
                self.current = None
                self.next_round_t = w.t
                return
        step = cur["steps"][cur["idx"]]
        if cur["step_end"] is None:
            cur["step_end"] = w.t + self.executor.start(step)
        if w.t < cur["step_end"]:
            return
        self._finish_step(step)
        cur["idx"] += 1
        cur["step_end"] = None
        if cur["idx"] >= len(cur["steps"]):
            self.current = None
            self.next_round_t = max(w.t, cur["started"] + self.round_min)

    def _finish_step(self, step: dict):
        room = self.executor.finish(step, self.body)
        if room:
            self.log(f"  now in the {room}")
            self.perceive(self.world.visibility_changes())

    # ----- intention layer -----
    def context(self, facts: dict, error: str | None = None) -> dict:
        w, d = self.world, self.drives
        recent = [(t, txt) for t, txt in w.recent_events if w.t - t <= 300][-8:]
        runs = []  # [time, text, signature, count]: identical consecutive intentions shown once with a count
        for t, txt, sig in [b for b in w.recent_behaviours if w.t - b[0] <= 300]:
            if runs and runs[-1][2] == sig:
                runs[-1][3] += 1
            else:
                runs.append([t, txt, sig, 1])
        beh = [f"{clock(t)[:5]} {txt}" + (f" (x{n})" if n > 1 else "") for t, txt, _, n in runs]
        words = {w.pet_room.split()[-1], period(w.hour), "owner" if w.owner_visible else "alone"}
        for _, txt in recent:
            words |= set(txt.replace("_", " ").split()) | set(txt.split())
        words |= {k.split("_")[0] for k in DRIVES if d.v[k] > 0.5}
        if w.stranger_present:
            words.add("stranger")
        return {"clock": clock(w.t)[:5], "period": period(w.hour), "posture": w.posture, "room": w.pet_room,
                "world": w.describe() + f", battery {d.battery_level:.0%}",
                "drives": ", ".join(f"{k} {d.v[k]:.2f}" for k in DRIVES),
                "mood": f"valence {d.valence:+.2f}, arousal {d.arousal:.2f}",
                "events": [f"{clock(t)[:5]} {txt}" for t, txt in recent], "behaviour": beh[-8:],
                "interrupted": self.interrupted_note,
                "plan": self.shared.active_plan(w.hour, self.today, facts),
                "rules": self.shared.rules_text(),
                "personality": str(self.shared.personality.get("traits_text", ""))[:300],
                "diary": self.shared.retrieve_diary({x.lower() for x in words}), "error": error}

    def _ask_model(self, facts: dict):
        error, unchecked = None, []
        for attempt in range(2):
            user = user_prompt(self.context(facts, error))
            rec = {"t": self.world.t, "clock": clock(self.world.t), "backend": self.backend.name, "attempt": attempt,
                   "wall": round(time.time(), 1)}
            t0 = time.monotonic()
            try:
                text, usage = self.backend.ask(self.system, user)
            except BackendError as e:
                rec.update(ok=False, error=str(e)[:300], latency_s=round(time.monotonic() - t0, 3))
                self.call_log.add(rec)
                self.backend_down_until = self.world.t + OFFLINE_RETRY_S
                self.log(f"  model offline ({str(e)[:80]}); fallback for {OFFLINE_RETRY_S // 60} min")
                return None, attempt
            rec.update(usage)
            rec["latency_s"] = round(usage.get("latency_s", 0), 3)
            rec["api_cost_usd"] = api_cost_usd(usage.get("input_tokens", 0), usage.get("output_tokens", 0))
            try:
                obj = parse_json_answer(text)
                intent, errs, unchecked = validate(obj, self.body, self.skills, facts)
            except ValueError as e:
                intent, errs = None, [f"not valid JSON: {e}"]
            rec.update(ok=intent is not None, errors=errs, unchecked=unchecked, answer=text[:600])
            self.call_log.add(rec)
            if intent:
                intent["latency_s"] = rec["latency_s"]
                return intent, attempt
            error = "; ".join(errs)[:500]
            self.log(f"  model answer rejected: {error[:160]}")
        return None, 1

    def compose(self):
        w = self.world
        facts = w.facts(self.drives.snapshot())
        intent, source, retries = None, "fallback", 0
        if self.backend is not None and w.t >= self.backend_down_until:
            intent, retries = self._ask_model(facts)
            source = "llm" if intent else "fallback"
        if intent is None:
            fb = self.fallback.compose(self.drives.snapshot(), self.drives.thresholds, facts)
            intent, errs, _ = validate(fb, self.body, self.skills, facts)
            if intent is None:  # the card offers nothing valid here: send nothing (the body holds) and retry
                self.log(f"  fallback rejected ({'; '.join(errs)}); holding without a command for 5 s")
                self.next_round_t = w.t + 5
                return
        intent.update(idx=0, step_end=None, started=w.t, source=source,
                      abort_init={c: bool(check_condition(c, facts)) for c in intent["abort_if"]})
        self.current = intent
        self.interrupted_note = None
        sig = tuple(s["primitive"] for s in intent["steps"])
        w.recent_behaviours.append((w.t, f"'{intent['intention_text']}' [{', '.join(sig)}]", sig))
        self.history.append({"t": w.t, "source": source, "text": intent["intention_text"], "signature": list(sig),
                             "steps": [fmt_step(s) for s in intent["steps"]], "mood_note": intent["mood_note"],
                             "retries": retries, "latency_s": intent.get("latency_s"),
                             "tags": sorted({t for s in intent["steps"] for t in self.body.tags(s["primitive"])}),
                             "posture_changes": sum(1 for s in intent["steps"] if self.body.primitives[
                                 s["primitive"]].get("effects", {}).get("posture")),
                             "owner_visible": facts["owner_visible"], "owner_home": facts["owner_home"],
                             "stranger_present": facts["stranger_present"]})
        lat = f" {intent['latency_s']:.1f}s" if intent.get("latency_s") is not None else ""
        abort = f"  abort if: {', '.join(intent['abort_if'])}" if intent["abort_if"] else ""
        mood = f"  ({intent['mood_note']})" if intent["mood_note"] and source == "llm" else ""
        self.log(f"INTENT [{source}{lat}] \"{intent['intention_text']}\"{mood}")
        self.log(f"    {' -> '.join(fmt_step(s) for s in intent['steps'])}{abort}")
