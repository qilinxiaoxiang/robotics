"""Build ../A7Z-TOUCH.html: make the copper touch pads, solder the XIAO ESP32-S3, bench-test one pad, stick everything
in the head cap, plug onto the A7Z and check (python3 + Pillow, no network). Picture first, few words.
Shares the page parts of build_a7z_pages.py; the cap views come from render_touch_views.py (CAD venv).
Sources: guide/extension-20261015-touch/PLAN.md and touch_routes.json, DECISIONS.md D-013, guide/content/steps.py
(wire lengths = route + 15 mm), Seeed XIAO ESP32-S3 wiki pinout. Verified 2026-10-20.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import build_a7z_pages as B
import photos as P

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'A7Z-TOUCH.html'
TOUCH = HERE.parent.parent / 'guide' / 'extension-20261015-touch'
LEN = json.loads((TOUCH / 'touch_routes.json').read_text())['lengths_mm']
CUT = {k: int(math.ceil((v + 15) / 5) * 5) for k, v in LEN.items()}   # same rule as guide/content/steps.py r5()

CU = '#c87533'
PADS = [  # name, XIAO pad, size mm, strips
    ('L1', 'D0', 18, 4), ('R1', 'D1', 18, 4), ('L2', 'D2', 12, 3), ('R2', 'D3', 12, 3), ('M', 'D8', 12, 3)]
A7Z = [('3V3', 17, '#d7263d'), ('GND', 25, '#1d1d1f'), ('D5', 29, '#c99a00'), ('D4', 31, '#1f6fd1')]

# ---------------------------------------------------------------- XIAO photo with every pad marked
# Pad centres on sources/xiao-esp32s3-front-pinout-crop.png (USB-C at the top): left column x 480, right column x 960,
# rows 108, 186, 264, 344, 424, 504, 582 (read on the crop, 2026-10-15/20).
ROWS = [108, 186, 264, 344, 424, 504, 582]
LEFT = ['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6']
RIGHT = ['VBUS', 'GND', '3V3', 'D10', 'D9', 'D8', 'D7']
XY = {**{n: (480, y) for n, y in zip(LEFT, ROWS)}, **{n: (960, y) for n, y in zip(RIGHT, ROWS)}}


MARGIN = 90


def xiao_all():
    src = P.Image.open(P.HERE / 'sources' / 'xiao-esp32s3-front-pinout-crop.png').convert('RGB')
    im = P.Image.new('RGB', (src.width + 2 * MARGIN, src.height), 'white')
    im.paste(src, (MARGIN, 0))
    side = lambda x: MARGIN // 2 if x < 700 else src.width + MARGIN + MARGIN // 2
    marks = []
    for name, pad, _, _ in PADS:
        x, y = XY[pad]
        marks.append((name, (x + MARGIN, y), (side(x), y), 26, CU, '#8d4a12'))
    for pad, pin, col in A7Z:
        x, y = XY[pad]
        marks.append((str(pin), (x + MARGIN, y), (side(x), y), 26, col, '#1565c0'))
    for pad, lab in (('D9', '左'), ('D10', '右')):
        x, y = XY[pad]
        marks.append((lab, (x + MARGIN, y), (side(x), y), 26, CU, '#6d4c41'))
    x, y = XY['VBUS']
    marks.append(('X', (x + MARGIN, y), (side(x), y), 26, '#d50000', '#d50000'))
    return P.draw_marks(im, marks)


IMG_XIAO = B.uri(xiao_all(), 1100)
LEGEND_XIAO = ([('land', n, f'{p} → 铜箔 {n}') for n, p, _, _ in PADS]
               + [('pin', str(pin), f'{pad} → A7Z {pin} 号针（带插头的线）') for pad, pin, _ in A7Z]
               + [('land', '左', 'D9 → 左侧躯干铜箔'), ('land', '右', 'D10 → 右侧躯干铜箔'),
                  ('land', 'X', 'VBUS（5 V）：不焊。D6、D7 也空着。')])

# ---------------------------------------------------------------- drawings
SVG_HEAD = '<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{a}"><style>text{{font:21px "PingFang SC","Hiragino Sans GB",system-ui,sans-serif;fill:#1b1b1b}}.s{{font-size:17px;fill:#4a5a63}}.b{{font-weight:700}}</style><rect width="{w}" height="{h}" fill="#fff"/>'


def svg_parts():
    s = SVG_HEAD.format(w=680, h=430, a='零件：XIAO、铜箔、两种线')
    # XIAO
    s += '<rect x="20" y="30" width="96" height="116" rx="10" fill="#1d1d1f"/><rect x="44" y="18" width="48" height="26" rx="5" fill="#b0bec5"/>'
    s += '<rect x="34" y="62" width="68" height="56" rx="4" fill="#eceff1"/><text x="68" y="96" text-anchor="middle" class="s">XIAO</text>'
    s += '<text x="20" y="176">XIAO ESP32-S3</text><text x="20" y="200" class="s">已烧好固件</text>'
    # tape
    s += '<circle cx="230" cy="88" r="58" fill="#e0a370"/><circle cx="230" cy="88" r="26" fill="#fff"/><rect x="230" y="138" width="130" height="10" fill="' + CU + '"/>'
    s += '<text x="250" y="176" text-anchor="middle">铜箔 5 mm 宽</text><text x="250" y="200" text-anchor="middle" class="s">约 30 cm</text>'
    # pad lead
    s += '<line x1="420" y1="60" x2="650" y2="60" stroke="#8d4a12" stroke-width="7" stroke-linecap="round"/>'
    s += '<text x="535" y="40" text-anchor="middle" class="b">铜箔引线 × 7</text>'
    s += '<text x="535" y="92" text-anchor="middle" class="s">杜邦线两头的插头都剪掉，多股软线</text>'
    # A7Z lead
    s += '<line x1="420" y1="140" x2="610" y2="140" stroke="#1f6fd1" stroke-width="7"/><rect x="610" y="128" width="36" height="24" rx="3" fill="#263238"/>'
    s += '<text x="535" y="120" text-anchor="middle" class="b">A7Z 线 × 4</text>'
    s += '<text x="535" y="176" text-anchor="middle" class="s">杜邦线，只剪一头，留一个母插头</text>'
    s += '<text x="535" y="200" text-anchor="middle" class="s">红 3V3 · 黑 GND · 黄 D5 · 蓝 D4</text>'
    # lengths
    pads = '　'.join(f'{n} {CUT["touch_pad_" + n.lower()]}' for n, _, _, _ in PADS)
    pins = '　'.join(f'{pin} 号 {CUT[f"touch_a7z_pin{pin}"]}' for _, pin, _ in A7Z)
    s += '<line x1="20" y1="236" x2="660" y2="236" stroke="#cfd8dc"/>'
    s += f'<text x="20" y="272" class="b">剪线长度（mm）</text><text x="20" y="304">铜箔引线：{pads}</text>'
    s += '<text x="20" y="334" class="s">左身、右身两根：等躯干那一步的长度</text>'
    s += f'<text x="20" y="370">A7Z 线（含插头）：{pins}</text>'
    s += '<text x="20" y="408" class="s">工具：烙铁、焊锡、助焊笔、剥线钳、万用表、瓷砖一块、酒精、泡棉双面胶</text>'
    return s + '</svg>'


def svg_pad():
    """Top view of an 18 mm pad: four 5 mm strips, 1 mm overlap, the lead's bare end soldered across all of them."""
    k = 14  # px per mm
    x0, y0 = 60, 70
    s = SVG_HEAD.format(w=680, h=420, a='铜箔：四条 5 mm 并排，引线横跨焊在每一条上')
    for i in range(4):
        x = x0 + i * 4 * k
        s += f'<rect x="{x}" y="{y0}" width="{5 * k}" height="{18 * k}" fill="{CU}" fill-opacity="0.92" stroke="#8d4a12"/>'
    w = (4 * 4 + 1) * k
    s += f'<line x1="{x0 - 10}" y1="{y0 + 3 * k}" x2="{x0 + w + 10}" y2="{y0 + 3 * k}" stroke="#eceff1" stroke-width="5"/>'
    for i in range(4):
        cx = x0 + i * 4 * k + 2.5 * k
        s += f'<circle cx="{cx}" cy="{y0 + 3 * k}" r="11" fill="#b0bec5" stroke="#546e7a" stroke-width="2"/>'
    s += f'<path d="M{x0 - 10} {y0 + 3 * k} Q{x0 - 40} {y0 + 3 * k} {x0 - 40} {y0 + 3 * k + 60}" fill="none" stroke="#8d4a12" stroke-width="7"/>'
    s += f'<text x="{x0 + w / 2}" y="40" text-anchor="middle" class="b">18 mm 的铜箔 = 4 条 × 18 mm 长</text>'
    xr = x0 + w + 30
    s += f'<text x="{xr}" y="{y0 + 3 * k - 8}">裸线横压在 4 条上</text><text x="{xr}" y="{y0 + 3 * k + 18}" class="s">每条点一下焊锡（灰点）</text>'
    s += f'<text x="{xr}" y="{y0 + 9 * k}">相邻两条压 1 mm</text><text x="{xr}" y="{y0 + 9 * k + 26}" class="s">12 mm 的 = 3 条 × 12 mm</text>'
    s += f'<text x="{xr}" y="{y0 + 15 * k}">在瓷砖上做</text><text x="{xr}" y="{y0 + 15 * k + 26}" class="s">背纸先不撕，焊好再撕</text>'
    s += f'<text x="20" y="{y0 + 18 * k + 40}" class="s">剥掉引线头 20 mm 的皮（12 mm 的铜箔剥 14 mm）。焊点越少越平越好。</text>'
    return s + '</svg>'


