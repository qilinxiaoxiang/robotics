# Writes the four lead-forming panels (HTML sources) into audio-bench/img/.
import os
OUT=__import__('os').path.dirname(__import__('os').path.abspath(__file__))
HEAD='''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{title}</title>
<style>
html,body{{margin:0;background:#fff}}
#canvas{{width:400px;height:300px;position:relative;background:#fff}}
svg{{display:block}}
.lab{{font:600 22px -apple-system,"PingFang SC","Noto Sans SC",sans-serif;fill:#1f2328}}
.dim{{font:700 22px -apple-system,"PingFang SC","Noto Sans SC",sans-serif;fill:#7d2fb8}}
.dl{{stroke:#7d2fb8;stroke-width:2.5;fill:none}}
.ext{{stroke:#7d2fb8;stroke-width:1.5;stroke-dasharray:5 4;fill:none}}
</style></head>
<body><div id="canvas">
<svg width="400" height="300" viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg">
<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#7d2fb8"/></marker>
<marker id="k" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#1f2328"/></marker>
<linearGradient id="fadeL" x1="0" x2="1"><stop offset="0" stop-color="#c9ced3" stop-opacity="0"/><stop offset="1" stop-color="#c9ced3"/></linearGradient>
<linearGradient id="fadeR" x1="0" x2="1"><stop offset="0" stop-color="#c9ced3"/><stop offset="1" stop-color="#c9ced3" stop-opacity="0"/></linearGradient>
</defs>
'''
TAIL='</svg>\n</div></body></html>\n'

def body(cx, cy, s, bands=True):
    """Resistor body 6.3 x 2.4 mm centred at (cx, cy), s px/mm, bands brown black black orange brown."""
    L, D = 6.3*s, 2.4*s
    x0 = cx-L/2
    out = f'<rect x="{x0:.1f}" y="{cy-D/2:.1f}" width="{L:.1f}" height="{D:.1f}" rx="{D*0.3:.1f}" fill="#9cc7e4" stroke="#4f7da0" stroke-width="2"/>\n'
    if bands:
        bw = 0.38*s
        for f, col in [(0.17,'#7b4a1e'),(0.29,'#151515'),(0.41,'#151515'),(0.53,'#f08a24'),(0.83,'#7b4a1e')]:
            out += f'<rect x="{x0+f*L-bw/2:.1f}" y="{cy-D/2+1:.1f}" width="{bw:.1f}" height="{D-2:.1f}" fill="{col}"/>\n'
    return out

def shrink(cx, cy, s):
    L, D = 7.0*s, 2.9*s
    return f'<rect x="{cx-L/2:.1f}" y="{cy-D/2:.1f}" width="{L:.1f}" height="{D:.1f}" rx="{D*0.35:.1f}" fill="#ffffff" fill-opacity="0.22" stroke="#3d4349" stroke-width="2.5" stroke-dasharray="7 5"/>\n'

def lead(d, s, extra='', cap='round', mask=None):
    w = 0.55*s
    g0 = f'<g mask="url(#{mask})">' if mask else ''
    g1 = '</g>' if mask else ''
    return (g0 + f'<path d="{d}" fill="none" stroke="#5d646b" stroke-width="{w+5:.1f}" stroke-linecap="{cap}" stroke-linejoin="round"{extra}/>\n'
            f'<path d="{d}" fill="none" stroke="#c9ced3" stroke-width="{w:.1f}" stroke-linecap="{cap}" stroke-linejoin="round"{extra}/>' + g1 + '\n')

