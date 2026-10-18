#!/usr/bin/env python3
"""Render the illustrated print sheet: the V1.6 parts to print and the 10/1 parts to throw away, or (--incremental)
the reprinted parts of a later release and the printed V1.6 parts they replace.

    /tmp/microduck-cad-venv/bin/python guide/print/make_parts_sheet.py [--out guide/print/PARTS-SHEET.html]

Every picture is rendered from the part's real STL. The 10/1 list comes from print-manifest.json (89 printed
instances); allocation to the current design comes from coverage.sourceStockAllocation and coverage.retainedStock in
full-build-data-current.json. The output is one self-contained HTML file (images embedded as JPEG data URIs).
"""
from __future__ import annotations

import argparse
import base64
import html
import io
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

HERE = Path(__file__).resolve().parent
SIM = HERE.parent.parent
MANIFEST = SIM / 'build-pack-20260913' / 'redesign-20260913' / 'print-manifest.json'
V15 = SIM / 'build-pack-20260913' / 'redesign-20260913' / 'printing' / '15-COMPLETE-INCREMENTAL-20261009' / 'complete-incremental.json'
SCRATCH = Path('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad')
sys.path.insert(0, str(SCRATCH / 'scene'))
sys.path.append(str(SIM / 'guide' / 'content'))   # same render(scene, views, out, size) when the old scratch copy is gone
from render import render  # noqa: E402

RGB = {'Orange': (232, 120, 30), 'Black': (45, 45, 48), 'Yellow': (236, 196, 60), 'White': (232, 230, 222)}

# 10/1 instance index -> (why it is retired, what replaces it). Indices are positions in print-manifest.json instances.
RETIRED = {
    2: ('Old head cap with USB window', 'Orange', 'The OpenRB moved out of the head; the new cap has a rear cable notch instead.', 'Head cap with rear cable notch'),
    7: ('Old lower head shell', 'Yellow', 'Lacks the connector relief for the head-roll motor plug.', 'Lower head shell'),
    84: ('Old face panel with Pi mount', 'White', 'The camera now sits inside the eye; the Pi mounts on the cap rails.', 'Face panel'),
    28: ('Old eye outer ring', 'Black', 'Replaced by the eye trim that matches the new face panel.', 'Eye trim'),
    18: ('Old neck U bracket', 'Black', 'Replaced by the pitch bracket with integral 1 mm screw seats (no loose washers).', 'Neck pitch bracket'),
    6: ('Coaxial jaw motor support', 'Black', 'The original open jaw support is restored.', 'Jaw support'),
    3: ('Old torso IMU clamp', 'Orange', 'Replaced by the holder for the BNO085 board.', 'IMU holder'),
    4: ('Old IMU rear cover', 'Black', 'Replaced by the matching rear cover.', 'IMU rear cover'),
    5: ('Eleven-fuse carrier', 'Black', 'Fuses are dropped from the harness.', None),
    1: ('Small-regulator cover', 'Black', 'The small regulator is gone; the DFR1202 makes all 5 V.', None),
    86: ('Camera tilt foot', 'Black', 'The rooftop camera mount was dropped; the camera is in the eye.', None),
    87: ('Camera cradle', 'Black', 'Same reason as the tilt foot.', None),
    88: ('Audio carrier', 'Black', 'This build has no speaker or amplifier.', None),
    17: ('Original PCB retaining strip', 'Black', 'Upstream battery-bay part; this wall-powered build does not use it.', None),
    8: ('Jaw frame', 'Yellow', 'The lower lip is now printed as part of a new jaw frame, so it is no longer glued in.', 'Jaw frame with the lower lip'),
    25: ('Lower lip pad', 'White', 'Printed as part of the new yellow jaw frame instead of glued into its pocket.', 'Jaw frame with the lower lip'),
    24: ('Upper lip pad', 'White', 'The upper lip is now printed as part of the lower head shell; glued in, the pad covered the two front closure screws.', 'Lower head shell'),
}
GROUP_COLOUR = {'old-orange-plate1': 'Orange', 'black': 'Black', 'old-black-plate5': 'Black', 'yellow': 'Yellow', 'WHITE': 'White'}

NEW_NAMES = {
    'head_bottom': 'Lower head shell', 'face_panel': 'Face panel', 'head_cap': 'Head cap with rear cable notch',
    'speaker_cradle': 'Speaker cradle', 'speaker_keeper': 'Speaker keeper', 'imu_clamp': 'IMU holder', 'eye_trim': 'Eye trim',
    'camera_retainer': 'Camera retainer', 'jaw_support_original': 'Jaw support', 'mouth_sliding_ring': 'Mouth sliding ring',
    'neck_pitch_integrated_1mm_seats': 'Neck pitch bracket', 'imu_cover': 'IMU rear cover', 'openrb_tray': 'OpenRB tray',
}
COLOUR_ORDER = ['Yellow', 'White', 'Orange', 'Black']


