#!/usr/bin/env python3
"""Build ../A7Z-SOLDER.html (three microphones: both ears and the optional back one) and ../A7Z-SOLDER-2MIC.html (the two
ears only): the head wiring as a soldering sequence, one board per step, and for every pad all the wires that go into it
at once, each with its cut length and kind (bare, female plug kept, male plug kept). The shared lines (SCK, WS, 3.3 V and
the three-microphone GND) join on strips of a mini breadboard on the camera back instead of soldered joints.

Lengths come from head-wire-lengths.json (head_wire_lengths.py, pickup-bend slack) and the guide's wire list (speaker and
touch pad leads). Run:  python3 build_a7z_solder.py
"""
from __future__ import annotations

import html
import json
import re

from PIL import Image, ImageDraw, ImageFont

import build_a7z_pages as AP
import photos as P

HERE = AP.HERE
OUTS = {True: HERE.parent / 'A7Z-SOLDER.html', False: HERE.parent / 'A7Z-SOLDER-2MIC.html'}   # key: back microphone fitted
HW = AP.HW
HWW = AP.HWW
F = P.FONT

# ---------------------------------------------------------------- lengths
PICK = lambda c: HWW[c]['cut']['whole']['pickup']                       # whole wire with one female plug
BB = HW['breadboard']
TOB = lambda k: BB['toBoard'][k]                                        # piece into the breadboard, male pin kept
NEED = lambda pin: BB['boardToPin'][str(pin)]                           # breadboard to pin, one uncut male-to-female wire
MF = 300                                                                # that wire: a stock 30 cm male-to-female Dupont
MR = HW['micPieces']['mic-r']                                           # right ear to left ear, bare
LINK = 15                                                               # bare L/R link
GND_WHOLE = PICK('mic-gnd')                                             # left ear GND straight to pin 34 (two microphones)
assert all(NEED(p) <= MF - 20 for p in (12, 35, 17, 34)), 'a 30 cm male-to-female wire no longer reaches'


def guide_items() -> list[str]:
    d = json.loads(AP.GUIDE_DATA.read_text())
    return [x['item'] for x in next(st for st in d['steps'] if st['id'] == 'wire-list')['prepare']]


ITEMS = guide_items()
SPK = int(next(re.search(r'(\d+) mm each, red and black', i).group(1) for i in ITEMS if i.startswith('Speaker leads')))
TOUCH = {k: int(v) for k, v in re.findall(r'(L1|R1|L2|R2|M) (\d+)', next(i for i in ITEMS if i.startswith('Touch pad leads')))}

COL = {'SCK': ('#c99a00', '黄'), 'WS': ('#1f9d55', '绿'), 'SD': ('#1f6fd1', '蓝'), 'VDD': ('#d7263d', '红'),
       'GND': ('#1d1d1f', '黑'), 'L/R': ('#78909c', '灰')}


# ---------------------------------------------------------------- wire phrases
def bare(mm: int, col: str = '') -> str:
    c = f'（{col}）' if col else ''
    return f'新取一根 <b>{mm} mm 细线</b>{c}'


def plug(mm: int, flag: int, col: str = '') -> str:
    c = f'{col}，' if col else ''
    return f'新取一根 <b>{mm} mm 带母头的线</b>（{c}小旗 {flag}）'


def male(mm: int, col: str, strip: str) -> str:
    return f'新取一根 <b>{mm} mm 带公头的线</b>（{col}），公头插面包板{strip}'


def link_end(which: str) -> str:
    return f'{LINK} mm 短线的{which}'


def pad_list(rows, cols: dict | None = None) -> str:
    """rows: [(number, pad, [wire phrase, ...], note)]; every wire that goes into the pad is listed at once.
    cols: number -> badge colour, else the signal colour of the pad name."""
    out = []
    for no, pad, wires, note in rows:
        col = (cols or {}).get(no) or COL.get(pad, ('#455a64', ''))[0]
        if not wires:
            body = '<b>空着，不焊。</b>'
        else:
            n = len(wires)
            body = (f'<b>一次焊 {n} 根：</b>' if n > 1 else '') + '；'.join(
                (f'{"①②③④"[i]} ' if n > 1 else '') + w for i, w in enumerate(wires)) + '。'
        nt = f'<div class="src">{note}</div>' if note else ''
        out.append(f'<li><span class="dot" style="background:{col}">{no}</span><span><b>{html.escape(pad)}</b> ── {body}{nt}</span></li>')
    return f'<ul class="legend pads">{"".join(out)}</ul>'


# ---------------------------------------------------------------- figures
def font(n): return ImageFont.truetype(F, n)


def badge(d, xy, text, fill, r=30):
    x, y = xy
    d.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline='white', width=4)
    d.text((x, y), text, font=font(34 if len(text) < 2 else 28), fill='white', anchor='mm')


