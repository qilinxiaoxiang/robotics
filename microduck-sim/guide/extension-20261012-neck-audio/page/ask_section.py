"""'先看这里' section of EXTENSION-REVIEW.html: the three items Shawn was asked about, each with a drawing.

Numbers: pack-uart/README.md (socket centres, converter box), audio/README.md (amp board, speaker stack) and the
4UCON 19963 drawing that Adafruit links for its 2-pin 3.5 mm terminal block (product 724): body 8.5 mm tall, 7.0 mm deep,
2 x 3.5 + 0.8 = 7.8 mm wide.
"""
from __future__ import annotations

from pathlib import Path

S = 8.0          # px per mm in the pack drawing


def _px(y):      # robot y (left +) -> svg x, seen from behind (duck's left on the left)
    return 30 + (22 - y) * S


def _pz(z):
    return 30 + (32 - z) * S


def _socket_z(n):
    return -15.35 + (n - 1) * 2.542


def pack_svg() -> str:
    o = ['<svg viewBox="0 0 412 700" role="img" aria-label="从背后看背包：两排排母和挡在后面的降压板" '
         'style="width:100%;max-width:460px;height:auto;display:block;margin:0 auto">',
         '<style>.t{font:600 17px -apple-system,PingFang SC,sans-serif;fill:#1d2a26}'
         '.s{font:15px -apple-system,PingFang SC,sans-serif;fill:#1d2a26}</style>']
    # cover outline (drawn see-through)
    o.append(f'<rect x="{_px(18.6):.1f}" y="{_pz(29.5):.1f}" width="{37.2 * S:.1f}" height="{73.5 * S:.1f}" rx="14" '
             'fill="#f1f2f0" stroke="#8a8f8c" stroke-width="2"/>')
    o.append(f'<text class="s" x="{_px(0):.1f}" y="{_pz(-38):.1f}" text-anchor="middle">后盖（画成透明的）</text>')
    # sockets
    rows = {9.93: {4: ('GND', '#bfc5c2', '#6b716e'), 6: ('D14', '#f6d0cb', '#c0392b'), 7: ('D13', '#f6d0cb', '#c0392b')},
            -10.43: {}}
    for y, special in rows.items():
        for n in range(1, 9):
            fill, stroke = '#e2e5e3', '#a9afac'
            lab = None
            if n in special:
                lab, fill, stroke = special[n]
            cx, cz = _px(y), _pz(_socket_z(n))
            o.append(f'<rect x="{cx - 8.8:.1f}" y="{cz - 8.8:.1f}" width="17.6" height="17.6" rx="2" fill="{fill}" '
                     f'stroke="{stroke}" stroke-width="{2.4 if lab else 1.2}"/>')
            if lab:
                tx = cx - 14 if y > 0 else cx + 14
                o.append(f'<text class="t" x="{tx:.1f}" y="{cz + 6:.1f}" text-anchor="{"end" if y > 0 else "start"}">{lab}</text>')
    # converter on top of the upper sockets
    o.append(f'<rect x="{_px(13):.1f}" y="{_pz(27):.1f}" width="{26 * S:.1f}" height="{30 * S:.1f}" rx="4" '
             'fill="#8fb8e3" fill-opacity="0.82" stroke="#3f6fa3" stroke-width="2"/>')
    o.append(f'<text class="t" x="{_px(0):.1f}" y="{_pz(14):.1f}" text-anchor="middle">降压板</text>')
    o.append(f'<text class="s" x="{_px(0):.1f}" y="{_pz(10.5):.1f}" text-anchor="middle">（挡在排母后面）</text>')
    # numbered markers
    for (x, y, n, c) in ((_px(9.93) + 24, _pz(-1.4), '1', '#c0392b'), ):
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="13" fill="{c}"/>'
                 f'<text x="{x:.1f}" y="{y + 6:.1f}" text-anchor="middle" style="font:700 17px sans-serif;fill:#fff">{n}</text>')
    o.append(f'<text class="s" x="{_px(18.6):.1f}" y="690">← 鸭子的左边</text>')
    o.append(f'<text class="s" x="{_px(-18.6):.1f}" y="690" text-anchor="end">鸭子的右边 →</text>')
    o.append(f'<text class="s" x="{_px(0):.1f}" y="22" text-anchor="middle">↑ 上（头的方向）</text>')
    o.append('</svg>')
    return ''.join(o)


