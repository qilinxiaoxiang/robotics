#!/usr/bin/env python3
"""Build ../A7Z-SOLDER.html (three microphones: both ears and the optional back one) and ../A7Z-SOLDER-2MIC.html (the two
ears only): the head wiring as a soldering sequence, one board (or one joint) per step, and for every pad
all the wires that go into it at once, each with its cut length and whether it is a bare wire or keeps one female plug.

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
PICK = lambda c: HWW[c]['cut']['whole']['pickup']                       # whole wire with one plug
DOWN = lambda c: HWW[c]['cut']['gatherToPin']['pickup']                 # gather point to pin, one plug
UP = lambda c: HWW[c]['cut']['toGather']                                # board to gather point, bare
MR, ML, MB = (HW['micPieces'][k] for k in ('mic-r', 'mic-l', 'mic-b'))
LINK = 15                                                               # bare L/R link
GND_DOWN = DOWN('mic-gnd')                                              # joint 4 to pin 34 (three microphones)
GND_WHOLE = PICK('mic-gnd')                                             # left ear GND straight to pin 34 (two)
assert UP('mic-gnd') == ML, 'left GND piece differs from the other left-ear pieces'


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
    W, H = 1300, 470
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    f, fs = font(38), font(30)

    def wire(y, x0, x1, col):
        d.line((x0, y, x1, y), fill=col, width=16)

    def stripped(x, y, left=True):
        a, b = (x - 40, x) if left else (x, x + 40)
        d.line((a, y, b, y), fill='#b87333', width=6)
    # bare wire
    d.text((40, 40), '细线：杜邦线两头的插头都剪掉', font=f, fill='#1b1b1b')
    wire(140, 140, 1100, '#c99a00')
    stripped(140, 140); stripped(1100, 140, False)
    d.line((100, 190, 1140, 190), fill='#546e7a', width=3)
    for x in (100, 1140):
        d.line((x, 175, x, 205), fill='#546e7a', width=3)
    d.text((620, 220), '长度 = 剪好以后整根量（含两头剥出来的铜丝）', font=fs, fill='#546e7a', anchor='mm')
    # one plug kept
    d.text((40, 280), '带母头的线：母对母杜邦线剪掉一头的插头', font=f, fill='#1b1b1b')
    wire(380, 140, 1020, '#1f6fd1')
    stripped(140, 380)
    d.rectangle((1020, 360, 1140, 400), fill='#263238')
    d.rectangle((1140, 368, 1150, 392), fill='#90a4ae')
    d.text((1080, 335), '母头', font=fs, fill='#263238', anchor='mm')
    d.line((100, 430, 1150, 430), fill='#546e7a', width=3)
    for x in (100, 1150):
        d.line((x, 415, x, 445), fill='#546e7a', width=3)
    d.text((620, 455), '长度 = 从剪口的铜丝头量到插头尖（含插头）', font=fs, fill='#546e7a', anchor='mm')
    return im


def joint_figure(title: str, ins: list[tuple[str, str]], out: str, col: str) -> Image.Image:
    n = len(ins)
    W, H = 1300, 150 + 110 * n
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    f = font(36)
    d.text((40, 40), title, font=font(40), fill='#1b1b1b', anchor='lm')
    ys = [130 + 110 * i for i in range(n)]
    jx, jy = 560, sum(ys) / n
    for (label, c), y in zip(ins, ys):
        d.text((40, y), label, font=f, fill='#1b1b1b', anchor='lm')
        d.line((300, y, jx - 60, jy), fill=c, width=12)
    d.rounded_rectangle((jx - 70, jy - 36, jx + 90, jy + 36), 14, fill='#455a64')
    d.text((jx + 10, jy), '焊+胶布', font=font(32), fill='white', anchor='mm')
    d.line((jx + 90, jy, 1080, jy), fill=col, width=12)
    d.rectangle((1080, jy - 24, 1200, jy + 24), fill='#263238')
    d.text((1200, jy + 40), out, font=f, fill='#1b1b1b', anchor='ra')
    return im


def fig(im, alt, cap, cls=''):
    return AP.figure(AP.uri(im, 1100), alt, cap, cls=cls)


# ---------------------------------------------------------------- steps
BACK = True          # set per page in main(): the back microphone is fitted
N: dict = {}         # step anchor -> step number on the current page


def no(key: str) -> str:
    return f'第 {N[key]} 步'


def note_top() -> str:
    other = ('<p><b>只装两只耳朵：</b>用 <a href="A7Z-SOLDER-2MIC.html">双麦克风版</a>，没有后脑那一步，接头少一个。</p>' if BACK else
             '<p><b>这是双麦克风版：</b>只有左右两只耳朵，像动物一样两只耳朵听声音。头盖后壁的第三个麦克风座空着。三个麦克风的版本留在 <a href="A7Z-SOLDER.html">A7Z-SOLDER</a>。</p>')
    return f"""
