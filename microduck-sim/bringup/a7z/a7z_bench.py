"""wiring-kit bench for A7Z-PINS.html: every board that connects to the A7Z 40-pin header, as wired in the roof saddle.

The A7Z is drawn as seen from above in the saddle (D-022) with the robot's nose pointing up the page: component side up,
the header along the rear edge (bottom of the drawing), pin 1 at the right-hand (-Y) end with the antenna and fan
sockets. That is the portrait photo of photos.py turned a quarter turn clockwise (wiring-kit rotation 90).

Wires and pins: the assembly guide (guide/data/guide-data.json steps saddle-plugs and saddle-head-plugs; mics and
mic-splice for the microphones, mic-back for the optional back microphone). The joints at the left rear corner of the cap
are drawn as one module, the gather point: the amplifier BCLK and LRC wires and the XIAO 3V3 wire run into it and on to A7Z
pins 12, 35 and 17; the left and back microphones' SCK, WS and VDD join them there; the left microphone's GND jumper runs
through it to pin 34 and the back microphone's GND joins it there. The right microphone's five wires end on the left
microphone's pads. The left SD goes straight to pin 38; the back SD ends on a flag-10 plug taped beside pin 10, drawn to
pin 10 in a group of its own (D-026 addendum: pin 10 stays UART0 RX until the I2S0 DIN3 overlay is tested).
Clicking a board in the view highlights its wires and fades the rest (wiring-kit module selection).

Pictures:
- A7Z and XIAO: touch_bench.py (Radxa top photo, Seeed front pinout crop).
- OpenRB-150: ../parts/photos/openrb_150_top.png (robotis.us product photo), lower part around J12 only; pads from the
  guide bench (J12 Rx 25.26 / Tx 21.57 mm across, 96.38 mm down on the 55.88 x 133.67 mm board).
- XL4015 #2: the guide bench drawing (rear converter box, OUT on the left).
- BNO085 and MAX98357A: ../parts/photos (Adafruit photos), pin positions from ../parts/parts.json.
- INMP441: sources/inmp441-label-face-aitrip.png, the label face from the AITRIP listing (Amazon B0972XP1YS, image
  51U06tkdoBS, read 2026-10-25). Board 13.4 mm across (D-025).
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

import photos as P
import touch_bench as TB

PARTS = json.loads((P.HERE.parent / 'parts' / 'parts.json').read_text())
PHOTOS = P.HERE.parent / 'parts' / 'photos'
GUIDE = P.HERE.parent.parent / 'guide' / 'data' / 'guide-data.json'

# Wire colours: the real ones where the build fixed them (5 V lead, UART pair, IMU cable, touch leads); the amplifier and
# microphone jumpers are any colour, identified by their flags, so they get one colour per signal here.
RED, BLK, BLU, YEL, GRN, WHT = '#d7263d', '#1d1d1f', '#1f6fd1', '#c99a00', '#1f9d55', '#ffffff'
PUR, ORG, TEAL, PINK, BRN = '#7b5ea7', '#ef6c00', '#00897b', '#d81b60', '#8d6e63'

WIRES = [  # id, from, to, colour, group, caption, note
    ('p5', 'xl2.OUTP', 'a7z.p2', RED, 'power', '红：5 V 线 → A7Z 2 号针',
     '来自后面转换盒里 XL4015 #2 的 OUT+（5.00 V），中间经 MR30 接头。'),
    ('g5', 'xl2.OUTN', 'a7z.p6', BLK, 'power', '黑：5 V 线地 → A7Z 6 号针', '来自 XL4015 #2 的 OUT−，经 MR30 接头。'),
    ('tx', 'orb.Rx', 'a7z.p7', GRN, 'uart', '绿：A7Z 7 号针 → OpenRB J12 的 Rx', 'A7Z 从 7 号针发（UART2 TX），OpenRB 收。'),
    ('rx', 'orb.Tx', 'a7z.p11', WHT, 'uart', '白：OpenRB J12 的 Tx → A7Z 11 号针', 'OpenRB 发，A7Z 从 11 号针收（UART2 RX）。'),
    ('ivin', 'imu.VIN', 'a7z.p1', RED, 'imu', '红：IMU 3.3 V → A7Z 1 号针', '4397 线的红插孔。线的另一头是白色小插头，插在 IMU 的 STEMMA QT 插座上。'),
    ('isda', 'imu.SDA', 'a7z.p3', BLU, 'imu', '蓝：IMU SDA → A7Z 3 号针', '4397 线的蓝插孔，TWI7 的数据线。'),
    ('iscl', 'imu.SCL', 'a7z.p5', YEL, 'imu', '黄：IMU SCL → A7Z 5 号针', '4397 线的黄插孔，TWI7 的时钟线。'),
    ('ignd', 'imu.GND', 'a7z.p9', BLK, 'imu', '黑：IMU GND → A7Z 9 号针', '4397 线的黑插孔。'),
    ('avin', 'amp.Vin', 'a7z.p4', RED, 'audio', '功放 Vin → A7Z 4 号针（5 V）', '小旗 4。4 号针是 5 V，插错会烧板子。'),
    ('abclk', 'amp.BCLK', 'gp.SCK', ORG, 'audio', '功放 BCLK → 集线点', '在头盖左后角剪开，和麦克风的 SCK 焊在一起，再接着往下到 12 号针。'),
    ('gsck', 'gp.SCK', 'a7z.p12', ORG, 'audio', '集线点 BCLK/SCK → A7Z 12 号针', '小旗 12。还是功放那根 BCLK 线，里面并着两个麦克风的 SCK。'),
    ('alrc', 'amp.LRC', 'gp.WS', PUR, 'audio', '功放 LRC → 集线点', '在头盖左后角剪开，和麦克风的 WS 焊在一起，再接着往下到 35 号针。'),
    ('gws', 'gp.WS', 'a7z.p35', PUR, 'audio', '集线点 LRC/WS → A7Z 35 号针', '小旗 35。还是功放那根 LRC 线，里面并着两个麦克风的 WS。'),
    ('agnd', 'amp.GND', 'a7z.p39', BLK, 'audio', '功放 GND → A7Z 39 号针', '小旗 39。'),
    ('adin', 'amp.DIN', 'a7z.p40', TEAL, 'audio', '功放 DIN → A7Z 40 号针', '小旗 40，A7Z 送给功放的声音数据。'),
    ('t3v3', 'xiao.3V3', 'gp.VDD', RED, 'touch', '红：触摸板 3V3 → 集线点', '在头盖左后角剪开，和麦克风的 VDD 焊在一起，再接着往下到 17 号针。'),
    ('gvdd', 'gp.VDD', 'a7z.p17', RED, 'touch', '红：集线点 3V3/VDD → A7Z 17 号针（3.3 V）', '小旗 17。还是触摸板那根 3V3 线，里面并着两个麦克风的 VDD。'),
    ('tgnd', 'xiao.GND', 'a7z.p25', BLK, 'touch', '黑：触摸板 GND → A7Z 25 号针', '小旗 25。'),
    ('tscl', 'xiao.D5', 'a7z.p29', BLU, 'touch', '蓝：触摸板 D5（SCL）→ A7Z 29 号针', '小旗 29。'),
    ('tsda', 'xiao.D4', 'a7z.p31', GRN, 'touch', '绿：触摸板 D4（SDA）→ A7Z 31 号针', '小旗 31。'),
    ('msd', 'micl.SD', 'a7z.p38', PINK, 'mic', '左耳麦克风 SD → A7Z 38 号针', '小旗 38，两个麦克风的数据线（I2S0 DIN0）。带插头的杜邦线。'),
    ('mgnd', 'micl.GND', 'gp.GND', BLK, 'mic', '左耳麦克风 GND → 集线点', '带插头的杜邦线，路过集线点（后脑的 GND 在这里焊进来）。'),
    ('ggnd', 'gp.GND', 'a7z.p34', BLK, 'mic', '集线点 GND → A7Z 34 号针', '小旗 34。还是左耳那根 GND 杜邦线。'),
    ('msck', 'micl.SCK', 'gp.SCK', ORG, 'mic', '左耳麦克风 SCK → 集线点（并进功放 BCLK）',
     '细线，不带插头：在头盖左后角和功放 BCLK 线拧在一起焊，套热缩管。'),
    ('mws', 'micl.WS', 'gp.WS', PUR, 'mic', '左耳麦克风 WS → 集线点（并进功放 LRC）', '细线，不带插头：和功放 LRC 线焊在一起。'),
    ('mvdd', 'micl.VDD', 'gp.VDD', RED, 'mic', '左耳麦克风 VDD → 集线点（并进触摸板 3V3）', '细线，不带插头：和触摸板 3V3 线焊在一起（3.3 V）。'),
    ('rsck', 'micr.SCK', 'micl.SCK', ORG, 'mic', '右耳 SCK → 左耳 SCK', '两头都焊，跨过头盖内顶。'),
    ('rws', 'micr.WS', 'micl.WS', PUR, 'mic', '右耳 WS → 左耳 WS', '两头都焊。'),
    ('rsd', 'micr.SD', 'micl.SD', PINK, 'mic', '右耳 SD → 左耳 SD', '两头都焊。两个麦克风共用一根数据线，左右声道由 L/R 焊盘分开。'),
    ('rvdd', 'micr.VDD', 'micl.VDD', RED, 'mic', '右耳 VDD → 左耳 VDD', '两头都焊。'),
    ('rgnd', 'micr.GND', 'micl.GND', BLK, 'mic', '右耳 GND → 左耳 GND', '两头都焊。'),
    ('bsck', 'micb.SCK', 'gp.SCK', ORG, 'micb', '后脑麦克风 SCK → 集线点', '可选。细线，焊进 SCK/BCLK 那个接头。'),
    ('bws', 'micb.WS', 'gp.WS', PUR, 'micb', '后脑麦克风 WS → 集线点', '可选。细线，焊进 WS/LRC 那个接头。'),
    ('bvdd', 'micb.VDD', 'gp.VDD', RED, 'micb', '后脑麦克风 VDD → 集线点', '可选。细线，焊进 VDD/3V3 那个接头（3.3 V）。'),
    ('bgnd', 'micb.GND', 'gp.GND', BLK, 'micb', '后脑麦克风 GND → 集线点', '可选。细线，在集线点剪开左耳那根 GND 杜邦线焊进去。'),
    ('bsd', 'micb.SD', 'a7z.p10', PINK, 'micb', '后脑麦克风 SD（小旗 10）→ 贴在 10 号针旁，先不插',
     '可选。它自己的数据线（I2S0 DIN3），带插头。10 号针现在是调试串口的接收脚，DIN3 的设置试过以前插头用胶带贴在排针旁边，不插上去。'),
]
GROUPS = [{'id': 'power', 'label': '5 V 电源', 'color': RED}, {'id': 'uart', 'label': '舵机串口', 'color': GRN},
          {'id': 'imu', 'label': 'IMU', 'color': BLU}, {'id': 'audio', 'label': '功放', 'color': ORG},
          {'id': 'touch', 'label': '触摸板', 'color': BRN}, {'id': 'mic', 'label': '麦克风', 'color': PINK},
          {'id': 'micb', 'label': '后脑麦克风（可选）', 'color': PINK}]

A7Z_ROLE = {  # what each used pin carries in this robot, shown when the pin is tapped
    1: 'IMU 3.3 V', 2: '5 V 进（5 V 线红）', 3: 'IMU SDA（TWI7）', 4: '功放 Vin（5 V 出）', 5: 'IMU SCL（TWI7）',
    6: 'GND（5 V 线黑）', 7: 'UART2 TX → OpenRB', 9: 'IMU GND', 11: 'UART2 RX ← OpenRB',
    12: 'I2S0 BCLK：功放 BCLK + 麦克风 SCK', 17: '3.3 V：触摸板 3V3 + 麦克风 VDD', 25: '触摸板 GND',
    29: 'PB2 · 触摸板 SCL（TWI0）', 31: 'PB3 · 触摸板 SDA（TWI0）',
    35: 'I2S0 LRCK：功放 LRC + 麦克风 WS', 38: 'I2S0 DIN0：麦克风 SD', 39: '功放 GND', 40: 'I2S0 DOUT0：功放 DIN',
    34: '麦克风 GND（两只耳朵和后脑共用）',
    8: '调试串口 TX：空着', 10: '调试串口 RX：空着；后脑麦克风 SD（小旗 10）贴在旁边，先不插',
}


def photo_module(mid, title, subtitle, short, im: Image.Image, w_mm: float, pins) -> dict:
    """A board drawn from a photo; pins given as (id, label, name, role, voltage, x_frac, y_frac) on that photo."""
    h_mm = w_mm * im.height / im.width
    out = []
    for pid, label, name, role, volt, fx, fy in pins:
        p = {'id': pid, 'label': label, 'name': name, 'role': role, 'x': round(fx * w_mm, 3), 'y': round(fy * h_mm, 3)}
        if volt is not None:
            p['voltage'] = volt
        out.append(p)
    return {'id': mid, 'title': title, 'subtitle': subtitle, 'short': short,
            'drawing': {'kind': 'svg', 'svg': TB.photo_svg(im, w_mm, h_mm)}, 'width': round(w_mm, 2), 'height': round(h_mm, 2),
            'pins': out}


def part_pins(part_id: str, keep: dict) -> list:
    part = next(p for p in PARTS['parts'] if p['id'] == part_id)
    by = {p['label']: p for p in part['pins']}
    return [(lab, lab, name, role, volt, by[lab]['x'], by[lab]['y']) for lab, (name, role, volt) in keep.items()]


def a7z() -> dict:
    m = TB.a7z()
    m['subtitle'] = '背包座里，从上往下看，机器人的头朝上：排针在后边（图的下边），1 号针在右端'
    for p in m['pins']:
        n = int(p['label'])
        if n in A7Z_ROLE:
            p['note'] = f"{p['note']} · {A7Z_ROLE[n]}"
    return m


def imu() -> dict:
    im = Image.open(PHOTOS / 'bno085_4754_top.jpg').convert('RGB')
    pins = part_pins('bno085_4754', {'VIN': ('VIN，3.3 V 进', 'power', 3.3), 'GND': ('GND', 'ground', None),
                                     'SCL': ('SCL，I2C 时钟', 'signal', 3.3), 'SDA': ('SDA，I2C 数据', 'signal', 3.3)})
    return photo_module('imu', 'Adafruit BNO085 IMU', '躯干里的姿态传感器；实际用 4397 线插它的 STEMMA QT 插座', 'IMU', im, 25.4, pins)


def amp() -> dict:
    im = Image.open(PHOTOS / 'max98357a_3006_top.jpg').convert('RGB')
    pins = part_pins('max98357a_3006', {'LRC': ('LRC，I2S 左右时钟', 'signal', 3.3), 'BCLK': ('BCLK，I2S 位时钟', 'signal', 3.3),
                                        'DIN': ('DIN，I2S 数据进', 'signal', 3.3), 'GND': ('GND', 'ground', None),
                                        'Vin': ('Vin，5 V 进', 'power', 5)})
    return photo_module('amp', 'MAX98357A 功放', '头里黄色下壳地板上，喇叭左边', '功放', im, 17.8, pins)


MIC_PADS = [('SCK', 134, 97), ('WS', 208, 97), ('L/R', 282, 97), ('SD', 134, 324), ('VDD', 208, 324), ('GND', 282, 324)]


def mic(mid: str, title: str, short: str, lr: str) -> dict:
    im = TB.rounded(Image.open(P.HERE / 'sources' / 'inmp441-label-face-aitrip.png').convert('RGB'), 200)
    names = {'SCK': 'SCK，I2S 位时钟', 'WS': 'WS，I2S 左右时钟', 'SD': 'SD，声音数据出', 'VDD': 'VDD，3.3 V',
             'GND': 'GND', 'L/R': f'L/R：{lr}'}
    pins = []
    for pad, x, y in MIC_PADS:
        role = 'ground' if pad == 'GND' else 'power' if pad == 'VDD' else 'signal'
        pins.append((pad, pad, names[pad], role, None if role == 'ground' else 3.3, x / im.width, y / im.height))
    m = photo_module(mid, f'INMP441 {title}', f'印字那面（贴着头盖内壁）；{lr}', short, im, 13.4, pins)
    for p in m['pins']:
        p['multi'] = mid == 'micl'   # the left board carries its own wire and the right board's on each pad
        if p['id'] == 'L/R':
            p['note'] = lr
    return m


def gather() -> dict:
    """The joints at the left rear corner of the cap, over the head exit: four heat-shrunk splices in a row."""
    W, H = 30.0, 9.0
    names = {'SCK': ('功放 BCLK + 麦克风 SCK', '接头：功放 BCLK 线剪开，左耳和后脑的 SCK 焊进去，往下是小旗 12。'),
             'WS': ('功放 LRC + 麦克风 WS', '接头：功放 LRC 线剪开，左耳和后脑的 WS 焊进去，往下是小旗 35。'),
             'VDD': ('触摸板 3V3 + 麦克风 VDD', '接头：触摸板 3V3 线剪开，左耳和后脑的 VDD 焊进去，往下是小旗 17。'),
             'GND': ('麦克风 GND', '接头：左耳的 GND 杜邦线剪开，后脑的 GND 焊进去，往下是小旗 34。')}
    pins = []
    for i, (pid, (name, note)) in enumerate(names.items()):
        pins.append({'id': pid, 'label': pid, 'name': name, 'note': note, 'multi': True,
                     'role': 'ground' if pid == 'GND' else 'power' if pid == 'VDD' else 'signal',
                     'voltage': None if pid == 'GND' else 3.3, 'x': 4.5 + i * 7.0, 'y': H / 2})
    for p in pins:
        if p['voltage'] is None:
            del p['voltage']
    return {'id': 'gp', 'title': '集线点（头盖左后角）', 'subtitle': '四个焊接接头，套热缩管；在出线口正上方', 'short': '集线点',
            'drawing': {'kind': 'outline', 'color': '#eceff1', 'radius': 2,
                        'blocks': [{'x': 1.5 + i * 7.0, 'y': 1.5, 'w': 6.0, 'h': 6.0, 'color': '#cfd8dc'} for i in range(4)]},
            'width': W, 'height': H, 'pins': pins}


def openrb() -> dict:
    im = Image.open(PHOTOS / 'openrb_150_top.png').convert('RGB')
    W, H = 55.88, 133.67
    y0, y1 = 80.0, 112.0   # mm: J12 (96.4) with the board edge text around it
    crop = im.crop((0, round(y0 / H * im.height), im.width, round(y1 / H * im.height)))
    h = W * crop.height / crop.width
    k = h / (y1 - y0)
    pins = [{'id': 'Rx', 'label': 'Rx', 'name': 'J12 焊盘 3，印着 Rx（OpenRB 收）', 'role': 'signal', 'voltage': 3.3,
             'x': 25.26, 'y': round((96.38 - y0) * k, 3), 'note': '焊绿线，绿线另一头插 A7Z 7 号针。'},
            {'id': 'Tx', 'label': 'Tx', 'name': 'J12 焊盘 4，印着 Tx（OpenRB 发）', 'role': 'signal', 'voltage': 3.3,
             'x': 21.57, 'y': round((96.38 - y0) * k, 3), 'note': '焊白线，白线另一头插 A7Z 11 号针。'}]
    return {'id': 'orb', 'title': 'OpenRB-150（只画 J12 这一段）', 'subtitle': '躯干里的舵机控制板；J12 的 V、G 两个孔空着',
            'short': 'OpenRB', 'drawing': {'kind': 'svg', 'svg': TB.photo_svg(crop, W, h)}, 'width': W, 'height': round(h, 2),
            'pins': pins}


def xl2() -> dict:
    data = json.loads(GUIDE.read_text())
    src = next(s for s in data['steps'] if (s.get('wiring') or {}).get('bench'))['wiring']['bench']
    m = json.loads(json.dumps(next(x for x in src['modules'] if x['id'] == 'xl2')))
    zh = {'INP': ('IN+', '15 V 进，不接 A7Z'), 'INN': ('IN−', '15 V 回，不接 A7Z'),
          'OUTP': ('OUT+', '5.00 V 出，红线去 A7Z 2 号针'), 'OUTN': ('OUT−', '黑线去 A7Z 6 号针')}
    m['pins'] = [dict(p, name=zh[p['id']][0], note=zh[p['id']][1]) for p in m['pins'] if p['id'] in ('OUTP', 'OUTN')]
    m.update(title='XL4015 #2：5.00 V', short='#2 5 V', subtitle='后面转换盒中间层；电池背包时换成背包里的 DFR1202，同样经 MR30 接到这两根线')
    return m


def bench() -> dict:
    a = a7z()
    mods = [a, imu(), openrb(), xl2(), amp(), TB.xiao(), mic('micl', '左耳麦克风', '左耳', '焊一根短线到 GND：左声道'),
            mic('micr', '右耳麦克风', '右耳', '焊一根短线到 VDD：右声道'),
            mic('micb', '后脑麦克风（可选）', '后脑', '焊一根短线到 GND：DIN3 线上的左声道'), gather()]
    for m in mods:
        if m['id'] == 'xiao':
            m['subtitle'] = '触摸板，头盖内顶中间'
    # A7Z turned a quarter clockwise: its 65 mm length runs across, the header along the bottom edge, pin 1 at the right.
    aw, ah = a['height'], a['width']
    row = ah + 42
    place = [
        {'module': 'a7z', 'x': 0, 'y': 0, 'rotation': 90},
        # One row under the header, left to right in the order of the pins each board uses (pin 40 is at the left end);
        # the robot's left is the left of the drawing, so the left ear sits at the far left:
        # the head boards come down the neck to the left half, the torso boards come up through the saddle floor.
        {'module': 'micl', 'x': -50, 'y': row},
        {'module': 'micr', 'x': -26, 'y': row + 14},
        {'module': 'micb', 'x': -38, 'y': row + 34},
        {'module': 'gp', 'x': -52, 'y': row - 26},
        {'module': 'amp', 'x': -2, 'y': row},
        {'module': 'xiao', 'x': 24, 'y': row},
        {'module': 'imu', 'x': 50, 'y': row},
        {'module': 'xl2', 'x': aw + 20, 'y': -4},
        {'module': 'orb', 'x': 40, 'y': row + 34},
    ]
    return {'modules': mods, 'placements': place, 'groups': GROUPS,
            'wires': [{'id': i, 'from': f, 'to': t, 'color': c, 'group': g, 'label': lab, 'note': note}
                      for i, f, t, c, g, lab, note in WIRES]}


TEXT = TB.TEXT.replace("hint:'点一下针脚或导线看详情。'", "hint:'点一块板子：只亮它的线。点针脚或导线看详情。'")


# One button per board under the view: on a phone the boards are too small to tap reliably (a tap lands on a pin).
PICKS = [('micl', '左耳麦克风'), ('micr', '右耳麦克风'), ('micb', '后脑麦克风'), ('gp', '集线点'), ('amp', '功放'), ('xiao', '触摸板'), ('imu', 'IMU'),
         ('orb', 'OpenRB 串口'), ('xl2', '5 V 电源')]
PICK_CSS = ('.a7zpick{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 0}'
            '.a7zpick button{font-size:16px;padding:6px 12px;border-radius:18px;border:1px solid #90a4ae;background:#fff;cursor:pointer}'
            '.a7zpick button[aria-pressed="true"]{background:#1557b0;border-color:#1557b0;color:#fff}')


def html(host_id: str = 'a7z-bench') -> str:
    css = (TB.WK / 'wiring-kit.css').read_text()
    js = (TB.WK / 'wiring-kit.js').read_text().replace('</script', '<\\/script')
    data = json.dumps(bench(), ensure_ascii=False).replace('</', '<\\/')
    picks = ''.join(f'<button type="button" data-pick="{m}" aria-pressed="false">{t}</button>' for m, t in PICKS)
    sync = ('function(s){document.querySelectorAll(".a7zpick button").forEach(function(b){'
            'b.setAttribute("aria-pressed",String(!!(s.selection&&s.selection.kind==="module"&&s.selection.id===b.dataset.pick)));});}')
    return (f'<style>{css}{PICK_CSS}</style><div class="wkhost" id="{host_id}"></div>'
            f'<div class="a7zpick"><button type="button" data-pick="" aria-pressed="false">全部</button>{picks}</div>'
            f'<script>{js}</script>'
            f'<script>window.a7zBench=WiringKit.render(document.getElementById("{host_id}"),{data},'
            f'{{text:{TEXT},onChange:{sync},pinLabel:(pin,m)=>m.id==="a7z"?pin.label+" 号":pin.label}});'
            'document.querySelectorAll(".a7zpick button").forEach(function(b){b.addEventListener("click",function(){'
            'window.a7zBench.select(b.dataset.pick||null);});});</script>')


if __name__ == '__main__':
    b = bench()
    print(json.dumps({m['id']: [m['width'], m['height'], len(m['pins'])] for m in b['modules']}))