def amp_svg() -> str:
    k = 10.0
    o = ['<svg viewBox="0 0 460 330" role="img" aria-label="功放板和它上面的接线端子" '
         'style="width:100%;max-width:480px;height:auto;display:block;margin:0 auto">',
         '<style>.t{font:600 16px -apple-system,PingFang SC,sans-serif;fill:#1d2a26}'
         '.s{font:14px -apple-system,PingFang SC,sans-serif;fill:#1d2a26}</style>']
    # top view
    bx, by = 20, 40
    o.append('<text class="t" x="20" y="24">从上往下看</text>')
    o.append(f'<rect x="{bx}" y="{by}" width="{17.78 * k}" height="{19.05 * k}" rx="6" fill="#3d5a99"/>')
    tbx = bx + (17.78 - 7.8) / 2 * k
    o.append(f'<rect x="{tbx}" y="{by + 4}" width="{7.8 * k}" height="{7.0 * k}" rx="3" fill="#2f8f6a" stroke="#14553d" stroke-width="2"/>')
    for i in range(2):
        cx = tbx + (2.15 + 3.5 * i) * k
        o.append(f'<circle cx="{cx}" cy="{by + 4 + 3.5 * k}" r="13" fill="#d9dcdb" stroke="#555" stroke-width="1.5"/>'
                 f'<path d="M{cx - 8} {by + 39} h16 M{cx} {by + 31} v16" stroke="#555" stroke-width="2.5"/>')
    for i in range(7):
        cx = bx + (1.27 + 2.54 * (i + 0.5) + 0.4) * k
        o.append(f'<rect x="{cx - 6}" y="{by + 19.05 * k - 26}" width="12" height="12" fill="#d4a017"/>')
    o.append(f'<text class="s" x="{bx + 8.89 * k}" y="{by + 19.05 * k - 34}" text-anchor="middle" style="fill:#fff">排针（插杜邦线到 Pi）</text>')
    o.append(f'<text class="s" x="{bx + 8.89 * k}" y="{by + 8.6 * k + 20}" text-anchor="middle" style="fill:#fff">接线端子</text>')
    # side view
    sx, base = 240, 300
    o.append(f'<text class="t" x="{sx}" y="24">从侧面看</text>')
    bt = base - 1.57 * k                      # board top
    tb_top = bt - 8.5 * k
    roof = tb_top - 2.2 * k
    o.append(f'<line x1="{sx}" y1="{roof}" x2="{sx + 210}" y2="{roof}" stroke="#8a8f8c" stroke-width="3" stroke-dasharray="8 5"/>')
    o.append(f'<text class="s" x="{sx + 210}" y="{roof - 8}" text-anchor="end">头盖内壁</text>')
    o.append(f'<rect x="{sx + 20}" y="{bt}" width="{19.05 * 8}" height="{1.57 * k}" fill="#3d5a99"/>')
    o.append(f'<rect x="{sx + 70}" y="{tb_top}" width="{7.0 * k}" height="{8.5 * k}" rx="3" fill="#2f8f6a" stroke="#14553d" stroke-width="2"/>')
    o.append(f'<rect x="{sx + 90}" y="{tb_top - 5}" width="30" height="5" fill="#d9dcdb" stroke="#555"/>')
    o.append(f'<text class="s" x="{sx + 105}" y="{(tb_top + bt) / 2 + 5}" text-anchor="middle" style="fill:#fff">端子</text>')
    ax = sx + 55
    o.append(f'<path d="M{ax} {tb_top} V{bt} M{ax - 5} {tb_top} h10 M{ax - 5} {bt} h10" stroke="#1d2a26" stroke-width="1.5"/>'
             f'<text class="t" x="{ax - 8}" y="{(tb_top + bt) / 2 + 6}" text-anchor="end">8.5 mm</text>')
    o.append(f'<path d="M{ax} {roof} V{tb_top}" stroke="#c96a12" stroke-width="2"/>'
             f'<text class="s" x="{ax - 8}" y="{roof + 16}" text-anchor="end" style="fill:#c96a12">空 2.2 mm</text>')
    o.append(f'<text class="s" x="{sx + 146}" y="{tb_top + 4}">顶上是螺丝</text>')
    wy = bt - 28
    o.append(f'<path d="M{sx + 210} {wy} H{sx + 144}" stroke="#c0392b" stroke-width="3"/>'
             f'<path d="M{sx + 154} {wy - 6} l-10 6 l10 6" fill="none" stroke="#c0392b" stroke-width="3"/>')
    o.append(f'<text class="s" x="{sx + 210}" y="{wy - 10}" text-anchor="end" style="fill:#c0392b">扬声器线</text>')
    o.append('</svg>')
    return ''.join(o)


