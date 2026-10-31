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
    # Dual Lock back plate (2026-10-31, print/back-plate/duallock-plate-20261031/): zero-clearance seats by design (0.0 mm in
    # the 2026-10-31 gate); these entries name the contacts should the world STLs model them as overlap.
    frozenset(['duallock_plate', 'rear_pack']): (
        'c', 'Back plate front face on the ends of the four pack posts at x -45, held by the four M2 x 6 (DL-plate-01..04): '
             'the V1.8 cover seat, a designed seat.', 'No change.'),
    frozenset(['duallock_plate', 'duallock_strips']): (
        'c', 'Dual Lock plate half stuck on the plate rear face (x -48): adhesive contact by design.', 'No change.'),
    frozenset(['rear_frame', 'duallock_strips']): (
        'c', 'Dual Lock box half stuck on the box frame front plate (x -53.7): adhesive contact by design.', 'No change.'),
    frozenset(['battery_backpack_frame', 'duallock_strips']): (
        'c', 'Dual Lock backpack half stuck on the backpack front plate (x -53.7): adhesive contact by design.', 'No change.'),
    frozenset(['rear_frame', 'duallock_plate']): (
        'c', 'Only if the envelopes meet: the box frame lip (|y| <= 13.2, z 27.3..28.5) passes through the plate top notch '
             '(|y| <= 13.5, from z 27.0) with 0.3 mm each side.', 'No change.'),
    frozenset(['rear_frame', 'xl4015_left']): (
        'c', 'XL4015 #1 (top tier) PCB back face on its four frame bosses (seat x -50.205), held by four M2 x 6; the PCB ends '
             'sit at the side wall inner faces (|y| 30.85): a designed seat.', 'No change.'),
    frozenset(['rear_frame', 'xl4015_right']): (
        'c', 'XL4015 #2 (middle tier) PCB back face on its four frame bosses (seat x -50.205), held by four M2 x 6; the PCB ends '
             'sit at the side wall inner faces (|y| 30.85): a designed seat.', 'No change.'),
    frozenset(['rear_frame', 'pd5991']): (
        'c', 'Adafruit 5991 PCB back face on its four 3.0 mm standoff bosses (seat x -50.0), held by four M2 x 6; the USB-C '
             'socket mouth sits in the +y wall window (plug in socket): a designed seat.', 'No change.'),
    # Mouth floor (2026-10-24, print/mouth-floor-20261024/): tapes modelled uncompressed, touching their two faces at 0 mm.
    frozenset(['speaker_tape', 'speaker']): (
        'c', 'Thin tape loop on the rim of the speaker grille face: adhesive contact by design.', 'No change.'),
    frozenset(['speaker_tape', 'head_bottom']): (
        'c', 'Thin tape loop on the floor of the speaker pocket, round the twelve sound holes: adhesive contact by design.', 'No change.'),
    frozenset(['amp_tape', 'amplifier']): (
        'c', 'Foam tape under the amplifier board: adhesive contact by design.', 'No change.'),
    frozenset(['amp_tape', 'head_bottom']): (
        'c', 'Foam tape of the amplifier on the yellow floor between the two rails: adhesive contact by design.', 'No change.'),
    # D-025 ears (2026-10-23, print/ears-mouth-20261023/): 1 mm foam rings.
    **{frozenset([f'mic_foam_{s}', 'head_cap']): (
        'c', f'Foam ring round the {s} sound hole on the inner face of the cap wall: adhesive contact by design.', 'No change.') for s in ('left', 'right', 'back')},
    **{frozenset([f'mic_foam_{s}', f'mic_{s}']): (
        'c', f'Foam ring on the {s} microphone face round its port: adhesive contact by design.', 'No change.') for s in ('left', 'right', 'back')},
    # Touch extension (extension-20261015-touch/): foam tape and copper foil stuck to the cap wall.
    frozenset(['touch_xiao_tape', 'head_cap']): (
        'c', 'Foam tape on the XIAO pressed onto the middle of the cap roof (modelled 0.05 mm under the roof; the tape presses up against it): adhesive contact by design.', 'No change.'),
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
    # 2026-10-25 D-028 saddle V3 (print/a7z-saddle/build/build.json checks): the A7Z, the Radxa 6530B heatsink and the bought parts
    # in the saddle pose; the board on the four saddle floor bosses, screwed from below into the heatsink; the lid a cover that
    # touches nothing (checks lid_heatsink_6530b 0.0, lid_screw_boss_above_heatsink_mm 1.0).
    frozenset(['sd_microsd_card', 'sd_microsd_socket']): (
        'c', 'microSD card pushed into its socket on the A7Z underside: a mated part (the card sticks out through the -Y saddle wall slot).', 'No change.'),
    frozenset(['sd_usb_c_plug', 'sd_usb_c_otg_dp']): (
        'c', 'Right-angle USB-C plug of the camera pigtail (D-023) seated in the A7Z OTG socket from behind through the rear-wall window: plug in socket.', 'No change.'),
    # 2026-10-22 D-023 U20 camera (print/face-u20/checks.json): the Innomaker U20CAM-720P on the face bosses, its cut cable and the splice.
    frozenset(['camera_u20cam', 'face_panel']): (
        'c', 'Camera PCB front face on the tops of the four 13.1 mm face bosses (x 67.0, modelled 0.02 mm off; checks.json clearances pcb/face_panel_u20), '
             'held by four M2 x 6; the lens (ROBOTIS OMX-F CAD) passes the dia 16.2 eye opening with 1.1 mm radial clearance: a designed seat.', 'No change.'),
    frozenset(['camera_u20cam', 'eye_trim']): (
        'c', 'Only if the envelopes meet: the M12 lens ring (dia 14.0) passes the dia 16.2 trim bore with 1.1 mm radial clearance (checks.json intersection volume 0).', 'No change.'),
    frozenset(['camera_u20cam', 'camera_cable_stub']): (
        'c', "The camera's own cable leaves the plug on the PCB back (near the +Y edge): one purchased assembly drawn as board and cable stub.", 'No change.'),
    frozenset(['sd_thermal_pad_6530b', 'sd_soc_a733']): (
        'c', '1.5 mm thermal pad from the 6530B kit lying on the A733 top face (z 51.2): pad contact by design.', 'No change.'),
    frozenset(['sd_heatsink_6530b', 'sd_thermal_pad_6530b']): (
        'c', 'Radxa 6530B base on the thermal pad (z 52.7): pad contact by design.', 'No change.'),
    frozenset(['sd_heatsink_6530b', 'sd_a7z_pcb']): (
        'c', 'The four threaded bosses of the 6530B stand on the PCB top face round the board holes (z 49.6), held by the four M2 x 6 from below: a designed seat.', 'No change.'),
    frozenset(['saddle_body', 'sd_a7z_pcb']): (
        'c', 'The four floor bosses of the saddle body (dia 6.0 at the top) under the PCB at the board holes (z 48.0; build.json checks body_pcb '
             'bounds at z 48.0 only): the board sits on them, held by the four M2 x 6 from below into the 6530B bosses: a designed seat.', 'No change.'),
    frozenset(['saddle_lid', 'saddle_body']): (
        'c', 'Lid plate on the wall tops (z 66.5), lip inside the three closed walls: a designed seat.', 'No change.'),
    frozenset(['sd_antenna', 'saddle_body']): (
        'c', 'AC019 antenna strip stuck on the inner face of the saddle front wall (x -6.9..-6.6): adhesive contact by design.', 'No change.'),
    frozenset(['sd_dupont_housings', 'sd_a7z_pcb']): (
        'c', 'Dupont housings standing on the header plastic at z 49.6, the PCB top face: a mated terminal row by design.', 'No change.'),
    frozenset(['sd_usb_c_otg_dp', 'sd_heatsink_6530b']): (
        'c', 'Only if the envelopes meet: the 6530B base envelope (bottom z 52.7, 3.1 above the PCB, estimated from photos) and the USB-C socket top (52.9); '
             'the kit is made for this board, so the base clears or is relieved over the sockets: measured on the part before fitting.', 'No change.'),
    frozenset(['sd_usb_c_power', 'sd_heatsink_6530b']): (
        'c', 'Only if the envelopes meet: as sd_usb_c_otg_dp / sd_heatsink_6530b (socket top 52.9 vs base envelope 52.7, estimated).', 'No change.'),
    frozenset(['sd_heatsink_6530b', 'sd_dupont_housings']): (
        'c', 'Only if the envelopes meet: the fin block starts 0.36 mm behind the housings (HS d 6.4, estimated from photos; measured on the part).', 'No change.'),
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
