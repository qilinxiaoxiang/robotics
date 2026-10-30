"""Tether survey on the robot: can the duck see its charging cable and the coil of cable on the floor?

Shawn 2026-10-30: the charging cable leaves the backpack at its lower left rear, so a cable always trails behind the
duck on its left; the duck must not trip on it and must not walk so far that the cable runs out. Before any tether
logic, this checks the input it would need. The duck turns on the spot to about +90 deg, back, to about -90 deg and
back (never a full circle, so the cable cannot wrap round its legs); at every stop it looks left, ahead and right with
the head pitched down, and each frame goes to a vision model that answers where the cable and the coil are. Frames are
saved with the brain row of the moment (joint angles, head command, IMU quaternion) for a later floor projection
(the U20CAM lens and mount calibration).

Needs the brain in walk mode at zero command and the robot upright; Shawn guards it. Stops by itself on a tilt over
20 deg, on any control-file value it did not write (the app), and on Ctrl-C, always leaving a zero-command walk.

    pet/.venv/bin/python -m pet.mind.survey            # on the Mac that has `claude`
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import math
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .brain_link import WALK_ZERO, RemoteLink, is_idle, same_cmd, tilt_deg
from .glance import ClaudeVision, where_text
from .tether import Heading

OUT = Path(__file__).resolve().parent / "out"
TURN_RATE = 0.3          # rad/s, the body card's walk vtheta limit
TURN_TIMEOUT_S = 15.0
TILT_STOP_DEG = 20.0
LOOKS = ((1.2, 0.3), (0.0, 0.3), (-1.2, 0.3))   # (head_yaw, head_pitch): left, ahead, right, pitched down 17 deg
LOOK_HOLD_S = 1.6        # head settle before the frame is taken
STOPS = (0, 90, 0, -90, 0)   # wanted heading change from the start, deg
PROMPT = ("This is one frame from the head camera of a small duck robot, about 25 cm tall, standing on the floor. Its "
          "head is turned {where}. A black charging cable leaves the robot's backpack at its lower left rear and runs "
          "over the floor to a charger; somewhere the spare cable may lie in a coil or pile. Answer with one JSON "
          "object and nothing else: {{\"cable_visible\": true|false, \"cable\": \"<where it runs in the picture, "
          "slack or taut, under 20 words>\", \"pile_visible\": true|false, \"pile_xy\": [x, y] or null (centre of the "
          "coil or pile as fractions of image width and height from the top left), \"scene\": \"<other things on "
          "the floor that matter to a small robot, under 20 words>\"}}. Image: {path}")


class Abort(Exception):
    pass


class Survey:
    def __init__(self, link, out_dir: Path):
        self.link, self.dir = link, out_dir
        (out_dir / "img").mkdir(parents=True, exist_ok=True)
        self.log = open(out_dir / "survey.jsonl", "a")
        self.row = None
        self.frame = None            # (t_a7z, jpeg, local receive time)
        self.written = None
        self.heading = None
        self.vision = ClaudeVision()
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.jobs = []
        self.stop = False

    def note(self, **rec):
        rec = {"wall": round(time.time(), 3), **rec}
        self.log.write(json.dumps(rec) + "\n")
        self.log.flush()
        print(json.dumps(rec)[:300], flush=True)

    def pump(self):
        rows = self.link.new_rows()
        self.link.new_lines()
        if rows:
            self.row = rows[-1]
        for x in self.link.extra():
            if x.get("kind") == "frame":
                self.frame = (float(x["t"]), base64.b64decode(x["jpeg_b64"]), time.time())
        cur = self.link.read()
        if self.written is not None and cur is not None and not same_cmd(cur, self.written):
            raise Abort(f"the control file changed to {json.dumps(cur)} (the app): stopping")
        if self.row is not None:
            t = tilt_deg(self.row.get("gb"))
            if t is not None and t > TILT_STOP_DEG:
                raise Abort(f"tilt {t:.1f} deg")
        if self.stop:
            raise Abort("Ctrl-C")

    def wait(self, s):
        t0 = time.time()
        while time.time() - t0 < s:
            self.pump()
            time.sleep(0.05)

    def write(self, cmd):
        self.link.write(cmd)
        self.written = cmd

    def yaw(self):
        q = self.row.get("quat") if self.row else None
        return None if q is None else math.degrees(self.heading(q))

    def turn_to(self, target_deg):
        now = self.yaw()
        err = target_deg - now
        if abs(err) < 10:
            return
        sign = 1.0 if err > 0 else -1.0
        self.write({"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": sign * TURN_RATE, "for_s": TURN_TIMEOUT_S})
        t0, start = time.time(), now
        while True:
            self.wait(0.05)
            y = self.yaw()
            if (target_deg - y) * sign <= 5:
                why = "reached"
                break
            if (y - start) * sign < -20:
                why = "turning the wrong way"
                break
            if time.time() - t0 > TURN_TIMEOUT_S:
                why = "timeout"
                break
        self.write(dict(WALK_ZERO))
        self.wait(1.5)
        self.note(kind="turn", target_deg=target_deg, start_deg=round(start, 1), end_deg=round(self.yaw(), 1),
                  seconds=round(time.time() - t0, 1), why=why)
        if why == "turning the wrong way":
            raise Abort(f"turn command {sign * TURN_RATE:+.1f} turned the other way; sign to check")

    def look(self, stop_i, yaw, pitch):
        self.write({**WALK_ZERO, "head": {"head_yaw": yaw, "head_pitch": pitch}})
        t_cmd = time.time()
        self.wait(LOOK_HOLD_S)
        while self.frame is None or self.frame[2] < t_cmd + LOOK_HOLD_S - 0.3:
            self.wait(0.1)
            if time.time() - t_cmd > LOOK_HOLD_S + 3:
                self.note(kind="look", error="no fresh frame (camera daemon not running?)")
                return
        t, jpg, _ = self.frame
        name = f"stop{stop_i}_yaw{yaw:+.1f}.jpg"
        (self.dir / "img" / name).write_bytes(jpg)
        r = self.row or {}
        rec = {"img": f"img/{name}", "stop": stop_i, "body_deg": round(self.yaw(), 1), "head_yaw": yaw,
               "head_pitch": pitch, "frame_t": t, "row_t": r.get("t"), "q": r.get("q"), "quat": r.get("quat"),
               "gb": r.get("gb")}
        where = where_text(yaw, pitch)
        self.jobs.append((rec, self.pool.submit(self.vision.describe, jpg, where, PROMPT)))
        self.note(kind="look", **{k: rec[k] for k in ("img", "body_deg", "head_yaw", "head_pitch")})

    def walk(self, vx, vtheta, seconds):
        """A robot-tested walk (vx 0.25, vtheta within +-0.3) for `seconds`, then the zero command."""
        start = self.yaw()
        self.write({"mode": "walk", "vx": vx, "vy": 0.0, "vtheta": vtheta, "for_s": seconds + 1.0})
        self.wait(seconds)
        self.write(dict(WALK_ZERO))
        self.wait(1.5)
        self.note(kind="walk", vx=vx, vtheta=vtheta, seconds=seconds, start_deg=round(start, 1),
                  end_deg=round(self.yaw(), 1))
        self.heading = Heading(self.row["quat"])   # the survey's stops count from where the walk ended

    def run(self, stops=STOPS, pre_walk=None):
        t0 = time.time()
        while self.row is None or self.row.get("quat") is None or self.frame is None:
            self.wait(0.1)
            if time.time() - t0 > 15:
                raise Abort("no brain rows with an IMU quaternion, or no camera frames, within 15 s")
        cur = self.link.read()
        if not (is_idle(cur) and cur.get("mode") == "walk"):
            raise Abort(f"the control file holds {json.dumps(cur)}; put the brain in walk at zero command first")
        if tilt_deg(self.row.get("gb")) > 10:
            raise Abort("not upright")
        self.written = cur
        self.heading = Heading(self.row["quat"])
        self.note(kind="start", cmd=cur)
        if pre_walk:
            self.walk(*pre_walk)
        for i, target in enumerate(stops):
            self.turn_to(target)
            for yaw, pitch in LOOKS:
                self.look(i, yaw, pitch)
        self.write(dict(WALK_ZERO))

    def finish(self):
        try:
            self.write(dict(WALK_ZERO))
        except Exception as e:
            print("could not write the zero walk:", e)
        results = []
        for rec, fut in self.jobs:
            try:
                text, meta = fut.result(timeout=90)
                try:
                    ans = json.loads(text[text.index("{"):text.rindex("}") + 1])
                except ValueError:
                    ans = {"raw": text}
                results.append({**rec, "answer": ans, **meta})
            except Exception as e:
                results.append({**rec, "error": str(e)[:200]})
        with open(self.dir / "looks.jsonl", "w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        for r in results:
            a = r.get("answer", {})
            print(f"{r['img']:28s} body {r['body_deg']:+6.1f}  cable {a.get('cable_visible')!s:5} {a.get('cable', '')}"
                  f" | pile {a.get('pile_visible')!s:5} {a.get('pile_xy')} | {a.get('scene', r.get('error', ''))}")
        self.log.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--host", default="a7z")
    ap.add_argument("--out", default=None)
    ap.add_argument("--pre-walk", default=None, help="vx,vtheta,seconds walked before the survey, e.g. 0.25,-0.3,2.5")
    ap.add_argument("--right-first", action="store_true", help="turn to -90 first (away from the cable side)")
    a = ap.parse_args()
    out = Path(a.out) if a.out else OUT / f"survey-{dt.datetime.now():%Y%m%d-%H%M%S}"
    link = RemoteLink(a.host, None, mic=None, cam_hz=2.0)
    s = Survey(link, out)
    signal.signal(signal.SIGINT, lambda *_: setattr(s, "stop", True))
    try:
        pre = tuple(float(x) for x in a.pre_walk.split(",")) if a.pre_walk else None
        if pre and not (0 <= pre[0] <= 0.25 and abs(pre[1]) <= 0.3 and 0 < pre[2] <= 4):
            raise SystemExit("--pre-walk outside the robot-tested range (vx 0..0.25, vtheta +-0.3, up to 4 s)")
        s.run(tuple(-x for x in STOPS) if a.right_first else STOPS, pre)
    except Abort as e:
        s.note(kind="abort", why=str(e))
    finally:
        s.finish()
        link.close()
        print("written to", out)


if __name__ == "__main__":
    main()
