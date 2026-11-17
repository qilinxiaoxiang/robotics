"""SVG figures for the flight pack guide's bench steps (cut list, bullet soldering).

The cut-list figure is drawn to scale from the same lead lengths the step text uses (wiring W.FAN_LEN / W.BAT_LEN),
so the picture and the numbers cannot disagree. Both figures are returned as data:image/svg+xml URIs for the
guide's `images` field.
"""
import base64

FONT = "-apple-system, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans SC', sans-serif"
WIRE = {'红': '#d32f2f', '黄': '#e0b000', '黑': '#222222'}
INK, MUTED, LINE = '#15191e', '#56606b', '#cfd5dc'


def _uri(svg):
    return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()


def _t(x, y, s, size=15, weight=400, fill=INK, anchor='start'):
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{s}</text>'


def cut_list(fan_len, bat_len):
    """fan_len: {'FL': mm, ...}; bat_len: {'L': mm, 'R': mm}. One row per labelled bundle, bars to scale."""
    rows = [('左前', '16 AWG', fan_len['FL'], '红黄黑', 'fan'), ('左后', '16 AWG', fan_len['RL'], '红黄黑', 'fan'),
            ('右前', '16 AWG', fan_len['FR'], '红黄黑', 'fan'), ('右后', '16 AWG', fan_len['RR'], '红黄黑', 'fan'),
            ('左电池', '12 AWG', bat_len['L'], '红黑', 'bat'), ('右电池', '12 AWG', bat_len['R'], '红黑', 'bat')]
    longest = max(r[2] for r in rows)
    x0, scale = 250, 640 / longest          # px per mm
    W, top = 1000, 92
    gap_wire, gap_row = 13, 30
    out, y = [], top
    for name, gauge, mm, cols, kind in rows:
        n = len(cols)
        thick = 7 if gauge == '16 AWG' else 10
        h = (n - 1) * gap_wire
        out.append(_t(24, y + h / 2 + 2, name, 20, 700))
        out.append(_t(24, y + h / 2 + 23, f'{gauge} · {"、".join(cols)} 各 1 根', 13, 400, MUTED))
        L = mm * scale
        for i, c in enumerate(cols):
            yy = y + i * gap_wire
            out.append(f'<line x1="{x0}" y1="{yy}" x2="{x0 + L}" y2="{yy}" stroke="{WIRE[c]}" stroke-width="{thick}" stroke-linecap="butt"/>')
            # bare copper at each end: long strip (solder cup) on the left, 2 mm (pad) on the right for fan leads
            out.append(f'<line x1="{x0 - 9}" y1="{yy}" x2="{x0}" y2="{yy}" stroke="#c77b30" stroke-width="{thick - 3}"/>')
            right = 4 if kind == 'fan' else 9
            out.append(f'<line x1="{x0 + L}" y1="{yy}" x2="{x0 + L + right}" y2="{yy}" stroke="#c77b30" stroke-width="{thick - 3}"/>')
        # tape flag with the name
        fx = x0 + min(L * 0.5, L - 30)
        out.append(f'<rect x="{fx - 26}" y="{y - 21}" width="52" height="17" rx="3" fill="#fff7cc" stroke="#d9b84a"/>')
        out.append(_t(fx, y - 8, name, 11.5, 700, INK, 'middle'))
        out.append(_t(x0 + L + 18, y + h / 2 + 6, f'{mm} mm', 19, 700))
        y += h + gap_row + 18
    H = y + 62
    # scale bar 50 mm
    sb = 50 * scale
    out.append(f'<line x1="{x0}" y1="{H - 52}" x2="{x0 + sb}" y2="{H - 52}" stroke="{INK}" stroke-width="2"/>')
    out.append(f'<line x1="{x0}" y1="{H - 58}" x2="{x0}" y2="{H - 46}" stroke="{INK}" stroke-width="2"/>')
    out.append(f'<line x1="{x0 + sb}" y1="{H - 58}" x2="{x0 + sb}" y2="{H - 46}" stroke="{INK}" stroke-width="2"/>')
    out.append(_t(x0 + sb + 10, H - 47, '50 mm（线的长短按同一比例画）', 13, 400, MUTED))
    out.append(_t(24, H - 22, '线两头的铜色是剥皮露出的线芯：左头剥到刚好填满焊杯（接子弹头或 XT60），右头：风扇线剥 2 mm（焊到电调焊盘），电池线剥到填满焊杯。', 13, 400, MUTED))
    head = (_t(24, 34, '剪线清单：16 根线，6 组，每组贴一张写名字的胶带', 21, 700)
            + _t(24, 62, f'风扇线每组 3 根（红、黄、黑一样长），电池线每组 2 根（红、黑一样长）。', 14, 400, MUTED))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>{head}{"".join(out)}</svg>')
    return _uri(svg)