<div class="card">
<p><b>怎么用这一页：</b>一步一块板子（或一个接头）。每个焊盘后面写着<b>这个焊盘一共要焊几根线、各是哪根</b>，同一个焊盘的线一次焊上，不会再回来加。每根线写清楚多长、是细线还是带母头的线、另一头去哪。</p>
<p><b>两种线（第 0 步有图）：</b><b>细线</b> = 杜邦线两头的插头都剪掉；<b>带母头的线</b> = 母对母杜邦线剪掉一头，留一个插头，最后插到 A7Z 的针上，长度含插头。所有长度都按低头叼东西留够了余量，不超过 30 cm，一根 30 cm 的母对母杜邦线就够剪。</p>
<p><b>颜色建议</b>（跟组装指南一样，方便以后认）：SCK / BCLK 黄，WS / LRC 绿，SD / DIN 蓝，VDD / 3V3 / Vin 红，GND 黑。带母头的线剪完马上贴小旗，写 A7Z 针号。</p>
<p><b>已经焊过线的板子</b>（功放、XIAO 可能已经焊好了）：每根量一下，比这里写的长或一样长就留着；短了就拆下来换一根。功放的 BCLK、LRC 和 XIAO 的 3V3 现在要在集线点剪断，见{no('s5')}、{no('s6')}。</p>
<p><b>焊在哪一面：</b>线从有元件的那面插进孔，在另一面上锡。麦克风印字那面贴头盖内壁，焊点要小要平，穿出来的铜丝剪齐，中间的声孔别沾锡。</p>
{other}
</div>"""


def s0():
    bares = [(MR, 5, '右耳到左耳'), (ML, 4 if BACK else 3, '左耳到集线点')]
    if BACK:
        bares.append((MB, 4, '后脑到集线点'))
    bares += [(LINK, 3 if BACK else 2, 'L/R 短线，每个麦克风一根'), (SPK, 2, '喇叭（红、黑）'), (UP('amp-bclk'), 2, '功放 BCLK、LRC 到集线点'),
              (UP('touch-pin17'), 1, 'XIAO 3V3 到集线点')]
    lis = ''.join(f'<li>{mm} mm 细线 × {n}：{what}</li>' for mm, n, what in bares)
    lis += f'<li>铜箔引线（XIAO 到 5 块铜箔）：{"、".join(f"{k} {v}" for k, v in TOUCH.items())} mm，各一根细线</li>'
    pl = [(PICK('mic-sd'), 38, '左耳 SD')] + ([(PICK('mic-sd3'), 10, '后脑 SD')] if BACK else []) + [
          (PICK('amp-vin'), 4, '功放 Vin'), (PICK('amp-gnd'), 39, '功放 GND'), (PICK('amp-din'), 40, '功放 DIN'),
          (PICK('touch-pin25'), 25, 'XIAO GND'), (PICK('touch-pin29'), 29, 'XIAO D5 / SCL'), (PICK('touch-pin31'), 31, 'XIAO D4 / SDA'),
          (DOWN('amp-bclk'), 12, '接头 1 下来'), (DOWN('amp-lrc'), 35, '接头 2 下来'), (DOWN('touch-pin17'), 17, '接头 3 下来'),
          (GND_DOWN, 34, '接头 4 下来') if BACK else (GND_WHOLE, 34, '左耳 GND')]
    lis2 = ''.join(f'<li>{mm} mm，小旗 {flag}：{what}</li>' for mm, flag, what in pl)
    js = f"{N['j1']} 到 {N['j4' if BACK else 'j3']}"
    return AP.step('s0', no('s0'), '认两种线，剥皮', '你知道“细线”和“带母头的线”是什么，长度怎么量。', f"""
{fig(wire_types(), '细线和带母头的线', '上：细线，两头都剥皮。下：带母头的线，只剥剪口那头；长度含插头。')}
<ul class="acts">
<li>剥皮：焊到焊盘上的线头剥 2 到 3 mm；第 {js} 步拧在一起的线头剥 5 mm。</li>
<li>先上锡：剥好的铜丝拧紧，沾一点锡再焊，好焊很多。</li>
<li>线可以每一步现剪，也可以按下面的清单一次剪好。</li>
</ul>
<details><summary>一次剪好的清单（可选）</summary>
<p><b>细线</b></p><ul class="acts">{lis}</ul>
<p><b>带母头的线</b>（剪完贴小旗）</p><ul class="acts">{lis2}</ul>
</details>""")


def s1():
    rows = [('1', 'SCK', [bare(MR, '黄')], ''), ('2', 'WS', [bare(MR, '绿')], ''), ('3', 'SD', [bare(MR, '蓝')], ''),
            ('4', 'VDD', [bare(MR, '红'), f'新取一根 <b>{LINK} mm 细线</b>（短线）的一头'], ''),
            ('5', 'GND', [bare(MR, '黑')], ''), ('6', 'L/R', [link_end('另一头')], '右耳的 L/R 接 VDD：它是右声道。')]
    im = mic_face('右耳 INMP441，没字那面（焊线这面）', {p: n for n, p, *_ in rows}, 'VDD')
    return AP.step('s1', no('s1'), f'右耳麦克风：5 根 {MR} mm 细线 + 1 根短线', f'右耳的 6 个焊盘都焊好，伸出 5 根 {MR} mm 细线，另一头先空着。', f"""