def mic_face(title: str, rows: dict, link_to: str) -> Image.Image:
    """The INMP441 solder face (no print; left and right swapped against the label face), pads numbered as in the list."""
    W, H, R = 900, 980, 380
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, 500
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill='#202124')
    d.arc((cx - R + 24, cy - R + 24, cx + R - 24, cy + R - 24), 120, 240, fill='#d2a679', width=20)
    d.arc((cx - R + 24, cy - R + 24, cx + R - 24, cy + R - 24), -60, 60, fill='#d2a679', width=20)
    s = 2 * R / 416
    pos = {}
    for pad, x, y in AP.AB.MIC_PADS:                     # label-face pixel coordinates, mirrored for the solder face
        pos[pad] = (cx + (416 - x - 208) * s, cy + (y - 208) * s)
    (lx, ly), (tx, ty) = pos['L/R'], pos[link_to]
    side = cx - 0.62 * R                                 # the link runs down the board edge, clear of the pad names
    d.line(((lx, ly), (side, ly + 40), (side, ty - 40), (tx, ty)), fill='#b0bec5', width=12, joint='curve')
    d.rounded_rectangle((cx - 80, cy - 60, cx + 80, cy + 60), 10, fill='#9e9e9e', outline='#cfd8dc', width=4)
    d.text((cx, cy), '金属壳', font=font(34), fill='#263238', anchor='mm')
    for pad, (x, y) in pos.items():
        col = COL[pad][0]
        d.ellipse((x - 38, y - 38, x + 38, y + 38), fill='#d2a679', outline=col, width=10)
        d.ellipse((x - 12, y - 12, x + 12, y + 12), fill='#202124')
        up = y < cy
        d.text((x, y + (70 if up else -70)), pad, font=font(40), fill='white', anchor='mm', stroke_width=6, stroke_fill='#202124')
        badge(d, (x, y + (-88 if up else 88)), rows[pad], col, 34)
    d.text((cx, 40), title, font=font(42), fill='#1b1b1b', anchor='mm')
    d.text((cx, H - 30), f'灰线 = L/R 到 {link_to} 的 {LINK} mm 短线', font=font(36), fill='#546e7a', anchor='mm')
    return im


def amp_figure(rows: dict) -> Image.Image:
    src = Image.open(AP.AB.PHOTOS / 'max98357a_3006_top.jpg').convert('RGB')
    s = src.width / 17.8
    pads = {'LRC': 2.741, 'BCLK': 4.913, 'DIN': 6.995, 'GAIN': 9.12, 'SD': 11.2, 'GND': 13.314, 'Vin': 15.326}
    W = src.width
    im = Image.new('RGB', (W, src.height + 120), 'white')
    im.paste(src, (0, 0))
    d = ImageDraw.Draw(im)
    y = 15.3 * s
    for pad, x in pads.items():
        x *= s
        no, col = rows[pad]
        d.ellipse((x - 42, y - 42, x + 42, y + 42), outline='white', width=12)
        d.ellipse((x - 38, y - 38, x + 38, y + 38), outline=col, width=7)
        d.line((x, y + 44, x, src.height + 40), fill=col, width=5)
        badge(d, (x, src.height + 62), no, col, 34)
    for sign, x, no in (('−', 330, 'A'), ('+', 510, 'B')):
        badge(d, (x, 105), no, '#6d4c41', 34)
    return im


def xiao_figure(rows) -> Image.Image:
    full = {'D0': (480, 108), 'D1': (480, 186), 'D2': (480, 264), 'D3': (480, 344), 'D4': (480, 424), 'D5': (480, 504),
            'D6': (480, 582), 'VBUS': (960, 108), 'GND': (960, 186), '3V3': (960, 264), 'D10': (960, 344),
            'D9': (960, 424), 'D8': (960, 504), 'D7': (960, 582)}
    im = Image.open(P.HERE / 'sources' / 'xiao-esp32s3-front-pinout-crop.png').convert('RGB')
    marks = []
    for pad, (no, col) in rows.items():
        x, y = full[pad]
        lx = x + 82 if x < im.width / 2 else x - 82
        marks.append((no, (x, y), (lx, y), 26, col, col))
    return P.draw_marks(im, marks)


