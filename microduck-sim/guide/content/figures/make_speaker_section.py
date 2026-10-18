"""Speaker-in-collar cross-section figure, cut from the world STLs at the speaker mid-plane (u = 0, across the 20 mm width).

Writes speaker-section-en.html and speaker-section-zh.html next to this file; render them to PNG at 2x with
render_figures (Chrome headless). Run with the CAD venv: /tmp/microduck-cad-venv/bin/python make_speaker_section.py
"""
from pathlib import Path
import numpy as np
import trimesh
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
WORLD = HERE.parents[1] / 'print' / 'world'
C = np.array([3.422, 0, 141.022]); A1 = np.array([-0.247, 0, 0.969]); L = np.array([0.969, 0, 0.247]); W = np.cross(A1, L)
S, X0, HTOP = 22.0, 430.0, 9.4                     # px per mm, x of w = 0, h at the top of the drawing
Y0 = 70.0
WIN = box(-19.5, -3.6, 19.5, HTOP)

def X(w): return X0 + S * w
def Y(h): return Y0 + S * (HTOP - h)

def section(name):
    m = trimesh.load(WORLD / name)
    sec = m.section(plane_origin=C, plane_normal=L)
    geom = None
    for loop in sec.discrete:
        q = loop - C
        p = Polygon(np.c_[q @ W, q @ A1])
        if not p.is_valid: p = p.buffer(0)
        geom = p if geom is None else geom.symmetric_difference(p)
    return geom.intersection(WIN)

def path(g):
    polys = [g] if g.geom_type == 'Polygon' else [p for p in getattr(g, 'geoms', []) if p.geom_type == 'Polygon']
    d = []
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            pts = list(ring.coords)
            d.append('M' + ' L'.join(f'{X(w):.1f} {Y(h):.1f}' for w, h in pts) + ' Z')
    return ' '.join(d)

def shape(g, fill, stroke):
    return f'<path d="{path(g)}" fill="{fill}" stroke="{stroke}" stroke-width="2" fill-rule="evenodd" stroke-linejoin="round"/>'

def rect(w0, h0, w1, h1, fill, stroke):
    return f'<rect x="{X(min(w0, w1)):.1f}" y="{Y(max(h0, h1)):.1f}" width="{S * abs(w1 - w0):.1f}" height="{S * abs(h1 - h0):.1f}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'

def marker(n, x, y):
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="15" fill="#1f2328" stroke="#fff" stroke-width="2.5"/>'
            f'<text x="{x:.1f}" y="{y + 6.5:.1f}" text-anchor="middle" fill="#fff" style="font-weight:700;font-size:17px">{n}</text>')

TEXT = {
    'en': {'legend': [
        ['Cap roof; the sound slots', 'open over the grille'],
        ['Collar lip: a 0.6 mm step ring', 'all round the speaker edge'],
        ['Foam double-sided tape: one', 'closed loop on that ring (two', 'strips); 1 mm pressed to 0.6 mm'],
        ['1.6 mm pocket over the grille:', 'no tape here'],
        ['Flat metal grille with seven', 'holes (here the big middle one)', 'faces the roof'],
        ['Raised round magnet and the two', 'solder pads face the retainer;', 'pads at the amplifier end'],
        ['Retainer frame'],
        ['M2 × 6 into the cap pilot,', 'one each side']],
        'caption': 'Section across the middle of the speaker, seen from the amplifier end'},
    'zh': {'legend': [
        ['头壳顶：出声槽开在', '金属网正上方'],
        ['集音圈台阶：沿喇叭边缘一整圈，', '高 0.6 mm'],
        ['泡棉双面胶：在这圈台阶上贴成', '封闭的一圈（两条接起来），', '1 mm 压到 0.6 mm'],
        ['金属网上方 1.6 mm 空腔：', '这里不贴胶'],
        ['平的金属网（7 个孔，这里切到', '中间大孔）朝头壳顶'],
        ['凸起的圆磁铁和两个焊点朝压板，', '焊点在靠功放那一头'],
        ['压板'],
        ['M2 × 6 拧进头壳的导孔，', '左右各一颗']],
        'caption': '从功放那头看，喇叭正中间的剖面'},
}