def svg_solder():
    """Side view of a wire laid flat on a XIAO edge pad."""
    s = SVG_HEAD.format(w=680, h=300, a='侧面：线平贴在焊盘顶面，从板边往外走')
    s += '<rect x="250" y="150" width="400" height="22" fill="#1d1d1f"/><text x="450" y="200" text-anchor="middle" class="s">XIAO 板子（侧面）</text>'
    s += '<path d="M250 150 h40 v22 h-40" fill="#d4a017"/><text x="270" y="222" text-anchor="middle" class="s">半孔焊盘</text>'
    s += '<rect x="250" y="140" width="56" height="10" rx="4" fill="#b0bec5"/>'
    s += '<line x1="30" y1="145" x2="262" y2="145" stroke="#8d4a12" stroke-width="9" stroke-linecap="round"/>'
    s += '<line x1="200" y1="145" x2="300" y2="145" stroke="#e0a370" stroke-width="5"/>'
    s += '<text x="30" y="118">线从板边往外平着走</text><text x="470" y="118" class="s">裸线 2 mm，先上锡</text>'
    s += '<path d="M380 30 L320 128" stroke="#757575" stroke-width="10" stroke-linecap="round"/><text x="392" y="40">烙铁 1 到 2 秒</text>'
    s += '<text x="30" y="268" class="b">线不往上翘：头盖里只有 2 mm 空间。</text>'
    return s + '</svg>'


