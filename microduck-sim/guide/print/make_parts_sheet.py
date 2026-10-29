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

# V1.21: the two hot-glue sole molds (tools, build-pack-20260913/procurement/feet-sole-20261018). V1.20 is printed
# ("电池包那个已经打了", Shawn 2026-10-19); nothing printed is replaced.
RETIRED_INCREMENTAL['V1.21'] = []
INTRO_BY_VERSION['V1.21'] = ('V1.21 is one plate with two tools: the hot-glue molds for the left and right foot soles. They are not '
                             'robot parts, so any PLA spool works. Wipe a thin release film into the cavity, fill it with hot glue, '
                             'press the sanded foot between the four tabs onto the three pins, let it cool fully, then lift straight up.')
INCREMENTAL_NAMES_BY_VERSION['V1.21'] = dict(hotglue_mold_left='Left foot sole mold', hotglue_mold_right='Right foot sole mold')
INCREMENTAL_NOTES_BY_VERSION['V1.21'] = dict(
    hotglue_mold_left='For the left foot (community-44). Raised L at the heel end; the top of the letter points to the toe. The cavity leaves a 1.0 mm glue coat over the flat and up the rounded edge to 3 mm. Prints cavity up, 0.12 mm layers with ironing, no support, no brim.',
    hotglue_mold_right='For the right foot (community-46), mirror of the left mold, with a raised R at the heel end, top of the letter to the toe. Same coat and print settings.')

# V1.22: the ankle rework (Shawn 2026-10-19: the one-piece orange bracket has to be spread over the lower link and its
# servo, and the yellow foot pressed onto it so hard that it could not come off; every fitting loaded the ankle servo).
# Split ankle from print/ankle-split-20261019 (the 2026-10-07 design) and the slip-fit feet from print/foot-slipfit-20261019.
# The V1.21 molds were printed in black on 2026-10-19 and are not in V1.22.
_STOCK = HERE.parents[1] / 'build-pack-20260913' / 'assembly' / 'print-parts'
RETIRED_INCREMENTAL['V1.22'] = [
    ('Left ankle bracket (stock print)', 'Orange', _STOCK / 'community-66.stl',
     'A closed fork: the lower link with its servo cannot come in from above, so it was spread and pressed on, loading the servo every time.', 'Left ankle base + left ankle side'),
    ('Right ankle bracket (stock print)', 'Orange', _STOCK / 'community-64.stl',
     'Same closed fork as the left bracket.', 'Right ankle base + right ankle side'),
    ('Left ankle sleeve (stock print)', 'Black', _STOCK / 'community-62.stl',
     '9.65 mm bore on the 10 mm link boss: a press fit that is part of why the fork had to be forced.', 'Left ankle sleeve'),
    ('Right ankle sleeve (stock print)', 'Black', _STOCK / 'community-68.stl',
     'Same press fit as the left sleeve.', 'Right ankle sleeve'),
    ('Left foot (stock print)', 'Yellow', _STOCK / 'community-44.stl',
     'Press fit on the ankle bracket, so tight that it cannot be taken off without loading the ankle servo.', 'Left foot, slip fit'),
    ('Right foot (stock print)', 'Yellow', _STOCK / 'community-46.stl',
     'Same press fit as the left foot.', 'Right foot, slip fit'),
]
_V122_INTRO_TWO_FEET = ('V1.22 is three plates and reworks both ankles. Orange: an ankle base and a removable ankle side for each '
                             'leg; the base sits on the servo horn and takes the lower link with its servo from above, the side slides '
                             'on along the shaft and two M2 x 8 hold it. Black: a new sleeve for each leg, 10.4 mm bore, that turns '
                             'freely on the link instead of being pressed. Yellow: two new feet that slide onto the base by hand and are '
                             'held by the toe M2 x 6. Nothing in the ankle is spread or pressed any more. The feet keep the old sole, so '
                             'the hot-glue molds (printed black on 2026-10-19) fit them.')
# Shawn 2026-10-19 night: the Yellow plate carries three pairs of feet, one to fit and two spare for sole experiments.
# V1.23 (withdrawn) keeps the two-feet wording it was issued with.
INTRO_BY_VERSION['V1.22'] = _V122_INTRO_TWO_FEET.replace(
    'Yellow: two new feet that slide onto the base by hand and are held by the toe M2 x 6.',
    'Yellow: three pairs of new feet that slide onto the base by hand and are held by the toe M2 x 6. One pair goes on '
    'the robot; the other two are spares for sole experiments, since a foot comes off with its one toe screw.').replace(
    ' The feet keep the old sole, so the hot-glue molds (printed black on 2026-10-19) fit them.', '')
assert INTRO_BY_VERSION['V1.22'] != _V122_INTRO_TWO_FEET
RETIRED_LEAD_BY_VERSION['V1.22'] = ('Take each ankle apart once, with the ankle-and-foot module off the knee: toe screw out and the foot rocked off '
                                    '(hold the orange bracket, not the leg or the servo; the foot may crack), then the four M2 x 4 output screws, '
                                    'the two M2 x 10 case screws and the M2.6 x 8 rear centre with its washer. Pull the link off the bracket evenly '
                                    'and lift the servo out. Keep every screw and the washer; only the printed parts below are replaced.')
