"""Motor babbling analysis: from one trace per joint (that joint moved, the others still) decide what the joint does
to the body, the body schema the card's notes carry (Lipson et al. 2006, "Resilient machines through continuous
self-modeling", Science 314:1118).

A trace is {"joint", "commanded_rad" (amplitude asked for), "babble" (true when the inspector itself commanded the
move; a recorded window's goal came from a policy, whose loaded joints lag their goals, so "did not move" is judged
only on babbling moves), "t": [s], "q": [rad of
that joint], "gb": [[x, y, z] unit gravity in the body frame], "gyro": [[rad/s] * 3], "img_change": [pixel change relative to image contrast] or None,
"source"}. Pure Python so the dry run needs nothing installed.
"""
import math

TILT_DEG = 1.0  # trunk tilt change that counts as "tilts the body" (BNO085 gravity noise is well below 0.2 deg)
IMG_CHANGE = 0.1  # mean absolute pixel change over the first frame's mean absolute deviation: "moves the camera"
RESPONDS = 0.3  # a joint that reaches under 30 % of the commanded amplitude did not respond


def _angle_deg(a, b):
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    c = sum(x * y for x, y in zip(a, b)) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def analyse(trace):
    q0, g0 = trace["q"][0], trace["gb"][0]
    excursion = max(abs(q - q0) for q in trace["q"])
    tilt = max(_angle_deg(g, g0) for g in trace["gb"])
    gyro = max(math.sqrt(sum(w * w for w in v)) for v in trace["gyro"]) if trace.get("gyro") else None
    img = max(trace["img_change"]) if trace.get("img_change") else None
    cmd = trace.get("commanded_rad")
    responds = None if not (cmd and trace.get("babble")) else excursion >= RESPONDS * abs(cmd)
    effects = []
    if responds is False:
        effects.append("did not move")
    else:
        if tilt >= TILT_DEG:
            effects.append("tilts the body")
        if img is not None and img >= IMG_CHANGE:
            effects.append("moves the camera")
        if not effects:
            effects.append("does nothing visible")
    out = dict(joint=trace["joint"], excursion_rad=round(excursion, 4), tilt_deg=round(tilt, 2),
               tilt_deg_per_rad=round(tilt / excursion, 1) if excursion > 1e-3 else None,
               gyro_peak=None if gyro is None else round(gyro, 3), img_change=None if img is None else round(img, 4),
               commanded_rad=cmd, responds=responds, effects=effects, source=trace.get("source", ""))
    out["text"] = describe(out)
    return out


def describe(e):
    parts = [f"moving {e['joint']} by {e['excursion_rad']:.2f} rad " + " and ".join(e["effects"])]
    if "tilts the body" in e["effects"]:
        parts.append(f"(trunk tilt {e['tilt_deg']:.1f} deg, {e['tilt_deg_per_rad']} deg/rad)")
    if "moves the camera" in e["effects"]:
        parts.append(f"(image change {e['img_change']:.3f})")
    if e["img_change"] is None:
        parts.append("[no camera in this trace]")
    if e["responds"] is None and e["commanded_rad"]:
        parts.append(f"[policy goal moved {e['commanded_rad']:.2f} rad]")
    return " ".join(parts) + f"; source {e['source']}"


def analyse_all(traces):
    return [analyse(t) for t in traces]
