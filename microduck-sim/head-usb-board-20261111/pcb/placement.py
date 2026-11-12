"""Part positions on the head USB board: ref -> (x mm, y mm, rotation deg, side). Board 30 x 30, y down, rear face = F.

Free depth behind the rear face (space_check.py depth probe, 2026-11-12): over 30 mm in the top band (y < 13.5),
4 mm under the band on the left half, 9 mm on the right half. So everything that takes a plug (2.54 mm headers,
speaker terminal, both PicoBlade headers) sits in the band; below it only parts up to about 1.3 mm tall.
The 2.54 mm headers lie in rows shoulder to shoulder on a 2.54 mm grid like one multi-row header, so their courtyards
overlap by design (check_drc.py waives connector-to-connector courtyard overlaps only).
"""

P = 2.54
PLACE = {
    # --- band: four rows of 2.54 mm positions, pin 1 at the left. Rows, not columns: fit_check.py found the yaw
    # bracket reaching plug tails below board y 10 when the head rolls, so every plug sits as high as it can.
    "J_EAR_R": (2.0, 1.7, 90, "F"),
    "J_EAR_L": (2.0, 1.7 + P, 90, "F"),
    "J_BACK": (2.0, 1.7 + 2 * P, 90, "F"),
    "J_BACK_SD": (2.0, 1.7 + 3 * P, 90, "F"),
    "J_TOUCH": (2.0 + P, 1.7 + 3 * P, 90, "F"),
    "J_TOUCH_3V3": (2.0, 1.7 + 4 * P, 90, "F"),          # far left: the yaw bracket reaches the right end of row 4 first
    "J_SPK": (15.9, 3.2, 0, "F"),
    # Turned half a turn when the pin order was settled (circuit 5 = 5 V, HANDOFF 2026-11-12): 5 V stays at the left
    # end as routed in draft 2 and the housings keep their place; the lock-window wall now faces the board top.
    "J_UP": (27.6, 2.1, 180, "F"),
    "J_CAM": (27.6, 8.6, 180, "F"),
    # --- microphone and touch passives, band floor
    "R8": (15.0, 9.4, 90, "F"), "R9": (16.2, 9.4, 90, "F"), "C27": (17.4, 9.4, 90, "F"),
    "R10": (18.6, 9.4, 90, "F"), "R11": (19.8, 9.4, 90, "F"),
    "R6": (13.4, 12.3, 0, "F"), "D1": (16.1, 12.3, 0, "F"),
    # --- MCU
    "U2": (7.6, 21.4, 0, "F"),
    "U3": (4.2, 15.2, 0, "F"), "R1": (7.5, 14.5, 0, "F"), "R2": (7.5, 15.65, 0, "F"), "C9": (1.2, 15.2, 90, "F"),
    "TP1": (9.9, 15.3, 0, "F"), "TP2": (12.1, 15.3, 0, "F"),
    "X1": (7.6, 27.7, 0, "F"), "C7": (4.3, 27.9, 0, "F"), "C8": (10.9, 28.8, 0, "F"), "R5": (10.9, 27.6, 0, "F"),
    "R3": (13.5, 17.4, 0, "F"), "R4": (13.5, 18.5, 0, "F"),
    "C10": (2.0, 18.4, 90, "F"), "C11": (2.0, 20.6, 90, "F"), "C12": (2.0, 22.8, 90, "F"), "C13": (2.0, 25.0, 90, "F"),
    "C14": (13.2, 20.5, 90, "F"), "C15": (13.2, 22.7, 90, "F"), "C16": (13.2, 24.9, 90, "F"),
    "C17": (2.5, 26.5, 0, "F"), "C19": (4.5, 26.4, 0, "F"), "C18": (12.8, 26.7, 0, "F"),
    "C20": (2.0, 27.9, 0, "F"), "C21": (2.0, 29.1, 0, "F"),
    "TP3": (13.5, 28.8, 0, "F"), "TP4": (15.7, 28.8, 0, "F"), "TP5": (17.9, 28.8, 0, "F"), "TP6": (20.1, 28.8, 0, "F"),
    "TP7": (22.3, 28.8, 0, "F"),
    # --- hub
    "U1": (18.4, 18.4, 0, "F"),
    "X2": (18.4, 23.7, 0, "F"),
    "C4": (21.8, 16.5, 90, "F"), "C5": (16.4, 14.8, 0, "F"), "C6": (19.2, 14.8, 0, "F"),
    # --- power, lower right
    "U4": (26.0, 26.9, 0, "F"), "C1": (21.4, 25.7, 90, "F"), "C2": (23.0, 25.7, 90, "F"), "C3": (29.0, 26.9, 90, "F"),
    # --- amp, right
    "U5": (26.4, 17.6, 0, "F"),
    "R7": (26.4, 14.4, 0, "F"), "C23": (23.2, 15.0, 90, "F"),
    "C22": (23.3, 18.7, 90, "F"), "C24": (22.7, 22.3, 90, "F"),
    "FB1": (25.7, 20.9, 0, "F"), "FB2": (25.7, 22.6, 0, "F"),
    "C25": (28.5, 20.9, 90, "F"), "C26": (28.5, 23.1, 90, "F"),
}

# The plug rows end at board y 11.2, so the MCU group moves up into the freed strip; the room it leaves along the
# bottom edge is routing space for the crystal and the 1V1 capacitors.
MCU_UP = 0.0
for _ref in ("U2", "U3", "R1", "R2", "C9", "TP1", "TP2", "X1", "C7", "C8", "R5", "R3", "R4", "C10", "C11", "C12",
             "C13", "C14", "C15", "C16", "C17", "C18", "C19", "C20", "C21"):
    _x, _y, _r, _s = PLACE[_ref]
    PLACE[_ref] = (_x, round(_y - MCU_UP, 2), _r, _s)
