"""Wiring drawing for the OpenRB-150 and power steps (rendered in the guide by ~/code/wiring-kit).

openrb_wiring(cut) returns a step's `wiring` field: a wiring-kit Bench plus marker labels. One drawing serves the
UART step (chapter 2), the supply-board bench step (chapter 3) and the power step (chapter 5): the two UART wires into
J12, the 15 V feed from the Adafruit 5991 screw terminal into XL4015 #2 IN and on to XL4015 #1 IN, the 7 V pair from
XL4015 #1 OUT into J4, and the two Pi jumper chains from XL4015 #2 OUT (PROJECT-CONTEXT.json
current_build.servo_rail_7v_20261014, adopted 2026-10-14; 2026-10-15 current_build.servo_shutdown_52_20261015: 15 V from
USB-C PD (only the 15V switch ON; 9 V browned out on the first walk command), 7 V servo rail set to 7.40 V with every
servo on Shutdown 52, 5.0 V Pi rail, no soldering on power wires).

Layout: the rear converter box as seen from behind with its lid off (layout F, approved 2026-10-14,
print/back-plate/layout-F/): XL4015 #1 (7 V) in the top tier and #2 (5 V) in the middle tier, both lying flat with the
long side across the robot, IN block on the right (-Y) and OUT block on the left (+Y), components towards the viewer
(the CAD agent mirrored layout F to the real board's handedness at 16:23, wires_F.json sha256 01d757a8); the 5991 in the
narrow bottom tier with its USB-C socket to the left (+Y window) and its screw terminal to the right (-Y window). The
XL4015 photo (OUT left, IN right, trimmers along the lower edge, as taken) is used as it is: that is how the real board
sits in the box, and the + screw of each block is the lower one. The 5991 photo is turned 270 degrees (USB-C left,
terminal right, + the lower screw). The tier gaps are drawn wider than in the box. The OpenRB-150 (left,
USB-C up as in its photo) and the Pi (below it, turned 180 degrees) are drawn beside the box; in the robot the OpenRB
stands in the pack in front of the box and the 7 V pair and the Pi lead reach it over the top of the box and down
through the wire notch at the front edge of its top wall. Every box wire leaves its window straight out and runs outside
the wall; the drawing shows only the connections.

Sources (checked 2026-10-12 unless noted):
- Photo: robotis.us product image https://robotis.us/cdn/shop/files/1__44988.1741649644.1280.1280.png, cropped copy
  in openrb_top.png (same file as bringup/parts/photos/openrb_150_top.png, copyright ROBOTIS, private reference use).
- UART: the Pi uses Serial2 on the 4-pad J12 row (schematic: pin 1 GND, 2 +3V3, 3 SERIAL_RX, 4 SERIAL_TX; variant.h
  PIN_SERIAL2_TX 28, PIN_SERIAL2_RX 29). The silkscreen reads "Tx Rx V G" from left to right with USB-C at the top; G
  is the square pad 1. Two jumper wires are soldered into pads 3 and 4 (Shawn's decision 2026-10-13: Dupont plugs on
  the side header do not fit behind the converter in the pack, and a cover window was rejected).
- Terminal block J4 (- left, + right) and JP1 are the photo fractions in bringup/parts/parts.json.
- Adafruit 5991 (HUSB238 USB-C PD board): photo pd5991_board.jpg (made by make_photos.py from the shop photo
  https://cdn-shop.adafruit.com/original/5991-05.jpg, copyright Adafruit Industries, private reference use). Pinouts page
  https://learn.adafruit.com/adafruit-usb-type-c-power-delivery-switchable-breakout/pinouts: 1x6 DIP switch, one switch
  per printed voltage ("flip the switch to ON next to the board silk label for the voltage you need"); the silk reads
  5V, 9V, 12V, 15V, 18V, 20V from the top with switch numbers 6 to 1 on the other side, so 15V is switch 3
  (bringup/parts/parts.json usb_pd_5991 claims, schematic: switch 3 puts 14K on VSET = 15 V in HUSB238 datasheet
  Table 5). Exactly one switch ON: with 5V and 9V both ON the board negotiated 5 V (Shawn, 2026-10-15, 5.167 V); the
  switch is read only at plug-in. Screw terminal + left, - right (printed below the block). Pin fractions are positions in
  pd5991_board.jpg (460 x 655 px): switch 6 at (0.772, 0.458), switch 1 (20V) at (0.772, 0.678), so switch 3 (15V) at
  (0.772, 0.590); terminal + at (0.444, 0.865), - at (0.614, 0.865), USB-C at (0.500, 0.036).
- HUSB238 datasheet (https://cdn-learn.adafruit.com/assets/assets/000/125/150/original/husb238_datasheet_full.pdf,
  read 2026-10-14), "RDO determination": the chip takes the highest source PDO with voltage <= the VSET voltage and
  current >= the ISET current, else the next lower one (the 003DD part on the 5991 has the "Next PDO" mismatch action).
  ISet closed requests 1.25 A, so a 15 V / 3 A charger offer qualifies; ISet cut requests 3.25 A, which a 3 A offer
  does not meet. Keep ISet closed.
- XL4015 DC converter (ROBOTIS OMX-AI kit module; 2026-10-14): photo xl4015_board.jpg is a crop of Shawn's own photo
  bringup/power12v/img/shawn_smps2dxl_xl4015.jpg (1000 x 420 px, board upside down: OUT block left, IN block right).
  "IN+" and "OUT+" are printed beside the lower screw of each block (bringup/power12v/build_power12v.py). Two blue
  W103 multi-turn trimmers, an 8-pin current-sense amplifier and three LEDs G, B, R: the constant-voltage /
  constant-current module type. Board 61.7 x 26.2 mm (print/candidates/back-box-20261014/parts/README.md).
"""
from __future__ import annotations