RETIRED_HEADING_BY_VERSION['V1.22'] = 'Replace these'
INCREMENTAL_NAMES_BY_VERSION['V1.22'] = dict(
    ankle_base_left='Left ankle base', ankle_base_right='Right ankle base', ankle_cheek_left='Left ankle side', ankle_cheek_right='Right ankle side',
    ankle_sleeve_left='Left ankle sleeve', ankle_sleeve_right='Right ankle sleeve',
    foot_left_slipfit='Left foot, slip fit', foot_right_slipfit='Right foot, slip fit')
INCREMENTAL_NOTES_BY_VERSION['V1.22'] = dict(
    ankle_base_left='With the left ankle side, replaces the left ankle bracket. Screws to the servo horn with the four M2 x 4 as before and carries the foot block. With the side off, the lower link with its servo and sleeve sits straight down into it; nothing is spread.',
    ankle_base_right='With the right ankle side, replaces the right ankle bracket. Same as the left base, mirrored.',
    ankle_cheek_left='The removable side of the left ankle, on the inner face (towards the other leg). Slide it along the shaft, away from the centre line, onto the sleeve until its two tabs meet the two posts of the base, then drive two M2 x 8 from above, hand snug (they cut their own thread). The foot, fitted afterwards, holds it in; take the foot off before opening it.',
    ankle_cheek_right='The removable side of the right ankle. Same as the left side, mirrored.',
    ankle_sleeve_left='Replaces the left ankle sleeve. Bore 10.4 mm: it slides onto the 10 mm boss of the lower link by hand and turns freely. Put it on the link before the link goes into the base.',
    ankle_sleeve_right='Replaces the right ankle sleeve. Same as the left sleeve.',
    foot_left_slipfit='Replaces the left foot. The socket for the ankle block is 0.2 mm wider on every side and the two snap hooks are gone, so the foot slides straight up onto the base and side by hand. Then drive the M2 x 6 from above through the toe of the base into the foot. If it is still tight, sand the socket walls of the foot; never press it on. Prints on its sole, as before.',
    foot_right_slipfit='Replaces the right foot. Same slip fit and the same M2 x 6 at the toe. Prints on its sole, as before.')

# V1.23: V1.22 was never printed, so its eight ankle parts travel here with the reworked hot-glue molds on the Black plate
# (Shawn 2026-10-19, IMG_7040: the V1.21 cavity floors had irregular one-layer islands and the third depth pin of both
# molds broke off). release-V1.23/retired/ holds the V1.21 mold meshes, regenerated byte-identical to the V1.21 release.
RETIRED_INCREMENTAL['V1.23'] = RETIRED_INCREMENTAL['V1.22'] + [
    ('Left hot-glue mold (V1.21 print)', 'Black', HERE / 'release-V1.23' / 'retired' / 'hotglue_mold_left-V1.21.stl',
     'The cavity floor has irregular one-layer islands that would print into the sole, and its thin depth pins break off.', 'Left hot-glue mold, flat floor'),
    ('Right hot-glue mold (V1.21 print)', 'Black', HERE / 'release-V1.23' / 'retired' / 'hotglue_mold_right-V1.21.stl',
     'Same islands and pins as the left mold.', 'Right hot-glue mold, flat floor'),
]
INTRO_BY_VERSION['V1.23'] = (_V122_INTRO_TWO_FEET.replace('V1.22 is three plates and reworks', 'V1.23 is three plates. It reworks')
                             .replace('so the hot-glue molds (printed black on 2026-10-19) fit them.',
                                      'so the hot-glue molds fit them. The Black plate also carries two new hot-glue molds: the cavity '
                                      'floor is one flat plane and the depth pins are gone; the foot stops on the mold rim all round. '
                                      'Print this instead of V1.22, which was never printed.'))
RETIRED_LEAD_BY_VERSION['V1.23'] = RETIRED_LEAD_BY_VERSION['V1.22'] + ' Throw the two V1.21 molds away once the new ones are printed.'
RETIRED_HEADING_BY_VERSION['V1.23'] = 'Replace these'
INCREMENTAL_NAMES_BY_VERSION['V1.23'] = dict(INCREMENTAL_NAMES_BY_VERSION['V1.22'],
                                             hotglue_mold_left='Left hot-glue mold, flat floor', hotglue_mold_right='Right hot-glue mold, flat floor')
INCREMENTAL_NOTES_BY_VERSION['V1.23'] = dict(
    INCREMENTAL_NOTES_BY_VERSION['V1.22'],
    hotglue_mold_left='Replaces the V1.21 left mold (the L on the heel strip). The floor under the flat of the foot is one plane 1.0 mm below it, so the sole comes out flat. No pins: press the foot down between the four tabs until its curved edge sits on the rim of the cavity; the four pencil lines at the tab tops show it is down. Glue that does not fit leaves through the eight vents. Prints cavity up, no support, no brim.',
    hotglue_mold_right='Replaces the V1.21 right mold (the R). Same as the left mold, mirrored.')

