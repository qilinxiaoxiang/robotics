"""Tether: the duck on its charging cable (Shawn 2026-10-30, docs/PET_DEPLOY_PLAN.md and PET_ROBOT_LOG.md).

The cable leaves the backpack at the lower left rear and runs back to the charger, so it trails behind the duck. Two
rules: never walk so far that the cable runs out, and never trip on it or wind it round the legs. The camera sees the
cable only when the duck faces back toward where it came from (survey 2026-10-30), so distance comes from odometry
and the look back is a check, not the measurement.

- Pose in the start frame: heading from the IMU quaternion (Heading), position from the walk the brain is executing
  (row `cmd` and `policy`), at the ground speed measured on the robot (CURRENT-STATE `walk_speed_vx025`: about
  0.15 m/s at vx 0.25 once stepping, so 0.6 m/s per unit vx). The arc's turn is taken from the IMU, not the command
  (a commanded 0.3 rad/s arc turned 7.7 deg in 2.5 s on 2026-10-30).
- Limits: distance from the start under `limit_m - margin_m`; net heading change since the start within +-SPIN_MAX_DEG
  (a full circle would wind the cable round the body).
- Turn stall: a turn on the spot that has not moved TURN_STALL_DEG in TURN_STALL_S is blocked (the wall, 2026-10-30).

Nothing here writes to the robot; runner.py asks `allow()` before every walk command and runs the return.
"""
from __future__ import annotations

import math

import numpy as np

SPEED_PER_VX = 0.15 / 0.25   # m/s per unit vx on the robot (CURRENT-STATE walk_speed_vx025)
TURN_RATE_MAX_DEG = 17.0     # deg/s, the most a 0.3 rad/s turn on the spot can give (robot: 7-13)
SPIN_MAX_DEG = 200.0
TURN_STALL_S = 4.0
TURN_STALL_DEG = 10.0
LOOK_BACK_FRACTION = 0.6     # first time out past this share of the limit: turn round and look at the cable