import base64
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHOTO = HERE / 'openrb_top.png'
PHOTO_PX = (204, 488)
# The board is 25.4 mm wide (guide mesh openrb-board-upright.stl). Drawn 2.2 times larger than the far-end tags,
# as for the DFR1202, so the 2.0 mm J12 pads and their markers stay readable at phone width.
SCALE = 2.2
BOARD_W = round(25.4 * SCALE, 2)
BOARD_H = round(BOARD_W * PHOTO_PX[1] / PHOTO_PX[0], 2)
# Pi Zero W photo (Adafruit 3708, Zero WH top view, 810 x 400 px) drawn at 1.3 times its 65 mm width.
PI_PHOTO = HERE / 'pi_zero_w_top.jpg'
PI_PX = (810, 400)
PI_W = round(65.0 * 1.3, 2)
PI_H = round(PI_W * PI_PX[1] / PI_PX[0], 2)
# Adafruit 5991 photo, drawn 1.7 times its 20.3 mm width (as the retired receiver drawing did).
PD_PHOTO = HERE / 'pd5991_board.jpg'
PD_PX = (460, 655)
PD_W = 34.0
PD_H = round(PD_W * PD_PX[1] / PD_PX[0], 2)
# XL4015 photo (crop of Shawn's photo, 1000 x 420 px) drawn at its 61.7 mm board length.
XL_PHOTO = HERE / 'xl4015_board.jpg'
XL_PX = (1000, 420)
XL_W = 61.7
XL_H = round(XL_W * XL_PX[1] / XL_PX[0], 2)