def speaker_svg() -> str:
    o = ['<svg viewBox="0 0 500 300" role="img" aria-label="扬声器在头盖里的夹层：头盖、围框、泡棉圈、扬声器、压板" '
         'style="width:100%;max-width:480px;height:auto;display:block;margin:0 auto">',
         '<style>.s{font:15px -apple-system,PingFang SC,sans-serif;fill:#1d2a26}</style>']
    L, R = 70, 370
    # roof with sound holes
    o.append(f'<rect x="20" y="40" width="400" height="22" fill="#b9bfbc"/>')
    for i in range(7):
        o.append(f'<rect x="{150 + i * 22}" y="40" width="10" height="22" fill="#fff"/>')
    # collar walls and lip
    o.append(f'<rect x="{L - 22}" y="62" width="22" height="150" fill="#b9bfbc"/><rect x="{R}" y="62" width="22" height="150" fill="#b9bfbc"/>')
    o.append(f'<rect x="{L}" y="62" width="34" height="22" fill="#b9bfbc"/><rect x="{R - 34}" y="62" width="34" height="22" fill="#b9bfbc"/>')
    # foam ring
    o.append(f'<rect x="{L}" y="84" width="34" height="12" fill="#f2c94c" stroke="#b8901a"/>'
             f'<rect x="{R - 34}" y="84" width="34" height="12" fill="#f2c94c" stroke="#b8901a"/>')
    # speaker
    o.append(f'<rect x="{L}" y="96" width="{R - L}" height="12" fill="#3a3a3a"/>'
             f'<path d="M{L + 40} 108 L{L + 90} 150 H{R - 90} L{R - 40} 108 Z" fill="#555"/>'
             f'<rect x="{L + 110}" y="150" width="{R - L - 220}" height="26" fill="#3a3a3a"/>')
    # retainer and screws
    o.append(f'<rect x="{L - 22}" y="212" width="{R - L + 44}" height="14" fill="#c96a12" fill-opacity="0.85"/>')
    o.append(f'<rect x="{L - 22}" y="108" width="22" height="104" fill="#b9bfbc"/>')
    for x in (L - 11, R + 11):
        o.append(f'<rect x="{x - 4}" y="150" width="8" height="76" fill="#6b716e"/><rect x="{x - 9}" y="226" width="18" height="6" fill="#6b716e"/>')
    labels = ((300, 30, '① 头盖顶上的出声孔'), (L - 48, 286, '② 围框（头盖上打印出来的）'),
              (R + 28, 95, '③ 泡棉圈'), (220, 196, '④ 扬声器'), (220, 250, '⑤ 压板，2 颗螺丝顶上去'))
    for x, y, t in labels:
        anchor = 'middle' if x in (220, 300) else 'start'
        o.append(f'<text class="s" x="{x}" y="{y}" text-anchor="{anchor}">{t}</text>')
    o.append('</svg>')
    return ''.join(o)


PHOTO = Path(__file__).resolve().parents[2] / 'content' / 'wiring' / 'openrb_top.png'


def j12_svg() -> str:
    """Enlarged J12 corner of the guide's OpenRB photo (crop 40..170 x 320..400 px, x6) with the two solder holes marked."""
    import base64
    import io
    from PIL import Image
    im = Image.open(PHOTO).convert('RGB').crop((40, 320, 170, 400)).resize((780, 480), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=88)
    uri = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
    o = ['<svg viewBox="0 0 780 700" role="img" aria-label="OpenRB 上 J12 四个焊孔：Tx、Rx、V、G" '
         'style="width:100%;max-width:520px;height:auto;display:block;margin:0 auto">',
         '<style>.b{font:600 36px -apple-system,PingFang SC,sans-serif}</style>',
         f'<image href="{uri}" x="0" y="0" width="780" height="480"/>']
    for x, col, text, ty in ((315, '#1f9e5c', 'Rx：绿线 → Pi 第 8 脚', 580), (232, '#ffffff', 'Tx：白线 → Pi 第 10 脚', 650)):
        o.append(f'<circle cx="{x}" cy="192" r="36" fill="none" stroke="{col}" stroke-width="7"/>')
        o.append(f'<path d="M{x} 228 V{ty - 40}" stroke="{col}" stroke-width="5"/>')
        o.append(f'<rect x="{x - 12}" y="{ty - 40}" width="{780 - x + 2}" height="52" rx="6" fill="#1d2a26" fill-opacity="0.9"/>'
                 f'<text class="b" x="{x}" y="{ty}" style="fill:{col if col != "#ffffff" else "#fff"}">{text}</text>')
    o.append('<rect x="360" y="150" width="160" height="86" rx="8" fill="none" stroke="#c0392b" stroke-width="5" stroke-dasharray="10 6"/>')
    o.append('<rect x="370" y="250" width="230" height="52" rx="6" fill="#1d2a26" fill-opacity="0.9"/>'
             '<text class="b" x="382" y="289" style="fill:#ff8c7a">V、G 空着</text>')
    o.append('</svg>')
    return ''.join(o)


