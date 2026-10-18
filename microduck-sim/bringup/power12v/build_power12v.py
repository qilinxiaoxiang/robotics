"""Build POWER-12V.html: tethered 12 V bench power for MicroDuck, wired the way the OMX-F follower is.

Chain (Shawn's OMX-F, 2026-10-12): ROBOTIS 12 V adapter -> SMPS2DXL -> his existing SMPS2DXL cable -> one OpenRB-150
DXL port, JP1 cap on VIN(DXL) (the +5V pin left empty), so every OpenRB DXL port carries 12 V. A second port takes the
ROBOTIS XL4015 prefab harness: the pair from that plug goes to XL4015 IN, the pair from the other plug to OUT, and the
other plug feeds the duck at 5 V. The duck's three servo chains (right leg 5->1, left leg 10->6, neck 12->11->13->14->15)
are joined into one chain behind that plug, because the remaining two OpenRB ports carry 12 V and must stay empty.

Sources (checked 2026-10-12):
- Photos: Shawn's own photos of the SMPS2DXL and XL4015 (img/shawn_smps2dxl_xl4015.jpg; "IN+" and "OUT+" sit beside
  the lower screw of each terminal block) and of the XL4015 harness (img/shawn_xl4015_harness.jpg).
- 12 V adapter render: ROBOTIS OMX-F hardware-setup image, docs.robotis.com quick start guide (img/robotis_smps_12v.png).
- OpenRB-150 photo and port/JP1 fractions: ../parts/parts.json (openrb_150).
- ROBOTIS OMX-F guide data (docs.robotis.com/interactive/omx/models/follower-xl4015.json): the XL4015 prefab harness
  runs from ID 13 (12 V side, IN+/IN-) to ID 14 (XL330 side, OUT+/OUT-).
- Follower log omx-local/evidence/hardware-check.json (2026-10-05): XL330 IDs 14-16 read 5.0-5.1 V behind this XL4015.
- Duck chains: guide/content/steps.py (leg chains 5->1 and 10->6; neck links 12->11, 11->13, 13->14, 14->15).
- Load: MicroDuck walking simulation, about 2.05 A mean at 5 V, 20 ms peaks near 5.4 A.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'POWER-12V.html'
PARTS = HERE.parent / 'parts' / 'photos'


def uri(im: Image.Image, fmt: str = 'JPEG', quality: int = 86) -> str:
    buf = io.BytesIO()
    if fmt == 'JPEG':
        im.convert('RGB').save(buf, 'JPEG', quality=quality)
    else:
        im.save(buf, fmt)
    return f'data:image/{fmt.lower()};base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


box = Image.open(HERE / 'img' / 'shawn_smps2dxl_xl4015.jpg')
s2d = box.crop((230, 240, 1080, 700))          # 850 x 460
xl = box.crop((100, 1020, 1100, 1440))         # 1000 x 420
harness = Image.open(HERE / 'img' / 'shawn_xl4015_harness.jpg').crop((180, 330, 1060, 1460)).resize((334, 429), Image.LANCZOS)
smps = Image.open(HERE / 'img' / 'robotis_smps_12v.png').convert('RGB')
orb = Image.open(PARTS / 'openrb_150_top.png').convert('RGBA')
orb = orb.resize((408, 976), Image.LANCZOS).rotate(90, expand=True)   # USB-C left, terminal block right

IMG = {'s2d': uri(s2d), 'xl': uri(xl), 'smps': uri(smps), 'orb': uri(orb, 'PNG'), 'harness': uri(harness)}


def servo(x, y, sid, name):
    return (f'<rect x="{x}" y="{y}" width="120" height="80" rx="10" fill="#263238"/>'
            f'<text x="{x + 60}" y="{y + 38}" class="sid">ID {sid}</text>'
            f'<text x="{x + 60}" y="{y + 66}" class="sname">{name}</text>')


ROW_A = [(1390, 5, '右髋 yaw'), (1250, 4, '髋 roll'), (1110, 3, '髋 pitch'), (970, 2, '膝'), (830, 1, '右脚踝')]
ROW_B = [(150, 6, '左脚踝'), (290, 7, '膝'), (430, 8, '髋 pitch'), (570, 9, '髋 roll'), (710, 10, '左髋 yaw'),
         (960, 12, '颈 pitch'), (1100, 11, '头 pitch'), (1240, 13, '头 yaw'), (1380, 14, '头 roll'), (1520, 15, '下巴')]
chain = ''.join(servo(x, 1240, i, n) for x, i, n in ROW_A) + ''.join(servo(x, 1420, i, n) for x, i, n in ROW_B)
links = ''.join(f'<path d="M{a[0]},1280 L{b[0] + 120},1280" class="link"/>' for a, b in zip(ROW_A, ROW_A[1:]))
links += ''.join(f'<path d="M{a[0] + 120},1460 L{b[0]},1460" class="link"/>'
                 for a, b in zip(ROW_B[:5], ROW_B[1:5]))
links += ''.join(f'<path d="M{a[0] + 120},1460 L{b[0]},1460" class="link"/>' for a, b in zip(ROW_B[5:], ROW_B[6:]))

# Canvas 2400 x 1640. Points read from the placed photos:
# SMPS2DXL at (430,130) scale 0.75: jack (666,408), J1 3P port (1052,220), red LED (936,291).
# OpenRB at (1280,170) scale 1: edge ports J10 (1580, top) and J11 (1580, bottom), middle ports J8 (1580,342) and
#   J9 (1580,402), JP1 pins +5V/mid/VIN at (2042, 378/414/450), USB-C (1370,374), terminal block (2185,348/400).
# XL4015 at (1460,800) scale 0.8: IN- (2202,910), IN+ (2202,966), OUT- (1512,910), OUT+ (1512,974).
SVG = f'''
<svg viewBox="0 0 2400 1640" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="12 V 适配器经 SMPS2DXL 进 OpenRB 舵机口，XL4015 线从另一个口降到 5 V，15 个舵机串成一条链">
  <rect width="2400" height="1640" fill="#ffffff"/>
  <rect x="20" y="70" width="2360" height="1070" rx="18" fill="#fff8e1" stroke="#ffcc80" stroke-width="3"/>
  <text x="44" y="112" class="zone">12 V 区：SMPS2DXL、OpenRB 的四个舵机口、XL4015 的 IN</text>
  <rect x="20" y="1160" width="2360" height="460" rx="18" fill="#e8f5e9" stroke="#a5d6a7" stroke-width="3"/>
  <text x="44" y="1202" class="zone">5 V 区：XL4015 OUT 以后，15 个舵机串成一条</text>

  <!-- 1. adapter -->
  <image href="{IMG['smps']}" x="40" y="150" width="330" height="286"/>
  <circle cx="64" cy="170" r="24" class="num"/><text x="64" y="180" class="numt">1</text>
  <text x="40" y="482" class="lab">12 V 适配器</text>
  <text x="40" y="518" class="sub2">ROBOTIS，OMX 套件</text>

  <!-- 2. SMPS2DXL with its own cable, exactly as on the OMX-F -->
  <image href="{IMG['s2d']}" x="430" y="130" width="638" height="345"/>
  <path d="M323,257 C390,257 380,490 520,490 L666,490 L666,474" fill="none" stroke="#424242" stroke-width="12" stroke-linecap="round"/>
  <rect x="650" y="428" width="32" height="46" rx="6" fill="#212121" stroke="#ffffff" stroke-width="3"/>
  <circle cx="936" cy="291" r="24" class="ring"/>
  <circle cx="456" cy="152" r="24" class="num"/><text x="456" y="162" class="numt">2</text>
  <text x="700" y="528" class="lab">SMPS2DXL：照 OMX-F 原样</text>
  <text x="700" y="566" class="sub2">圆口插 12 V，红灯（橙圈）亮 = 有电</text>
  <rect x="1048" y="196" width="40" height="48" rx="5" fill="#f3e5c8" stroke="#8d6e63" stroke-width="3"/>
  <path d="M1088,220 L1120,220 L1120,128 L1580,128 L1580,150" fill="none" stroke="#9e9e9e" stroke-width="14" stroke-linejoin="round"/>
  <rect x="1550" y="150" width="60" height="50" rx="6" fill="#fafafa" stroke="#616161" stroke-width="3"/>
  <text x="1140" y="110" class="sub2">你 OMX-F 上 SMPS2DXL → OpenRB 那根线</text>

  <!-- 3. OpenRB-150 with 12 V on its rail -->
  <image href="{IMG['orb']}" x="1280" y="170" width="976" height="408"/>
  <circle cx="2042" cy="432" r="40" class="ring2"/>
  <circle cx="1370" cy="374" r="34" class="ring2"/>
  <path d="M1556,320 L1604,364 M1604,320 L1556,364 M1556,380 L1604,424 M1604,380 L1556,424" stroke="#d50000" stroke-width="9" stroke-linecap="round"/>
  <path d="M1610,372 L1700,606" stroke="#d50000" stroke-width="3" stroke-dasharray="8 6"/>
  <circle cx="1306" cy="196" r="24" class="num"/><text x="1306" y="206" class="numt">3</text>
  <text x="1290" y="622" class="lab">OpenRB-150</text>
  <text x="1290" y="660" class="sub2">任一块都行</text>
  <text x="1710" y="626" class="warnt">中间两个口（红叉）空着：现在都是 12 V</text>
  <text x="1710" y="666" class="sub2">跳线帽（紫圈）放 VIN(DXL) 那边，+5V 那针空着</text>
  <text x="1710" y="702" class="sub2">绿色端子不用；USB-C（紫圈）插 MacBook 做标定</text>

  <!-- 4. XL4015 harness: IN plug in the bottom edge port -->
  <image href="{IMG['harness']}" x="56" y="600" width="334" height="429"/>
  <circle cx="80" cy="624" r="24" class="num"/><text x="80" y="634" class="numt">4</text>
  <text x="420" y="652" class="lab">XL4015 线（你照片里那根）</text>
  <text x="420" y="694" class="sub2">两头一样，各一个舵机小白头</text>
  <text x="420" y="730" class="sub2">每个头分出一对端子，带红圈的是 +</text>
  <text x="420" y="766" class="sub2">插 OpenRB 那头的一对 → XL4015 的 IN</text>
  <text x="420" y="802" class="sub2">插舵机那头的一对 → XL4015 的 OUT</text>
  <text x="420" y="838" class="sub2">红圈那根应该从插头中间那根针出来</text>

  <rect x="1550" y="548" width="60" height="50" rx="6" fill="#fafafa" stroke="#616161" stroke-width="3"/>
  <path d="M1580,598 L1580,800" class="hw"/>
  <path d="M1580,750 L2330,750 L2330,966 L2250,966" class="hw"/>
  <path d="M1580,780 L2290,780 L2290,910 L2250,910" class="hw"/>
  <rect x="2262" y="958" width="18" height="16" fill="#e53935"/>
  <rect x="2226" y="958" width="24" height="16" rx="3" fill="#eeeeee" stroke="#9e9e9e"/>
  <rect x="2226" y="902" width="24" height="16" rx="3" fill="#eeeeee" stroke="#9e9e9e"/>
  <text x="1620" y="738" class="sub2">IN 这一对（12 V）</text>

  <!-- 5. XL4015 -->
  <image href="{IMG['xl']}" x="1460" y="800" width="800" height="336"/>
  <circle cx="2202" cy="910" r="22" class="ring"/><circle cx="2202" cy="966" r="22" class="ring"/>
  <circle cx="1512" cy="910" r="22" class="ring"/><circle cx="1512" cy="974" r="22" class="ring"/>
  <circle cx="1796" cy="1068" r="26" class="ring2"/><circle cx="1940" cy="1068" r="26" class="ring2"/>
  <rect x="1548" y="1088" width="190" height="34" rx="8" fill="none" stroke="#6a1b9a" stroke-width="4"/>
  <circle cx="1486" cy="826" r="24" class="num"/><text x="1486" y="836" class="numt">5</text>
  <text x="2140" y="880" class="pin halo" text-anchor="middle">IN−</text>
  <text x="2140" y="1010" class="pinr halo" text-anchor="middle">IN+</text>

  <!-- OUT pair plus the straight data wire run to the second plug -->
  <path d="M1580,800 L1410,800 L1410,1170" class="hw"/>
  <path d="M1490,910 L1430,910 L1430,1170" class="hw"/>
  <path d="M1490,974 L1450,974 L1450,1170" class="hw"/>
  <rect x="1462" y="966" width="18" height="16" fill="#e53935"/>
  <text x="1236" y="900" class="sub2">OUT 这一对</text>
  <text x="1236" y="936" class="sub2">（5 V）</text>
  <text x="840" y="1000" class="sub">XL4015（OMX 套件那块）</text>
  <text x="840" y="1038" class="sub2">挨着 IN+ / OUT+ 字样的螺丝是 +</text>
  <text x="840" y="1074" class="sub2">红灯（紫框里 R）常亮 = 在限流</text>
  <text x="840" y="1110" class="sub2">两个蓝旋钮（紫圈）先别动</text>

  <!-- 6. the 5 V plug and the single chain -->
  <rect x="1400" y="1170" width="60" height="50" rx="6" fill="#fafafa" stroke="#616161" stroke-width="3"/>
  <path d="M1450,1220 L1450,1240" class="link"/>
  <circle cx="1560" cy="1196" r="24" class="num"/><text x="1560" y="1206" class="numt">6</text>
  <text x="1530" y="1290" class="sub2">右腿：ID 5（原来插 OpenRB 的口）→ 1</text>
  {links}
  {chain}
  <path d="M830,1280 L210,1280 L210,1420" fill="none" stroke="#ff6f00" stroke-width="12" stroke-linejoin="round"/>
  <path d="M830,1460 L960,1460" fill="none" stroke="#ff6f00" stroke-width="12"/>
  <text x="230" y="1368" class="bridge">加一根舵机线：右脚踝 ID 1 空口 → 左脚踝 ID 6 空口</text>
  <text x="150" y="1546" class="sub2">左腿 ID 6 → 10</text>
  <text x="960" y="1546" class="sub2">脖子 ID 12 → 11 → 13 → 14 → 15（没装就先不接）</text>
  <text x="560" y="1594" class="bridge">ID 10 原来插 OpenRB 的那根线，另一头改插 ID 12</text>
  <text x="1700" y="1380" class="sub2">先只接右腿：扫描 ID 1–5，电压约 5.0 V</text>
  <text x="1700" y="1420" class="sub2">再接两根橙色线：15 个都在，</text>
  <text x="1700" y="1456" class="sub2">电压都在 4.7 V 以上</text>

  <style>
    .zone {{ font: 700 30px "PingFang SC","Hiragino Sans GB",sans-serif; fill: #5d4037; }}
    .lab {{ font: 700 34px "PingFang SC","Hiragino Sans GB",sans-serif; fill: #1b1b1b; }}
    .sub {{ font: 600 30px "PingFang SC","Hiragino Sans GB",sans-serif; fill: #263238; }}
    .sub2 {{ font: 500 26px "PingFang SC","Hiragino Sans GB",sans-serif; fill: #37474f; }}
    .warnt {{ font: 700 28px "PingFang SC","Hiragino Sans GB",sans-serif; fill: #c62828; }}
    .bridge {{ font: 700 26px "PingFang SC","Hiragino Sans GB",sans-serif; fill: #e65100; }}
    .pin {{ font: 700 26px "PingFang SC",sans-serif; fill: #212121; }}
    .pinr {{ font: 700 28px "PingFang SC",sans-serif; fill: #c62828; }}
    .sid {{ font: 700 26px sans-serif; fill: #ffffff; text-anchor: middle; }}
    .sname {{ font: 500 19px "PingFang SC",sans-serif; fill: #cfd8dc; text-anchor: middle; }}
    .num {{ fill: #1565c0; }}
    .numt {{ font: 700 28px sans-serif; fill: #fff; text-anchor: middle; }}
    .ring {{ fill: none; stroke: #ff6f00; stroke-width: 5; }}
    .ring2 {{ fill: none; stroke: #6a1b9a; stroke-width: 6; }}
    .hw {{ fill: none; stroke: #212121; stroke-width: 8; stroke-linejoin: round; }}
    .link {{ fill: none; stroke: #78909c; stroke-width: 8; }}
    .halo {{ paint-order: stroke; stroke: #ffffff; stroke-width: 7px; stroke-linejoin: round; }}
  </style>
</svg>'''

STEPS = [
    ('先不插鸭子的舵机，照 OMX-F 接好 12 V',
     '12 V 适配器插 SMPS2DXL 的圆口。SMPS2DXL 用你 OMX-F 上那根线插 OpenRB 一个边上的舵机口。'
     'OpenRB 跳线帽放 VIN(DXL) 那边，+5V 那根针空着。到这里和 OMX-F 一模一样，绿色端子不用。',
     'SMPS2DXL 红灯亮。'),
    ('XL4015 线：一头插 OpenRB，两对端子拧上 XL4015',
     '这根线一头插 OpenRB 另一个边上的舵机口。这一头分出来的一对端子拧进 XL4015 的 IN：带红圈的进挨着 “IN+” 字样的螺丝，另一根进 IN 的另一颗。'
     '另一头分出来的一对拧进 OUT：带红圈的进挨着 “OUT+” 的螺丝。先看一眼：红圈那根应该从它那头插头中间那根针出来。',
     '四个端子拉一下都不松；XL4015 上有灯亮。'),
    ('OpenRB 剩下两个口空着',
     'OpenRB 四个舵机口是并联的，现在全是 12 V。鸭子的任何舵机线都不能插 OpenRB，只能插在 XL4015 线的另一头后面。',
     'OpenRB 上只插了两根线：SMPS2DXL 来的那根和 XL4015 线。'),
    ('先只接右腿，确认 5 V',
     'XL4015 线空着的那头插右髋 ID 5 原来插 OpenRB 的那个口。MacBook 的 USB-C 插 OpenRB，扫描。'
     '这块 XL4015 就是机械臂上用的那块，10 月 5 日机械臂记录里它后面的 XL330（ID 14–16）读到 5.0–5.1 V。',
     '扫到 ID 1–5，电压读数都在 5.0 V 左右。不在 4.8–5.2 V 就停下，先别接其他舵机。'),
    ('接两根桥线，15 个串成一条',
     '断开 12 V。加一根舵机线：右脚踝 ID 1 空着的口 → 左脚踝 ID 6 空着的口。'
     'ID 10 原来插 OpenRB 的那根线，另一头改插脖子 ID 12 原来插 OpenRB 的口（脖子没装好就先不接这根）。再上电扫描。',
     '15 个（或腿上 10 个）都扫到，电压都在 4.7 V 以上。离 XL4015 越远的舵机电压会低一点，正常。'),
    ('标定、站立、走几步',
     '照常标定。站立和走路时看 XL4015 的红灯，偶尔再读一次舵机电压。',
     '红灯不常亮，最远的舵机电压不低于 4.5 V。不满足就停下告诉我，改成两路（第二块 XL4015 和第二根这种线挂在 OpenRB 另一个口，单独带脖子）。'),
]

steps_html = '\n'.join(
    f'<li class="step"><h3>{i}. {t}</h3><p>{body}</p><p class="ok"><b>这一步做完的样子：</b>{ok}</p></li>'
    for i, (t, body, ok) in enumerate(STEPS, 1))

HTML = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MicroDuck 12V 供电</title>
<style>
  :root {{ --bg:#ffffff; --fg:#1b1b1b; --muted:#455a64; --card:#f5f7f8; --line:#cfd8dc; --warn:#fff3e0; --warnb:#ffb74d; }}
  body {{ margin:0; background:var(--bg); color:var(--fg); font:18px/1.6 "PingFang SC","Hiragino Sans GB",system-ui,sans-serif; }}
  main {{ max-width:1500px; margin:0 auto; padding:16px; }}
  h1 {{ font-size:28px; margin:8px 0 4px; }}
  h2 {{ font-size:23px; margin:28px 0 8px; }}
  .lead {{ font-size:20px; margin:4px 0 12px; }}
  figure {{ margin:0; border:1px solid var(--line); border-radius:12px; overflow:auto; }}
  figure svg {{ display:block; width:100%; min-width:900px; height:auto; }}
  figcaption {{ font-size:15px; color:var(--muted); padding:8px 12px; }}
  ol {{ list-style:none; padding:0; margin:0; }}
  .step {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px 16px; margin:10px 0; }}
  .step h3 {{ margin:0 0 6px; font-size:21px; }}
  .step p {{ margin:4px 0; overflow-wrap:anywhere; }}
  .ok {{ color:#1b5e20; }}
  .warn {{ background:var(--warn); border:2px solid var(--warnb); border-radius:12px; padding:12px 16px; font-size:19px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px 16px; margin:10px 0; }}
  .src {{ color:var(--muted); font-size:14px; overflow-wrap:anywhere; }}
</style></head>
<body><main>
<h1>用 OMX 套件的 12 V 电源给鸭子供电（照 OMX-F 接法，一路带 15 个）</h1>
<p class="lead">12 V 适配器 → SMPS2DXL → OpenRB 舵机口（12 V）→ XL4015 线 → XL4015 降到 5 V → 15 个舵机串成一条链。不焊，不买。</p>
<p class="warn"><b>唯一的危险：</b>OpenRB 的四个舵机口现在全是 12 V。XL330 最高 6 V，鸭子的舵机线只能插在 XL4015 线后面，不能直接插 OpenRB。</p>
<figure>{SVG}
<figcaption>照片：SMPS2DXL、XL4015 和 XL4015 线是你自己拍的；12 V 适配器和 OpenRB-150 是 ROBOTIS 官方图。数字圈对应下面的步骤。可以横向滚动或放大看。</figcaption></figure>

<h2>一路够不够带 15 个：够</h2>
<div class="card">
<p><b>平均电流：</b>鸭子仿真走路平均约 2 A（5 V，约 10 W）。换到 12 V 这边不到 1 A，适配器绰绰有余。</p>
<p><b>XL4015：</b>最大 5 A。走路时 20 ms 左右的尖峰能到约 5 A，最多让红灯闪一下、电压短暂掉一点。</p>
<p><b>线和插头：</b>全部电流走 XL4015 线和右腿第一段舵机线，舵机小白头每针约 3 A，平均 2 A 在范围内。串成一条以后，离 XL4015 最远的舵机电压会低零点几伏，XL330 到 3.7 V 才停机。</p>
<p><b>什么时候改两路：</b>走路时红灯常亮，或者最远的舵机电压低于 4.5 V。那时第二块 XL4015 和第二根这种线挂在 OpenRB 另一个口，单独带脖子。</p>
</div>

<h2>步骤</h2>
<ol>{steps_html}</ol>

<h2>要准备的东西</h2>
<div class="card">
<p>OMX 套件里的：12 V 适配器、SMPS2DXL 和它接 OpenRB 的那根线、OpenRB-150、XL4015、XL4015 线。</p>
<p>舵机线一根，用来连两只脚踝（套件里的 180 mm 那种）。小一字螺丝刀。</p>
<p>Pi 照原计划用笔记本另一根 USB 线单独供电；三根 UART 杜邦线照 OpenRB 那一页接。</p>
</div>

<h2>依据</h2>
<p class="src">接法：Shawn 的 OMX-F（SMPS2DXL 接 OpenRB 舵机口，跳线帽放 VIN(DXL)，XL4015 线在三个 XL430 之后降压）；
ROBOTIS OMX-F 组装指南 XL4015 版（docs.robotis.com/docs/systems/omx/quick_start_guide/assembly_guide/?model=follower）。
OpenRB-150 e-Manual：舵机口合计 3,000 mA，VIN 最高 12.6 V。机械臂记录 omx-local/evidence/hardware-check.json（2026-10-05）。
鸭子的链：guide/content/steps.py。XL4015 红灯 = 恒流（限流）模式。核对日期 2026-10-12。</p>
</main></body></html>
'''

OUT.write_text(HTML, encoding='utf-8')
print(OUT, len(HTML))