def build():
    cap, spk, tape, ret = (section(n) for n in ('head_cap.stl', 'speaker.stl', 'speaker_tape.stl', 'speaker_retainer.stl'))
    body = []
    body.append(shape(cap, '#e9a842', '#2b2f33'))
    body.append(shape(spk, '#4a4f55', '#2b2f33'))
    # metal grille: a thin light band on the front face of the speaker section, broken where the cut crosses a hole
    grille = spk.intersection(box(-9.7, 1.65, 9.7, 2.0))
    body.append(shape(grille, '#c9ced3', '#6b7178'))
    body.append(shape(tape, '#f2c14e', '#9a6b00'))
    body.append(shape(ret, '#e07b00', '#2b2f33'))
    for sgn in (1, -1):                               # solder pads at the amplifier end, nearest the viewer
        body.append(rect(sgn * 2.0, -0.5, sgn * 4.0, -1.0, '#d9b24a', '#6b5300'))
        w = sgn * 14.6                                # M2 x 6: shank through the retainer hole into the pilot, head under the frame
        body.append(rect(w - 0.8, -2.1, w + 0.8, 3.9, '#9aa0a6', '#555'))
        body.append(rect(w - 1.8, -2.1, w + 1.8, -3.3, '#9aa0a6', '#555'))
    dims = (f'<line x1="{X(9.3):.1f}" y1="{Y(2.0):.1f}" x2="{X(9.3):.1f}" y2="{Y(2.6):.1f}" stroke="#7d2fb8" stroke-width="3"/>'
            f'<text x="{X(8.2):.1f}" y="{Y(2.05):.1f}" fill="#7d2fb8" text-anchor="end" style="font-weight:700">0.6 mm</text>'
            f'<line x1="{X(-6.8):.1f}" y1="{Y(2.0):.1f}" x2="{X(-6.8):.1f}" y2="{Y(3.6):.1f}" stroke="#7d2fb8" stroke-width="3"/>'
            f'<text x="{X(-6.3):.1f}" y="{Y(2.45):.1f}" fill="#7d2fb8" style="font-weight:700">1.6 mm</text>')
    marks = [marker(1, X(0.0), Y(6.2)), marker(2, X(12.3), Y(3.0)), marker(3, X(-9.2), Y(3.3)), marker(4, X(2.6), Y(2.85)),
             marker(5, X(0.0), Y(0.4)), marker(6, X(5.6), Y(-0.75)), marker(7, X(-10.7), Y(-2.9)), marker(8, X(-17.0), Y(-0.6))]
    for lang, t in TEXT.items():
        out = []
        y = 52.0
        for i, lines in enumerate(t['legend'], 1):
            out.append(f'<circle cx="890" cy="{y - 6:.0f}" r="14" fill="#1f2328"/><text x="890" y="{y:.0f}" text-anchor="middle" fill="#fff" style="font-weight:700;font-size:16px">{i}</text>')
            for k, line in enumerate(lines):
                out.append(f'<text x="916" y="{y + 23 * k:.0f}" fill="#1f2328">{line}</text>')
            y += 23 * len(lines) + 12
        html = ('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#fff}</style></head><body>'
                '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="640" viewBox="0 0 1400 640" '
                'style="background:#fff;font:500 19px -apple-system,&quot;PingFang SC&quot;,&quot;Noto Sans SC&quot;,sans-serif">\n'
                + '\n'.join(body + [dims] + marks + out)
                + f'\n<text x="430" y="{Y(-3.6) + 40:.0f}" text-anchor="middle" fill="#5b636b" style="font-size:17px">{t["caption"]}</text>\n</svg></body></html>')
        (HERE / f'speaker-section-{lang}.html').write_text(html, encoding='utf-8')
        print('wrote', HERE / f'speaker-section-{lang}.html', 'legend bottom y', y)

if __name__ == '__main__':
    build()
