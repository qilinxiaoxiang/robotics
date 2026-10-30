"""Find an object of a named colour, walk to it, pick it up with the learned seeing pick, and retry when it fails or the
object slips out of the beak (final-goal steps 1-4, D-019; cmu/grasp/PLAN-seeing-pickup.md, the coordinator layer).

Runs on the A7Z beside walk_wired.py, like approach.py, whose controller it reuses for finding and walking. Phases:
  approach  approach.Approach with this colour's detector: scan, walk, stop with the object about 10 cm ahead
  aim       standing, head aimed at it, MEASURE_N detections -> object centre (foot frame) and width
  align     inside the pick window around the trained spot (SPOT, +-PICK_WIN): pick; to the side: turn in place toward
            it; too far: a short walk burst; too close: give up this try (walk61 does not step back)
  pick      {"mode": "seepick", "object": ...} to walk_wired; every new frame that sees the object near the last
            estimate updates it (projected with the joints and gravity logged at its capture time); walk_wired runs
            the policy, drives the jaw on the trained timeline and hands back to stand61 after the rise
  verify    after the hand-back, walk_wired's jaw_holding over VERIFY_S: holding -> hold, else retry
  hold      watch the jaw: holding lost for SLIP_S (the jaw closed past GRIP_MIN, i.e. the object fell out) is a slip
            -> the head searches and the next try starts from approach
At most --tries picks. A walk_wired guard trip (mode monitor) or stale state ends the run.

The policy was trained with the object at SPOT = (0.087, 0.0) m from the standing root (the foot-frame origin of
duck_kin) +-3-4 cm (sim: 80 % at +-3 cm, 71 % at +-5 cm, 31-39 % when the object moves before the bite).

  ~/.venvs/duck-policy/bin/python seepick.py --color orange          on the A7Z, walk_wired running, jaw calibrated
  ~/.venvs/duck-policy/bin/python seepick.py --color green --dry     approach, aim and align only, no pick
  ~/.venvs/duck-policy/bin/python seepick.py --color green --observe 10   detections only, no motion
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import approach as ap  # noqa: E402

SPOT = (0.087, 0.0)        # m, foot frame: the trained object position (static grasp OBJECT_NOMINAL_XY)
PICK_WIN = 0.05            # m: |dx| and |dy| within this -> pick (training: 80 % at +-3 cm, 71 % at +-5 cm). Was 0.04:
                           # robot 2026-10-30 (seepick_1030-025920), object at dx +4.1 cm, 1 mm over, took a blind
                           # BURST_S walk instead and lost the ball under the beak; a pick at +-5 cm beats that burst
TURN_RATE = 0.5            # rad/s in place (approach.VTH_SPIN, robot-tested)
TURN_MIN = math.radians(8)  # a bearing under this is not worth a turn (the in-place turn coasts)
TURN_MAX_S = 3.0
BURST_S = 0.6              # one short walk burst at approach.VX when the object is too far
MAX_ALIGN = 3              # align moves per try before picking anyway (inside PICK_WIN + 2 cm) or giving up
AIM_N, AIM_S = 5, 3.0      # detections for the pick measurement, and the time allowed
SETTLE_S = 1.0             # after a stop, before measuring (approach.SETTLE_S is 1.2 after a walk)
TRACK_GATE = 0.04          # m: a detection further than this from the estimate during the pick is another object
TRACK_GATE_HERE = 0.08     # m: the gate on a --pick-here try, whose estimate is a person's guess (robot 2026-10-30: the
#                            guess was 11 cm off and three true sightings during the bend were gated away)
CMD_PERIOD = 0.1           # s: the pick command is rewritten at least this often while the camera sees the object
PICK_MAX_S = 6.0           # the seeing pick takes 3.6 s to the hand-back (phase 0.9 x 4 s)
VERIFY_S = 0.5
SLIP_S = 0.2
HOLD_WATCH_S = 10.0        # watch for a slip this long after a pick, then done
DEFAULT_SIZE = 0.013       # m, the training mean width (BODY_SLOT_MEAN)
SIZE_RANGE = (0.008, 0.03)
# OpenCV HSV (H 0-180). Orange is approach.py's tested range; the others are starting points to check on real frames
# (orange_target.py --hist on a snapshot).
COLORS = {"orange": ((5, 120, 120), (22, 255, 255)), "yellow": ((22, 100, 120), (35, 255, 255)),
          "green": ((40, 80, 60), (85, 255, 255)), "blue": ((95, 100, 60), (130, 255, 255)),
          "red": ((170, 120, 90), (180, 255, 255)), "pink": ((145, 60, 120), (170, 255, 255))}


class SeePick:
    """The coordinator; camera, state, commands and the approach controller are injected (fakes in test_seepick.py).

    state() / state_at(t) return approach.parse_state dicts plus jaw_holding and sp_phase (SeeTail)."""

    def __init__(self, kin, latest_frame, state, state_at, send, detect, make_approach, tries=3, dry=False,
                 now=time.time, log=print, pick_here=None, track_gate=None):
        self.kin, self.latest_frame, self.state_fn, self.state_at = kin, latest_frame, state, state_at
        self.send_fn, self.detect, self.make_approach = send, detect, make_approach
        self.tries, self.dry, self.now, self.log = tries, dry, now, log
        self.track_gate = track_gate  # m, overrides TRACK_GATE / TRACK_GATE_HERE when given
        self.pick_here = pick_here   # (x, y) foot frame: the object is already at the feet; the first try skips the
        #                              approach, aims there and picks on this estimate even if the camera cannot see
        #                              it (the beak's blind zone); frames seen during the bend still correct it
        self.helper = ap.Approach(kin, latest_frame, state, state_at, send, detect, now=now, log=lambda s: None,
                                  obj_radius=DEFAULT_SIZE / 2)   # its projection and head aiming, never stepped
        self.phase, self.t_phase, self.result = "start", now(), None
        self.app, self.try_n, self.align_n = None, 0, 0
        self.obj, self.meas, self.last_idx = None, [], None   # obj: dict x, y, size, t (capture time)
        self.turn = None          # (direction, target yaw change, start yaw)
        self.cmd_t, self.picked_t, self.seen_pick = 0.0, None, False
        self.holding_since, self.lost_since = None, None
        self.trace, self.attempts = [], []

    # --- helpers -----------------------------------------------------------------------------------------------
    def enter(self, phase, why=""):
        self.log(f"[{self.now():.1f}] {self.phase} -> {phase}{': ' + why if why else ''}")
        self.trace.append(dict(t=self.now(), phase=phase, why=why))
        self.phase, self.t_phase = phase, self.now()

    def finish(self, ok, why, stop=True):
        self.result = dict(ok=ok, why=why, tries=self.try_n, attempts=self.attempts)
        if stop:
            self.send_fn({"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0})
        self.enter("done" if ok else "failed", why)

    def stand(self, head=None):
        cmd = {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0}
        if head:
            cmd["head"] = {k: v for k, v in head.items() if k in ("head_pitch", "head_yaw", "neck_pitch")}
        self.send_fn(cmd)

    def measure(self, st, gate=None):
        """New frame -> (x, y, width, capture time) of the object centre in the capture-time foot frame, or None."""
        fr = self.latest_frame()
        if fr is None:
            return None
        frame, t_cap, idx = fr
        if idx == self.last_idx or self.now() - t_cap > ap.FRAME_MAX_AGE_S:
            return None
        self.last_idx = idx
        sc = self.state_at(t_cap) or st
        h, w = frame.shape[:2]
        det = self.detect(frame, ap.below_horizon(self.kin, sc, w, h))
        if det is None:
            return None
        x0, y0, bw, bh = det["bbox"]
        a = self.kin.pixel_to_ground(x0, y0 + bh, sc["q"], sc["gb"], w, h, z=0.0)
        b = self.kin.pixel_to_ground(x0 + bw, y0 + bh, sc["q"], sc["gb"], w, h, z=0.0)
        size = DEFAULT_SIZE if a is None or b is None else float(np.clip(math.dist(a, b), *SIZE_RANGE))
        self.helper.obj_radius = size / 2
        p = self.helper.project(det, sc, w, h)
        if p is None or p[0] < 0.03:   # the duck's own coloured parts project under the body
            return None
        gate_m = TRACK_GATE_HERE if (self.pick_here is not None and self.app is None) else TRACK_GATE
        if self.track_gate is not None:
            gate_m = self.track_gate   # --track-gate; 0 keeps the given estimate and only records what the camera saw
        if gate is not None and math.hypot(p[0] - gate[0], p[1] - gate[1]) > gate_m:
            self.trace.append(dict(t=self.now(), phase=self.phase, frame=idx, gated=[p[0], p[1]], t_cap=float(t_cap),
                                   bbox=[int(v) for v in det["bbox"]], u=float(det.get("base_cx", det["cx"])),
                                   v=float(y0 + bh), w=w, h=h, q=sc["q"], gb=list(sc["gb"])))  # cam_calib obs row
            return None
        m = dict(x=float(p[0]), y=float(p[1]), size=size, t=float(t_cap), cut=bool(p[2]), frame=idx)
        self.trace.append(dict(t=self.now(), phase=self.phase, meas=m))
        return m

    def pick_cmd(self):
        o = self.obj
        return {"mode": "seepick", "phase": 1.0,
                "object": {"x": round(o["x"], 4), "y": round(o["y"], 4), "size": round(o["size"], 4), "t": o["t"]}}

    # --- the machine -------------------------------------------------------------------------------------------
    def step(self):
        now = self.now()
        st = self.state_fn()
        if st is None or now - st["t"] > ap.STATE_MAX_AGE_S:
            if now - self.t_phase > ap.STALE_START_S:
                self.finish(False, "no fresh walk_wired state")
            return
        if self.phase not in ("start", "approach") and st["mode"] == "monitor":
            self.finish(False, "walk_wired is in monitor mode (a guard trip or a manual command)", stop=False)
            return
        getattr(self, "p_" + self.phase)(st, now)

    def p_start(self, st, now):
        if st.get("jaw_deg") is None and not self.dry:
            self.finish(False, "the jaw is not calibrated or not read (jaw_deg missing in walk_wired's log)", stop=False)
            return
        if self.pick_here is not None:
            self.try_n, self.align_n, self.app, self.meas = 1, 0, None, []
            self.enter("aim", f"try 1: pick here, estimate x {self.pick_here[0]:.3f} y {self.pick_here[1]:.3f}")
            return
        self.next_try("start")

    def next_try(self, why):
        if self.try_n >= self.tries:
            self.finish(False, f"{self.tries} tries used ({why})")
            return
        self.try_n += 1
        self.align_n = 0
        self.app = self.make_approach()
        self.enter("approach", f"try {self.try_n}: {why}")

    def p_approach(self, st, now):
        self.app.step()
        if self.app.phase == "done":
            self.meas = []
            self.enter("aim", f"arrived at x {self.app.result.get('x')} y {self.app.result.get('y')}")
        elif self.app.phase == "failed":
            self.finish(False, f"approach: {self.app.result.get('why')}")

    def p_aim(self, st, now):
        est = (self.obj["x"], self.obj["y"]) if self.obj else ((self.app.est if self.app else None) or self.pick_here or SPOT)
        head = self.helper.aim_head(st, *est)
        self.stand(head)
        if now - self.t_phase < SETTLE_S:
            return
        m = self.measure(st)
        if m is not None:
            self.meas.append(m)
        if len(self.meas) >= AIM_N or (now - self.t_phase > SETTLE_S + AIM_S and self.meas):
            med = {k: float(np.median([q[k] for q in self.meas])) for k in ("x", "y", "size")}
            self.obj = dict(med, t=max(q["t"] for q in self.meas))
            self.log(f"  object x {med['x']:.3f} y {med['y']:.3f} width {med['size'] * 1000:.0f} mm "
                     f"from {len(self.meas)} frames (spot {SPOT[0]:.3f} {SPOT[1]:.3f})")
            self.enter("align")
        elif now - self.t_phase > SETTLE_S + AIM_S:
            if self.pick_here is not None and self.app is None:
                self.obj = dict(x=float(self.pick_here[0]), y=float(self.pick_here[1]), size=DEFAULT_SIZE, t=now)
                self.log("  not seen (blind zone): picking on the given estimate")
                self.enter("align")
                return
            self.obj = None
            self.next_try("not seen at the pick spot")

    def p_align(self, st, now):
        dx, dy = self.obj["x"] - SPOT[0], self.obj["y"] - SPOT[1]
        win = PICK_WIN + (0.02 if self.align_n >= MAX_ALIGN else 0.0)
        if abs(dx) <= win and abs(dy) <= win:
            if self.dry:
                self.finish(True, f"dry run: would pick at dx {dx * 100:+.1f} dy {dy * 100:+.1f} cm")
                return
            self.attempts.append(dict(try_n=self.try_n, x=round(self.obj["x"], 3), y=round(self.obj["y"], 3),
                                      size=round(self.obj["size"], 3)))
            self.seen_pick, self.picked_t = False, None
            self.send_fn(self.pick_cmd())
            self.cmd_t = now
            self.enter("pick", f"dx {dx * 100:+.1f} dy {dy * 100:+.1f} cm")
            return
        if self.align_n >= MAX_ALIGN:
            self.next_try(f"still off the spot after {MAX_ALIGN} moves (dx {dx * 100:+.1f} dy {dy * 100:+.1f} cm)")
            return
        if dx < -win:
            self.next_try(f"too close (dx {dx * 100:+.1f} cm; walk61 does not step back)")
            return
        self.align_n += 1
        bearing = math.atan2(self.obj["y"], self.obj["x"])
        if abs(dy) > win and abs(bearing) >= TURN_MIN:
            self.turn = (1 if bearing > 0 else -1, abs(bearing), st["yaw"])
            self.enter("turning", f"bearing {math.degrees(bearing):+.0f} deg")
        else:
            self.enter("burst", f"dx {dx * 100:+.1f} cm")

    def p_turning(self, st, now):
        d, target, yaw0 = self.turn
        done = abs(ap.wrap(st["yaw"] - yaw0)) >= target - math.radians(3)
        if done or now - self.t_phase > TURN_MAX_S:
            self.stand()
            self.obj, self.meas = None, []
            self.enter("aim", "turned" if done else "turn time limit")
            return
        self.send_fn({"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": d * TURN_RATE, "for_s": ap.CMD_FOR_S})

    def p_burst(self, st, now):
        if now - self.t_phase < BURST_S:
            self.send_fn({"mode": "walk", "vx": ap.VX, "vy": 0.0, "vtheta": 0.0, "for_s": ap.CMD_FOR_S})
            return
        self.stand()
        self.obj, self.meas = None, []
        self.enter("aim", "burst done")

    def p_pick(self, st, now):
        if st["mode"] == "seepick":
            self.seen_pick = True
        elif self.seen_pick:   # walk_wired handed back to stand61 after the rise
            self.enter("verify")
            return
        if now - self.t_phase > PICK_MAX_S:
            self.finish(False, f"seeing pick did not hand back within {PICK_MAX_S} s (mode {st['mode']})")
            return
        if (st.get("sp_phase") or 0.0) >= 0.85:
            return   # never rewrite the pick command around the hand-back
        m = self.measure(st, gate=(self.obj["x"], self.obj["y"]))
        if m is not None:
            self.obj = m
        if m is not None or now - self.cmd_t >= CMD_PERIOD:
            self.send_fn(self.pick_cmd())
            self.cmd_t = now

    def p_verify(self, st, now):
        if now - self.t_phase < VERIFY_S:
            return
        rows = [self.state_at(t) for t in np.linspace(now - VERIFY_S, now, 5)]
        held = sum(bool(r and r.get("jaw_holding")) for r in rows) >= 3
        self.attempts[-1]["holding"] = held
        if held:
            self.holding_since, self.lost_since = now, None
            self.enter("hold", "the jaw holds something")
        else:
            self.next_try("nothing between the bills after the rise")

    def p_hold(self, st, now):
        if st.get("jaw_holding"):
            self.lost_since = None
        else:
            self.lost_since = self.lost_since or now
            if now - self.lost_since >= SLIP_S:
                self.attempts[-1]["slipped_after_s"] = round(now - self.holding_since, 2)
                self.obj = None
                self.next_try("slipped out of the beak")
                return
        if now - self.holding_since >= HOLD_WATCH_S:
            self.finish(True, "holding", stop=False)

    p_done = p_failed = lambda self, st, now: None


class SeeTail(ap.LogTail):
    """approach.LogTail plus the jaw and seeing-pick fields of walk_wired's log rows."""

    def poll(self):
        self.buf += self.f.read()
        *lines, self.buf = self.buf.split(b"\n")
        for ln in lines:
            try:
                row = json.loads(ln)
                s = ap.parse_state(row)
            except (ValueError, KeyError, TypeError):
                continue
            s.update(jaw_holding=bool(row.get("jaw_holding")), jaw_deg=row.get("jaw_deg"), sp_phase=row.get("sp_phase"))
            self.rows.append(s)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--color", default="orange", choices=sorted(COLORS))
    p.add_argument("--hsv-lo", default=None, help="override the colour table, e.g. 40,80,60")
    p.add_argument("--hsv-hi", default=None)
    p.add_argument("--cmd", default="/tmp/duck_cmd.json")
    p.add_argument("--log", default=None, help="walk_wired log (default: the --log of the running walk_wired)")
    p.add_argument("--tries", type=int, default=3)
    p.add_argument("--dry", action="store_true", help="approach, aim and align only, no pick")
    p.add_argument("--observe", type=float, default=None, help="s; print detections only, no motion")
    p.add_argument("--max-s", type=float, default=180.0)
    p.add_argument("--pick-here", nargs=2, type=float, metavar=("X", "Y"),
                   help="m, foot frame: the object is already at the feet; skip the approach and pick there")
    p.add_argument("--track-gate", type=float, default=None, metavar="M",
                   help="override the tracking gate; 0 = never move the estimate on a sighting (sightings are traced)")
    p.add_argument("--trace", default=os.path.expanduser(f"~/duck-logs/seepick_{time.strftime('%m%d-%H%M%S')}.jsonl"))
    a = p.parse_args()
    import orange_target
    from duck_kin import DuckKin
    lo, hi = COLORS[a.color]
    lo = tuple(int(v) for v in a.hsv_lo.split(",")) if a.hsv_lo else lo
    hi = tuple(int(v) for v in a.hsv_hi.split(",")) if a.hsv_hi else hi
    detect = lambda f, accept=None: orange_target.detect(f, lo, hi, ap.MIN_AREA, accept=accept)  # noqa: E731
    log_path = a.log or ap.find_log()
    if not log_path:
        sys.exit("no walk_wired log found: start the brain from the app first")
    kin = DuckKin()
    tail = SeeTail(log_path)
    cam = ap.ShmCamera()
    send = ap.send_file(a.cmd)
    ctl = SeePick(kin, cam.latest, tail.latest, tail.at, send, detect, tries=a.tries, dry=a.dry,
                  pick_here=tuple(a.pick_here) if a.pick_here else None, track_gate=a.track_gate,
                  make_approach=lambda: ap.Approach(kin, cam.latest, tail.latest, tail.at, send, detect,
                                                    log=lambda s: print("  approach " + s, flush=True)),
                  log=lambda s: print(s, flush=True))
    print(f"log {log_path}, colour {a.color} HSV {lo}..{hi}, tries {a.tries}{', dry run' if a.dry else ''}", flush=True)
    try:
        if a.observe is not None:
            end = time.time() + a.observe
            while time.time() < end:
                st = tail.latest()
                m = ctl.measure(st) if st else None
                print(f"{time.strftime('%H:%M:%S')} " + (f"x {m['x']:.3f} y {m['y']:.3f} width {m['size'] * 1000:.0f} mm"
                                                         if m else "not seen"), flush=True)
                time.sleep(0.3)
            return
        end = time.time() + a.max_s
        while ctl.phase not in ("done", "failed"):
            if time.time() > end:
                ctl.finish(False, f"time limit {a.max_s} s")
                break
            ctl.step()
            time.sleep(0.05)
    except KeyboardInterrupt:
        send({"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0})
        print("interrupted: walk at zero command written (stand61)")
    finally:
        cam.close()
    os.makedirs(os.path.dirname(a.trace), exist_ok=True)
    with open(a.trace, "w") as f:
        for row in ctl.trace:
            f.write(json.dumps(row) + "\n")
        f.write(json.dumps(dict(result=ctl.result)) + "\n")
    print(json.dumps(ctl.result))
    print(f"trace {a.trace}")


if __name__ == "__main__":
    main()