def picture(path: Path, colour: str, size=(520, 400)) -> str:
    m = trimesh.load(path, force='mesh', process=False)
    v = np.asarray(m.vertices, dtype=np.float64)
    c = (v.min(0) + v.max(0)) / 2
    r = float(np.linalg.norm(v.max(0) - v.min(0))) / 2
    d = np.array([1.0, -1.25, 0.9])
    d /= np.linalg.norm(d)
    pos = c + d * r / np.tan(np.radians(15)) * 1.1   # 0.92 clipped the top of tall parts
    scene = {'p': {'v': v - 0, 'f': np.asarray(m.faces), 'color': RGB[colour], 'module': 'p'}}
    with tempfile.TemporaryDirectory() as tmp:
        out = render(scene, [(pos.tolist(), c.tolist(), (0, 0, 1))], str(Path(tmp) / 'x.png'), size=size)[0]
        img = Image.open(out).convert('RGB')
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=82, optimize=True)
    ext = sorted((v.max(0) - v.min(0)).tolist(), reverse=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode(), ' × '.join(f'{x:.0f}' for x in ext) + ' mm'


def first_existing(*paths):
    for p in paths:
        if p and Path(p).exists():
            return Path(p)
    return None


CSS = """
:root{--bg:#f7f6f2;--card:#fff;--ink:#1d1d1f;--muted:#5d5d63;--line:#e3e1da;--accent:#c4501a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
header h1{font-size:28px;margin:0 0 6px}header p{color:var(--muted);margin:0 0 8px}
h2{font-size:22px;margin:36px 0 6px}.lead{color:var(--muted);margin:0 0 12px}
h3.colour{display:flex;align-items:center;gap:10px;font-size:18px;margin:22px 0 10px}
.dot{width:18px;height:18px;border-radius:50%;border:1px solid #0003;display:inline-block}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.card img{width:100%;height:auto;display:block;background:#f4f4f1}
.txt{padding:10px 12px 12px}.txt h3{font-size:16px;margin:0 0 4px}.sub{margin:0;color:var(--muted);font-size:14px;overflow-wrap:anywhere}
.repl{margin:6px 0 0;font-size:14px;color:var(--accent);font-weight:600}.repl.none{color:var(--muted);font-weight:500}
.spares{padding-left:20px}.spares li{margin:6px 0}
"""


# Incremental reprints: release manifest -> parts to print; these printed V1.6 parts become scrap.
RETIRED_INCREMENTAL = {
    'V1.7': [
        ('V1.6 head cap', 'Orange', HERE / 'release-V1.7' / 'retired' / 'head_cap-V1.6.stl',
         'Its Pi rails sit 4.6 mm too far forward: the plugged 40-pin housing hits the camera as the cap goes on.', 'Head cap, Pi seat moved back'),
        ('V1.6 OpenRB tray', 'Black', HERE / 'release-V1.7' / 'retired' / 'openrb_tray-V1.6.stl',
         'Its rails block the two side DYNAMIXEL plugs of the OpenRB.', 'OpenRB tray with port notches'),
    ],
}
_SIMP = SIM / 'build-pack-20260913' / 'redesign-20260913'
RETIRED_INCREMENTAL['V1.8'] = [
    ('Printed head cap (V1.6 or V1.7, whichever you printed)', 'Orange', HERE / 'candidates' / 'head-cap-pi-shift' / 'head_cap-pi-shift-print.stl',
     'Its Pi rails sit 1 mm too low: the plugged jumper housings need the beak window that the new lower shell no longer has.', 'Head cap, Pi rails raised'),
    ('Printed face panel (V1.6)', 'White', _SIMP / 'head-redesign-20261008' / 'camera-ribbon-repair' / 'positive-x225' / 'face_three_screw_camera-world.stl',
     'Carries the three clamp anchors, corner bosses and oval slot that nothing uses.', 'Face plate with direct camera screws'),
    ('Printed lower head shell (V1.6)', 'Yellow', _SIMP / 'workflow-review-20261009' / 'enclosed-wiring-repair' / 'motor-wires' / 'head-neck-local-20261009' / 'head-bottom-eh14-clearance-world.stl',
     'Has the square window in the beak roof.', 'Lower head shell without window'),
    ('Upper lip pad (original 10/1 print)', 'White', SIM / 'build-pack-20260913' / 'assembly' / 'print-parts' / 'community-40.stl',
     'The upper lip is now part of the yellow lower head shell. Glued in, this pad covered the two front closure screws, so the head could not be opened again.', 'Lower head shell without window'),
    ('Jaw frame (original 10/1 print)', 'Yellow', SIM / 'build-pack-20260913' / 'assembly' / 'print-parts' / 'community-4.stl',
     'The lower lip is now printed as part of a new jaw frame, so nothing in the beak is glued.', 'Jaw frame with the lower lip'),
    ('Lower lip pad (original 10/1 print)', 'White', SIM / 'build-pack-20260913' / 'assembly' / 'print-parts' / 'community-42.stl',
     'Printed as part of the new yellow jaw frame instead of glued into its pocket, so the beak is one colour.', 'Jaw frame with the lower lip'),
    ('Printed eye trim (V1.6)', 'Black', _SIMP / 'printing' / '15-COMPLETE-INCREMENTAL-20261009' / 'black-source-print' / 'eye_trim-print.stl',
     'Lacks the two pilots for the camera screws.', 'Eye trim with camera screw pilots'),
    ('Camera retainer ring (V1.6)', 'Black', _SIMP / 'printing' / '15-COMPLETE-INCREMENTAL-20261009' / 'black-source-print' / 'camera_retainer-print.stl',
     'The camera is now screwed straight to the face through its own holes.', None),
    ('OpenRB tray (V1.6 or V1.7)', 'Black', HERE / 'stl' / 'openrb_tray.stl',
     'The OpenRB-150 moves into the rear pack behind the hip-yaw motors; nothing hangs under the crotch.', 'Rear electronics pack'),
    ('Integrated power support (original 10/1 print)', 'Orange', _SIMP / 'printing' / '01-STL' / 'plate-01' / '01_power-support-integrated-print.stl',
     'The rear pack takes its place on the same four hip-yaw case screws.', 'Rear electronics pack'),
    ('Fuse bank (original 10/1 print)', 'Black', _SIMP / 'printing' / '01-STL' / 'plate-03' / '04_fuse-bank-print.stl',
     'Fuses are dropped from the harness.', None),
    ('Open regulator insert (original 10/1 print)', 'Black', _SIMP / 'printing' / '01-STL' / 'plate-04' / '04_regulator-open-insert-print.stl',
     'The DFR1202 converter sits in the rear pack.', 'Rear electronics pack'),
    ('IMU holder (V1.6)', 'Orange', _SIMP / 'workflow-review-20261009' / 'enclosed-wiring-repair' / 'power-sensor' / 'imu-clamp-retained-world.stl',
     'The BNO085 slides into the slot in the rear pack plate.', 'Rear electronics pack'),
    ('IMU rear cover (V1.6)', 'Black', _SIMP / 'workflow-review-20261009' / 'enclosed-wiring-repair' / 'power-sensor' / 'imu-cover-retained-world.stl',
     'Went with the IMU holder.', 'Rear pack cover'),
    ('Speaker cradle (V1.6)', 'Orange', _SIMP / 'workflow-review-20261009' / 'enclosed-wiring-repair' / 'head-layout' / 'speaker-mount-repair' / 'speaker_cradle-print.stl',
     'This build has no speaker; it can come back later as a loose add-on. Keep it with the speaker if you like.', None),
    ('Speaker keeper (V1.6)', 'Orange', _SIMP / 'workflow-review-20261009' / 'enclosed-wiring-repair' / 'head-layout' / 'speaker-mount-repair' / 'speaker_keeper-print.stl',
     'Goes with the speaker cradle.', None),
]
RETIRED_INCREMENTAL['V1.9'] = [
    ('Printed head cap (V1.8)', 'Orange', HERE / 'world' / 'head_cap.stl',
     'Has no speaker collar, retainer bosses or amplifier posts, and still has the rear cable notch with its zip tie. The V1.9 cap takes the speaker, amplifier and the cap cable clip.', 'Head cap for speaker, amplifier and neck bundle'),
    ('Printed rear electronics pack (V1.8)', 'Orange', HERE / 'world' / 'rear_pack.stl',
     'Its BNO085 shelf with zip-tie slots is replaced by a rib with two M2 x 4 pilots, and its T-head is 0.4 mm too small to seat the printed side shells. The Black rear pack cover stays.', 'Rear electronics pack with BNO085 rib'),
]
INCREMENTAL_NAMES = {'head_cap': 'Head cap, Pi seat moved back', 'openrb_tray': 'OpenRB tray with port notches'}
INCREMENTAL_NOTES = {'head_cap': 'Replaces the V1.6 cap. Print with the 4 mm brim already in the file.',
                     'openrb_tray': 'Replaces the V1.6 tray. Two notches in the rails let the side servo plugs in.'}
INCREMENTAL_NAMES_BY_VERSION = {
    'V1.8': {'head_cap': 'Head cap, Pi rails raised', 'face_panel': 'Face plate with direct camera screws', 'head_bottom': 'Lower head shell without window', 'jaw_frame': 'Jaw frame with the lower lip',
             'eye_trim': 'Eye trim with camera screw pilots', 'rear_pack': 'Rear electronics pack', 'rear_pack_cover': 'Rear pack cover'}}
INCREMENTAL_NOTES_BY_VERSION = {
    'V1.8': {'head_cap': 'Replaces the printed cap. Pi rails 1 mm higher, rear roof bosses gone. Print with the 4 mm brim already in the file.',
             'face_panel': 'Replaces the printed face. Flat plate; the camera screws to it through its own two holes, the other two holes sit on pegs.',
             'head_bottom': 'Replaces the printed lower shell and the upper lip pad. Same shell without the square beak window, with the upper lip printed on and two 5 mm driver holes through it.',
             'jaw_frame': 'Replaces the printed jaw frame and the lower lip pad. Same jaw with the lower lip printed in its pocket; break the low support from under the two back corners of the lip.',
             'eye_trim': 'Replaces the printed eye trim. Two 1.7 mm pilots take the M2 x 8 camera screws.',
             'rear_pack': 'New. Holds the OpenRB-150, the DFR1202 converter and the BNO085 behind the hip-yaw motors on the four existing case screws.',
             'rear_pack_cover': 'New. Closes the back of the pack with four screws.'}}
INCREMENTAL_NAMES_BY_VERSION['V1.9'] = {
    'rear_pack': 'Rear electronics pack with BNO085 rib', 'head_cap_v19': 'Head cap for speaker, amplifier and neck bundle',
    'speaker_retainer_v19': 'Speaker retainer', 'clip_torso_v19': 'Torso cable clip', 'clip_bracket_v19': 'Neck bracket cable clip',
    'clip_head_v19': 'Head cable clip', 'clip_cap_v19': 'Cap cable clip'}
INCREMENTAL_NOTES_BY_VERSION['V1.9'] = {
    'rear_pack': 'Replaces the printed V1.8 pack. The BNO085 screws to a rib with two M2 x 4 at the bench before the pack goes in; the T-head and two shoulder bars seat the printed side shells. Keep the V1.8 Black cover. Tree support under the ears and bars.',
    'head_cap_v19': 'Replaces the printed V1.8 cap. Speaker collar and two retainer bosses in the roof, two amplifier posts, no rear cable notch; Pi rails and closure screws unchanged. Print with the 4 mm brim already in the file.',
    'speaker_retainer_v19': 'New. 1.6 mm frame that holds the speaker and its foam ring in the cap roof with two M2 x 6; no glue.',
    'clip_torso_v19': 'New. 2 mm tab under S12-horn-025 (now M2 x 8) with a snap-in channel for the 8-wire neck bundle.',
    'clip_bracket_v19': 'New. 2 mm tab under S11-horn-040 (now M2 x 8) on the head-pitch axis; same channel.',
    'clip_head_v19': 'New. 2 mm tab under H-jaw_support-03 (now M2.5 x 8); the bundle goes down its channel and out through a side window.',
    'clip_cap_v19': 'New. 2 mm tab under E-pi-04 (now M2 x 8) over the Pi top edge; same channel.'}


RETIRED_INCREMENTAL['V1.10'] = [
    ('Printed rear pack cover (V1.8)', 'Black', HERE / 'world' / 'rear_pack_cover.stl',
     'The V1.10 rear frame carries the same cover outline, four screw holes and lip, plus the converter box behind the pack. Reuse its four M2 x 6 screws for the frame.', 'Rear converter box frame'),
]
RETIRED_LEAD_BY_VERSION = {'V1.10': 'Take the old cover off the pack and keep its four screws; the new frame goes on in its place.'}
INCREMENTAL_NAMES_BY_VERSION['V1.10'] = {'rear_frame': 'Rear converter box frame', 'rear_lid': 'Rear converter box lid'}
INCREMENTAL_NOTES_BY_VERSION['V1.10'] = {
    'rear_frame': 'Replaces the printed V1.8 rear pack cover; screws to the pack with the cover\'s four M2 x 6. Holds two XL4015 boards and the 5991 USB-C trigger. Prints standing on its bottom wall with tree support inside the box (pull it out through the open back) and under the front lip, and with the 4 mm brim already in the file.',
    'rear_lid': 'New. Flat 1.2 mm lid that closes the back of the box with two M2 x 6. No support.'}

RETIRED_INCREMENTAL['V1.11'] = [
    ('Printed rear pack cover (V1.8)', 'Black', HERE / 'world' / 'rear_pack_cover.stl',
     'The V1.11 rear frame carries the same cover outline, four screw holes and lip, plus the converter box behind the pack. Reuse its four M2 x 6 screws for the frame.', 'Rear converter box frame'),
    ('Rear converter box frame (V1.10, if printed)', 'Orange', HERE / 'back-plate' / 'rear_frame-world.stl',
     'Superseded by the V1.11 frame (layout F): boards lie flat in three tiers and slide in from the back; do not fit the V1.10 frame.', 'Rear converter box frame'),
    ('Rear converter box lid (V1.10, if printed)', 'Orange', HERE / 'back-plate' / 'rear_lid-world.stl',
     'Fits only the V1.10 frame. The V1.11 box closes with a rounded cap.', 'Rear converter box cap'),
]
RETIRED_LEAD_BY_VERSION['V1.11'] = 'Take the old cover off the pack and keep its four screws; the new frame goes on in its place. If you printed the V1.10 box, set it aside.'
INCREMENTAL_NAMES_BY_VERSION['V1.11'] = {'rear_frame': 'Rear converter box frame', 'rear_lid': 'Rear converter box cap'}
INCREMENTAL_NOTES_BY_VERSION['V1.11'] = {
    'rear_frame': 'Replaces the printed V1.8 rear pack cover (and the V1.10 frame); screws to the pack with the cover\'s four M2 x 6. Holds two XL4015 boards and the 5991 USB-C trigger, which slide in from the open back. Prints standing on its open back rim with tree support inside the box and under the cover flap, no brim. Clean the support off the board boss tips so the boards sit flat.',
    'rear_lid': 'New. Rounded cap that closes the back of the box: slide it on, lift it so the two top teeth click into the frame slots, then fit two M2 x 6 through the ears. Prints on its flat back face with tree support under the rounded edges and the ears.'}

_STOCK = SIM / 'build-pack-20260913' / 'assembly' / 'print-parts'
RETIRED_INCREMENTAL['V1.12'] = [
    ('Left torso shell (10/1 print)', 'Orange', _STOCK / 'community-8.stl',
     'Joined to the right shell by the cross screw down a tunnel. The white V2.0 shell screws down into the rear pack instead and has counterbores for the M2 x 4 horn screws.', 'White left torso shell'),
    ('Right torso shell (10/1 print)', 'Orange', _STOCK / 'community-10.stl',
     'Same change on the right side.', 'White right torso shell'),
    ('Left thigh (10/1 print)', 'Orange', _STOCK / 'community-74.stl',
     'Same part; only the colour changes. Swap it only when that leg is apart anyway.', 'White left thigh'),
    ('Right thigh (10/1 print)', 'Orange', _STOCK / 'community-72.stl',
     'Same part; only the colour changes. Swap it only when that leg is apart anyway.', 'White right thigh'),
    ('Head cap (V1.9 print)', 'Orange', HERE / 'ext-v19' / 'head_cap_v19-world.stl',
     'Same cap; only the colour changes. Move the Pi, speaker, amplifier and cap clip across and close it with the same three M2.6 x 6.', 'White head cap'),
]
RETIRED_LEAD_BY_VERSION['V1.12'] = 'Colour scheme C. These orange parts are not broken: keep them as spares and mark them so they do not get mixed up with the white prints.'
RETIRED_HEADING_BY_VERSION = {'V1.12': 'Keep these as spares'}
INCREMENTAL_NAMES_BY_VERSION['V1.12'] = {'shell_left_v20': 'Left torso shell, screwed to the pack', 'shell_right_v20': 'Right torso shell, screwed to the pack',
                                         'thigh_left': 'Left thigh', 'thigh_right': 'Right thigh', 'head_cap_v19_white': 'Head cap (V1.9, white)'}
INCREMENTAL_NOTES_BY_VERSION['V1.12'] = {
    'shell_left_v20': 'Replaces the orange left shell. One M2 x 6 goes straight down through the round counterbore in its roof into the rear pack shoulder bar (drill the bar 1.6 mm through the hole first, tape flag 7.0 mm from the tip). No cross tunnel. Four M2 x 4 into the ID12 horn sit in counterbores. Prints on its flat outer face, no brim.',
    'shell_right_v20': 'Replaces the orange right shell. Same pack screw on this side; three M2 x 4 in counterbores into the ID12 idler, the rear hole keeps its M2 x 8 under the clip tab. Prints on its flat outer face, no brim.',
    'thigh_left': 'The same thigh in white (colour only). Prints in the 10/1 pose, no brim.',
    'thigh_right': 'The same thigh in white (colour only). Prints in the 10/1 pose, no brim.',
    'head_cap_v19_white': 'The same V1.9 cap in white: same Pi rails, speaker collar, amplifier posts and closing pilots for the three M2.6 x 6. Prints roof down with the 4 mm brim already in the file; the support under the crown is ironed, but sand the matte band lightly and push a needle through each sound hole above the speaker.'}


# V1.13: the single print-now package, the V1.11 Orange box plate plus the V1.12 White plate (Shawn 2026-10-14: one package).
RETIRED_INCREMENTAL['V1.13'] = RETIRED_INCREMENTAL['V1.11'] + RETIRED_INCREMENTAL['V1.12']
RETIRED_LEAD_BY_VERSION['V1.13'] = ('Take the old black cover off the pack and keep its four screws; the new box frame goes on in its place. '
                                    'The orange shells, thighs and cap are not broken: keep them as spares and mark them so they do not get mixed up with the white prints.')
RETIRED_HEADING_BY_VERSION['V1.13'] = 'Set these aside'
INCREMENTAL_NAMES_BY_VERSION['V1.13'] = dict(INCREMENTAL_NAMES_BY_VERSION['V1.11'], **INCREMENTAL_NAMES_BY_VERSION['V1.12'])
INCREMENTAL_NOTES_BY_VERSION['V1.13'] = dict(INCREMENTAL_NOTES_BY_VERSION['V1.11'], **INCREMENTAL_NOTES_BY_VERSION['V1.12'])
# V1.14: the V1.13 package re-sliced (X1C files open on Preview in Bambu Studio); same parts, same sheet.
for _t in (RETIRED_INCREMENTAL, RETIRED_LEAD_BY_VERSION, RETIRED_HEADING_BY_VERSION, INCREMENTAL_NAMES_BY_VERSION, INCREMENTAL_NOTES_BY_VERSION):
    _t['V1.14'] = _t['V1.13']
# V1.15: the V1.14 package with the box frame and cap regenerated: no cap ears (one hidden M2 x 10 through the cap back into the
# 5991 boss, plus a hook on the other side), no front passage P1 (every box wire runs outside the box). Same White plate.
RETIRED_INCREMENTAL['V1.15'] = RETIRED_INCREMENTAL['V1.13']
RETIRED_LEAD_BY_VERSION['V1.15'] = RETIRED_LEAD_BY_VERSION['V1.13']
RETIRED_HEADING_BY_VERSION['V1.15'] = RETIRED_HEADING_BY_VERSION['V1.13']
INCREMENTAL_NAMES_BY_VERSION['V1.15'] = dict(INCREMENTAL_NAMES_BY_VERSION['V1.13'])
INCREMENTAL_NOTES_BY_VERSION['V1.15'] = dict(INCREMENTAL_NOTES_BY_VERSION['V1.13'],
    rear_frame='Replaces the printed V1.8 rear pack cover; screws to the pack with the cover\'s four M2 x 6. Holds two XL4015 boards and the 5991 USB-C trigger, which slide in from the open back; every wire leaves through a side window and stays outside the box (the front plate is solid); the 7 V pair and the Pi lead cross the box top and drop through the small notch at the front edge of the top wall into the pack. Prints standing on its open back rim with tree support inside the box and under the cover flap, no brim. Clean the support off the board boss tips so the boards sit flat.',
    rear_lid='New. Rounded cap that closes the back of the box: slide it on low, lift it so the two top teeth click into the frame slots and the hook on the right catches the 5991 window, then drive one M2 x 10 through the round hole low on the left of its back into the 5991 corner boss. No ears, nothing outside the box outline. Prints on its flat back face with tree support under the rounded edges.')

# V1.16: the V1.15 package with the cap held by four hidden M2 x 10 (two through the 7 V converter's top corner holes, two
# through the 5991 upper holes); no tongues, tooth slots, hook or hook notch; the cap pushes straight on. Same White plate.
for _t in (RETIRED_INCREMENTAL, RETIRED_LEAD_BY_VERSION, RETIRED_HEADING_BY_VERSION, INCREMENTAL_NAMES_BY_VERSION):
    _t['V1.16'] = _t['V1.15']
INCREMENTAL_NOTES_BY_VERSION['V1.16'] = dict(INCREMENTAL_NOTES_BY_VERSION['V1.15'],
    rear_lid='New. Rounded cap that closes the back of the box: push it straight on, then drive four M2 x 10 through the round holes in its back: two at the top corners through the 7 V converter\'s upper holes, two low through the 5991\'s upper holes. The heads stay hidden inside the cap. No ears, no tongues, no hook, nothing outside the box outline. Prints on its flat back face with tree support under the rounded edges.')

# V1.17: the V1.16 package plus three head parts for the Radxa Cubie A7Z and the Radxa Camera 13M 214 (Shawn 2026-10-15). The
# white A7Z cap replaces the white V1.9 cap of V1.16 (never printed); the eye trim is the V1.8 trim and is reused.
RETIRED_INCREMENTAL['V1.17'] = RETIRED_INCREMENTAL['V1.11'] + [x for x in RETIRED_INCREMENTAL['V1.12'] if x[0] != 'Head cap (V1.9 print)'] + [
    ('Head cap (V1.9 print)', 'Orange', HERE / 'ext-v19' / 'head_cap_v19-world.stl',
     'Fits the Pi Zero W only: its board rails press on the A7Z camera connector and microSD socket. Keep it as a spare for the Pi. Move the speaker, amplifier and cap clip screws across.', 'White head cap for the A7Z'),
    ('Face panel (V1.8 print)', 'White', HERE / 'world' / 'face_panel-v18.stl',
     'Its back carries the pads and pegs for the Camera Module 3, not the four bosses the Radxa 13M 214 camera screws into. Take the black eye trim off it and reuse the trim.', 'Face panel for the 13M 214 camera'),
    ('Cap cable clip (V1.9 print)', 'Orange', HERE / 'ext-v19' / 'clip_cap_v19-world.stl',
     'Its arm sits on the A7Z micro HDMI socket. Reuse its M2 x 8.', 'Cap cable clip with HDMI notch'),
]
INTRO_BY_VERSION = {'V1.17': ('V1.17 is all of V1.16 plus three head parts for the Radxa Cubie A7Z board and the Radxa 13M 214 camera: '
                                'a head cap with relieved board rails and a slot at each rail end, a face with four camera bosses, and a cap clip '
                                'with a notch over the HDMI socket. The black eye trim does not change: reuse the one on the robot. '
                                'Print only this package; V1.16 was never printed and is replaced.')}
RETIRED_LEAD_BY_VERSION['V1.17'] = ('Take the old black cover off the pack and keep its four screws; the new box frame goes on in its place. '
                                    'The orange shells, thighs and V1.9 cap are not broken: keep them as spares and mark them so they do not get mixed up with the white prints.')
RETIRED_HEADING_BY_VERSION['V1.17'] = 'Set these aside'
INCREMENTAL_NAMES_BY_VERSION['V1.17'] = dict({k: v for k, v in INCREMENTAL_NAMES_BY_VERSION['V1.16'].items() if k != 'head_cap_v19_white'},
                                             head_cap_a7z='White head cap for the A7Z', face_panel_a7z='Face panel for the 13M 214 camera',
                                             clip_cap_a7z='Cap cable clip with HDMI notch')
INCREMENTAL_NOTES_BY_VERSION['V1.17'] = dict({k: v for k, v in INCREMENTAL_NOTES_BY_VERSION['V1.16'].items() if k != 'head_cap_v19_white'},
    head_cap_a7z="Replaces the orange V1.9 cap. The V1.9 cap with two inside changes for the A7Z: the board rails are cut back 1.6 mm, so the board rests only on a round pad at each of its four holes, and each rail end has a slot, one for the camera connector and ribbon (at the robot's left end), one for the microSD card (at the robot's right end). Speaker collar, amplifier posts, Pi screws and the three M2.6 x 6 closing screws are unchanged. Prints roof down with the 4 mm brim already in the file; the support under the crown is ironed, but sand the matte band lightly and push a needle through each sound hole above the speaker. Clean any support off the rail ends.",
    face_panel_a7z='Replaces the printed V1.8 face. Same front; on the back, four round bosses take the Radxa 13M 214 camera with 4 x M2 x 4, and the two holes above and below the eye take the 2 x M2 x 6 that hold the black eye trim from behind. Reuse the trim on the robot. Prints front down, no brim.',
    clip_cap_a7z='Replaces the orange V1.9 cap clip. Same clip with a notch in its underside so the arm clears the A7Z micro HDMI socket; same M2 x 8. Prints flat, no brim; on the X1C file a little support fills the notch, pick it out.')

# V1.18: only the D-010 battery backpack frame and cap (Shawn 2026-10-15: V1.17 is being printed, so V1.18 drops everything in it). The backpack is an alternative to the rear converter box on the same four cover screws: it retires nothing.
RETIRED_INCREMENTAL['V1.18'] = []
INTRO_BY_VERSION['V1.18'] = ('V1.18 holds only the battery backpack: a frame and a cap that hold the 2S battery, its switch and the '
                             'DFR1202 5 V board, and bolt on in place of the rear converter box with the same four screws. '
                             'V1.17 is the package you are printing now; nothing from it is repeated here, and the backpack retires nothing.')
RETIRED_LEAD_BY_VERSION['V1.18'] = 'Nothing to set aside: the backpack is an alternative to the rear converter box, which you keep.'
RETIRED_HEADING_BY_VERSION['V1.18'] = 'Set these aside'
INCREMENTAL_NAMES_BY_VERSION['V1.18'] = dict(battery_backpack_frame='Battery backpack frame', battery_backpack_cap='Battery backpack cap')
INCREMENTAL_NOTES_BY_VERSION['V1.18'] = dict(
    battery_backpack_frame='New, an alternative to the rear converter box frame (it replaces nothing). The same front plate and four corner holes, with a box 26.75 mm deep behind it: a pocket in the floor of the narrow bottom part takes the REV switch rocker down, the battery stands upright behind it, and the DFR1202 clips behind the front plate on two ribs and four flexible lips. Prints on its open back rim like the box frame, with tree support and no brim; take every support out from under the front plate and round the lips.',
    battery_backpack_cap='New. Rounded cap that closes the battery backpack: push it straight on and drive three M2 x 6 through the round holes in its back (two high at the sides, one low in the middle). Two thin fences inside keep the battery centred. Prints on its flat back face, no brim.')

# V1.19: the two screw caps with 3.0 mm screw-head floors (Shawn 2026-10-15, IMG_7004: the 1.0 mm floors under the two low
# hidden screws of the printed V1.17 box cap tore into open holes when it was taken off). Frames unchanged.
RETIRED_INCREMENTAL['V1.19'] = [
    ('Box cap (V1.17 print)', 'Orange', HERE / 'release-V1.19' / 'retired' / 'rear_lid-V1.17.stl',
     'The 1.0 mm floors the four screw heads sit on are too thin: two tore through when the cap came off. Keep its four M2 x 10.', 'Box cap, 3 mm screw floors'),
    ('Battery backpack cap (V1.18 print)', 'Orange', HERE / 'release-V1.19' / 'retired' / 'battery_backpack_cap-V1.18.stl',
     'Same 1.0 mm screw floors as the old box cap. Its M2 x 6 are too short for the new cap.', 'Battery backpack cap, 3 mm screw floors'),
]
INTRO_BY_VERSION['V1.19'] = ('V1.19 holds only the two screw caps: the rear converter box cap and the battery backpack cap. Each screw head '
                             'now sits on a 3.0 mm printed floor instead of 1.0 mm. Both frames stay: keep the printed V1.17 box frame and '
                             'the printed V1.18 backpack frame.')
RETIRED_LEAD_BY_VERSION['V1.19'] = 'Throw away the old caps once the new ones fit; keep the box cap\'s four M2 x 10.'
RETIRED_HEADING_BY_VERSION['V1.19'] = 'Replace these'
INCREMENTAL_NAMES_BY_VERSION['V1.19'] = dict(rear_lid='Box cap, 3 mm screw floors', battery_backpack_cap='Battery backpack cap, 3 mm screw floors')
INCREMENTAL_NOTES_BY_VERSION['V1.19'] = dict(
    rear_lid='Replaces the V1.17 box cap. Same outside and the same four M2 x 10 through the round holes in its back; each head now sits on a 3.0 mm floor (was 1.0 mm). The floors grow toward the boards, so the screw depth is unchanged. Tighten until the cap sits on the rim, then stop. Prints on its flat back face, no brim.',
    battery_backpack_cap='Replaces the V1.18 backpack cap. Same outside; each of the three screw heads sits on a 3.0 mm floor (was 1.0 mm), so the screws become 3 x M2 x 8 (were M2 x 6). Prints on its flat back face, no brim.')

# V1.20: V1.19 was never printed ("1.19的两个没打", Shawn 2026-10-17), so its two caps travel here with the backpack frame
# refitted to the Swann 39 switch in hand (its 11.5 mm body did not pass the V1.18 10.6 mm hole).
RETIRED_INCREMENTAL['V1.20'] = [
    ('Battery backpack frame (V1.18 print)', 'Orange', HERE / 'release-V1.20' / 'retired' / 'battery_backpack_frame-V1.18.stl',
     'Its 10.6 mm switch hole is too narrow for the Swann 39 switch body (11.5 mm).', 'Backpack frame, Swann hole'),
    ('Battery backpack cap (V1.18 print)', 'Orange', HERE / 'release-V1.20' / 'retired' / 'battery_backpack_cap-V1.18.stl',
     'Thin 1.0 mm screw floors, and it no longer meets the deeper frame. Its M2 x 6 are too short for the new cap.', 'Battery backpack cap, 3 mm screw floors'),
    ('Box cap (V1.17 print)', 'Orange', HERE / 'release-V1.20' / 'retired' / 'rear_lid-V1.17.stl',
     'The 1.0 mm floors the four screw heads sit on are too thin: two tore through when the cap came off. Keep its four M2 x 10.', 'Box cap, 3 mm screw floors'),
]
INTRO_BY_VERSION['V1.20'] = ('V1.20 is one orange plate. It holds the battery backpack frame with a wider switch hole for the Swann 39 '
                             'switch, the backpack cap, and the rear converter box cap from V1.19, which was never printed. '
                             'Print this instead of V1.19.')
RETIRED_LEAD_BY_VERSION['V1.20'] = 'Throw these away once the new parts fit; keep the box cap\'s four M2 x 10.'
RETIRED_HEADING_BY_VERSION['V1.20'] = 'Replace these'
INCREMENTAL_NAMES_BY_VERSION['V1.20'] = dict(rear_lid='Box cap, 3 mm screw floors', battery_backpack_frame='Backpack frame, Swann hole',
                                             battery_backpack_cap='Battery backpack cap, 3 mm screw floors')
INCREMENTAL_NOTES_BY_VERSION['V1.20'] = dict(
    rear_lid=INCREMENTAL_NOTES_BY_VERSION['V1.19']['rear_lid'],
    battery_backpack_frame='Replaces the V1.18 backpack frame. The floor hole is now 12.3 x 27.5 mm, the Swann 39 cutout, and the rocker pocket under it 14.4 mm wide for the 13.8 mm flange; the box is 0.7 mm deeper so the battery clears the thicker switch body. Wire the switch lead first, then push the switch up through the hole from the pocket until both wings click. Prints on its open back rim with tree support and no brim; take every support out from under the front plate and round the lips.',
    battery_backpack_cap='Replaces the V1.18 backpack cap. Same outside, 0.7 mm further back to meet the deeper frame; each of the three screw heads sits on a 3.0 mm floor, so the screws are 3 x M2 x 8 (were M2 x 6). Prints on its flat back face, no brim.')

def page_html(version: str, body: list[str]) -> str:
    css = CSS
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>MicroDuck prints {version}</title><style>{css}</style></head><body><main>' + '\n'.join(body) + '</main></body></html>')


def card(title, sub, img, extra=''):
    return (f'<article class="card"><img src="{img}" alt="{html.escape(title)}" loading="lazy">'
            f'<div class="txt"><h3>{html.escape(title)}</h3><p class="sub">{html.escape(sub)}</p>{extra}</div></article>')


def incremental(args) -> None:
    m = json.loads(args.incremental.read_text())
    version = m['version']
    names = INCREMENTAL_NAMES_BY_VERSION.get(version, INCREMENTAL_NAMES); notes = INCREMENTAL_NOTES_BY_VERSION.get(version, INCREMENTAL_NOTES)
    body = [f'<header><h1>MicroDuck prints {version}</h1><p>{len(m["parts"])} parts to print, and {len(RETIRED_INCREMENTAL[version])} printed part{"s" if len(RETIRED_INCREMENTAL[version]) != 1 else ""} they replace. '
            'Every other printed part stays.</p>' + (f'<p>{html.escape(INTRO_BY_VERSION[version])}</p>' if version in globals().get('INTRO_BY_VERSION', {}) else '') + '</header>',
            f'<section><h2>Print these {len(m["parts"])} parts</h2><p class="lead">One plate per colour. Each colour has a Bambu X1C file and an Elegoo Centauri Carbon file; use either printer.</p>']
    for c in COLOUR_ORDER:
        rows = [r for r in m['parts'] if r['color'] == c]
        if not rows:
            continue
        body.append(f'<h3 class="colour"><span class="dot" style="background:rgb{RGB[c]}"></span>{c} plate · {len(rows)} part{"s" if len(rows) > 1 else ""}</h3><div class="grid">')
        for r in rows:
            img, dims = picture(Path(r['path']), c)
            body.append(card(names[r['key']], f'{notes[r["key"]]} {dims}', img))
        body.append('</div>')
    lead = RETIRED_LEAD_BY_VERSION.get(version, 'The new and old parts look almost the same. Mark the old ones before the new prints arrive.')
    heading = RETIRED_HEADING_BY_VERSION.get(version, 'Throw these away')
    body.append(f'</section><section><h2>{heading}</h2><p class="lead">{html.escape(lead)}</p><div class="grid">')
    for name, colour, path, why, repl in RETIRED_INCREMENTAL[version]:
        img, dims = picture(path, colour)
        tail = f'<p class="repl">Replaced by: {html.escape(repl)}</p>' if repl else '<p class="repl none">Nothing replaces it.</p>'
        body.append(card(name, f'{colour} · {why} Size {dims}.', img, tail))
    body.append('</div></section>')
    args.out.write_text(page_html(version, body))
    print(json.dumps({'out': str(args.out), 'bytes': args.out.stat().st_size, 'print': len(m['parts']), 'retired': len(RETIRED_INCREMENTAL[version])}))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=HERE / 'PARTS-SHEET.html')
    ap.add_argument('--version', default='V1.6')
    ap.add_argument('--incremental', type=Path, help='incremental release manifest (lists only the reprinted parts)')
    args = ap.parse_args()
    if args.incremental:
        return incremental(args)

    inst = json.loads(MANIFEST.read_text())['instances']
    v15 = json.loads(V15.read_text())

    new = []
    for p in v15['parts']:
        path = Path(p['path'])
        if p['key'] == 'head_cap':
            path = first_existing(HERE / 'stl' / 'head_cap.stl', SCRATCH / 'print-work' / 'cap' / 'head_cap_notched-print.stl') or path
        new.append({'key': p['key'], 'name': NEW_NAMES[p['key']], 'colour': p['color'], 'path': path,
                    'replaces': [int(s) for s in p.get('replacesStockIds', [])]})
    tray = first_existing(HERE / 'stl' / 'openrb_tray.stl', SCRATCH / 'print-work' / 'tray' / 'openrb_tray-world.stl')
    if tray:
        new.append({'key': 'openrb_tray', 'name': NEW_NAMES['openrb_tray'], 'colour': 'Black', 'path': tray, 'replaces': []})

    cards_new = {c: [] for c in COLOUR_ORDER}
    for p in new:
        old = next((RETIRED[i][0] for i, r in RETIRED.items() if r[3] == p['name']), None)
        note = f'Replaces: {old}' if old else 'New part'
        if p['key'] == 'head_cap' and 'notched' not in str(p['path']) and 'stl/head_cap' not in str(p['path']):
            note += ' (picture shows V1.5; notch pending)'
        img, dims = picture(p['path'], p['colour'])
        cards_new[p['colour']].append((p['name'], f'{note} · {dims}', img))

    cards_old = []
    for i, (name, colour, why, repl) in RETIRED.items():
        path = Path(inst[i]['file'])
        img, dims = picture(path, colour)
        cards_old.append((name, colour, f'{why} Size {dims}.', repl, img))

    spares = [
        ('22 mm sliding rings', 6, 'Spare copies; 11 of the 17 are installed.'),
        ('Printed passive idlers', 12, 'Spare copies; 2 are used in the neck.'),
        ('Printed idler caps', 12, 'Spare copies; 2 are used in the neck.'),
    ]

    body = []
    body.append(f'<header><h1>MicroDuck prints {args.version}</h1><p>13 parts to print in four colours, and 14 old parts you can throw away. '
                'Everything not listed here from the 10/1 batch is still used.</p></header>')
    body.append('<section><h2>Print these 13 parts</h2><p class="lead">One plate per colour. Each colour has a Bambu X1C file and an Elegoo Centauri Carbon file; use either printer.</p>')
    for c in COLOUR_ORDER:
        if not cards_new[c]:
            continue
        body.append(f'<h3 class="colour"><span class="dot" style="background:rgb{RGB[c]}"></span>{c} plate · {len(cards_new[c])} part{"s" if len(cards_new[c]) > 1 else ""}</h3><div class="grid">')
        body += [card(n, s, img) for n, s, img in cards_new[c]]
        body.append('</div>')
    body.append('</section>')
    body.append('<section><h2>Throw these away</h2><p class="lead">' + str(len(RETIRED)) + ' printed parts from the 10/1 batch that this design no longer uses. Some old black parts look like their new versions; bin the old ones before the new prints arrive, or compare sizes with a caliper.</p><div class="grid">')
    for name, colour, why, repl, img in cards_old:
        extra = f'<p class="repl">Replaced by: {html.escape(repl)}</p>' if repl else '<p class="repl none">Not replaced</p>'
        body.append(card(name, f'{colour} · {why}', img, extra))
    body.append('</div></section>')
    body.append('<section><h2>Keep as spares</h2><ul class="spares">')
    body += [f'<li><strong>{html.escape(n)} × {q}</strong>: {html.escape(t)}</li>' for n, q, t in spares]
    body.append('</ul></section>')


    args.out.write_text(page_html(args.version, body))
    print(json.dumps({'out': str(args.out), 'bytes': args.out.stat().st_size, 'new': len(new), 'retired': len(cards_old),
                      'cap_source': str(next(p['path'] for p in new if p['key'] == 'head_cap')), 'tray_source': str(tray)}))


if __name__ == '__main__':
    main()
