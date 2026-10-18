#!/usr/bin/env python3
"""The four V1.9 bundle clips: geometry (release solids in the robot frame at q = 0) and their parameters.

Every clip is one printed part: a 2.0 mm tab that sits under the head of an existing screw (the screw becomes 2 mm
longer, so its tip stays where it is today) and a U channel that holds the eight-wire group. The channel interior is
CH_W x CH_H (wire group of 8: 2 x 22 AWG at 1.7 mm and 6 x 26 AWG at 1.3 mm, 12.5 mm2 of copper and insulation),
the top closes with 45 degree lips to a CH_MOUTH mouth, so the wires are pressed in one at a time and the lips keep
them in. The lip undersides are 45 degree slopes, so each clip prints mounting face down with no support and with
its screw hole vertical.

Torso clip (S12-horn-025) and bracket clip (S11-horn-040): the channel is centred on the joint axis (neck pitch and
head pitch respectively), between the four horn screws, with its floor on the flat ear / plate face. The tab is
under the rear horn screw (x = 20) and joins the channel floor. The torso channel runs along x (the group comes
forward along the torso side, passes over the neck-pitch axis and turns up); the bracket channel runs along z (the
group runs straight up the neck over the head-pitch axis). With both clip channels on the joint axes, the span
between them keeps its length at every neck and head pitch.
"""
from __future__ import annotations

import manifold3d as m3
import numpy as np

import ext_lib as E

TAB_T = 2.0
HOLE = {2.0: 2.4, 2.5: 2.9}          # clearance holes (M2, M2.5)
CH_W, CH_H, CH_MOUTH = 4.8, 4.8, 2.4  # interior width (along s), interior height (along n, floor to mouth), mouth
WALL, FLOOR, LIP = 1.2, 1.2, 1.0      # wall, floor, lip thickness at the mouth edge
CH_L = 5.5                            # channel length along the wires
TORSO_X0, TORSO_L = 22.6, 5.0         # torso channel: x start and length (clear of the r 2.3 driver keep-out at x 22.3)
TORSO_ZC = 36.0                       # torso channel centre z: the group's approach clears the shell rib under it
CLEAR = 0.3                           # clearance to screw heads and neighbouring parts
# Torso and bracket channels: the open jaw sweeps past them when the head is yawed and rolled (jaw_cap_v19.py), and it
# meets the outer corners first. Rounding the two mouth-side corners (r 2.4) and chamfering the mouth-side edges at the
# channel ends (1.5 mm) removes only material outboard of the wire space and raises the bracket clip's first jaw
# contact at head roll 5..20 deg by 0.6 to 1.8 deg (clip_candidates.py c3; checks/clip-candidates-v19.json).
HORN_CH = {'r_out': 2.4, 'end_chamfer': 1.5}


def frame_T(origin, s, w, n):
    """Local (s, w, n) -> world 4x4."""
    T = np.eye(4)
    T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = s, w, n, origin
    return T


