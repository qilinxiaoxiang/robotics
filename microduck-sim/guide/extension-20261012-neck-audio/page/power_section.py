"""'供电' section of EXTENSION-REVIEW.html: should the OMX 12 V parts replace the USB-PD front end?

Numbers:
- Load: simulated walking about 2.05 A mean and 5.4 A 20 ms peaks at 5 V (guide step 'current'; omx-power-chain memory).
- Pi Zero W with camera: about 2 W (estimate).
- DFR1202: 6-24 V in, 5 V out, 16 A, >90 % at 12 V (DFRobot product 2907).
- ROBOTIS SMPS 12 V 5 A (PS-10); SMPS2Dynamixel outputs are Molex 3P/4P only (robotis.us).
- Pack converter bay: x -45..-37, |y| <= 13, z -3..27, i.e. 26 x 30 x 8 mm (pack-uart/README.md).
- XL4015 5 A module: common size about 51 x 26 x 14 mm (vendor listings; inference, not measured on Shawn's board).
- Tether: 2 m of 18 AWG, 0.021 ohm/m, 4 m loop.
"""
from __future__ import annotations


def _chain(items) -> str:
    out = ['<div class="chain">']
    for k, (text, kind) in enumerate(items):
        if k:
            out.append('<span class="arrow">→</span>')
        out.append(f'<span class="node {kind}">{text}</span>')
    out.append('</div>')
    return ''.join(out)


def size_svg() -> str:
    k = 5.0
    o = ['<svg viewBox="0 0 440 250" role="img" aria-label="XL4015 降压板和背包里降压板位置的大小对比" '
         'style="width:100%;max-width:480px;height:auto;display:block;margin:0 auto">',
         '<style>.s{font:15px -apple-system,PingFang SC,sans-serif;fill:#1d2a26}'
         '.t{font:600 16px -apple-system,PingFang SC,sans-serif;fill:#1d2a26}</style>',
         '<text class="t" x="20" y="22">从上往下看（同一比例）</text>']
    x0, y0 = 20, 40
    o.append(f'<rect x="{x0}" y="{y0}" width="{26 * k}" height="{30 * k}" fill="#e7f5ee" stroke="#1f7a52" stroke-width="3"/>')
    o.append(f'<text class="s" x="{x0 + 13 * k}" y="{y0 + 15 * k - 8}" text-anchor="middle">背包里</text>'
             f'<text class="s" x="{x0 + 13 * k}" y="{y0 + 15 * k + 12}" text-anchor="middle">降压板的位置</text>'
             f'<text class="s" x="{x0 + 13 * k}" y="{y0 + 30 * k + 22}" text-anchor="middle">26×30 mm，厚 8 mm</text>')
    x1 = 180
    o.append(f'<rect x="{x1}" y="{y0 + 10}" width="{51 * k}" height="{26 * k}" rx="4" fill="#cfe0f5" stroke="#3f6fa3" stroke-width="3"/>')
    for i in range(2):
        o.append(f'<circle cx="{x1 + (22 + 9 * i) * k}" cy="{y0 + 10 + 9 * k}" r="11" fill="#3b6fb6"/>')
    o.append(f'<rect x="{x1 + 3 * k}" y="{y0 + 10 + 14 * k}" width="{14 * k}" height="{9 * k}" fill="#9aa3ab"/>')
    o.append(f'<text class="s" x="{x1 + 25.5 * k}" y="{y0 + 10 + 26 * k + 22}" text-anchor="middle">XL4015 板 约 51×26 mm，高约 14 mm</text>')
    o.append('</svg>')
    return ''.join(o)