def _photo_module() -> dict:
    uri = 'data:image/png;base64,' + base64.b64encode(PHOTO.read_bytes()).decode('ascii')
    w, h = PHOTO_PX
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{BOARD_W}mm" height="{BOARD_H}mm" viewBox="0 0 {w} {h}">'
           f'<image width="{w}" height="{h}" href="{uri}"/></svg>')

    def at(fx, fy):
        return round(fx * BOARD_W, 2), round(fy * BOARD_H, 2)

    pins = []
    # J12 pads, left to right as printed "Tx Rx V G" (photo fractions measured on openrb_top.png, 2.0 mm pitch).
    for pid, fx, fy, role, label, name, note in (
            ('Tx', 0.386, 0.721, 'signal', 'Tx', 'J12 pad 4, SERIAL_TX (OpenRB sends)',
             'Marker 2. White wire: goes to Pi pin 10 (the Pi receives here). Printed "Tx" above the pad.'),
            ('Rx', 0.452, 0.721, 'signal', 'Rx', 'J12 pad 3, SERIAL_RX (OpenRB receives)',
             'Marker 1. Green wire: comes from Pi pin 8 (the Pi sends here). Printed "Rx" above the pad.'),
            ('V', 0.521, 0.721, 'nc', 'V', 'J12 pad 2, +3.3 V, leave empty',
             'Printed "V". 3.3 V output of the OpenRB: never connect it to the Pi.'),
            ('G', 0.588, 0.721, 'nc', 'G', 'J12 pad 1, GND (square pad), leave empty',
             'Printed "G", the square pad. It beeps to the terminal block −. Left empty: in the robot the OpenRB and the Pi '
             'already share ground through the converters and the one 5991.')):
        x, y = at(fx, fy)
        p = {'id': pid, 'label': label, 'name': name, 'role': role, 'x': x, 'y': y, 'note': note}
        if role == 'signal':
            p.update(voltage=3.3, maxVoltage=3.6)
        pins.append(p)
    for pid, fx, fy, role, label, name, note in (
            ('JPV', 0.314, 0.781, 'nc', 'VIN', 'JP1, VIN(DXL) side',
             'Jumper cap on this side when the board runs from the terminal block. On laptop USB power it goes on the +5V side.'),
            ('n', 0.451, 0.932, 'ground', '−', 'Terminal block J4 −',
             'Marker 4. 7 V pair black (22 AWG solid) from XL4015 #1 OUT−, alone under the screw. Printed "−" beside the left screw.'),
            ('p', 0.571, 0.932, 'power', '+', 'Terminal block J4 +',
             'Marker 3. 7 V pair red (22 AWG solid) from XL4015 #1 OUT+, alone under the screw. Printed "+" beside the right screw.')):
        x, y = at(fx, fy)
        p = {'id': pid, 'label': label, 'name': name, 'role': role, 'x': x, 'y': y, 'note': note}
        if pid == 'p':
            p.update(voltage=7.4, maxVoltage=12.6)
        pins.append(p)
    return {'id': 'orb', 'title': 'OpenRB-150 (component side, USB-C at the top)',
            'subtitle': 'ROBOTIS OpenRB-150 (902-0183-000)', 'short': 'OpenRB', 'partNumber': '902-0183-000',
            'drawing': {'kind': 'svg', 'svg': svg}, 'width': BOARD_W, 'height': BOARD_H, 'pins': pins}


def _pi_module() -> dict:
    """Pi Zero W photo with all 40 header pins at the photo fractions recorded in bringup/parts/parts.json."""
    import json
    parts = json.loads((HERE.parents[2] / 'bringup/parts/parts.json').read_text())
    parts = parts if isinstance(parts, list) else parts.get('parts', parts)
    rec = next(p for p in parts if p.get('id') == 'pi_zero_w')
    w_px, h_px = PI_PX
    uri = 'data:image/jpeg;base64,' + base64.b64encode(PI_PHOTO.read_bytes()).decode('ascii')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{PI_W}mm" height="{PI_H}mm" viewBox="0 0 {w_px} {h_px}">'
           f'<image width="{w_px}" height="{h_px}" href="{uri}"/></svg>')
    used = {'2': ('power', 'Marker 7. Red Pi jumper chain from XL4015 #2 OUT+ (female end). 5 V only: never 7 V or 15 V.'),
            '6': ('ground', 'Marker 8. Black Pi jumper chain from XL4015 #2 OUT− (female end).'),
            '8': ('signal', 'Marker 5. Green wire: the Pi sends here, to OpenRB J12 pad 3 (printed Rx).'),
            '10': ('signal', 'Marker 6. White wire: the Pi receives here, from OpenRB J12 pad 4 (printed Tx).')}
    pins = []
    for q in rec['pins']:
        n = str(q['pin'])
        role, note = used.get(n, ('nc', 'Not used by this connection.'))
        p = {'id': n, 'label': n, 'name': f'Pi pin {n} ({q["label"]})', 'role': role,
             'x': round(q['x'] * PI_W, 2), 'y': round(q['y'] * PI_H, 2), 'note': note}
        if n == '2':
            p.update(voltage=5, maxVoltage=5.25)
        if role == 'signal':
            p.update(voltage=3.3, maxVoltage=3.6)
        pins.append(p)
    return {'id': 'pi', 'title': 'Raspberry Pi Zero W (turned round: header at the bottom, microSD slot on the right)',
            'subtitle': 'All 40 pins; only 2, 6, 8 and 10 are used here', 'short': 'Pi',
            'drawing': {'kind': 'svg', 'svg': svg}, 'width': PI_W, 'height': PI_H, 'pins': pins}