def fade_mask(mid, x0, y0, x1, y1, stops, horizontal=True):
    """Mask that fades leads out: stops are (offset, opacity) along x (or y) from x0..x1 (y0..y1)."""
    grad = ''.join(f'<stop offset="{o}" stop-color="#fff" stop-opacity="{a}"/>' for o, a in stops)
    gx = 'x1="0" x2="1" y1="0" y2="0"' if horizontal else 'x1="0" x2="0" y1="0" y2="1"'
    return (f'<defs><linearGradient id="{mid}g" {gx}>{grad}</linearGradient>'
            f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="400" height="300">'
            f'<rect x="0" y="0" width="400" height="300" fill="#fff"/>'
            f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#000"/>'
            f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="url(#{mid}g)"/></mask></defs>\n')

# Panel 1: heat-shrink on the straight resistor, leads still full length (ends fade out: they continue)
s=20; cx, cy = 200, 160
p = ''
p += fade_mask('m1', 0, 0, 400, 300, [(0.035,0),(0.18,1),(0.82,1),(0.965,0)])
p += lead(f'M14 {cy} H386', s, cap='butt', mask='m1')
p += body(cx, cy, s) + shrink(cx, cy, s)
L=7.0*s
p += f'<path class="ext" d="M{cx-L/2:.1f} {cy-34:.1f} V{cy-70:.1f} M{cx+L/2:.1f} {cy-34:.1f} V{cy-70:.1f}"/>\n'
p += f'<path class="dl" d="M{cx-L/2+2:.1f} {cy-62:.1f} H{cx+L/2-2:.1f}" marker-start="url(#a)" marker-end="url(#a)"/>\n'
p += f'<text class="dim" x="{cx}" y="{cy-74}" text-anchor="middle">热缩管约 7 mm</text>\n'
p += f'<text class="lab" x="{cx}" y="{cy+78}" text-anchor="middle">两条腿先留全长（各约 28 mm）</text>\n'
open(os.path.join(OUT,'leadform-1.html'),'w').write(HEAD.format(title='Lead forming 1: heat-shrink')+p+TAIL)

# Panel 2: pliers next to the heat-shrink, bend 90 degrees about 0.9 mm from the body
s=40; cy=120; bodyR=200  # right end of the body at x=200; body cut by a break at x=30
p = ''
L=6.3*s
cxb = bodyR - L/2
w=0.55*s
bend = bodyR + 0.9*s            # bend centreline, 0.9 mm from the body
jaw0 = bodyR + 0.35*s           # jaws start at the heat-shrink end
jaw1 = bend - (w+5)/2 - 1       # jaws end at the inner face of the bent leg
p += fade_mask('m2', 0, 186, 400, 214, [(0,1),(1,0)], horizontal=False)
p += lead(f'M{bodyR-5:.1f} {cy} H{bend:.1f} V214', s, cap='butt', mask='m2')
p += '<defs><clipPath id="cut"><path d="M34 0 L44 60 L30 120 L44 180 L34 300 H400 V0 Z"/></clipPath></defs>\n'
p += '<g clip-path="url(#cut)">' + body(cxb, cy, s) + shrink(cxb, cy, s) + '</g>\n'
# jaws (tips seen from the side): grip only the straight part between the heat-shrink and the bend,
# widen away from the resistor (up and to the right; down and to the left under the heat-shrink)
top = cy - w/2 - 2.5; bot = cy + w/2 + 2.5
p += f'<path d="M{jaw0:.1f} {top:.1f} H{jaw1:.1f} L{jaw1+30:.1f} 18 H184 L{jaw0:.1f} 70 Z" fill="#8a9097" stroke="#4e555c" stroke-width="2"/>\n'
p += f'<path d="M{jaw0:.1f} {bot:.1f} H{jaw1:.1f} V{bot+14:.1f} L{jaw1-16:.1f} 190 H184 L{jaw0:.1f} 170 Z" fill="#8a9097" stroke="#4e555c" stroke-width="2"/>\n'
p += f'<text class="lab" x="{jaw1+40:.1f}" y="44">尖嘴钳</text>\n'
# bend arrow
p += f'<path d="M{bend+70:.1f} {cy+8:.1f} A56 56 0 0 1 {bend+20:.1f} {cy+62:.1f}" fill="none" stroke="#1f2328" stroke-width="2.5" marker-end="url(#k)"/>\n'
p += f'<text class="lab" x="{bend+28:.1f}" y="{cy+100:.1f}">弯 90°</text>\n'
# dimension: body end -> bend centreline
p += f'<path class="ext" d="M{bodyR:.1f} 198 V{cy+120:.1f} M{bend:.1f} 220 V{cy+120:.1f}"/>\n'
p += f'<path class="dl" d="M{bodyR+2:.1f} {cy+112:.1f} H{bend-2:.1f}" marker-start="url(#a)" marker-end="url(#a)"/>\n'
p += f'<text class="dim" x="{bodyR-8:.1f}" y="{cy+120:.1f}" text-anchor="end">约 0.9 mm</text>\n'
p += f'<text class="lab" x="20" y="284">钳口贴着热缩管，只弯钳子外面那段</text>\n'
open(os.path.join(OUT,'leadform-2.html'),'w').write(HEAD.format(title='Lead forming 2: bend with pliers')+p+TAIL)

# Panel 3: U shape seen from the back. GAIN leg centred on the GAIN hole (bent down into it), Vin leg on the
# outer (board-corner) side of the 4 mm Vin wire tail. Vin tail to GAIN hole 7.62 mm; legs about 8.15 mm apart.
s=20; cx=200; cy=86
L=6.3*s
w=0.55*s
half = (7.62 + 0.25 + 0.275)*s/2     # Vin tail r 0.25 mm (tinned) + leg r 0.275 mm outside the tail
xlv, xlg = cx-half, cx+half           # leg centrelines
xv, xg = xlg-7.62*s, xlg              # Vin tail and GAIN hole centres
xgnd, xsd = xv+2.54*s, xv+5.08*s
p = ''
ty = cy+118
for tx in (xv, xgnd, xsd, xg):
    p += f'<circle cx="{tx:.1f}" cy="{ty}" r="{0.96*s:.1f}" fill="#d6a84f"/>\n'
for tx in (xsd, xg):                  # open holes (drill 1.0 mm)
    p += f'<circle cx="{tx:.1f}" cy="{ty}" r="{0.5*s:.1f}" fill="#3a3f44"/>\n'
for tx in (xv, xgnd):                 # soldered wire joints, tail seen end-on
    p += f'<circle cx="{tx:.1f}" cy="{ty}" r="{0.7*s:.1f}" fill="#cfd4d9" stroke="#9aa1a8" stroke-width="2"/>\n'
    p += f'<circle cx="{tx:.1f}" cy="{ty}" r="{0.25*s+1:.1f}" fill="#b9bec4" stroke="#5d646b" stroke-width="2"/>\n'
p += fade_mask('m3', 0, ty+6, 400, ty+44, [(0,1),(1,0)], horizontal=False)
p += lead(f'M{cx-L/2+4:.1f} {cy} H{xlv:.1f} V{ty+44}', s, cap='butt', mask='m3')
p += lead(f'M{cx+L/2-4:.1f} {cy} H{xlg:.1f} V{ty}', s)
p += f'<circle cx="{xg:.1f}" cy="{ty}" r="{w/2+1.5:.1f}" fill="#e3e6e9" stroke="#5d646b" stroke-width="2.5"/>\n'
p += body(cx, cy, s) + shrink(cx, cy, s)
p += f'<text class="lab" x="{xlv-14:.1f}" y="{ty+8}" text-anchor="end">Vin</text>\n'
p += f'<text class="lab" x="{xg+0.96*s+6:.1f}" y="{ty+8}">GAIN</text>\n'
p += f'<path class="dl" d="M{xlv+2:.1f} {cy-46:.1f} H{xlg-2:.1f}" marker-start="url(#a)" marker-end="url(#a)"/>\n'
p += f'<path class="ext" d="M{xlv:.1f} {cy-6:.1f} V{cy-54:.1f} M{xlg:.1f} {cy-6:.1f} V{cy-54:.1f}"/>\n'
p += f'<text class="dim" x="{cx}" y="{cy-54}" text-anchor="middle">腿间距约 8 mm</text>\n'
p += f'<path class="dl" d="M{xv+2:.1f} {ty+40:.1f} H{xg-2:.1f}" marker-start="url(#a)" marker-end="url(#a)"/>\n'
p += f'<path class="ext" d="M{xv:.1f} {ty+24:.1f} V{ty+48:.1f} M{xg:.1f} {ty+24:.1f} V{ty+48:.1f}"/>\n'
p += f'<text class="dim" x="{(xv+xg)/2:.1f}" y="{ty+70}" text-anchor="middle">Vin 线尾到 GAIN 孔 7.62 mm</text>\n'
open(os.path.join(OUT,'leadform-3.html'),'w').write(HEAD.format(title='Lead forming 3: U shape')+p+TAIL)

# Panel 4: Vin hook formed round a spare straight header pin, seen from the end of the pin
# (the GAIN leg gets no hook: it is bent straight down into its hole)
s=34; px, py = 150, 150
p = ''
r = 0.32*s + 0.275*s + 1
ex, ey = px + r*0.7071, py - r*0.7071   # end of the hook
p += fade_mask('m4', 0, 0, 400, 46, [(0,0),(1,1)], horizontal=False)
# lead comes in from the top (it continues to the resistor), runs down the left side of the pin and wraps round
p += lead(f'M{px-r:.1f} 0 V{py:.1f} A{r:.1f} {r:.1f} 0 0 0 {px+r:.1f} {py:.1f} A{r:.1f} {r:.1f} 0 0 0 {ex:.1f} {ey:.1f}', s, cap='butt', mask='m4')
# the part to cut off: dashed, beyond the hook end, with a cut mark
p += f'<g opacity="0.45">' + lead(f'M{ex:.1f} {ey:.1f} Q{ex+7:.1f} {ey-13:.1f} {ex+25:.1f} {ey-31:.1f}', s, cap='butt') + '</g>\n'
p += f'<path d="M{ex-5:.1f} {ey-24:.1f} L{ex+20:.1f} {ey-5:.1f}" stroke="#d7263d" stroke-width="3" fill="none"/>\n'
p += f'<rect x="{px-0.32*s:.1f}" y="{py-0.32*s:.1f}" width="{0.64*s:.1f}" height="{0.64*s:.1f}" fill="#b9bec4" stroke="#5d646b" stroke-width="2"/>\n'
p += f'<path d="M{px:.1f} {py+2:.1f} L262 198" stroke="#1f2328" stroke-width="2" fill="none"/><circle cx="{px:.1f}" cy="{py+2:.1f}" r="3" fill="#1f2328"/>\n'
p += f'<text class="lab" x="200" y="222">多余的直排针</text>\n<text class="lab" x="200" y="250">(当模具用)</text>\n'
p += f'<text class="lab" x="14" y="290">GAIN 腿不绕钩，直接向下弯</text>\n'
p += f'<path d="M{px-r-10:.1f} 60 L84 60" stroke="#1f2328" stroke-width="2" fill="none"/>\n'
p += f'<text class="lab" x="76" y="68" text-anchor="end">Vin 腿</text>\n'
p += f'<text class="lab" x="200" y="64">绕大半圈成小钩</text>\n'
p += f'<text class="lab" x="200" y="94">剪掉多余的部分</text>\n'
open(os.path.join(OUT,'leadform-4.html'),'w').write(HEAD.format(title='Lead forming 4: hook')+p+TAIL)
print('ok')