def wire_types() -> Image.Image:
    W, H = 1300, 960
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    f, fs = font(38), font(30)

    def wire(y, x0, x1, col):
        d.line((x0, y, x1, y), fill=col, width=16)

    def stripped(x, y, left=True):
        a, b = (x - 40, x) if left else (x, x + 40)
        d.line((a, y, b, y), fill='#b87333', width=6)

    def female(x, y):
        d.rectangle((x, y - 20, x + 120, y + 20), fill='#263238')
        d.rectangle((x + 120, y - 12, x + 130, y + 12), fill='#90a4ae')

    def male_end(x, y):
        d.rectangle((x, y - 20, x + 110, y + 20), fill='#263238')
        d.line((x + 110, y, x + 150, y), fill='#cfd8dc', width=8)

    def ruler(y, x0, x1, text):
        d.line((x0, y, x1, y), fill='#546e7a', width=3)
        for x in (x0, x1):
            d.line((x, y - 15, x, y + 15), fill='#546e7a', width=3)
        d.text(((x0 + x1) / 2, y + 28), text, font=fs, fill='#546e7a', anchor='mm')
    d.text((40, 40), '细线：杜邦线两头的插头都剪掉', font=f, fill='#1b1b1b')
    wire(130, 140, 1100, '#c99a00'); stripped(140, 130); stripped(1100, 130, False)
    ruler(175, 100, 1140, '长度 = 剪好以后整根量（含两头剥出来的铜丝）')
    d.text((40, 260), '带母头的线：母头杜邦线剪掉另一头，母头最后插 A7Z', font=f, fill='#1b1b1b')
    wire(350, 140, 1020, '#1f6fd1'); stripped(140, 350); female(1020, 350)
    ruler(395, 100, 1150, '长度 = 从剪口的铜丝头量到插头尖（含插头）')
    d.text((40, 480), '带公头的线：公头杜邦线剪掉另一头，公头插面包板', font=f, fill='#1b1b1b')
    wire(570, 140, 1000, '#d7263d'); stripped(140, 570); male_end(1000, 570)
    ruler(615, 100, 1150, '长度 = 从剪口的铜丝头量到公针尖（含插头）')
    d.text((40, 700), f'公对母整根：{MF // 10} cm 公对母杜邦线，不剪', font=f, fill='#1b1b1b')
    d.rectangle((140, 770, 250, 810), fill='#263238')
    d.line((100, 790, 140, 790), fill='#cfd8dc', width=8)
    wire(790, 250, 1000, '#1f9d55'); female(1000, 790)
    d.text((195, 845), '公头：插面包板', font=fs, fill='#263238', anchor='mm')
    d.text((1060, 845), '母头：插 A7Z', font=fs, fill='#263238', anchor='mm')
    d.text((620, 910), '从面包板到 A7Z 针的线，多出来的在面包板旁边折一下贴住', font=fs, fill='#546e7a', anchor='mm')
    return im


def bb_figure(strips) -> Image.Image:
    """The breadboard from behind (robot left on the left), landscape, 5 x 5 holes; two panels for the two ways the
    strips can run. strips: [(colour, name, [hole letter, ...])], top strip first; the first letter of each is the wire
    down to the A7Z."""
    P, R = 110, 32
    W, H = 1500, 940
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    for k, (ox, title) in enumerate(((40, '量出来是“横着通”（一排 5 个孔连在一起）'), (780, '量出来是“竖着通”（一列 5 个孔连在一起）'))):
        d.text((ox + 340, 40), title, font=font(30), fill='#1b1b1b', anchor='mm')
        d.rounded_rectangle((ox, 130, ox + 680, 130 + 520), 24, fill='#f3f0e8', outline='#9e9e9e', width=4)
        x0, y0 = ox + 340 - 2 * P, 130 + 260 - 2 * P
        for i in range(5):
            for j in range(5):
                x, y = x0 + j * P, y0 + i * P
                d.ellipse((x - R, y - R, x + R, y + R), fill='#cfcfcf')
        for si, (col, name, holes) in enumerate(strips):
            for hi, t in enumerate(holes):
                i, j = (si, hi) if k == 0 else (hi, si)
                x, y = x0 + j * P, y0 + i * P
                d.ellipse((x - R - 6, y - R - 6, x + R + 6, y + R + 6), fill=col)
                d.text((x, y), t, font=font(34), fill='white', anchor='mm', stroke_width=3, stroke_fill='#1b1b1b')
            i0, j0 = (si, 0) if k == 0 else (0, si)
            a, b = (x0 + j0 * P, y0 + i0 * P)
            if k == 0:
                d.line((a - R, b, a - R - 30, b), fill=col, width=8)
            else:
                d.line((a, b - R, a, b - R - 30), fill=col, width=8)
        d.text((ox + 340, 680), '灰孔空着。从机器人后面看，左边是机器人的左边', font=font(26), fill='#546e7a', anchor='mm')
    y = 740
    for col, name, holes in strips:
        d.ellipse((60, y - 18, 96, y + 18), fill=col)
        d.text((120, y), name, font=font(30), fill='#1b1b1b', anchor='lm')
        y += 48
    return im


def fig(im, alt, cap, cls=''):
    return AP.figure(AP.uri(im, 1100), alt, cap, cls=cls)


# ---------------------------------------------------------------- steps
BACK = True          # set per page in main(): the back microphone is fitted
N: dict = {}         # step anchor -> step number on the current page


def no(key: str) -> str:
    return f'第 {N[key]} 步'