def channel_local(ch_w=CH_W, ch_h=CH_H, mouth=CH_MOUTH, wall=WALL, floor=FLOOR, lip=LIP, length=CH_L, r_out=0.0,
                  end_chamfer=0.0):
    """U channel in local coords: s across (width), w along the wires (centred), n from the floor's outer face (n = 0)
    towards the mouth. Interior ch_w x ch_h; the mouth (width `mouth`) is closed down by two lips whose undersides are
    45 degree slopes. r_out rounds the two outer corners on the mouth side (radius r_out, the floor side stays square);
    end_chamfer cuts a 45 degree chamfer of that size on the outer (mouth-side) edges at both channel ends. Both remove
    only material outboard of the wire space."""
    wo = ch_w + 2 * wall
    taper = (ch_w - mouth) / 2
    ho = floor + ch_h + lip
    outer = m3.CrossSection.square([wo, ho]).translate([-wo / 2, 0])
    if r_out > 0:
        rr = m3.CrossSection.square([wo - 2 * r_out, ho - r_out]).translate([-wo / 2 + r_out, 0])
        outer = outer ^ rr.offset(r_out, m3.JoinType.Round, 2.0, 96)
    rect_top = floor + ch_h - taper
    inner = m3.CrossSection([[(-ch_w / 2, floor), (ch_w / 2, floor), (ch_w / 2, rect_top), (mouth / 2, floor + ch_h),
                              (mouth / 2, ho + 1), (-mouth / 2, ho + 1), (-mouth / 2, floor + ch_h),
                              (-ch_w / 2, rect_top)]])
    prof = outer - inner                       # in (s, n)
    M = prof.extrude(length).translate([0, 0, -length / 2])   # extruded along local z -> becomes w
    if end_chamfer > 0:
        c = end_chamfer
        env = m3.Manifold.batch_hull([m3.Manifold.cube([wo, ho - c, length]).translate([-wo / 2, 0, -length / 2]),
                                      m3.Manifold.cube([wo, ho, length - 2 * c]).translate([-wo / 2, 0, -length / 2 + c])])
        M = M ^ env
    R = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0]], float)   # (s, n, w) -> (s, w, n)
    space = m3.CrossSection([[(-ch_w / 2, floor), (ch_w / 2, floor), (ch_w / 2, rect_top), (mouth / 2, floor + ch_h),
                              (-mouth / 2, floor + ch_h), (-ch_w / 2, rect_top)]])
    return M.transform(R), {'outerWidth': wo, 'height': ho, 'interior': [ch_w, ch_h], 'mouth': mouth, 'wall': wall,
                            'floor': floor, 'lip': lip, 'wireSpaceMm2': float(space.area()), 'length': length,
                            'outerCornerRadius': r_out, 'endChamfer': end_chamfer}


def horn_clip(screw_id, axis_point, channel_dir, tab_r=3.2, raised=False, length=None, channel_kw=None):
    """Tab under `screw_id` + channel centred at `axis_point` (on the seat plane), channel along `channel_dir`.
    raised: the channel stands on a 2.0 mm plate (the tab extended under it), its floor 0.1 mm sunk into the plate,
    so the wire group lies outboard of every screw head, including this screw's head lifted by the tab."""
    F = E.fasteners()
    r = F[screw_id]
    c = np.array(r['center'], float)
    ax = np.array(r['axis'], float)
    ax /= np.linalg.norm(ax)
    n = -ax
    w = np.asarray(channel_dir, float)
    w = w - (w @ n) * n
    w /= np.linalg.norm(w)
    s = np.cross(w, n)
    p = np.asarray(axis_point, float)
    p = p - ((p - c) @ n) * n                 # project the axis point onto the seat plane
    L = CH_L if length is None else length
    base = (TAB_T - 0.1) if raised else 0.0
    T = frame_T(p + base * n, s, w, n)
    ch, info = channel_local(length=L, **(channel_kw or {}))
    channel = ch.transform(T[:3, :])
    T0 = frame_T(p, s, w, n)
    # tab: disc around the screw + bridge to the channel (hull of the disc and the channel footprint), n 0..TAB_T
    disc = E.cyl(c, n, TAB_T, tab_r, 96)
    wo = CH_W + 2 * WALL
    # footprint for the bridge hull, inset 0.1 mm so the hull never shares a face or edge with the channel; raised:
    # full tab thickness (the plate the channel stands on), else just under the channel floor
    fh = TAB_T if raised else info['floor'] - 0.05
    floor = m3.Manifold.cube([wo - 0.2, L - 0.2, fh]).translate([-wo / 2 + 0.1, -L / 2 + 0.1, 0]).transform(T0[:3, :])
    bridge = m3.Manifold.batch_hull([disc, floor])
    hole = E.cyl(c - 1.0 * n, n, TAB_T + 10.0, HOLE[r['diameterMm']] / 2, 48)
    clip = (channel + disc + bridge) - hole
    centre = p + (base + info['floor'] + info['interior'][1] / 2) * n
    rec = {'screw': screw_id, 'seat': c, 'n': n, 'channelCentre': p, 'w': w, 's': s, 'tabRadiusMm': tab_r, 'tabMm': TAB_T,
           'holeMm': HOLE[r['diameterMm']], 'raised': raised, 'channelBaseAboveSeatMm': base,
           'channelInteriorCentre': centre, 'channelEnds': [centre - L / 2 * w, centre + L / 2 * w], 'channel': info}
    return clip, rec