def svg_check():
    s = SVG_HEAD.format(w=680, h=250, a='万用表通断档：铜箔到 XIAO 响，铜箔之间不响')
    s += f'<rect x="40" y="60" width="110" height="110" fill="{CU}"/><text x="95" y="122" text-anchor="middle" class="b">L1</text>'
    s += f'<rect x="190" y="80" width="80" height="80" fill="{CU}"/><text x="230" y="127" text-anchor="middle" class="b">L2</text>'
    s += '<rect x="470" y="60" width="96" height="116" rx="10" fill="#1d1d1f"/><text x="518" y="124" text-anchor="middle" style="fill:#fff">D0</text>'
    s += '<path d="M95 60 Q300 -20 500 90" fill="none" stroke="#2e7d32" stroke-width="5"/><text x="330" y="30" style="fill:#2e7d32" class="b">响 ✓</text>'
    s += '<path d="M120 170 Q170 220 220 160" fill="none" stroke="#d50000" stroke-width="5" stroke-dasharray="10 8"/><text x="175" y="232" style="fill:#d50000" class="b">不响 ✓</text>'
    s += '<text x="310" y="200" class="s">每块铜箔 ↔ 它的 XIAO 焊盘：响</text><text x="310" y="226" class="s">任意两块铜箔之间、3V3 ↔ GND：不响</text>'
    return s + '</svg>'