# V1.24: the two-half ankle (Shawn 2026-10-20: the V1.22 base and side look fragile, need careful support removal, and the
# two pairs of screw posts catch the servo wire; he never fitted the two M2 x 8 and the ankle worked). Each ankle is the stock
# bracket cut in half at mid shaft (print/ankle-halves-20261020/make_halves.py), held by the foot. The V1.22 black sleeves
# and yellow feet stay. release-V1.24/retired/ holds the V1.22 base and side meshes.
RETIRED_INCREMENTAL['V1.24'] = [
    ('Left ankle base (V1.22 print)', 'Orange', HERE / 'release-V1.24' / 'retired' / 'ankle_base_left-V1.22.stl',
     'Its two screw posts are thin, catch the servo wire and need careful support removal.', 'Left ankle outer half'),
    ('Right ankle base (V1.22 print)', 'Orange', HERE / 'release-V1.24' / 'retired' / 'ankle_base_right-V1.22.stl',
     'Same posts as the left base.', 'Right ankle outer half'),
    ('Left ankle side (V1.22 print)', 'Orange', HERE / 'release-V1.24' / 'retired' / 'ankle_cheek_left-V1.22.stl',
     'Held by two M2 x 8 on the posts; small tabs that break easily.', 'Left ankle inner half'),
    ('Right ankle side (V1.22 print)', 'Orange', HERE / 'release-V1.24' / 'retired' / 'ankle_cheek_right-V1.22.stl',
     'Same as the left side.', 'Right ankle inner half'),
]
INTRO_BY_VERSION['V1.24'] = ('V1.24 is one orange plate: each ankle is the stock bracket cut in half in the middle. The outer half screws to '
                             'the servo horn with the four M2 x 4; the inner half slides along the shaft onto the black sleeve. The foot '
                             'holds both: its socket wraps the two halves, and the toe M2 x 6 sits on the line where they meet and holds '
                             'both down. No posts and no M2 x 8. The V1.22 black sleeves and yellow slip-fit feet stay.')
RETIRED_LEAD_BY_VERSION['V1.24'] = ('On each leg, with the ankle-and-foot module off the knee: toe screw out and the foot slid down, the two M2 x 8 '
                                    'out of the side (they are not used again) and the side slid off towards the centre line, then the four '
                                    'M2 x 4 output screws. Lift the link with its servo and sleeve out of the base. Keep the sleeve, the feet '
                                    'and the other screws.')
RETIRED_HEADING_BY_VERSION['V1.24'] = 'Replace these'
INCREMENTAL_NAMES_BY_VERSION['V1.24'] = dict(ankle_outer_left='Left ankle outer half', ankle_outer_right='Right ankle outer half',
                                             ankle_inner_left='Left ankle inner half', ankle_inner_right='Right ankle inner half')
INCREMENTAL_NOTES_BY_VERSION['V1.24'] = dict(
    ankle_outer_left='The outer half of the left ankle: the plate on the servo horn and half of the foot block. Screws to the horn with the four M2 x 4 as before; the lower link with its servo and sleeve sits straight down into it. After printing: cut the thin brim strip out of the small notch on the end face that stood on the bed; on an Elegoo print also pull any support tips out of the four screw counterbores so the screw heads sit flat.',
    ankle_outer_right='The outer half of the right ankle. Same as the left, mirrored.',
    ankle_inner_left='The inner half of the left ankle, on the face towards the other leg: the plate with the sleeve pocket and the other half of the foot block. Slide it along the shaft, away from the centre line, onto the sleeve until it meets the outer half; then slide the foot on and drive the toe M2 x 6. It prints on its heel corner with the round sleeve pocket free of support (the pocket has a pointed top for that); break the support off under the foot block.',
    ankle_inner_right='The inner half of the right ankle. Same as the left, mirrored.')

# V1.25: the V1.24 plate again with round sleeve bores (Shawn 2026-10-20 on the printed V1.24: the pointed top of the inner
# half's sleeve pocket is not wanted; keep the bore round and let support stand in it). The inner halves now stand on their
# toe end like the outer halves, so the support touches the heel side of the bore, never the side that carries the weight.
# Every half gets an 8 mm brim (one V1.24 outer half came off the bed with the 4 mm brim). release-V1.25/retired/ holds the
# V1.24 inner-half meshes; the V1.24 outer halves are the same part as V1.25's.
RETIRED_INCREMENTAL['V1.25'] = [
    ('Left ankle inner half (V1.24 print)', 'Orange', HERE / 'release-V1.25' / 'retired' / 'ankle_inner_left-V1.24.stl',
     'Its sleeve pocket has a pointed top instead of a round bore.', 'Left ankle inner half'),
    ('Right ankle inner half (V1.24 print)', 'Orange', HERE / 'release-V1.25' / 'retired' / 'ankle_inner_right-V1.24.stl',
     'Same pointed pocket as the left.', 'Right ankle inner half'),
]
INTRO_BY_VERSION['V1.25'] = ('V1.25 is the V1.24 orange plate again with a round sleeve bore in both inner halves. Support stands inside '
                             'the bore while it prints; it sits on the heel side of the bore, away from the side that carries the '
                             'robot. The outer halves are the same as in V1.24; a good printed V1.24 outer half can be used instead '
                             'of a new one. Every half has a wider brim (8 mm) so the tall parts stay on the bed.')
RETIRED_LEAD_BY_VERSION['V1.25'] = ('If a V1.24 inner half is already fitted: foot off (toe screw out, foot slid down), then slide the inner '
                                    'half off along the shaft towards the centre line. Keep the sleeve, the foot and the screw.')
