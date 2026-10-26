"""Runtime body health: re-read the servos every N seconds, mark an actuator failed on a hardware error (overload,
overheating, voltage, encoder, electrical shock), on a run of unanswered reads, and rewrite the body card with the
primitives that remain; every change is appended as an event the mind can read.

Two sources:
- `--bus PORT`: polls the servos itself (dynamixel-sdk). Only when nothing else owns the port (the OMX-F arm idle).
- `--log FILE`: follows the walk_wired.py tick log (/tmp/duck_wired_log_<suffix>.jsonl) on the duck, where the brain
  owns the bus and already logs per tick which servos did not answer (`missing`) and which report a hardware error
  (`hw_faults`). Reading the log adds no traffic to the bus.

Events go to pet/state/body_events.jsonl, one JSON object per line:
  {"t": ISO time, "kind": "body_fault" | "body_recovered", "actuator": name, "id": n, "reason": text,
   "primitives": [names now on the card], "lost": [names dropped by this change], "gained": [names back]}

  python -m pet.body.health --log /tmp/duck_wired_log_x.jsonl --follow
  python -m pet.body.health --bus /dev/ttyUSB0 --baud 1000000 --every 5
  python -m pet.body.health --log pet/body/fixtures/duck_health_replay.jsonl --out /tmp/card.json   # replay
"""
import argparse
import datetime
import gzip
import json
import os
import time

from . import card, dxl_models, primitives

EVENTS_PATH = os.path.join(card.STATE_DIR, "body_events.jsonl")
LOG_REPORTED = 0x80  # a hardware error the tick log names without its error byte (bit 7 is unused by the servos)


class Health:
    """State machine per actuator. A poll is {id: {"replied": bool, "hw_error": int}}; ids absent from a poll are not
    judged that poll. `miss_limit` consecutive unanswered polls fail an actuator, `recover_after` consecutive clean
    replies bring a no-reply failure back. A hardware-error failure clears only when the servo reports no error
    again (the error byte latches until the servo is rebooted)."""

    def __init__(self, body_card, miss_limit=3, recover_after=3, card_path=None, events_path=None, tolerance=None):
        self.card = body_card
        self.by_id = {a["id"]: a for a in body_card["actuators"]}
        self.miss_limit, self.recover_after = miss_limit, recover_after
        self.card_path, self.events_path = card_path, events_path
        self.tolerance = tolerance
        self.misses = {i: 0 for i in self.by_id}
        self.clean = {i: 0 for i in self.by_id}
        self.why = {i: None for i in self.by_id}  # None, "no_reply" or "hardware_error:..."
        self.events = []

    def update(self, poll, t=None):
        changed = []
        for i, r in poll.items():
            a = self.by_id.get(i)
            if a is None:
                continue
            if not r["replied"]:
                self.misses[i] += 1
                self.clean[i] = 0
                if a["ok"] and self.misses[i] >= self.miss_limit:
                    changed.append((i, False, f"no reply for {self.misses[i]} reads"))
                    self.why[i] = "no_reply"
                continue
            self.misses[i] = 0
            if r.get("hw_error"):
                self.clean[i] = 0
                if a["ok"] or self.why[i] == "no_reply":
                    names = (["reported in the walk_wired log (hw_faults)"] if r["hw_error"] == LOG_REPORTED else
                             dxl_models.hw_error_names(r["hw_error"]) or [f"0x{r['hw_error']:02x}"])
                    changed.append((i, False, "hardware error " + ",".join(names)))
                    self.why[i] = "hardware_error"
                continue
            self.clean[i] += 1
            if not a["ok"] and self.why[i] is not None and self.clean[i] >= self.recover_after:
                changed.append((i, True, f"answers cleanly again ({self.clean[i]} reads) after {self.why[i]}"))
                self.why[i] = None
        if changed:
            self._apply(changed, t)
        return changed

    def _apply(self, changed, t):
        before = {p["name"] for p in self.card["primitives"]}
        for i, ok, _ in changed:
            self.by_id[i]["ok"] = ok
        body = self.card["name"] if self.card["name"] in {r["body"] for r in primitives.RULES} else "unknown"
        prims, _ = primitives.discover(body, self.card["actuators"], self.card["sensors"], tolerance=self.tolerance)
        self.card["primitives"] = prims
        after = {p["name"] for p in prims}
        stamp = t or datetime.datetime.now().isoformat(timespec="seconds")
        for i, ok, reason in changed:
            a = self.by_id[i]
            note = f"health {stamp}: {a['name']} (ID {i}) {'recovered' if ok else 'failed'}: {reason}"
            self.card["notes"] = [n for n in self.card["notes"] if not n.startswith(f"health ") or f"(ID {i})" not in n] + [note]
            ev = dict(t=stamp, kind="body_recovered" if ok else "body_fault", actuator=a["name"], id=i, reason=reason,
                      primitives=sorted(after), lost=sorted(before - after), gained=sorted(after - before))
            self.events.append(ev)
            if self.events_path:
                os.makedirs(os.path.dirname(os.path.abspath(self.events_path)), exist_ok=True)
                with open(self.events_path, "a") as f:
                    f.write(json.dumps(ev) + "\n")
        if self.card_path:
            card.write(self.card, self.card_path)


