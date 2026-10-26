"""Event vocabulary, JSON-lines event log and a synthetic-day generator.

An event is {t, type, args}: t in seconds since the start of the day (float),
type from VOCAB, args a dict (room name, sentence text, primitive name...).
Types written with a parameter in the register (owner:said(text),
self:entered(room), self:did(primitive)) keep the parameter in args and are
written as "self:entered(bedroom)" only in rule patterns (see `pattern_matches`).

The vocabulary bounds what can be learned: a regularity between two things the
perception layer never reports cannot become a rule. See README "Vocabulary".
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, Iterator

# type -> name of the single argument it carries (None = no argument)
VOCAB: dict[str, str | None] = {
    # sounds (microphone classifier)
    "sound:keys": None,
    "sound:door": None,
    "sound:doorbell": None,
    "sound:footsteps": None,
    "sound:voice:owner": None,
    "sound:voice:unknown": None,
    "sound:tv": None,
    "sound:kitchen": None,
    "sound:loud": None,
    # vision
    "see:owner": None,
    "see:person": "name",
    "see:stranger": None,
    "see:object": "label",
    "see:dark": None,
    "see:light": None,
    # owner state (fused by identity + presence tracking)
    "owner:left": None,
    "owner:returned": None,
    "owner:sat": None,
    "owner:went_to_bed": None,
    "owner:woke": None,
    "owner:ate": None,
    # owner speech (cloud speech-to-text, already transcribed)
    "owner:said": "text",
    "owner:said_no": "text",
    "owner:praised": "text",
    "owner:called_name": None,
    # touch
    "touch:head": None,
    "touch:back": None,
    "touch:picked_up": None,
    "touch:put_down": None,
    # the pet itself
    "self:entered": "room",
    "self:vocalised": "kind",
    "self:did": "primitive",
    "self:fell": None,
    "self:got_up": None,
    "self:battery_low": None,
    "self:charging": None,
    "self:woke": None,
    "self:slept": None,
    # world
    "time:hour": "hour",
    "weather:rain": None,
}

ROOMS = ("living_room", "kitchen", "bedroom", "hallway", "bathroom")


@dataclass
class Event:
    t: float
    type: str
    args: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_dict(d: dict) -> "Event":
        return Event(float(d["t"]), str(d["type"]), dict(d.get("args") or {}))


def validate(ev: Event) -> None:
    if ev.type not in VOCAB:
        raise ValueError(f"unknown event type {ev.type!r}")
    key = VOCAB[ev.type]
    if key is not None and key not in ev.args:
        raise ValueError(f"{ev.type} needs args.{key}")


def write_log(path: str | Path, events: Iterable[Event]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for ev in events:
            validate(ev)
            f.write(ev.to_json() + "\n")


def read_log(path: str | Path) -> list[Event]:
    with Path(path).open() as f:
        return [Event.from_dict(json.loads(line)) for line in f if line.strip()]


def label(ev: Event) -> str:
    """Human/pattern label: 'self:entered(bedroom)', 'owner:said_no', ..."""
    key = VOCAB.get(ev.type)
    if key and key != "text" and key in ev.args:
        return f"{ev.type}({ev.args[key]})"
    return ev.type


def parse_pattern(pat: str) -> tuple[str, str | None]:
    """'self:entered(bedroom)' -> ('self:entered', 'bedroom'); 'sound:keys' -> ('sound:keys', None)."""
    pat = pat.strip()
    if pat.endswith(")") and "(" in pat:
        base, arg = pat[:-1].split("(", 1)
        return base, arg
    return pat, None


def pattern_matches(pat: str, ev: Event) -> bool:
    base, arg = parse_pattern(pat)
    if ev.type != base:
        return False
    if arg is None:
        return True
    key = VOCAB.get(base)
    return key is not None and str(ev.args.get(key)) == arg


def is_known_pattern(pat: str) -> bool:
    base, _ = parse_pattern(pat)
    return base in VOCAB


def fmt_t(t: float) -> str:
    h, rem = divmod(int(t), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ---------------------------------------------------------------- synthetic days

NO_SENTENCES = ("No!", "Hey, not in here.", "Out of the bedroom, buddy.", "不行，出去。", "No no no.")
PRAISE_SENTENCES = ("Good duck!", "Well done.", "乖。", "That's my duck.")
CHAT_SENTENCES = ("I'm making coffee.", "What a day.", "今天好累。", "Did you miss me?", "Let's see what's on TV.")


def synth_day(day: int, seed: int = 0, *, p_no: float = 0.8, spurious: bool | None = None) -> list[Event]:
    """One synthetic day with planted regularities.

    - keys -> owner:left 30-90 s later (every departure; on ~15 % of days one
      extra jingle is the owner tidying the key bowl with no departure);
    - self:entered(bedroom) -> owner:said_no within 10 s with probability p_no
      while the owner is home;
    - spurious coincidence (day 1 by default): the TV goes on twice and the
      doorbell rings 5-15 s later both times; later days have TV and no doorbell.
    Everything else is background: room wandering, TV, kitchen, chatter, touches.
    """
    rng = random.Random(seed * 1000 + day)
    ev: list[Event] = []
    if spurious is None:
        spurious = day == 1

    def add(t, typ, **args):
        ev.append(Event(round(t, 1), typ, args))

    wake = 7 * 3600 + rng.uniform(0, 1800)
    add(wake, "owner:woke")
    add(wake + 30, "self:woke")
    add(wake + 60, "sound:voice:owner")
    add(wake + 1200, "sound:kitchen")
    add(wake + 1500, "owner:ate")

    # departures: morning, and on some days a short afternoon errand
    outings = [(8.5 * 3600 + rng.uniform(0, 1800), 9 * 3600 + rng.uniform(0, 1800))]
    if rng.random() < 0.8:  # evening errand
        start = 18.5 * 3600 + rng.uniform(0, 1800)
        outings.append((start, rng.uniform(1200, 3600)))
    if rng.random() < 0.5:  # bins out, a few minutes
        outings.append((21.2 * 3600 + rng.uniform(0, 900), rng.uniform(120, 400)))
    for leave, dur in outings:
        jingle = leave - rng.uniform(30, 90)
        add(jingle, "sound:keys")
        add(leave - 5, "sound:footsteps")
        add(leave, "owner:left")
        add(leave + 2, "sound:door")
        back = leave + dur
        add(back - 3, "sound:door")
        add(back, "owner:returned")
        add(back + 2, "see:owner")
        if rng.random() < 0.5:
            add(back + 20, "owner:said", text=rng.choice(CHAT_SENTENCES))

    def home(t):
        return not any(l <= t < l + d for l, d in outings)

    # key-bowl tidy without leaving
    if rng.random() < 0.15:
        t = 20.4 * 3600 + rng.uniform(0, 1200)
        if home(t) and home(t + 120):
            add(t, "sound:keys")

    # the pet wanders between rooms all day
    t = wake + 120
    room = "living_room"
    while t < 22 * 3600:
        t += rng.uniform(600, 1800)
        nxt = rng.choice([r for r in ROOMS if r != room] + ["bedroom"])  # likes the bedroom
        room = nxt
        add(t, "self:entered", room=room)
        if room == "bedroom" and home(t) and home(t + 10) and rng.random() < p_no:
            # perception tags most "no"s itself; the rest arrive as plain speech for the fuzzy matcher
            typ = "owner:said_no" if rng.random() < 0.75 else "owner:said"
            add(t + rng.uniform(2, 9), typ, text=rng.choice(NO_SENTENCES))
            add(t + 15, "self:entered", room="hallway")
            room = "hallway"

    # touches, praise, TV, chatter while home
    for _ in range(rng.randint(4, 7)):
        t = rng.uniform(wake + 600, 22 * 3600)
        if home(t):
            add(t, "touch:head")
            if rng.random() < 0.3:
                add(t + 3, "owner:praised", text=rng.choice(PRAISE_SENTENCES))
    for _ in range(0 if spurious else rng.randint(1, 3)):
        t = rng.uniform(18 * 3600, 22.5 * 3600)
        if home(t):
            add(t, "sound:tv")
            add(t + 1, "owner:sat")
    for _ in range(rng.randint(1, 3)):
        t = rng.uniform(wake + 600, 22 * 3600)
        if home(t):
            add(t, "owner:said", text=rng.choice(CHAT_SENTENCES))
    if rng.random() < 0.3:
        add(14 * 3600, "weather:rain")

    if spurious:
        # the TV goes on twice and both times the doorbell rings seconds later (a parcel, a neighbour)
        for base in (20 * 3600 + 1900, 22 * 3600 + 300):
            if home(base) and home(base + 20):
                add(base, "sound:tv")
                add(base + 1, "owner:sat")
                add(base + rng.uniform(5, 15), "sound:doorbell")

    bed = 22.5 * 3600 + rng.uniform(0, 1800)
    add(bed, "owner:went_to_bed")
    add(bed + 60, "self:slept")
    ev.sort(key=lambda e: e.t)
    for e in ev:
        validate(e)
    return ev


def iter_days(n: int, seed: int = 0) -> Iterator[tuple[int, list[Event]]]:
    for d in range(1, n + 1):
        yield d, synth_day(d, seed)
