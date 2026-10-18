#!/usr/bin/env python3
"""Build ../A7Z-WIRES.html: one interactive picture, Pi Zero W pin -> A7Z pin for every Dupont wire.

Pi pins as wired on the robot: IMU 1/3/5/9 on hardware I2C bus 1 (moved back from the 7/13 software bus on
2026-10-14; the BNO085 answered on bus 1 at 0x4a on 2026-10-16), amplifier 4/12/34/35/40, 5 V lead 2/6, UART 8/10.
A7Z pins: build_a7z_pages.py.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'A7Z-WIRES.html'

RED, BLU, YEL, BLK, GRN, WHT = '#d7263d', '#1f6fd1', '#c99a00', '#1d1d1f', '#1f9d55', '#9aa5ad'
AMP, TOUCH = '#7b5ea7', '#c87533'

# id, label, colour, Pi pin (None = new wire), A7Z pin, note
WIRES = [
    ('imu-red', 'IMU 红 3.3 V', RED, 1, 1, ''),
    ('imu-blu', 'IMU 蓝 SDA', BLU, 3, 3, '两块板的硬件 I2C 都在 3、5 号针（Pi 是 1 号总线，A7Z 是 TWI7）'),
    ('imu-yel', 'IMU 黄 SCL', YEL, 5, 5, '两块板的硬件 I2C 都在 3、5 号针（Pi 是 1 号总线，A7Z 是 TWI7）'),
    ('imu-blk', 'IMU 黑 GND', BLK, 9, 9, ''),
    ('pwr-red', '5 V 线 红', RED, 2, 2, ''),
    ('pwr-blk', '5 V 线 黑 GND', BLK, 6, 6, ''),
    ('uart-grn', '串口 绿（A7Z 发 → OpenRB Rx）', GRN, 8, 7, 'A7Z 的 8、10 号是调试串口，空着'),
    ('uart-wht', '串口 白（A7Z 收 ← OpenRB Tx）', WHT, 10, 11, 'A7Z 的 8、10 号是调试串口，空着'),
    ('amp-vin', '功放 Vin 5 V', AMP, 4, 4, ''),
    ('amp-bclk', '功放 BCLK', AMP, 12, 12, 'A7Z 只有 12 号针能出 BCLK；线贴着插头往下折'),
    ('amp-lrc', '功放 LRC', AMP, 35, 35, ''),
    ('amp-din', '功放 DIN', AMP, 40, 40, ''),
    ('amp-gnd', '功放 GND', AMP, 34, 39, '39 号离摄像头最远，好插拔'),
    ('t-3v3', '触摸板 3.3 V（XIAO 3V3）', TOUCH, None, 17, '新线，Pi 上没有'),
    ('t-gnd', '触摸板 GND（XIAO GND）', TOUCH, None, 25, '新线，Pi 上没有'),
    ('t-scl', '触摸板 SCL（XIAO D5）', TOUCH, None, 29, '新线，Pi 上没有'),
    ('t-sda', '触摸板 SDA（XIAO D4）', TOUCH, None, 31, '新线，Pi 上没有'),
]
EMPTY_NOTE = {('a', 8): 'A7Z 8 号：调试串口，空着', ('a', 10): 'A7Z 10 号：调试串口，空着'}

# geometry: both headers drawn the same way: pin 1 on top, odd (inner) column left, even (edge) column right
W, TOP, DY, SQ = 440, 96, 30, 22
PI_X, A7_X = 70, 318          # x of the odd column; the even column is +28
XIAO_X = 214                  # touch board sits in the empty gap between the headers, rows 17 to 31
H = TOP + 20 * DY + 16


def pin_xy(board: str, n: int) -> tuple[float, float]:
    x0 = PI_X if board == 'p' else A7_X
    k = (n - 1) // 2
    return x0 + (0 if n % 2 else 28) + SQ / 2, TOP + k * DY + SQ / 2


def svg() -> str:
    out = [f'<svg id="map" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
           'aria-label="Pi Zero W 排针到 A7Z 排针的接线图">']
    out.append(f'<rect class="bg" x="0" y="0" width="{W}" height="{H}"/>')
    # headings
    for x0, name, end in ((PI_X, 'Pi Zero W（旧）', '1 号针在 microSD 卡那头'), (A7_X, 'A7Z（新）', '1 号针在天线插座那头')):
        cx = x0 + 25
        out.append(f'<text x="{cx}" y="24" class="hd" text-anchor="middle">{name}</text>')
        out.append(f'<text x="{cx}" y="44" class="sub" text-anchor="middle">{end}</text>')
        out.append(f'<text x="{x0 + SQ / 2}" y="{TOP - 14}" class="col" text-anchor="middle">里排</text>')
        out.append(f'<text x="{x0 + 28 + SQ / 2}" y="{TOP - 14}" class="col" text-anchor="middle">外排</text>')
        out.append(f'<rect class="hdr" x="{x0 - 6}" y="{TOP - 6}" width="62" height="{20 * DY + 6}" rx="6"/>')
    # wires (under the pins)
    xe = PI_X + 28 + SQ + 10          # first x past the Pi even column
    for i, (wid, lab, col, p, a, _) in enumerate(WIRES):
        ax, ay = pin_xy('a', a)
        # A7Z end: odd pins take the wire straight from the left; even pins through the row gap above
        if a % 2:
            tail, ey = f'L{ax},{ay}', ay
        else:
            tail, ey = f'L{ax - 14},{ay - DY / 2} L{ax},{ay}', ay - DY / 2
        ex = A7_X - 12
        if p is not None:
            px, py = pin_xy('p', p)
            if p % 2:   # leave the odd pin diagonally into the row gap, then run between the even pins
                head, sy = f'M{px},{py} L{px + 14},{py + DY / 2} L{xe},{py + DY / 2}', py + DY / 2
            else:
                head, sy = f'M{px},{py} L{xe},{py}', py
            d = f'{head} C{xe + 90},{sy} {ex - 90},{ey} {ex},{ey} {tail}'
        else:
            d = f'M{XIAO_X + 44},{ay} {tail}'
        if col == WHT:  # light wire: dark casing underneath so it reads as a solid wire
            out.append(f'<path class="wire case" data-w="{wid}" d="{d}" stroke="#5f6b76"/>')
        out.append(f'<path class="wire" data-w="{wid}" d="{d}" stroke="{'#e9edf0' if col == WHT else col}"/>')
        out.append(f'<path class="hit" data-w="{wid}" d="{d}"/>')
    # pins
    used = {('p', w[3]): w for w in WIRES if w[3]} | {('a', w[4]): w for w in WIRES}
    for board, x0 in (('p', PI_X), ('a', A7_X)):
        for n in range(1, 41):
            cx, cy = pin_xy(board, n)
            w = used.get((board, n))
            if w:
                col = w[2]
                tc = '#1b1b1b' if col in (WHT, YEL) else '#ffffff'
                out.append(f'<g class="pin on" data-b="{board}" data-n="{n}" data-w="{w[0]}">'
                           f'<rect x="{cx - SQ / 2}" y="{cy - SQ / 2}" width="{SQ}" height="{SQ}" rx="4" fill="{col}"/>'
                           f'<text x="{cx}" y="{cy + 4.5}" fill="{tc}" text-anchor="middle">{n}</text></g>')
            else:
                cls = 'pin off dbg' if (board, n) in EMPTY_NOTE else 'pin off'
                out.append(f'<g class="{cls}" data-b="{board}" data-n="{n}">'
                           f'<rect x="{cx - SQ / 2}" y="{cy - SQ / 2}" width="{SQ}" height="{SQ}" rx="4"/>'
                           f'<text x="{cx}" y="{cy + 4.5}" text-anchor="middle">{n}</text></g>')
    # touch board pads, each level with its A7Z pin
    y17, y31 = pin_xy('a', 17)[1], pin_xy('a', 31)[1]
    out.append(f'<rect class="xiao" x="{XIAO_X - 6}" y="{y17 - 22}" width="56" height="{y31 - y17 + 44}" rx="8"/>')
    for k, line in enumerate(('触摸板', 'XIAO', '新加的线', 'Pi 上没有')):
        out.append(f'<text x="{XIAO_X - 14}" y="{y17 + 46 + k * 18}" class="{'xl' if k < 2 else 'sub'}" text-anchor="end">{line}</text>')
    for j, name in enumerate(('3V3', 'GND', 'D5', 'D4')):
        wid = WIRES[13 + j][0]
        y = pin_xy('a', WIRES[13 + j][4])[1]
        out.append(f'<g class="pin on pad" data-b="x" data-n="{name}" data-w="{wid}"><rect x="{XIAO_X}" y="{y - 11}" width="40" height="22" rx="5" fill="{TOUCH}"/>'
                   f'<text x="{XIAO_X + 20}" y="{y + 4.5}" fill="#fff" text-anchor="middle">{name}</text></g>')
    out.append('</svg>')
    return ''.join(out)


def chips() -> str:
    groups = [('换针（改小旗）', [w for w in WIRES if w[3] and w[3] != w[4]]),
              ('针号不变', [w for w in WIRES if w[3] and w[3] == w[4]]),
              ('新加的线', [w for w in WIRES if not w[3]])]
    html = []
    for title, ws in groups:
        html.append(f'<h2>{title} · {len(ws)} 根</h2><div class="chips">')
        for wid, lab, col, p, a, _ in ws:
            src = f'Pi {p}' if p else 'XIAO'
            html.append(f'<button class="chip" data-w="{wid}"><i style="background:{col}"></i>'
                        f'<span class="cl">{lab}</span><span class="pp">{src} → <b>A7Z {a}</b></span></button>')
        html.append('</div>')
    return ''.join(html)


CSS = '''
:root{--bg:#f7f8fa;--card:#fff;--ink:#1b1f24;--mute:#5f6b76;--line:#d5dbe1;--accent:#1565c0}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.5 -apple-system,"PingFang SC","Hiragino Sans GB",sans-serif}
main{max-width:760px;margin:0 auto;padding:16px}
h1{font-size:22px;margin:4px 0 6px}h2{font-size:16px;margin:22px 0 8px}
.lead{color:var(--mute);margin:0 0 12px}
.info{position:sticky;top:0;z-index:2;background:#fffbe6;border:1px solid #f0d77a;border-radius:10px;
padding:10px 12px;margin-bottom:10px;min-height:48px;display:flex;gap:10px;align-items:center;justify-content:space-between}
.info .txt{overflow-wrap:anywhere}.info button{flex:none;font:inherit;font-size:16px;padding:6px 12px;border-radius:8px;
border:1px solid var(--line);background:#fff;cursor:pointer}
.fig{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px}
svg{display:block;width:100%;height:auto}
.bg{fill:#fff}.hdr{fill:#eef1f4;stroke:#b8c2cc}.xiao{fill:#fbf1e8;stroke:#d9a77a}
.hd{font:700 17px -apple-system,"PingFang SC",sans-serif;fill:#1b1f24}
.sub{font:500 13px -apple-system,"PingFang SC",sans-serif;fill:#5f6b76}
.xl{font:700 14px -apple-system,"PingFang SC",sans-serif;fill:#8a5524}
.col{font:600 12px -apple-system,"PingFang SC",sans-serif;fill:#5f6b76}
.pin text{font:700 12px -apple-system,sans-serif;pointer-events:none}
.pin.off rect{fill:#f5f6f7;stroke:#c3ccd4}.pin.off text{fill:#9aa5ad}
.pin.dbg rect{fill:#fff;stroke:#9aa5ad;stroke-dasharray:3 2}
.pin{cursor:pointer}.pin.on rect{stroke:#ffffff;stroke-width:1.5}
.wire{fill:none;stroke-width:3.2;stroke-linecap:round;transition:opacity .15s}
.hit{fill:none;stroke:transparent;stroke-width:14;cursor:pointer}
#map.sel .wire,#map.sel .pin.on{opacity:.08}
#map.sel .wire.hl{opacity:1;stroke-width:5}
.wire.case{stroke-width:5.4}#map.sel .wire.case.hl{stroke-width:7.2}
#map.sel .pin.hl{opacity:1}#map.sel .pin.hl rect{stroke:#111;stroke-width:2.5}
.chips{display:flex;flex-direction:column;gap:8px}
.chip{display:flex;align-items:center;gap:10px;width:100%;text-align:left;font:inherit;padding:10px 12px;
background:var(--card);border:1px solid var(--line);border-radius:10px;cursor:pointer}
.chip i{flex:none;width:14px;height:14px;border-radius:50%;border:1px solid #0002}
.chip .cl{flex:1;min-width:0;overflow-wrap:anywhere}.chip .pp{flex:none;color:var(--mute);white-space:nowrap}
.chip .pp b{color:var(--ink)}.chip.hl{border-color:var(--accent);box-shadow:0 0 0 2px #1565c033}
.foot{color:var(--mute);font-size:14px;margin-top:20px}
'''

JS = '''
const W=%s;const map=document.getElementById('map');const txt=document.getElementById('txt');
const byId=Object.fromEntries(W.map(w=>[w[0],w]));const DEF=txt.innerHTML;
function clear(){map.classList.remove('sel');document.querySelectorAll('.hl').forEach(e=>e.classList.remove('hl'));txt.innerHTML=DEF}
function show(id){clear();const w=byId[id];if(!w)return;map.classList.add('sel');
document.querySelectorAll('[data-w="'+id+'"]').forEach(e=>e.classList.add('hl'));
const src=w[3]?('Pi <b>'+w[3]+'</b> 号针'):'触摸板 XIAO';
const chg=w[3]&&w[3]!==w[4]?'，<b>换针，小旗改成 '+w[4]+'</b>':(w[3]?'，针号不变':'');
txt.innerHTML='<b>'+w[1]+'</b>：'+src+' → A7Z <b>'+w[4]+'</b> 号针'+chg+(w[5]?'。'+w[5]:'')}
document.addEventListener('click',e=>{const t=e.target.closest('[data-w]');
if(t){const id=t.dataset.w;if(map.classList.contains('sel')&&t.classList.contains('hl'))clear();else show(id);return}
const p=e.target.closest('.pin');if(p){clear();const b=p.dataset.b==='p'?'Pi':'A7Z';
txt.innerHTML=(p.classList.contains('dbg')?'<b>'+b+' '+p.dataset.n+' 号</b>：调试串口，空着':'<b>'+b+' '+p.dataset.n+' 号</b>：空着');return}
if(e.target.closest('#reset')||e.target.closest('svg'))clear()});
''' % json.dumps([list(w) for w in WIRES], ensure_ascii=False)


def page() -> str:
    MOVED = sum(1 for w in WIRES if w[3])
    CHANGED = sum(1 for w in WIRES if w[3] and w[3] != w[4])
    NEW = len(WIRES) - MOVED
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>A7Z 接线</title><style>{CSS}</style></head>
<body><main>
<h1>Pi 上的线插到 A7Z 哪根针</h1>
<p class="lead">两块板画成同一个方向：元件面朝你，排针竖着，1 号针在上，里排（单号）在左，外排（双号，靠板边）在右。注意两块板的 1 号针在不同的一头。</p>
<div class="info"><span class="txt" id="txt">点一根线、一根针或下面的一行，只显示这根线。</span><button id="reset" type="button">全部显示</button></div>
<div class="fig">{svg()}</div>
{chips()}
<p class="foot">虚线框的 A7Z 8、10 号是调试串口，空着。17 根线：{MOVED} 根从 Pi 搬过来（{CHANGED} 根换针），{NEW} 根是新加的触摸板线。详细步骤和来源：<a href="A7Z-PINS.html">A7Z-PINS.html</a>。</p>
</main><script>{JS}</script></body></html>'''


if __name__ == '__main__':
    OUT.write_text(page(), encoding='utf-8')
    print(OUT, OUT.stat().st_size)