def note_top() -> str:
    other = ('<p><b>只装两只耳朵：</b>用 <a href="A7Z-SOLDER-2MIC.html">双麦克风版</a>，没有后脑那一步，面包板只用 3 条。</p>' if BACK else
             '<p><b>这是双麦克风版：</b>只有左右两只耳朵，像动物一样两只耳朵听声音。头盖后壁的第三个麦克风座空着。三个麦克风的版本在 <a href="A7Z-SOLDER.html">A7Z-SOLDER</a>。</p>')
    return f"""
<div class="card">
<p><b>怎么用这一页：</b>一步一块板子。每个焊盘后面写着<b>这个焊盘一共要焊几根线、各是哪根</b>，同一个焊盘的线一次焊上，不会再回来加。每根线写清楚多长、是哪种线、另一头去哪。</p>
<p><b>不焊接头，用面包板合线：</b>功放、触摸板和麦克风共用的线（时钟 SCK、左右时钟 WS、3.3 V{"、麦克风 GND" if BACK else ""}）以前在头盖左后角焊成接头，头盖和下面的板子就焊死在一起了。现在每根线末端留一个杜邦公头，插进摄像头背面的迷你面包板；同一条上的孔是连通的，就等于接在一起。要拆头盖，拔插头就行。</p>
<p><b>四种线（{no('s0')}有图）：</b><b>细线</b> = 两头插头都剪掉；<b>带母头的线</b> = 剪掉一头，留母头，最后插 A7Z；<b>带公头的线</b> = 剪掉一头，留公头，插面包板；<b>公对母整根</b> = {MF // 10} cm 公对母杜邦线不剪，从面包板到 A7Z。长度含插头，都按低头叼东西留够了余量。</p>
<p><b>颜色建议</b>（跟组装指南一样，方便以后认）：SCK / BCLK 黄，WS / LRC 绿，SD / DIN 蓝，VDD / 3V3 / Vin 红，GND 黑。带母头的线剪完马上贴小旗，写 A7Z 针号。</p>
<p><b>已经焊过线的板子</b>（功放、XIAO 可能已经焊好了）：每根量一下，比这里写的长或一样长就留着；短了就拆下来换一根。功放的 BCLK、LRC 和 XIAO 的 3V3 现在要换成带公头的线，见{no('s5')}、{no('s6')}。</p>
<p><b>焊在哪一面：</b>线从有元件的那面插进孔，在另一面上锡。麦克风印字那面贴头盖内壁，焊点要小要平，穿出来的铜丝剪齐，中间的声孔别沾锡。</p>
{other}
</div>"""


def strips():
    """Breadboard strips, top first: (colour, legend, hole letters); the first hole is the wire down to the A7Z."""
    y, g, r, k = COL['SCK'][0], COL['WS'][0], COL['VDD'][0], COL['GND'][0]
    b = lambda: ['后'] if BACK else []
    out = [(y, '黄条 SCK：针 = 往下 12 号针，功 = 功放 BCLK，右 = 右耳 SCK' + ('，后 = 后脑 SCK' if BACK else ''), ['针', '功', '右', *b()]),
           (g, '绿条 WS：针 = 往下 35 号针，功 = 功放 LRC，右 = 右耳 WS' + ('，后 = 后脑 WS' if BACK else ''), ['针', '功', '右', *b()]),
           (r, '红条 3.3 V：针 = 往下 17 号针，X = XIAO 3V3，右 = 右耳 VDD' + ('，后 = 后脑 VDD' if BACK else ''), ['针', 'X', '右', *b()])]
    if BACK:
        out.append((k, '黑条 GND：针 = 往下 34 号针，右 = 右耳 GND，后 = 后脑 GND', ['针', '右', '后']))
    return out