def _pd_module() -> dict:
    """Adafruit 5991: the screw terminal the 15 V feed starts from, and the one DIP switch that is ON (15V)."""
    w, h = PD_PX
    uri = 'data:image/jpeg;base64,' + base64.b64encode(PD_PHOTO.read_bytes()).decode('ascii')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{PD_W}mm" height="{PD_H}mm" viewBox="0 0 {w} {h}">'
           f'<image width="{w}" height="{h}" href="{uri}"/></svg>')
    pins = []
    for pid, fx, fy, role, label, name, note, volt in (
            ('P', 0.444, 0.865, 'power', '+', 'Screw terminal + (lower screw in this view, printed ⊕ beside it)',
             'Marker 9. 15 V feed red, 22 AWG solid, to XL4015 #2 IN+: strip 6 mm, push under the screw, tighten, tug. One wire per screw.', 15),
            ('N', 0.614, 0.865, 'ground', '−', 'Screw terminal − (upper screw in this view, printed ⊖ beside it)',
             'Marker 10. 15 V feed black, to XL4015 #2 IN−, the same way.', None),
            ('SW15', 0.772, 0.590, 'nc', '15V', 'DIP switch 3, printed 15V',
             'The only slider ON. 5V, 9V and 12V above it and 18V and 20V below it stay OFF: with 5V also ON the board asks for 5 V, and with all six off it asks for the highest voltage (20 V on the Xiaomi 67 W). Not 9V: its 27 W offer browned out the robot on the first walk command (2026-10-15). The board reads the switch only at plug-in: replug after changing it.', None),
            ('USB', 0.500, 0.036, 'nc', 'USB-C', 'USB-C input',
             'The charger cable. Plug it in only for the meter checks in chapter 3 and at first power-up in chapter 10.', None)):
        p = {'id': pid, 'label': label, 'name': name, 'role': role, 'x': round(fx * PD_W, 2), 'y': round(fy * PD_H, 2), 'note': note}
        if volt:
            p.update(voltage=volt, maxVoltage=15.75)
        pins.append(p)
    return {'id': 'pd', 'title': 'Adafruit 5991 USB-C PD board (15 V)', 'short': '5991',
            'subtitle': 'Adafruit 5991 (HUSB238), DigiKey 1528-5991-ND; only the 15V switch ON, ISet left closed', 'partNumber': '5991', 'digikey': '1528-5991-ND',
            'drawing': {'kind': 'svg', 'svg': svg}, 'width': PD_W, 'height': PD_H, 'pins': pins}


