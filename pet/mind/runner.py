"""Live runner: pet/mind drives the duck's brain (walk_brain.py / walk_wired.py) through its control file.

    pet/.venv/bin/python -m pet.mind.runner --dry --minutes 5                       # scratch files, a fake brain, no sim
    pet/.venv/bin/python -m pet.mind.runner --sim --minutes 30 --backend claude-cli  # MuJoCo duck behind walk_brain.py
    pet/.venv/bin/python -m pet.mind.runner --robot --allow head --minutes 10        # the A7Z brain over ssh (RUNNER.md)

What it does every 0.1 s (Runner.step):
1. Readback: new rows of the brain's tick log and new stdout lines -> Readback -> events `fell`, `guard_trip`,
   `refused`, `seated`, `standing`, `handback`. The first three stop the current intention at once; a fall or a guard
   trip also stops the runner until a person has put the brain back (RUNNER.md).
2. Perception: head pads and body gyro from the rows, sound levels and camera frames from the A7Z agent, scripted
   events in the off-robot modes -> percepts -> Mind.perceive() (reflexes first, as reflex.py defines).
3. Control-file ownership: a value the runner did not write means the app (or a person) took over; the runner then
   writes nothing until the file has held an idle command (zero-command walk or plain sit) for RESUME_S.
4. Mind.tick(dt) on the wall clock: drives, abort conditions, the running step; a finished step starts the next one;
   a finished intention leaves the brain idle (zero-command walk, or plain sit when seated) until the next one, which
   the model composes in a background thread (LiveMind) while the body holds.
5. Commands: each primitive's control-file commands (executors.duck_commands) at their offsets, written whole and
   atomically; walking commands carry `for_s` so the brain stops the walk itself if the runner dies.

Nothing here knows a joint: the validator admits only card primitives, and the control file carries only modes,
velocities, head poses and ground-pick phases.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .backends import BackendError, CallLog, api_cost_usd, make_backend, parse_json_answer
from .body import BodyCard, check_condition
from .brain_link import IDLE_BY_POSTURE, SIT, WALK_ZERO, LocalLink, Readback, RemoteLink, is_idle, same_cmd
from .executors import duck_commands
from .inbox import VoiceInbox, mark_done, merge_rule, translate_task
from .metrics import rigidity
from .mind import Mind, fmt_step, percept_text
from .perception import DEFAULT_SESSION, BumpDetector, FaceAdapter, ScriptedEvents, SoundOnset, TouchDetector
from .prompt import user_prompt
from .state import EXAMPLES, SharedState, load_body_card
from .validator import validate
from .world import World, clock

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
MAC = HERE.parents[1] / "microduck-sim" / "guide" / "firmware" / "mac"
WHOLE = HERE.parents[1] / "microduck-sim" / "hardware-design-20260912" / "whole-robot-20260912"
CURRENT_STATE = HERE.parents[1] / "microduck-sim" / "CURRENT-STATE.json"
LOOP_S = 0.1
POLL_S = 0.5            # how often a waiting LiveMind looks for the model's answer
RESUME_S = 30.0         # the file must hold an idle command this long before the runner takes over again
FOREIGN_GRACE_S = 1.5   # a foreign write is classified once the brain's STOP line had time to arrive
REFUSALS_STOP = 3       # refusals within REFUSAL_WINDOW_S stop the runner (something is wrong with the body)
REFUSAL_WINDOW_S = 60.0
START_WAIT_S = 40.0
UPRIGHT_START_S = 2.0
# Primitive groups for the first robot sessions (RUNNER.md): head only, then posture, walking last.
ALLOW = {"head": {"turn_head", "look_around", "nod", "wait", "stop"},
         "sit": {"sit", "rest", "stand"},
         "walk": {"walk", "approach_owner", "wander", "bow"}}


def allowed_names(spec: str) -> set | None:
    if spec in ("all", "", None):
        return None
    names = set()
    for part in spec.split(","):
        part = part.strip()
        if part not in ALLOW:
            raise ValueError(f"--allow takes all or a list of {', '.join(ALLOW)}; got {part!r}")
        names |= ALLOW[part]
    return names


def seconds_of_day(wall: float) -> float:
    d = dt.datetime.fromtimestamp(wall)
    return d.hour * 3600 + d.minute * 60 + d.second + d.microsecond / 1e6


class LiveWorld(World):
    """The mind's world fed by perception instead of a script: who is in view is what the camera reported lately,
    the owner is home unless a leave event said otherwise, the room is unknown (the robot has no map yet)."""

    FACE_HOLD_S = 20.0

    def __init__(self, body, rng, t0, room="home"):
        self.owner_seen_until, self.stranger_seen_until = -1.0, -1.0
        super().__init__(body, rng, t0, pet_room=room)
        self.owner_room = None
        self.owner_last_room = "home"
        self.sound_direction = None

    @property
    def owner_visible(self) -> bool:
        return self.t < self.owner_seen_until and "camera" in self.body.sensor_kinds

    @property
    def stranger_present(self) -> bool:
        return self.t < self.stranger_seen_until and "camera" in self.body.sensor_kinds

    def visibility_changes(self) -> list:
        return []  # perception reports face / face_lost itself

    def move_pet(self, primitive, params):
        return None

    def observe(self, ev: dict) -> list[dict]:
        """Update what the world believes from one perception event; return the percepts for the mind."""
        kind, out = ev.get("kind"), []
        if kind == "face":
            if ev.get("who") == "stranger":
                self.stranger_seen_until = self.t + self.FACE_HOLD_S
            else:
                self.owner_seen_until = self.t + self.FACE_HOLD_S
                self.owner_home = True
                self.owner_last_seen_t = self.t
            out.append(ev)
        elif kind == "face_lost":
            self.owner_seen_until = self.t
            out.append(ev)
        elif kind == "stranger_leaves":
            self.stranger_seen_until = self.t
            out.append(ev)
        elif kind == "owner_leaves":
            self.owner_home, self.owner_seen_until = False, self.t
            out.append({"kind": "sound", "label": "door_slam", "direction": ev.get("direction", 1.0)})
        elif kind == "owner_returns":
            self.owner_home = True
            out.append({"kind": "sound", "label": "door", "direction": ev.get("direction", 1.0)})
        elif kind == "touch":
            self.touched_until = self.t + 5
            out.append(ev)
        elif kind == "lights":
            self.lights = float(ev.get("level", 1.0))
            out.append(ev)
        elif kind in ("charge_start", "charge_end"):
            self.charging = kind == "charge_start"
        else:  # sound, bump, anything else the adapters report
            out.append(ev)
        return [p for p in out if self.body.perceives(p)]


class LiveExecutor:
    """Turns a validated step into timed control-file commands on the runner's schedule."""

    def __init__(self, runner):
        self.runner = runner
        self.started = Counter()

    def start(self, step: dict) -> float:
        r = self.runner
        secs = float(step.get("seconds") or r.body.step_seconds(step["primitive"], step["params"]))
        cmds = duck_commands(step, r.world.posture)
        r.schedule = []  # a new step cancels whatever the previous step still had queued
        for off, cmd in cmds:
            cmd = dict(cmd)
            if cmd.get("mode") == "walk" and (abs(float(cmd.get("vx", 0))) > 0 or abs(float(cmd.get("vtheta", 0))) > 0):
                cmd["for_s"] = round(max(0.5, secs - off) + 1.0, 1)  # dead man: the brain stops the walk itself
            r.schedule.append((r.now + float(off), cmd, step["primitive"]))
        self.started[step["primitive"]] += 1
        r.learn("self:did", primitive=step["primitive"])
        r.log(f"  step {fmt_step(step)} for {secs:g} s: {len(cmds)} command{'s' if len(cmds) != 1 else ''}")
        return secs

    def finish(self, step: dict, body) -> None:
        posture = body.primitives[step["primitive"]].get("effects", {}).get("posture")
        if posture:
            self.runner.world.posture = posture  # expected; the brain's readback corrects it
        return None