RETIRED_HEADING_BY_VERSION['V1.25'] = 'Replace these'
INCREMENTAL_NAMES_BY_VERSION['V1.25'] = dict(INCREMENTAL_NAMES_BY_VERSION['V1.24'])
INCREMENTAL_NOTES_BY_VERSION['V1.25'] = dict(
    INCREMENTAL_NOTES_BY_VERSION['V1.24'],
    ankle_outer_left=INCREMENTAL_NOTES_BY_VERSION['V1.24']['ankle_outer_left'] + ' Peel the 8 mm brim off all round.',
    ankle_inner_left='The inner half of the left ankle, on the face towards the other leg: the plate with the round sleeve bore and the other half of the foot block. Slide it along the shaft, away from the centre line, onto the sleeve until it meets the outer half; then slide the foot on and drive the toe M2 x 6. It prints standing on its toe end with support inside the bore: break the support out, then scrape the bore and the flat lip face inside it smooth until the black sleeve turns freely in it. Peel the 8 mm brim off and cut the thin brim strip out of the small notch on the end face that stood on the bed; on an Elegoo print also pick the support tips out of the toe screw countersink.')

# V1.27: the right lower-leg link (stock community-32, black) reprinted unchanged; Shawn 2026-10-22 found the printed one bent.
RETIRED_INCREMENTAL['V1.27'] = [
    ('Right lower-leg link (10/1 print)', 'Black', HERE.parents[1] / 'build-pack-20260913' / 'assembly' / 'print-parts' / 'community-32.stl',
     'It is bent.', 'Right lower-leg link'),
]
INTRO_BY_VERSION['V1.27'] = ('V1.27 is one black part: the right lower-leg link, the link between the right knee servo and the right '
                             'ankle servo, printed again unchanged because the printed one is bent.')
RETIRED_LEAD_BY_VERSION['V1.27'] = 'Swap it with the new link on the same servo horns and screws.'
RETIRED_HEADING_BY_VERSION['V1.27'] = 'Replace this'
INCREMENTAL_NAMES_BY_VERSION['V1.27'] = dict(lower_right='Right lower-leg link')
INCREMENTAL_NOTES_BY_VERSION['V1.27'] = dict(
    lower_right='The link between the right knee servo and the right ankle servo, the same part as the 10/1 print. It prints flat with support; break the support off before fitting.')

# V1.31: the battery backpack frame with a wider DFR1202 slot (2026-10-23): the board did not go into the V1.20 frame.
RETIRED_INCREMENTAL['V1.31'] = [
    ('V1.20 battery backpack frame', 'Orange', HERE / 'release-V1.31' / 'retired' / 'battery_backpack_frame-V1.20.stl',
     'The 5 V board does not go between its clip arms.', 'Frame with the wider board slot'),
]
INTRO_BY_VERSION['V1.31'] = ('V1.31 is one orange part: the battery backpack frame again, with a wider slot for the DFR1202 5 V board. '
                             'The clip arms stand 0.5 mm off each board edge and no longer touch the ribs behind the board, so they '
                             'bend and the two lips click over the board edge. Everything else is the V1.20 frame; the cap stays.')
RETIRED_LEAD_BY_VERSION['V1.31'] = 'Move the switch, battery and cap over to the new frame.'
RETIRED_HEADING_BY_VERSION['V1.31'] = 'Replace this'
INCREMENTAL_NAMES_BY_VERSION['V1.31'] = dict(battery_backpack_frame='Battery backpack frame (wider board slot)')
INCREMENTAL_NOTES_BY_VERSION['V1.31'] = dict(
    battery_backpack_frame=('Prints rim down on tree support, as V1.20. Clear the support from the two clip arms on each side of the board '
                            'slot and check each arm springs out a little under a fingertip. Push the board in power-pad edge down, '
                            'components towards you, until the lips click over its edges.'))

# V1.29: the A7Z roof saddle (D-022, 2026-10-22): the board leaves the head after the closed-head soak and rides on the torso
# roof behind the neck, fan in the lid. Nothing printed is replaced; the V1.17 A7Z head clip stays fitted but unused.
RETIRED_INCREMENTAL['V1.29'] = []
INTRO_BY_VERSION['V1.29'] = ('V1.29 is one white plate with two new parts: the saddle body and its lid for the Radxa Cubie A7Z, which moves out '
                             'of the head onto the torso roof behind the neck (it overheated inside the closed head). The body screws down '
                             'through the two roof screws of the shells (M2 x 10 instead of M2 x 6); the board sits on four posts (M2 x 4); '
                             'the 30 mm fan sits in the lid pocket; the lid takes two M2 x 6 from the sides. Nothing printed is replaced.')
RETIRED_HEADING_BY_VERSION['V1.29'] = 'Nothing to throw away'
RETIRED_LEAD_BY_VERSION['V1.29'] = 'Every printed part stays; the A7Z head clip is left in the cap, unused.'
INCREMENTAL_NAMES_BY_VERSION['V1.29'] = dict(saddle_body='A7Z saddle body', saddle_lid='A7Z saddle lid')
INCREMENTAL_NOTES_BY_VERSION['V1.29'] = dict(
    saddle_body=('The box on the torso roof behind the neck. It prints upright on tree support over its whole curved floor: break the '
                 'support off the underside, then clear the two roof-screw holes in the floor and the slot at the foot of the front wall. '
                 'The curved floor sits on the shell dome; the two roof screws (M2 x 10) go down through it into the rear pack.'),
    saddle_lid=('The lid with the fan pocket and the exhaust grille. It prints upside down on its flat top; the fan clips into the bars, '
                'the two side screws (M2 x 6) hold it on the body.'))
