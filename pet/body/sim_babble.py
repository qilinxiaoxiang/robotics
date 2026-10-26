"""Motor babbling in the as-built MuJoCo MicroDuck (the brain_sim_check.py / getup_sim.py plant: evaluate_delay.load,
BAM XL330 actuators, 2.5 ms steps, saddle mass manifest, rail voltage from microduck-sim/CURRENT-STATE.json).

The duck stands feet flat at walk_brain.STAND with every servo at the stand-mode P gain; one joint at a time is moved
+A, -A and back at a lower P gain, A growing through AMPS while the trunk stays within GROW_TILT_DEG while the trunk's gravity vector, the IMU gyro and the head camera image are recorded.
A joint run aborts and returns home if the trunk tilts past ABORT_TILT_DEG. Every joint starts from the same settled
stand (the sim state is restored between joints; on the robot the return home plays that part). Needs
~/.venvs/microduck-dyn.
"""
import json
import math
import os
import sys

import mujoco
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAC = os.path.join(REPO, "microduck-sim", "guide", "firmware", "mac")
WHOLE = os.path.join(REPO, "microduck-sim", "hardware-design-20260912", "whole-robot-20260912")
for p in (MAC, os.path.join(MAC, "..", "pi"), os.path.join(WHOLE, "dynamics", "realgap-20261014"),
          os.path.join(WHOLE, "delay-repair-20260912")):
    if p not in sys.path:
        sys.path.append(p)
SADDLE = os.path.join(REPO, "microduck-sim", "guide", "print", "a7z-saddle", "balance", "manifest-saddle.json")
STATE = os.path.join(REPO, "microduck-sim", "CURRENT-STATE.json")

KP_STAND = 400  # stand mode P gain (CURRENT-STATE walking_policy: "stand mode KP 400")
KP_BABBLE = 200  # lower gain on the joint being moved: the walking gain (KP_RL), half the stand gain
AMPS = (0.02, 0.04, 0.08)  # rad, tried in turn; the next only while the last one tilted the trunk under GROW_TILT_DEG
GROW_TILT_DEG = 3.0
ABORT_TILT_DEG = 6.0  # 2026-10-26 sim: one hip pitch, ankle or the neck moved 0.05 rad at KP 200 tips the standing duck over
SEGMENT = [(0.5, 1.0), (0.3, 1.0), (1.0, -1.0), (0.3, -1.0), (0.5, 0.0), (0.5, 0.0)]  # (seconds, target as a fraction of the amplitude), ramps between


def _angle(a, b):
    c = sum(x * y for x, y in zip(a, b)) / math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def load_plant(volt):
    import evaluate_delay as ev
    from static_gap import cfg, feet_flat_rot, setup, sole_points
    from walk_brain import STAND
    c0 = cfg(0.09, model="asbuilt", kp=KP_STAND, voltage=volt)
    c0["mass_manifest"] = os.path.abspath(SADDLE)
    m, d, c, names, bam = ev.load(c0)
    p0 = np.array([STAND[n] for n in names])
    Rt = feet_flat_rot(m, d, names, dict(zip(names, p0)))
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, Rt.ravel())
    ji = setup(m, d, names, dict(zip(names, p0)), q)
    d.qpos[2] -= np.vstack(sole_points(m, d))[:, 2].min() - 0.0005
    mujoco.mj_forward(m, d)
    c.q_target = p0.copy()
    return m, d, c, names, bam, p0, m.jnt_qposadr[ji]


