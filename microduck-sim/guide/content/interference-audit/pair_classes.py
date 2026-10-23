"""Final-pose part pairs that are intended contact, shared by build_findings.py (report) and run_gate.py (print gate).

pair_class(a, b) -> (class, explanation, fix); class 'c' is an intended contact, '?' is unclassified. A pair deeper than
0.1 mm that is not class 'c' fails the print gate. Add a pair here only with the reason it is a designed contact.
"""
from __future__ import annotations

PAIR_TEXT = {
    frozenset(['head_bottom', 'head_cap']): (
        'c', 'Head seam lap joint: lower shell rim lip and cap rim (eight 0.2 mm horizontal slabs at z 111.11-111.31 and 112.61-112.81 '
        'along both sides, front corners and rear). The upstream Onshape assembly (assembly_fk.py top/bottom head shell) carries the '
        'same 0.2 mm overlap, so it is a zero-clearance seat modelled as overlap, not a placement error. Printed parts cannot '
        'interpenetrate; the cap will sit up to 0.2 mm higher at the seam (inference).',
        'No change. If a flush seam is required, lower the cap rim seat 0.2 mm in the next head_cap revision (reprint head_cap).'),
    frozenset(['imu_board', 'imu_sh4_receiving']): (
        'c', 'The SH4 (STEMMA QT) plug envelope sits inside the IMU board socket envelope: a mated connector.', 'No change.'),
    # 2026-10-22: the knee/ankle small-ring press-fit entries left with the separate sleeve (now printed on the lower link).
    # Rear converter box, layout F (2026-10-14, V1.11, print/back-plate/layout-F/). Zero-clearance seats by design; these
    # entries name the contacts should the world STLs model them as overlap.
    frozenset(['rear_frame', 'rear_pack']): (
        'c', 'Rear box frame on the pack: the frame front plate is the V1.8 cover plate and seats on the ends of the two pack '
             'cover posts and the pack rim at x -45 (cover seat, layout-F/checks.json fit at rest: frame to pack 0 by design); '
             'its lip runs inside the converter channel over the pack side walls.',
        'No change.'),
    frozenset(['rear_frame', 'xl4015_left']): (
        'c', 'XL4015 #1 (top tier) PCB back face on its four frame bosses (seat x -50.205), held by four M2 x 6; the PCB ends '
             'sit at the side wall inner faces (|y| 30.85): a designed seat.', 'No change.'),
    frozenset(['rear_frame', 'xl4015_right']): (
        'c', 'XL4015 #2 (middle tier) PCB back face on its four frame bosses (seat x -50.205), held by four M2 x 6; the PCB ends '
             'sit at the side wall inner faces (|y| 30.85): a designed seat.', 'No change.'),
    frozenset(['rear_frame', 'pd5991']): (
        'c', 'Adafruit 5991 PCB back face on its four 3.0 mm standoff bosses (seat x -50.0), held by four M2 x 6; the USB-C '
             'socket mouth sits in the +y wall window (plug in socket): a designed seat.', 'No change.'),
    # Speaker tape (2026-10-14): a closed loop of foam double-sided tape (two halves) modelled 0.6 mm thick (1 mm tape compressed) on the collar's
    # 0.6 mm lip ring at the speaker edge; touching the speaker face and the lip at 0 mm is the design (0 mm3 on the world STLs).
    frozenset(['speaker_tape', 'speaker']): (
        'c', 'Tape loop on the edge of the speaker grille face: adhesive contact by design.', 'No change.'),
    frozenset(['speaker_tape', 'head_cap']): (
        'c', 'Tape loop on the collar lip ring of the cap: compressed foam contact by design.', 'No change.'),
    # Touch extension (extension-20261015-touch/): foam tape and copper foil stuck to the cap wall.
    frozenset(['touch_xiao_tape', 'head_cap']): (
        'c', 'Foam tape under the XIAO pressed onto the inner left wall of the cap (1 mm tape at 0.8 mm, up to 0.2 mm more into the curve): adhesive contact by design.', 'No change.'),
    frozenset(['touch_xiao_tape', 'touch_xiao']): (
        'c', 'Foam tape on the flat back of the XIAO: adhesive contact by design.', 'No change.'),
    **{frozenset([f'touch_pad_{p}', 'head_cap']): (
        'c', 'Copper foil pad stuck to the inner face of the cap wall: adhesive contact by design.', 'No change.') for p in ('l1', 'r1', 'l2', 'r2', 'm')},
    frozenset(['rear_frame', 'rear_lid']): (
        'c', 'Cap on the frame rim at x -59.1 (cap seam): two top tongues under the frame top wall with teeth in its slots, and two ears on the frame bosses at (y -23.8, z -17.4) and (y +23.8, z -33.6), held by two M2 x 6: a designed seat.', 'No change.'),
    # Battery backpack (2026-10-15, D-010, print/back-plate/battery-backpack-20261015/build/build.json boughtPartOverlapMm3):
    # bought parts in their clipped state. The backpack never meets the rear converter box (guide-data 'alternates').
    frozenset(['battery_backpack_frame', 'bp_switch']): (
        'c', 'REV-31-1387 snap wings in their 3 mm floor panel: the wings are modelled relaxed (REV STEP), so they cross the panel '
             'hole edges at |y| 13.75..15.39, z -24.85..-22.51 (31.9 mm3, 1.0 mm deep); on the robot they spring in as the body passes '
             'and grip the panel: a designed snap fit.', 'No change.'),
    frozenset(['battery_backpack_frame', 'bp_dfr1202']): (
        'c', 'DFR1202 long edges in the four flexure clip lips at |y| 12.75..13, z 12.8..21.7 and 30.3..39.2 (7.8 mm3, 0.25 mm deep): '
             'the lips are modelled unflexed and grip the board edges: a designed clip.', 'No change.'),
    # Radxa Cubie A7Z head (2026-10-15, print/a7z-head/, print/face-a7z/): purchased parts in their mated state.
    frozenset(['head_pi_a7z_microsd_card', 'head_pi_a7z_microsd_socket']): (
        'c', 'microSD card pushed into its socket on the A7Z underside: a mated part (the card sticks out about 2 mm past the -Y end).', 'No change.'),
    frozenset(['head_pi_a7z_csi_connector', 'camera_ribbon']): (
        'c', 'Camera FPC end inserted in the A7Z underside flip-lock camera connector with the latch closed: a mated connector.', 'No change.'),
    frozenset(['camera_board', 'camera_ribbon']): (
        'c', 'One camera FPC drawn in two halves: camera_ribbon (A7Z end, a7z-head/build_a7z_head.py ribbon()) meets the ribbon '
             'tail modelled with the Radxa Camera 13M 214 (face-a7z/camera_13m214.stl) at x 70-70.5 along the left wall.', 'No change.'),
    frozenset(['head_pi_a7z_ipex_socket', 'antenna_ipex']): (
        'c', 'Antenna IPEX (U.FL) plug snapped onto the A7Z antenna socket: a mated connector.', 'No change.'),
    frozenset(['antenna_coax', 'antenna_ipex']): (
        'c', 'The 1.13 mm antenna coax enters its own IPEX plug: one purchased cable assembly (AC019) drawn as plug and cable.', 'No change.'),
    # 2026-10-22 D-022 roof saddle (print/a7z-saddle/build/build.json checks): the A7Z and its bought parts in the saddle pose.
    frozenset(['sd_microsd_card', 'sd_microsd_socket']): (
        'c', 'microSD card pushed into its socket on the A7Z underside: a mated part (the card sticks out through the +Y saddle wall slot).', 'No change.'),
    frozenset(['sd_usb_c_plug', 'sd_usb_c_otg_dp']): (
        'c', 'Right-angle USB-C plug of the camera pigtail (D-023) seated in the A7Z OTG socket through the saddle front-wall notch: plug in socket.', 'No change.'),
    # 2026-10-22 D-023 U20 camera (print/face-u20/checks.json): the Innomaker U20CAM-720P on the face bosses, its cut cable and the splice.
    frozenset(['camera_u20cam', 'face_panel']): (
        'c', 'Camera PCB front face on the tops of the four face bosses (x 72.4, checks.json clearances pcb/face_panel_u20 0.0), held by four M2 x 6; '
             'the lens holder stands in the dia 16.2 eye opening with 0.55 mm radial clearance: a designed seat.', 'No change.'),
    frozenset(['camera_u20cam', 'eye_trim']): (
        'c', 'Only if the envelopes meet: the M12 lens ring (dia 15.1) passes the dia 16.2 trim bore with 0.55 mm radial clearance (checks.json intersection volume 0).', 'No change.'),
    frozenset(['camera_u20cam', 'camera_cable_stub']): (
        'c', "The camera's own cable leaves the connector on the PCB back (+Y edge): one purchased assembly drawn as board and cable stub.", 'No change.'),
    frozenset(['sd_thermal_pad', 'sd_soc_a733']): (
        'c', '0.5 mm thermal pad lying on the A733 top face (z 50.2): pad contact by design.', 'No change.'),
    frozenset(['sd_heatsink', 'sd_thermal_pad']): (
        'c', '15 x 15 x 5 copper heatsink on the thermal pad (z 50.7): pad contact by design.', 'No change.'),
    frozenset(['sd_antenna', 'saddle_body']): (
        'c', 'AC019 antenna strip stuck on the inner face of the saddle rear wall (x -43.4..-43.1): adhesive contact by design.', 'No change.'),
    frozenset(['sd_fan', 'saddle_lid']): (
        'c', '30 mm fan in the lid pocket: the four 0.6 mm snap lips under the fan corners and the rear stop hold it against the lid plate '
             '(build.json lid_fan 0.405 mm3 at z 72.39-72.4): a designed snap fit.', 'No change.'),
    frozenset(['sd_dupont_housings', 'sd_a7z_pcb']): (
        'c', 'Dupont housings standing on the header plastic at z 48.6, the PCB top face: a mated terminal row by design.', 'No change.'),
    frozenset(['sd_dupont_housings', 'sd_fan']): (
        'c', 'Only if the envelopes meet: the housings end at z 63.1 and the fan starts at z 64.4 (1.3 mm gap, build.json gap_fan_to_dupont_mm).', 'No change.'),
}


def pair_class(a, b):
    k = frozenset([a, b])
    if k in PAIR_TEXT:
        return PAIR_TEXT[k]
    if 'screw' in a or 'screw' in b:
        part = b if 'screw' in a else a
        return ('c', f'Screw thread envelope (0.2 mm radial) in its pilot hole in {part}: thread engagement, modelled as overlap.', 'No change.')
    if 'header_pin' in a + b and 'receiving' in a + b:
        return ('c', 'Header pin inside its GPIO receiving-contact envelope: a mated terminal (0.64 mm is the contact grip).', 'No change.')
    return ('?', 'unclassified', '')
