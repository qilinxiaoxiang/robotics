"""Build the two standalone A7Z bench pages for MicroDuck (python3 + Pillow, no network):

  ../A7Z-PINS.html     Dupont wires on the Radxa Cubie A7Z 40-pin header (replaces the Pi Zero W pins)
  ../A7Z-ANTENNA.html  AC019 FPC antenna inside the head cap

Images are embedded as data URIs; no CDN, no browser storage. The CAD renders in img/ come from render_cad_views.py
(run it first with the CAD venv when the head geometry changes). Sources and the verification date: README.md.
"""
from __future__ import annotations

import base64
import html
import io
from pathlib import Path

from PIL import Image

import photos as P

HERE = Path(__file__).resolve().parent
OUT_PINS = HERE.parent / 'A7Z-PINS.html'
OUT_ANT = HERE.parent / 'A7Z-ANTENNA.html'
IMG = HERE / 'img'


def uri(im: Image.Image, width: int | None = None, quality: int = 84) -> str:
    if width and im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert('RGB').save(buf, 'JPEG', quality=quality, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


# ---------------------------------------------------------------- shared page parts
CSS = '''
  :root { --bg:#ffffff; --fg:#1b1b1b; --muted:#4a5a63; --card:#f5f7f8; --line:#cfd8dc; --warn:#fff3e0; --warnb:#ffb74d;
          --ok:#e8f5e9; --okb:#81c784; --pend:#fff8e1; --pendb:#f9a825; --link:#1557b0; }
  * { box-sizing:border-box; }
  html { -webkit-text-size-adjust:100%; }
  body { margin:0; background:var(--bg); color:var(--fg); font:17px/1.65 "PingFang SC","Hiragino Sans GB",system-ui,sans-serif; }
  main { max-width:1100px; margin:0 auto; padding:16px; }
  h1 { font-size:26px; line-height:1.35; margin:8px 0 6px; }
  h2 { font-size:22px; line-height:1.4; margin:0 0 8px; }
  h3 { font-size:18px; margin:16px 0 6px; }
  p, li { overflow-wrap:anywhere; }
  a { color:var(--link); }
  .lead { font-size:18px; margin:4px 0 12px; }
  .nav { display:flex; flex-wrap:wrap; gap:8px; margin:12px 0 4px; padding:0; list-style:none; }
  .nav a { display:block; padding:6px 12px; border:1px solid var(--line); border-radius:18px; text-decoration:none; background:var(--card); font-size:16px; }
  .step { border:1px solid var(--line); border-radius:14px; padding:14px 16px; margin:22px 0; scroll-margin-top:12px; }
  .stepno { color:var(--muted); font-size:15px; margin-bottom:2px; }
  .goal { background:var(--ok); border:1px solid var(--okb); border-radius:10px; padding:10px 12px; margin:8px 0 12px; }
  .warn { background:var(--warn); border:2px solid var(--warnb); border-radius:10px; padding:10px 12px; margin:12px 0; }
  .pend { background:var(--pend); border:2px dashed var(--pendb); border-radius:10px; padding:10px 12px; margin:12px 0; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 14px; margin:10px 0; }
  .acts { padding-left:22px; margin:6px 0; }
  .acts li { margin:6px 0; }
  .where { display:inline-block; font-size:14px; font-weight:700; border-radius:6px; padding:0 7px; margin-right:6px; color:#fff; }
  .where.hand { background:#6d4c41; } .where.a7z { background:#2e7d32; } .where.mac { background:#1565c0; }
  .cmd { border:1px solid #b0bec5; border-radius:8px; margin:6px 0; background:#fafafa; }
  .cmdbar { display:flex; justify-content:space-between; align-items:center; gap:8px; padding:4px 8px; border-bottom:1px solid #e0e0e0; }
  .cmd pre { margin:0; padding:8px 10px; white-space:pre-wrap; overflow-wrap:anywhere; font:15px/1.5 Menlo,Consolas,monospace; }
  .copy { font-size:16px; padding:3px 12px; border-radius:6px; border:1px solid #90a4ae; background:#fff; cursor:pointer; }
  .expect { border-left:4px solid var(--okb); padding:4px 10px; margin:6px 0; background:#f7fbf7; }
  .expect pre { margin:4px 0 0; white-space:pre-wrap; overflow-wrap:anywhere; font:14px/1.45 Menlo,Consolas,monospace; }
  figure { margin:10px 0; border:1px solid var(--line); border-radius:12px; overflow:hidden; background:#fff; }
  figure img, figure svg { display:block; width:100%; height:auto; }
  figcaption { font-size:15px; color:var(--muted); padding:8px 12px; }
  .legend { margin:0; padding:6px 12px 10px 12px; list-style:none; font-size:16px; }
  .legend li { margin:4px 0; display:flex; gap:8px; align-items:flex-start; }
  .dot { flex:0 0 auto; min-width:30px; height:30px; padding:0 6px; border-radius:15px; color:#fff; font-weight:700; font-size:15px;
         display:inline-flex; align-items:center; justify-content:center; }
  .dot.pin { background:#1565c0; } .dot.land { background:#e65100; }
  .pair { display:grid; grid-template-columns:1fr 1fr; gap:12px; align-items:start; }
  .pair3 { display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; align-items:start; }
  .narrow { max-width:520px; }
  .mid { max-width:760px; }
  .wire { display:inline-block; width:14px; height:14px; border-radius:3px; border:1px solid #607d8b; vertical-align:-2px; margin-right:4px; }
  .src { color:var(--muted); font-size:14px; }
  .src li { margin:4px 0; }
  code { font-family:Menlo,Consolas,monospace; font-size:0.92em; background:#eef2f4; border-radius:4px; padding:0 3px; overflow-wrap:anywhere; }
  details { margin:10px 0; } summary { cursor:pointer; font-weight:700; }
  @media (max-width: 760px) { .pair, .pair3 { grid-template-columns:1fr; } h1 { font-size:23px; } }
'''

JS = '''
document.querySelectorAll('.copy').forEach(function (b) {
  b.addEventListener('click', function () {
    var t = b.closest('.cmd').querySelector('pre').innerText;
    function done() { b.textContent = '已复制'; setTimeout(function () { b.textContent = '复制'; }, 1500); }
    if (navigator.clipboard) { navigator.clipboard.writeText(t).then(done, function () {}); }
  });
});
'''

WHERE = {'a7z': '在 A7Z 上', 'mac': '在 Mac 上', 'hand': '手上'}


def tag(where: str) -> str:
    return f'<span class="where {where}">{WHERE[where]}</span>'


def cmd(where: str, code: str, expect: str | None = None, expect_title: str = '应该看到') -> str:
    out = (f'<div class="cmd"><div class="cmdbar">{tag(where)}<button class="copy" type="button">复制</button></div>'
           f'<pre><code>{html.escape(code)}</code></pre></div>')
    if expect is not None:
        out += f'<div class="expect"><b>{expect_title}</b><pre>{html.escape(expect)}</pre></div>'
    return out


def figure(src: str, alt: str, cap: str, legend=(), cls: str = '') -> str:
    lis = ''.join(f'<li><span class="dot {k}">{html.escape(n)}</span><span>{t}</span></li>' for k, n, t in legend)
    leg = f'<ul class="legend">{lis}</ul>' if lis else ''
    return (f'<figure class="{cls}"><img alt="{html.escape(alt)}" src="{src}">'
            f'<figcaption>{cap}</figcaption>{leg}</figure>')


def step(anchor: str, no: str, title: str, goal: str, body: str) -> str:
    return (f'<section class="step" id="{anchor}"><div class="stepno">{no}</div><h2>{title}</h2>'
            f'<div class="goal"><b>这一步完成后：</b>{goal}</div>{body}</section>')


def page(title: str, h1: str, lead: str, nav, body: str) -> str:
    navh = ''.join(f'<li><a href="#{a}">{t}</a></li>' for a, t in nav)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{CSS}</style></head>
<body><main>
<h1>{h1}</h1>
{lead}
<ul class="nav">{navh}</ul>
{body}
</main>
<script>{JS}</script>
</body></html>
'''


# ---------------------------------------------------------------- pin map (vertical, like the photo)
YEL, RED, BLK, BLU, GRN, WHT = '#c99a00', '#d7263d', '#1d1d1f', '#1f6fd1', '#1f9d55', '#ffffff'
AMP = '#7b5ea7'
TOUCH = '#c87533'   # copper, as in the assembly guide's touch wires
USED = {
    1: (RED, 'IMU 红 3.3 V'),
    3: (BLU, 'IMU 蓝 SDA'),
    5: (YEL, 'IMU 黄 SCL'),
    7: (GRN, '串口绿 A7Z 发'),
    9: (BLK, 'IMU 黑 GND'),
    11: (WHT, '串口白 A7Z 收'),
    17: (TOUCH, '触摸板 3.3 V'),
    25: (TOUCH, '触摸板 GND'),
    29: (TOUCH, '触摸板 SCL'),
    31: (TOUCH, '触摸板 SDA'),
    35: (AMP, '功放 LRC'),
    39: (AMP, '功放 GND'),
    2: (RED, '5 V 线 红'),
    4: (AMP, '功放 Vin 5 V'),
    6: (BLK, '5 V 线 黑 GND'),
    12: (AMP, '功放 BCLK'),
    40: (AMP, '功放 DIN'),
}
NOTE = {8: '调试串口 空着', 10: '调试串口 空着'}


def pin_map_svg() -> str:
    W, top, dy = 420, 74, 31
    xin, xed = 190, 230
    rows = []
    rows.append(f'<rect x="0" y="0" width="{W}" height="{top + 20 * dy + 20}" fill="#ffffff"/>')
    rows.append(f'<text x="{xin + 13}" y="26" class="hd" text-anchor="end">里排（单号）</text>')
    rows.append(f'<text x="{xed + 13}" y="26" class="hd" text-anchor="start">外排（双号，靠板边）</text>')
    rows.append(f'<text x="{(xin + xed) / 2 + 13}" y="52" class="sub" text-anchor="middle">天线插座这一头</text>')
    # camera band on the edge row, pins 10 to 34
    y10, y34 = top + 4 * dy, top + 16 * dy
    rows.append(f'<rect x="{xed - 4}" y="{y10 - 4}" width="34" height="{y34 - y10 + 34}" rx="6" fill="#eceff1" stroke="#90a4ae" stroke-dasharray="5 4"/>')
    rows.append(f'<text x="{W - 10}" y="{(y10 + y34) / 2 + 60}" class="cam" text-anchor="middle" '
                f'transform="rotate(-90 {W - 10} {(y10 + y34) / 2 + 60})">摄像头下沿在这段插头前约 2 mm</text>')
    for k in range(20):
        y = top + k * dy
        for n, x, anchor, lx in ((2 * k + 1, xin, 'end', xin - 10), (2 * k + 2, xed, 'start', xed + 36)):
            col, lab = USED.get(n, (None, None))
            if col:
                stroke = '#607d8b' if col == WHT else col
                rows.append(f'<rect x="{x}" y="{y}" width="26" height="26" rx="4" fill="{col}" stroke="{stroke}" stroke-width="2"/>')
                tc = '#1b1b1b' if col in (WHT, YEL) else '#ffffff'
            else:
                rows.append(f'<rect x="{x}" y="{y}" width="26" height="26" rx="4" fill="#f5f5f5" stroke="#b0bec5"/>')
                tc = '#90a4ae'
            rows.append(f'<text x="{x + 13}" y="{y + 18}" class="pn" fill="{tc}" text-anchor="middle">{n}</text>')
            if lab:
                cls = 'lab'
                rows.append(f'<text x="{lx}" y="{y + 18}" class="{cls}" text-anchor="{anchor}">{lab}</text>')
            elif n in NOTE:
                rows.append(f'<text x="{lx}" y="{y + 18}" class="note" text-anchor="{anchor}">{NOTE[n]}</text>')
    yb = top + 20 * dy + 4
    rows.append(f'<text x="{(xin + xed) / 2 + 13}" y="{yb + 8}" class="sub" text-anchor="middle">microSD 卡这一头</text>')
    H = yb + 20
    return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="A7Z 40 针排针，竖着放，1 号针在上：用到的针和线">'
            '<style>.hd{font:700 15px "PingFang SC","Hiragino Sans GB",sans-serif;fill:#263238}'
            '.sub{font:500 13px "PingFang SC","Hiragino Sans GB",sans-serif;fill:#546e7a}'
            '.pn{font:700 13px sans-serif}.lab{font:600 14px "PingFang SC","Hiragino Sans GB",sans-serif;fill:#1b1b1b}'
            '.pending{fill:#bf360c}.note{font:500 13px "PingFang SC","Hiragino Sans GB",sans-serif;fill:#78909c}'
            '.cam{font:600 13px "PingFang SC","Hiragino Sans GB",sans-serif;fill:#607d8b}</style>'
            + ''.join(rows) + '</svg>')


# ---------------------------------------------------------------- photos
TOP_W = 760
LAND_TOP = [('A', P.IPEX_TOP, 22, 150), ('F', P.FAN_TOP, 22, 40), ('SD', P.SD_END_TOP, 0, 1320)]


def top_fig(pins, landmarks=()):
    return uri(P.top_figure(pins, landmarks), TOP_W)


IMG_COUNT = top_fig([(1, '#ffd600'), (2, '#e53935'), (39, '#ffd600'), (40, '#e53935')], LAND_TOP)
IMG_BOTTOM = uri(P.bottom_figure(), TOP_W)
IMG_POWER = top_fig([(2, '#e53935'), (4, '#7b5ea7'), (6, '#1d1d1f')],
                    [('U1', P.USBC1_TOP, 30, 1130), ('U2', P.USBC2_TOP, 30, 880)])
IMG_IMU = top_fig([(1, '#d7263d'), (3, '#1f6fd1'), (5, '#c99a00'), (9, '#1d1d1f')])
IMG_UART = top_fig([(7, '#1f9d55'), (11, '#ffffff'), (8, '#9e9e9e'), (10, '#9e9e9e')])
IMG_AUDIO = top_fig([(4, '#7b5ea7'), (12, '#f9a825'), (35, '#7b5ea7'), (39, '#7b5ea7'), (40, '#7b5ea7')])
IMG_TOUCH = top_fig([(17, TOUCH), (25, TOUCH), (29, TOUCH), (31, TOUCH)])
IMG_XIAO = uri(P.xiao_figure([('3V3', '17', TOUCH), ('GND', '25', TOUCH), ('D5', '29', TOUCH), ('D4', '31', TOUCH)]), 1100)
IMG_ANT_PHOTO = top_fig([(1, '#ffd600')], [('A', P.IPEX_TOP, 22, 150), ('F', P.FAN_TOP, 22, 40)])


def cad(name: str, width: int = 1100) -> str:
    return uri(Image.open(IMG / f'{name}.png'), width, quality=86)


# ================================================================ PAGE 1: A7Z-PINS.html
PIN_LEGEND_COUNT = [
    ('pin', '1', '1 号针：最上面，里排（靠板子中间那排）。官方图上涂黄。'),
    ('pin', '2', '2 号针：1 号针右边，外排（靠板边那排）。官方图上涂红。'),
    ('pin', '39', '39、40 号针：最下面一对，靠 microSD 卡那头。'),
    ('land', 'A', '天线插座（IPEX 接头，同轴天线小插头的座子），金色小圆座。'),
    ('land', 'F', '白色小风扇插座，挨着天线插座。'),
    ('land', 'SD', 'microSD 卡槽在背面的这一头（见右图）。'),
]

S_CHANGES = '''
<section class="step" id="changes"><div class="stepno">先看一眼</div><h2>和 Pi 的版本比，变了什么</h2>
<p>Radxa Cubie A7Z（瑞莎的小电脑板，换掉 Pi Zero W）装在头壳里原来 Pi 的位置：同样的四个螺丝孔（58 × 23 mm），排针在同一个地方。所以每根线都还够得着，只是有几根换了针。</p>
<div class="card">
<p><b>为什么要换针：</b></p>
<ul class="acts">
<li>A7Z 和 Pi 的 1 号针在<b>不同的一头</b>。Pi 的指南从 microSD 卡那头数；在 A7Z 上要从天线插座那头数（第 1 步）。</li>
<li>A7Z 的 8、10 号针是<b>调试串口</b>（debug console，开机信息和登录用，115200 波特率）。它们空着，出问题时可以夹一根 USB 转串口线救急。</li>
<li>新的摄像头板（32 mm 宽）比原来的大，下沿正好在排针中段（7 到 34 号）插头末端前面约 2 mm。这一段的线要贴着插头末端往下折（第 6、7 步、合头壳那步），插头照常插。</li>
<li>串口用里排的 7、11 号针：Radxa 的 UART2 就在这两根针上（8、10 号是调试串口）。功放地线用 39 号，离摄像头最远，插拔方便。</li>
<li>IMU 四根线针号不变（红 1、蓝 3、黄 5、黑 9）：Pi 上 IMU 已经在 3、5 号针的硬件 I2C 上（2026-10-14 从 7、13 号挪回），A7Z 的硬件 I2C（TWI7）也在这两根针上。</li>
<li><b>新加的触摸板</b>（XIAO ESP32-S3，读头壳里的五块铜箔）有四根线，全插里排：17（3.3 V）、25（GND）、29（SCL）、31（SDA）。外排 10 到 34 号的插头末端被摄像头挡着，所以只用里排（第 7 步，D-013）。</li>
</ul></div>
<div class="card">
<p><b>换针的线（小旗要改，第 2 步）：</b>串口绿 8 → 7，串口白 10 → 11，功放 GND 34 → 39。</p>
<p><b>不变的线：</b>IMU 红 1、蓝 3、黄 5、黑 9，5 V 线红 2、黑 6，功放 Vin 4、LRC 35、DIN 40。</p>
<p><b>新的线（焊在触摸板上时就贴好了小旗）：</b>触摸板 3.3 V 17，GND 25，SCL 29，SDA 31。</p>
<p><b>功放 BCLK：</b>A7Z 上只有 12 号针能出 I2S0 的 BCLK，用普通杜邦插头，线贴着插头末端往下折（第 6 步）。</p>
</div>
<p>Pi 的版本还在：<a href="BRINGUP.html">BRINGUP.html</a>。</p>
</section>'''

S_COUNT = step('count', '第 1 步 · 最重要', '先认 1 号针：从天线插座那头数', '你能在 A7Z 上指出 1 号针和 2 号针，知道从哪一头往下数。', f'''
<div class="warn"><b>A7Z 的 1 号针在天线插座那一头，不在 microSD 卡那一头。</b>照 Pi 的习惯从 microSD 卡那头数，整排都会插反，5 V 会插到信号针上。</div>
<ol class="acts">
<li>{tag('hand')}板子元件面朝你，竖着拿：金色的天线插座（A）和白色风扇插座（F）在上面，排针在右边。</li>
<li>{tag('hand')}排针有两排。靠板子中间的叫<b>里排</b>，全是单号：1、3、5 … 39。靠板边的叫<b>外排</b>，全是双号：2、4、6 … 40。</li>
<li>{tag('hand')}最上面一对：左边（里排）是 1 号，右边（外排）是 2 号。从上往下数：里排第 k 根是 2k − 1 号，外排第 k 根是 2k 号。</li>
<li>{tag('hand')}翻过来看背面：microSD 卡槽（SD）在最下面。看到 microSD 卡的那一头是 39、40 号针。</li>
</ol>
<div class="pair">
{figure(IMG_COUNT, 'A7Z 正面竖放：1、2 号针在天线插座那头，39、40 号在 microSD 那头', 'A7Z 正面（Radxa 官方照片）。针上的颜色是 Radxa 标的功能，不是线的颜色。', PIN_LEGEND_COUNT)}
{figure(IMG_BOTTOM, 'A7Z 背面竖放：microSD 卡槽在下面，1 号针的孔在左上', 'A7Z 背面（Radxa 官方照片），绕竖着的长边翻过来：排针的孔到了左边。', [('pin', '1', '1 号针的孔：在天线插座那头，靠板子中间那一列。'), ('land', 'SD', 'microSD 卡槽：这一头是 39、40 号针。')])}
</div>
<h3>全部 17 根线插在哪里</h3>
<p>和上面照片同一个方向：1 号针在上，里排在左，外排在右。灰色的针空着。</p>
<figure class="narrow">{pin_map_svg()}<figcaption>紫色是功放的线，铜色是触摸板的线（颜色随意，按小旗认）。外排的灰色虚线框：摄像头下沿在这一段插头前面约 2 mm，线要贴着插头折。</figcaption></figure>
<div class="card"><b>装进头壳以后：</b>板子竖着，排针在下边，1 号针和天线插座那头在机器人<b>左边</b>。组装指南的顺序是先把板子装上导轨，再插线：功放的五根和触摸板的四根在线夹和天线装好以后插，从躯干上来的八根在合头壳的时候插。</div>
''')

S_FLAGS = step('flags', '第 2 步 · 2 分钟', '改三个小旗', '每个插头后面的小旗都写着 A7Z 上的针号。', f'''
<p>小旗就是插头后面贴的那条纸胶带，上面写着针号。先改旗，再插线，插的时候只看旗。</p>
<ol class="acts">
<li>{tag('hand')}串口 <span class="wire" style="background:{GRN}"></span>绿线：8 改成 <b>7</b>。</li>
<li>{tag('hand')}串口 <span class="wire" style="background:{WHT}"></span>白线：10 改成 <b>11</b>。</li>
<li>{tag('hand')}功放 GND：34 改成 <b>39</b>。</li>
</ol>
<p>IMU 四根线的小旗不变：红 1、蓝 3、黄 5、黑 9（没贴旗的现在贴上）。其余小旗也不变：5 V 线红 2、黑 6，功放 Vin 4、BCLK 12、LRC 35、DIN 40。</p>
<p>触摸板的四根线是新的，焊线时已经贴好旗：17、25、29、31。看一眼四个旗都在，字看得清。</p>
''')

S_POWER = step('power', '第 3 步 · 5 分钟', '5 V 电源线：红插 2 号针，黑插 6 号针', '5 V 线的红插头在 2 号针，黑插头在 6 号针，MR30 接头还断开着。', f'''
<div class="warn"><b>2 号和 4 号针都是 5 V。</b>插偏一根就可能烧板子。插完再数一遍。</div>
<ol class="acts">
<li>{tag('hand')}先断开 5 V 线上的 MR30 接头（两针的小电源插头），整一步不通电。</li>
<li>{tag('hand')}红插头（小旗 2）插<b>外排第 1 根</b>，就是 2 号针。</li>
<li>{tag('hand')}黑插头（小旗 6）插<b>外排第 3 根</b>，就是 6 号针。中间的外排第 2 根（4 号针）留给功放 Vin。</li>
</ol>
<p>这根线的电从背包来：台架背包里是 XL4015 #2（5.00 V），电池背包里是 DFR1202。两种背包都经 MR30 接头接到这根线（D-010）。</p>
<div class="pair">
{figure(IMG_POWER, '2、4、6 号针和两个 USB-C 口', 'A7Z 正面，竖放。', [('pin', '2', '2 号针：5 V 线红'), ('pin', '4', '4 号针：功放 Vin（第 6 步）'), ('pin', '6', '6 号针：5 V 线黑'), ('land', 'U1', 'USB-C 电源口（Radxa 叫接口 1，USB 2.0 OTG 和供电）'), ('land', 'U2', 'USB-C 3.1 口（接口 2，数据和显示）')])}
<div>
<div class="warn"><b>2 号针有电时，两个 USB-C 口都不插线。</b>
<p>原理图第 13、14 页：USB-C 电源口（U1）的 5 V 只经过一个磁珠 FB2（ferrite bead，滤高频干扰的小元件，不挡电流）就到板上的 5 V 线 VCC5V0_SYS；2、4 号针就接在这同一条线上。两路 5 V 会直接顶在一起，电脑或充电器的 5 V 也可能被倒灌。</p>
<p>另一个 USB-C（U2）的 5 V 经过板上一颗电源开关芯片（原理图 U4），但手册没写它能不能挡住反向的电，所以一样处理。</p>
<p>要插 USB-C（刷机、用 Mac 供电、传数据），先断开 MR30。</p></div>
</div></div>
''')

S_IMU = step('imu', '第 4 步 · 5 分钟', 'IMU：红 1、蓝 3、黄 5、黑 9', 'IMU 的 4397 线四个插孔插在 1、3、5、9 号针上。', f'''
<p>和 Pi 一样用那根 4397 线（一头白色小插头插 IMU，另一头红、黑、蓝、黄四个插孔）。全在<b>里排</b>：</p>
<ol class="acts">
<li>{tag('hand')}<span class="wire" style="background:{RED}"></span>红（3.3 V）插里排第 1 根，1 号针。</li>
<li>{tag('hand')}<span class="wire" style="background:{BLU}"></span>蓝（SDA，数据线）插里排第 2 根，3 号针。</li>
<li>{tag('hand')}<span class="wire" style="background:{YEL}"></span>黄（SCL，时钟线）插里排第 3 根，5 号针。</li>
<li>{tag('hand')}<span class="wire" style="background:{BLK}"></span>黑（GND，地）插里排第 5 根，9 号针。里排第 4 根（7 号）留给串口绿线。</li>
</ol>
<div class="pair">
{figure(IMG_IMU, 'IMU 用的 1、3、5、9 号针', 'A7Z 正面，竖放。四根都在里排。', [('pin', '1', '红 3.3 V'), ('pin', '3', '蓝 SDA'), ('pin', '5', '黄 SCL'), ('pin', '9', '黑 GND')])}
<div class="card">
<p><b>1 号针是 3.3 V，</b>原理图上来自 DCDC1，不是 5 V。IMU 板吃 3.3 V。</p>
<p><b>3、5 号针就是 TWI7：</b>Radxa 的 overlay 说明写的是 “On Radxa Cubie A7Z this is SDA pin 3 & SCL pin 5.”（第 9 步打开它）。</p>
<p>IMU 那头和以前一样：扫不到 4a 时，把白色小插头换到 IMU 的另一个白色插座。</p>
</div></div>
''')

S_UART = step('uart', '第 5 步 · 5 分钟', 'OpenRB 串口：绿 7、白 11，8 和 10 空着', '绿线插 7 号针，白线插 11 号针，8、10 号针空着。', f'''
<p>就是第 11 步焊在 OpenRB 那两根线，另一头的插头改插这里。也在<b>里排</b>，紧接着 IMU：</p>
<ol class="acts">
<li>{tag('hand')}<span class="wire" style="background:{GRN}"></span>绿（小旗 7）插里排第 4 根，7 号针。A7Z 从这根<b>发</b>（TX），进 OpenRB 的 Rx 孔。</li>
<li>{tag('hand')}<span class="wire" style="background:{WHT}"></span>白（小旗 11）插里排第 6 根，11 号针。A7Z 从这根<b>收</b>（RX），来自 OpenRB 的 Tx 孔。</li>
<li>{tag('hand')}外排第 4、5 根（8、10 号）不插：那是调试串口。</li>
</ol>
<p>插完以后里排最上面 6 根从上往下正好是：<b>红、蓝、黄、绿、黑、白</b>。</p>
<div class="pair">
{figure(IMG_UART, '串口用的 7、11 号针，8、10 号空着', 'A7Z 正面，竖放。灰圈的 8、10 号空着。', [('pin', '7', '绿：A7Z 发 → OpenRB Rx'), ('pin', '11', '白：A7Z 收 ← OpenRB Tx'), ('pin', '8', '空着：调试串口'), ('pin', '10', '空着：调试串口')])}
<div class="card">
<p><b>为什么是 7、11：</b>Radxa 的 UART2 overlay 写着 “On Radxa Cubie A7Z, TX is pin 7 and RX is pin 11.” 7、11 在里排，摄像头板不挡。</p>
<p><b>为什么 8、10 空着：</b>Radxa 串口调试文档：UART0_TX 是 Pin8，UART0_RX 是 Pin10，115200 波特率，系统在这里输出开机信息和登录提示。接 OpenRB 会和它打架。</p>
<p><b>电平：</b>7、11 号针是 3.3 V 电平，和 OpenRB 的串口一样，直接对接，不用电平转换板。原理图第 14 页：7、11 号针就是 PB0、PB1，中间没有别的零件；第 4 页：给这组引脚供电的 VCC-IO 是 3.3 V。</p>
<p>接反了不会坏东西：以后扫不到舵机，先把绿、白两个插头对调再试。</p>
</div></div>
''')

S_AUDIO = step('audio', '第 6 步 · 5 分钟', '功放：Vin 4、BCLK 12、LRC 35、GND 39、DIN 40', '功放的五个插头都插好，BCLK 的线贴着插头折下来。', f'''
<p>功放（MAX98357A）五根线在第 13 步已经焊好，插头后面有小旗。这一步只插线，不试声音。</p>
<ol class="acts">
<li>{tag('hand')}小旗 4（Vin，5 V）插<b>外排第 2 根</b>，4 号针。</li>
<li>{tag('hand')}小旗 35（LRC）插<b>里排第 18 根</b>，倒数第 3 根，35 号针。</li>
<li>{tag('hand')}小旗 39（GND，原来写 34）插<b>里排最后一根</b>，39 号针。</li>
<li>{tag('hand')}小旗 40（DIN）插<b>外排最后一根</b>，40 号针。</li>
<li>{tag('hand')}小旗 12（BCLK）插<b>外排第 6 根</b>，12 号针。插好后把线贴着插头末端往下折：头壳合上后摄像头板就在插头前面约 2 mm。</li>
</ol>
<div class="warn"><b>4 号针是 5 V：</b>Vin 插错针会烧板子，插完再数一遍。</div>
<div class="pair">
{figure(IMG_AUDIO, '功放用的 4、12、35、39、40 号针', 'A7Z 正面，竖放。', [('pin', '4', 'Vin（5 V）'), ('pin', '12', 'BCLK'), ('pin', '35', 'LRC'), ('pin', '39', 'GND（原来 34）'), ('pin', '40', 'DIN')])}
</div>
<p>36、38 号针也空着（Radxa 的 I2S0 overlay 把它们设成 MCLK 和 DIN0，功放用不到）。</p>
''')

S_TOUCH = step('touch', '第 7 步 · 5 分钟', '触摸板：3.3 V 17、GND 25、SCL 29、SDA 31', '触摸板的四个插头插在里排的 17、25、29、31 号针上，每根线贴着插头往下折。', f'''
<p>触摸板就是贴在头壳左内壁的 Seeed XIAO ESP32-S3（seeedstudio.com 买的那块小板，21 × 17.8 mm）。它读头壳里五块铜箔的电容，再通过 I2C（两根线的总线）报给 A7Z。九根线在组装指南的 “Stick the five copper touch pads and the XIAO inside the cap” 那一步已经焊好：五根去铜箔，四根带插头和小旗来这里。四根全在<b>里排</b>：</p>
<ol class="acts">
<li>{tag('hand')}小旗 17（3.3 V，XIAO 的 3V3 焊盘）插<b>里排第 9 根</b>，17 号针。</li>
<li>{tag('hand')}小旗 25（GND，XIAO 的 GND 焊盘）插<b>里排第 13 根</b>，25 号针。</li>
<li>{tag('hand')}小旗 29（SCL，时钟线，XIAO 的 D5）插<b>里排第 15 根</b>，29 号针。</li>
<li>{tag('hand')}小旗 31（SDA，数据线，XIAO 的 D4）插<b>里排第 16 根</b>，31 号针，紧挨着 29 下面。</li>
<li>{tag('hand')}每根线在插头根部往下折，和 39 号的功放地线一样；再顺着 A7Z 正面往上、翻过板子上边沿，沿左内壁回到 XIAO。</li>
</ol>
<div class="warn"><b>17 号针是 3.3 V，XIAO 的 3V3 只能接 3.3 V。</b>小旗 17 绝不能插到 2、4 号针（5 V）上。插完从天线插座那头再数一遍：里排第 9 根。</div>
<div class="pair">
{figure(IMG_TOUCH, 'A7Z 正面竖放：触摸板用的 17、25、29、31 号针', 'A7Z 正面，竖放。四根都在里排。', [('pin', '17', '3.3 V（和 1 号针是同一路 3.3 V）'), ('pin', '25', 'GND'), ('pin', '29', 'SCL'), ('pin', '31', 'SDA')])}
{figure(IMG_XIAO, 'XIAO ESP32-S3 正面：3V3、GND、D4、D5 四个焊盘', 'XIAO ESP32-S3 正面（Seeed 官方引脚图，裁了中间一段）。USB-C 口在上。圈里的数字是这根线插的 A7Z 针号。', [('pin', '17', '3.3V-OUT 焊盘（右边第 3 个）→ A7Z 17 号针'), ('pin', '25', 'GND 焊盘（右边第 2 个）→ A7Z 25 号针'), ('pin', '29', 'D5 焊盘（左边第 6 个，I2C 的 SCL）→ A7Z 29 号针'), ('pin', '31', 'D4 焊盘（左边第 5 个，I2C 的 SDA）→ A7Z 31 号针')])}
</div>
<div class="card">
<p><b>为什么是这四根：</b>原理图第 14 页，17 号针和 1 号针接在同一路 3.3 V（DCDC1）上，25 号针是地；29、31 号针是 PB2、PB3，Radxa 的引脚表上这两根的功能里有 TWI0-SCK 和 TWI0-SDA（A7Z 的 0 号 I2C）。外排被摄像头挡着，所以 I2C 放在里排的这一对空针上（D-013）。</p>
<p><b>电平：</b>XIAO 的引脚是 3.3 V，A7Z 这两根针也是 3.3 V（和 7、11 号同一组 PB 引脚），直接对接。</p>
</div>
''')

S_CHECK = step('check', '第 8 步 · 10 分钟', '通电前检查，再接 MR30', '万用表确认 5 V 没有跑到信号线上，照片对过一遍，然后才接 MR30 通电。', f'''
<h3>万用表蜂鸣档（MR30 断开，不通电）</h3>
<p>排针上插满了插头，表笔碰不到针，所以都在线的另一头量。MR30 指 A7Z 这边的 MR30 插头。</p>
<ol class="acts">
<li>{tag('hand')}MR30 的红线针和黑线针之间（就是 2 号针和 6 号针）：<b>不能一直响</b>。“嘀”一声就停是板上的电容在充电，正常。</li>
<li>{tag('hand')}功放板上的 Vin 孔和 MR30 红线针：<b>响</b>（4 号和 2 号是同一条 5 V）。功放的 GND 孔和 MR30 黑线针：<b>响</b>。</li>
<li>{tag('hand')}OpenRB 的 Rx 孔（绿线）和 MR30 红线针：<b>不响</b>。Tx 孔（白线）和 MR30 红线针：<b>不响</b>。</li>
<li>{tag('hand')}IMU 板上的 SDA、SCL 两个孔，分别和 MR30 红线针：<b>不响</b>。</li>
<li>{tag('hand')}XIAO 的 3V3 焊盘和 MR30 红线针：<b>不响</b>（不响才说明 17 号线没插到 5 V 上）。XIAO 的 3V3 焊盘和 IMU 板的 VIN 孔：<b>响</b>（17 号和 1 号是同一路 3.3 V）。</li>
<li>{tag('hand')}XIAO 的 GND 焊盘和 MR30 黑线针：<b>响</b>。XIAO 的 D4、D5 焊盘，分别和 MR30 红线针：<b>不响</b>。</li>
</ol>
<p>有一条不对，就是插偏了一根针：回第 1 步再数一遍。</p>
<h3>照着数一遍，拍张照片发给我</h3>
<div class="card">
<p><b>里排，从天线插座那头往下：</b>红、蓝、黄、绿、黑、白（第 1 到 6 根），第 7、8 根空，第 9 根触摸板 3.3 V（17），第 10 到 12 根空，第 13 根触摸板 GND（25），第 14 根空，第 15 根触摸板 SCL（29），第 16 根触摸板 SDA（31），第 17 根空，第 18 根 LRC，第 19 根空，第 20 根 GND。里排一共 12 根线。</p>
<p><b>外排，从天线插座那头往下：</b>红（5 V）、Vin、黑（5 V 地），第 4、5 根空（调试串口），第 6 根 BCLK，第 7 到 19 根空，第 20 根 DIN。外排一共 5 根线。</p>
<p><b>合计 17 根：</b>里排 12 根加外排 5 根。数出来不是 17，先别通电。</p>
</div>
<h3>通电</h3>
<ol class="acts">
<li>{tag('hand')}两个 USB-C 口都没插线，再接上 MR30。</li>
<li>{tag('hand')}A7Z 的电源灯亮绿色（Radxa 文档：“若 Cubie A7Z 供电正常，电源指示灯将显示为绿色”）。IMU 上的小绿灯也亮。</li>
<li>{tag('hand')}万用表直流电压档，量功放的 Vin 和 GND 两个孔：4.9 到 5.1 V。超过 5.25 V 马上断开 MR30。</li>
<li>{tag('hand')}再量 XIAO 的 3V3 和 GND 两个焊盘：3.2 到 3.4 V。低于 3.2 V 就断开 MR30，告诉我（触摸板吃电太多，把 3.3 V 拉低了）。</li>
</ol>
''')

S_SOFT = step('software', '第 9 步 · 10 分钟', '打开 I2C、串口和 I2S', 'A7Z 上有 7 号 I2C 总线和 UART2 的串口，IMU 在 7 号总线上答 4a。', f'''
<p>这三个接口默认是关着的，要在 Radxa 的设置工具 rsetup 里打开（overlay，设备树叠加，告诉系统这几根针接了什么）。</p>
<ol class="acts">
<li>{tag('mac')}ssh 登录 A7Z。Radxa 系统的默认用户是 radxa（文档里的命令提示符是 <code>radxa@cubie-a7z</code>）；装系统时改过名字就换成你的。
{cmd('mac', 'ssh radxa@cubie-a7z.local')}</li>
<li>{tag('a7z')}打开设置工具：
{cmd('a7z', 'sudo rsetup')}
进 <b>Overlays</b> → <b>Manage overlays</b>。方向键移动，空格勾选，回车确定。勾上这三项：
<ul>
<li><b>Enable TWI7</b>：IMU 的 I2C，3、5 号针。</li>
<li><b>Enable UART2</b>：OpenRB 串口，7、11 号针。</li>
<li><b>Enable I2S0</b>：功放的声音，12、35、40 号针。</li>
</ul>
第四项是触摸板的 <b>Enable TWI0</b>（29、31 号针）：待定，列表里没有它，原因在下面黄框里。<br>
Radxa 文档的原话：“进入 <code>rsetup</code> 的 <code>Overlay</code> -&gt; <code>Manage overlays</code> 勾选 <code>Enable TWI7</code> 选项，勾选后重启系统”。</li>
<li>{tag('a7z')}重启，1 分钟后重新 ssh 登录：
{cmd('a7z', 'sudo reboot')}</li>
<li>{tag('a7z')}看串口：
{cmd('a7z', 'ls /dev/ttyAS*', '/dev/ttyAS0  /dev/ttyAS2', '应该看到（ttyAS0 是调试串口）')}
UART2 应该叫 <code>/dev/ttyAS2</code>：Radxa 文档里 UART4 叫 <code>/dev/ttyAS4</code>，照这个规律推出来的。名字不一样就把你看到的告诉我。</li>
<li>{tag('a7z')}装 I2C 扫描工具（装过会直接提示）：
{cmd('a7z', 'sudo apt install -y i2c-tools')}</li>
<li>{tag('a7z')}扫描 7 号总线：
{cmd('a7z', 'sudo i2cdetect -y -r 7', '''     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
...
40: -- -- -- -- -- -- -- -- -- -- 4a -- -- -- -- --
...''', '应该看到一张表，40 那一行的 a 列是 4a（4b 也对）')}
</li>
</ol>
<div class="card">
<p><b>脚本要改：</b>我们的脚本（scan_bus.py、imu_read.py 等）现在还按 Pi 写的：串口 <code>/dev/serial0</code>，I2C 3 号总线。脚本里的串口和总线号要改成这两个：串口 <code>/dev/ttyAS2</code>，I2C <b>7</b> 号总线。这个由协调这件事的那个会话来改，改好之前先别跑这些脚本。</p>
</div>
<div class="pend" id="twi0"><b>触摸板的 Enable TWI0：A7Z 上还没有能用的 overlay</b>
<p>Radxa 现成的 Enable TWI0 overlay（sun60iw2p1-twi0.dtso）是给另一块板子 CM-A7（插在树莓派 CM5 底板上）写的：它只声明支持 <code>radxa,cm-a7-rpi-cm5-io</code>，用的是 PG8、PG9 两个引脚。rsetup 只列出声明支持这块板的 overlay，所以在 A7Z 的列表里看不到它；就算硬装上，它设置的也是 PG8、PG9，不是 A7Z 29、31 号针上的 PB2、PB3。</p>
<p>A7Z 能做 I2C 的另一对 TWI2 在 27、28 号针，28 号在外排，被摄像头挡着。所以 29、31 号针上的 I2C 要用一个自己写的 overlay：首选让 TWI0 用 PB2、PB3；备选是在同样两根针上用软件模拟的 I2C（i2c-gpio）。速度 100 kHz，上拉用 A7Z 和 XIAO 两边芯片里自带的上拉电阻（板上没有上拉电阻）。</p>
<p>这个 overlay 在台架验收时由我写好并在板子上验证，验证过才会加到这一页。现在不用找它，也不要自己装别处的 TWI0 overlay。触摸板的线照样插（第 7 步），只是在那之前 A7Z 读不到它。</p></div>
<div class="pend"><b>声音：还没在这块板上试过</b>
<p>Radxa 的 Enable I2S0 overlay 做的是一张两声道的“空壳”声卡（dummy sound card），它自己的说明写着 “This overlay is only for demonstration purpose. It does not support any specific hardware device.”。MAX98357A 上电就工作，系统不用给它写任何设置（不需要 codec 驱动），所以预计这张空壳声卡能带它，但还没验证。</p>
<p>喇叭试音先不做：那道 −3 dB 的音量上限（D-012）在 A7Z 上还没设好，也等 12 号针的接法定下来。到时由我通过 ssh 来做。</p></div>
<details><summary>不成功时</summary><ul>
<li>表里全是 <code>--</code>，IMU 绿灯不亮：红线或黑线插错了针，回第 4 步。</li>
<li>表里全是 <code>--</code>，绿灯亮：蓝、黄插反或插偏了一根。再数：蓝是里排第 2 根，黄是里排第 3 根。都对的话把 IMU 那头的白色小插头换一个插座。</li>
<li>提示 <code>Could not open file /dev/i2c-7</code>：Enable TWI7 没勾上，或勾完没重启。</li>
<li>没有 <code>/dev/ttyAS2</code>：Enable UART2 没勾上，或勾完没重启。</li>
<li>Overlays 列表里找不到 Enable TWI0：正常，见上面黄框。</li>
</ul></details>
''')

SOURCES_PINS = '''
<section class="step" id="sources"><h2>依据</h2><ul class="src">
<li>40 针功能表、rsetup 操作、UART4 = /dev/ttyAS4、TWI7 = /dev/i2c-7：Radxa 文档 “40 Pin GPIO 接口”（docs.radxa.com，Cubie A7Z，本地副本 guide/print/a7z-head/sources/radxa-a7z-pin-gpio.md）。</li>
<li>overlay 名字和针脚：radxa-pkg/radxa-overlays 仓库 arch/arm64/boot/dts/allwinner/overlays/ 下 sun60iw2p1-twi7.dtso（Enable TWI7，pin 3/5）、sun60iw2p1-uart2.dtso（Enable UART2，pin 7/11）、sun60iw2p1-i2s0-2ch.dtso（Enable I2S0，pin 36/12/35/38/40）、sun60iw2p1-twi0.dtso（Enable TWI0，compatible 只有 radxa,cm-a7-rpi-cm5-io，PG8/PG9，2026-08-05 加入）。本地副本 bringup/a7z/sources/。</li>
<li>触摸板：DECISIONS.md D-013，组装指南 guide/content/steps.py 的 touch、touch-pi 两步（针脚 17、25、29、31）。XIAO 焊盘：Seeed wiki “Getting Started with Seeed Studio XIAO ESP32S3” 的正面引脚图（D4 = GPIO5 = I2C1_SDA，D5 = GPIO6 = I2C1_SCL，3.3V-OUT，GND），裁剪副本 bringup/a7z/sources/xiao-esp32s3-front-pinout-crop.png。29、31 号针是 PB2、PB3，17 号针接 DCDC1：原理图 V1.11 第 14 页和 Radxa 40 针功能表（TWI0-SCK、TWI0-SDA）。</li>
<li>调试串口 Pin8/Pin10、115200：Radxa 文档 “串口调试”（radxa-a7z-uart-debug.md）。电源灯：“硬件接口”（a7z-hardware-info.md）。</li>
<li>5 V 和 USB-C：Radxa Cubie A7Z 原理图 V1.11 第 13 页（J16 VBUS → FB2 60R 3A → VCC5V0_SYS）、第 14 页（J11 的 2、4 号是 VCC5V0_SYS，1 号 DCDC1，8/10 号 CPUX-TX/RX）、第 12 页（USB 3.1 口 VBUS 经 U4）。</li>
<li>摄像头板和插头的距离：组装指南 CAD（guide/print/world/camera_board.stl 和排针插头的位置），背面元件范围按 Radxa 背面照片，2026-10-15 核对（guide/print/face-a7z/pin-clearance/pin-clearance.png）。接线颜色和小旗沿用 BRINGUP.html 第 4、11、12、13 步。背包电源：DECISIONS.md D-010。</li>
<li>核对日期：2026-10-15。</li></ul></section>'''

PINS_BODY = S_CHANGES + S_COUNT + S_FLAGS + S_POWER + S_IMU + S_UART + S_AUDIO + S_TOUCH + S_CHECK + S_SOFT + SOURCES_PINS
PINS_LEAD = ('<p class="lead">头里的电脑从 Pi Zero W 换成 Radxa Cubie A7Z。这一页一步一步讲 40 针排针上每根杜邦线插哪里，和插好以后要打开的接口。'
             '全程断电插线，最后检查完才通电。</p>')
PINS_NAV = [('changes', '变了什么'), ('count', '1 认针'), ('flags', '2 改小旗'), ('power', '3 5 V'), ('imu', '4 IMU'),
            ('uart', '5 串口'), ('audio', '6 功放'), ('touch', '7 触摸板'), ('check', '8 检查'), ('software', '9 打开接口')]

# ================================================================ PAGE 2: A7Z-ANTENNA.html
ANT_LEGEND = [
    ('pin', '1', '天线（AC019，橙色那片）：贴在头壳顶的前半截，横着放'),
    ('pin', '2', '天线的线头：在机器人左边那一端'),
    ('pin', '3', 'A7Z 的天线插座，IPEX 插头扣在上面'),
    ('pin', '4', '排针 1 号针（同一头，用来认方向）'),
]

A_PARTS = step('parts', '第 1 步 · 2 分钟', '认零件', '手上有 AC019 天线、酒精和布，认得 A7Z 上的天线插座。', f'''
<div class="card">
<p><b>AC019 双频 FPC 天线：</b>A7Z 盒子里附带的那片（FPC，柔性电路板，薄片状，背面是不干胶）。Radxa 文档的规格：</p>
<ul class="acts">
<li>尺寸 42 mm × 11.9 mm，线长 50 mm。</li>
<li>接口：1 代 IPEX（同轴天线小插头，按扣式）。</li>
<li>双频：Wi-Fi 2.4 GHz 和 5 GHz。</li>
</ul>
<p>Radxa 文档写的是：A7Z 板载 WiFi 6 和蓝牙 5.4，“提供 1 个天线接口用于外接天线，以增强无线通信性能”。头壳合上以后你 ssh 用的就是这个 Wi-Fi。</p>
</div>
<p>另外准备：酒精（异丙醇）、不掉毛的布或棉签、记号笔。</p>
<div class="pair">
{figure(IMG_ANT_PHOTO, 'A7Z 正面，天线插座 A 在 1 号针那一头，挨着风扇插座 F', 'A7Z 正面（Radxa 官方照片），竖放。', [('land', 'A', '天线插座：金色小圆座，在元件面'), ('land', 'F', '白色风扇插座，挨着它'), ('pin', '1', '排针 1 号针：同一头')])}
<div class="card"><p><b>天线插座在哪：</b>元件面（有芯片的那面），排针 1 号针那一头，挨着白色风扇插座。</p>
<p>装进头壳后这一头在机器人<b>左边</b>，排针在下边，元件面朝脸。</p></div>
</div>
''')

A_STICK = step('stick', '第 2 步 · 5 分钟', '擦干净，把天线贴在头壳顶的前半截', '天线平贴在白色头壳顶的内面、导轨前面，横着放，线头朝机器人左边；线和插头先垂着，不插。', f'''
<p>头壳翻过来，从下往里看（下图）。天线贴在顶的内面、板子导轨前面（朝脸那边）那块光滑的弧顶上：</p>
<ul class="acts">
<li><b>前后：</b>天线的后边沿在板子正上方往前约 2 mm，往前贴满 11.9 mm 宽。</li>
<li><b>左右：</b>横着，左右居中，42 mm 长几乎占满这里的宽度。</li>
<li><b>线头：</b>朝机器人<b>左边</b>（就是 A7Z 天线插座那一边）。</li>
<li><b>平贴：</b>不干胶那面贴顶，顺着弧面贴平，不要折。不要盖住导轨上的圆垫和螺丝孔。</li>
</ul>
<ol class="acts">
<li>{tag('hand')}先把 A7Z 竖直放到导轨上比一下（不拧螺丝，不沿导轨推），用记号笔在顶上画一条横线：板子元件面正上方往前约 2 mm。拿下板子。</li>
<li>{tag('hand')}酒精擦这块顶，等它干透（约 1 分钟）。</li>
<li>{tag('hand')}撕掉天线背面的纸，后边沿对着那条线，线头朝机器人左边。先按住中间，再往两头压平，沿整个长度压一遍。</li>
<li>{tag('hand')}线和 IPEX 插头从头壳<b>左边</b>那头垂出来，<b>先不插</b>。插头要等板子和线夹都装好以后才插（第 5 步）。</li>
</ol>
{figure(cad('cad_below'), '从下往上看翻过来的头壳：天线贴在顶上，线头在机器人左边', '头壳倒过来拿在手上、往里看（CAD 图，头壳下沿切掉了一截）。图的上方是脸，右边是机器人左边。图里画的是全部装好以后的样子，板子和插好的线是给你对位置用的；这一步还没装板。排针在 A7Z 下边沿，所以这个方向下 1 号针被 2 号针挡住。', ANT_LEGEND[:3])}
<p class="src">渲染里天线画成橙色，实物颜色可能不同。浅蓝的是头壳上的线夹。</p>
''')

A_MOUNT = step('mount', '第 3 步 · 5 分钟', '装板：竖直放下，先不插天线', 'A7Z 用三颗螺丝固定在导轨上，左上角的孔空着留给线夹；天线线还垂在一边，没插。', f'''
<ol class="acts">
<li>{tag('hand')}先插 microSD 卡（系统卡，第 10 章装的系统）。卡槽在 A7Z 背面、离排针 1 号针远的那一头；插好后卡露出约 2 mm。</li>
<li>{tag('hand')}头壳放在头旁边，把摄像头排线的空头插进 A7Z 的摄像头插座，金手指朝板子，扣上卡扣。这个插座在 A7Z 背面、1 号针那一头的板边。</li>
<li>{tag('hand')}用手把功放的五根线和天线线拨到一边。A7Z <b>竖直往下</b>放到两条导轨上：排针朝脸、在下边，1 号针那头在机器人左边。<b>不要沿导轨推进去</b>，板子下面的零件会卡在导轨上。排线绕过板子那头进头壳左边的槽，microSD 卡进右边的槽。板子落在四个圆垫上。</li>
<li>{tag('hand')}先拧左下角（1 号针旁边、天线插座那头）的短螺丝 M2 × 4 TAP，再拧右边两个角的 M2 × 6 TAP。<b>左上角空着</b>，下一步线夹压在那颗螺丝下面。导轨孔是 1.7 mm，M2.5 或 M2.6 的螺丝会把它撑裂。</li>
</ol>
<div class="warn"><b>天线这时还不要插。</b>CAD 检查时发现：插头先插上，线就挡住线夹装进来的路。所以先装线夹，再插天线。</div>
<div class="card"><p><b>装完看一眼：</b>天线还是平的，没有翘角；天线线自由垂着，没被板子压住；左上角的孔还空着；左边导轨背面看不到螺丝尖。</p></div>
''')

A_CLIP = step('clip', '第 4 步 · 2 分钟', '装线夹', '橙色线夹用一颗 M2 × 8 TAP 拧在 A7Z 左上角，卡槽口朝外、空着。', f'''
<ol class="acts">
<li>{tag('hand')}拿 A7Z 版的橙色线夹（底面有一个缺口，正好跨在 micro HDMI 插座上）。V1.9 的线夹没有这个缺口，会在插座上晃，不要用。</li>
<li>{tag('hand')}线夹的耳朵压在左上角空着的孔上，方形卡槽横搭在板子上边沿，槽口朝外（背着板子）。</li>
<li>{tag('hand')}一颗 M2 × 8 TAP 穿过耳朵和板角拧进导轨，螺丝头碰到耳朵就停。</li>
</ol>
<div class="card"><p><b>装完看一眼：</b>耳朵平贴在螺丝头下面，用手拧线夹不转；卡槽口是空的。线夹完整的说明在组装指南的 “Fit the cap wire clip” 那一步。</p></div>
''')

A_PLUG = step('plug', '第 5 步 · 2 分钟', '插 IPEX：竖直按下去，线朝机器人右边', 'IPEX 插头“咔”一声扣在 A7Z 的天线插座上，线沿板面往右走一点，再往前、往上到天线，从线夹前面过。', f'''
<ol class="acts">
<li>{tag('hand')}找插座：A7Z 元件面（朝脸那面），1 号针那头（机器人左边），挨着白色小风扇插座的金色小圆座（第 1 步照片里的 A）。</li>
<li>{tag('hand')}插头正对插座上方，摆正，线朝机器人<b>右边</b>（顺着板面）。用指尖竖直往下按，听到或感到“咔”一声。不要晃着往上扣。</li>
<li>{tag('hand')}理线：线先平贴着板面往右走约 2 mm；然后朝脸的方向离开板面约 10 mm；再往上，贴着顶到天线的线头。线从<b>线夹前面</b>过，不跨排针。弯要圆，不要折成直角。</li>
</ol>
<div class="card"><p><b>插完看一眼：</b>插头平贴在插座上，碰一下线插头不转；线不跨排针，不压线夹的卡槽，也不压线夹那颗螺丝。</p></div>
<div class="warn"><b>绝不拉线拔。</b>要拔的时候，指甲或塑料撬片伸到插头下面，竖直往上撬。</div>
{figure(cad('cad_ipex', 1000), 'IPEX 那一头的近景：插头、线的走向、1 号针', 'IPEX 那一头的近景（CAD 图，头壳前半截和左边切掉了；从前面偏左、稍低处看）。线从插头出来先顺着板面往机器人右边走，再朝脸的方向离开板面，然后往上到天线的线头，一直在浅蓝色线夹的前面。', ANT_LEGEND, 'mid')}
{figure(cad('cad_side'), '从机器人左边看，头壳左半边切掉：天线线从插头往前再往上到天线', '从机器人左边看（CAD 图，头壳左半边切掉）。左边是脸，右边是后脑勺。线从插头往前，再往上到天线，在线夹（浅蓝）前面。', ANT_LEGEND, 'mid')}
<div class="card"><p>CAD 核对过这条路线：用掉 50 mm 线里的 36 mm，剩 14 mm 松量；线和线夹、天线和线夹都不碰，插头离线夹 7.7 mm；线离摄像头板最近 3.8 mm（摄像头板没画在图里）。</p></div>
''')

A_CHECK = step('check', '第 6 步 · 5 分钟', '看 Wi-Fi 信号：盖子开着和合上各记一次', '记下头壳打开和合上时的 Wi-Fi 信号强度，两个数只差一点。', f'''
<ol class="acts">
<li>{tag('mac')}A7Z 通电开机以后，从 Mac ssh 登录（地址和装系统时一样）：
{cmd('mac', 'ssh radxa@cubie-a7z.local')}</li>
<li>{tag('a7z')}看无线网卡的名字：
{cmd('a7z', 'iw dev', 'Interface wlan0', '应该有一行（名字一般是 wlan0，下面用你看到的名字）')}</li>
<li>{tag('a7z')}头壳<b>打开</b>时读一次信号：
{cmd('a7z', 'iw dev wlan0 link', 'Connected to ...\n\tSSID: 你的网络名\n\tsignal: -48 dBm', '应该看到 signal 这一行，单位 dBm（负数，越接近 0 越强）')}</li>
<li>{tag('a7z')}也可以看周围网络的列表，连着的那个前面有 <code>*</code>，SIGNAL 一列是 0 到 100：
{cmd('a7z', 'nmcli dev wifi list')}</li>
<li>{tag('hand')}把头壳<b>合上</b>，等 10 秒，再跑一次 <code>iw dev wlan0 link</code>。</li>
</ol>
<div class="card"><p><b>记下两个数：</b>打开时的 signal 和合上时的 signal，发给我。合上以后应该只比打开时差一点。</p>
<p>差很多，或者合上就断线：先打开看天线是不是翘起来了、IPEX 插头有没有松，再告诉我。</p></div>
''')

SOURCES_ANT = '''
<section class="step" id="sources"><h2>依据</h2><ul class="src">
<li>天线规格（AC019 双频 FPC，1 代 IPEX，42mm × 11.9mm，线长 50mm，Wi-Fi 2.4GHz / 5GHz）：Radxa 文档 “天线接口”，Cubie A7Z（本地副本 guide/print/a7z-head/sources/radxa-a7z-antenna.md、radxa-a7z-ante.md）。</li>
<li>天线插座位置：Radxa 文档 “硬件接口” 的接口图（⑥ 天线接口）和官方正面照片 a7z-top.png。</li>
<li>贴的位置和走线：guide/print/a7z-head/build_a7z_head.py 和 checks.json（天线 x 64 到 75.9 mm、y −21 到 +21 mm，线头在 +Y；线长 36 / 50 mm；线夹和天线、线都不碰）。图由 bringup/a7z/render_cad_views.py 从这些 STL 画出。</li>
<li>线和摄像头板的间距 3.8 mm：guide/print/world/camera_board.stl 与 a7z_parts/antenna_coax.stl 的最近距离，2026-10-15 计算。</li>
<li>顺序（贴天线、装板、装线夹、插 IPEX）和插法：组装指南 guide/content/steps.py 的 antenna、pi、pi-clip、antenna-plug 四步；先插 IPEX 时线挡住线夹的路，是 2026-10-15 的打印检查发现的。插头离线夹 7.7 mm：checks.json。</li>
<li>核对日期：2026-10-15。</li></ul></section>'''

ANT_BODY = A_PARTS + A_STICK + A_MOUNT + A_CLIP + A_PLUG + A_CHECK + SOURCES_ANT
ANT_LEAD = ('<p class="lead">A7Z 的 Wi-Fi 天线是一片带不干胶的软天线，贴在白色头壳顶的内面，用一根 50 mm 的细线插到 A7Z 上。'
            '顺序很重要：先贴天线，再装板子，再装线夹，最后才插 IPEX 插头。插头先插的话，线会挡住线夹。</p>')
ANT_NAV = [('parts', '1 认零件'), ('stick', '2 贴天线'), ('mount', '3 装板'), ('clip', '4 装线夹'), ('plug', '5 插 IPEX'), ('check', '6 看信号')]

if __name__ == '__main__':
    OUT_PINS.write_text(page('A7Z 杜邦线插线', 'A7Z 杜邦线插线指南：每根线插哪根针', PINS_LEAD, PINS_NAV, PINS_BODY), encoding='utf-8')
    OUT_ANT.write_text(page('A7Z 天线安装', 'A7Z 天线安装指南：贴在头壳顶，插到 A7Z', ANT_LEAD, ANT_NAV, ANT_BODY), encoding='utf-8')
    for p in (OUT_PINS, OUT_ANT):
        print(p, p.stat().st_size)
