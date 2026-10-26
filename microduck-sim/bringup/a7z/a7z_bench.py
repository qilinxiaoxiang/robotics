"""wiring-kit bench for A7Z-PINS.html: every board that connects to the A7Z 40-pin header, as wired in the roof saddle.

The A7Z is drawn as seen from above in the V2 saddle (D-028) with the robot's nose pointing up the page: component side
up, the header along the FRONT edge (top of the drawing), pin 1 at the left-hand (+Y, robot left) end with the antenna
and fan sockets, the USB-C and micro HDMI sockets along the rear edge (bottom). That is the portrait photo of photos.py
turned a quarter turn anticlockwise (wiring-kit rotation 270). The boards sit in a row above the header, in front of it
like the neck and the floor cut they come from: torso boards on the pin-1 (left) half, head boards on the pin-40 half.

Wires and pins: the assembly guide (guide/data/guide-data.json steps saddle-plugs and saddle-head-plugs; mics and
mic-splice for the microphones, mic-back for the optional back microphone), with the shared lines on the mini breadboard
taped to the camera back (A7Z-SOLDER, 2026-10-26). The breadboard is one module with one pin per strip: the amplifier BCLK
and LRC, the XIAO 3V3 and the right microphone's SCK, WS and VDD plug into the yellow, green and red strips, and each strip
goes down to pin 12, 35 or 17 on one male-to-female wire. The right microphone's five wires also end on the left
microphone's pads. The left SD goes straight to pin 38 and, with two microphones, the left GND straight to pin 34; with the
back microphone, its SCK, WS and VDD join the same strips, its GND and the right GND the black strip, and the black strip
goes to pin 34 instead; the back SD ends on a flag-10 plug taped beside pin 10, drawn to
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
    ('abclk', 'amp.BCLK', 'bb.SCK', ORG, 'audio', '功放 BCLK → 面包板黄条', '带公头的线，插面包板黄条，和麦克风的 SCK 连通。'),
    ('gsck', 'bb.SCK', 'a7z.p12', ORG, 'audio', '面包板黄条 → A7Z 12 号针', '小旗 12。30 cm 公对母杜邦线，不剪：公头插黄条，母头插 12 号针。'),
    ('alrc', 'amp.LRC', 'bb.WS', PUR, 'audio', '功放 LRC → 面包板绿条', '带公头的线，插面包板绿条，和麦克风的 WS 连通。'),
    ('gws', 'bb.WS', 'a7z.p35', PUR, 'audio', '面包板绿条 → A7Z 35 号针', '小旗 35。30 cm 公对母杜邦线，不剪。'),
    ('agnd', 'amp.GND', 'a7z.p39', BLK, 'audio', '功放 GND → A7Z 39 号针', '小旗 39。'),
    ('adin', 'amp.DIN', 'a7z.p40', TEAL, 'audio', '功放 DIN → A7Z 40 号针', '小旗 40，A7Z 送给功放的声音数据。'),
    ('t3v3', 'xiao.3V3', 'bb.VDD', RED, 'touch', '红：触摸板 3V3 → 面包板红条', '带公头的线，插面包板红条，和麦克风的 VDD 连通。'),
    ('gvdd', 'bb.VDD', 'a7z.p17', RED, 'touch', '红：面包板红条 → A7Z 17 号针（3.3 V）', '小旗 17。30 cm 公对母杜邦线，不剪。'),
    ('tgnd', 'xiao.GND', 'a7z.p25', BLK, 'touch', '黑：触摸板 GND → A7Z 25 号针', '小旗 25。'),
    ('tscl', 'xiao.D5', 'a7z.p29', BLU, 'touch', '蓝：触摸板 D5（SCL）→ A7Z 29 号针', '小旗 29。'),
    ('tsda', 'xiao.D4', 'a7z.p31', GRN, 'touch', '绿：触摸板 D4（SDA）→ A7Z 31 号针', '小旗 31。'),
    ('msd', 'micl.SD', 'a7z.p38', PINK, 'mic', '左耳麦克风 SD → A7Z 38 号针', '小旗 38，两个麦克风的数据线（I2S0 DIN0）。带插头的杜邦线。'),
    ('mgnd', 'micl.GND', 'a7z.p34', BLK, 'mic', '左耳麦克风 GND → A7Z 34 号针（双麦克风）',
     '小旗 34，一整根带插头的杜邦线。装了后脑麦克风就不要这根，34 号针改由面包板黑条下来。'),
    ('msck', 'micr.SCK', 'bb.SCK', ORG, 'mic', '右耳 SCK → 面包板黄条', '带公头的线。右耳离面包板最近，共用的线从右耳去面包板。'),
    ('mws', 'micr.WS', 'bb.WS', PUR, 'mic', '右耳 WS → 面包板绿条', '带公头的线。'),
    ('mvdd', 'micr.VDD', 'bb.VDD', RED, 'mic', '右耳 VDD → 面包板红条', '带公头的线（3.3 V）。'),
    ('rsck', 'micr.SCK', 'micl.SCK', ORG, 'mic', '右耳 SCK → 左耳 SCK', '两头都焊，跨过头盖内顶。'),
    ('rws', 'micr.WS', 'micl.WS', PUR, 'mic', '右耳 WS → 左耳 WS', '两头都焊。'),
    ('rsd', 'micr.SD', 'micl.SD', PINK, 'mic', '右耳 SD → 左耳 SD', '两头都焊。两个麦克风共用一根数据线，左右声道由 L/R 焊盘分开。'),
    ('rvdd', 'micr.VDD', 'micl.VDD', RED, 'mic', '右耳 VDD → 左耳 VDD', '两头都焊。'),
    ('rgnd', 'micr.GND', 'micl.GND', BLK, 'mic', '右耳 GND → 左耳 GND', '两头都焊。'),
    ('bsck', 'micb.SCK', 'bb.SCK', ORG, 'micb', '后脑麦克风 SCK → 面包板黄条', '可选。带公头的线。'),
    ('bws', 'micb.WS', 'bb.WS', PUR, 'micb', '后脑麦克风 WS → 面包板绿条', '可选。带公头的线。'),
    ('bvdd', 'micb.VDD', 'bb.VDD', RED, 'micb', '后脑麦克风 VDD → 面包板红条', '可选。带公头的线（3.3 V）。'),
    ('bgnd', 'micb.GND', 'bb.GND', BLK, 'micb', '后脑麦克风 GND → 面包板黑条', '可选。带公头的线。'),
    ('rgndb', 'micr.GND', 'bb.GND', BLK, 'micb', '右耳 GND → 面包板黑条（三个麦克风）', '可选。装后脑麦克风时右耳 GND 焊盘再焊一根带公头的线插黑条。'),
    ('ggnd', 'bb.GND', 'a7z.p34', BLK, 'micb', '面包板黑条 → A7Z 34 号针（三个麦克风）', '可选。小旗 34，30 cm 公对母杜邦线；这时左耳那根整根 GND 不要。'),
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
    12: 'I2S0 BCLK：面包板黄条（功放 BCLK + 麦克风 SCK）', 17: '3.3 V：面包板红条（触摸板 3V3 + 麦克风 VDD）', 25: '触摸板 GND',
    29: 'PB2 · 触摸板 SCL（TWI0）', 31: 'PB3 · 触摸板 SDA（TWI0）',
    35: 'I2S0 LRCK：面包板绿条（功放 LRC + 麦克风 WS）', 38: 'I2S0 DIN0：麦克风 SD', 39: '功放 GND', 40: 'I2S0 DOUT0：功放 DIN',
    34: '麦克风 GND（双麦克风：左耳一整根；三个：面包板黑条）',
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
    m['subtitle'] = '背包座里，从上往下看，机器人的头朝上：排针在前沿（图的上边），1 号针在左端（机器人左边）'
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
        p['multi'] = mid in ('micl', 'micr')   # chain wire plus its own wire (or the breadboard wire) on one pad
        if p['id'] == 'L/R':
            p['note'] = lr
    return m


def breadboard() -> dict:
    """The 25-hole mini breadboard on the camera back, landscape, seen from behind: one pin per strip in use."""
    W, H = 20.0, 15.0
    names = {'SCK': ('黄条：功放 BCLK + 麦克风 SCK', '面包板黄条，往下一根公对母线到 12 号针。'),
             'WS': ('绿条：功放 LRC + 麦克风 WS', '面包板绿条，往下一根公对母线到 35 号针。'),
             'VDD': ('红条：触摸板 3V3 + 麦克风 VDD', '面包板红条，往下一根公对母线到 17 号针。'),
             'GND': ('黑条：麦克风 GND（只在三个麦克风时用）', '右耳和后脑的 GND 插这里，往下一根公对母线到 34 号针。')}
    pins = []
    for i, (pid, (name, note)) in enumerate(names.items()):
        pins.append({'id': pid, 'label': pid, 'name': name, 'note': note, 'multi': True,
                     'role': 'ground' if pid == 'GND' else 'power' if pid == 'VDD' else 'signal',
                     'x': 3.5, 'y': 2.5 + i * 2.54 * 1.25})
        if pid != 'GND':
            pins[-1]['voltage'] = 3.3
    blocks = [{'x': 2.0 + j * 3.4, 'y': 1.3 + i * 3.17, 'w': 2.2, 'h': 2.2, 'color': '#5d4037' if j < 4 and i < 4 else '#bdbdbd'}
              for i in range(5) for j in range(5)]
    return {'id': 'bb', 'title': '迷你面包板（摄像头背面）', 'subtitle': '横贴在摄像头板背面、插头右边；从后面插杜邦公头，同一条的孔连通', 'short': '面包板',
            'drawing': {'kind': 'outline', 'color': '#ffe082', 'radius': 1.5, 'blocks': blocks},
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
            mic('micb', '后脑麦克风（可选）', '后脑', '焊一根短线到 GND：DIN3 线上的左声道'), breadboard()]
    for m in mods:
        if m['id'] == 'xiao':
            m['subtitle'] = '触摸板，头盖内顶中间'
    # A7Z turned a quarter anticlockwise (V2 saddle): its 65 mm length runs across, the header along the top edge, pin 1 at the
    # left. The boards are laid out as a half turn of the bottom row used for the V1.29 drawing (header at the bottom, pin 1 at
    # the right), so each board still faces the pins it uses, now from above; the two ears swap places so the left ear is the
    # left one of the pair.
    aw, ah = a['height'], a['width']
    size = {m['id']: (m['width'], m['height']) for m in mods}
    row = ah + 42
    below = [  # V1.29 layout under a header at the bottom edge (pin 40 at the left end)
        ('micl', -26, row + 16), ('micr', -50, row + 30), ('micb', -38, row + 50), ('bb', -27, row - 4),
        ('amp', -2, row), ('xiao', 24, row), ('imu', 50, row), ('xl2', aw + 20, -4), ('orb', 40, row + 34),
    ]
    place = [{'module': 'a7z', 'x': 0, 'y': 0, 'rotation': 270}]
    for mid, x, y in below:
        w, h = size[mid]
        place.append({'module': mid, 'x': round(aw - x - w, 2), 'y': round(ah - y - h, 2)})
    return {'modules': mods, 'placements': place, 'groups': GROUPS,
            'wires': [{'id': i, 'from': f, 'to': t, 'color': c, 'group': g, 'label': lab, 'note': note}
                      for i, f, t, c, g, lab, note in WIRES]}


TEXT = TB.TEXT.replace("hint:'点一下针脚或导线看详情。'", "hint:'点一块板子：只亮它的线。点针脚或导线看详情。'")


# One button per board under the view: on a phone the boards are too small to tap reliably (a tap lands on a pin).
PICKS = [('micl', '左耳麦克风'), ('micr', '右耳麦克风'), ('micb', '后脑麦克风'), ('bb', '面包板'), ('amp', '功放'), ('xiao', '触摸板'), ('imu', 'IMU'),
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