class LiveMind(Mind):
    """Mind whose model call runs in a background thread: the loop keeps reading the body while the model thinks."""

    def __init__(self, *a, backend_timeout_s=90.0, **kw):
        super().__init__(*a, **kw)
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.pending = None  # (future, attempt, submitted_wall)
        self.backend_timeout_s = backend_timeout_s
        self.ask_count = 0

    def cancel_pending(self):
        if self.pending:
            self.log("  (the model's pending answer is dropped)")
        self.pending = None

    def _submit(self, facts, error, attempt):
        user = user_prompt(self.context(facts, error))
        rec = {"t": self.world.t, "clock": clock(self.world.t), "backend": self.backend.name, "attempt": attempt,
               "wall": round(time.time(), 1)}
        fut = self.pool.submit(self._call, self.backend, self.system, user, rec)
        self.pending = (fut, attempt, time.monotonic())
        self.ask_count += 1

    @staticmethod
    def _call(backend, system, user, rec):
        t0 = time.monotonic()
        try:
            text, usage = backend.ask(system, user)
        except BackendError as e:
            rec.update(ok=False, error=str(e)[:300], latency_s=round(time.monotonic() - t0, 3))
            return rec, None
        rec.update(usage)
        rec["latency_s"] = round(usage.get("latency_s", time.monotonic() - t0), 3)
        rec["api_cost_usd"] = api_cost_usd(usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        return rec, text

    def compose(self):
        w = self.world
        facts = w.facts(self.drives.snapshot())
        if self.backend is None or w.t < self.backend_down_until:
            self.cancel_pending()
            intent = self.compose_fallback(facts)
            if intent is not None:
                self._install(intent, "fallback", 0, facts)
            return
        if self.pending is None:
            self._submit(facts, None, 0)
            self.next_round_t = w.t + POLL_S
            return
        fut, attempt, t0 = self.pending
        if not fut.done():
            if time.monotonic() - t0 > self.backend_timeout_s:
                self.pending = None
                self.backend_down_until = w.t + 300
                self.log(f"  model answer late (> {self.backend_timeout_s:.0f} s); fallback for 5 min")
                intent = self.compose_fallback(facts)
                if intent is not None:
                    self._install(intent, "fallback", attempt, facts)
            else:
                self.next_round_t = w.t + POLL_S
            return
        self.pending = None
        rec, text = fut.result()
        if text is None:  # backend error
            self.call_log.add(rec)
            self.backend_down_until = w.t + 300
            self.log(f"  model offline ({rec.get('error', '')[:80]}); fallback for 5 min")
            intent = self.compose_fallback(facts)
            if intent is not None:
                self._install(intent, "fallback", attempt, facts)
            return
        try:
            obj = parse_json_answer(text)
            intent, errs, unchecked = validate(obj, self.body, self.skills, facts)
        except ValueError as e:
            intent, errs, unchecked = None, [f"not valid JSON: {e}"], []
        rec.update(ok=intent is not None, errors=errs, unchecked=unchecked, answer=text[:600])
        self.call_log.add(rec)
        if intent:
            intent["latency_s"] = rec["latency_s"]
            self._install(intent, "llm", attempt, facts)
            return
        error = "; ".join(errs)[:500]
        self.log(f"  model answer rejected: {error[:160]}")
        if attempt == 0:
            self._submit(facts, error, 1)
            self.next_round_t = w.t + POLL_S
            return
        intent = self.compose_fallback(facts)
        if intent is not None:
            self._install(intent, "fallback", 1, facts)


class Runner:
    def __init__(self, body: BodyCard, shared: SharedState, backend, link, out_dir: Path, mode="dry",
                 clock_fn=time.time, seed=0, events=None, resume_s=RESUME_S, today=None, perception=True,
                 face_recognise=None, round_min=10.0, inbox=None, rules_path=None):
        self.body, self.shared, self.backend, self.link, self.mode = body, shared, backend, link, mode
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.clock_fn = clock_fn
        self.now = clock_fn()
        self.t_start = self.now
        self.rng = random.Random(seed)
        self.world = LiveWorld(body, self.rng, seconds_of_day(self.now))
        self.calls = CallLog(self.out_dir / "calls.jsonl")
        self.mind = LiveMind(body, shared, self.world, backend=backend, rng=self.rng, call_log=self.calls,
                             executor=LiveExecutor(self), today=today or dt.date.fromtimestamp(self.now).isoformat(),
                             round_min=round_min)
        self.readback = Readback()
        self.schedule: list[tuple[float, dict, str]] = []
        self.last_written = None
        self.last_seen = None
        self.pending_foreign = None   # (seen_at, cmd)
        self.state = "starting"       # starting | running | yield | stopped | done
        self.state_why = ""
        self.idle_since = None
        self.resume_s = resume_s
        self.refusals = deque()
        self.counters = Counter()
        self.events: list[dict] = []
        self.commands: list[dict] = []
        self.lines: list[str] = []
        self.perception = perception
        self.touch, self.bump, self.sound = TouchDetector(), BumpDetector(), SoundOnset()
        self.face = FaceAdapter(face_recognise) if face_recognise or mode == "robot" else FaceAdapter(lambda f: [])
        self.scripted = ScriptedEvents(events, self.now) if events else None
        self.stop_flag = False
        # the voice layer's inbox (inbox.py) and pet/learn's day matcher
        self.inbox = VoiceInbox(inbox) if inbox else None
        self.inbox_next = 0.0
        self.rules_path = Path(rules_path) if rules_path else Path(shared.dir) / "rules.json"
        self.owner_task = None        # {"file", "said", "intent", "t"} while an owner request runs
        self.owner_log: list[dict] = []
        self.learn_events: list = []  # pet.learn.events.Event, the day log pet/learn reads
        self.matcher = None
        if self.inbox is not None:
            self._start_matcher()

    # ----- logging -----
    def log(self, text: str):
        self.mind.log(text)

    def event(self, ev: dict):
        rec = {"wall": round(self.now, 3), "session_s": round(self.now - self.t_start, 2), **ev}
        self.events.append(rec)
        self.counters[ev["kind"]] += 1

    # ----- control file -----
    def write(self, cmd: dict, why: str):
        if same_cmd(cmd, self.last_written):
            return
        self.link.write(cmd)
        self.last_written = self.last_seen = cmd
        self.counters["commands"] += 1
        self.commands.append({"wall": round(self.now, 3), "session_s": round(self.now - self.t_start, 2), "why": why,
                              "cmd": cmd})

    def idle_cmd(self):
        return IDLE_BY_POSTURE.get(self.world.posture)

    def write_idle(self, why="idle"):
        idle = self.idle_cmd()
        if idle is not None and not same_cmd(idle, self.last_written):
            self.write(dict(idle), why)
            self.log(f"  idle: {'zero-command walk (stand61)' if idle['mode'] == 'walk' else 'sit'} ({why})")

    def check_file(self):
        """Who holds the control file? A value the runner did not write is the brain's own stop or hand-back (a STOP
        line names it within FOREIGN_GRACE_S) or someone else's command, after which the runner yields."""
        cur = self.link.read()
        if cur is None:
            return
        if self.state not in ("running", "starting"):
            self.last_seen = cur  # paused: only remember what is there; maybe_resume() decides
            return
        if self.pending_foreign is None:
            if same_cmd(cur, self.last_written) or same_cmd(cur, self.last_seen):
                return
            self.last_seen = cur
            self.pending_foreign = (self.now, cur)
        seen_at, cmd = self.pending_foreign
        stop = self.readback.last_stop
        if stop is not None and seen_at - FOREIGN_GRACE_S <= stop[0] <= self.now and brain_value(stop[1], cmd):
            self.pending_foreign = None
            self.last_written = cmd
            self.log(f"  brain wrote the file itself: {stop[1]} ({stop[2]})")
            return
        if self.now - seen_at < FOREIGN_GRACE_S:
            return  # the STOP line may still be on its way
        self.pending_foreign = None
        self.enter_yield(cmd)

    def enter_yield(self, cmd):
        self.hard_stop("the control file changed to a command the runner did not write", pause=True)
        self.state, self.state_why = "yield", "app"
        self.idle_since = None
        self.event({"kind": "yield", "cmd": cmd})
        self.log(f"YIELD: the control file holds {json.dumps(cmd)} (the app or a person); the runner writes nothing "
                 f"until it has held an idle command for {self.resume_s:.0f} s")

    def maybe_resume(self):
        cur = self.link.read()
        rb = self.readback
        ok = is_idle(cur) and rb.upright() and rb.mode in ("walk", "sit") and rb.posture != "fallen" \
            and not rb.hw_fault and not rb.imu_lost
        if not ok:
            self.idle_since = None
            return
        if self.idle_since is None:
            self.idle_since = self.now
            return
        if self.now - self.idle_since < self.resume_s:
            return
        self.last_written = self.last_seen = cur
        self.pending_foreign = None
        self.world.posture = "sitting" if cur.get("mode") == "sit" else "standing"
        self.state, self.state_why = "running", ""
        self.mind.next_round_t = self.world.t
        self.mind.interrupted_note = "the runner was paused; start afresh"
        self.event({"kind": "resume", "cmd": cur, "posture": self.world.posture})
        self.log(f"RESUME: the brain has held {json.dumps(cur)} for {self.resume_s:.0f} s, {self.world.posture}")

    # ----- stops -----
    def hard_stop(self, why: str, pause: bool):
        self.schedule = []
        m = self.mind
        cur = m.current or m.paused
        if cur:
            self.log(f"  STOP '{cur['intention_text']}' at step {cur['idx'] + 1}/{len(cur['steps'])}: {why}")
        m.current = m.paused = None
        m.reflex, m.reflex_end, m.salient = [], None, False
        m.cancel_pending()
        m.interrupted_note = f"stopped: {why}"
        m.next_round_t = self.world.t + 3
        if pause:
            self.state = "stopped"
            self.state_why = why
            self.idle_since = None

    def on_brain_event(self, ev: dict):
        k = ev["kind"]
        self.event(ev)
        if k == "fell":
            self.learn("self:fell")
            self.world.posture = "lying"
            self.hard_stop(f"fell (gravity z {ev['gb'][2]:+.2f}, tilt {ev.get('tilt_deg')} deg)", pause=True)
            self.log("FELL: the runner writes nothing until a person has righted the duck and put the brain back in "
                     "walk mode at zero command (RUNNER.md)")
        elif k == "guard_trip":
            self.hard_stop(f"guard trip: {ev['why']}", pause=True)
            self.log(f"GUARD TRIP: {ev['why']}; the runner writes nothing until the brain is back in walk mode at "
                     f"zero command for {self.resume_s:.0f} s")
        elif k == "refused":
            self.refusals.append(self.now)
            while self.refusals and self.now - self.refusals[0] > REFUSAL_WINDOW_S:
                self.refusals.popleft()
            if ev.get("what") == "sit":
                self.world.posture = "standing"  # the seat never happened
            self.hard_stop(f"the brain refused {ev.get('what')}: {ev.get('why')}", pause=False)
            if len(self.refusals) >= REFUSALS_STOP:
                self.state, self.state_why = "stopped", f"{len(self.refusals)} refusals in {REFUSAL_WINDOW_S:.0f} s"
                self.log(f"STOPPED: {self.state_why}; the body is not doing what it is told, check it before resuming")
            else:
                self.write_idle("after a refusal")
        elif k == "seated":
            self.world.posture = "sitting"
            self.log("  body: seated")
        elif k == "standing":
            self.world.posture = "standing"
            self.log(f"  body: standing (after {ev.get('after')})")
        elif k in ("brain_mode", "brain_waits", "getup", "battery_low", "brain_cleared", "handback"):
            self.log(f"  brain: {ev.get('mode') or ev.get('why') or ev.get('what') or k}")

    # ----- perception -----
    MODE_SETTLE_S = 3.0

    def still(self) -> bool:
        """The body is meant to hold still: no walking, no posture change under way, and the brain's mode has not just
        changed (a stand-up or a sit is not a bump)."""
        step = self.mind._active_step()
        if step is not None:
            prim = self.body.primitives[step["primitive"]]
            if "locomotion" in prim.get("tags", []) or prim.get("effects", {}).get("posture") or step["primitive"] == "bow":
                return False
        rb = self.readback
        if rb.mode not in ("walk", "sit") or rb.sit_phase not in (None, "seated"):
            return False
        return rb.mode_changed_t is not None and rb.row_t is not None and rb.row_t - rb.mode_changed_t >= self.MODE_SETTLE_S

    def collect_percepts(self, rows: list[dict]) -> list[dict]:
        out = []
        if self.perception:
            for row in rows:
                t = float(row.get("t", self.now))
                if "touch" in row:
                    out += self.touch.feed(row.get("touch"), t)
                out += self.bump.feed(row.get("gyro_body"), t, self.still())
            for x in self.link.extra():
                k = x.get("kind")
                if k == "sound":
                    out += self.sound.feed(x.get("db"), float(x.get("t", self.now)))
                elif k == "frame":
                    out += self.face.feed_jpeg(x.get("jpeg_b64", ""), float(x.get("t", self.now)))
                elif k == "note":
                    self.log(f"  agent: {x.get('text')}")
            out += self.face.tick(self.now)
        if self.scripted and self.state == "running":
            out += self.scripted.due(self.now)
        return out

    # ----- what pet/learn sees -----
    LEARN_OF = {"touch": "touch:head", "owner_leaves": "owner:left", "owner_returns": "owner:returned"}
    LEARN_SOUND = {"keys_jingle": "sound:keys", "doorbell": "sound:doorbell", "door_slam": "sound:door",
                   "door": "sound:door"}

    def _start_matcher(self):
        from pet.learn.match import FuzzyJudge, Matcher
        from pet.learn.state import validate_rule
        rules = []
        for r in self.shared.rules:
            try:
                rules.append(validate_rule(r))
            except (ValueError, KeyError, TypeError):
                continue
        self.matcher = Matcher(rules, FuzzyJudge(use_model=False))

    def learn(self, typ: str, **args):
        """One event in pet/learn's vocabulary, at the world clock (seconds of the day), fed to the live matcher."""
        from pet.learn.events import Event, validate as validate_event
        ev = Event(round(self.world.t, 2), typ, args)
        try:
            validate_event(ev)
        except ValueError:
            return
        self.learn_events.append(ev)
        if self.matcher is not None:
            n = len(self.matcher.log)
            self.matcher.feed(ev)
            for rec in self.matcher.log[n:]:
                self.log(f"  [learn] rule {rec['rule']}: {rec['result']} -> weight {rec['weight']:.2f}")

    def learn_percept(self, p: dict):
        k = p.get("kind")
        if k == "face":
            self.learn("see:owner" if p.get("who") == "owner" else "see:stranger")
        elif k == "sound" and p.get("label") in self.LEARN_SOUND:
            self.learn(self.LEARN_SOUND[p["label"]])
        elif k in self.LEARN_OF:
            self.learn(self.LEARN_OF[k])

    # ----- the voice layer's inbox -----
    def poll_inbox(self):
        if self.inbox is None or self.now < self.inbox_next:
            return
        self.inbox_next = self.now + POLL_S
        for line in self.inbox.new_said():
            self.on_said(line)
        for path in self.inbox.new_rules():
            self.on_rule_file(path)
        for path in self.inbox.new_tasks():
            self.on_task_file(path)

    def on_said(self, line: dict):
        text, reaction = str(line.get("text", "")), line.get("reaction") or "none"
        p = {"kind": "owner_said", "text": text, "lang": line.get("lang", ""), "result": line.get("result"),
             "reaction": reaction}
        self.event({"kind": "owner_said", "text": text, "result": p["result"], "reaction": reaction,
                    "file": line.get("file")})
        self.owner_log.append({"session_s": round(self.now - self.t_start, 1), "said": text, "result": p["result"],
                               "reaction": reaction})
        self.world.owner_home = True
        self.learn("owner:said", text=text)
        if reaction == "praised":
            self.learn("owner:praised", text=text)
        elif reaction == "said_no":
            self.learn("owner:said_no", text=text)
        if self.state == "running" and p["result"] != "task":
            self.mind.perceive([p])  # salient: the mind re-plans with the sentence in its recent events
        elif self.state == "running":  # the task file is what happens next (on_task_file); no re-plan of its own
            self.world.note(percept_text(p))
            self.mind.drives.apply_event(p)
            self.log(f"[owner_said] {percept_text(p)}")
        else:
            self.mind.drives.apply_event(p)
            self.log(f"[owner_said] {percept_text(p)} (runner {self.state})")

    def on_rule_file(self, path: Path):
        try:
            d = json.loads(path.read_text())
            rule = d["rule"]
            rules, what = merge_rule(self.rules_path, rule)
        except (OSError, ValueError, KeyError, TypeError) as e:
            mark_done(path)
            self.event({"kind": "owner_rule", "file": path.name, "outcome": f"rejected: {e}"[:200]})
            self.log(f"OWNER RULE {path.name} rejected: {e}")
            return
        mark_done(path)
        self.shared.rules = [r for r in rules if isinstance(r, dict)]  # the next intention's prompt lists it
        if self.matcher is not None:
            new = next(r for r in self.shared.rules if r.get("id") == rule["id"])
            self.matcher.rules = [r for r in self.matcher.rules
                                  if (r["trigger"], r["outcome_or_effect"]) != (new["trigger"], new["outcome_or_effect"])]
            self.matcher.rules.append(new)
            self.matcher.by_id = {r["id"]: r for r in self.matcher.rules}
        self.world.note(f"the owner's rule: {rule.get('text')}")
        self.event({"kind": "owner_rule", "file": path.name, "said": d.get("said"), "rule_id": rule.get("id"),
                    "trigger": rule.get("trigger"), "outcome": rule.get("outcome_or_effect"), "what": what})
        self.log(f"OWNER RULE \"{d.get('said')}\": {rule.get('trigger')} -> {rule.get('outcome_or_effect')} "
                 f"(w {float(rule.get('weight', 0)):.2f}, {what}; {self.rules_path.name} and the matcher)")

    def on_task_file(self, path: Path):
        done = mark_done(path)  # taken: it never runs twice, even if the runner dies mid-task
        try:
            task = json.loads(done.read_text())
        except (OSError, ValueError) as e:
            self.finish_owner({"file": done.name, "said": "?"}, f"refused: unreadable task ({e})"[:200])
            return
        ot = {"file": done.name, "said": str(task.get("said", "")).strip(), "t": self.now}
        if self.state != "running":
            self.finish_owner(ot, f"dropped: the runner is {self.state} ({self.state_why})")
            return
        if self.readback.mode == "sit" and self.world.posture == "standing":
            self.world.posture = "sitting"  # a sit under way (prep or glide) ends seated before anything else runs
            notes0 = ["the brain is in sit mode: the body counts as sitting"]
        else:
            notes0 = []
        obj, notes = translate_task(task, self.body)
        notes = notes0 + notes
        facts = self.world.facts(self.mind.drives.snapshot())
        intent, errs, _ = validate(obj, self.body, self.mind.skills, facts) if obj["steps"] else (None, ["no step "
                                                                                                         "left"], [])
        if intent is None and self.world.posture == "sitting" and "stand" in self.body.primitives and obj["steps"] \
                and any("standing" in e for e in errs):
            obj = {**obj, "steps": [{"primitive": "stand", "params": {}}] + obj["steps"]}
            intent, errs, _ = validate(obj, self.body, self.mind.skills, facts)
            notes.append("stand first (the body was sitting)")
        for n in notes:
            self.log(f"  owner task {done.name}: {n}")
        if intent is None:
            self.world.note(f"could not do what the owner asked (\"{ot['said']}\")")
            self.finish_owner(ot, f"refused: {'; '.join(errs)}"[:300])
            return
        if self.owner_task:
            self.finish_owner(self.owner_task, "replaced by a newer request")
        self.hard_stop(f"the owner asked: {ot['said']}", pause=False)
        intent["mood_note"] = "asked by the owner"
        self.mind._install(intent, "owner", 0, facts)
        ot["intent"] = intent
        self.owner_task = ot
        self.event({"kind": "owner_task", "file": done.name, "said": ot["said"], "outcome": "started",
                    "steps": [fmt_step(s) for s in intent["steps"]], "notes": notes})

    def check_owner_task(self):
        ot = self.owner_task
        if not ot:
            return
        it, m = ot["intent"], self.mind
        if m.current is it or m.paused is it:
            return
        n = len(it["steps"])
        if it["idx"] >= n:
            outcome = "done"
        elif self.state in ("stopped", "yield"):
            outcome = f"stopped at step {it['idx'] + 1}/{n}: {self.state_why}"
        else:
            last = next((ln for ln in reversed(m.lines[-20:]) if "aborts '" in ln or "STOP '" in ln), "")
            outcome = f"ended at step {it['idx'] + 1}/{n}" + (f": {last.split(': ', 1)[-1]}" if last else "")
        self.finish_owner(ot, outcome)

    def finish_owner(self, ot: dict, outcome: str):
        if self.owner_task is ot:
            self.owner_task = None
        rec = {"kind": "owner_task", "file": ot.get("file"), "said": ot.get("said"), "outcome": outcome}
        if ot.get("intent"):
            rec["steps_done"] = min(ot["intent"]["idx"], len(ot["intent"]["steps"]))
            rec["steps"] = len(ot["intent"]["steps"])
        self.event(rec)
        self.owner_log.append({"session_s": round(self.now - self.t_start, 1), "task": ot.get("file"),
                               "said": ot.get("said"), "outcome": outcome})
        if not outcome.startswith(("refused", "dropped")):  # those already left their own note
            self.world.note(f"did what the owner asked (\"{ot.get('said')}\"): {outcome}")
        self.log(f"OWNER TASK \"{ot.get('said')}\" ({ot.get('file')}): {outcome}")

    # ----- the loop -----
    def step(self, now: float | None = None):
        now = self.clock_fn() if now is None else now
        d = max(0.0, now - self.now)
        self.now = now
        rows, lines = self.link.new_rows(), self.link.new_lines()
        for ev in self.readback.feed(rows, lines, now):
            self.on_brain_event(ev)
        percepts = self.collect_percepts(rows)
        self.check_file()
        self.poll_inbox()
        for p in percepts:
            self.learn_percept(p)
        if self.state == "running":
            fed = []
            for p in percepts:
                self.event({"kind": "percept", "percept": p})
                fed += self.world.observe(p)
            if fed:
                self.mind.perceive(fed)
            if d > 0:
                self.mind.tick(d)
            self.flush()
            if not self.mind.current and not self.mind.reflex and not self.schedule and not self.pending_foreign:
                self.write_idle()
        else:
            self.world.t += d  # Mind.tick is not called: advance the clock here
            for p in percepts:  # the world and the drives still follow what happens; nothing moves
                self.event({"kind": "percept", "percept": p})
                for q in self.world.observe(p):
                    self.mind.drives.apply_event(q)
                    self.log(f"[{q['kind']}] {percept_text(q)} (runner {self.state})")
            self.mind.drives.update(d, set(), self.world.owner_visible, self.world.owner_home, self.world.hour,
                                    self.world.charging)
            self.mind.trace.append({"t": self.world.t, **self.mind.drives.snapshot()})
            if self.state == "starting":
                self._starting()
            elif self.state in ("yield", "stopped"):
                self.maybe_resume()
        self.check_owner_task()

    def flush(self):
        while self.schedule and self.schedule[0][0] <= self.now + 1e-3:
            _, cmd, prim = self.schedule.pop(0)
            self.write(cmd, prim)

    def begin(self):
        """Robot: the brain must already be in walk mode at zero command (the app put it there). Sim / dry: the runner
        writes that command itself. The session starts once rows arrive and the body has been upright for a moment."""
        cur = self.link.read()
        if self.mode == "robot":
            if not (is_idle(cur) and cur.get("mode") == "walk"):
                raise SystemExit(f"the control file holds {json.dumps(cur)}; put the brain in walk mode at zero command "
                                 "from the app first (RUNNER.md), then start the runner")
            self.last_written = self.last_seen = cur
        else:
            self.write(dict(WALK_ZERO), "start")
        self.state = "starting"
        self.upright_since = None

    def _starting(self):
        rb = self.readback
        if rb.rows_seen and rb.mode == "walk" and rb.upright():
            self.upright_since = self.upright_since or self.now
            if self.now - self.upright_since < UPRIGHT_START_S:
                return
        else:
            self.upright_since = None
            return
        self.world.posture = rb.posture = "standing"
        rb.max_tilt_deg = 0.0  # the start transient (sim drop, torque-on) is not part of the session
        self.state = "running"
        self.t_start = self.now
        self.world.t = seconds_of_day(self.now)
        self.mind.next_round_t = self.world.t
        if self.scripted:
            self.scripted.t0 = self.now  # scripted events count from the session start
        self.log(f"=== runner {self.mode}: {self.body.name}, {', '.join(sorted(self.body.primitives))}; model "
                 f"{self.backend.name if self.backend else 'none (fallback)'}; brain upright in walk mode; face "
                 f"recognition {'on' if self.face.enabled else 'off'} ===")

    def start(self, wait_s=START_WAIT_S):
        self.begin()
        t0 = self.clock_fn()
        while self.state == "starting" and self.clock_fn() - t0 < wait_s:
            self.step()
            time.sleep(LOOP_S)
        if self.state != "running":
            raise SystemExit(f"no upright walk-mode brain within {wait_s:.0f} s (state {self.state} {self.state_why}; "
                             f"rows seen {self.readback.rows_seen}, mode {self.readback.mode}, gravity {self.readback.gb})")

    def run(self, minutes: float):
        end = self.now + minutes * 60
        printed = 0
        while not self.stop_flag and self.clock_fn() < end:
            self.step()
            for line in self.mind.lines[printed:]:
                print(line, flush=True)
            printed = len(self.mind.lines)
            time.sleep(LOOP_S)
        self.close()
        for line in self.mind.lines[printed:]:
            print(line, flush=True)

    def close(self):
        if self.state == "running":
            self.schedule = []
            self.write_idle("session end")
        self.state = "done"
        self.mind.pool.shutdown(wait=False, cancel_futures=True)

    # ----- evidence -----
    def summary(self) -> dict:
        calls = self.calls.calls
        rej = [c for c in calls if "ok" in c and not c["ok"] and "error" not in c]
        ref = None
        try:
            prev = json.loads((OUT / "microduck-claude-cli" / "summary.json").read_text())
            ref = {"run": "microduck-claude-cli 2026-10-26 (scripted day, 90 awake minutes)",
                   **{k: prev["rigidity"][k] for k in ("intentions", "distinct_action_sequences",
                                                        "repeat_of_previous_rate", "sequence_entropy_bits")}}
        except (OSError, KeyError, ValueError):
            pass
        refusals = [e for e in self.events if e["kind"] == "refused"]
        return {"mode": self.mode, "backend": self.backend.name if self.backend else "fallback",
                "started": dt.datetime.fromtimestamp(self.t_start).isoformat(timespec="seconds"),
                "session_minutes": round((self.now - self.t_start) / 60, 2),
                "primitives_allowed": sorted(self.body.primitives),
                "intentions": len(self.mind.history),
                "sources": dict(Counter(h["source"] for h in self.mind.history)),
                "primitives_issued": dict(self.mind.executor.started),
                "steps_issued": sum(self.mind.executor.started.values()),
                "commands_written": self.counters["commands"],
                "model_calls": len(calls), "validator_rejections": len(rej),
                "validator_rejection_errors": [c["errors"] for c in rej][:20],
                "brain_refusals": len(refusals), "brain_refusal_lines": [(r.get("what"), r.get("why")) for r in refusals],
                "falls": self.counters["fell"], "guard_trips": self.counters["guard_trip"],
                "yields": self.counters["yield"], "handbacks": self.counters["handback"],
                "reflexes": sum(1 for ln in self.mind.lines if "reflex:" in ln),
                "percepts": dict(Counter(e["percept"].get("kind") for e in self.events if e["kind"] == "percept")),
                "brain": {"rows_seen": self.readback.rows_seen, "max_tilt_deg": round(self.readback.max_tilt_deg, 1),
                          "last_mode": self.readback.mode, "posture": self.readback.posture},
                "end_state": self.state, "end_why": self.state_why,
                "owner": {"inbox": str(self.inbox.dir) if self.inbox else None, "log": self.owner_log,
                          "tasks": dict(Counter(o["outcome"].split(":")[0].split(" at step")[0]
                                                for o in self.owner_log if "task" in o)),
                          "sentences": sum(1 for o in self.owner_log if "result" in o)},
                "learn": {"events": len(self.learn_events),
                          "matcher": self.matcher.log if self.matcher is not None else None,
                          "rules": [{"id": r["id"], "trigger": r["trigger"], "outcome": r["outcome_or_effect"],
                                     "weight": round(float(r["weight"]), 3)} for r in self.matcher.rules]
                          if self.matcher is not None else None},
                "rigidity": rigidity(self.mind.history, self.body),
                "reference_20261026": ref,
                "calls": self.calls.summary()}

    def save(self):
        d = self.out_dir
        (d / "behaviour.log").write_text("\n".join(self.mind.lines) + "\n")
        with (d / "intentions.jsonl").open("w") as f:
            for h in self.mind.history:
                f.write(json.dumps(h) + "\n")
        with (d / "events.jsonl").open("w") as f:
            for e in self.events:
                f.write(json.dumps(e) + "\n")
        with (d / "commands.jsonl").open("w") as f:
            for c in self.commands:
                f.write(json.dumps(c) + "\n")
        if self.learn_events:  # pet/learn's day-log format (events.read_log)
            with (d / "learn_events.jsonl").open("w") as f:
                for ev in self.learn_events:
                    f.write(ev.to_json() + "\n")
        s = self.summary()
        (d / "summary.json").write_text(json.dumps(s, indent=1) + "\n")
        return s


class FakeBrain:
    """Stands in for walk_brain.py in the dry run: follows the control file's modes with walk_wired.py's timing, appends
    rows (10 Hz) to the log and lines to the stdout file, and can be made to fall, stall or refuse from a test."""

    SIT_PREP_S, SIT_SETTLE_S, RISE_S = 0.8, 2.0, 1.4  # rise: walk_brain hands over on evidence, 1.3-1.5 s in sim
    GP_RATE = 0.25

    def __init__(self, cmd_path, log_path, out_path, hz=10.0):
        self.cmd_path, self.log_path, self.out_path = str(cmd_path), str(log_path), str(out_path)
        self.period = 1.0 / hz
        self.mode, self.want, self.cmd_since = "monitor", {"mode": "monitor"}, None
        self.sit_phase, self.sit_t, self.stall = None, None, False
        self.gp_phase = 0.0
        self.fallen = False
        self.gyro = [0.0, 0.0, 0.0]
        self.touch = [24000.0] * 5
        self.pressed = []
        self.next_t = None
        self.rows = 0
        open(self.log_path, "a").close()
        open(self.out_path, "a").close()

    def say(self, text):
        with open(self.out_path, "a") as f:
            f.write(text + "\n")

    def fall(self):
        self.fallen = True

    def press(self, pads):
        self.pressed = list(pads)

    def _read(self):
        try:
            with open(self.cmd_path) as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def _write(self, cmd, why):
        tmp = self.cmd_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(cmd, f)
        os.replace(tmp, self.cmd_path)
        what = {"walk": "zero command", "stand": "stand", "monitor": "hold the last goals"}.get(cmd.get("mode"), cmd.get("mode"))
        self.say(f"STOP -> {what}: {why}")

    def step(self, now: float):
        if self.next_t is None:
            self.next_t = now
        if now < self.next_t:
            return
        self.next_t += self.period
        want = self._read()
        if want is not None and want != self.want:
            self.want, self.cmd_since = want, now
        want = self.want
        wm = want.get("mode", "monitor")
        if wm == "walk" and want.get("for_s") is not None and now - self.cmd_since > float(want["for_s"]):
            zero = dict(WALK_ZERO)
            if want.get("head"):
                zero["head"] = want["head"]
            self._write(zero, f"walk for_s {want['for_s']} elapsed")
            self.want, self.cmd_since, want, wm = zero, now, zero, "walk"
        if self.mode == "sit":
            if wm == "sit":
                if self.sit_phase == "prep" and now - self.sit_t >= self.SIT_PREP_S:
                    self.sit_phase, self.sit_t = "down", now
                    self.say("sit: posture flag 1")
                elif self.sit_phase == "down" and now - self.sit_t >= self.SIT_SETTLE_S:
                    self.sit_phase = "seated"
                    if self.stall:
                        self.say("sit: STALLED, still standing on the sitstand policy: knees +0.02 / -0.03 rad")
            else:
                if self.sit_phase != "up":
                    self.sit_phase, self.sit_t = "up", now
                    self.say("sit: standing up (posture flag 0) until up, at most 4.0 s")
                elif now - self.sit_t >= self.RISE_S:
                    self.say(f"sit: up after {self.RISE_S:.2f} s, handing over")
                    self.mode, self.sit_phase = wm if wm in ("walk", "stand", "groundpick") else "walk", None
                    self.say(f"mode -> {self.mode}")
        elif wm != self.mode and wm in ("walk", "stand", "sit", "groundpick", "monitor"):
            if wm == "sit" and self.mode in ("walk", "stand"):
                self.sit_phase, self.sit_t = "prep", now
            self.mode = wm
            if wm == "groundpick":
                self.gp_phase = 0.0
            self.say(f"mode -> {wm}")
        if self.mode == "groundpick":
            target = float(want.get("phase", 0.0)) if wm == "groundpick" else 1.0
            self.gp_phase = min(target, self.gp_phase + self.GP_RATE * self.period)
            if self.gp_phase >= 0.8 and target >= 0.8:
                self._write(dict(WALK_ZERO), "ground pick complete, stand61 takes over")
                self.want, self.cmd_since, self.mode = dict(WALK_ZERO), now, "walk"
        gb = [0.9, 0.0, -0.3] if self.fallen else [-0.05, 0.01, -0.998]
        touch = [c + (1500.0 if p in self.pressed else 0.0) for c, p in zip(self.touch, ("L1", "R1", "L2", "R2", "M"))]
        row = {"t": now, "mode": self.mode, "gb": gb, "gyro_body": list(self.gyro), "sit_phase": self.sit_phase,
               "sit_stalled": (self.stall if self.sit_phase == "seated" else None), "torque": self.mode != "monitor",
               "fresh": True, "touch": touch, "touch_age": 0.0, "cmd": want,
               "policy": {"walk": "stand", "sit": "sitstand", "groundpick": "groundpick"}.get(self.mode),
               "gp_phase": self.gp_phase if self.mode == "groundpick" else None}
        with open(self.log_path, "a") as f:
            f.write(json.dumps(row) + "\n")
        self.rows += 1


class SimBrain:
    """fake_pi.py (the MuJoCo duck behind the Pi protocol) and walk_brain.py as subprocesses: the brain-in-sim path."""

    def __init__(self, out_dir: Path, udp: int, minutes: float, volt: float | None = None):
        self.out_dir = Path(out_dir)
        self.cmd = str(self.out_dir / "duck_cmd.json")
        self.log = str(self.out_dir / "brain_log.jsonl")
        self.out = str(self.out_dir / "brain.out")
        dyn = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
        walk = os.path.expanduser("~/.venvs/microduck-walk/bin/python")
        if not os.path.exists(walk):
            walk = dyn
        if not os.path.exists(dyn):
            raise SystemExit(f"{dyn} is missing: the simulated duck needs the microduck-dyn environment")
        if volt is None:
            volt = float(json.loads(CURRENT_STATE.read_text())["facts"]["servo_rail_v"]["value"])
        # the as-built mass model the robot studies use (brain_sim_check.py --model asbuilt: static_gap.cfg)
        cfg = json.loads((WHOLE / "dynamics" / "asbuilt-20261015" / "asbuilt.config.json").read_text())
        cfg["mass_manifest"] = str(WHOLE / "dynamics" / "asbuilt-20261015" / "asbuilt-mass-manifest.json")
        cfg.update(remove_old_battery_kg=0.09, kp=200, voltage=volt)
        cfg_path = self.out_dir / "sim_config.json"
        cfg_path.write_text(json.dumps(cfg, indent=1))
        self.volt = volt
        with open(self.cmd, "w") as f:
            json.dump({"mode": "monitor"}, f)
        self.fake_out = open(self.out_dir / "fake_pi.out", "w")
        self.launched = time.time()
        self.fake = subprocess.Popen([dyn, str(MAC / "fake_pi.py"), "--udp", str(udp), "--duration",
                                      str(minutes * 60 + 180), "--trace", str(self.out_dir / "sim_trace.jsonl"),
                                      "--config", str(cfg_path)], stdout=self.fake_out, stderr=subprocess.STDOUT,
                                     cwd=str(MAC))
        time.sleep(4.0)  # the model loads before the brain's first packets
        self.brain_out = open(self.out, "w")
        self.brain = subprocess.Popen([walk, str(MAC / "walk_brain.py"), "--pi", "127.0.0.1", "--udp", str(udp),
                                       "--cmd", self.cmd, "--log", self.log], stdout=self.brain_out,
                                      stderr=subprocess.STDOUT, cwd=str(MAC))

    def alive(self) -> bool:
        return self.fake.poll() is None and self.brain.poll() is None

    def stop(self):
        for p in (self.brain, self.fake):
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
        self.fake_out.close()
        self.brain_out.close()

    def falls(self, from_wall: float | None = None) -> dict:
        """From fake_pi's trace: peak trunk tilt from the session start on and the ticks past 60 deg."""
        peak, over = 0.0, 0
        skip = max(0.0, from_wall - self.launched) if from_wall else 0.0
        try:
            for ln in open(self.out_dir / "sim_trace.jsonl"):
                rec = json.loads(ln)
                if float(rec.get("t", 0.0)) < skip:
                    continue
                tilt = float(rec.get("tilt", 0.0))
                peak = max(peak, tilt)
                over += tilt > 60.0
        except (OSError, ValueError):
            pass
        return {"peak_tilt_deg": round(peak, 1), "ticks_over_60deg": over}


def brain_value(what: str, cmd) -> bool:
    """Is `cmd` what walk_wired.py writes for a STOP line naming `what`? (zero-command walk, plain stand or monitor)"""
    if not isinstance(cmd, dict):
        return False
    if what == "zero command":
        return cmd.get("mode") == "walk" and is_idle(cmd) and "for_s" not in cmd
    if what == "stand":
        return cmd == {"mode": "stand"}
    if what == "hold the last goals":
        return cmd == {"mode": "monitor"}
    return cmd.get("mode") == what


def filtered_card(card: dict, allow: set | None) -> dict:
    if allow is None:
        return card
    card = dict(card)
    card["primitives"] = [p for p in card["primitives"] if p["name"] in allow]
    return card


def pick_backend(name: str):
    if name == "auto":
        for cand in ("claude-cli",):
            try:
                return make_backend(cand)
            except (BackendError, ValueError):
                continue
        return None
    return make_backend(name)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    m = ap.add_mutually_exclusive_group(required=True)
    m.add_argument("--dry", action="store_true", help="scratch control file and a fake brain (no sim)")
    m.add_argument("--sim", action="store_true", help="the MuJoCo duck behind walk_brain.py (fake_pi.py)")
    m.add_argument("--robot", action="store_true", help="the brain on the A7Z over ssh (RUNNER.md)")
    ap.add_argument("--minutes", type=float, default=30.0)
    ap.add_argument("--backend", default="auto", help="auto (claude-cli if present) | claude-cli | anthropic | ollama | fallback")
    ap.add_argument("--body", default="duck", help="duck | live | path to a body card")
    ap.add_argument("--allow", default=None, help="all, or groups head,sit,walk (robot default: head; others: all)")
    ap.add_argument("--state-dir", default=str(EXAMPLES))
    ap.add_argument("--events", default="default", help="default | none | path to a JSONL of {at, kind, ...} (dry/sim)")
    ap.add_argument("--out", default=None, help="output directory (default pet/mind/out/runner-<date>[-<tag>])")
    ap.add_argument("--tag", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--udp", type=int, default=9870, help="sim: fake_pi port (distinct per parallel run)")
    ap.add_argument("--volt", type=float, default=None, help="sim: servo supply (default CURRENT-STATE servo_rail_v)")
    ap.add_argument("--host", default="a7z", help="robot: ssh alias of the A7Z")
    ap.add_argument("--cmd", default=None, help="robot: control file path (default: what ~/duck-run.sh passes)")
    ap.add_argument("--mic", default=None, help="robot: ALSA capture device for sound onsets, e.g. hw:0,0 (off by default)")
    ap.add_argument("--cam-hz", type=float, default=0.0, help="robot: face frames per second while the camera daemon runs")
    ap.add_argument("--inbox", default=None,
                    help="the voice layer's inbox (pet/state/inbox on the robot); rules merge into <state-dir>/rules.json")
    ap.add_argument("--resume-s", type=float, default=RESUME_S)
    ap.add_argument("--round-min", type=float, default=10.0, help="least seconds between two intentions")
    a = ap.parse_args(argv)

    mode = "dry" if a.dry else "sim" if a.sim else "robot"
    allow = allowed_names(a.allow if a.allow is not None else ("head" if mode == "robot" else "all"))
    body = BodyCard(filtered_card(load_body_card(a.body), allow))
    backend = pick_backend(a.backend)
    out_dir = Path(a.out) if a.out else OUT / f"runner-{dt.date.today():%Y%m%d}{'-' + a.tag if a.tag else ''}"
    if out_dir.exists() and mode != "robot":
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    events = None if a.events == "none" else (DEFAULT_SESSION if a.events == "default" else
                                               [(o.pop("at"), o) for o in map(json.loads, open(a.events)) if o])
    if mode == "robot":
        events = None

    fake = sim = None
    if mode == "dry":
        cmd, log, out = out_dir / "duck_cmd.json", out_dir / "brain_log.jsonl", out_dir / "brain.out"
        with open(cmd, "w") as f:
            json.dump({"mode": "monitor"}, f)
        fake = FakeBrain(cmd, log, out)
        link = LocalLink(cmd, log, out, from_start=True)
        stop = threading.Event()

        def fake_loop():
            while not stop.is_set():
                fake.step(time.time())
                time.sleep(0.02)
        threading.Thread(target=fake_loop, daemon=True).start()
    elif mode == "sim":
        sys.path.insert(0, str(MAC))
        import sim_host_guard  # one sim at a time on the MacBook; batches on the Mac mini
        sim_host_guard.one_sim_on_laptop("pet runner --sim")
        sim = SimBrain(out_dir, a.udp, a.minutes, a.volt)
        link = LocalLink(sim.cmd, sim.log, sim.out, from_start=True)
    else:
        link = RemoteLink(a.host, a.cmd, mic=a.mic, cam_hz=a.cam_hz)

    runner = Runner(body, SharedState(a.state_dir), backend, link, out_dir, mode=mode, seed=a.seed, events=events,
                    resume_s=a.resume_s, round_min=a.round_min, inbox=a.inbox)
    signal.signal(signal.SIGINT, lambda *_: setattr(runner, "stop_flag", True))
    signal.signal(signal.SIGTERM, lambda *_: setattr(runner, "stop_flag", True))
    try:
        runner.start()
        runner.run(a.minutes)
    finally:
        if mode == "dry":
            stop.set()
        if sim is not None:
            sim.stop()
        link.close()
        s = runner.save()
        if sim is not None:
            s["sim"] = {"volt": sim.volt, "model": "asbuilt-20261015 (static_gap.cfg asbuilt, 90 g old battery removed)",
                        **sim.falls(runner.t_start)}
            (out_dir / "summary.json").write_text(json.dumps(s, indent=1) + "\n")
        r = s["rigidity"]
        print(f"\n{mode}: {s['intentions']} intentions ({s['sources']}), {s['steps_issued']} steps, "
              f"{s['commands_written']} commands; validator rejections {s['validator_rejections']}, brain refusals "
              f"{s['brain_refusals']}, falls {s['falls']}, guard trips {s['guard_trips']}, yields {s['yields']}; "
              f"entropy {r.get('sequence_entropy_bits')} bits, repeat {r.get('repeat_of_previous_rate')}; "
              f"end state {s['end_state']} {s['end_why']}".strip())
        print(f"written to {out_dir}")


if __name__ == "__main__":
    main()
