"""Funnel concept geometry (dock frame D, mm) as boxes for the sim, and the pass check of one sit run.

Base = the released BatteryDock-A1 as boxes (build/build.json numbers): plate, contact block (top 8.0), stop wall with
the screw-head relief, tower walls. Leaves are not collision geometry (0.30 bronze springs); they are checked from the
pad pose. Rails = the concept: two side rails beside the backpack's lower tier, each a vertical guide face up to z_v and
a 45 deg lead-in to z_top, x from x0 to x1; optional rear ramp on the stop wall.
"""
import math
import numpy as np

# backpack lower tier in D (trunk frame, rev B): x -75.55..-45, y -25.3..21.8 (build_dock.py D1 note, STL bbox)
BP_Y = (-25.3, 21.8)
LEAF_Y, LEAF_W = 9.0, 7.0                       # Keystone 5209 leaves at y +-9, 7.0 wide (P-5209)
LEAF_FREE_Z, LEAF_TIP_FREE, LEAF_TIP_10_9 = 13.9, -70.313, -72.382   # build.json leaf checks


def Rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def Ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def box(name, x, y, z, R=None):
    """axis ranges (lo, hi) in D, optional rotation about the centre"""
    c = [(x[0] + x[1]) / 2, (y[0] + y[1]) / 2, (z[0] + z[1]) / 2]
    h = [(x[1] - x[0]) / 2, (y[1] - y[0]) / 2, (z[1] - z[0]) / 2]
    return dict(name=name, pos=c, size=h, R=np.eye(3) if R is None else R)


def base_boxes():
    return [
        box("plate", (-100, -55), (-20, 20), (0, 2)),
        box("block", (-76.5, -58), (-16.5, 16.5), (2, 8.0)),
        box("stop_lo", (-79.7, -76.5), (-17, 17), (0, 14.6)),
        box("stop_hi", (-79.7, -78.0), (-17, 17), (14.6, 22)),
        box("tower_l", (-100, -79.7), (15, 17), (0, 22)),
        box("tower_r", (-100, -79.7), (-17, -15), (0, 22)),
        box("tower_back", (-100, -97.5), (-15, 15), (0, 22)),
    ]


def slope_box(name, p0, p1, x, inward, t=4.0):
    """a box whose inward face is the plane through the two (y, z) points p0 (low, inner) and p1 (high, outer), along
    x; inward = +1 if the face looks toward +y (right-hand rail), -1 toward -y (left-hand rail)"""
    (y0, z0), (y1, z1) = p0, p1
    L = math.hypot(y1 - y0, z1 - z0)
    a = math.atan2(z1 - z0, abs(y1 - y0))         # slope angle from horizontal
    # face normal: up and toward the robot; local z of the box = normal
    R = Rx(-inward * a)
    n = R @ np.array([0, 0, 1.0])
    along = R @ np.array([0, 1.0, 0])             # up the slope
    if along[2] < 0:
        along = -along
    # the box starts exactly at p0 (nothing pokes inward of the vertical face) and runs t past p1 (outer top)
    mid = np.array([0, (y0 + y1) / 2, (z0 + z1) / 2]) - n * t + along * (t / 2)
    return dict(name=name, pos=[(x[0] + x[1]) / 2, mid[1], mid[2]], size=[(x[1] - x[0]) / 2, (L + t) / 2, t], R=R)


def rail_boxes(c=1.5, z_v=14.0, z_top=34.0, slope_deg=45.0, x0=-78.0, x1=-50.0, w=3.0, **_):
    """side rails at the lower tier's faces + c; vertical face 0..z_v, then the lead-in at slope_deg up to z_top"""
    out = []
    h = z_top - z_v
    run = h / math.tan(math.radians(slope_deg))
    yl = BP_Y[1] + c                               # left rail inner face (robot's left, +y)
    yr = BP_Y[0] - c
    out.append(box("rail_l_v", (x0, x1), (yl, yl + run + w), (0, z_v)))
    out.append(box("rail_r_v", (x0, x1), (yr - run - w, yr), (0, z_v)))
    out.append(slope_box("rail_l_s", (yl, z_v), (yl + run, z_top), (x0, x1), inward=-1))
    out.append(slope_box("rail_r_s", (yr, z_v), (yr - run, z_top), (x0, x1), inward=+1))
    return out