def _bullet(x, y, scale=1.0):
    """A female 3.5 mm bullet lying along +x from (x, y): solder cup on the left, socket on the right."""
    s = scale
    return (f'<rect x="{x}" y="{y - 13 * s}" width="{40 * s}" height="{26 * s}" rx="3" fill="#d8b24a" stroke="#9c7a1c" stroke-width="1.5"/>'
            f'<rect x="{x + 40 * s}" y="{y - 15 * s}" width="{70 * s}" height="{30 * s}" rx="4" fill="#e6c25a" stroke="#9c7a1c" stroke-width="1.5"/>'
            f'<rect x="{x + 104 * s}" y="{y - 9 * s}" width="{8 * s}" height="{18 * s}" fill="#7a5d12"/>')


def _bullet_up(cx, top, solder=True):
    """The same bullet standing up, solder cup open at the top (cut away to show the cup and its solder)."""
    g = [f'<rect x="{cx - 17}" y="{top}" width="34" height="52" rx="3" fill="#d8b24a" stroke="#9c7a1c" stroke-width="1.5"/>',
         f'<rect x="{cx - 10}" y="{top - 1}" width="20" height="40" fill="#8a6a1a"/>',
         f'<rect x="{cx - 19}" y="{top + 52}" width="38" height="88" rx="4" fill="#e6c25a" stroke="#9c7a1c" stroke-width="1.5"/>',
         f'<rect x="{cx - 11}" y="{top + 134}" width="22" height="8" fill="#7a5d12"/>']
    if solder:
        g.append(f'<rect x="{cx - 10}" y="{top + 6}" width="20" height="33" fill="#b9bfc6" stroke="#8a9198"/>')
    return ''.join(g)