<div class="pair"><div>{fig(im, '右耳 INMP441 焊线面', '没字那面（有金属壳那面）朝你，左右和印字那面是反的：上排 L/R、WS、SCK，下排 GND、VDD、SD。焊之前翻过去对着字认一遍。')}</div>
<div>{pad_list(rows)}<p>5 根 {MR} mm 细线的另一头先空着，{no('s2')}焊到左耳的同名焊盘上。</p></div></div>""")


def s2():
    gnd = ([bare(ML, '黑') + '，去集线点接头 4'] if BACK else
           [plug(GND_WHOLE, 34, '黑') + '，插头最后插 A7Z 34 号针'])
    rows = [('1', 'SCK', ['右耳 SCK 线的另一头', bare(ML, '黄') + '，去集线点接头 1'], ''),
            ('2', 'WS', ['右耳 WS 线的另一头', bare(ML, '绿') + '，去集线点接头 2'], ''),
            ('3', 'SD', ['右耳 SD 线的另一头', plug(PICK('mic-sd'), 38, '蓝') + '，插头最后插 A7Z 38 号针'], ''),
            ('4', 'VDD', ['右耳 VDD 线的另一头', bare(ML, '红') + '，去集线点接头 3'], ''),
            ('5', 'GND', ['右耳 GND 线的另一头', *gnd, f'新取一根 <b>{LINK} mm 细线</b>（短线）的一头'],
             '三根挤一个孔太紧的话：先焊前两根，短线这头搭在焊点上补一点锡。'),
            ('6', 'L/R', [link_end('另一头')], '左耳的 L/R 接 GND：它是左声道。')]
    im = mic_face('左耳 INMP441，没字那面（焊线这面）', {p: n for n, p, *_ in rows}, 'GND')
    out = (f'伸出去 4 根 {ML} mm 细线（去集线点）和 1 根小旗 38 的带母头线' if BACK else
           f'伸出去 3 根 {ML} mm 细线（去集线点）和 2 根带母头线（小旗 38、34）')
    return AP.step('s2', no('s2'), '左耳麦克风：右耳的 5 根 + 新的 5 根 + 1 根短线', f'左耳 6 个焊盘焊好；{out}。', f"""