def keepouts(screw_ids, extra_head=CLEAR, n_lift=None):
    """Screw-head keep-out cylinders (head diameter + 2 x CLEAR, from 0.02 mm off the seat to head height + CLEAR)."""
    F = E.fasteners()
    out = []
    for sid in screw_ids:
        r = F[sid]
        c = np.array(r['center'], float)
        ax = np.array(r['axis'], float)
        ax /= np.linalg.norm(ax)
        out.append(E.cyl(c - 0.02 * ax, -ax, r['headHeightMm'] + extra_head, r['headDiameterMm'] / 2 + extra_head, 64))
    return m3.Manifold.batch_boolean(out, m3.OpType.Add)


# ---- cap clip (E-pi-04) -------------------------------------------------------------------------------------------
# Frame at the screw: n = outward screw normal (forward, off the Pi's component face), y = world y, t = n x y (up along
# the board). The Pi top edge is at t = 3.5 (the hole is 3.5 mm from the edges); the Pi's mini-HDMI socket (not in the
# guide meshes; Raspberry Pi Zero W drawing: centre 12.4 mm from the board end, 11.2 mm wide, about 3.5 mm tall,
# reaching 0.3 mm past the edge) occupies y 14.7..25.5, t -3.6..3.8, n 0..3.5. The release cap's side wall curves
# over this corner (inner face at about t 8 at y 29, t 11 at y 24, t 12.5 at y 19).
# The channel stands off the component face along n (its axis along n, so it prints upright), above the HDMI socket
# (0.3 mm clear) and under the cap wall, at y 14.2..22.0, t 4.1..10.3 (interior 3.8 across t, 5.6 deep along y). Its mouth faces -y (open towards the board
# middle, where the wires are pressed in before the Pi goes into the cap); its floor is the +y wall. A side wall
# extension (t 4.1..5.3, y 21.5..28.6) and a bar (y 25.8..28.6, t 0..5.3, tab thickness) tie it to the tab.
CAP_SCREW = 'E-pi-04'
CAP_CH = dict(ch_w=3.8, ch_h=5.6, mouth=2.4, wall=1.2, floor=1.2, lip=1.0, length=6.0)
CAP_Y_FLOOR = 22.0          # world y of the floor's outer face
CAP_T_MID = 7.2             # channel centre along t (t 4.1..10.3)
HDMI_BOX = dict(y=(14.7, 25.5), t=(-3.6, 3.8), n=(0.0, 3.5))
CAP_TAB_R = 3.0            # tab radius (3.2 reaches within 0.3 mm of the cap's rail corner)


def cap_frame():
    r = E.fasteners()[CAP_SCREW]
    c = np.array(r['center'], float)
    n = -np.array(r['axis'], float)
    n /= np.linalg.norm(n)
    y = np.array([0.0, 1.0, 0.0])
    t = np.cross(n, y)
    return c, n, y, t


def cap_point(n_, y_, t_):
    c, n, y, t = cap_frame()
    return c + n_ * n + (y_ - c[1]) * y + t_ * t