def _xl_module(mid: str, volts: float, load: str) -> dict:
    """ROBOTIS kit XL4015 converter. Module frame: Shawn's photo (OUT block left, IN block right, trimmers along the lower
    edge), placed unturned: that is the box seen from behind."""
    w, h = XL_PX
    uri = 'data:image/jpeg;base64,' + base64.b64encode(XL_PHOTO.read_bytes()).decode('ascii')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{XL_W}mm" height="{XL_H}mm" viewBox="0 0 {w} {h}">'
           f'<image width="{w}" height="{h}" href="{uri}"/></svg>')
    n = mid[-1]
    feed = ('from the 5991 + (marker 9), and the red 15 V link on to XL4015 #1 IN+ under the same screw'
            if n == '2' else 'the red 15 V link from XL4015 #2 IN+')
    pins = []
    for pid, fx, fy, role, label, name, note, volt in (
            ('INP', 0.930, 0.507, 'power', 'IN+', 'IN+ screw (lower screw of the IN block in this view, printed IN+)', f'15 V in: {feed}.', 15),
            ('INN', 0.930, 0.333, 'ground', 'IN−', 'IN− screw (upper screw of the IN block in this view)', '15 V return, black, the same way as IN+.', None),
            ('OUTP', 0.063, 0.512, 'power', 'OUT+', 'OUT+ screw (lower screw of the OUT block in this view, printed OUT+)',
             f'{volts:.2f} V out, set with nothing connected (chapter 3), then red to {load}.', volts),
            ('OUTN', 0.063, 0.333, 'ground', 'OUT−', 'OUT− screw (upper screw of the OUT block in this view)', f'Black to {load}.', None)):
        p = {'id': pid, 'label': label, 'name': name, 'role': role, 'x': round(fx * XL_W, 2), 'y': round(fy * XL_H, 2), 'note': note}
        if volt:
            p.update(voltage=volt, maxVoltage=15.75 if pid == 'INP' else (7.45 if volts > 6 else 5.25))
        if pid in ('INP', 'INN') and n == '2':
            p['multi'] = True   # the 5991 feed and the link to XL4015 #1 share each IN screw of #2
        pins.append(p)
    side = 'top' if n == '1' else 'middle'
    return {'id': mid, 'title': f'#{n} {side}: {volts:.2f} V', 'short': f'#{n} {side}: {volts:.2f} V',
            'subtitle': f'ROBOTIS OMX-AI kit DC converter (XL4015), {side} tier of the rear box seen from behind: IN on the right, OUT on the left',
            'drawing': {'kind': 'svg', 'svg': svg}, 'width': XL_W, 'height': XL_H, 'pins': pins}


# Bench placements (mm, y down). XL4015 unturned: 61.7 wide, 25.9 tall; 5991 turned 270 degrees: 48.4 x 34.
# The tier gaps are drawn 18 mm (2.4 mm and 0.5 mm in the box) so each converter's title and the wires fit between them.
BOX_X, BOX_Y, TIER_GAP = 72.0, 8.0, 18.0
BOX_PLACEMENTS = [{'module': 'orb', 'x': 0, 'y': 0},
                  {'module': 'pi', 'x': 16, 'y': 150, 'rotation': 180},
                  {'module': 'xl1', 'x': BOX_X, 'y': BOX_Y},
                  {'module': 'xl2', 'x': BOX_X, 'y': round(BOX_Y + XL_H + TIER_GAP, 2)},
                  {'module': 'pd', 'x': round(BOX_X + (XL_W - PD_H) / 2, 2), 'y': round(BOX_Y + 2 * (XL_H + TIER_GAP), 2), 'rotation': 270}]


