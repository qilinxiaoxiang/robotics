"""Full-flow demo for the final-project office hours: the whole MicroDuck story in one MuJoCo run of the robot as it
is now (microduck_rl/cmu/model/current.json: battery backpack, orange A7Z saddle), recorded. The duck works on a
table top so its look-up camera sees the standing owner's face.

  1. The owner calls "Mochi!": the duck answers with a head glance up to the owner's face (namecall.py's answer: head
     only, YAW_CAP 1.40, LOOK_PITCH 1.1, gaze held a few seconds), and quacks.
  2. The owner says "Mochi, find the orange ball": the head goes down to the table and the duck turns on the spot until
     orange_target.detect sees the ball in the rendered head-camera picture.
  3. It walks to the ball (walk61) and creeps up to the pick window in short bursts, as seepick.py does on the robot.
  4. It picks the ball with the learned seeing pick (seepick61, brain_sim_check's SeePick harness: jaw as walk_wired
     drives ID15, the drawn jaw on the hinge, camera stand-in with the training noise), turns to the owner, walks back
     with the ball between the beak pads (beak at 10 deg) and opens the beak in front of the owner.

What is real and what is scripted (printed on the video too):
  - Real runtime: walk_brain.Brain with stand61, walk61 and seepick61, walk_wired's guards, jaw and command smoothing;
    the ball is a physical 12 mm, 1 g ball until the pick holds.
  - Scripted: the two voice lines are timed triggers (no audio in the sim); walking to the ball and back steers on the
    sim's true positions (the camera only decides "found" in the search); the carry back is assisted (the ball is
    pinned between the pads after a pick that held) and was never trained or tried on the robot.

  ~/.venvs/microduck-dyn/bin/python fullflow_sim.py --out fullflow.mp4 [--seed 0] [--events events.json]
Runs on the Mac mini (renders 1280 x 720 frames with MuJoCo's offscreen renderer and pipes them to ffmpeg).
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys

SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
if os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])
import cv2  # noqa: E402
import mujoco  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brain_sim_check as bsc  # noqa: E402
from orange_target import detect  # noqa: E402

VW, VH = 1280, 720          # video frame
CW, CH = 480, 640           # head camera render (upright, approach_sim.py's), shown scaled in the corner
CAM_VFOV = 66.2             # deg, approach_sim.py (Radxa 13M / U20CAM vertical field of view upright)
FPS = 25                    # one frame every second 20 ms tick
CMD_ALPHA = 0.2             # walk_wired: the file command is smoothed every tick
# scene in the duck's start frame (x forward, y left, m)
# The demo is on a table: the duck's look-up camera (LOOK_PITCH, 30 deg above the horizontal, 66 deg tall picture)
# sees a standing adult's face from the table top; from the floor the face is at the top edge or out of the picture.
# The sim floor is the table top (z 0); the room floor, the table frame and the owner are drawn 0.75 m below it, and
# the run fails if the duck's trunk comes within TABLE_MARGIN of an edge (the sim's floor plane has no edge).
TABLE_Z = 0.75
TABLE_X, TABLE_Y = (-0.40, 1.00), (-0.70, 0.70)   # table top in the duck's start frame (m)
TABLE_MARGIN = 0.10
OWNER = (0.50, 1.10)        # owner's feet: standing 0.4 m off the table's left side, 1.21 m from the duck, 66 deg left
BALL = (0.50, -0.38)        # the orange ball: about 0.63 m away, 37 deg to the right (outside the first view)
OWNER_EYE = 1.60 - TABLE_Z  # eye height above the table top: 1.60 m standing eye height on the room floor
DELIVER_R = 0.70            # stop this far from the owner's feet: the ball lands about 0.2 m inside the table edge
CARRY_DEG = 10.0            # beak opening while carrying: the 12 mm ball between the pads (the robot held at 9.5 deg, 11-06)
LANDING = bsc.SP_LANDING_XY
PICK_X = (0.067, 0.112)     # foot-frame x window for the pick (landing spot 0.087, seepick61 trained +-3 cm)
PICK_Y = 0.02
HEAD_DEFAULT_PITCH = 0.349
LOOK_PITCH = HEAD_DEFAULT_PITCH - 1.1   # namecall.LOOK_PITCH: camera 30 deg above the horizontal
YAW_CAP = 1.40
TITLES = {"idle": "", "call": "1  Name call", "look": "1  Name call: looks at the owner",
          "command": "2  Voice command", "search": "3  Search for the orange ball", "approach": "3  Walk to the ball",
          "creep": "3  Creep into the pick window", "pick": "4  Pick it up with the beak (seepick61)",
          "check": "4  Pick it up with the beak (seepick61)", "turn_back": "5  Bring it back to the owner",
          "carry": "5  Bring it back to the owner", "backoff": "3  Creep into the pick window", "deliver": "5  Delivered", "end": "5  Delivered"}


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class Story:
    def __init__(self, out, events_path, max_s):
        self.out, self.events_path, self.max_s = out, events_path, max_s
        self.done = False
        self.phase, self.t0 = "idle", 0.0
        self.cmd_s = [0.0, 0.0, 0.0]
        self.raw = {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0}
        self.events = []
        self.sub = ("", 0.0)
        self.det = None
        self.creeps, self.burst_end = 0, None
        self.held = None
        self.frame_n = 0
        self.attempt = 1
        self.attached = False
        self.opened = False
        self.edge = None

    # ---------------------------------------------------------------- set-up
    def setup(self, m, d, sp, args, trunk):
        self.m, self.d, self.sp, self.args, self.trunk = m, d, sp, args, trunk
        p = d.xpos[trunk].copy()
        y0 = bsc._yaw(d.xquat[trunk])
        c, s = math.cos(y0), math.sin(y0)
        self.W = lambda x, y: np.array([p[0] + c * x - s * y, p[1] + s * x + c * y])
        self.owner = self.W(*OWNER)
        self.owner_yaw = math.atan2(p[1] - self.owner[1], p[0] - self.owner[0])   # the owner faces the duck
        b = self.W(*BALL)
        half = sp.obj["half"]
        d.qpos[sp.oq:sp.oq + 7] = [b[0], b[1], half[2] + 0.0005, 1, 0, 0, 0]
        d.qvel[sp.odof:sp.odof + 6] = 0
        mujoco.mj_forward(m, d)
        # the sim floor drawn as the table top: an infinite plane with a finite drawn extent (physics unchanged)
        self.table_c = self.W(0.5 * sum(TABLE_X), 0.5 * sum(TABLE_Y))
        fl = sp.floor
        m.geom_pos[fl, :2] = self.table_c
        m.geom_size[fl, :2] = [0.5 * (TABLE_X[1] - TABLE_X[0]), 0.5 * (TABLE_Y[1] - TABLE_Y[0])]
        m.geom_quat[fl] = [math.cos(y0 / 2), 0, 0, math.sin(y0 / 2)]
        m.geom_matid[fl] = -1
        m.geom_rgba[fl] = [0.80, 0.80, 0.78, 1.0]   # light grey: a wood brown reads as orange to the detector
        self.y0 = y0
        self.p0 = p.copy()
        m.vis.global_.offwidth, m.vis.global_.offheight = max(VW, CW), max(VH, CH)
        self.rv = mujoco.Renderer(m, height=VH, width=VW)
        self.cid = m.camera("head_camera").id
        m.cam_fovy[self.cid] = CAM_VFOV
        # aim the model camera as target_ground.DuckGeometry does: the site's x axis forward, the site's z up
        from target_ground import _CAM_IN_SITE
        Rs = np.zeros(9)
        mujoco.mju_quat2Mat(Rs, m.site_quat[m.site("head_camera").id])
        qc = np.zeros(4)
        mujoco.mju_mat2Quat(qc, (Rs.reshape(3, 3) @ _CAM_IN_SITE).ravel())
        m.cam_quat[self.cid] = qc
        self.rh = mujoco.Renderer(m, height=CH, width=CW)
        cb = int(m.cam_bodyid[self.cid])
        self.head_bodies = {b for b in range(m.nbody) if self._under(b, cb)}
        self.ev("head_camera", 0.0, body=m.body(cb).name, hidden=sorted(m.body(b).name for b in self.head_bodies))
        self.cam = mujoco.MjvCamera()
        self.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        self.cam.azimuth = math.degrees(y0) + 200.0
        self.cam.elevation = -16.0
        self.view = None
        self.ffmpeg = subprocess.Popen(
            [shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{VW}x{VH}",
             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
             self.out], stdin=subprocess.PIPE)
        self.ev("start", 0.0, ball_world=[round(float(v), 3) for v in b], owner_world=[round(float(v), 3) for v in self.owner],
                ball_half=half, ball_mass=sp.obj["mass"], ball_mu=sp.obj["mu"])

    def _under(self, b, root):
        while b > 0:
            if b == root:
                return True
            b = int(self.m.body_parentid[b])
        return False

    def ev(self, name, t, **kw):
        self.events.append(dict(ev=name, t=round(t, 2), **kw))
        print(f"[{t:6.2f}] {name} {json.dumps(kw) if kw else ''}", flush=True)

    def enter(self, phase, t, **kw):
        self.phase, self.t0 = phase, t
        self.ev(phase, t, **kw)

    # ---------------------------------------------------------------- geometry
    def foot(self, pw):
        return self.sp.foot_xy(np.asarray(pw, float))

    def ball(self):
        return self.d.xpos[self.sp.body].copy()

    def head_to(self, pw, z):
        """Absolute head command that turns the glance toward the world point (pw, z), inside the trained range."""
        f = self.foot(pw)
        yaw = max(-YAW_CAP, min(YAW_CAP, math.atan2(f[1], f[0])))
        return {"head_yaw": yaw, "head_pitch": LOOK_PITCH if z > 0.5 else HEAD_DEFAULT_PITCH}

    # ---------------------------------------------------------------- commands
    def walk(self, vx=0.0, vth=0.0, head=None):
        self.raw = {"mode": "walk", "vx": vx, "vy": 0.0, "vtheta": vth}
        if head:
            self.raw["head"] = head

    def want(self, t, want, brain):
        if t < 1.0:          # brain_sim_check's stand phase before walk mode (stand61)
            return want
        if t > self.max_s:
            self.done = True
        self.step(t, brain)
        raw = self.raw
        if raw.get("mode") == "walk":
            for k, key in enumerate(("vx", "vy", "vtheta")):
                self.cmd_s[k] += CMD_ALPHA * (float(raw.get(key, 0)) - self.cmd_s[k])
                self.cmd_s[k] = 0.0 if abs(self.cmd_s[k]) < 1e-4 else self.cmd_s[k]
            return dict(raw, vx=self.cmd_s[0], vy=self.cmd_s[1], vtheta=self.cmd_s[2])
        self.cmd_s = [0.0, 0.0, 0.0]
        return dict(raw)

    def step(self, t, brain):
        ph, dt = self.phase, t - self.t0
        sp = self.sp
        if ph == "idle":
            self.walk()
            if t >= 3.0:
                self.sub = ('Owner: "Mochi!"', t)
                self.enter("call", t)
        elif ph == "call":
            if dt >= 0.5:   # namecall.py answers inside about a second (R2): glance up to the owner, one quack
                self.enter("look", t)
                self.ev("quack", t)
        elif ph == "look":
            self.walk(head=self.head_to(self.owner, OWNER_EYE))
            if dt >= 4.0:
                self.sub = ('Owner: "Mochi, go find the orange ball!"', t)
                self.enter("command", t)
        elif ph == "command":
            self.walk(head=self.head_to(self.owner, OWNER_EYE))
            if dt >= 3.0:
                self.enter("search", t)
        elif ph == "search":
            # head down to the floor and centred, then turn on the spot (robot-tested vtheta 0.3) until the detector
            # sees the ball near the middle of the picture
            head = {"head_yaw": 0.0, "head_pitch": 0.45}
            self.walk(0.0, -0.3 if dt > 1.0 else 0.0, head)
            if int(dt / 0.02) % 50 == 0:
                f = self.foot(self.ball())
                self.ev("search_tick", t, ball_bearing_deg=round(math.degrees(math.atan2(f[1], f[0])), 1),
                        det=self.det, yaw_deg=round(math.degrees(bsc._yaw(self.d.xquat[self.trunk])), 1))
                if os.environ.get("FF_DUMP"):
                    cv2.imwrite(os.path.join(os.environ["FF_DUMP"], f"head_{t:05.1f}.jpg"), self.head_render())
            if self.det is not None and dt > 1.0 and abs(self.det[0] - CW / 2) < CW * 0.3:
                self.enter("approach", t, det=self.det)
        elif ph == "approach":
            f = self.foot(self.ball())
            bear = math.atan2(f[1], f[0])
            pitch = float(np.interp(f[0], (0.2, 0.6), (1.0, 0.45)))
            head = {"head_yaw": 0.0, "head_pitch": pitch}
            if abs(bear) > 0.35 and f[0] > 0.2:
                self.walk(0.0, 0.3 * math.copysign(1, bear), head)
            else:
                self.walk(0.25, max(-0.6, min(0.6, 1.5 * bear)), head)
            # walk straight on into the pick window: stopping at 0.2 m and creeping from a standstill left walk61
            # stepping on the spot in this sim (seed 3, 2026-11-11: eight 1.5 s bursts, no progress); the stop command
            # coasts about 3-4 cm, so it goes out at x 0.125 for the 0.087 landing spot
            if f[0] < 0.125:
                self.walk(0.0, 0.0, {"head_yaw": 0.0, "head_pitch": 1.0})
                self.enter("creep", t, foot=[round(float(v), 3) for v in f])
                self.burst_end = None
        elif ph == "creep":
            # seepick.py's walk-up: stand, look, a short burst toward the ball, stand again; pick inside the window
            f = self.foot(self.ball())
            head = {"head_yaw": 0.0, "head_pitch": 1.0}
            if self.burst_end is not None:
                if t >= self.burst_end:
                    self.burst_end, self.t0 = None, t
                    self.walk(0.0, 0.0, head)
                return
            if dt < 1.2:
                self.walk(0.0, 0.0, head)
                return
            inside = PICK_X[0] <= f[0] <= PICK_X[1] and abs(f[1]) <= PICK_Y
            if inside or self.creeps >= 8:
                self.sp_switch(t, f)
                return
            if f[0] < PICK_X[0]:     # walked over it: one short step back
                self.creeps += 1
                self.walk(-0.2, 0.0, head)
                self.phase, self.t0 = "backoff", t
                self.ev("creep_back", t, n=self.creeps, foot=[round(float(v), 3) for v in f])
                return
            self.creeps += 1
            if abs(f[1]) > PICK_Y and f[0] < 0.14:
                self.walk(0.0, 0.3 * math.copysign(1, f[1]), head)
                self.burst_end = t + min(1.2, max(0.6, abs(math.atan2(f[1], f[0])) / 0.25))
            else:
                # seepick.py's timed creeps (NUDGE_S 1.2 s from 0.135 m, BURST_MAX_S 1.5 s further out): a 0.8 s
                # burst never got walk61 stepping in this sim (seeds 1-4, 2026-11-11: four bursts at 0.134 m, no move)
                self.walk(0.25, max(-0.4, min(0.4, 2.0 * math.atan2(f[1], f[0]))), head)
                self.burst_end = t + 2.0
            self.ev("creep_burst", t, n=self.creeps, foot=[round(float(v), 3) for v in f])
            return
        elif ph == "backoff":
            if dt >= 1.5:
                self.walk(0.0, 0.0, {"head_yaw": 0.0, "head_pitch": 1.0})
                self.phase, self.t0 = "creep", t
        elif ph == "pick":
            if sp.done_t is not None and brain.mode != "seepick":
                # the hand-back: the pick's own result (held = pinched, off the floor, lifted > 1 cm)
                snap = sp.snapshot(brain)
                self.held = bool(snap["held"])
                self.ev("handback", t, attempt=self.attempt, held=self.held, snapshot=snap)
                if self.held:
                    self.attach(True, t)
                self.enter("check", t)
        elif ph == "check":
            self.walk()
            if dt >= 1.2:
                if self.held:
                    self.enter("turn_back", t)
                elif self.attempt < 3:      # seepick.py tries again: walk up and pick once more
                    self.attempt += 1
                    sp.switched, sp.done_t, sp.close_shift = None, None, 0.0
                    sp.goal_deg = bsc.walk_brain.SP_JAW_REST_DEG
                    self.args.sp_at = 1e9
                    self.creeps = 0
                    self.sub = (f"Missed. Try {self.attempt}", t)
                    self.enter("creep", t, attempt=self.attempt)
                    self.burst_end = None
                else:
                    self.enter("turn_back", t)
        elif ph == "turn_back":
            f = self.foot(self.owner)
            bear = math.atan2(f[1], f[0])
            self.walk(0.0, 0.5 * math.copysign(1, bear))
            if abs(bear) < 0.2:
                self.enter("carry", t)
        elif ph == "carry":
            f = self.foot(self.owner)
            bear = math.atan2(f[1], f[0])
            if abs(bear) > 0.4:
                self.walk(0.0, 0.3 * math.copysign(1, bear))
            else:
                self.walk(0.25, max(-0.6, min(0.6, 1.5 * bear)))
            if math.hypot(*f) < DELIVER_R:
                self.walk()
                self.enter("deliver", t, ball_z=round(float(self.ball()[2]), 4))
        elif ph == "deliver":
            self.walk(head=self.head_to(self.owner, OWNER_EYE) if dt > 1.5 else None)
            if dt >= 1.0 and not self.opened:
                self.opened = True
                sp.goal_deg = 25.0      # open the beak: the ball drops in front of the owner
                self.ev("beak_open", t)
                self.sub = ("", t)
            if self.attached and self.opened and (sp.opening_deg()[0] >= 20.0 or dt >= 1.6):
                self.attach(False, t)
                self.ev("ball_released", t)
            if dt >= 5.0:
                self.enter("end", t)
                self.done = True

    def attach(self, on, t=0.0):
        """Carry assist: after a pick that held (the sim's own grip result), the beak goes to CARRY_DEG and the ball,
        its contacts off, slides in 0.6 s from where the pick left it (pinched at the tip) to between the beak pads,
        and stays there until the beak opens in front of the owner. In every unassisted run on 2026-11-11 the tip
        pinch let go within 1.5 s of the hand-back to stand61 (README.md in fullflow-20261111/)."""
        sp, m, d = self.sp, self.m, self.d
        self.attached = on
        m.geom_contype[sp.ogeom] = 0 if on else 1
        m.geom_conaffinity[sp.ogeom] = 0 if on else 1
        if on:
            sp.goal_deg = CARRY_DEG
            self.head_id = m.body("jaw_soft").id
            R = d.xmat[self.head_id].reshape(3, 3)
            self.att_t, self.att_local = t, R.T @ (d.xpos[sp.body] - d.xpos[self.head_id])
            self.pin(t)

    def pin(self, t):
        sp, d = self.sp, self.d
        R, x = d.xmat[self.head_id].reshape(3, 3), d.xpos[self.head_id]
        pad = 0.5 * (d.site_xpos[sp.site["pad_up"]] + d.site_xpos[sp.site["pad_low"]])
        s = min(1.0, max(0.0, (t - self.att_t) / 0.6))
        s = s * s * (3 - 2 * s)
        d.qpos[sp.oq:sp.oq + 3] = (1 - s) * (x + R @ self.att_local) + s * pad
        d.qvel[sp.odof:sp.odof + 6] = 0
        mujoco.mj_forward(self.m, d)

    def sp_switch(self, t, f):
        off = [float(f[0] - LANDING[0]), float(f[1] - LANDING[1])]
        self.args.sp_offset = off      # SeePick.place() then puts the ball back exactly where it lies
        self.args.sp_at = t
        self.enter("pick", t, foot=[round(float(v), 3) for v in f], offset=[round(v, 3) for v in off], creeps=self.creeps)

    # ---------------------------------------------------------------- per tick: camera, video
    def after(self, t, brain, info, tilt):
        tick = int(round(t / 0.02))
        if self.attached:
            self.pin(t)
        tr = self.d.xpos[self.trunk]
        c, s_ = math.cos(self.y0), math.sin(self.y0)
        dx, dy = tr[0] - self.p0[0], tr[1] - self.p0[1]
        lx, ly = c * dx + s_ * dy, -s_ * dx + c * dy
        gap = min(lx - TABLE_X[0], TABLE_X[1] - lx, ly - TABLE_Y[0], TABLE_Y[1] - ly)
        self.edge = gap if self.edge is None else min(self.edge, gap)
        if gap < TABLE_MARGIN and not self.done:
            self.ev("table_edge", t, trunk_local=[round(lx, 3), round(ly, 3)], gap=round(gap, 3))
            self.done = True
        if self.phase in ("search", "approach") and tick % 4 == 0:   # the detector at 12.5 Hz
            self.det = self.detect_head()
        if tick % 2:
            return
        self.frame(t, brain, tilt)

    def detect_head(self):
        img = self.head_render(overlay=False)
        r = detect(img, min_area=6, open_px=0)
        if r is None:
            return None
        x, y, w, h = r["bbox"]
        return (float(x) + float(w) / 2, float(y) + float(h) / 2, float(w), float(h))

    def add_owner(self, scn):
        """Visual-only scenery (no collision): the room floor, the table frame under the top, and the owner standing at
        the table's side, facing the duck (eyes, nose and mouth on the side toward the duck)."""
        def put(typ, size, pos, mat, rgba):
            if scn.ngeom >= scn.maxgeom:
                return
            g = scn.geoms[scn.ngeom]
            scn.ngeom += 1
            mujoco.mjv_initGeom(g, typ, np.array(size, float), np.array(pos, float), np.asarray(mat, float).ravel(),
                                np.array(rgba, np.float32))
        B = mujoco.mjtGeom.mjGEOM_BOX
        cy, sy = math.cos(self.y0), math.sin(self.y0)
        Rt = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
        tc = np.array([self.table_c[0], self.table_c[1], 0.0])
        hx, hy = 0.5 * (TABLE_X[1] - TABLE_X[0]), 0.5 * (TABLE_Y[1] - TABLE_Y[0])
        wood, legc, room = (0.62, 0.62, 0.60, 1), (0.25, 0.25, 0.27, 1), (0.36, 0.40, 0.46, 1)
        put(B, (6.0, 6.0, 0.01), tc + np.array([0, 0, -TABLE_Z - 0.01]), np.eye(3), room)       # room floor
        put(B, (hx, hy, 0.015), tc + np.array([0, 0, -0.0155]), Rt, wood)                        # table top slab
        for sx in (-1, 1):
            for sy_ in (-1, 1):
                put(B, (0.025, 0.025, 0.5 * TABLE_Z - 0.015),
                    tc + Rt @ np.array([sx * (hx - 0.06), sy_ * (hy - 0.06), -0.5 * TABLE_Z - 0.015]), Rt, legc)
        c, s = math.cos(self.owner_yaw), math.sin(self.owner_yaw)
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        o = np.array([self.owner[0], self.owner[1], -TABLE_Z])     # the owner stands on the room floor
        jeans, shirt, skin, shoe = (0.20, 0.27, 0.42, 1), (0.85, 0.85, 0.80, 1), (0.93, 0.76, 0.62, 1), (0.15, 0.15, 0.15, 1)
        hair, eye, lip = (0.22, 0.15, 0.10, 1), (0.08, 0.08, 0.10, 1), (0.70, 0.30, 0.30, 1)
        S, C = mujoco.mjtGeom.mjGEOM_SPHERE, mujoco.mjtGeom.mjGEOM_CAPSULE
        eye_z = OWNER_EYE + TABLE_Z                                   # 1.60 m on the room floor
        parts = []
        for side in (-1, 1):
            parts.append((B, (0.13, 0.05, 0.035), (0.04, side * 0.11, 0.035), shoe))
            parts.append((C, (0.065, 0.40, 0), (0.0, side * 0.11, 0.48), jeans))
            parts.append((C, (0.045, 0.27, 0), (0.0, side * 0.25, 1.10), shirt))
            parts.append((S, (0.016, 0, 0), (0.105, side * 0.038, eye_z), eye))                  # eyes
        parts.append((B, (0.11, 0.19, 0.27), (0.0, 0.0, 1.15), shirt))
        parts.append((C, (0.045, 0.05, 0), (0.0, 0.0, 1.47), skin))                              # neck
        parts.append((S, (0.11, 0, 0), (0.0, 0.0, eye_z + 0.01), skin))                          # head
        parts.append((S, (0.108, 0, 0), (-0.03, 0.0, eye_z + 0.05), hair))                       # hair, back and top
        parts.append((S, (0.017, 0, 0), (0.112, 0.0, eye_z - 0.03), (0.86, 0.66, 0.52, 1)))     # nose
        parts.append((B, (0.006, 0.032, 0.007), (0.098, 0.0, eye_z - 0.065), lip))                # mouth
        for typ, size, pos, rgba in parts:
            put(typ, size, o + R @ np.array(pos), R, rgba)

    def head_render(self, overlay=True):
        self.rh.update_scene(self.d, camera=self.cid)
        scn = self.rh.scene
        cp = self.d.cam_xpos[self.cid]
        for i in range(scn.ngeom):   # the camera sits inside the head shell: robot geoms around it are not drawn
            g = scn.geoms[i]
            if g.objtype == mujoco.mjtObj.mjOBJ_GEOM and g.objid != self.sp.ogeom and g.objid != self.sp.floor and \
                    (self.m.geom_bodyid[g.objid] in self.head_bodies or np.linalg.norm(np.array(g.pos) - cp) < 0.07):
                g.rgba[3] = 0.0
        self.add_owner(scn)
        return cv2.cvtColor(self.rh.render(), cv2.COLOR_RGB2BGR)

    def aim_view(self):
        """Follow camera per phase: look-at point, distance, elevation and view direction (deg, world)."""
        duck = self.d.xpos[self.trunk].copy()
        duck[2] = 0.0
        ball = self.ball()
        ball[2] = 0.0
        own = np.array([self.owner[0], self.owner[1], 0.0])
        hd = math.degrees(bsc._yaw(self.d.xquat[self.trunk]))
        to_owner = math.degrees(math.atan2(own[1] - duck[1], own[0] - duck[0]))
        ph = self.phase
        if ph in ("idle", "call", "look", "command"):      # from behind the duck toward the owner, whole body in view
            return 0.45 * duck + 0.55 * own + np.array([0, 0, 0.25]), 3.0, -10.0, to_owner - 32
        if ph in ("deliver", "end"):
            return duck + 0.25 * (own - duck) / max(1e-6, np.linalg.norm(own - duck)) + np.array([0, 0, 0.12]), 0.95, -14.0, to_owner + 40   # from behind the duck toward the owner: the drop, the owner beyond the table
        if ph in ("search", "approach"):                    # three-quarter front of the duck
            return 0.5 * (duck + ball) + np.array([0, 0, 0.09]), 1.15, -18.0, hd + 180 + 40
        if ph in ("creep", "pick", "check"):               # low three-quarter front of the beak and the ball
            return 0.5 * duck + 0.5 * ball + np.array([0, 0, 0.08]), 0.62, -12.0, hd + 180 + 60
        return duck + np.array([0, 0, 0.12]), 1.0, -14.0, hd - 90   # carrying it back, side on

    def frame(self, t, brain, tilt):
        look, dist, elev, az = self.aim_view()
        if self.view is None:
            self.view = [look, dist, elev, az]
        a = 0.05
        daz = (az - self.view[3] + 180) % 360 - 180
        self.view = [self.view[0] + a * (look - self.view[0]), self.view[1] + a * (dist - self.view[1]),
                     self.view[2] + a * (elev - self.view[2]), self.view[3] + 0.6 * a * daz]
        self.cam.lookat[:] = self.view[0]
        self.cam.distance = self.view[1]
        self.cam.elevation = self.view[2]
        self.cam.azimuth = self.view[3]
        self.rv.update_scene(self.d, camera=self.cam)
        self.add_owner(self.rv.scene)
        img = cv2.cvtColor(self.rv.render(), cv2.COLOR_RGB2BGR)
        # head camera inset (bottom right), with the detector's box while searching / approaching
        hc = self.head_render()
        if self.phase in ("search", "approach") and self.det is not None:
            x, y, w, h = self.det
            cv2.rectangle(hc, (int(x - w / 2 - 6), int(y - h / 2 - 6)), (int(x + w / 2 + 6), int(y + h / 2 + 6)),
                          (0, 255, 0), 3)
        ih = 300
        iw = int(ih * CW / CH)
        small = cv2.resize(hc, (iw, ih), interpolation=cv2.INTER_AREA)
        x0, y0 = VW - iw - 20, VH - ih - 50
        img[y0:y0 + ih, x0:x0 + iw] = small
        cv2.rectangle(img, (x0 - 2, y0 - 2), (x0 + iw + 1, y0 + ih + 1), (255, 255, 255), 2)
        cv2.rectangle(img, (x0 - 2, y0 - 30), (x0 + 130, y0 - 2), (20, 20, 20), -1)
        self.text(img, "head camera", (x0, y0 - 10), 0.55, 1)
        # titles, subtitle, mode, footer (on dark bands so small text stays clean)
        band = img.copy()
        cv2.rectangle(band, (0, 0), (760, 134), (20, 20, 20), -1)
        cv2.rectangle(band, (0, VH - 40), (VW, VH), (20, 20, 20), -1)
        img = cv2.addWeighted(band, 0.55, img, 0.45, 0)
        title = TITLES.get(self.phase, "")
        if title:
            self.text(img, title, (28, 52), 1.0, 2)
        self.text(img, f"t {t:5.1f} s   policy: {brain.mode if brain.mode != 'walk' else (('walk61' if any(abs(v) > 0.02 for v in self.cmd_s) else 'stand61'))}"
                       f"   tilt {tilt:4.1f} deg", (28, 88), 0.6, 1)
        if self.phase in ("pick", "check", "turn_back", "carry", "deliver", "end") and self.held is not None:
            self.text(img, ("ball in the beak (carry assisted: held between the pads at 10 deg after the pick held)" if self.attached else
                            "ball dropped in front of the owner") if self.held else "missed", (28, 120), 0.6, 1,
                      (120, 255, 120) if self.held else (80, 80, 255))
        sub, st = self.sub
        if sub and t - st < 4.5:
            (tw, _), _ = cv2.getTextSize(sub, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
            self.text(img, sub, ((VW - tw) // 2 - 120, VH - 90), 1.0, 2, (80, 230, 255))
        if self.phase == "look" and t - self.t0 < 1.2:
            self.text(img, "Quack!", (VW // 2 - 60, VH // 2 - 120), 1.2, 3, (80, 230, 255))
        self.text(img, "MuJoCo sim, as-built MicroDuck. Real runtime: stand61 / walk61 / seepick61, jaw + guards as on the robot. "
                       "Scripted: voice triggers, path steering on sim truth. On a table so the look-up camera sees the face." + (f" Trial: {self.blend:g} s pick-to-stand blend." if self.blend else ""),
                  (20, VH - 18), 0.45, 1, (220, 220, 220))
        self.ffmpeg.stdin.write(img.tobytes())
        self.frame_n += 1

    @staticmethod
    def text(img, s, org, scale, th, color=(255, 255, 255)):
        if scale >= 0.9:
            cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), th + 3, cv2.LINE_AA)
        cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, th, cv2.LINE_AA)

    def close(self, fell=None):
        if hasattr(self, "ffmpeg"):
            self.ffmpeg.stdin.close()
            self.ffmpeg.wait()
        out = dict(events=self.events, frames=self.frame_n, held=self.held, final_phase=self.phase, video=self.out)
        if self.events_path:
            with open(self.events_path, "w") as f:
                json.dump(out, f, indent=1)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="fullflow.mp4")
    ap.add_argument("--events", default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-s", type=float, default=140.0)
    ap.add_argument("--sp-blend", type=float, default=0.0, help="s; walk_brain sp_blend_s trial (pick goals blend into stand61); 0 = off, as deployed")
    a = ap.parse_args()
    story = Story(os.path.abspath(a.out), a.events, a.max_s)
    story.blend = a.sp_blend
    bsc.STORY = story
    # the seepick rehearsal's corrected harness (seepick-gap-20261029): elliptic cone, impratio 10, the current robot
    # (microduck_rl/cmu/model/current.json: battery backpack, orange saddle),
    # COM calibration; jaw current from CURRENT-STATE.json jaw_grip_current_ma (150 mA); servo rail from servo_rail_v
    sys.argv = ["brain_sim_check.py", "--model", "asbuilt", "--manifest", "current", "--com-x", "-2.25", "--drop", "0.04",
                "--wired-guards", "--walk-at", "1e6", "--walk-s", "0", "--sp-at", "150", "--sp-shape", "ball",
                "--sp-half", "0.006", "0.006", "0.006", "--sp-mass", "1.0", "--sp-friction", "0.6",
                "--sp-jaw-current", "150", "--sp-cone", "elliptic", "--sp-impratio", "10", "--sp-after", "0",
                "--sp-blend", str(a.sp_blend), "--seed", str(a.seed)] + (["--sp-log", os.environ["FF_SPLOG"]] if os.environ.get("FF_SPLOG") else [])
    try:
        bsc.main()
    finally:
        out = story.close()
        print(json.dumps(dict(held=out["held"], final_phase=out["final_phase"], frames=out["frames"])), flush=True)


if __name__ == "__main__":
    main()