# V1.30: the U20CAM USB camera on the face and the dia 11 left-rear head exit (D-023, 2026-10-22/23). Four reprints replace
# four printed parts, kept as spares; the V1.9/V1.17 wire clips were never fitted.
RETIRED_INCREMENTAL['V1.30'] = [
    ('V1.17 face panel (A7Z)', 'White', HERE / 'face-a7z' / 'face_panel_a7z.stl',
     'Its camera bosses and eye opening fit the Radxa CSI camera, which left with the A7Z.', 'Face panel for the U20 USB camera'),
    ('V1.8 eye trim', 'Black', HERE / 'world' / 'eye_trim-v18.stl',
     'Its dia 14.4 bore is too small for the U20 lens ring.', 'Eye trim with the dia 16.2 bore'),
    ('V1.6 jaw support', 'Black', Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/printing/15-COMPLETE-INCREMENTAL-20261009/black-source-print/jaw_support_original-print.stl'),
     'Its left-rear corner closes the head exit to a 6 mm gap.', 'Jaw support with the 11 mm exit'),
    ('V1.8 lower head shell', 'Yellow', HERE / 'world' / 'head_bottom_v18.stl',
     'Its floor closes the head exit to a 6 mm gap; the camera cable does not pass.', 'Lower head shell with the 11 mm exit'),
]
INTRO_BY_VERSION['V1.30'] = ('V1.30 is three plates with eight parts. Six are for the U20 USB camera. The face panel and eye trim take the camera and its '
                             'larger lens; the tall bosses hold the board 13 mm behind the face so the lens ends just behind the trim. The jaw '
                             'support and the lower head shell open the wire exit at the left rear of the head to 11 mm, so the camera cable '
                             'leaves the head in one piece with the other head wires. The left-rear jaw-support screw moves 12 mm back, behind '
                             'the jaw servo. A printed two-piece clamp holds the wires in the exit: one half is part of the jaw support, the '
                             'other is a small separate part that snaps on, printed in two sizes. It also carries the package that was not '
                             'printed yet: the A7Z saddle body and lid (V1.29, white; the body now has the wider front notch for the '
                             'right-angle USB-C plug).')
RETIRED_HEADING_BY_VERSION['V1.30'] = 'Keep these as spares'
RETIRED_LEAD_BY_VERSION['V1.30'] = ('The four parts these prints replace. Keep them in case a new part does not fit. The four wire clips from V1.9 and '
                                    'V1.17 were never fitted and are not needed.')
INCREMENTAL_NAMES_BY_VERSION['V1.30'] = dict(face_panel='Face panel (U20 camera)', eye_trim='Eye trim (U20 camera)',
                                             jaw_support='Jaw support, exit + clamp', head_bottom='Lower head shell (11 mm exit)',
                                             exit_clamp_loose_a='Exit clamp, loose half A', exit_clamp_loose_b='Exit clamp half B (tighter)',
                                             saddle_body='A7Z saddle body', saddle_lid='A7Z saddle lid')
INCREMENTAL_NOTES_BY_VERSION['V1.30'] = dict(
    face_panel=('Prints face down, no support. The camera board screws onto the ends of the four 13 mm bosses behind the eye with four M2 x 6.'),
    eye_trim=('Prints as V1.8. Its bore now passes the U20 lens ring; the two side tabs are gone, the top key pair stays.'),
    jaw_support=('Prints top face down, as V1.6. The curved wall inside the 11 mm exit at the left-rear corner is the fixed half of the '
                 'wire clamp: clear any support from its two narrow slots, one at each end behind a thin lip. The left-rear screw '
                 '(M2.6 x 6) now goes in behind the jaw servo.'),
    exit_clamp_loose_a=('Prints upside down on its flat top, no support. A curved strip with a tongue at each end that slides down into the '
                        'two slots of the fixed half and clicks in. Fit this one first.'),
    exit_clamp_loose_b=('The same strip with a 0.4 mm thicker wall, for a bundle that slides through A. Keep it as the spare.'),
    head_bottom=('Prints floor down, as V1.8, on tree support. Clear the support from the 11 mm exit in the floor and from the new screw '
                 'boss behind the jaw servo.'),
    saddle_body=INCREMENTAL_NOTES_BY_VERSION['V1.29']['saddle_body'][:-1] + '. From V1.29; the front notch is now wider for the right-angle USB-C plug.',
    saddle_lid=INCREMENTAL_NOTES_BY_VERSION['V1.29']['saddle_lid'] + ' From V1.29, unchanged.')

# V1.32: ears and mouth speaker (D-025, 2026-10-23): two INMP441 microphones in the cap side walls, the speaker in a printed box
# behind the camera that sounds through six floor ports; the still unprinted V1.30 White parts ride along.
RETIRED_INCREMENTAL['V1.32'] = [
    ('V1.17 head cap (A7Z)', 'White', HERE / 'a7z-head' / 'head_cap_a7z-world.stl',
     'It has the roof speaker collar and no ears.', 'Head cap with two ears'),
    ('V1.30 lower head shell', 'Yellow', HERE / 'neck-exit-20261023' / 'head_bottom_exit.stl',
     'It has no speaker ports in the floor. Instead of reprinting, it can be drilled with the paper template.', 'Lower head shell with six ports'),
    ('V1.9 speaker retainer', 'Orange', HERE / 'ext-v19' / 'speaker_retainer_v19-world.stl',
     'The speaker leaves the cap roof for the mouth speaker box.', 'Mouth speaker box'),
]
INTRO_BY_VERSION['V1.32'] = ('V1.32 is two plates. The new head cap has two ears: a small sound hole on each side wall just behind the face, '
                             'with a ring inside that holds a round INMP441 microphone. The speaker moves out of the cap roof into a small '
                             'white box that stands on the head floor behind the camera; its flat duct runs under the camera to six holes '
                             'in the floor over the lower jaw, so the duck sounds through its open beak. The yellow lower head shell has those '
                             'six holes; the printed V1.30 shell can be drilled instead with the paper template '
                             '(ears-mouth-20261023/drill-template/drill-template.pdf), and then the yellow plate is not needed. The white plate '
                             'also carries the V1.30 white parts that were not printed yet: the U20 face panel and the A7Z saddle body and lid.')