def ask_section(img, pu_png) -> str:
    return f'''
<p>我前面让你"确认改动 5""量接线端子""找闭孔泡棉"，没配图，说得不清楚。下面每件事都配了图。三件事现在都定了：串口按你说的焊线，端子不用量，泡棉你去找。</p>

<h3>1. OpenRB 串口：拆掉 J12 上的座子，把两根线焊进去（你定的）</h3>
<p><b>为什么要改</b>：Pi 靠两根串口线控制所有舵机。指南原来让杜邦线插 OpenRB 侧边的 D13、D14，但板子装进背包后，降压板正好压在这两个孔后面，只剩 2 mm，插不进去（下图 ①）。后盖开窗的办法你不要，所以改焊 J12。</p>
{pack_svg()}
<p>J12 是 OpenRB 下部一排 4 个小焊孔，就是你焊了 4 针座的地方。它本身就是一个串口（芯片的 Serial2），只用其中两个孔：</p>
{j12_svg()}
<p><b>步骤</b>：</p>
<ol>
<li><b>拆座子</b>：先用斜口钳把座子的塑料壳剪开拿掉，剩下 4 根针一根一根地拆：烙铁加热一根，用镊子拔出来。最后用吸锡带把 4 个孔清通。</li>
<li><b>备线</b>：拿两根公对母杜邦线，一白一绿，剪掉公头，剥出约 2 mm 的线头并上锡。母头那端留着插 Pi。</li>
<li><b>焊</b>：从有字的那一面把线头穿进孔里焊。绿线焊 Rx，接 Pi 第 8 脚。白线焊 Tx，接 Pi 第 10 脚。V 和 G 空着，不用接地线，两块板已经通过降压板共地。</li>
<li><b>防拉断</b>：两根线贴着板面往上折，用一小条胶带贴在板边，别让焊点受力。</li>
<li><b>固件</b>：给 OpenRB 烧 J12 版固件。我已经写好并编译通过，在 <code>pack-uart/firmware/openrb_uart_bridge_j12/</code>，还没上板测。和原来比只改了一行：串口从 Serial3 换成 Serial2。</li>
</ol>
<p>线出了板子以后，走 V1.8 指南最早的 J12 路线，从背包顶上的出线口出去。背包和后盖都不改，也不开洞。装配检查里一直带着这条串口线。</p>

<h3>2. 接线端子是什么（不用你量了）</h3>
<p>功放板是把 Pi 的声音信号放大、推动扬声器的小板子。板上有一个绿色小方块，叫<b>接线端子</b>。它侧面有两个孔，扬声器的两根线插进去；顶上有两颗小螺丝，拧紧就把线夹住。这样扬声器线不用焊在板子上，拆的时候松开螺丝就行。</p>
{amp_svg()}
<p>之前我不知道它有多高，所以让你量。现在查到了：Adafruit 给这个端子挂的官方图纸（4UCON 19963）写的是 <b>8.5 mm</b>，比我原来假设的 10 mm 矮。装好后离头盖还有约 2.2 mm，放得下，<b>不用你量了</b>。</p>
<p class="note">装配时记一件事：先把扬声器线拧进端子，再把功放装进头里。装进去以后螺丝刀够不着端子上的螺丝。</p>

<h3>3. 闭孔泡棉是什么（装扬声器时用，不急）</h3>
<p>扬声器装在头盖顶下面，声音从头顶的小孔出去。扬声器和头盖之间要垫一圈 1 mm 厚的软泡棉，有两个作用：</p>
<ul>
<li>把缝封住。扬声器背面发出的声音如果从缝里绕到前面，会和前面的声音互相抵消，声音变小、变闷。</li>
<li>压紧防震。压板把扬声器压在泡棉上，扬声器不会晃，不会嗡嗡响。</li>
</ul>
{speaker_svg()}
<p><b>"闭孔"是什么意思</b>：泡棉里的小气泡是封闭的、不透气，比如<b>泡棉双面胶</b>、手工用的 <b>EVA 海绵纸</b>。洗碗海绵是开孔的，透气，起不到封缝的作用，不能用。</p>
<p><b>用什么</b>：家里常见的 1 mm 厚泡棉双面胶就可以，只撕一面的离型纸，贴在扬声器正面边缘。剪成一个外圈约 30×20 mm、宽 1.5 mm 的框。到装扬声器那一步再弄就行。</p>
'''