<div class="pair"><div>{fig(im, '左耳 INMP441 焊线面', '同样是没字那面朝你。右耳过来的线焊到名字相同的焊盘上。')}</div>
<div>{pad_list(rows)}<p>{ML} mm 里含 25 mm 余量，头盖装好以后还能像盖子一样往后翻开。</p></div></div>""")


def s3():
    rows = [('1', 'SCK', [bare(MB, '黄') + '，去集线点接头 1'], ''), ('2', 'WS', [bare(MB, '绿') + '，去集线点接头 2'], ''),
            ('3', 'SD', [plug(PICK('mic-sd3'), 10, '蓝') + '，插头最后贴在 A7Z 10 号针旁边，先不插'], ''),
            ('4', 'VDD', [bare(MB, '红') + '，去集线点接头 3'], ''),
            ('5', 'GND', [bare(MB, '黑') + '，去集线点接头 4', f'新取一根 <b>{LINK} mm 细线</b>（短线）的一头'], ''),
            ('6', 'L/R', [link_end('另一头')], '后脑的 L/R 接 GND。')]
    im = mic_face('后脑 INMP441，没字那面（焊线这面）', {p: n for n, p, *_ in rows}, 'GND')
    return AP.step('s3', no('s3'), f'后脑麦克风：4 根 {MB} mm 细线 + 1 根带母头 + 1 根短线', f'后脑 6 个焊盘焊好；伸出去 4 根 {MB} mm 细线和 1 根小旗 10 的带母头线。', f"""
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
    rows = [('1', 'LRC', [bare(UP('amp-lrc'), '绿') + '，去集线点接头 2'], ''),
            ('2', 'BCLK', [bare(UP('amp-bclk'), '黄') + '，去集线点接头 1'], ''),
            ('3', 'DIN', [plug(PICK('amp-din'), 40, '蓝')], ''), ('4', 'GAIN', [], ''), ('5', 'SD', [], ''),
            ('6', 'GND', [plug(PICK('amp-gnd'), 39, '黑')], ''), ('7', 'Vin', [plug(PICK('amp-vin'), 4, '红')], ''),
            ('A', '绿色端子 −', ['喇叭黑线，剥 5 mm 插进去拧紧，不焊'], ''), ('B', '绿色端子 +', ['喇叭红线，剥 5 mm 插进去拧紧，不焊'], '')]
    pl = pad_list(rows, {**{n: c for n, c in a.values()}, 'A': '#6d4c41', 'B': '#6d4c41'})
    return AP.step('s5', no('s5'), '功放：2 根细线 + 3 根带母头，GAIN、SD 空着', '功放焊好 5 根线，喇叭线拧进绿色端子。', f"""
<div class="pair"><div>{fig(amp_figure(a), 'MAX98357A 功放', '印字面朝你，焊盘在下边一排，从左到右 LRC、BCLK、DIN、GAIN、SD、GND、Vin。')}</div>
<div>{pl}
<div class="card"><b>以前已经焊好整根 BCLK、LRC（带插头）的：</b>不用拆。量离功放 {UP('amp-bclk')} mm 的地方剪断，靠功放这段就是这里的细线；带插头那段如果还有 {DOWN('amp-bclk')} mm（BCLK）/ {DOWN('amp-lrc')} mm（LRC）以上，留着当第 {N['j1']} / {N['j2']} 步的“新带母头线”用。</div></div></div>""")