def ramp_box(name, x_front, z_front, x_back, y, t=4.0):
    """45 deg face rising backward from (x_front, z_front) to x_back, looking forward-up, over y = (lo, hi)"""
    R = Ry(math.radians(45))
    n = R @ np.array([0, 0, 1.0])                 # (+0.707, 0, +0.707)
    L = (x_front - x_back) * math.sqrt(2)
    along = np.array([-1, 0, 1.0]) / math.sqrt(2)
    mid = np.array([x_front, 0, z_front]) + along * (L / 2) - n * t
    return dict(name=name, pos=[mid[0], (y[0] + y[1]) / 2, mid[2]], size=[L / 2, (y[1] - y[0]) / 2, t], R=R)


def dock_geometry(p):
    """p: rails (bool), rear (bool: stop wall top and tower front become a 45 deg ramp from the stop face top edge,
    replacing the screw-head relief ledge), bias (mm: the whole dock forward of the A1 datum), rail params."""
    bias = p.get("bias", 0.0)
    if p.get("rear"):
        zt = 14.6
        boxes = [
            box("plate", (-100, -55), (-20, 20), (0, 2)),
            box("block", (-76.5, -58), (-16.5, 16.5), (2, 8.0)),
            box("stop_lo", (-79.7, -76.5), (-17, 17), (0, zt)),
            ramp_box("ramp_stop", -76.5, zt, -79.7, (-17, 17)),
            ramp_box("ramp_l", -76.5, zt, -92.0, (15, 17)),
            ramp_box("ramp_r", -76.5, zt, -92.0, (-17, -15)),
            box("tower_l", (-100, -84.0), (15, 17), (0, 22)),
            box("tower_r", (-100, -84.0), (-17, -15), (0, 22)),
            box("tower_back", (-100, -97.5), (-15, 15), (0, 22)),
        ]
    else:
        boxes = base_boxes()
    if p.get("rails"):
        boxes += rail_boxes(**p)
    for b_ in boxes:
        b_["pos"] = [b_["pos"][0] + bias, b_["pos"][1], b_["pos"][2]]
    return boxes


def concept_geometry(params):
    return dock_geometry(dict(params, rails=True)) if "rails" not in params else dock_geometry(params)


# ------------------------------------------------------------------ evaluation of one run
def box_sdf(P, b):
    R = np.asarray(b["R"]); c = np.asarray(b["pos"], float); h = np.asarray(b["size"], float)
    q = np.abs((P - c) @ R) - h
    out = np.linalg.norm(np.maximum(q, 0), axis=1)
    return out + np.minimum(q.max(1), 0)


def pad_check(pads_D, leaf_dx=0.0):
    """pads_D: dict plus/minus -> (N,3) pad vertices in D. Pass = each pad's face over its own leaf, not the other."""
    res = {}
    ok = True
    for k, sgn in (("plus", 1), ("minus", -1)):
        v = pads_D[k]
        zf = v[:, 2].min()
        face = v[v[:, 2] < zf + 0.3]
        x0, x1 = face[:, 0].min(), face[:, 0].max()
        y0, y1 = face[:, 1].min(), face[:, 1].max()
        tip = leaf_dx + LEAF_TIP_10_9 + (zf - 10.9) * (LEAF_TIP_FREE - LEAF_TIP_10_9) / (LEAF_FREE_Z - 10.9)
        own = (sgn * LEAF_Y - LEAF_W / 2, sgn * LEAF_Y + LEAF_W / 2)
        oth = (-sgn * LEAF_Y - LEAF_W / 2, -sgn * LEAF_Y + LEAF_W / 2)
        ov_own = min(y1, own[1]) - max(y0, own[0])
        ov_oth = min(y1, oth[1]) - max(y0, oth[0])
        x_margin = min(tip - x0, x1 - tip)
        comp = LEAF_FREE_Z - zf
        p = (ov_own >= 1.0) and (ov_oth <= 0) and (x_margin >= 0.5) and (comp >= 1.0)
        ok &= p
        res[k] = dict(face_z=round(zf, 2), x=[round(x0, 2), round(x1, 2)], y=[round(y0, 2), round(y1, 2)],
                      leaf_tip_x=round(tip, 2), x_margin=round(x_margin, 2), y_overlap_own=round(ov_own, 2),
                      y_overlap_other=round(ov_oth, 2), compression=round(comp, 2), ok=bool(p))
    return ok, res