def s0():
    bares = [(MR, 5, '右耳到左耳'), (LINK, 3 if BACK else 2, 'L/R 短线，每个麦克风一根'), (SPK, 2, '喇叭（红、黑）')]
    lis = ''.join(f'<li>{mm} mm 细线 × {n}：{what}</li>' for mm, n, what in bares)
    lis += f'<li>铜箔引线（XIAO 到 5 块铜箔）：{"、".join(f"{k} {v}" for k, v in TOUCH.items())} mm，各一根细线</li>'
    ml = [(TOB('mic-r'), 4 if BACK else 3, '右耳 SCK、WS、VDD' + ('、GND' if BACK else ''))] + (
        [(TOB('mic-b'), 4, '后脑 SCK、WS、VDD、GND')] if BACK else []) + [
        (TOB('amp-bclk'), 1, '功放 BCLK'), (TOB('amp-lrc'), 1, '功放 LRC'), (TOB('touch-pin17'), 1, 'XIAO 3V3')]
    lism = ''.join(f'<li>{mm} mm × {n}：{what}</li>' for mm, n, what in ml)
    pl = [(PICK('mic-sd'), 38, '左耳 SD')] + ([(PICK('mic-sd3'), 10, '后脑 SD')] if BACK else [(GND_WHOLE, 34, '左耳 GND')]) + [
          (PICK('amp-vin'), 4, '功放 Vin'), (PICK('amp-gnd'), 39, '功放 GND'), (PICK('amp-din'), 40, '功放 DIN'),
          (PICK('touch-pin25'), 25, 'XIAO GND'), (PICK('touch-pin29'), 29, 'XIAO D5 / SCL'), (PICK('touch-pin31'), 31, 'XIAO D4 / SDA')]
    lis2 = ''.join(f'<li>{mm} mm，小旗 {flag}：{what}</li>' for mm, flag, what in pl)
    downs = [12, 35, 17] + ([34] if BACK else [])
    lisd = ''.join(f'<li>小旗 {p}：面包板到 {p} 号针要 {NEED(p)} mm，多 {MF - NEED(p)} mm</li>' for p in downs)
    return AP.step('s0', no('s0'), '认四种线，剥皮', '你知道四种线各是什么，长度怎么量。', f"""
{fig(wire_types(), '四种线', '细线两头剥皮；带母头、带公头的线只剥剪口那头，长度含插头；公对母整根不剪。')}
<ul class="acts">
<li>剥皮：焊到焊盘上的线头剥 2 到 3 mm。</li>
<li>先上锡：剥好的铜丝拧紧，沾一点锡再焊，好焊很多。</li>
<li>线可以每一步现剪，也可以按下面的清单一次剪好。</li>
</ul>
<details><summary>一次剪好的清单（可选）</summary>
<p><b>细线</b></p><ul class="acts">{lis}</ul>
<p><b>带公头的线</b>（插面包板）</p><ul class="acts">{lism}</ul>
<p><b>带母头的线</b>（剪完贴小旗）</p><ul class="acts">{lis2}</ul>
<p><b>公对母整根，不剪</b>（{MF // 10} cm，{len(downs)} 根，贴小旗）</p><ul class="acts">{lisd}</ul>
</details>""")


def s1():
    gnd = [bare(MR, '黑') + '，另一头去左耳 GND'] + ([male(TOB('mic-r'), '黑', '黑条')] if BACK else [])
    rows = [('1', 'SCK', [bare(MR, '黄') + '，另一头去左耳 SCK', male(TOB('mic-r'), '黄', '黄条')], ''),
            ('2', 'WS', [bare(MR, '绿') + '，另一头去左耳 WS', male(TOB('mic-r'), '绿', '绿条')], ''),
            ('3', 'SD', [bare(MR, '蓝') + '，另一头去左耳 SD'], ''),
            ('4', 'VDD', [bare(MR, '红') + '，另一头去左耳 VDD', male(TOB('mic-r'), '红', '红条'), f'新取一根 <b>{LINK} mm 细线</b>（短线）的一头'],
             '三根挤一个孔太紧的话：先焊前两根，短线这头搭在焊点上补一点锡。'),
            ('5', 'GND', gnd, ''), ('6', 'L/R', [link_end('另一头')], '右耳的 L/R 接 VDD：它是右声道。')]
    im = mic_face('右耳 INMP441，没字那面（焊线这面）', {p: n for n, p, *_ in rows}, 'VDD')
    nm = 4 if BACK else 3
    return AP.step('s1', no('s1'), f'右耳麦克风：5 根 {MR} mm 细线 + {nm} 根带公头 + 1 根短线',
                   f'右耳 6 个焊盘焊好；5 根细线去左耳，{nm} 根带公头的线去面包板，另一头都先空着。', f"""
<div class="pair"><div>{fig(im, '右耳 INMP441 焊线面', '没字那面（有金属壳那面）朝你，左右和印字那面是反的：上排 L/R、WS、SCK，下排 GND、VDD、SD。焊之前翻过去对着字认一遍。')}</div>
<div>{pad_list(rows)}<p>右耳离摄像头背面的面包板最近，所以共用的线从右耳去面包板；左耳只接右耳过来的线和自己去 A7Z 的线。带公头的线里含 25 mm 余量，头盖装好以后还能像盖子一样往后翻开。</p></div></div>""")


