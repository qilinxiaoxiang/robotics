"""Sim check of the 10/23 fix: during a sit rise the sitstand61 neck output is replaced by the robot's logged runaway
(rise 3 of app1023-204119 from +0.57 s), with walk_wired's guards. argv: robot rows jsonl, tick log out, [noheadhome]."""
import json, sys
MAC = "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac"
sys.path.insert(0, MAC)
import brain_sim_check as bsc
import walk_brain as wb
NK = wb.OBSERVATION_DOF_ORDER.index("neck_pitch")
rows = [json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")]
rises, cur = [], None
for i, r in enumerate(rows):
    on = r["mode"] == "sit" and r["cmd"].get("mode") != "sit"
    if on and cur is None: cur = i
    if not on and cur is not None: rises.append(cur); cur = None
a = rises[-1]
seq = [r["action"][NK] for r in rows[a:] if r["mode"] == "sit" and r.get("action") and r["t"] - rows[a]["t"] >= 0.57]
print("injected neck sequence", [round(x, 2) for x in seq])

class Inject:
    def __init__(self, real): self.real, self.was1, self.rise = real, False, 0
    def __getattr__(self, n): return getattr(self.real, n)
    def run(self, outputs, feeds):
        out = self.real.run(outputs, feeds)
        flag = float(list(feeds.values())[0][0][48])
        if flag > 0.5: self.was1 = True
        elif self.was1:
            self.rise += 1
            k = self.rise - 29  # +0.57 s at 50 Hz
            if k >= 0: out[0][0][NK] = seq[min(k, len(seq) - 1)]
        return out

class B(bsc.Brain):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.sessions["sitstand"] = Inject(self.sessions["sitstand"])
    if "noheadhome" in sys.argv:
        def home_head(self, now): pass

import os
wb.HEAD_HOME_TO = os.environ.get("HH_TO", "stand")
wb.HEAD_HOME_KP = int(os.environ["HH_KP"]) if os.environ.get("HH_KP") else None
if os.environ.get("NECK_DOWN"):
    lo = wb.NEUTRAL["neck_pitch"] - float(os.environ["NECK_DOWN"])
    wb.JOINT_RANGE["neck_pitch"] = (lo, wb.JOINT_RANGE["neck_pitch"][1])
RECOVER = float(os.environ.get("RECOVER_AT", "1e9"))
_tick = B.tick
def tick(self, want, now, *a):
    if now >= RECOVER:
        want = {"mode": "stand"}
    return _tick(self, want, now, *a)
B.tick = tick
bsc.Brain = B
sys.argv = ["brain_sim_check.py", "--model", "asbuilt", "--drop", "0.04", "--walk-s", "0", "--sit-at", "3", "--unsit-at", "7",
            "--seed", os.environ.get("SEED", "0"), "--wired-guards", "--tick-log", sys.argv[2]]
bsc.main()