def splice_svg() -> str:
    """SMPS2DXL 3P cable with the servo plug cut off, spliced to the 2 m tether. Pin 2 (middle) = VDD per ROBOTIS."""
    o = ['<svg viewBox="0 0 360 250" role="img" aria-label="转接板的 3 线连接线剪掉舵机插头后接到 2 m 线" '
         'style="width:100%;max-width:420px;height:auto;display:block;margin:0 auto">',
         '<style>.s{font:16px -apple-system,PingFang SC,sans-serif;fill:#1d2a26}'
         '.t{font:600 17px -apple-system,PingFang SC,sans-serif}</style>']
    o.append('<text class="s" x="4" y="22">12 V 适配器</text>'
             '<rect x="4" y="32" width="54" height="36" rx="6" fill="#333"/>'
             '<path d="M58 50 H84" stroke="#333" stroke-width="6"/>')
    o.append('<rect x="84" y="20" width="100" height="62" rx="6" fill="#2a4f8f"/>'
             '<rect x="166" y="36" width="18" height="28" rx="2" fill="#f2f2f2" stroke="#888"/>'
             '<text class="s" x="134" y="100" text-anchor="middle">SMPS2DXL 转接板</text>')
    o.append('<path d="M184 50 H262" stroke="#555" stroke-width="9"/>'
             '<path d="M268 36 l16 28 M284 36 l-16 28" stroke="#c0392b" stroke-width="3"/>'
             '<text class="s" x="300" y="56" style="fill:#c0392b">剪</text>')
    ends = ((150, '#1d2a26', '边上：地线 → 焊黑线'), (185, '#c0392b', '中间：+12 V → 焊红线'),
            (220, '#8a8f8c', '边上：数据线 → 包起来'))
    for k, (y, col, lab) in enumerate(ends):
        o.append(f'<path d="M{244 + 8 * k} 56 V{y} H232" stroke="{col}" stroke-width="3" fill="none"/>'
                 f'<circle cx="230" cy="{y}" r="5" fill="{col}"/>'
                 f'<text class="t" x="220" y="{y + 6}" text-anchor="end" style="fill:{col}">{lab}</text>')
    o.append('</svg>')
    return ''.join(o)


CSS = '''
.chain{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:8px 0 14px}
.node{display:inline-block;border-radius:8px;padding:4px 10px;font-size:15px;line-height:1.45;border:1px solid var(--line);background:#fff}
.node.wall{background:#fff4e5;border-color:#e2b46a}
.node.drop{background:#fdecea;border-color:#e7a39b;text-decoration:line-through;color:#8a3a2f}
.node.robot{background:#e7f5ee;border-color:#8cc7a8}
.node.bad{background:#fdecea;border-color:#c0392b;color:#8a1f12;font-weight:600}
.node.new{background:#e8f0fb;border-color:#7ea6d8;font-weight:600}
.arrow{color:var(--muted)}
'''


