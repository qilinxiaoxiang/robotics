#!/usr/bin/env python3
"""Build ../HEAD-USB-BOARD.html: how every part in the head plugs into the head USB board (head-usb-board-20261111).

Nothing about the board is typed here twice. Read at build time:
- connector pins and nets, in pin order:   head-usb-board-20261111/sch/netlist.py
- connector origin (pad 1) and rotation:   head-usb-board-20261111/pcb/placement.py, cross-checked against
                                           pcb/build/pos.csv and the courtyard boxes in pcb/build/footprints.json
- pin count and pitch:                     the footprint names in footprints.json
- silkscreen words (R, L, B, SD.T, 3V, SPK, A7Z, CAM, 5V): the SILK list in pcb/gen_pcb.py
- board picture:                           pcb/build/jlcpcb-placement-preview.jpg (JLCPCB's assembly preview, connectors
                                           drawn in place); pins sit at picture coordinates through JLC_BOX below

What is on the robot now comes from ../../CURRENT-STATE.json (a7z_touch_bus, parts_a7z_extensions, backpack_swap_plugs);
the builder stops if the phrases it relies on are no longer there. Two things are NOT in the state file and come from the
soldering page source (build_a7z_solder.py, steps s1 to s6), as HANDOFF.md also notes ("not yet confirmed on the robot"):
which lead ends are male or female, and the microphone lead colours, which that page only suggests. The page says so
where it matters and never uses a suggested colour as the only way to tell a lead.

Run:  python3 build_head_usb_board.py     then  python3 check_head_usb_board.py
"""
from __future__ import annotations

import ast
import csv
import html
import importlib.util
import json
import math
import re

from PIL import Image, ImageDraw, ImageFont

import a7z_bench as AB
import build_a7z_pages as AP
import build_a7z_solder as SOL
import photos as P
import touch_bench as TB

HERE = AP.HERE
ROOT = HERE.parent.parent
BOARD = ROOT / 'head-usb-board-20261111'
OUT = HERE.parent / 'HEAD-USB-BOARD.html'
BOARD_REF = 'head-usb-board-20261111'


# ---------------------------------------------------------------- sources
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NETLIST = load(BOARD / 'sch' / 'netlist.py', 'hub_netlist')
PLACE = load(BOARD / 'pcb' / 'placement.py', 'hub_placement').PLACE
FOOT_JSON = json.loads((BOARD / 'pcb' / 'build' / 'footprints.json').read_text())
FOOT = {p['ref']: p for p in FOOT_JSON['parts']}
OUTLINE = FOOT_JSON['outline_mm']                       # 30.1: the 30 mm outline plus its 0.1 mm line
EDGE = (OUTLINE[0] - 30.0) / 2                          # footprints.json and the picture start at the line's outer edge
with open(BOARD / 'pcb' / 'build' / 'pos.csv') as fh:
    POS = {r['Ref']: r for r in csv.DictReader(fh)}