RETIRED_HEADING_BY_VERSION['V1.32'] = 'Keep these as spares'
RETIRED_LEAD_BY_VERSION['V1.32'] = ('The parts these prints replace. Keep the cap and the shell in case a new part does not fit; the speaker '
                                    'retainer and its two screws are no longer used.')
INCREMENTAL_NAMES_BY_VERSION['V1.32'] = dict(head_cap='Head cap with two ears', speaker_box='Mouth speaker box',
                                             head_bottom='Lower head shell (six ports)', face_panel='Face panel (U20 camera)',
                                             saddle_body='A7Z saddle body', saddle_lid='A7Z saddle lid')
INCREMENTAL_NOTES_BY_VERSION['V1.32'] = dict(
    head_cap=('Prints roof down on tree support with a 4 mm brim, as the V1.17 cap. Clear the support from the two ear rings on the side '
              'walls and push a needle through each small sound hole from outside so it is open.'),
    speaker_box=('Prints standing on its bottom, no support, no brim. The flat duct and the chamber top print as bridges: do not poke into '
                 'the duct. The speaker slides down between the two rails behind the window.'),
    head_bottom=('Prints floor down, as V1.30, on tree support. Push a 2.5 mm drill through each of the six floor holes by hand to clear them.'),
    face_panel=INCREMENTAL_NOTES_BY_VERSION['V1.30']['face_panel'] + ' From V1.30, unchanged.',
    saddle_body=INCREMENTAL_NOTES_BY_VERSION['V1.30']['saddle_body'],
    saddle_lid=INCREMENTAL_NOTES_BY_VERSION['V1.30']['saddle_lid'])

# V1.33: mouth floor (D-026, 2026-10-24): the speaker in a pocket in the yellow floor, the amplifier on rails beside it, the XIAO at
# the roof centre, a long-round head exit, an optional third microphone seat in the cap back wall. Supersedes the unprinted V1.32.
RETIRED_INCREMENTAL['V1.33'] = [
    ('V1.17 head cap (A7Z)', 'White', HERE / 'a7z-head' / 'head_cap_a7z-world.stl',
     'It has the roof speaker collar and no ears.', 'Head cap with ears, no amplifier posts'),
    ('V1.30 lower head shell', 'Yellow', HERE / 'neck-exit-20261023' / 'head_bottom_exit.stl',
     'It has a round 11 mm exit and no speaker pocket.', 'Lower head shell with speaker pocket'),
    ('V1.30 jaw support', 'Black', HERE / 'world' / 'jaw_support-v132.stl',
     'Its exit is round; the new lower shell needs the long-round one.', 'Jaw support with long-round exit'),
]
INTRO_BY_VERSION['V1.33'] = ('V1.33 is three plates and replaces V1.32, which was never printed (its speaker box is dropped). The speaker '
                             'lies face down in a shallow pocket in the floor of the yellow lower head shell, over twelve small holes above '
                             'the lower jaw; the amplifier stands beside it between two low rails. The head exit at the left rear becomes a '
                             'long-round slot 11 x 17 mm in both the yellow shell and the black jaw support, so the wires pass easily. The '
                             'white cap has two ears, no amplifier posts, the XIAO touch board in the middle of its roof and a third, optional '
                             'microphone seat on its back wall. The white plate also carries the V1.30 white parts not printed yet: the U20 '
                             'face panel and the A7Z saddle body and lid. The yellow shell can be printed on the club H2S (its own file).')
RETIRED_HEADING_BY_VERSION['V1.33'] = 'Keep these as spares'
RETIRED_LEAD_BY_VERSION['V1.33'] = 'The parts these prints replace. Keep them in case a new part does not fit.'
INCREMENTAL_NAMES_BY_VERSION['V1.33'] = dict(head_cap='Head cap with ears, no amplifier posts', head_bottom='Lower head shell with speaker pocket',
                                             jaw_support='Jaw support with long-round exit', face_panel='Face panel (U20 camera)',
                                             saddle_body='A7Z saddle body', saddle_lid='A7Z saddle lid')
INCREMENTAL_NOTES_BY_VERSION['V1.33'] = dict(
    head_cap=('Prints roof down on tree support with a 4 mm brim, as the V1.17 cap. Clear the support from the two ear rings and push a '
              'needle through the three small sound holes (two sides and the back) from outside so they are open.'),
    head_bottom=('Prints floor down on tree support. Push a 2.5 mm drill through each of the twelve floor holes by hand to clear them, and '
                 'clear the long-round exit and the two amplifier rails.'),
    jaw_support=('Prints as the V1.30 jaw support. Clear the long-round exit; the two loose clamp halves from V1.30 still fit it.'),
    face_panel=INCREMENTAL_NOTES_BY_VERSION['V1.32']['face_panel'],
    saddle_body=INCREMENTAL_NOTES_BY_VERSION['V1.32']['saddle_body'],
    saddle_lid=INCREMENTAL_NOTES_BY_VERSION['V1.32']['saddle_lid'])