def box_in_frame(origin, axes, lo, hi):
    """Axis-aligned box [lo, hi] in a local frame (columns of `axes`) placed at `origin`."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    B = m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())
    T = np.eye(4)
    T[:3, :3] = np.column_stack(axes)
    T[:3, 3] = origin
    return B.transform(T[:3, :])


def cap_clip():
    c, n, y, t = cap_frame()
    r = E.fasteners()[CAP_SCREW]
    ch, info = channel_local(**CAP_CH)
    L = CAP_CH['length']
    # channel local (s, w, n_ch) = (-t, n, -y): right-handed since (-t) x n = -y
    origin = cap_point(L / 2, CAP_Y_FLOOR, CAP_T_MID)
    channel = ch.transform(frame_T(origin, -t, n, -y)[:3, :])
    wo = info['outerWidth']
    t_lo = CAP_T_MID - wo / 2                 # low-t side wall: t_lo .. t_lo + wall
    # (n, y, t) local box helper at the seat origin, with world y measured from c[1]
    ax = (n, y, t)
    disc = E.cyl(c, n, TAB_T, CAP_TAB_R, 96)
    # the extension is 0.05 mm inside the channel's low-t wall faces and ends 0.05 mm short of the channel's front,
    # and the bar stops 0.1 mm short of the extension's faces, so no two features share a face or an edge
    bar = box_in_frame(c, ax, [0, 25.8 - c[1], 0.0], [TAB_T, 28.5 - c[1], t_lo + CAP_CH['wall'] - 0.1])
    ext = box_in_frame(c, ax, [0, CAP_Y_FLOOR - c[1] - 0.5, t_lo + 0.05], [L - 0.05, 28.6 - c[1], t_lo + CAP_CH['wall'] - 0.05])
    hole = E.cyl(c - 1.0 * n, n, TAB_T + 10.0, HOLE[r['diameterMm']] / 2, 48)
    clip = (channel + disc + bar + ext) - hole
    centre = cap_point(L / 2, CAP_Y_FLOOR - CAP_CH['floor'] - CAP_CH['ch_h'] / 2, CAP_T_MID)
    rec = {'screw': CAP_SCREW, 'seat': c, 'n': n, 'frame': {'n': n, 'y': y, 't': t},
           'channelAxis': n, 'channelMouthDirection': -y, 'channelLengthAlongN': [0.0, L],
           'channelInteriorCentreAtMidLength': centre,
           'channelEnds': [cap_point(0.0, CAP_Y_FLOOR - CAP_CH['floor'] - CAP_CH['ch_h'] / 2, CAP_T_MID),
                           cap_point(L, CAP_Y_FLOOR - CAP_CH['floor'] - CAP_CH['ch_h'] / 2, CAP_T_MID)],
           'hdmiBoxAssumed': HDMI_BOX, 'tabRadiusMm': CAP_TAB_R, 'tabMm': TAB_T, 'holeMm': HOLE[r['diameterMm']], 'channel': info}
    return clip, rec


def hdmi_envelope():
    """Mini-HDMI socket envelope on the Pi (not in the guide meshes), for clearance checks."""
    c, n, y, t = cap_frame()
    b = HDMI_BOX
    return box_in_frame(c, (n, y, t), [b['n'][0] + 0.01, b['y'][0] - c[1], b['t'][0]], [b['n'][1], b['y'][1] - c[1], b['t'][1]])


# ---- head clip (H-jaw_support-03) ---------------------------------------------------------------------------------
# The screw stands on the jaw support base (seat z 113.215, axis -z). Around it: the jaw support's cross wall at
# x <= 42.4 (and its arc behind the screw, >= 2.9 mm from the axis), the descending cap's -y Pi rail at x >= 49.3 for
# y <= -27.5 (z >= 116.7) and its side wall at y <= -39.7; the space x 42.7..53, y -26..-14 is free from the jaw
# support base up (sections in the release check).
# Elbow clip: a tab under the raised screw head, a 2 mm plate that runs forward-left to a vertical channel at
# x 45.6..52.6, y -25.3..-18.1, z 115.215..124.415. The group comes down into the top of the channel, turns on the
# plate and leaves through a window in the +y wall (z 115.215..121.215) towards the Pi; the mouth is a 2.4 mm slot
# down the +x side (the wires are pressed in from the front before the cap goes on). The plate's left edge follows
# the cross wall 0.3 mm away, which stops the clip turning about its single screw.
HEAD_SCREW = 'H-jaw_support-03'
HEAD_CH = dict(ch_w=4.8, ch_h=4.8, mouth=2.4, wall=1.2, floor=1.2, lip=1.0)
HEAD_CENTRE_Y = -21.7        # channel centre (across = world y)
HEAD_FLOOR_X = 45.6          # floor outer face (world x)
HEAD_H = 9.2                 # channel height above the plate
HEAD_WINDOW_H = 6.0          # window height above the plate in the +y wall
HEAD_TURN_Z = 2.7            # group centre height above the plate where it turns out of the window


def head_clip():
    r = E.fasteners()[HEAD_SCREW]
    c = np.array(r['center'], float)
    n = -np.array(r['axis'], float)
    n /= np.linalg.norm(n)                              # +z
    z0 = c[2] + TAB_T                                   # plate top
    ch, info = channel_local(length=HEAD_H + TAB_T, **HEAD_CH)      # walls stand on the bed (plate bottom)
    # local (s, w, n_ch) = (y, z, x): y x z = x, right-handed
    origin = np.array([HEAD_FLOOR_X, HEAD_CENTRE_Y, c[2] + (HEAD_H + TAB_T) / 2])
    channel = ch.transform(frame_T(origin, np.array([0, 1.0, 0]), np.array([0, 0, 1.0]), np.array([1.0, 0, 0]))[:3, :])
    wo, ho = info['outerWidth'], info['height']
    x1 = HEAD_FLOOR_X + ho
    y0, y1 = HEAD_CENTRE_Y - wo / 2, HEAD_CENTRE_Y + wo / 2
    disc = E.cyl(c, n, TAB_T, 3.2, 96)
    # plate footprint under the channel, 0.1 mm inside its outer faces (the walls themselves reach the bed)
    foot = m3.Manifold.cube([x1 - HEAD_FLOOR_X - 0.2, y1 - y0 - 0.2, TAB_T]).translate([HEAD_FLOOR_X + 0.1, y0 + 0.1, c[2]])
    plate = m3.Manifold.batch_hull([disc, foot])
    xi0 = HEAD_FLOOR_X + HEAD_CH['floor']
    xi1 = HEAD_FLOOR_X + HEAD_CH['floor'] + HEAD_CH['ch_h']
    # window in the +y wall at the bottom of the channel; it also takes away the +y lip and its 45 degree underside
    # over the window height, so the group turning out of the window does not ride on the lip
    taper = (HEAD_CH['ch_w'] - HEAD_CH['mouth']) / 2
    wy0 = HEAD_CENTRE_Y + HEAD_CH['ch_w'] / 2 - taper - 0.1
    window = m3.Manifold.cube([x1 + 0.1 - xi0, y1 + 0.1 - wy0, HEAD_WINDOW_H]).translate([xi0, wy0, z0 - 0.01])
    hole = E.cyl(c - 1.0 * n, n, TAB_T + 10.0, HOLE[r['diameterMm']] / 2, 48)
    clip = (plate + channel - window) - hole
    xm = (xi0 + xi1) / 2
    rec = {'screw': HEAD_SCREW, 'seat': c, 'n': n, 'channelAxis': [0, 0, 1], 'channelMouthDirection': [1, 0, 0],
           'channelInteriorX': [xi0, xi1], 'channelInteriorY': [HEAD_CENTRE_Y - HEAD_CH['ch_w'] / 2, HEAD_CENTRE_Y + HEAD_CH['ch_w'] / 2],
           'channelZ': [z0, z0 + HEAD_H], 'windowZ': [z0, z0 + HEAD_WINDOW_H],
           'groupTop': [xm, HEAD_CENTRE_Y, z0 + HEAD_H], 'groupTurn': [xm, HEAD_CENTRE_Y, z0 + HEAD_TURN_Z],
           'groupExit': [xm, y1 + 0.6, z0 + HEAD_TURN_Z], 'neighbourScrews': [],
           'tabRadiusMm': 3.2, 'tabMm': TAB_T, 'holeMm': HOLE[r['diameterMm']], 'channel': info}
    return clip, rec