def silk_list():
    tree = ast.parse((BOARD / 'pcb' / 'gen_pcb.py').read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'SILK':
            return ast.literal_eval(node.value)
    raise SystemExit('gen_pcb.py: SILK list not found')


SILK = silk_list()
SILK_WORDS = [t for t, *_ in SILK]

# connector -> (description, [net of pin 1, net of pin 2, ...]) straight from the netlist
CONN = {}
for _group in NETLIST.GROUPS.values():
    for _ref, _kind, _value, _pins in _group:
        if _kind.startswith('CONN'):
            _nets = [None] * len(_pins)
            for _key, _net in _pins.items():
                _nets[int(_key.split('_')[0]) - 1] = _net
            CONN[_ref] = (_value, _nets)

STATE = json.loads((ROOT / 'CURRENT-STATE.json').read_text())['facts']


def fact(name) -> str:
    return json.dumps(STATE[name]['value'], ensure_ascii=False)


def need(name, *phrases):
    text = fact(name)
    for ph in phrases:
        if ph not in text:
            raise SystemExit(f'CURRENT-STATE.json {name} no longer says "{ph}": reread it and update this builder')


# Facts this page states about the robot as it is now; each is tied to the words of the state entry.
need('a7z_touch_bus', '29 (PB2, SCL, blue)', '31 (PB3, SDA, green)', '3V3 red pin 17', 'GND black pin 25')
need('parts_a7z_extensions', 'red 5V, white D-, green D+, black GND, shield', 'plug edge UP',
     'head camera = spare U20CAM on the re-pinned short cable', 'Shawn re-pins one end')   # no purchase status on the page: it changes
need('backpack_swap_plugs', 'servo XT30, A7Z MR30', "lower left")
need('a7z_audio_capture', 'All three microphones fitted')

RED, BLK, BLU, GRN, WHT, GREY = '#d7263d', '#1d1d1f', '#1f6fd1', '#1f9d55', '#ffffff', '#90a4ae'
TOUCH_COL = {'3V3': (RED, '红'), 'GND': (BLK, '黑'), 'D5': (BLU, '蓝'), 'D4': (GRN, '绿')}          # a7z_touch_bus
USB_COL = {'5V': (RED, '红'), 'D-': (WHT, '白'), 'D+': (GRN, '绿'), 'GND': (BLK, '黑'), '屏蔽': (BLK, '黑')}  # parts_a7z_extensions
SPK_COL = {'+': (RED, '红'), '−': (BLK, '黑')}                                                     # build_a7z_solder.py s4
MIC_COL = SOL.COL                                                                                  # suggested only (solder page)

# ---------------------------------------------------------------- connector geometry
# Direction of a footprint's pin row in its own frame, pad 1 at the origin (KiCad library convention; the check script
# compares every resulting position with the pads in pcb/build/board.kicad_pcb).
AXIS = {'PinSocket': (0, 1), 'PinHeader': (0, 1), 'Molex_PicoBlade': (1, 0), 'TerminalBlock': (1, 0)}
HOLE = {'PinSocket': '孔', 'PinHeader': '针', 'Molex_PicoBlade': '针', 'TerminalBlock': '孔'}


def family(ref):
    return next(k for k in AXIS if FOOT[ref]['footprint'].startswith(k))


def cells(ref):
    """[(pin number, x mm, y mm, net or None)] in the board frame (x right, y down, seen from the rear)."""
    fp = FOOT[ref]['footprint']
    n = int(re.search(r'_1x(\d+)_', fp).group(1))
    pitch = float(re.search(r'_P([\d.]+)mm', fp).group(1))
    ax = AXIS[family(ref)]
    x0, y0, rot, side = PLACE[ref]
    pos = POS[ref]
    assert side == 'F' and pos['Side'] == 'top', ref
    assert abs(float(pos['PosX']) - x0) < 0.01 and abs(-float(pos['PosY']) - y0) < 0.01 and abs(float(pos['Rot']) - rot) < 0.01, \
        f'{ref}: placement.py and pos.csv disagree'
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    dx, dy = ax[0] * c + ax[1] * s, -ax[0] * s + ax[1] * c       # KiCad turns anticlockwise on a y-down sheet
    nets = CONN[ref][1]
    assert len(nets) <= n, ref
    out = []
    bx0, by0, bx1, by1 = FOOT[ref]['box']
    for k in range(n):
        x, y = x0 + k * pitch * dx, y0 + k * pitch * dy
        assert bx0 - 0.3 <= x + EDGE <= bx1 + 0.3 and by0 - 0.3 <= y + EDGE <= by1 + 0.3, f'{ref} pin {k + 1} outside its courtyard'
        out.append((k + 1, round(x, 3), round(y, 3), nets[k] if k < len(nets) else None))
    return out


CELLS = {ref: cells(ref) for ref in CONN}


def silk_at_row(y):
    hits = [t for t, tx, ty, _ in SILK if abs(ty - y) < 0.1 and t != '5V']
    assert len(hits) == 1, (y, hits)
    return hits[0]


# Rows of 2.54 mm positions share one silkscreen word; a position is named by that word and its place from the left.
ROWS: dict[str, list] = {}
for _ref in CONN:
    if family(_ref) in ('PinSocket', 'PinHeader'):
        for _n, _x, _y, _net in CELLS[_ref]:
            ROWS.setdefault(silk_at_row(_y), []).append((_x, _ref, _n))
for _row in ROWS.values():
    _row.sort()
for _word in ('SPK', 'A7Z', 'CAM'):
    assert _word in SILK_WORDS, _word
assert SILK_WORDS.count('5V') == 2
SILK_OF = {'J_SPK': 'SPK', 'J_UP': 'A7Z', 'J_CAM': 'CAM'}
for _word, _row in ROWS.items():
    for _x, _ref, _n in _row:
        SILK_OF.setdefault(_ref, _word)

USB_REFS = [r for r in CONN if family(r) == 'Molex_PicoBlade']
for _ref in USB_REFS:
    assert 'shield' in CONN[_ref][0] and CONN[_ref][1][0] == 'GND' and CONN[_ref][1][4] == 'VBUS', _ref
    _five = min(CELLS[_ref], key=lambda c: c[1])                 # the 5 V pin is the left end, beside the silk 5V
    assert _five[3] == 'VBUS' and any(t == '5V' and tx < _five[1] and abs(ty - _five[2]) < 1.5 for t, tx, ty, _ in SILK), _ref


def usb_signal(ref, n):
    net = CONN[ref][1][n - 1]
    if n == 1:
        return '屏蔽'
    return {'GND': 'GND', 'VBUS': '5V'}.get(net) or ('D+' if net.endswith('_DP') else 'D-')


def where(ref, n) -> str:
    """Where a position is on the board, in words the builder can follow with the board in hand."""
    fam = family(ref)
    if fam == 'Molex_PicoBlade':
        order = sorted(CELLS[ref], key=lambda c: c[1])
        rank = [c[0] for c in order].index(n) + 1
        return f'{SILK_OF[ref]} 座，从 5V 字样那头数第 {rank} 针'
    if fam == 'TerminalBlock':
        order = sorted(CELLS[ref], key=lambda c: c[1])
        return f'SPK 端子{"左右"[[c[0] for c in order].index(n)]}孔'
    word = SILK_OF[ref]
    row = ROWS[word]
    rank = [(r, k) for _, r, k in row].index((ref, n)) + 1
    if len(row) == 2:
        return f'{word} 座{"左右"[rank - 1]}孔'
    return f'{word} 排左起第 {rank} {HOLE[fam]}'


NET_NAME = {  # net -> (label on the pin, name, role, volts)
    '+3V3': ('3V3', '3.3 V 电源', 'power', 3.3), 'GND': ('GND', '地线', 'ground', None),
    'MIC_SCK': ('SCK', '麦克风位时钟', 'signal', 3.3), 'MIC_WS': ('WS', '麦克风左右时钟', 'signal', 3.3),
    'MIC_SD_EARS': ('SD', '两只耳朵的声音数据', 'signal', 3.3), 'MIC_SD_BACK': ('SD', '后脑麦克风的声音数据', 'signal', 3.3),
    'TOUCH_SCL': ('SCL', '触摸板 I2C 时钟', 'signal', 3.3), 'TOUCH_SDA': ('SDA', '触摸板 I2C 数据', 'signal', 3.3),
    'SPK_P': ('+', '喇叭 +', 'signal', 5), 'SPK_N': ('−', '喇叭 −', 'signal', 5),
    'VBUS': ('5V', 'USB 5 V', 'power', 5),
    'UP_DP': ('D+', 'USB 数据 D+', 'signal', 3.3), 'UP_DM': ('D-', 'USB 数据 D-', 'signal', 3.3),
    'CAM_DP': ('D+', 'USB 数据 D+', 'signal', 3.3), 'CAM_DM': ('D-', 'USB 数据 D-', 'signal', 3.3),
}

# ---------------------------------------------------------------- pictures
JLC = BOARD / 'pcb' / 'build' / 'jlcpcb-placement-preview.jpg'
JLC_BOX = (157, 262, 854, 861)      # the board on the screenshot: left, top and right edges of the green; the bottom is cut
JLC_PX = (JLC_BOX[2] - JLC_BOX[0]) / OUTLINE[0]
BAND_MM = 14.6                      # every connector is in the top band; the benches show this strip


def jlc_px(x, y):
    """Board mm -> pixel on the JLCPCB screenshot."""
    return JLC_BOX[0] + (x + EDGE) * JLC_PX, JLC_BOX[1] + (y + EDGE) * JLC_PX


def font(n):
    return ImageFont.truetype(P.FONT, n)


def board_module() -> dict:
    src = Image.open(JLC).convert('RGB')
    h = round(BAND_MM * JLC_PX)
    im = src.crop((JLC_BOX[0], JLC_BOX[1], JLC_BOX[2], JLC_BOX[1] + h))
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    pins = []
    for ref in CONN:
        usb = ref in USB_REFS
        for n, x, y, net in CELLS[ref]:
            pin = {'id': f'{ref}.{n}', 'net': net, 'x': round(x + EDGE, 3), 'y': round(y + EDGE, 3), 'note': where(ref, n)}
            if net is None:
                pin.update(label='空', name='空着，什么都不插', role='nc')
            else:
                label, name, role, volt = NET_NAME[net]
                if usb and n == 1:
                    label, name = '屏蔽', 'USB 屏蔽线（板上接地）'
                pin.update(label=label, name=name, role=role)
                if volt is not None:
                    pin['voltage'] = volt
            pins.append(pin)
    w = OUTLINE[0]
    return {'id': 'board', 'title': '头部 USB 板', 'short': 'USB 板',
            'subtitle': '从机器人后面看，只画板子上边有插座的一条；板子下边是芯片，不插线',
            'drawing': {'kind': 'svg', 'svg': TB.photo_svg(im, w, BAND_MM)}, 'width': w, 'height': BAND_MM, 'pins': pins}


def overview_figure() -> Image.Image:
    """The JLCPCB preview of the board with a badge per connector carrying its silkscreen word."""
    S = 2
    src = Image.open(JLC).convert('RGB').crop(JLC_BOX)
    src = src.resize((src.width * S, src.height * S), Image.LANCZOS)
    ML, MT, MR = 190, 150, 230
    im = Image.new('RGB', (src.width + ML + MR, src.height + MT), 'white')
    im.paste(src, (ML, MT))
    d = ImageDraw.Draw(im)

    def at(x, y):
        px, py = jlc_px(x, y)
        return ML + (px - JLC_BOX[0]) * S, MT + (py - JLC_BOX[1]) * S

    def centre(ref):
        pts = CELLS[ref]
        return sum(p[1] for p in pts) / len(pts), sum(p[2] for p in pts) / len(pts)

    def end(ref, which):
        return (min if which == 'left' else max)(p[1] for p in CELLS[ref])

    marks = []          # (text, target px, badge centre px)
    for ref in CONN:
        fam, word = family(ref), OVERVIEW_BADGE[ref]
        cx, cy = centre(ref)
        if fam == 'Molex_PicoBlade':
            tx, ty = at(end(ref, 'right') + 1.6, cy)
            marks.append((word, (tx, ty), (im.width - MR / 2, ty)))
        elif fam == 'TerminalBlock':
            tx, ty = at(cx, cy - 2.2)
            marks.append((word, (tx, ty), (tx, MT / 2)))
        elif ref == 'J_TOUCH':
            tx, ty = at(cx, cy + 1.0)
            marks.append((word, (tx, ty), at(cx + 3.6, cy + 4.6)))
        else:
            tx, ty = at(end(ref, 'left') - 1.2, cy)
            marks.append((word, (tx, ty), (ML / 2, ty)))
    for text, (tx, ty), (bx, by) in marks:
        d.line((tx, ty, bx, by), fill='#0d47a1', width=8)
        d.ellipse((tx - 12, ty - 12, tx + 12, ty + 12), fill='#0d47a1')
    for text, (tx, ty), (bx, by) in marks:
        f = font(62 if len(text) < 3 else 56)
        w = max(104, d.textlength(text, font=f) + 44)
        d.rounded_rectangle((bx - w / 2, by - 50, bx + w / 2, by + 50), 50, fill='#0d47a1', outline='white', width=5)
        d.text((bx, by), text, font=f, fill='white', anchor='mm')
    return im


# badge text per connector on the overview: the silkscreen word, split where one word covers two connectors
OVERVIEW_BADGE = {'J_EAR_R': 'R', 'J_EAR_L': 'L', 'J_BACK': 'B', 'J_BACK_SD': 'SD', 'J_TOUCH': 'T', 'J_TOUCH_3V3': '3V',
                  'J_SPK': 'SPK', 'J_UP': 'A7Z', 'J_CAM': 'CAM'}
assert set(OVERVIEW_BADGE) == set(CONN)
assert SILK_OF['J_BACK_SD'] == SILK_OF['J_TOUCH'] == 'SD.T' and all(
    OVERVIEW_BADGE[r] == SILK_OF[r] for r in CONN if r not in ('J_BACK_SD', 'J_TOUCH'))

# Speaker: DigiKey photo of the CMS-30204-18SP back; the two solder pads at the lower left edge.
SPK_PADS_PX = {'a': (104, 522), 'b': (166, 588)}
# Camera socket: seller close-up kept as evidence for the pin order (HANDOFF "camera socket pin order"): the corner mounting
# hole is at the lower left, so the pin nearest it (left in the picture) is silk V = circuit 5, then 4, 3, 2, 1.
CAM_CROP = (0, 240, 860, 1040)
CAM_PIN_PX = {5: (283, 585), 4: (350, 535), 3: (415, 488), 2: (482, 440), 1: (545, 398)}
CAM_SILK = {'5V': 'V', 'D-': 'M', 'D+': 'P', 'GND': 'G', '屏蔽': 'G'}


def speaker_module() -> dict:
    im = Image.open(AB.PHOTOS / 'speaker_cms_30204_18sp_back.jpg').convert('RGB').crop((0, 150, 900, 760))
    pins = [(pid, lab, name, 'signal', 5, x / im.width, (y - 150) / im.height)
            for (pid, (x, y)), (lab, name) in zip(SPK_PADS_PX.items(), (('红', '喇叭红线（已焊在喇叭上）'), ('黑', '喇叭黑线（已焊在喇叭上）')))]
    return AB.photo_module('spk', '喇叭 CMS-30204-18SP', '喇叭背面；红、黑两根线已经焊在这两个焊盘上，不用动', '喇叭', im, 30.0, pins)


def camera_module() -> dict:
    im = Image.open(BOARD / 'evidence-cam-socket' / 'sock_big.jpg').convert('RGB').crop(CAM_CROP)
    pins = []
    for n, (x, y) in CAM_PIN_PX.items():
        sig = usb_signal('J_CAM', n)
        role = 'power' if sig == '5V' else 'ground' if sig in ('GND', '屏蔽') else 'signal'
        pins.append((f'c{n}', CAM_SILK[sig], f'板上印 {CAM_SILK[sig]}：{sig}', role, 5 if sig == '5V' else None if role == 'ground' else 3.3,
                     (x - CAM_CROP[0]) / im.width, (y - CAM_CROP[1]) / im.height))
    return AB.photo_module('cam', 'U20CAM 摄像头的插座', '摄像头板上的白色 5 针小插座；V 那头靠着板角的螺丝孔', '摄像头', im, 13.0, pins)


def a7z_usb_module() -> dict:
    """The USB-C end of the A7Z from Radxa's top photo (photos.py landmarks): only the edge with the two USB-C ports."""
    box = (1100, 330, P.TOP_BOX[2], P.TOP_BOX[3])
    im = Image.open(P.SRC / 'a7z-top.png').convert('RGBA').crop(box)      # photo_svg flattens the transparent edge
    w, h = im.width / TB.A7Z_PX_MM, im.height / TB.A7Z_PX_MM
    x, y = (P.USBC2_TOP[0] - box[0]) / TB.A7Z_PX_MM, (P.USBC2_TOP[1] - box[1]) / TB.A7Z_PX_MM
    pins = []                   # the cable's five wires end in the one USB plug: five points across the port, 1.6 mm apart
    for i, (n, _, _, _) in enumerate(sorted(CELLS['J_UP'], key=lambda c: c[1])):
        sig = usb_signal('J_UP', n)
        role = 'power' if sig == '5V' else 'ground' if sig in ('GND', '屏蔽') else 'signal'
        pin = {'id': f'u{n}', 'label': sig, 'name': f'USB 线的{sig}线，进 A7Z 的 USB 口（经 USB-A 转 USB-C 转接头）', 'role': role,
               'x': round(x + (i - 2) * 1.6, 3), 'y': round(y, 3)}
        if role != 'ground':
            pin['voltage'] = 5 if sig == '5V' else 3.3
        pins.append(pin)
    return {'id': 'a7zusb', 'title': 'Radxa Cubie A7Z（只画 USB 口这一段）', 'short': 'A7Z', 'subtitle': '背包座里的主板；USB 线这一头不动',
            'drawing': {'kind': 'svg', 'svg': TB.photo_svg(im, w, h)}, 'width': round(w, 2), 'height': round(h, 2), 'pins': pins}


# ---------------------------------------------------------------- the leads, one step each
def pin_for(ref, net):
    hits = [n for n, _, _, pnet in CELLS[ref] if pnet == net]
    assert len(hits) == 1, (ref, net, hits)
    return hits[0]


MIC_NET = {'VDD': '+3V3', 'GND': 'GND', 'SCK': 'MIC_SCK', 'WS': 'MIC_WS'}
XIAO_NET = {'GND': 'GND', 'D5': 'TOUCH_SCL', 'D4': 'TOUCH_SDA', '3V3': '+3V3'}
XIAO_FLAG = {'GND': 25, 'D5': 29, 'D4': 31}             # A7Z pins these leads sit on today (a7z_touch_bus)
END = {'male': '带公头', 'female': '带母头', 'bare': '剥好的线头', 'plug': '成品插头'}


def wire(wid, frm, ref, n, col, zh, what, end, group, note=''):
    target = where(ref, n)
    sig = usb_signal(ref, n) if ref in USB_REFS else NET_NAME[CONN[ref][1][n - 1]][0]
    return {'id': wid, 'from': frm, 'to': f'board.{ref}.{n}', 'color': col, 'group': group, 'note': note,
            'label': f'{what} → {target}（{sig}）', 'zh': zh, 'what': what, 'end': end, 'ref': ref, 'pin': n,
            'net': CONN[ref][1][n - 1], 'target': target, 'sig': sig}


def mic_wires(mid, name, ref, sd_net):
    out = []
    for pad in ('VDD', 'GND', 'SCK', 'WS', 'SD'):
        net = sd_net if pad == 'SD' else MIC_NET[pad]
        col, zh = MIC_COL[pad]
        out.append(wire(f'{mid}-{pad}', f'{mid}.{pad}', ref, pin_for(ref, net), col, zh, f'{name} {pad}', 'male', 'mic'))
    return out


def lead_list(wires, colour_known=True) -> str:
    """One card per wire: colour chip, what it is, which position it goes into. No table."""
    lis = []
    for w in wires:
        if colour_known:
            head = f'<b>{w["zh"]}线</b>（{w["what"]}，{END[w["end"]]}）'
        else:
            head = f'<b>{w["what"]}</b> 那根（{END[w["end"]]}；照焊线页配色的话是{w["zh"]}色）'
        note = f'<div class="src">{w["note"]}</div>' if w['note'] else ''
        lis.append(f'<li data-pin="{w["ref"]}.{w["pin"]}" data-net="{w["net"]}"><span class="chip" style="background:{w["color"]}"></span>'
                   f'<span>{head} → <b>{w["target"]}</b>，板上这个位置是 {w["sig"]}。{note}</span></li>')
    return f'<ul class="leads">{"".join(lis)}</ul>'


def empty_note(ref, n) -> str:
    return f'<li data-pin="{ref}.{n}" data-net="{CONN[ref][1][n - 1] if n <= len(CONN[ref][1]) else ""}" data-empty="1">'


BENCHES = []          # (host id, module ids, placements, wires)
MODS = {}


def bench(host, mods, placements, wires) -> str:
    BENCHES.append({'host': host, 'modules': mods, 'placements': placements,
                    'groups': [{'id': 'mic', 'label': '麦克风', 'color': '#d81b60'}, {'id': 'touch', 'label': '触摸板', 'color': '#8d6e63'},
                               {'id': 'spk', 'label': '喇叭', 'color': '#6d4c41'}, {'id': 'usb', 'label': 'USB', 'color': '#1565c0'}],
                    'wires': [{k: w[k] for k in ('id', 'from', 'to', 'color', 'group', 'label', 'note', 'ref', 'pin', 'net')} for w in wires]})
    return f'<div class="wkhost" id="{host}"></div><p class="benchhint">图可以点：“逐根接线”一根一根看，点针脚看名字。</p>'


BOARD_AT = {'module': 'board', 'x': 0, 'y': 30}


def mic_step(key, no, mid, side, ref, sd_net, tob):
    name = f'{side}麦克风'
    wires = mic_wires(mid, side, ref, sd_net)
    word = SILK_OF[ref]
    order = '、'.join(w['sig'] for w in sorted(wires, key=lambda w: w['pin']))
    return AP.step(key, no, f'{name}：5 根线插进 {word} 排', f'{name}的 5 根线在 {word} 排，从左到右是 {order}。', f"""
{bench(f'bench-{key}', [mid, 'board'], [{'module': mid, 'x': 1, 'y': 0}, BOARD_AT], wires)}
<ol class="acts">
<li>顺着线找：{name}是头盖{side}位置内壁上那块圆形小板，从它出来 5 根带公头的线（每根大约 {tob} mm），现在插在面包板上。</li>
<li>把这 5 根从面包板上拔下来。一次只拔这一个麦克风的，别的先不动，这样不会认混。</li>
<li>照下面的顺序插进板子最上面印着 <b>{word}</b> 的那一排（字在这一排右端）。每根插到底。</li>
</ol>
{lead_list(wires, colour_known=False)}
<p class="src">认线看它焊在麦克风的哪个焊盘（焊盘名印在麦克风贴着头盖的那面，上图点焊盘能看到名字）。颜色只是当时焊线页的建议，你用的颜色不一样也没关系。</p>""")


def s_ear_r(no):
    return mic_step('ear-r', no, 'micr', '右耳', 'J_EAR_R', 'MIC_SD_EARS', SOL.TOB('mic-r'))


def s_ear_l(no):
    return mic_step('ear-l', no, 'micl', '左耳', 'J_EAR_L', 'MIC_SD_EARS', SOL.TOB('mic-l'))


def s_back(no):
    wires = [w for w in mic_wires('micb', '后脑', 'J_BACK', 'MIC_SD_BACK') if not w['id'].endswith('-SD')]
    col, zh = MIC_COL['SD']
    sd = wire('micb-SD', 'micb.SD', 'J_BACK_SD', 1, col, zh, '后脑 SD', 'female', 'mic', '这根带母头，原来插 A7Z 10 号针（小旗 10），第 1 步已经抽回头里。')
    spare = pin_for('J_BACK', 'MIC_SD_BACK')
    return AP.step('back', no, f'后脑麦克风：4 根插进 {SILK_OF["J_BACK"]} 排，SD 套在针上',
                   f'后脑麦克风的 4 根带公头的线在 {SILK_OF["J_BACK"]} 排左边 4 个孔，带母头的 SD 套在 {where("J_BACK_SD", 1)}上。', f"""
{bench('bench-back', ['micb', 'board'], [{'module': 'micb', 'x': 1, 'y': 0}, BOARD_AT], wires + [sd])}
<ol class="acts">
<li>后脑麦克风在头盖后壁上。它有 4 根带公头的线（每根大约 {SOL.TOB('mic-b')} mm）插在面包板上，从面包板拔下来。</li>
<li>4 根照下面的顺序插进印着 <b>{SILK_OF['J_BACK']}</b> 的那一排。</li>
<li>它的第 5 根线是 SD，带母头（小旗 10）。把母头套在下面一排最左边那根针上，套到底。</li>
</ol>
{lead_list(wires, colour_known=False)}
{lead_list([sd], colour_known=False)}
<ul class="leads">{empty_note('J_BACK', spare)}<span class="chip none"></span><span><b>{where('J_BACK', spare)}空着。</b>后脑的 SD 走旁边那根针，这个孔不插东西。</span></li></ul>""")


def s_touch(no):
    wires = []
    for pad, end in (('GND', 'female'), ('D5', 'female'), ('D4', 'female')):
        col, zh = TOUCH_COL[pad]
        n = pin_for('J_TOUCH', XIAO_NET[pad])
        wires.append(wire(f'x-{pad}', f'xiao.{pad}', 'J_TOUCH', n, col, zh, f'触摸板 {pad}', end, 'touch', f'小旗 {XIAO_FLAG[pad]}，第 1 步从 A7Z 上拔下来抽回头里的。'))
    col, zh = TOUCH_COL['3V3']
    v = wire('x-3V3', 'xiao.3V3', 'J_TOUCH_3V3', pin_for('J_TOUCH_3V3', '+3V3'), col, zh, '触摸板 3V3', 'male', 'touch',
             f'短线，大约 {SOL.TOB("touch-pin17")} mm，现在插在面包板上。')
    spare = next(n for n, _, _, net in CELLS['J_TOUCH_3V3'] if net is None)
    row = '、'.join(f'第 {i + 1} 根{"后脑 SD" if r == "J_BACK_SD" else NET_NAME[CONN[r][1][k - 1]][0]}' for i, (_, r, k) in enumerate(ROWS['SD.T']))
    return AP.step('touch', no, '触摸板 XIAO：黑、蓝、绿套在针上，红线插 3V 座左孔',
                   f'触摸板的黑、蓝、绿三根在 SD.T 排的针上，红线在 3V 座左孔，3V 座右孔空着。', f"""
{bench('bench-touch', ['xiao', 'board'], [{'module': 'xiao', 'rotation': 180, 'x': 2, 'y': -6}, BOARD_AT], wires + [v])}
<ol class="acts">
<li>触摸板是头盖内顶上那块 XIAO 小板。它有 4 根线：黑、蓝、绿三根带母头，红的一根带公头。</li>
<li>黑、蓝、绿三个母头套在印着 <b>SD.T</b> 的那一排针上。这一排从左数：{row}。</li>
<li>红线的公头从面包板拔下来，插进最下面印着 <b>3V</b> 的两孔小座的<b>左孔</b>。</li>
</ol>
{lead_list(wires + [v])}
<ul class="leads">{empty_note('J_TOUCH_3V3', spare)}<span class="chip none"></span><span><b>{where('J_TOUCH_3V3', spare)}空着，什么都不插。</b></span></li></ul>""")


def speaker_reach() -> tuple[int, int]:
    """Straight-line mm from the speaker (guide model) to the J_SPK pins: nearest speaker point, and speaker centre.
    Board frame -> robot frame as in head-usb-board-20261111/fit_check.py (x right = robot -y, y down = robot -z)."""
    from array import array
    import base64
    src = (BOARD / 'fit_check.py').read_text()
    y_at_x0, z_at_y0 = (float(v) for v in re.search(r'Y_AT_X0, Z_AT_Y0 = ([\d.]+), ([\d.]+)', src).groups())
    x_limit = float(re.search(r'X_LIMIT = ([\d.]+)', src).group(1))
    tail, pcb = (float(v) for v in re.search(r'TAIL, PCB = ([\d.]+), ([\d.]+)', src).groups())
    cx = sum(c[1] for c in CELLS['J_SPK']) / len(CELLS['J_SPK'])
    cy = CELLS['J_SPK'][0][2]
    t = (x_limit - tail - pcb, y_at_x0 - cx, z_at_y0 - cy)
    part = next(p for p in json.loads(AP.GUIDE_DATA.read_text())['parts'] if p['key'] == 'speaker')
    a = array('f')
    a.frombytes(base64.b64decode(part['positionB64']))
    pts = [tuple(a[i:i + 3]) for i in range(0, len(a), 3)]
    near = min(math.dist(p, t) for p in pts)
    centre = math.dist(tuple(sum(p[k] for p in pts) / len(pts) for k in range(3)), t)
    return round(near), round(centre)


SPK_NEAR, SPK_CENTRE = speaker_reach()


def s_spk(no):
    wires = []
    for (pid, _), net in zip(SPK_PADS_PX.items(), ('SPK_P', 'SPK_N')):
        lab = NET_NAME[net][0]
        col, zh = SPK_COL[lab]
        wires.append(wire(f'spk-{pid}', f'spk.{pid}', 'J_SPK', pin_for('J_SPK', net), col, zh, f'喇叭{zh}线', 'bare', 'spk'))
    return AP.step('spk', no, '喇叭：红线进左孔，黑线进右孔，拧紧', '喇叭的红、黑两根线拧在绿色 SPK 端子里，拉一下不松。', f"""
{bench('bench-spk', ['spk', 'board'], [{'module': 'spk', 'x': 0, 'y': -2}, BOARD_AT], wires)}
<ol class="acts">
<li>先比一下线够不够长：喇叭线当时是按 {SOL.SPK} mm 剪的，喇叭到 SPK 端子直线就有 {SPK_NEAR} 到 {SPK_CENTRE} mm。板子放到摄像头背面的位置，线能松松地到端子下边就行；够不到就换两根 60 mm 的细线焊到喇叭的两个焊盘上，不要硬拉。</li>
<li>SPK 是板上那个绿色的两孔端子。两颗螺丝朝你（朝后），进线口在端子的<b>下边</b>，线从下往上插。</li>
<li>用小螺丝刀把两颗螺丝各拧松几圈。</li>
<li>喇叭红线的线头插进左孔，黑线的线头插进右孔（从后面看板子，和上图一样）。铜丝全部进孔，外面不留铜丝毛。</li>
<li>两颗螺丝拧紧，每根线轻轻拉一下，不松就对了。</li>
</ol>
{lead_list(wires)}""")


def usb_wires(ref, frm, prefix, cable):
    out = []
    for n, _, _, _ in sorted(CELLS[ref], key=lambda c: c[1]):
        sig = usb_signal(ref, n)
        col, zh = USB_COL[sig] if cable else ((RED, '红') if sig == '5V' else (GREY, '灰'))
        out.append(wire(f'{prefix}-{n}', frm(n), ref, n, col, zh, f'{sig}线' if sig == '屏蔽' else f'{sig} 线', 'plug', 'usb'))
    return out


def s_cam(no):
    wires = usb_wires('J_CAM', lambda n: f'cam.c{n}', 'cam', cable=False)
    order = '、'.join(CAM_SILK[w['sig']] for w in wires)
    return AP.step('cam', no, '摄像头短线：先改一头线序，再插摄像头和 CAM 座',
                   '短线两头线序一样；一头插在摄像头上，一头插在板子的 CAM 座上，5 V 那根在摄像头的 V 和板子的 5V 字样那头。', f"""
{bench('bench-cam', ['cam', 'board'], [{'module': 'cam', 'x': 16, 'y': 4}, BOARD_AT], wires)}
<div class="warn"><b>买来的双头短线是交叉的，不能直接用。</b>查到的成品短线一头的第 1 根通到另一头的第 5 根。上一次没改线序的线插上去，烧了第一块摄像头。</div>
<ol class="acts">
<li>把短线的两个插头并排放，同一面朝上，线都朝你。看两边从左到右的颜色顺序：一样就不用改；左右相反就要改。</li>
<li>先定哪个插头不动：拿一个插头对着摄像头的插座比一下，先不插。摄像头的 5 针从靠板角螺丝孔那头数是 {order}。红线能落在 <b>V</b> 那一针上的那个插头不动，改另一个。</li>
<li>全黑的线分不出颜色：随便定一个插头不动，用记号笔在落在 V 上的那根线两头各点一个点，后面把它当红线看。</li>
<li>改另一个插头：用针尖轻轻挑起插头上每根线的小卡片，把 5 根线都抽出来，按相反的顺序插回去，每根推到“咔”一下卡住。</li>
<li>改完再并排比一次：两边颜色顺序一样了才对。</li>
<li>把现在插在摄像头上的 USB 线拔下来：捏住小插头拔，不要拉线。这根线第 {N['up']} 步还要用。</li>
<li>短线一头插进摄像头的白色小插座，另一头插进板子上印 <b>CAM</b> 的座。插头有方向，反了插不进，不要硬按。</li>
<li>看板子这头：红线（或做了记号的那根）在 CAM 座旁边 <b>5V</b> 字样那一头。不在就拔下来，不要通电。</li>
</ol>
{lead_list(wires)}
<p class="src">图里只有 5 V 那根画成红色，其余画成灰色：别的线是什么颜色要看你买到的线。要求只有一条，每一针通到另一头同一个位置的针。</p>""")


def s_up(no):
    wires = usb_wires('J_UP', lambda n: f'a7zusb.u{n}', 'up', cable=True)
    for w in wires:
        w['from'], w['to'] = w['to'], w['from']
    colours = '、'.join(w['zh'] for w in wires)
    return AP.step('up', no, '原来的摄像头 USB 线：小插头从摄像头换到 A7Z 座',
                   '摄像头现在用的那根 USB 线，小插头插在板子的 A7Z 座上，红线在 5V 字样那头；另一头还在 A7Z 的 USB 口上。', f"""
{bench('bench-up', ['board', 'a7zusb'], [{'module': 'a7zusb', 'x': 9, 'y': 0}, {'module': 'board', 'x': 0, 'y': 28}], wires)}
<ol class="acts">
<li>拿起第 {N['cam']} 步从摄像头上拔下来的那根 USB 线的 5 针小插头。线的另一头经转接头插在 A7Z 的 USB 口上，那一头不动。</li>
<li>把 5 针小插头插进板子上印 <b>A7Z</b> 的座。插头有方向，反了插不进，不要硬按。</li>
<li>看颜色：从 5V 字样那头数，5 根线是{colours}。红线必须在 <b>5V</b> 字样那一头。不在就拔下来，不要通电。</li>
</ol>
{lead_list(wires)}
<p>从头到背包座，过脖子的线现在只剩这一根 USB 线（舵机的线不算）。</p>""")


# ---------------------------------------------------------------- first and last sections
HEAD_PINS = sorted(set(AP.USED) - set(AP.TORSO_PINS))        # plugs on the A7Z header that come from the head today
STAY_IN_HEAD = sorted([10, *XIAO_FLAG.values()])             # leads that keep their far end and move to the new board
LEAVE_BB = sorted(SOL.DOWNS)                                 # breadboard strips' wires down to the A7Z
LEAVE_AMP = sorted(set(HEAD_PINS) - set(STAY_IN_HEAD) - set(LEAVE_BB))
assert LEAVE_AMP == [4, 39, 40] and len(HEAD_PINS) == 12, (HEAD_PINS, LEAVE_AMP)


def nums(ns) -> str:
    return '、'.join(str(n) for n in ns)


def s_parts():
    amp = '、'.join(f'{k} {v[1]}' for k, v in SOL.AMP_COL.items())
    return f"""
<section class="step" id="parts"><div class="stepno">开始之前</div><h2>手上要有什么，哪些东西离开头</h2>
<div class="cards">
<div class="card"><h3>手上要有</h3>
<ul class="acts">
<li><b>头部 USB 板</b>：JLCPCB 做好焊好的 30 × 30 mm 板（文件在 <code>{BOARD_REF}/</code>），固件已经刷进去（<code>{BOARD_REF}/firmware/README.md</code> 的 Flashing 一节，板子装进头之前刷）。</li>
<li><b>摄像头到板子的短线</b>：1.25 mm 间距 5 针的双头线（Molex PicoBlade 那种小白插头，两头一样）。买来的是交叉的，第 {N['cam']} 步改一头线序。越短越好，10 cm 以内。</li>
<li><b>针或尖镊子</b>：改线序时挑插头上的小卡片。</li>
<li><b>小螺丝刀</b>：拧喇叭端子的两颗螺丝。</li>
<li><b>1.5 mm 厚的泡棉胶，或者一根扎带</b>：最后固定板子，二选一。</li>
<li><b>Kapton 胶带</b>：把多出来的线贴住。</li>
<li><b>可能用到：两根 60 mm 细线（红、黑）和烙铁</b>。喇叭线现在只有 {SOL.SPK} mm，够不到新板的端子时换长的（第 {N['spk']} 步先比）。</li>
</ul></div>
<div class="card"><h3>离开头的</h3>
<ul class="acts">
<li><b>迷你面包板</b>（摄像头背面那块）。</li>
<li><b>MAX98357A 功放模块</b>，连它的 5 根线（{amp}）。新板上已经有同一颗功放芯片。</li>
<li><b>过脖子的杜邦线</b>：面包板到 A7Z 的 5 根公对母线（小旗 {nums(LEAVE_BB)}），功放到 A7Z 的 3 根（小旗 {nums(LEAVE_AMP)}）。</li>
</ul></div>
<div class="card"><h3>留下、换个地方插的</h3>
<ul class="acts">
<li>三个麦克风、触摸板 XIAO、喇叭、摄像头都不动，也不重新焊。</li>
<li>它们的线原样留着，只是另一头改插到新板上。</li>
<li>A7Z 的 40 针排针上最后只剩从躯干上来的 {len(AP.TORSO_PINS)} 个插头：{nums(sorted(AP.TORSO_PINS))} 号针。</li>
</ul></div>
</div>
<p class="src">板子和短线到手以后再做这一页（买没买、到没到看 <code>CURRENT-STATE.json</code> 的 <code>parts_a7z_extensions</code>）。这一页只讲接线；接好以后 A7Z 上录音、放声音、读触摸的程序要改成走 USB，那部分不在这一页。</p>
</section>"""


def s_overview():
    im = overview_figure()
    rows = []
    for ref in OVERVIEW_BADGE:
        fam = family(ref)
        n = len(CELLS[ref])
        what = {
            'J_EAR_R': f'右耳麦克风的 5 根线，第 {N["ear-r"]} 步',
            'J_EAR_L': f'左耳麦克风的 5 根线，第 {N["ear-l"]} 步',
            'J_BACK': f'后脑麦克风的 4 根线，最右边一个孔空着，第 {N["back"]} 步',
            'J_BACK_SD': f'后脑麦克风的 SD 线（带母头），第 {N["back"]} 步',
            'J_TOUCH': f'触摸板的黑、蓝、绿三根线（带母头），第 {N["touch"]} 步',
            'J_TOUCH_3V3': f'触摸板的红线插左孔，右孔空着，第 {N["touch"]} 步',
            'J_SPK': f'喇叭的红、黑两根线，第 {N["spk"]} 步',
            'J_UP': f'原来插在摄像头上的那根 USB 线，另一头在 A7Z，第 {N["up"]} 步',
            'J_CAM': f'到摄像头的短线，第 {N["cam"]} 步',
        }[ref]
        shape = {'PinSocket': f'{n} 孔黑色排母', 'PinHeader': f'{n} 根针', 'Molex_PicoBlade': '白色 5 针小座', 'TerminalBlock': '绿色两孔螺丝端子'}[fam]
        silk = SILK_OF[ref]
        row = [r for _, r, _ in ROWS.get(silk, [])]
        tail = '' if silk == OVERVIEW_BADGE[ref] else f'，板上印 {silk} 的那一排{"最左边" if row[0] == ref else "靠右"}的 {n} 根'
        rows.append(f'<li><span class="dot pin">{OVERVIEW_BADGE[ref]}</span><span><b>{shape}</b>{tail}：{what}。</span></li>')
    return f"""
<section class="step" id="overview"><div class="stepno">总览</div><h2>板子上每个插座插什么</h2>
<div class="goal"><b>看完这一节：</b>你能在板子上指出 9 个插座，知道每个插什么。</div>
<div class="pair"><div>{AP.figure(AP.uri(im, 1300), '头部 USB 板，每个插座标了名字',
    '这是 JLCPCB 的贴片预览图，从机器人后面看板子有元件的那面；红字是图纸上的零件编号，实物上没有。蓝色标签是板上白色丝印的字。截图没截到板子最下面 4 mm，那里只有芯片。两个白色小座左边各印着 5V。')}</div>
<div><ul class="legend big">{''.join(rows)}</ul>
<div class="card"><b>方向：</b>板子竖着装在摄像头背面、原来面包板的位置。有插座的那面朝后（朝你），插座那一条在上边。这一页所有的“左”“右”都是从机器人后面看板子，和图一样。</div></div></div>
</section>"""


def s_strip(no):
    keep = '、'.join(f'{n}（{"后脑麦克风 SD" if n == 10 else "触摸板"}）' for n in STAY_IN_HEAD)
    long_mm = max(SOL.PICK('mic-sd3'), *(SOL.PICK(f'touch-pin{n}') for n in XIAO_FLAG.values()))
    return AP.step('strip', no, '断电，拔掉过脖子的线，取出功放',
                   f'电源断开；A7Z 排针上只剩 {nums(sorted(AP.TORSO_PINS))} 号针的 {len(AP.TORSO_PINS)} 个插头；功放拿出来了；面包板还贴着，麦克风和触摸板的线还插在上面。', f"""
<ol class="acts">
<li><b>断电：</b>拔开电池背包左下方的两个插头（舵机的 XT30 和 A7Z 的 MR30）。</li>
<li>翻开头盖，能看到摄像头背面的面包板。</li>
<li><b>A7Z 排针上拔 {len(HEAD_PINS)} 个插头：</b>小旗 {nums(HEAD_PINS)}。小旗 {nums(sorted(AP.TORSO_PINS))} 是从躯干上来的，不要动。</li>
<li><b>4 根线留着用，抽回头里：</b>小旗 {keep}。顺着脖子把它们抽上来。</li>
<li><b>8 根线不要了：</b>小旗 {nums(LEAVE_BB)} 的 5 根，把它们的公头从面包板上拔下来，整根拿走；小旗 {nums(LEAVE_AMP)} 的 3 根连着功放，下一条一起拿走。</li>
<li><b>取出功放：</b>拧松功放绿色端子上的两颗螺丝，抽出喇叭的红、黑两根线（喇叭线留着）；把功放的白线、紫线两个公头从面包板上拔下来；功放连它的 5 根线一起拿出来。</li>
<li>抽回头里的 4 根线原来通到背包座，每根大约 {long_mm // 10} 厘米长。多出来的折两折，用 Kapton 贴成一小捆，留出带插头的一段。</li>
<li>面包板先不撕：麦克风和触摸板的线还插在上面，后面一步一步挪到新板上。新板这时候拿在手上，贴着面包板旁边插线。</li>
</ol>
<div class="warn"><b>4 号针是 5 V。</b>拔下来的插头不要搭在 A7Z 的排针上。这一页做完之前不要接回电源。</div>""")


def s_check(no):
    five = '、'.join(f'{SILK_OF[r]} 座' for r in USB_REFS)
    empty = [where('J_TOUCH_3V3', next(n for n, *_, net in CELLS['J_TOUCH_3V3'] if net is None)), where('J_BACK', pin_for('J_BACK', 'MIC_SD_BACK'))]
    mic_order = '、'.join(NET_NAME[n][0] for n in CONN['J_EAR_R'][1])
    return AP.step('check', no, '通电前检查，固定板子，再接电源', '六项检查都对；面包板撕掉了；板子固定在摄像头背面；电源接回去了。', f"""
<h3>先检查，一项一项看</h3>
<ol class="acts">
<li><b>红线在 5V 字样那头：</b>{five}，两个白色小座都看一遍。有一个不对就不要通电。</li>
<li><b>{empty[0]}是空的。</b></li>
<li><b>{empty[1]}是空的。</b></li>
<li>R、L、B 三排，每排从左到右是 {mic_order}：顺着每根线看一眼它焊在麦克风的哪个焊盘。3V3 和 GND 不能插反。</li>
<li>喇叭两根线拧紧了，端子外面没有铜丝毛。</li>
<li>A7Z 排针上只有 {nums(sorted(AP.TORSO_PINS))} 号针有插头，没有散着的线头搭在排针上。</li>
</ol>
<h3>再固定板子</h3>
<ol class="acts">
<li>把空了的面包板从摄像头背面撕下来。</li>
<li>板子竖着放到摄像头背面、原来面包板的位置：有插座的那面朝后，插座那一条在上边。</li>
<li><b>用泡棉胶：</b>剪一块 1.5 mm 厚的泡棉胶，贴在板子没有元件那面的<b>下半截</b>，再按到摄像头背面。上面 13 mm 那一条有焊脚的尖，不贴胶。</li>
<li><b>或者用扎带：</b>一根扎带绕过板子和摄像头板，勒住板子下半截，不要压到插头和线。</li>
<li>线顺一下，用 Kapton 把线束贴在板子旁边，拉线时力在胶带上。合上头盖。</li>
</ol>
<h3>最后接电源</h3>
<ol class="acts">
<li>接回电池背包的两个插头（XT30 和 MR30）。</li>
</ol>""")


def s_sources():
    return f"""
<details class="src"><summary>这一页的数据从哪来</summary>
<ul>
<li>每个插座每一针接什么：<code>{BOARD_REF}/sch/netlist.py</code>。位置：<code>pcb/placement.py</code>、<code>pcb/build/footprints.json</code>、<code>pcb/build/pos.csv</code>。丝印字：<code>pcb/gen_pcb.py</code> 的 SILK。板子图片：<code>pcb/build/jlcpcb-placement-preview.jpg</code>。</li>
<li>机器人现在的接法和线色（触摸板四根线、摄像头线的红白绿黑黑、三个麦克风都装着、电源插头的位置）：<code>CURRENT-STATE.json</code> 的 <code>a7z_touch_bus</code>、<code>parts_a7z_extensions</code>、<code>a7z_audio_capture</code>、<code>backpack_swap_plugs</code>。</li>
<li>线头是公头还是母头、喇叭线红黑、麦克风线的建议颜色和大约长度：焊线页的源文件 <code>bringup/a7z/build_a7z_solder.py</code> 和 <code>head-wire-lengths.json</code>。这几项状态文件里没有记，也没有在机器人上核对过。</li>
<li>摄像头插座哪头是 V、短线要改线序、固定方法：<code>{BOARD_REF}/HANDOFF.md</code>（2026-11-12 各节）。摄像头的针序是从厂家手册和卖家照片推出来的，所以第 {N['cam']}、{N['up']}、{N['check']} 步都要看红线。</li>
</ul></details>"""


CSS = """
.cards { display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; align-items:start; }
.cards .card { margin:0; } .cards h3 { margin-top:2px; }
.leads { list-style:none; padding:0; margin:12px 0; display:grid; gap:8px; }
.leads li { display:flex; gap:10px; align-items:flex-start; border:1px solid var(--line); border-radius:10px; padding:8px 12px; background:#fff; }
.chip { flex:0 0 auto; width:22px; height:22px; border-radius:50%; border:1px solid #607d8b; margin-top:4px; }
.chip.none { background:repeating-linear-gradient(45deg, #fff, #fff 4px, #cfd8dc 4px, #cfd8dc 7px); }
.legend.big li { margin:8px 0; } .legend.big .dot { min-width:48px; }
.wkhost { margin:10px 0 4px; }
.benchhint { color:var(--muted); font-size:15px; margin:0 0 10px; }
@media (max-width: 760px) { .cards { grid-template-columns:1fr; } }
"""

ORDER = [('strip', '拆旧线'), ('ear-r', '右耳'), ('ear-l', '左耳'), ('back', '后脑'), ('touch', '触摸板'), ('spk', '喇叭'),
         ('cam', '摄像头短线'), ('up', 'USB 线'), ('check', '检查固定')]
N = {k: i + 1 for i, (k, _) in enumerate(ORDER)}


def build() -> None:
    MODS.update(board=board_module(), micr=AB.mic('micr', '右耳麦克风', '右耳', '已焊一根短线到 VDD'),
                micl=AB.mic('micl', '左耳麦克风', '左耳', '已焊一根短线到 GND'), micb=AB.mic('micb', '后脑麦克风', '后脑', '已焊一根短线到 GND'),
                xiao=TB.xiao(), spk=speaker_module(), cam=camera_module(), a7zusb=a7z_usb_module())
    for mid in ('micr', 'micl', 'micb'):
        MODS[mid]['subtitle'] = '印字那面（贴着头盖内壁的那面）；L/R 焊盘上的短线不用动'
    MODS['xiao']['subtitle'] = '触摸板，头盖内顶上；铜箔的 5 根线不用动'
    fn = {'strip': s_strip, 'ear-r': s_ear_r, 'ear-l': s_ear_l, 'back': s_back, 'touch': s_touch, 'spk': s_spk, 'cam': s_cam,
          'up': s_up, 'check': s_check}
    steps = ''.join(fn[k](f'第 {N[k]} 步') for k, _ in ORDER)
    data = json.dumps({'modules': MODS, 'benches': BENCHES}, ensure_ascii=False).replace('</', '<\\/')
    wk_css = (TB.WK / 'wiring-kit.css').read_text()
    wk_js = (TB.WK / 'wiring-kit.js').read_text().replace('</script', '<\\/script')
    kit = (f'<script type="application/json" id="hub-data">{data}</script><script>{wk_js}</script>'
           '<script>(function(){var D=JSON.parse(document.getElementById("hub-data").textContent);'
           'D.benches.forEach(function(b){WiringKit.render(document.getElementById(b.host),'
           '{modules:b.modules.map(function(id){return D.modules[id];}),placements:b.placements,groups:b.groups,wires:b.wires},'
           f'{{text:{TB.TEXT},pinLabel:function(pin){{return pin.label;}}}});}});}})();</script>')
    title = '头部 USB 板接线：头里每个元器件怎么插到新板子上'
    lead = ('<p class="lead">头里加一块 30 × 30 mm 的 USB 板，装在摄像头背面，替掉面包板和功放模块。三个麦克风、触摸板、喇叭、摄像头的线都改插到这块板上，'
            '过脖子到 A7Z 的只剩一根 USB 线。这一页先说要准备什么，再看板子上每个插座插什么，然后一根线一步。</p>')
    nav = [('parts', '准备'), ('overview', '总览')] + [(k, f'{N[k]} {t}') for k, t in ORDER]
    text = lead + s_parts() + s_overview() + steps + s_sources()
    assert not any(ch in text for ch in '—–─') and '<table' not in text, 'dash or table in the page text'
    out = AP.page(title, title, lead, nav, text[len(lead):] + kit)
    out = out.replace('</head>', f'<style>{wk_css}</style><style>{CSS}</style></head>', 1)
    OUT.write_text(out)
    print(f'wrote {OUT} ({OUT.stat().st_size // 1024} kB), {len(BENCHES)} wiring views, {sum(len(c) for c in CELLS.values())} board positions')


if __name__ == '__main__':
    build()