def bullet_steps():
    """Four panels, one image each (2 x 2 on a wide screen, stacked on a phone)."""
    panels = []
    bx, by = 0, 0
    pw, ph = 455, 250
    titles = ['① 线上先套一段 5 mm 热缩管，推到远处', '② 子弹头焊杯朝上夹住，焊杯里化满锡',
              '③ 线芯插进焊杯，锡流满再拿开烙铁，线别动', '④ 冷了把热缩管推上来盖住焊杯，吹缩']
    for i, title in enumerate(titles):
        px, py = bx, by
        g = [f'<rect x="1" y="1" width="{pw - 2}" height="{ph - 2}" rx="10" fill="#f6f8fa" stroke="{LINE}"/>',
             _t(px + 16, py + 32, title, 16, 700)]
        cy = py + 150
        if i == 0:
            g.append(f'<line x1="{px + 30}" y1="{cy}" x2="{px + 330}" y2="{cy}" stroke="{WIRE["红"]}" stroke-width="9"/>')
            g.append(f'<line x1="{px + 330}" y1="{cy}" x2="{px + 352}" y2="{cy}" stroke="#c77b30" stroke-width="6"/>')
            g.append(f'<rect x="{px + 90}" y="{cy - 12}" width="90" height="24" rx="5" fill="#3d7bd9" opacity="0.35" stroke="#2a5fae"/>')
            g.append(_t(px + 135, cy + 42, '热缩管', 14, 600, '#2a5fae', 'middle'))
            g.append(_t(px + 341, cy + 42, '剥皮的长头', 14, 600, '#a35a14', 'middle'))
            g.append(f'<path d="M{px + 200} {cy - 30} L{px + 110} {cy - 30}" stroke="#2a5fae" stroke-width="2.5" marker-end="url(#arr)"/>')
        elif i == 1:
            top = py + 70
            g.append(_bullet_up(px + 200, top))
            g.append(f'<rect x="{px + 176}" y="{top + 100}" width="48" height="26" rx="4" fill="#9aa3ad"/>')
            g.append(_t(px + 236, top + 118, '第三只手夹住插口那段', 13, 400, MUTED))
            g.append(f'<line x1="{px + 330}" y1="{py + 55}" x2="{px + 222}" y2="{top + 20}" stroke="#555" stroke-width="7" stroke-linecap="round"/>')
            g.append(_t(px + 336, py + 62, '烙铁', 14, 600))
            g.append(_t(px + 30, top + 24, '焊杯开口朝上', 13, 600, '#7a5d12'))
            g.append(_t(px + 30, top + 44, '灰色是化满的锡', 13, 400, MUTED))
        elif i == 2:
            top = py + 90
            g.append(_bullet_up(px + 200, top))
            g.append(f'<line x1="{px + 200}" y1="{py + 44}" x2="{px + 200}" y2="{top + 8}" stroke="{WIRE["红"]}" stroke-width="10"/>')
            g.append(f'<line x1="{px + 200}" y1="{top + 8}" x2="{px + 200}" y2="{top + 34}" stroke="#c77b30" stroke-width="6"/>')
            g.append(f'<rect x="{px + 187}" y="{py + 44}" width="26" height="22" rx="5" fill="#3d7bd9" opacity="0.4" stroke="#2a5fae"/>')
            g.append(f'<line x1="{px + 330}" y1="{py + 60}" x2="{px + 222}" y2="{top + 30}" stroke="#555" stroke-width="7" stroke-linecap="round"/>')
            g.append(_t(px + 336, py + 67, '烙铁贴着焊杯', 14, 600))
            g.append(_t(px + 30, top + 24, '线芯插到底', 13, 600, '#a35a14'))
            g.append(_t(px + 236, py + ph - 30, '锡凝固（变哑光）前不要碰线', 13, 400, MUTED))
        else:
            g.append(f'<line x1="{px + 30}" y1="{cy}" x2="{px + 200}" y2="{cy}" stroke="{WIRE["红"]}" stroke-width="9"/>')
            g.append(_bullet(px + 196, cy, scale=1.25))
            g.append(f'<rect x="{px + 170}" y="{cy - 20}" width="90" height="40" rx="7" fill="#3d7bd9" opacity="0.45" stroke="#2a5fae"/>')
            g.append(_t(px + 215, cy + 50, '热缩管盖住焊杯', 14, 600, '#2a5fae', 'middle'))
            g.append(_t(px + 335, cy + 50, '插口露在外面', 14, 600, '#7a5d12', 'middle'))
            g.append(f'<path d="M{px + 335} {cy + 32} L{px + 335} {cy + 22}" stroke="#7a5d12" stroke-width="2" marker-end="url(#arrb)"/>')
        panels.append(''.join(g))
    defs = ('<defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            '<path d="M0 0 L10 5 L0 10 z" fill="#2a5fae"/></marker>'
            '<marker id="arrb" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            '<path d="M0 0 L10 5 L0 10 z" fill="#7a5d12"/></marker></defs>')
    return [_uri(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {pw} {ph}" width="{pw}" height="{ph}">{defs}'
                 f'<rect width="{pw}" height="{ph}" fill="#ffffff"/>{g}</svg>') for g in panels]