def rot(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def wrap_deg(a: float) -> float:
    return (a + 180.0) % 360.0 - 180.0


class Heading:
    """Heading change about the vertical from the IMU quaternion ([w, x, y, z], world z up; checked against the
    brain's body gravity 2026-10-30), positive to the left. A sensor axis that is horizontal at the start is followed in
    the world plane; the result is unwrapped, so +200 means a turn past the back on the left."""

    def __init__(self, q0):
        r0 = rot(q0)
        up_s = r0.T @ np.array([0.0, 0.0, 1.0])
        v = np.cross(up_s, [0.0, 0.0, 1.0] if abs(up_s[2]) < 0.9 else [1.0, 0.0, 0.0])
        self.v = v / np.linalg.norm(v)
        self.a0 = self._angle(r0)
        self.prev = 0.0

    def _angle(self, r):
        w = r @ self.v
        return math.atan2(w[1], w[0])

    def __call__(self, q) -> float:
        d = self._angle(rot(q)) - self.a0
        d = (d + math.pi) % (2 * math.pi) - math.pi
        while d - self.prev > math.pi:
            d -= 2 * math.pi
        while d - self.prev < -math.pi:
            d += 2 * math.pi
        self.prev = d
        return d


class Tether:
    def __init__(self, limit_m=0.8, margin_m=0.15):
        self.limit_m, self.margin_m = float(limit_m), float(margin_m)
        self.heading = None
        self.yaw_deg = 0.0           # net heading change since the start, unwrapped, + = left
        self.x = self.y = 0.0        # metres in the start frame (x = the start heading)
        self.row_t = None
        self.walked_m = 0.0
        self.max_dist_m = 0.0
        self.turn = None             # (start_t, start_yaw, sign) while a turn on the spot is commanded
        self.looked_back = False
        self.cable = None            # last look: "slack" | "taut" | "not seen"

    # ----- state -----
    @property
    def dist(self) -> float:
        return math.hypot(self.x, self.y)

    @property
    def ready(self) -> bool:
        return self.heading is not None

    def bearing_to_start_deg(self) -> float:
        """Where the start lies, relative to where the duck faces now; + = to its left."""
        if self.dist < 1e-3:
            return 180.0
        return wrap_deg(math.degrees(math.atan2(-self.y, -self.x)) - self.yaw_deg)

    def feed_rows(self, rows: list[dict]):
        for r in rows:
            q, t = r.get("quat"), r.get("t")
            if q is None or t is None:
                continue
            t = float(t)
            if self.heading is None:
                self.heading = Heading(q)
                self.row_t = t
                continue
            dt = max(0.0, min(0.5, t - self.row_t))
            self.row_t = t
            self.yaw_deg = math.degrees(self.heading(q))
            c = r.get("cmd") or {}
            vx = float(c.get("vx", 0) or 0)
            if r.get("mode") == "walk" and r.get("policy") == "walk" and vx > 0:
                ds = SPEED_PER_VX * vx * dt
                a = math.radians(self.yaw_deg)
                self.x += ds * math.cos(a)
                self.y += ds * math.sin(a)
                self.walked_m += ds
                self.max_dist_m = max(self.max_dist_m, self.dist)

    # ----- checks -----
    def allow(self, cmd: dict) -> tuple[bool, str]:
        """May the runner write this command? Walks that would end past the distance limit while moving away, and turns
        on the spot that would wind the net heading past SPIN_MAX_DEG, are refused with the reason."""
        if not self.ready or cmd.get("mode") != "walk":
            return True, ""
        vx, vth = float(cmd.get("vx", 0) or 0), float(cmd.get("vtheta", 0) or 0)
        secs = max(0.5, float(cmd.get("for_s", 5.0) or 5.0) - 1.0)  # for_s carries the executor's 1 s dead-man margin
        if vx > 0:
            a = math.radians(self.yaw_deg)
            s = SPEED_PER_VX * vx * secs
            ex, ey = self.x + s * math.cos(a), self.y + s * math.sin(a)
            end = math.hypot(ex, ey)
            lim = self.limit_m - self.margin_m
            if end > lim and end > self.dist:
                room = self.room_ahead()
                return False, (f"the cable: that walk would end {end:.2f} m from where the cable starts, the limit is "
                               f"{lim:.2f} m; straight ahead there is room for {room:.2f} m "
                               f"(about {room / (SPEED_PER_VX * 0.25):.0f} s at vx 0.25)")
        elif vth != 0:
            after = self.yaw_deg + math.copysign(min(secs * TURN_RATE_MAX_DEG, 360.0), vth)
            if abs(after) > SPIN_MAX_DEG and abs(after) > abs(self.yaw_deg):
                return False, (f"the cable: turning {'left' if vth > 0 else 'right'} could bring the net turn to "
                               f"{after:+.0f} deg and wind the cable round the legs; turn the other way")
        return True, ""

    def room_ahead(self) -> float:
        """How far the duck can walk straight on before it reaches the limit circle."""
        lim = self.limit_m - self.margin_m
        a = math.radians(self.yaw_deg)
        b = self.x * math.cos(a) + self.y * math.sin(a)
        c = self.x * self.x + self.y * self.y - lim * lim
        disc = b * b - c
        return max(0.0, -b + math.sqrt(disc)) if disc >= 0 else 0.0

    def outward_over(self) -> bool:
        """Walking away from the start beyond the limit (checked every tick while a walk runs)."""
        return self.dist > self.limit_m - self.margin_m and abs(self.bearing_to_start_deg()) > 90

    def wants_look_back(self) -> bool:
        return not self.looked_back and self.dist > LOOK_BACK_FRACTION * (self.limit_m - self.margin_m)

    def turn_cmd_started(self, t: float, sign: float):
        self.turn = (t, self.yaw_deg, sign)

    def turn_stalled(self, t: float) -> bool:
        if self.turn is None:
            return False
        t0, y0, sign = self.turn
        return t - t0 >= TURN_STALL_S and (self.yaw_deg - y0) * sign < TURN_STALL_DEG

    def turn_toward_start(self) -> float:
        """The turn (deg, + = left) that faces the start, choosing the way round that keeps the net heading smaller."""
        b = self.bearing_to_start_deg()
        options = [b, b - 360.0 if b > 0 else b + 360.0]
        return min(options, key=lambda d: (abs(self.yaw_deg + d) > SPIN_MAX_DEG, abs(d)))

    def learn_taut(self):
        """The cable looked taut here: this distance is the real limit (less a margin)."""
        self.cable = "taut"
        self.limit_m = min(self.limit_m, self.dist + self.margin_m * 0.5)

    def describe(self) -> str:
        if not self.ready:
            return ""
        b = self.bearing_to_start_deg()
        side = "behind you" if abs(b) > 150 else f"{abs(b):.0f} deg to your {'left' if b > 0 else 'right'}"
        return (f"You are {self.dist:.2f} m from where your cable starts (limit {self.limit_m - self.margin_m:.2f} m); "
                f"that point is {side}. Net turn since the start {self.yaw_deg:+.0f} deg (keep within "
                f"+-{SPIN_MAX_DEG:.0f}, or the cable winds round your legs)."
                + (f" Last look at the cable: {self.cable}." if self.cable else ""))

    def snapshot(self) -> dict:
        return {"x": round(self.x, 3), "y": round(self.y, 3), "dist": round(self.dist, 3),
                "yaw_deg": round(self.yaw_deg, 1), "walked_m": round(self.walked_m, 3),
                "max_dist_m": round(self.max_dist_m, 3), "limit_m": round(self.limit_m, 3), "cable": self.cable}


SITUATION = ("A charging cable leaves your backpack at your lower left rear and runs back over the floor to the charger, "
             "so it always trails behind you. Do not trip on it and do not walk so far that it runs out; when it is "
             "out far, walk back toward where it starts. You cannot walk backward: to go back, turn on the spot "
             "(walk with vx 0 and vtheta +-0.3; + is left, about 7-13 deg per second) and then walk. Before turning, "
             "make sure that side is clear: a turn toward a wall gets stuck. head_yaw + is left; head_pitch + is down.")