def s2():
    gnd = ['右耳 GND 线的另一头'] + ([] if BACK else [plug(GND_WHOLE, 34, '黑') + '，插头最后插 A7Z 34 号针']) + [
        f'新取一根 <b>{LINK} mm 细线</b>（短线）的一头']
    rows = [('1', 'SCK', ['右耳 SCK 线的另一头'], ''), ('2', 'WS', ['右耳 WS 线的另一头'], ''),
            ('3', 'SD', ['右耳 SD 线的另一头', plug(PICK('mic-sd'), 38, '蓝') + '，插头最后插 A7Z 38 号针'], ''),
            ('4', 'VDD', ['右耳 VDD 线的另一头'], ''),
            ('5', 'GND', gnd, '三根挤一个孔太紧的话：先焊前两根，短线这头搭在焊点上补一点锡。' if not BACK else ''),
            ('6', 'L/R', [link_end('另一头')], '左耳的 L/R 接 GND：它是左声道。')]
    im = mic_face('左耳 INMP441，没字那面（焊线这面）', {p: n for n, p, *_ in rows}, 'GND')
    out = '伸出去 1 根小旗 38 的带母头线' if BACK else '伸出去 2 根带母头线（小旗 38、34）'
    return AP.step('s2', no('s2'), '左耳麦克风：接右耳的 5 根 + 带母头线 + 1 根短线', f'左耳 6 个焊盘焊好；{out}。', f"""
<div class="pair"><div>{fig(im, '左耳 INMP441 焊线面', '同样是没字那面朝你。右耳过来的线焊到名字相同的焊盘上。')}</div>
<div>{pad_list(rows)}</div></div>""")


def s3():
    rows = [('1', 'SCK', [male(TOB('mic-b'), '黄', '黄条')], ''), ('2', 'WS', [male(TOB('mic-b'), '绿', '绿条')], ''),
            ('3', 'SD', [plug(PICK('mic-sd3'), 10, '蓝') + '，插头最后贴在 A7Z 10 号针旁边，先不插'], ''),
            ('4', 'VDD', [male(TOB('mic-b'), '红', '红条')], ''),
            ('5', 'GND', [male(TOB('mic-b'), '黑', '黑条'), f'新取一根 <b>{LINK} mm 细线</b>（短线）的一头'], ''),
            ('6', 'L/R', [link_end('另一头')], '后脑的 L/R 接 GND。')]
    im = mic_face('后脑 INMP441，没字那面（焊线这面）', {p: n for n, p, *_ in rows}, 'GND')
    return AP.step('s3', no('s3'), f'后脑麦克风：4 根带公头 + 1 根带母头 + 1 根短线', f'后脑 6 个焊盘焊好；伸出去 4 根 {TOB("mic-b")} mm 带公头的线和 1 根小旗 10 的带母头线。', f"""
<div class="pair"><div>{fig(im, '后脑 INMP441 焊线面', '和耳朵一样的板子，没字那面朝你。')}</div>
<div>{pad_list(rows)}</div></div>""")


def s4():
    spk = Image.open(AP.AB.PHOTOS / 'speaker_cms_30204_18sp_back.jpg').convert('RGB')
    rows = [('+', '喇叭 +', [bare(SPK, '红') + f"，另一头剥 5 mm，拧进功放绿色端子的 +（{no('s5')}图里 B）"], ''),
            ('−', '喇叭 −', [bare(SPK, '黑') + f"，另一头剥 5 mm，拧进功放绿色端子的 −（{no('s5')}图里 A）"], '')]
    return AP.step('s4', no('s4'), f'喇叭：2 根 {SPK} mm 细线', '喇叭两个焊盘各一根线，另一头拧在功放的绿色端子里（不焊）。', f"""
<div class="pair"><div>{fig(spk, '喇叭背面', '喇叭背面，两个焊盘在边上。焊盘旁有 + 标记就按它接；没有标记也能响，接反只是相位反。')}</div>
<div>{pad_list(rows)}<p>以前焊过喇叭线的：60 mm 以内都能用，更长就剪短。</p></div></div>""")


def s5():
    a = {'LRC': ('1', COL['WS'][0]), 'BCLK': ('2', COL['SCK'][0]), 'DIN': ('3', COL['SD'][0]), 'GAIN': ('4', '#9e9e9e'),
         'SD': ('5', '#9e9e9e'), 'GND': ('6', COL['GND'][0]), 'Vin': ('7', COL['VDD'][0])}
    rows = [('1', 'LRC', [male(TOB('amp-lrc'), '绿', '绿条')], ''),
            ('2', 'BCLK', [male(TOB('amp-bclk'), '黄', '黄条')], ''),
            ('3', 'DIN', [plug(PICK('amp-din'), 40, '蓝')], ''), ('4', 'GAIN', [], ''), ('5', 'SD', [], ''),
            ('6', 'GND', [plug(PICK('amp-gnd'), 39, '黑')], ''), ('7', 'Vin', [plug(PICK('amp-vin'), 4, '红')], ''),
            ('A', '绿色端子 −', ['喇叭黑线，剥 5 mm 插进去拧紧，不焊'], ''), ('B', '绿色端子 +', ['喇叭红线，剥 5 mm 插进去拧紧，不焊'], '')]
    pl = pad_list(rows, {**{n: c for n, c in a.values()}, 'A': '#6d4c41', 'B': '#6d4c41'})
    return AP.step('s5', no('s5'), '功放：2 根带公头 + 3 根带母头，GAIN、SD 空着', '功放焊好 5 根线，喇叭线拧进绿色端子。', f"""
<div class="pair"><div>{fig(amp_figure(a), 'MAX98357A 功放', '印字面朝你，焊盘在下边一排，从左到右 LRC、BCLK、DIN、GAIN、SD、GND、Vin。')}</div>
<div>{pl}
<div class="card"><b>以前已经焊好整根 BCLK、LRC（带母头）的：</b>母头插不进面包板，拆下来换成上面两根带公头的线。</div></div></div>""")