def log_polls(path, name_to_id, follow=False, sleep_s=0.2):
    """(t, poll) per walk_wired tick-log row: `missing` ids unanswered, `hw_faults` joint names with a hardware error
    (the log keeps the names, not the error byte, so the reason reads 'reported')."""
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as f:
        while True:
            line = f.readline()
            if not line:
                if not follow:
                    return
                time.sleep(sleep_s)
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            missing = set(r.get("missing") or [])
            faults = {name_to_id[n] for n in (r.get("hw_faults") or []) if n in name_to_id}
            poll = {i: dict(replied=i not in missing, hw_error=LOG_REPORTED if i in faults else 0)
                    for i in name_to_id.values() if i <= 14 or i in missing}  # the jaw (15) is not in the per-tick read
            t = r.get("t")
            yield (datetime.datetime.fromtimestamp(t).isoformat(timespec="milliseconds") if isinstance(t, (int, float)) else None), poll


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--log", help="walk_wired tick log to read (.jsonl or .jsonl.gz)")
    src.add_argument("--bus", help="serial port to poll directly")
    ap.add_argument("--baud", type=int, default=1000000)
    ap.add_argument("--every", type=float, default=5.0, help="s between bus polls")
    ap.add_argument("--follow", action="store_true", help="--log: keep reading as the file grows")
    ap.add_argument("--card", default=card.CARD_PATH, help="body card to start from")
    ap.add_argument("--out", default=None, help="card to rewrite (default: --card)")
    ap.add_argument("--events", default=EVENTS_PATH)
    ap.add_argument("--miss-limit", type=int, default=None, help="unanswered reads before a fault (log 25 ticks, bus 3 polls)")
    args = ap.parse_args(argv)
    c = card.load(args.card)
    out = args.out or args.card
    if args.log:
        h = Health(c, miss_limit=args.miss_limit or 25, recover_after=25, card_path=out, events_path=args.events)
        for t, poll in log_polls(args.log, {a["name"]: a["id"] for a in c["actuators"]}, follow=args.follow):
            for i, ok, reason in h.update(poll, t):
                print(f"{t} {h.by_id[i]['name']}: {'recovered' if ok else 'FAILED'} ({reason})", flush=True)
    else:
        from .bus import BusPoller
        models = {a["id"]: next(n for n, m in dxl_models.MODELS.items() if m["name"] == a["model"]) for a in c["actuators"]
                  if any(m["name"] == a["model"] for m in dxl_models.MODELS.values())}
        h = Health(c, miss_limit=args.miss_limit or 3, recover_after=3, card_path=out, events_path=args.events)
        poller = BusPoller(args.bus, args.baud, models)
        try:
            while True:
                for i, ok, reason in h.update(poller.poll()):
                    print(f"{h.by_id[i]['name']}: {'recovered' if ok else 'FAILED'} ({reason})", flush=True)
                time.sleep(args.every)
        finally:
            poller.close()
    print(f"{out}: {sum(a['ok'] for a in c['actuators'])}/{len(c['actuators'])} ok; primitives {[p['name'] for p in c['primitives']]}")


if __name__ == "__main__":
    main()