def openrb_wiring(cut: dict) -> dict:
    """cut: 'uart' in mm; 'pw-15v', 'pw-15v-link', 'pw-7v', 'pi-lead' as length text (mm or the pending-route note)."""
    uart = cut['uart']
    feed, link, seven, pilead = (cut[k] for k in ('pw-15v', 'pw-15v-link', 'pw-7v', 'pi-lead'))
    wires = [
        ('tx', 'orb.Rx', 'pi.8', 'green', 'uart',
         f'Green jumper wire TX, {uart} mm: OpenRB J12 pad 3, printed Rx (marker 1) → Pi pin 8, GPIO14 TXD (marker 5).',
         'Soldered into its hole in chapter 2; the jumper plug at the other end goes on the Pi in chapter 9.'),
        ('rx', 'orb.Tx', 'pi.10', 'white', 'uart',
         f'White jumper wire RX, {uart} mm: OpenRB J12 pad 4, printed Tx (marker 2) → Pi pin 10, GPIO15 RXD (marker 6).',
         'Soldered into its hole in chapter 2; the jumper plug at the other end goes on the Pi in chapter 9.'),
        ('f15p', 'pd.P', 'xl2.INP', 'red', 'feed',
         f'15 V feed red, 22 AWG solid, {feed}: 5991 terminal + (marker 9) → XL4015 #2 IN+ (marker 15).',
         'Screwed in at both ends in chapter 3. In the box it loops out and back through the right-hand window of the bottom tier and of the middle tier. No solder.'),
        ('f15n', 'pd.N', 'xl2.INN', 'black', 'feed',
         f'15 V feed black, 22 AWG solid, {feed}: 5991 terminal − (marker 10) → XL4015 #2 IN− (marker 16).',
         'Screwed in at both ends in chapter 3, beside the red. No solder.'),
        ('l15p', 'xl2.INP', 'xl1.INP', 'red', 'feed',
         f'15 V link red, 22 AWG solid, {link}: XL4015 #2 IN+ (marker 15, under the same screw as the feed) → XL4015 #1 IN+ (marker 11).',
         'Two solid wires under the #2 IN+ screw. Chapter 3. In the box it loops through the right-hand window of the middle tier and of the top tier.'),
        ('l15n', 'xl2.INN', 'xl1.INN', 'black', 'feed',
         f'15 V link black, 22 AWG solid, {link}: XL4015 #2 IN− (marker 16) → XL4015 #1 IN− (marker 12).',
         'Two solid wires under the #2 IN− screw. Chapter 3.'),
        ('s7p', 'xl1.OUTP', 'orb.p', 'red', 'servo',
         f'7 V pair red, 22 AWG solid, {seven}: XL4015 #1 OUT+ (marker 13) → OpenRB terminal block + (marker 3).',
         'Into J4 in chapter 5, forward along the cover lip, out through the wire notch at the top of the plate, up the box front and over the box top, down the outside of the left (+Y) wall and in through the left-hand window of the top tier; onto XL4015 #1 OUT+ only after the 7.40 V readback in chapter 10. No solder.'),
        ('s7n', 'xl1.OUTN', 'orb.n', 'black', 'servo',
         f'7 V pair black, 22 AWG solid, {seven}: XL4015 #1 OUT− (marker 14) → OpenRB terminal block − (marker 4).',
         'Into J4 in chapter 5, beside the red all the way; onto XL4015 #1 OUT− in chapter 10. No solder.'),
        ('pip', 'xl2.OUTP', 'pi.2', 'red', 'pi',
         f'Red Pi jumper chain (300 mm male-female into 300 mm female-female), {pilead}: XL4015 #2 OUT+ (marker 17) → Pi pin 2, 5 V (marker 7).',
         'Through the pack notch, out through the wire notch at the top of the box plate, over the box top and down the outside of the left (+Y) wall into the left-hand window of the middle tier (chapter 5), running outboard of the coil; male pin cut off, 10 mm stripped, twisted and folded back under the #2 OUT+ screw (chapter 10, after the 5.00 V readback); female end on the Pi (chapter 9).'),
        ('pin', 'xl2.OUTN', 'pi.6', 'black', 'pi',
         f'Black Pi jumper chain (300 mm male-female into 300 mm female-female), {pilead}: XL4015 #2 OUT− (marker 18) → Pi pin 6, GND (marker 8).',
         'The same way under the #2 OUT− screw; female end on the Pi (chapter 9).'),
    ]
    bench = {
        'modules': [_photo_module(), _pi_module(), _pd_module(),
                    _xl_module('xl1', 7.4, 'the OpenRB terminal block J4'), _xl_module('xl2', 5.0, 'Pi pins 2 and 6')],
        # The rear box seen from behind with the lid off: #1 on top and #2 in the middle, flat (unturned, IN on the
        # right), the 5991 below (turned 270 degrees, USB-C left, terminal right). The OpenRB stands
        # to the left (USB-C up), the Pi below it (turned 180 degrees: pins 2 and 6 at the right end of the header, so the
        # Pi lead from the right and the UART pair from the left reach their pins without crossing).
        'placements': BOX_PLACEMENTS,
        'groups': [{'id': 'uart', 'label': 'UART wires, OpenRB J12 ↔ Pi (jumper wire)', 'color': '#00897b'},
                   {'id': 'feed', 'label': '15 V feed, 5991 → XL4015 #2 IN → XL4015 #1 IN (22 AWG solid)', 'color': '#ef6c00'},
                   {'id': 'servo', 'label': '7 V pair, XL4015 #1 OUT → OpenRB J4 (22 AWG solid)', 'color': '#d32f2f'},
                   {'id': 'pi', 'label': 'Pi 5 V lead, XL4015 #2 OUT → Pi pins 2 and 6 (jumper chains)', 'color': '#ad1457'}],
        'wires': [{'id': i, 'from': a, 'to': b, 'color': c, 'group': g, 'label': lab, 'note': note}
                  for i, a, b, c, g, lab, note in wires],
    }
    marker = {'orb.Rx': '1 J12 Rx', 'orb.Tx': '2 J12 Tx', 'orb.p': '3 J4 +', 'orb.n': '4 J4 −',
              'pi.8': '5 pin 8 TXD', 'pi.10': '6 pin 10 RXD', 'pi.2': '7 pin 2 5V', 'pi.6': '8 pin 6 GND',
              'pd.P': '9 5991 + (lower)', 'pd.N': '10 5991 − (upper)',
              'xl1.INP': '11 #1 IN+ (lower)', 'xl1.INN': '12 #1 IN− (upper)', 'xl1.OUTP': '13 #1 OUT+ (lower)', 'xl1.OUTN': '14 #1 OUT− (upper)',
              'xl2.INP': '15 #2 IN+ (lower)', 'xl2.INN': '16 #2 IN− (upper)', 'xl2.OUTP': '17 #2 OUT+ (lower)', 'xl2.OUTN': '18 #2 OUT− (upper)'}
    return {
        'title': 'OpenRB-150, 5991, the two XL4015 and the Pi: every power and UART wire',
        'caption': 'The rear converter box seen from behind with its lid off (layout F): XL4015 #1 (7 V) in the top tier and #2 (5 V) in the '
                   'middle tier, both lying flat with the IN block on the right and the OUT block on the left, components towards you, and '
                   'the 5991 in the narrow bottom tier with its USB-C socket to the left and its screw terminal to the right. On every '
                   'terminal block the + screw is the lower one in this view. The gaps '
                   'between the tiers are drawn wider than in the box. In the box every one of these wires leaves its terminal sideways, '
                   'runs straight out through the window in the side wall beside it and along the outside of the wall; the drawing shows only '
                   'which screw goes to which. The 7 V pair and the Pi lead climb the outside of the left (+Y) wall, cross the box top and drop '
                   'through the wire notch at the front edge of the top wall under the shell lip into the pack; the OpenRB (in the pack, in front of the box) and the Pi (in the head) are drawn '
                   'beside the box. Photos: ROBOTIS (OpenRB-150), Adafruit (5991 and Pi Zero W with header), Shawn (XL4015 from the OMX-AI '
                   'kit). The two UART wires are soldered into J12, the row of four pads printed "Tx Rx V G" above the power jumper: green '
                   'into pad 3 (Rx), white into pad 4 (Tx). The V and G pads stay empty. The 5991 (only its 15V switch ON) feeds 15 V to '
                   'XL4015 #2 IN, and a second pair under the same screws carries it on to XL4015 #1 IN. #1 is set to 7.40 V (the 7 V rail) '
                   'and feeds the OpenRB terminal block J4; #2 is set to 5.00 V and feeds Pi pins 2 and 6. Nothing on the power path is '
                   'soldered. "Open large view" shows the drawing full screen.',
        'pinText': marker,
        'bench': bench,
    }