def s6():
    x = {'D0': ('1', '#b87333'), 'D1': ('2', '#b87333'), 'D2': ('3', '#b87333'), 'D3': ('4', '#b87333'), 'D8': ('5', '#b87333'),
         '3V3': ('6', COL['VDD'][0]), 'GND': ('7', COL['GND'][0]), 'D5': ('8', COL['SCK'][0]), 'D4': ('9', COL['WS'][0])}
    rows = [('1', 'D0', [bare(TOUCH['L1']) + '，另一头焊铜箔 L1 的角'], ''), ('2', 'D1', [bare(TOUCH['R1']) + '，另一头焊铜箔 R1'], ''),
            ('3', 'D2', [bare(TOUCH['L2']) + '，另一头焊铜箔 L2'], ''), ('4', 'D3', [bare(TOUCH['R2']) + '，另一头焊铜箔 R2'], ''),
            ('5', 'D8', [bare(TOUCH['M']) + '，另一头焊铜箔 M'], ''),
            ('6', '3V3', [male(TOB('touch-pin17'), '红', '红条')], ''),
            ('7', 'GND', [plug(PICK('touch-pin25'), 25, '黑')], ''), ('8', 'D5（SCL）', [plug(PICK('touch-pin29'), 29, '蓝')], ''),
            ('9', 'D4（SDA）', [plug(PICK('touch-pin31'), 31, '绿')], '')]
    pl = pad_list(rows, dict(x.values()))
    return AP.step('s6', no('s6'), 'XIAO 触摸板：5 根铜箔线 + 1 根带公头 + 3 根带母头', 'XIAO 焊好 9 根线；其余焊盘（VBUS、D6、D7、D9、D10）空着。', f"""
<div class="pair"><div>{fig(xiao_figure(x), 'XIAO ESP32-S3 正面', 'XIAO 正面，USB-C 口朝上。左列 D0 到 D6，右列 5V、GND、3V3、D10 到 D7。')}</div>
<div>{pl}
<div class="card"><b>你的 XIAO 已经焊好、能用了</b>（10/20 五个铜箔都试过）。只核对长度：GND、D5、D4 三根比上面写的短，就拆下换新的。红色 3V3 现在是一整根带母头的，拆下来换成 {TOB('touch-pin17')} mm 带公头的线（XIAO 就在摄像头上方，离面包板很近）。</div></div></div>""")


def s7():
    n = len(strips())
    mics = '三个麦克风' if BACK else '两只耳朵的麦克风'
    return AP.step('s7', no('s7'), '量面包板，贴到摄像头背面', f'面包板横着贴在摄像头板背面、插头右边；你知道它是横着通还是竖着通。{mics}、功放、喇叭、XIAO 按组装指南装好。', f"""
{AP.figure(AP.uri(Image.open(HERE / 'img' / 'breadboard_camera_back.png').convert('RGB'), 1100), '面包板在摄像头背面', '按组装指南的 CAD 画的。左：从机器人左边看；右：从后往前看摄像头背面。面包板横放，20 mm 那边水平，孔朝后；上面 4 排都能插，插头离下巴支架和 XIAO 至少 1.8 mm，板子离头盖 2 mm。')}
<ol class="acts">
<li><b>先量连通方向：</b>万用表打到蜂鸣档，两根表笔各插一个杜邦公头，插进同一排相邻两个孔，响了就是“横着通”；不响再试同一列上下两个孔，响了就是“竖着通”。记下来，{no('bb')}按它插。</li>
<li>面包板横着拿（20 mm 那边水平），孔朝后。底面撕掉背胶（或贴一层 3M 泡棉胶），贴在摄像头板背面、摄像头插头的右边（从机器人后面看）。上边和摄像头板上边齐平，别凸出去碰头盖。</li>
<li>面包板右边大约 10 mm 伸出摄像头板外面，粘住的只有左边 10 × 15 mm：贴之前用酒精擦干净摄像头板背面，按住 30 秒；插线时用手指在板子前面顶住。</li>
<li>板子按组装指南第 9 章装进头里。这一步不焊东西。</li>
<li>带母头的线经过面包板不停，直接走头盖左后角，从出线口出去，顺脖子左边下来。</li>
</ol>
<p>{n} 条要用，每条最多 {max(len(h) for *_, h in strips())} 个孔，所以只用左上角一块，最下面一排和最右边一列空着。</p>""")