def svg_bench():
    """Bench set-up, side view: fingertip, PLA wall, copper pad, lead to D0, USB-C to the Mac."""
    s = SVG_HEAD.format(w=680, h=300, a='桌上测试：手指隔着 PLA 碰铜箔，引线到 XIAO，USB-C 到 Mac')
    s += '<rect x="60" y="120" width="260" height="26" fill="#eceff1" stroke="#90a4ae"/><text x="190" y="138" text-anchor="middle" class="s">PLA 1.7 mm</text>'
    s += f'<rect x="100" y="146" width="180" height="7" fill="{CU}"/>'
    s += '<path d="M150 30 q40 -10 60 20 l10 66 q-40 10 -80 0 z" fill="#f2c9a8" stroke="#bf8f6a" stroke-width="2"/>'
    s += '<text x="240" y="70">指尖在这一面</text><text x="60" y="186" class="s">铜箔贴在另一面</text>'
    s += '<path d="M280 153 Q360 220 420 200" fill="none" stroke="#8d4a12" stroke-width="6"/>'
    s += '<rect x="420" y="170" width="80" height="96" rx="8" fill="#1d1d1f"/><text x="460" y="224" text-anchor="middle" style="fill:#fff">D0</text>'
    s += '<path d="M500 200 L580 200" stroke="#607d8b" stroke-width="8"/><rect x="580" y="170" width="80" height="60" rx="6" fill="#b0bec5"/>'
    s += '<text x="620" y="206" text-anchor="middle" class="b">Mac</text><text x="540" y="186" text-anchor="middle" class="s">USB-C</text>'
    return s + '</svg>'


# ---------------------------------------------------------------- steps
LIVE_PY = '~/code/robotics/microduck-sim/guide/extension-20261015-touch/firmware/touch_live.py'

S_PARTS = B.step('parts', '第 1 步', '零件和线', '线按长度剪好，摆在桌上。', f'''
<figure>{svg_parts()}</figure>''')

S_PAD = B.step('pad', '第 2 步', '做铜箔', '5 块铜箔在瓷砖上做好，每块的引线焊牢。', f'''
<figure>{svg_pad()}<figcaption>L1、R1：18 × 18 mm，4 条。L2、R2、M：12 × 12 mm，3 条。</figcaption></figure>
<div class="card">面积：手指压上去的那块（约 1 cm²）决定信号大小；铜箔比指尖大，只是让手更容易碰到。所以不用更大。</div>''')

S_XIAO = B.step('xiao', '第 3 步', '焊 XIAO', '11 根线平焊在 XIAO 正面的焊盘上，5 V 没焊。', f'''
{B.figure(IMG_XIAO, 'XIAO 正面：每个焊盘焊哪根线', 'XIAO 正面，USB-C 朝上。棕色 = 铜箔引线，蓝色 = 去 A7Z 的线。', LEGEND_XIAO)}
<figure>{svg_solder()}</figure>''')

