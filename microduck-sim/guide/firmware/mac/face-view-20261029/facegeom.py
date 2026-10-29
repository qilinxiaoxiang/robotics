"""Face-view geometry of the MicroDuck head camera (U20CAM on the face, D-023): numpy only, no MuJoCo.

For a posture (14 joints, model rad, plus the trunk-frame gravity direction gb as the brain reads it) duck_kin.DuckKin
gives the camera's position and axes in the foot frame (x forward, z up, lowest sole on z = 0). From that:
- elevation of the optical axis (deg above the horizontal), the camera height,
- the fisheye's vertical half-angle (u20cam_intrinsics.json: equidistant, f = 359.5 px on the published 640 x 360 frame,
  so rows 0..360 span +-28.7 deg; the pinhole formula duck_kin prints as vfov_deg, 53.2 deg, is the renderer's
  approximation and is not used here),
- for a face centre at horizontal distance D and height H: whether it projects inside the 640 x 360 frame
  (Intrinsics.project, the fisheye model), the inter-pupil distance in px (two points 63 mm apart across the line of
  sight, both projected), the line-of-sight angle below the face (the face model's "seen from below" pitch when the
  person looks straight ahead; a person looking at the duck presents a frontal face whatever the angle), and the image
  roll (angle between the camera's image-up vector and world up, projected on the image plane: the rotation to apply
  to the frame before face detection).

Library: posture_report(q, gb) -> dict. CLI: facegeom.py prints the table for the kinematic postures (no sim).
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
sys.path.insert(0, MAC)
sys.path.insert(0, os.path.join(MAC, "..", "pi"))
import duck_kin  # noqa: E402
from walk_brain import HEAD_RANGE, HEAD_JOINTS, JOINT_RANGE, STAND, NEUTRAL  # noqa: E402

IPD_M = 0.063
MIN_IPD_PX = 10.0          # pet/identity/face.py MIN_IPD_PX
DISTANCES = (0.3, 0.5, 1.0, 2.0)
PEOPLE = {"adult_standing": 1.60, "seated": 1.10, "child": 1.00, "crouching": 0.80}
KIN = duck_kin.DuckKin()   # U20CAM intrinsics + mount
K = KIN.K
HALF_V_DEG = math.degrees((K.height / 2) / K.fy)   # equidistant: r = f theta
HALF_H_DEG = math.degrees((K.width / 2) / K.fx)


def gb_from_pitch(pitch_deg, roll_deg=0.0):
    """Trunk-frame gravity for a trunk pitched nose-down by pitch_deg (positive = leaning forward, as the brain's gb[0]
    and stand_sim's end_pitch read it; negative = leaning back) and rolled roll_deg."""
    p, r = math.radians(pitch_deg), math.radians(roll_deg)
    Ry = np.array([[math.cos(p), 0, math.sin(p)], [0, 1, 0], [-math.sin(p), 0, math.cos(p)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(r), -math.sin(r)], [0, math.sin(r), math.cos(r)]])
    return tuple((Ry @ Rx).T @ np.array([0.0, 0.0, -1.0]))


def trunk_pitch_from_gb(gb):
    """Nose-down trunk pitch in deg from the trunk-frame gravity (positive = leaning forward; the inverse of gb_from_pitch)."""
    g = np.asarray(gb, float) / np.linalg.norm(gb)
    return math.degrees(math.asin(float(np.clip(g[0], -1, 1))))


def camera(q, gb=duck_kin.UPRIGHT):
    """(pos, R) in the foot frame; R columns = optical axis, image left, image up."""
    return KIN.camera_pose(q, gb)


def elevation_deg(R):
    return math.degrees(math.asin(float(np.clip(R[2, 0], -1, 1))))


def image_roll_deg(R):
    """Angle from the image-up vector to world up, both projected onto the image plane (perpendicular to the optical
    axis); positive = the frame must be turned clockwise by this to make faces upright. 0 for a level camera."""
    a = R[:, 0]
    up = np.array([0.0, 0.0, 1.0])
    up_p = up - a * float(up @ a)
    if np.linalg.norm(up_p) < 1e-6:
        return 0.0  # looking straight up or down: roll undefined
    up_p /= np.linalg.norm(up_p)
    iu, il = R[:, 2], R[:, 1]
    return math.degrees(math.atan2(float(up_p @ il), float(up_p @ iu)))


def face_view(pos, R, D, H, yaw_deg=0.0):
    """Project a face centre at horizontal distance D (m, along the camera's horizontal heading) and height H."""
    heading = R[:, 0].copy(); heading[2] = 0.0
    if np.linalg.norm(heading) < 1e-6:
        heading = np.array([1.0, 0.0, 0.0])
    heading /= np.linalg.norm(heading)
    c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    heading = np.array([c * heading[0] - s * heading[1], s * heading[0] + c * heading[1], 0.0])
    pw = pos + D * heading + np.array([0.0, 0.0, H - pos[2]])
    rel = pw - pos
    pc = R.T @ rel
    uv = K.project(pc)
    inside = uv is not None and 0 <= uv[0] < K.width and 0 <= uv[1] < K.height
    # inter-pupil distance: two points 63 mm apart, horizontal and across the line of sight
    los = rel / np.linalg.norm(rel)
    across = np.cross(np.array([0.0, 0.0, 1.0]), los)
    across /= np.linalg.norm(across)
    e1 = K.project(R.T @ (rel + across * IPD_M / 2))
    e2 = K.project(R.T @ (rel - across * IPD_M / 2))
    ipd = math.hypot(e1[0] - e2[0], e1[1] - e2[1]) if (e1 is not None and e2 is not None) else 0.0
    below = math.degrees(math.atan2(H - pos[2], D))  # line of sight rises by this to the face (face seen from below)
    return dict(inside=bool(inside), u=None if uv is None else round(uv[0], 1), v=None if uv is None else round(uv[1], 1),
                ipd_px=round(ipd, 1), ipd_ok=ipd >= MIN_IPD_PX, los_up_deg=round(below, 1), range_m=round(float(np.linalg.norm(rel)), 3))


def highest_face(pos, elev, D):
    """Highest face-centre height whose line of sight is inside the fisheye's vertical half-angle at distance D."""
    top = elev + HALF_V_DEG
    if top >= 89.9:
        return None  # the top edge looks above vertical: no limit
    return round(pos[2] + D * math.tan(math.radians(top)), 2)


def posture_report(q, gb=duck_kin.UPRIGHT, name=""):
    pos, R = camera(q, gb)
    elev = elevation_deg(R)
    rep = dict(name=name, cam_height_m=round(float(pos[2]), 3), cam_x_m=round(float(pos[0]), 3),
               elev_deg=round(elev, 1), image_roll_deg=round(image_roll_deg(R), 1),
               top_edge_deg=round(elev + HALF_V_DEG, 1), bottom_edge_deg=round(elev - HALF_V_DEG, 1),
               trunk_pitch_deg=round(trunk_pitch_from_gb(gb), 1),
               head_q={n: round(float(q[n]), 3) for n in HEAD_JOINTS},
               highest_face_m={str(D): highest_face(pos, elev, D) for D in DISTANCES}, faces={})
    for D in DISTANCES:
        for person, H in PEOPLE.items():
            rep["faces"][f"{person}@{D}"] = face_view(pos, R, D, H)
    return rep


def summary_line(rep):
    seen = [k for k, f in rep["faces"].items() if f["inside"] and f["ipd_ok"]]
    return (f"{rep['name']:<34} cam z {rep['cam_height_m']:.3f} m  elev {rep['elev_deg']:+6.1f}  top edge "
            f"{rep['top_edge_deg']:+6.1f}  roll {rep['image_roll_deg']:+6.1f}  trunk {rep['trunk_pitch_deg']:+5.1f} | "
            f"highest face at 0.5/1/2 m: {rep['highest_face_m']['0.5']}/{rep['highest_face_m']['1.0']}/{rep['highest_face_m']['2.0']} | "
            f"seen+IPD: {', '.join(seen) or 'none'}")


def kinematic_postures():
    """Postures whose joints are known without a simulation (trunk upright; the sim rest tilt is added in the README)."""
    out = {}
    out["stand_default (STAND, neck 0.25)"] = (dict(STAND), duck_kin.UPRIGHT)
    out["stand61 default head (NEUTRAL 0.349/0.349)"] = (dict(NEUTRAL), duck_kin.UPRIGHT)
    # stand61/walk61 head_pose command at its caps: deltas from the policy default (NEUTRAL head), clamped to the MJCF range
    cap = dict(NEUTRAL)
    cap["neck_pitch"] = min(JOINT_RANGE["neck_pitch"][1], NEUTRAL["neck_pitch"] + HEAD_RANGE[0])
    cap["head_pitch"] = max(JOINT_RANGE["head_pitch"][0], NEUTRAL["head_pitch"] - HEAD_RANGE[1])
    out["policy head cap: neck +1.10 (clamp 1.047), head_pitch -1.10"] = (cap, duck_kin.UPRIGHT)
    out["policy head cap: head_pitch -1.10 only"] = (dict(NEUTRAL, head_pitch=NEUTRAL["head_pitch"] - HEAD_RANGE[1]), duck_kin.UPRIGHT)
    out["policy head: head_pitch -0.50 (dance-size look-up)"] = (dict(NEUTRAL, head_pitch=NEUTRAL["head_pitch"] - 0.5), duck_kin.UPRIGHT)
    # open-loop stand at the MJCF head limits (balance checked in sim separately)
    lim = dict(STAND, neck_pitch=JOINT_RANGE["neck_pitch"][1], head_pitch=JOINT_RANGE["head_pitch"][0])
    out["open-loop: neck 1.047, head_pitch -1.571 (MJCF limits)"] = (lim, duck_kin.UPRIGHT)
    out["open-loop: head_pitch -1.571, neck 0.25"] = (dict(STAND, head_pitch=JOINT_RANGE["head_pitch"][0]), duck_kin.UPRIGHT)
    out["open-loop: head_pitch -0.90, neck 0.25"] = (dict(STAND, head_pitch=-0.90), duck_kin.UPRIGHT)
    return out


if __name__ == "__main__":
    print(f"fisheye half angles: vertical {HALF_V_DEG:.1f} deg, horizontal {HALF_H_DEG:.1f} deg; f {K.fx:.1f} px on {K.width}x{K.height}")
    print(f"IPD {IPD_M*1000:.0f} mm reaches {MIN_IPD_PX:.0f} px at range {K.fx * IPD_M / MIN_IPD_PX:.2f} m (on axis)")
    reps = {}
    for name, (q, gb) in kinematic_postures().items():
        r = posture_report(q, gb, name)
        reps[name] = r
        print(summary_line(r))
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w") as f:
            json.dump(reps, f, indent=1)