def s_bb():
    downs = [12, 35, 17] + ([34] if BACK else [])
    im = bb_figure(strips())
    return AP.step('bb', no('bb'), '插面包板，贴 Kapton', f'所有带公头的线和 {len(downs)} 根公对母整根插好，一道 Kapton 压住，线束贴在头里。', f"""
{fig(im, '面包板插孔分配', '从机器人后面看面包板。按第 ' + str(N['s7']) + ' 步量出来的方向用左图或右图。每个彩色孔插一根线：“针”是往下到 A7Z 的公对母整根，其他字是哪块板子过来的。', cls='mid')}
<ol class="acts">
<li>每一条先插“针”那个孔：{MF // 10} cm 公对母整根，公头插面包板，母头贴小旗（{'、'.join(str(p) for p in downs)}）。</li>
<li>再把各板子过来的带公头的线插进同一条的其他孔，按图上的字。</li>
<li>插完一道 Kapton 胶带横着贴过所有插头的塑料壳，两头压到面包板侧面，防松脱。</li>
<li>线束在离面包板 1 到 2 cm 的地方用 Kapton 贴在摄像头板或面板背面，拉线时力在胶带上，不在插头上。</li>
<li>公对母整根比要的长：多出来的在面包板后面折一下，用 Kapton 贴住，再一起走头盖左后角，从出线口出去。</li>
</ol>
<p>要拆头盖：撕开 Kapton，把麦克风过来的公头拔出来就行，不用动烙铁。</p>""")


def s12():
    pins = [(4, '#d7263d'), (12, '#c99a00'), (17, '#d7263d'), (25, '#1d1d1f'), (29, '#1f6fd1'), (31, '#1f9d55'), (34, '#1d1d1f'),
            (35, '#1f9d55'), (38, '#1f6fd1'), (39, '#1d1d1f'), (40, '#1f6fd1')] + ([(10, '#9e9e9e')] if BACK else [])
    goal = '11 个插头插在 A7Z 上；小旗 10 贴在 10 号针旁边，不插。' if BACK else '11 个插头插在 A7Z 上，10 号针空着。'
    cap = 'A7Z 正面竖放（1 号针在上）。灰色的 10 号针先不插。' if BACK else 'A7Z 正面竖放（1 号针在上）。'
    mic = '麦克风：34、38；后脑的 10 先不插' if BACK else '麦克风：34、38'
    return AP.step('s12', no('s12'), '插到 A7Z：小旗几号就插几号针', goal, f"""
<div class="pair"><div>{AP.figure(AP.top_fig(pins), f'A7Z 上要插的 {len(pins)} 个针', cap)}</div>
<div><p>插法、怎么数针号、插完怎么检查，见 <a href="A7Z-PINS.html#audio">A7Z-PINS 第 6 到 8 步</a>。</p>
<ul class="acts"><li>面包板下来的：12、35、17{'、34' if BACK else ''}</li><li>功放：4、39、40</li><li>触摸板：25、29、31</li><li>{mic}</li></ul></div></div>""")


ORDER = [('s0', '四种线'), ('s1', '右耳'), ('s2', '左耳'), ('s3', '后脑'), ('s4', '喇叭'), ('s5', '功放'), ('s6', 'XIAO'),
         ('s7', '贴面包板'), ('bb', '插面包板'), ('s12', '插 A7Z')]


def build(back: bool) -> None:
    global BACK, N
    BACK = back
    order = [(k, t) for k, t in ORDER if back or k != 's3']
    N = {k: i for i, (k, _) in enumerate(order)}
    steps = [s0(), s1(), s2(), *([s3()] if back else []), s4(), s5(), s6(), s7(), s_bb(), s12()]
    nav = [(k, f'{N[k]} {t}') for k, t in order]
    lead = (f"<p class=\"lead\">头里的线一步一步怎么焊：先焊每块板子（第 1 到 {N['s6']} 步），面包板贴到摄像头背面（{no('s7')}），"
            f"共用的线插进面包板（{no('bb')}），最后插到 A7Z（{no('s12')}）。不再有焊接接头，头盖拔插头就能拆。"
            '为什么是这些长度见 <a href="A7Z-PINS.html#changes">A7Z-PINS“现在的装法”</a>。</p>')
    title = 'A7Z 头里的线：一步一步焊' + ('' if back else '（双麦克风）')
    extra_css = '<style>.pads li { margin:10px 0; } .pads .dot { margin-top:2px; }</style>'
    out = AP.page(title, title, lead + note_top(), nav, ''.join(steps))
    out = out.replace('</head>', extra_css + '</head>', 1)
    OUTS[back].write_text(out)
    print(f'wrote {OUTS[back]} ({OUTS[back].stat().st_size // 1024} kB)')


def main():
    for back in (True, False):
        build(back)


if __name__ == '__main__':
    main()