# V1.34: sole press molds (2026-10-24): tools for gluing the bike inner tube sole onto the slip-fit feet with E6000; each foot
# sits in its mold on the glued tube and a lid screws down on four posts until the glue cures. Nothing printed is replaced.
RETIRED_INCREMENTAL['V1.34'] = []
INTRO_BY_VERSION['V1.34'] = ('V1.34 is one plate of tools: a press mold and a lid for each foot, to glue the inner tube sole on. Take the foot '
                             'off the robot, glue the tube to its bottom, set it in its mold (raised L or R at the heel end) and screw the '
                             'lid down with four M2 x 10 until it sits on the posts. Leave it two days, then trim the tube at the glue line. '
                             'Nothing printed is replaced.')
RETIRED_HEADING_BY_VERSION['V1.34'] = 'Nothing to throw away'
RETIRED_LEAD_BY_VERSION['V1.34'] = 'These are tools; every printed part stays.'
INCREMENTAL_NAMES_BY_VERSION['V1.34'] = dict(press_mold_left='Left sole press mold', press_mold_right='Right sole press mold',
                                             press_lid_left='Left press lid', press_lid_right='Right press lid')
_mold_note = ('Prints cavity up without support, 0.12 mm layers with ironed tops. The four posts take M2 x 10 self-tapping screws '
              'in 1.6 mm pilots; run each screw in once before the first use.')
_lid_note = ('Prints flat top down without support. Its underside fits only the foot of the same side; the screws go through the four '
             'corner holes into the mold posts.')
INCREMENTAL_NOTES_BY_VERSION['V1.34'] = dict(press_mold_left=_mold_note, press_mold_right=_mold_note,
                                             press_lid_left=_lid_note, press_lid_right=_lid_note)


# V1.35: A7Z saddle V3 (D-028, 2026-10-25): the board turned round so its USB-C and HDMI sockets face the rear wall, the header at the
# front under an open strip, the Radxa 6530B heatsink on the board, board + heatsink screwed from below to four bosses of the saddle
# floor, the unit taped to the shell roofs, the lid a cover that touches nothing. Two parts (body, lid); the V2 tray of the afternoon
# release was never printed and is gone. Orange is the interim colour (white PLA out). Replaces the V1.29 saddle body and lid printed on
# the V1.33 white plate.
RETIRED_INCREMENTAL['V1.35'] = [
    ('V1.29 A7Z saddle body', 'White', HERE / 'a7z-saddle' / 'build' / 'retired-v129' / 'saddle_body-v129.stl',
     'Its board faced the neck (USB-C sockets at the front) and it screwed to the shell roof; the new one has the sockets at the rear, carries the board on four floor bosses and is taped on.', 'A7Z saddle V3 body'),
    ('V1.29 A7Z saddle lid', 'White', HERE / 'a7z-saddle' / 'build' / 'retired-v129' / 'saddle_lid-v129.stl',
     'It has a pocket for a 30 mm fan that was never bought; the new lid is a cover over the Radxa 6530B heatsink that touches nothing.', 'A7Z saddle V3 lid'),
]
INTRO_BY_VERSION['V1.35'] = ('V1.35 is one orange plate with two parts: the A7Z saddle V3 body and lid. The board is turned round so its two USB-C '
                             'sockets and the micro HDMI face the back of the robot through one window in the rear wall, and the 40-pin header '
                             'sits at the front under an open strip with no lid over the wires. The Radxa 6530B heatsink (65 x 30 mm with its '
                             'own blower fan) sits on the board; on the bench the board lies on four bosses that rise from the saddle floor and '
                             'four M2 x 6 from under the floor screw board and heatsink to the saddle, so the three are one unit. That unit is '
                             'taped onto the torso roof with 3M 0.5 mm foam tape after the two roof screws are in; no screw holds the saddle. '
                             'The lid is a cover over the heatsink end only and touches nothing hot. The Wi-Fi antenna goes on the inside of the '
                             'front wall. Orange is the interim colour while the club is out of white; print it white later if you like.')
RETIRED_HEADING_BY_VERSION['V1.35'] = 'Keep these as spares'
RETIRED_LEAD_BY_VERSION['V1.35'] = 'The V1.29 saddle body and lid from the V1.33 white plate; their board orientation is wrong, so they are not fitted.'
INCREMENTAL_NAMES_BY_VERSION['V1.35'] = dict(saddle_body='A7Z saddle V3 body', saddle_lid='A7Z saddle V3 lid')
INCREMENTAL_NOTES_BY_VERSION['V1.35'] = dict(
    saddle_body=('Prints open side up on tree support under its domed floor, as the V1.29 body. Clear the support from the floor underside, the '
                 'rear port window, the channel bulge on the left wall, the exhaust slots and the floor opening; the four board-screw pockets '
                 'in the floor underside and the holes through the four floor bosses must be open, the floor underside smooth along its left, '
                 'right and rear edges where the foam tape goes, and the two side holes for the lid screws open.'),
    saddle_lid=('Prints upside down, plate on the bed, without support. The grille slots over the fan must be open; only the lip and the two '
                'screw bosses stand up from the plate, nothing else on its underside.'))