def s6():
    x = {'D0': ('1', '#b87333'), 'D1': ('2', '#b87333'), 'D2': ('3', '#b87333'), 'D3': ('4', '#b87333'), 'D8': ('5', '#b87333'),
         '3V3': ('6', COL['VDD'][0]), 'GND': ('7', COL['GND'][0]), 'D5': ('8', COL['SCK'][0]), 'D4': ('9', COL['WS'][0])}
    rows = [('1', 'D0', [bare(TOUCH['L1']) + '，另一头焊铜箔 L1 的角'], ''), ('2', 'D1', [bare(TOUCH['R1']) + '，另一头焊铜箔 R1'], ''),
            ('3', 'D2', [bare(TOUCH['L2']) + '，另一头焊铜箔 L2'], ''), ('4', 'D3', [bare(TOUCH['R2']) + '，另一头焊铜箔 R2'], ''),
            ('5', 'D8', [bare(TOUCH['M']) + '，另一头焊铜箔 M'], ''),
            ('6', '3V3', [bare(UP('touch-pin17'), '红') + '，去集线点接头 3'], ''),
            ('7', 'GND', [plug(PICK('touch-pin25'), 25, '黑')], ''), ('8', 'D5（SCL）', [plug(PICK('touch-pin29'), 29, '蓝')], ''),
            ('9', 'D4（SDA）', [plug(PICK('touch-pin31'), 31, '绿')], '')]
    pl = pad_list(rows, dict(x.values()))
    return AP.step('s6', no('s6'), 'XIAO 触摸板：5 根铜箔线 + 1 根细线 + 3 根带母头', 'XIAO 焊好 9 根线；其余焊盘（VBUS、D6、D7、D9、D10）空着。', f"""
<div class="pair"><div>{fig(xiao_figure(x), 'XIAO ESP32-S3 正面', 'XIAO 正面，USB-C 口朝上。左列 D0 到 D6，右列 5V、GND、3V3、D10 到 D7。')}</div>
<div>{pl}
<div class="card"><b>你的 XIAO 已经焊好、能用了</b>（10/20 五个铜箔都试过）。只核对长度：GND、D5、D4 三根比上面写的短，就拆下换新的。红色 3V3 现在是一整根带插头的：量离 XIAO {UP('touch-pin17')} mm 剪断，带插头那段还有 {DOWN('touch-pin17')} mm 以上就留着当第 {N['j3']} 步的新线。</div></div></div>""")


def s7():
    if BACK:
        heads = '功放 BCLK、LRC，XIAO 3V3，左耳 SCK、WS、VDD、GND，后脑 SCK、WS、VDD、GND，一共 11 个细线头'
        plugs = '带母头的 8 根（小旗 4、39、40、25、29、31、38、10）'
    else:
        heads = '功放 BCLK、LRC，XIAO 3V3，左耳 SCK、WS、VDD，一共 6 个细线头'
        plugs = '带母头的 8 根（小旗 4、39、40、25、29、31、38、34）'
    mics = '三个麦克风' if BACK else '两只耳朵的麦克风'
    return AP.step('s7', no('s7'), '板子装进头里，线都拢到集线点', f'{mics}、功放、喇叭、XIAO 按组装指南装好；所有线头都到了头盖左后角、出线口正上方。', f"""
{AP.figure(AP.IMG_HEAD_WIRES, '头里的线到集线点', AP.HEAD_WIRES_CAP)}
<ul class="acts">
<li>装法照组装指南第 9 章。这一步不焊东西。</li>
<li>到集线点的是：{heads}。</li>
<li>{plugs}经过集线点不停，直接从出线口出去，顺脖子左边下来。</li>
</ul>""")


def joint(anchor, title, flag, plug_mm, col, ins):
    figure_ins = [(lab, c) for lab, _, c in ins]
    body = '；'.join(f'{"①②③④⑤"[i]} {lab}（{w}）' for i, (lab, w, _) in enumerate(ins))
    im = joint_figure(title, figure_ins, f'新带母头线 {plug_mm} mm，小旗 {flag} → {flag} 号针', col)
    return AP.step(anchor, no(anchor), title, f'{len(ins) + 1} 根线拧成一个焊点，只剩一根带母头的线（小旗 {flag}）往下走。', f"""
{fig(im, title, '左边是已经焊在板子上的细线；右边是新取的带母头线。剥头拧在一起焊、缠胶布，往下走的只有右边这一根。', cls='mid')}
<p><b>一次焊 {len(ins) + 1} 根：</b>{body}；{"①②③④⑤"[len(ins)]} {plug(plug_mm, flag)}。</p>
<ol class="acts"><li>每个线头剥 5 mm，并排对齐，拧成一股。</li><li>上锡焊透，焊点顺着线折平。</li><li>缠 2 到 3 圈电工胶布。</li></ol>""")