def power_section() -> str:
    now = _chain([('小米充电器', 'wall'), ('PD 板：拨 5 个开关、割一根线、装盒', 'wall'), ('2 m 线', 'wall'),
                  ('XT30 插头', 'robot'), ('降压板（背包里）', 'robot'), ('OpenRB：3 条舵机链 5 V', 'robot'),
                  ('Pi 5 V', 'robot')])
    rec = _chain([('OMX 的 12 V 适配器', 'new'), ('SMPS2DXL 转接板', 'new'), ('3 线连接线（剪掉舵机插头）', 'new'), ('2 m 线', 'wall'),
                  ('XT30 插头', 'robot'), ('降压板（背包里）', 'robot'), ('OpenRB：3 条舵机链 5 V', 'robot'),
                  ('Pi 5 V', 'robot')])
    gone = _chain([('小米充电器', 'drop'), ('PD 板', 'drop'), ('拨开关', 'drop'), ('割线', 'drop'), ('装盒', 'drop')])
    omx = _chain([('12 V 适配器', 'wall'), ('SMPS2DXL 转接板', 'wall'), ('线', 'wall'),
                  ('OpenRB 舵机口：全是 12 V', 'bad'), ('XL4015 降压板 + 预制线', 'bad'),
                  ('15 个舵机串成一条', 'bad'), ('Pi：没有 5 V', 'bad')])
    return f'''
<p><b>已定（10 月 13 日）</b>：按推荐方案做正式供电。<b>结论</b>：可以简单很多，但只换墙那头。用 OMX 的 12 V 适配器代替"小米充电器 + PD 板"，机器人身上一样不动：降压板、背包、三条舵机链、Pi 的供电都照旧。不建议把 OMX-F 那套接法（OpenRB 走 12 V，再用 XL4015 降压）原样做成正式方案。</p>

<h3>三种接法放在一起看</h3>
<p><b>现在的正式方案</b>（橙色在墙边，绿色在机器人身上）：</p>
{now}
<p><b>推荐：只把墙那头换成 12 V</b>（蓝色是新换的）：</p>
{rec}
<p>这些就都不要了：</p>
{gone}
<p><b>照搬 OMX-F 的接法</b>（红色是有问题的地方）：</p>
{omx}

<h3>推荐方案为什么行</h3>
<ul>
<li><b>降压板吃得下 12 V</b>：DFR1202 输入 6 到 24 V，输出 5 V，最大 16 A。原来喂 20 V，现在喂 12 V，输出一样。</li>
<li><b>电够用</b>：走路时舵机平均约 2 A（5 V），加上 Pi，一共约 12 W，换到 12 V 这边约 1.1 A。走路时约 20 毫秒的尖峰约 5.4 A（5 V），换到 12 V 这边约 2.7 A。适配器是 5 A 的。</li>
<li><b>线不用换</b>：2 m 的 18 AWG 线在 2.7 A 时只掉约 0.2 V。</li>
<li><b>机器人身上零改动</b>：XT30、降压板、背包、指南里的舵机和 Pi 接线全不变。</li>
</ul>

<h3>为什么不把 OMX-F 接法做成正式方案</h3>
<ul>
<li><b>XL4015 放不进背包</b>：它比背包里给降压板留的位置大一圈，还高出 6 mm。要放进去，背包和壳子都得重新设计。</li>
</ul>
{size_svg()}
<ul>
<li><b>15 个舵机串成一条，要从裆下走线</b>：右脚踝要拉一根线到左脚踝，这根线会挂在两腿之间。另外，第一段线要过全部电流，走路尖峰约 5.4 A，舵机插头每针只有约 3 A。</li>
<li><b>Pi 没电</b>：XL4015 的 5 V 只有舵机插头，Pi 还得另找 5 V。</li>
<li><b>容易烧舵机</b>：OpenRB 四个舵机口全是 12 V。以后哪条腿的线顺手插回 OpenRB，那条腿的 XL330 当场烧掉（它们最高只能接 6 V）。</li>
</ul>
<p>现在桌上调试继续用 OMX-F 那套接法没问题，它是临时拖线用的。</p>

<h3>换成推荐方案怎么接（不用买东西）</h3>
<p>用你说的那根：一头插在转接板上的 3 线连接线，把另一头的舵机插头剪掉，分出三根线接到 2 m 线上。</p>
{splice_svg()}
<ol>
<li><b>选线</b>：你有 3 套，拿一套不给机械臂用的转接板和它的线。</li>
<li><b>剪</b>：把舵机插头那端剪掉，整根线留长，三根线头各剥出约 5 mm。</li>
<li><b>分地线</b>：插上适配器，红表笔接中间那根，黑表笔分别碰两边，读到 12 V 的那根是地线。然后拔掉适配器。</li>
<li><b>接</b>：中间那根（+12 V）焊 2 m 线的红线，地线焊黑线，各套一段热缩管。数据线剪短，单独用热缩管包好，不接。线对线焊，不焊在板子上。</li>
<li><b>防拉</b>：用扎带把两个接头固定在转接板旁边，拽 2 m 线时不会扯到焊点。</li>
<li><b>验</b>：插上适配器，在 2 m 线另一头的 XT30 母头量电压，红表笔在 + 杯，应读 11.5 到 12.5 V。读到负数说明红黑接反了。确认后再插机器人。</li>
</ol>
<ul>
<li><b>这根线够粗</b>：ROBOTIS 舵机线是 21 AWG，只有十几厘米长，走路尖峰 2.7 A 时掉不到 0.05 V。机械臂平时也用这条路过电。</li>
<li><b>这样就不要的东西</b>：小米充电器、PD 板、拨开关、割线、装盒。指南里 PD 那一步换成上面这 6 步。</li>
</ul>
'''