# V1.36: the lower head shell of D-026 addendum 2 (2026-10-25): speaker pocket (racetrack) and its twelve holes 4.5 mm forward so
# the lower jaw covers every hole, no amplifier rails. Replaces the printed V1.33 shell.
RETIRED_INCREMENTAL['V1.36'] = [
    ('V1.33 lower head shell', 'Yellow', HERE / 'release-V1.36' / 'run-inputs' / 'head_bottom-v133-world.stl',
     'Its front row of sound holes is partly off the lower jaw and it has two amplifier rails; it still works.', 'Lower head shell, pocket forward, no rails'),
]
INTRO_BY_VERSION['V1.36'] = ('V1.36 is one yellow plate: the lower head shell again. The speaker pocket now has round ends like the speaker '
                             'and sits 4.5 mm further forward, right behind the slot for the face, so the lower jaw covers all twelve sound '
                             'holes. The two amplifier rails are gone: tape the amplifier on the flat floor where it fits. Everything else, '
                             'the exit slot included, is the V1.33 shell.')
RETIRED_HEADING_BY_VERSION['V1.36'] = 'Keep this as a spare'
RETIRED_LEAD_BY_VERSION['V1.36'] = 'The V1.33 lower head shell. It still works if the new one does not fit.'
INCREMENTAL_NAMES_BY_VERSION['V1.36'] = dict(head_bottom='Lower head shell, pocket forward, no rails')
INCREMENTAL_NOTES_BY_VERSION['V1.36'] = dict(
    head_bottom=('Prints floor down on tree support, as the V1.33 shell. Push a 2.5 mm drill through each of the twelve floor holes by hand, '
                 'scrape the pocket floor clean and clear the long-round exit. The thin wall of floor between the pocket and the face slot '
                 'is about 1.4 mm: do not pry against it.'))

# V1.37: the capped jaw ring of D-033 (2026-10-29), held on the right jaw boss by one M2 x 8. Replaces the V1.6 mouth sliding ring.
RETIRED_INCREMENTAL['V1.37'] = [
    ('V1.6 mouth sliding ring', 'Black', HERE.parents[1] / 'build-pack-20260913/redesign-20260913/workflow-review-20261009/central-cad/fusion-C-meshes/mouth_sliding_ring.stl',
     'Nothing held it on the boss and it fell off.', 'Capped jaw ring'),
]
INTRO_BY_VERSION['V1.37'] = ('V1.37 is one black plate with two capped jaw rings, one to fit and one spare. The ring is a small cup that '
                             'goes on the boss inside the right jaw arm, open side towards the arm, and one M2 × 8 from outside the arm '
                             'holds it there. Before fitting it, cut the boss back 2 mm and drill its centre hole to 2.5 (guide chapter 8, jaw step).')
RETIRED_HEADING_BY_VERSION['V1.37'] = 'No longer used'
RETIRED_LEAD_BY_VERSION['V1.37'] = 'The V1.6 mouth sliding ring with its thin flange.'
INCREMENTAL_NAMES_BY_VERSION['V1.37'] = dict(jaw_ring_capped='Capped jaw ring')
INCREMENTAL_NOTES_BY_VERSION['V1.37'] = dict(
    jaw_ring_capped=('Prints closed end down with a 5 mm brim, no support; peel the brim off. Clean the plate first: the rings are small, and the first plate without a brim came off. The centre hole is the M2 pilot: do not drill it. '
                     'Bore 10.5 slides over the boss; outer dia 14 turns in the seat.'))

# V1.38: the box cap of D-034 (2026-10-29): its four screw columns reach the boards. Replaces the printed V1.20 box cap.
RETIRED_INCREMENTAL['V1.38'] = [
    ('Box cap (V1.20 print)', 'Orange', HERE / 'release-V1.38' / 'retired' / 'rear_lid-V1.20.stl',
     'Its screw floors stopped short of the boards, so tightening pulled them off. Keep its four M2 x 10.', 'Box cap, columns on the boards'),
]
INTRO_BY_VERSION['V1.38'] = ('V1.38 is one orange plate with the rear converter box cap. Its four screw columns now run forward until they '
                             'sit on the boards, so the screws press each column onto a board instead of pulling its floor across a gap. '
                             'The cap edge stops about 0.3 mm short of the frame rim on purpose. Same four M2 × 10; the frame stays.')
RETIRED_HEADING_BY_VERSION['V1.38'] = 'No longer used'
RETIRED_LEAD_BY_VERSION['V1.38'] = 'The V1.20 box cap, whose screw floors broke off.'
INCREMENTAL_NAMES_BY_VERSION['V1.38'] = dict(rear_lid='Box cap, columns on the boards')
INCREMENTAL_NOTES_BY_VERSION['V1.38'] = dict(
    rear_lid=('Replaces the V1.20 box cap. Same outside and the same four M2 × 10 through the round holes in its back. Each column '
              'is longer and ends on a board: the low two on the 5991, the top two on the 7 V converter. Tighten until each column '
              'sits firmly and stop; a hairline gap stays at the cap edge. Prints on its flat back face with tree support under the '
              'rounded edges, as before.'))

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
    nret = len(RETIRED_INCREMENTAL[version])
    replaced = (f'and {nret} printed part{"s" if nret != 1 else ""} they replace' if nret else 'and they replace no printed part')
    body = [f'<header><h1>MicroDuck prints {version}</h1><p>{len(m["parts"])} parts to print, {replaced}. '
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
    if not nret:
        body.append('</section>')
        args.out.write_text(page_html(version, body))
        print(json.dumps({'out': str(args.out), 'bytes': args.out.stat().st_size, 'print': len(m['parts']), 'retired': 0}))
        return
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