S_BENCH = B.step('bench', '第 4 步 · 先只做 L1', '桌上测试', '指尖压上去，L1 的条明显变长；松开就回去。', f'''
<figure>{svg_bench()}<figcaption>先只做 L1 一块：贴在一片约 1.7 mm 厚的 PLA 废件上，引线焊到 D0，XIAO 插 Mac。</figcaption></figure>
{B.cmd('mac', f'~/.venvs/touch/bin/python {LIVE_PY}', 'L1   19398      -2\nR1   16021      -1\n（每块一行：读数、比刚打开时变了多少、条。Ctrl-C 退出）')}
<div class="card">指尖压在 PLA <b>另一面</b>、正对铜箔，看 L1 那一行的条。</div>''')

S_CAP = B.step('cap', '第 5 步', '贴进头盖', '5 块铜箔和 XIAO 贴好，引线贴着壁走。', f'''
{B.figure(B.uri(P.Image.open(B.IMG / 'touch_below.png'), 1100), '头盖翻过来往里看：五块铜箔和 XIAO 的位置', '头盖翻过来往里看。棕线 = 引线走法。')}
{B.figure(B.uri(P.Image.open(B.IMG / 'touch_side.png'), 1100), '从机器人右边看，右半边切掉：XIAO 贴在左内壁', '从右边看（右半边切掉）：XIAO 贴在左内壁，金属罩朝里，USB-C 朝后。', cls='mid')}
<ol class="acts">
<li>{B.tag('hand')}酒精擦一遍贴的位置，干透。</li>
<li>{B.tag('hand')}撕背纸，贴上，用指甲压平，没有气泡。</li>
<li>{B.tag('hand')}引线贴着壁走，隔几厘米贴一小块胶带。</li>
</ol>
<div class="warn">铜箔不碰铜箔、螺丝头、喇叭压圈、功放。</div>''')

S_PLUG = B.step('plug', '第 6 步', '插 A7Z', '4 个插头插在 17、25、29、31 号针上。', f'''
{B.figure(B.IMG_TOUCH, 'A7Z 正面：17、25、29、31 号针', 'A7Z 上的 4 根针，都在里排。详细做法：<a href="A7Z-PINS.html#touch">插线页第 7 步</a>。', cls='narrow')}
<div class="warn">红线（3V3）绝不插 2 号或 4 号针（5 V）。</div>''')

S_CHECK = B.step('check', '第 7 步', '检查', '每块铜箔都响，铜箔之间都不响。', f'''
<figure>{svg_check()}</figure>''')

SOURCES = '''
<section class="step" id="sources"><h2>依据</h2><ul class="src">
<li>铜箔位置、大小和走线：guide/extension-20261015-touch/touch_routes.json 和 world/*.stl（L1、R1 18 mm，L2、R2、M 12 mm），DECISIONS.md D-013。图由 bringup/a7z/render_touch_views.py 画出。</li>
<li>线长：走线长度 + 15 mm，取整到 5 mm（guide/content/steps.py 同一规则）。</li>
<li>XIAO 焊盘：Seeed XIAO ESP32-S3 wiki 正面引脚图。触摸脚 D0–D5、D8–D10；D4、D5 用作 I2C。</li>
<li>固件和测试：guide/extension-20261015-touch/firmware/（touch_xiao、touch_bench.py）。</li>
<li>核对日期：2026-10-20。</li></ul></section>'''

LEAD = '<p class="lead">XIAO 读头壳里的铜箔。手指隔着 1.7 mm 的壳碰到铜箔，XIAO 就读出来。</p>'
NAV = [('parts', '1 零件'), ('pad', '2 做铜箔'), ('xiao', '3 焊 XIAO'), ('bench', '4 桌上测试'), ('cap', '5 贴进头盖'),
       ('plug', '6 插 A7Z'), ('check', '7 检查')]
BODY = S_PARTS + S_PAD + S_XIAO + S_BENCH + S_CAP + S_PLUG + S_CHECK + SOURCES

if __name__ == '__main__':
    OUT.write_text(B.page('MicroDuck 触摸板', '触摸板：做铜箔、焊 XIAO、贴进头盖', LEAD, NAV, BODY), encoding='utf-8')
    print(OUT, OUT.stat().st_size)
