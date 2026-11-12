#!/usr/bin/env python3
"""Draw the same sheet gen_sch.py writes as an SVG, for a look without Fusion. Run: python3 render_svg.py OUT.svg"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gen_sch as GS
import netlist as NL

S = 4.0   # px per mm


def main(out):
    kinds, parts, wires, labels = GS.build()
    xs = [w[3][0] for w in wires] + [w[4][0] for w in wires] + [p[3] for p in parts] + [p[3] + p[6].w for p in parts]
    ys = [p[4] for p in parts] + [p[4] + p[6].h + 6 for p in parts]
    x0, x1, y0, y1 = min(xs) - 8, max(xs) + 8, min(ys) - 8, max(ys) + 18
    X = lambda x: (x - x0) * S
    Y = lambda y: (y1 - y) * S
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{(x1 - x0) * S:.0f}" height="{(y1 - y0) * S:.0f}" '
         f'font-family="Menlo, monospace"><rect width="100%" height="100%" fill="#fff"/>',
         f'<text x="{X(x0 + 8)}" y="{Y(y1 - 8)}" font-size="{3.8 * S}" fill="#333">{NL.TITLE}</text>']
    box = {}
    for ref, kind, value, ox, oy, g, k in parts:
        b = box.setdefault(g, [1e9, 1e9, -1e9, -1e9])
        b[0], b[1], b[2], b[3] = min(b[0], ox - 3), min(b[1], oy - 3), max(b[2], ox + k.w + 3), max(b[3], oy + k.h + 7)
    for w in wires:
        b = box[w[5]]
        b[0], b[2] = min(b[0], w[3][0] - 2, w[4][0] - 2), max(b[2], w[3][0] + 2, w[4][0] + 2)
    for g, b in box.items():
        o.append(f'<rect x="{X(b[0])}" y="{Y(b[3])}" width="{(b[2] - b[0]) * S}" height="{(b[3] - b[1]) * S}" fill="none" '
                 f'stroke="#9aa" stroke-dasharray="6 4"/><text x="{X(b[0])}" y="{Y(b[3] + 1.5)}" font-size="{2.6 * S}" fill="#567">{g}</text>')
    for ref, kind, value, ox, oy, g, k in parts:
        o.append(f'<rect x="{X(ox)}" y="{Y(oy + k.h)}" width="{k.w * S}" height="{k.h * S}" fill="#fffbe6" stroke="#a33"/>')
        o.append(f'<text x="{X(ox)}" y="{Y(oy + k.h + 3.2)}" font-size="{1.8 * S}" fill="#333">{ref}</text>')
        o.append(f'<text x="{X(ox)}" y="{Y(oy + k.h + 0.8)}" font-size="{1.8 * S}" fill="#666">{value}</text>')
        for pn, (x, y, side) in k.pos.items():
            px = ox + x
            ix = ox if side == "L" else ox + k.w
            o.append(f'<line x1="{X(px)}" y1="{Y(oy + y)}" x2="{X(ix)}" y2="{Y(oy + y)}" stroke="#a33"/>')
            anchor, tx = ("start", ix + 0.8) if side == "L" else ("end", ix - 0.8)
            o.append(f'<text x="{X(tx)}" y="{Y(oy + y - 0.6)}" font-size="{1.5 * S}" text-anchor="{anchor}" fill="#555">{pn}</text>')
    for net, ref, pn, p, q, g in wires:
        o.append(f'<line x1="{X(p[0])}" y1="{Y(p[1])}" x2="{X(q[0])}" y2="{Y(q[1])}" stroke="#1a7f37"/>')
    for net, ref, pn, x, y, g in labels:
        o.append(f'<text x="{X(x)}" y="{Y(y)}" font-size="{1.75 * S}" fill="#1a4fa0">{net}</text>')
    o.append('</svg>')
    Path(out).write_text("\n".join(o))
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1])