def joints():
    y, g, r, k = COL['SCK'][0], COL['WS'][0], COL['VDD'][0], COL['GND'][0]
    ear, amp, xiao, back = f"{no('s2')}那根", f"{no('s5')}那根", f"{no('s6')}那根", (f"{no('s3')}那根" if BACK else '')
    b = lambda lab, c: [(lab, back, c)] if BACK else []
    out = [joint('j1', '接头 1（时钟 SCK）→ 12 号针', 12, DOWN('amp-bclk'), y, [('功放 BCLK', amp, y), ('左耳 SCK', ear, y), *b('后脑 SCK', y)]),
           joint('j2', '接头 2（左右时钟 WS）→ 35 号针', 35, DOWN('amp-lrc'), g, [('功放 LRC', amp, g), ('左耳 WS', ear, g), *b('后脑 WS', g)]),
           joint('j3', '接头 3（3.3 V）→ 17 号针', 17, DOWN('touch-pin17'), r, [('XIAO 3V3', xiao, r), ('左耳 VDD', ear, r), *b('后脑 VDD', r)])]
    if BACK:
        out.append(joint('j4', '接头 4（GND）→ 34 号针', 34, GND_DOWN, k, [('左耳 GND', ear, k), ('后脑 GND', back, k)]))
    return out


def s12():
    pins = [(4, '#d7263d'), (12, '#c99a00'), (17, '#d7263d'), (25, '#1d1d1f'), (29, '#1f6fd1'), (31, '#1f9d55'), (34, '#1d1d1f'),
            (35, '#1f9d55'), (38, '#1f6fd1'), (39, '#1d1d1f'), (40, '#1f6fd1')] + ([(10, '#9e9e9e')] if BACK else [])
    goal = '11 个插头插在 A7Z 上；小旗 10 贴在 10 号针旁边，不插。' if BACK else '11 个插头插在 A7Z 上，10 号针空着。'
    cap = 'A7Z 正面竖放（1 号针在上）。灰色的 10 号针先不插。' if BACK else 'A7Z 正面竖放（1 号针在上）。'
    mic = '麦克风：34、38；后脑的 10 先不插' if BACK else '麦克风：34、38'
    return AP.step('s12', no('s12'), '插到 A7Z：小旗几号就插几号针', goal, f"""
<div class="pair"><div>{AP.figure(AP.top_fig(pins), f'A7Z 上要插的 {len(pins)} 个针', cap)}</div>
<div><p>插法、怎么数针号、插完怎么检查，见 <a href="A7Z-PINS.html#audio">A7Z-PINS 第 6 到 8 步</a>。</p>
<ul class="acts"><li>功放：4、12、35、39、40</li><li>触摸板：17、25、29、31</li><li>{mic}</li></ul></div></div>""")


ORDER = [('s0', '两种线'), ('s1', '右耳'), ('s2', '左耳'), ('s3', '后脑'), ('s4', '喇叭'), ('s5', '功放'), ('s6', 'XIAO'),
         ('s7', '装进头里'), ('j1', '接头 1'), ('j2', '接头 2'), ('j3', '接头 3'), ('j4', '接头 4'), ('s12', '插 A7Z')]


def build(back: bool) -> None:
    global BACK, N
    BACK = back
    order = [(k, t) for k, t in ORDER if back or k not in ('s3', 'j4')]
    N = {k: i for i, (k, _) in enumerate(order)}
    steps = [s0(), s1(), s2(), *([s3()] if back else []), s4(), s5(), s6(), s7(), *joints(), s12()]
    nav = [(k, f'{N[k]} {t}') for k, t in order]
    nj = 4 if back else 3
    lead = (f"<p class=\"lead\">头里的线一步一步怎么焊：先焊每块板子（第 1 到 {N['s6']} 步），装进头里（{no('s7')}），"
            f"再在集线点焊 {nj} 个接头（第 {N['j1']} 到 {N['j4' if back else 'j3']} 步），最后插到 A7Z（{no('s12')}）。"
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