def run(volt=None, joints=None, img_hz=10, size=(80, 60)):
    if volt is None:
        volt = float(json.load(open(STATE))["facts"]["servo_rail_v"]["value"])
    m, d, c, names, bam, p0, qa = load_plant(volt)
    trunk = m.body("trunk_base").id
    gyro_adr = m.sensor("imu_ang_vel").adr[0]
    sub = round(0.02 / m.opt.timestep)
    try:
        renderer = mujoco.Renderer(m, size[1], size[0])
    except Exception as exc:  # no GL context: traces carry no image, the card says so
        renderer, why = None, str(exc)
    vopt = mujoco.MjvOption()
    vopt.geomgroup[2] = vopt.geomgroup[3] = 0  # hide the robot's own meshes: the model camera sits inside the head shell
    kp = np.full(len(names), float(KP_STAND))
    bam.actuator.kp = kp.copy()

    def step(n_ticks, rec=None, k=None, frac0=0.0, frac1=0.0, amp=0.0):
        for i in range(n_ticks):
            if k is not None:
                f = frac0 + (frac1 - frac0) * (i + 1) / n_ticks
                tgt = p0.copy()
                tgt[k] = p0[k] + f * amp
                c.q_target = tgt
            for _ in range(sub):
                c.update()
                mujoco.mj_step(m, d)
            if rec is not None:
                rec(i)

    step(50)  # settle 1 s
    settled = mujoco.MjData(m)
    mujoco.mj_copyData(settled, m, d)
    traces = []
    def trial(k, name, amp):
        tr = dict(joint=name, commanded_rad=amp, babble=True, t=[], q=[], gb=[], gyro=[], img_change=[] if renderer else None,
                  source=f"MuJoCo as-built duck, saddle manifest, {volt} V, KP {KP_STAND} stand / {KP_BABBLE} babble")
        mujoco.mj_copyData(d, m, settled)
        c.q_target = p0.copy()
        kp[:] = KP_STAND
        kp[k] = KP_BABBLE
        bam.actuator.kp = kp.copy()
        t0 = d.time
        img0 = [None]
        aborted = [False]

        def rec(_):
            R = d.xmat[trunk].reshape(3, 3)
            g = (R.T @ np.array([0.0, 0.0, -1.0])).tolist()
            tr["t"].append(round(d.time - t0, 3))
            tr["q"].append(float(d.qpos[qa[k]]))
            tr["gb"].append([round(x, 5) for x in g])
            tr["gyro"].append([round(float(x), 4) for x in d.sensordata[gyro_adr:gyro_adr + 3]])
            if renderer is not None and len(tr["t"]) % max(1, round(50 / img_hz)) == 1:
                renderer.update_scene(d, camera="head_camera", scene_option=vopt)
                img = renderer.render().astype(np.float32) / 255.0
                if img0[0] is None:  # first frame and its contrast (mean absolute deviation)
                    img0[0] = (img, float(np.abs(img - img.mean()).mean()) or 1.0)
                # pixel change relative to the image's own contrast: a low-contrast floor would hide a real move
                tr["img_change"].append(round(float(np.abs(img - img0[0][0]).mean()) / img0[0][1], 4))
            if _angle(g, tr["gb"][0]) > ABORT_TILT_DEG:
                aborted[0] = True

        frac = 0.0
        for secs, f in SEGMENT:
            if aborted[0]:
                break
            step(round(secs * 50), rec, k, frac, f, amp)
            frac = f
        if aborted[0]:
            tr["aborted"] = True
            step(50, None, k, frac, 0.0, amp)
        return tr

    for k, name in enumerate(names):
        if joints and name not in joints:
            continue
        kept = None
        for amp in AMPS:
            tr = trial(k, name, amp)
            if kept is None or not tr.get("aborted"):
                kept = tr
            tilt = max(_angle(g, tr["gb"][0]) for g in tr["gb"])
            if tr.get("aborted") or tilt >= GROW_TILT_DEG:
                break
        kept["amps_tried"] = [a for a in AMPS if a <= amp]
        traces.append(kept)
    kp[:] = KP_STAND
    bam.actuator.kp = kp.copy()
    return traces, dict(volt=volt, renderer=renderer is not None, note=None if renderer else why,
                        joints_in_model=list(names))


if __name__ == "__main__":
    tr, info = run()
    json.dump(dict(info=info, traces=tr), sys.stdout)
