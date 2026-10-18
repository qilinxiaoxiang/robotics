"""Build BATTERY-WIRING.html: soldering and wiring the MicroDuck 2S battery backpack (DECISIONS.md D-010).

Plan this page follows: ../../build-pack-20260913/power/battery-backpack-20261015/README.md section 5 (wiring) and
section 6 (power-off order). Assembly into the printed backpack: guide chapter 11 (guide/content/steps.py, 'backpack').
Bench XL4015 #1 output: ../../CURRENT-STATE.json 'power' / 'servo_rail_v' (read, not copied from the README's 6.80 V).

Photos (read 2026-10-17; private reference use only, copyright their owners):
- img/tattu_2s650_xt30.jpg: genstattu.com product page "Tattu 650mAh 2S 75C 7.4V Lipo Battery | XT30 Plug", image
  products/2307/7075. The XT30 housing on the battery lead carries a moulded "+" on the red-wire side.
- img/swann39_side.jpg: Shawn's photo IMG_7023 (2026-10-17) of the RoboClub Swann 39 rocker switch, cropped.
- img/amass_mr30_pair.jpg: racedayquads.com "Amass MR30 Connector Male/Female Set", second product image
  (female MR30-F on the left, male on the right, black sleeves above).
- ../parts/photos/dfr1202_top.jpg, xt30_fit0586_rear.jpg, openrb_150_top.png and their marker fractions:
  ../parts/parts.json (dfr1202, xt30_fit0586, openrb_150).
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'BATTERY-WIRING.html'
PHOTOS = HERE.parent / 'parts' / 'photos'
STATE = HERE.parent.parent / 'CURRENT-STATE.json'


def uri(im: Image.Image, fmt: str = 'JPEG', quality: int = 85) -> str:
    buf = io.BytesIO()
    if fmt == 'JPEG':
        im.convert('RGB').save(buf, 'JPEG', quality=quality)
    else:
        im.save(buf, fmt, optimize=True)
    return f'data:image/{fmt.lower()};base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def photo(path: Path, crop=None, width=900, fmt='JPEG'):
    im = Image.open(path)
    im = im.convert('RGBA' if fmt == 'PNG' else 'RGB')
    if crop:
        im = im.crop(crop)
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    return im


def marked(im: Image.Image, marks, fmt='JPEG', alt=''):
    """marks: (x_frac, y_frac, number). Returns an inline SVG with the photo and numbered circles."""
    w, h = im.size
    r = max(14, round(w / 34))
    dots = ''.join(
        f'<circle cx="{x * w:.0f}" cy="{y * h:.0f}" r="{r}" class="mk"/>'
        f'<text x="{x * w:.0f}" y="{y * h + r * 0.36:.0f}" class="mkt" style="font-size:{r * 1.05:.0f}px">{n}</text>'
        for x, y, n in marks)
    return (f'<svg class="ph" viewBox="0 0 {w} {h}" role="img" aria-label="{alt}">'
            f'<image href="{uri(im, fmt)}" width="{w}" height="{h}"/>{dots}</svg>')


def in_crop(px, py, crop):
    x0, y0, x1, y1 = crop
    return (px - x0) / (x1 - x0), (py - y0) / (y1 - y0)


# ---------------------------------------------------------------- photos and markers
parts = {p['id']: p for p in json.loads((HERE.parent / 'parts' / 'parts.json').read_text())['parts']} \
    if isinstance(json.loads((HERE.parent / 'parts' / 'parts.json').read_text()), dict) else \
    {p['id']: p for p in json.loads((HERE.parent / 'parts' / 'parts.json').read_text())}


def frac(part, label):
    for c in parts[part].get('connectors', []) + parts[part].get('pins', []):
        if c.get('label') == label:
            return c['x'], c['y']
    raise KeyError((part, label))


T_CROP = (0, 230, 1001, 830)
tattu = photo(HERE / 'img' / 'tattu_2s650_xt30.jpg', T_CROP, 800)
SVG_TATTU = marked(tattu, [(*in_crop(700, 735, T_CROP), 1), (*in_crop(606, 672, T_CROP), 2),
                           (*in_crop(170, 455, T_CROP), 3)], alt='Tattu 2S 650 电池')

sw = photo(HERE / 'img' / 'swann39_side.jpg', None, 700)
SVG_SW = marked(sw, [(0.094, 0.598, 1), (0.094, 0.784, 2), (0.49, 0.08, 3), (0.86, 0.48, 4)], alt='Swann 39 开关')

M_CROP = (260, 300, 770, 720)
mr30 = photo(HERE / 'img' / 'amass_mr30_pair.jpg', M_CROP, 700)
SVG_MR30 = marked(mr30, [(*in_crop(400, 528, M_CROP), 1), (*in_crop(600, 505, M_CROP), 2),
                         (*in_crop(400, 655, M_CROP), 3), (*in_crop(355, 345, M_CROP), 4)], alt='MR30 公母')

xt = photo(PHOTOS / 'xt30_fit0586_rear.jpg', None, 900)
fc1, fc2, mc1, mc2 = frac('xt30_fit0586', 'F cup 1'), frac('xt30_fit0586', 'F cup 2'), \
    frac('xt30_fit0586', 'M cup 1'), frac('xt30_fit0586', 'M cup 2')
SVG_XT30 = marked(xt, [((fc1[0] + fc2[0]) / 2, (fc1[1] + fc2[1]) / 2 + 0.08, 1),
                       ((mc1[0] + mc2[0]) / 2, (mc1[1] + mc2[1]) / 2 + 0.09, 2),
                       (0.31, 0.62, 3)], alt='XT30 公母焊杯')

dfr = photo(PHOTOS / 'dfr1202_top.jpg', None, 700)
SVG_DFR = marked(dfr, [(*frac('dfr1202', 'VIN'), 1), (*frac('dfr1202', 'GND'), 2), (*frac('dfr1202', 'VOUT'), 3),
                       (0.93, 0.29, 4)], alt='DFR1202 焊盘')

orb = photo(PHOTOS / 'openrb_150_top.png', None, 600, 'PNG')
orb = orb.resize((orb.width * 2, orb.height * 2), Image.LANCZOS)
SVG_ORB = marked(orb, [(*frac('openrb_150', '-'), 1), (*frac('openrb_150', '+'), 2),
                       (*frac('openrb_150', 'JP1'), 3)], fmt='PNG', alt='OpenRB-150 J4')

state = json.loads(STATE.read_text())
facts = state.get('facts', state)
BENCH_V = facts['servo_rail_v'].get('no_load_v')
BENCH_DATE = facts['servo_rail_v'].get('verified_at')

# ---------------------------------------------------------------- overview diagram
OVERVIEW = '''
<svg class="dg" viewBox="0 0 1200 760" role="img" aria-label="电池背包接线总图">
 <defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
  <path d="M0,0 L10,5 L0,10 z" fill="#555"/></marker></defs>
 <rect x="10" y="10" width="640" height="470" rx="16" class="zb"/>
 <text x="30" y="46" class="zt">电池背包（可拆，整个换）</text>
 <rect x="680" y="10" width="510" height="470" rx="16" class="zr"/>
 <text x="700" y="46" class="zt">机器人身上（装一次，两个背包共用）</text>
 <rect x="10" y="510" width="640" height="240" rx="16" class="zg"/>
 <text x="30" y="546" class="zt">桌面背包（XL4015，留着在桌上用）</text>

 <rect x="40" y="80" width="150" height="80" rx="10" class="bx"/><text x="115" y="115" class="bt">电池</text>
 <text x="115" y="143" class="bs">Tattu 2S 650</text>
 <rect x="40" y="250" width="150" height="80" rx="10" class="bx"/><text x="115" y="285" class="bt">开关</text>
 <text x="115" y="313" class="bs">Swann 39</text>
 <path d="M115,160 L115,250" class="w"/><circle cx="115" cy="205" r="20" class="pl"/><text x="115" y="212" class="plt">1</text>
 <text x="148" y="212" class="bs st">S 开关线（自己焊）</text>

 <rect x="330" y="160" width="190" height="250" rx="10" class="bx"/><text x="425" y="195" class="bt">DFR1202</text>
 <text x="425" y="222" class="bs">6–24 V 进，5.0 V 出</text>
 <rect x="330" y="250" width="70" height="36" class="pd"/><text x="365" y="275" class="pdt">VIN</text>
 <rect x="330" y="300" width="70" height="36" class="pd"/><text x="365" y="325" class="pdt">GND</text>
 <rect x="330" y="350" width="70" height="36" class="pd"/><text x="365" y="375" class="pdt">VOUT</text>

 <path d="M190,290 L330,268" class="w"/><circle cx="240" cy="282" r="20" class="pl"/><text x="240" y="289" class="plt">2</text>
 <text x="262" y="250" class="ld">C 输入线</text>

 <path d="M520,268 L620,130 L760,130" class="w"/><circle cx="660" cy="130" r="20" class="pl"/><text x="660" y="137" class="plt">3</text>
 <text x="540" y="168" class="ld">D 舵机线</text>
 <path d="M520,370 L620,370 L620,360 L760,360" class="w5"/><circle cx="660" cy="360" r="20" class="pl5"/><text x="660" y="367" class="plt">4</text>
 <text x="540" y="400" class="ld">E 5 V 线</text>
 <text x="512" y="262" class="bs en">接 VIN + GND</text>
 <text x="512" y="364" class="bs en">接 VOUT + GND</text>

 <rect x="900" y="90" width="260" height="90" rx="10" class="bx"/><text x="1030" y="128" class="bt">OpenRB J4</text>
 <text x="1030" y="158" class="bs">右 +，左 −；JP1 在 VIN(DXL)</text>
 <path d="M760,130 L900,130" class="w"/><text x="790" y="115" class="ld">A 舵机输入线</text>
 <text x="1030" y="220" class="bs">→ 15 个舵机（6.6–8.4 V）</text>
 <rect x="900" y="300" width="260" height="110" rx="10" class="bx"/><text x="1030" y="340" class="bt">A7Z 排针</text>
 <text x="1030" y="370" class="bs">pin 2 = 5 V（红）</text><text x="1030" y="396" class="bs">pin 6 = GND（黑）</text>
 <path d="M760,360 L900,360" class="w5"/><text x="790" y="345" class="ld">B 5 V 线</text>

 <rect x="40" y="580" width="170" height="70" rx="10" class="bx"/><text x="125" y="612" class="bt">XL4015 #1</text>
 <text x="125" y="636" class="bs">舵机电压</text>
 <rect x="40" y="665" width="170" height="70" rx="10" class="bx"/><text x="125" y="697" class="bt">XL4015 #2</text>
 <text x="125" y="721" class="bs">5.0 V</text>
 <path d="M210,615 L700,615 L700,140 L760,140" class="wd"/><text x="260" y="604" class="ld">F 桌面舵机线（XT30 母）</text>
 <path d="M210,700 L730,700 L730,370 L760,370" class="wd"/><text x="260" y="690" class="ld">G 桌面 5 V 线（MR30 母）</text>
 <text x="840" y="560" class="bs st">虚线：换成桌面背包时，</text>
 <text x="840" y="590" class="bs st">F、G 插在同样的 3、4 号接头上</text>
 <circle cx="860" cy="650" r="20" class="pl"/><text x="860" y="657" class="plt">3</text>
 <text x="895" y="657" class="bs st">XT30：电池电压（黄线）</text>
 <circle cx="860" cy="710" r="20" class="pl5"/><text x="860" y="717" class="plt">4</text>
 <text x="895" y="717" class="bs st">MR30：只走 5 V（绿线）</text>
</svg>'''

# ---------------------------------------------------------------- page content
STEPS = [
    ('overview', '总览：8 根线、4 个插头'),
    ('parts', '零件和工具'),
    ('polarity', '1. 认公母、定正负'),
    ('cups', '2. 焊插头（XT30 / MR30 通用手法）'),
    ('switch', '3. 焊开关线 S'),
    ('dfr', '4. 焊 DFR1202 的三对线'),
    ('robot', '5. 机器人侧：A 舵机输入线、B 5 V 线'),
    ('bench', '6. 桌面背包：F、G'),
    ('meter', '7. 第一次插上之前量一遍'),
    ('next', '8. 装进背包、第一次用电池'),
]

PARTS_CARDS = [
    ('Tattu 2S 650mAh 75C 锂电池，XT30 插头', 'Amazon B0727XZFDW，2 块轮换', '57 × 31 × 12 mm，43 g，满电 8.4 V'),
    ('Swann 39 船型开关（rocker switch）', 'RoboClub 的黑开关，已有', 'SPST（单刀单掷），15 A 125 VAC；只有两个带孔焊片，没有线，要自己焊成开关线 S（第 3 步）。V1.20 背包底板的孔按它开：12.3 × 27.5 mm'),
    ('DFRobot DFR1202 降压板（buck converter，降压板）', 'DigiKey 1738-DFR1202-ND，已有', '6–24 V 进，5.0 V 出；只有焊盘，必须焊'),
    ('DFRobot FIT0586 XT30 公母一对', 'DigiKey 1738-1436-ND（订单 101587695），已有', '公头做机器人舵机输入 A，母头做桌面 F'),
    ('Amass XT30U 公母 10 对，带热缩管', 'Amazon B07CTRH86M；RoboClub 也有 XT30', '用 2 公（C、S 电池头）+ 2 母（D、S 输入头），其余备用'),
    ('Amass MR30 公母 10 对', 'Amazon B0747MW9RX', '用 1 公（B）+ 2 母（E、G）；三针只用两边两根'),
    ('20–22 AWG 多股硅胶线，红 + 黑', 'RoboClub 线架；问 "20 or 22 AWG stranded silicone wire, red and black"', '每色约 1.3 m。红黑并排的那种可以，撕开成两根用；不用单芯实心线，也不用 10 AWG 粗线（见第 3 步）'),
    ('3 mm 热缩管', 'RoboClub', '包开关的两个焊片'),
    ('Dupont 母端子 2 个 + 1P 外壳 2 个，压线钳', '问 RoboClub："Dupont female crimp terminals, 1-pin housings, crimp tool"', '只给 B 线接 A7Z 那头'),
]

TOOLS = ('烙铁（soldering iron，350–400 °C）、焊锡丝、助焊剂（flux）、剥线钳（wire stripper）、斜口钳、'
         '热缩管和热风枪（或打火机远远烤）、第三只手（helping hands，夹具）、万用表（multimeter）、油漆笔或记号笔。')

LEADS = [
    ('S', '开关线（在背包里）', '电池头 XT30 公（接头 1），输入头 XT30 母（接头 2）', '红 2 × 6 cm，黑 12 cm', '红线经过开关两个焊片，黑线直通'),
    ('A', '机器人舵机输入线', 'FIT0586 XT30 公', '约 150 mm', '裸线头 → OpenRB J4 螺丝（红 +，黑 −）'),
    ('B', '机器人 A7Z 5 V 线', 'MR30 公（两边两针）', '约 500 mm，沿现在 Pi 5 V 线的走线', 'Dupont 母端子 → A7Z pin 2（红）、pin 6（黑）'),
    ('C', '背包输入线', 'XT30 公（插开关的母头，接头 2）', '约 80 mm', 'DFR1202 VIN（红）、GND（黑）'),
    ('D', '背包舵机线', 'XT30 母（接头 3）', '约 100 mm', 'DFR1202 VIN（红）、GND（黑），和 C 共用焊盘'),
    ('E', '背包 5 V 线', 'MR30 母（接头 4）', '约 100 mm', 'DFR1202 VOUT（红）、GND（黑）'),
    ('F', '桌面舵机线', 'FIT0586 XT30 母', '够到接头 3 就行', 'XL4015 #1 OUT+ / OUT−（换掉现在直通 J4 的线）'),
    ('G', '桌面 5 V 线', 'MR30 母', '短', 'XL4015 #2 OUT+ / OUT−（换掉现在的 Dupont 跳线）'),
]


def lead_cards():
    return ''.join(
        f'<div class="lead"><div class="lid">{k}</div><div><b>{name}</b>'
        f'<div class="kv"><span>插头</span>{plug}</div><div class="kv"><span>长度</span>{ln}</div>'
        f'<div class="kv"><span>另一头</span>{other}</div></div></div>' for k, name, plug, ln, other in LEADS)


def part_cards():
    return ''.join(f'<div class="part"><b>{n}</b><div class="src">{s}</div><div>{d}</div></div>'
                   for n, s, d in PARTS_CARDS)


def legend(items):
    return '<ol class="lg">' + ''.join(f'<li><span class="n">{i}</span>{t}</li>' for i, t in items) + '</ol>'


SECTIONS = f'''
<section id="overview"><h2>总览：7 根线、4 个插头</h2>
<p class="goal">这一页做完：开关焊成开关线 S，电池背包的 C、D、E 三根线焊在 DFR1202 上，机器人身上换成 A、B 两根带插头的线，桌面背包换成 F、G。
之后换背包只要拔插 3、4 两个插头。</p>
{OVERVIEW}
<p>规则只有三条：</p>
<ul>
<li><b>电源那一侧装母头，机器人那一侧装公头。</b>母头（female）是带孔的那半，金属藏在里面，拔下来不会碰到短路。</li>
<li><b>红线 = +，黑线 = −。</b>全部用 20–22 AWG 多股硅胶线（stranded silicone wire），不分叉、不接 Y 线。</li>
<li><b>XT30 走电池电压，MR30 只走 5 V。</b>两种插头形状不同，插不错，电池电压到不了 A7Z。</li>
</ul>
<div class="leads">{lead_cards()}</div>
<p class="note">接头编号 1–4 和组装指南第 11 章一致：1 电池→开关，2 输入线→开关，3 舵机 XT30，4 A7Z 的 MR30。</p>
</section>

<section id="parts"><h2>零件和工具</h2>
<div class="parts">{part_cards()}</div>
<p><b>工具：</b>{TOOLS}</p>
<div class="grid2">
<figure>{SVG_TATTU}{legend([(1, '电池的 XT30 <b>母头</b>（带孔），接开关'), (2, '插头壳上压出来的小 “+”：红线那一侧'), (3, '白色平衡头（balance plug），只给充电器用，不接机器人')])}
<figcaption>Tattu 2S 650 电池（图：genstattu.com 商品页）</figcaption></figure>
<figure>{SVG_SW}{legend([(1, '焊片 1（带孔）'), (2, '焊片 2。两个焊片不分方向，红线一头一个'), (3, '卡扣（snap wing），两头各一个，穿过底板孔后弹开卡住'), (4, '船型按键，装进背包时朝下')])}
<figcaption>Swann 39 开关侧面（Shawn 2026-10-17 拍）。机身上印着 “39”、Swann 天鹅标、SINGAPORE。</figcaption></figure>
</div>
</section>

<section id="polarity"><h2>1. 认公母、定正负</h2>
<p class="goal">每个要焊的插头上都用油漆笔点好 “+” 那一侧，焊的时候红线进点了的那个焊杯。</p>
<div class="grid2">
<figure>{SVG_XT30}{legend([(1, '<b>母头</b> XT30U-F 的两个焊杯（背面开口，焊锡填在里面）'), (2, '<b>公头</b> XT30U-M 的两个焊杯'), (3, '母头壳上印着 “XT30U-F”')])}
<figcaption>XT30 公母（DFRobot FIT0586 商品图）。焊杯在插头背面，正面是插针/插孔。</figcaption></figure>
<figure>{SVG_MR30}{legend([(1, '<b>母头</b> MR30 的三个焊杯'), (2, '<b>公头</b> MR30 的三个焊杯'), (3, '母头正面：三个孔'), (4, '黑色护套：焊之前先套到线上')])}
<figcaption>MR30 公母（racedayquads.com 商品图）。三针只用两边，中间空着。</figcaption></figure>
</div>
<h3>XT30：用电池当基准</h3>
<ol class="do">
<li>拿电池的 XT30 母头当基准：它的红线那一侧就是 +，壳上也压了一个小 “+”。</li>
<li>每个新的 XT30 <b>公头</b>（A、C、S 电池头）：先插到电池上，在对着电池红线的那一侧壳上点一个漆点。拔下来，漆点那侧的焊杯焊红线。</li>
<li>每个新的 XT30 <b>母头</b>（D、F、S 输入头）：插到刚点好的公头上，在对着公头漆点的一侧也点一个，同样红线焊漆点那侧。</li>
</ol>
<h3>MR30：先定机器人那个公头，其他照它点</h3>
<ol class="do">
<li>拿 B 线要用的 MR30 公头，两边任选一边点漆点 = +。中间那根针不焊。</li>
<li>E、G 两个 MR30 母头：各插到这个公头上，对着漆点那一侧也点一个。</li>
<li>四个 MR30 半边都是同一规矩：红线 → 漆点那边，黑线 → 另一边，中间空。</li>
</ol>
<p class="warn">点完以后插上拔下各试一次：两个漆点必须在同一侧。点错了后面所有测量都会读成负数。</p>
</section>

<section id="cups"><h2>2. 焊插头（XT30 / MR30 通用手法）</h2>
<p class="goal">线头整根插在焊杯里、焊锡填满焊杯、外面包好热缩管；用力拉不动，两个焊杯之间没有锡连起来。</p>
<ol class="do">
<li><b>先套东西再焊。</b>XT30：每根线先套一段 10 mm 热缩管（包里带的），推远一点别被烙铁烤缩。MR30：先把黑色护套套在两根线上（开口朝插头）。焊完再套不上去。</li>
<li><b>剥线、上锡。</b>剥 5 mm，把铜丝拧紧，蘸一点助焊剂，用烙铁把线头镀上一层锡（tin，上锡）。</li>
<li><b>夹住插头，插上对头。</b>把要焊的插头插在一个对应的公/母头上再夹在第三只手上：塑料被烫软时针脚不会歪。焊杯开口朝上。</li>
<li><b>焊杯里先填锡。</b>烙铁贴住焊杯外侧，送锡进去，填到大约 2/3。</li>
<li><b>插线。</b>锡还是化的时候把镀好锡的线头插到底，烙铁拿开，线不动等 3 秒凝固。一个焊杯控制在 3–4 秒内，别一直烤。</li>
<li><b>检查。</b>焊点亮、包住线头、没有锡流到另一个焊杯。用力拉一下线。</li>
<li><b>收尾。</b>XT30：热缩管推到焊杯上，盖住整个金属，加热缩紧。MR30：把黑色护套推上去卡在插头上。</li>
</ol>
<p class="note">焊完后用万用表蜂鸣档（continuity，通断档）量同一个插头的两个针：不能响。响了就是两杯之间连锡了。</p>
</section>

<section id="switch"><h2>3. 焊开关线 S</h2>
<p class="goal">开关两边各有一个 XT30：电池那头是<b>公头</b>（接头 1，插电池的母头），另一头是<b>母头</b>（接头 2，C 线的公头插它）。红线经过开关，黑线从公头直通母头，不碰开关。</p>
<h3>用哪种线</h3>
<ul>
<li><b>用多股硅胶线，20 AWG 最好，22 AWG 也行。</b>舵机电流全部走这根线（平时约 1 A，起身瞬间约 8 A），线只有几厘米，20–22 AWG 足够。多股线软，机器人走路震动时不会在焊点根部折断。</li>
<li><b>红黑并排的那种可以。</b>看线皮上印的 AWG 数，18–22 都能用；用刀从中间那条缝划开，撕成红、黑两根。</li>
<li><b>不用单芯实心线（solid core）。</b>它硬，背包里弯不过来，震久了会在焊点处断。</li>
<li><b>不用 10 AWG 粗线。</b>XT30 的焊杯最多塞得进约 16 AWG，10 AWG 塞不进，也弯不进背包。</li>
</ul>
<h3>步骤</h3>
<ol class="do">
<li><b>剪线。</b>红线 2 段，每段 6 cm；黑线 1 段，12 cm。两头各剥 5 mm，拧紧，上锡。</li>
<li><b>先套热缩管。</b>两根红线各套一段约 15 mm 的 3 mm 热缩管，推到线中间，离焊片远一点。XT30 那头的 10 mm 热缩管也先套上（第 2 步的规矩）。</li>
<li><b>焊开关。</b>开关焊片朝上夹住。每根红线的一头穿过一个焊片的孔，往回弯一下勾住，烙铁贴住焊片 2–3 秒，送锡包住线和孔。只焊这一下就拿开：开关是塑料的，烤久了会软、按键会卡。</li>
<li><b>包好焊片。</b>等焊片凉了，把热缩管推上去盖住整个金属焊片和根部，加热缩紧。两个焊片离得近，必须各包各的。</li>
<li><b>焊 XT30 公头（电池头，接头 1）。</b>先按第 1 步点好漆点：焊片 1 那根红线进漆点焊杯，黑线的一头进另一个焊杯。</li>
<li><b>焊 XT30 母头（输入头，接头 2）。</b>焊片 2 那根红线进漆点焊杯，黑线的另一头进另一个焊杯。两个插头都按第 2 步收尾。</li>
<li><b>量。</b>万用表蜂鸣档：
  <div class="kv"><span>黑对黑</span>公头 − 对母头 −：一直响</div>
  <div class="kv"><span>红对红</span>公头 + 对母头 +：按键按一边响、另一边不响</div>
  <div class="kv"><span>红对黑</span>任何一个插头的 + 对 −：按键在哪边都不能响</div>
  响的那一边就是 “开”（ON）。装好以后在背包底面那一侧用记号笔点一下。</li>
</ol>
<p class="note">先焊好再装：装进背包时两个 XT30 先从底板的孔里往上穿（XT30 比 12.3 × 27.5 mm 的孔小），然后把开关推上去，直到两头卡扣都 “咔” 一声卡住（组装指南第 11 章第 1 步）。</p>
</section>

<section id="dfr"><h2>4. 焊 DFR1202 的三对线</h2>
<p class="goal">C、D 两对线一起焊在 VIN 和 GND 上，E 焊在 VOUT 和 GND 上。所有线从焊盘那条边往外伸出，不横穿板面。</p>
<figure class="narrow">{SVG_DFR}{legend([(1, '<b>VIN</b>：C 红 + D 红（两根）'), (2, '<b>GND</b>：C 黑 + D 黑 + E 黑（三根）'), (3, '<b>VOUT</b>：E 红（一根）'), (4, 'EN、AGND、PGOOD：都<b>不接</b>')])}
<figcaption>DFR1202 正面（DFRobot 商品图）。左边是带半孔的边缘焊盘（castellated pad，邮票孔）。</figcaption></figure>
<ol class="do">
<li><b>先焊插头那头。</b>按第 2 步把 C（XT30 公）、D（XT30 母）、E（MR30 母）各焊在一对线的一端。长度：C 约 80 mm，D、E 约 100 mm。另一端各剥 4 mm、上锡。</li>
<li><b>焊盘上锡。</b>板子平放夹住，在 VIN、GND、VOUT 三个焊盘上各镀一层锡。</li>
<li><b>VIN：</b>C 的红线和 D 的红线并排，线头拧在一起再上锡，平贴在 VIN 焊盘上，烙铁压上去让两边的锡化在一起。线朝板子外面伸。</li>
<li><b>GND：</b>三根黑线（C、D、E）。先把 C 和 D 的两根一起焊上，再把 E 的黑线贴在旁边补焊。三根要都被同一块锡包住。</li>
<li><b>VOUT：</b>E 的红线。</li>
<li><b>这两个焊点要焊实。</b>走路时舵机电流全部经过 VIN 和 GND 这两个焊点（约 1 A，起身瞬间约 8 A）。焊点要饱满、发亮，冷了以后每根线拉一下都不动。</li>
<li><b>量短路。</b>万用表蜂鸣档：VIN 对 GND、VOUT 对 GND 都不能一直响（输入电容可能让它“哔”一下就停，这正常）。VIN 对 VOUT 也不能响。</li>
</ol>
<p class="note">装进背包时，D、E 两个插头要先从里面穿出前板的扁窗口（第 11 章第 2 步），所以三根线都焊好再装。</p>
</section>

<section id="robot"><h2>5. 机器人侧：A 舵机输入线、B 5 V 线</h2>
<p class="goal">A、B 两根线做好、量过，OpenRB J4 上接的是带 XT30 公头的 A 线；A7Z 的 pin 2、pin 6 上接的是带 MR30 公头的 B 线。现在直接接 J4 和 Pi 5 V 的桌面线换下来。</p>
<figure class="slim">{SVG_ORB}{legend([(1, 'J4 <b>−</b> 螺丝（左）：A 黑线'), (2, 'J4 <b>+</b> 螺丝（右）：A 红线'), (3, 'JP1 跳线帽：保持在 VIN(DXL) 一侧，不动')])}
<figcaption>OpenRB-150（ROBOTIS 图）。丝印 “−” 在左螺丝旁，“+” 在右螺丝旁。</figcaption></figure>
<ol class="do">
<li><b>先断电。</b>A7Z 关机，拔掉桌面背包的 USB-C。</li>
<li><b>A 线：</b>FIT0586 的公头焊一对约 150 mm 的线（红线进漆点那杯，套热缩管）。另一头剥 6 mm，拧紧，<b>不上锡</b>（螺丝端子压镀锡的线会慢慢松）。</li>
<li>松开 J4 两个螺丝，取下桌面背包 XL4015 #1 原来的线。A 线先别拧进去，第 7 步量过电压再接：红线进右边 +，黑线进左边 −，拧紧，拉一下不掉。</li>
<li><b>B 线：</b>MR30 公头焊一对约 500 mm 的线（红线进漆点那边，中间空，先套护套）。沿现在 Pi 5 V 线的路线走。</li>
<li>A7Z 那头：剥 2–3 mm，压 Dupont 母端子（铜线压在前面那对爪里，线皮压在后面那对爪里），塞进 1P 外壳。拉一下不掉。</li>
<li>先别插上 A7Z，第 7 步量过电压再插。插的位置：红 → pin 2，黑 → pin 6（见 <a href="A7Z-PINS.html#power">A7Z 排针页的电源一节</a>）。</li>
</ol>
<p class="warn">B 线接上排针以后，A7Z 的 USB-C 口就<b>不能</b>再插电源：排针 5 V 和 USB-C 口是同一条线。</p>
<p class="note">为什么不用 Dupont 跳线：跳线是 26–28 AWG，2.2 A 峰值时 1 m 来回会掉 0.3–0.45 V；22 AWG 只掉约 0.12 V。A7Z 那头开机或满载时低于 4.85 V，就在 pin 4 和 pin 9 再加一对。</p>
</section>

<section id="bench"><h2>6. 桌面背包：F、G</h2>
<p class="goal">桌面背包也变成两个母头（XT30 + MR30），和电池背包插同样的 3、4 号接头。</p>
<ol class="do">
<li><b>F：</b>FIT0586 的母头焊一对线，另一头接 XL4015 #1 的 OUT+（红）、OUT−（黑）。就是刚才从 J4 拆下来的那个输出。</li>
<li><b>G：</b>MR30 母头焊一对短线，另一头接 XL4015 #2 的 OUT+（红）、OUT−（黑），替换原来去 Pi 的 Dupont 跳线。</li>
<li>XL4015 的旋钮（trimmer）都不要动。</li>
</ol>
<p class="note">XL4015 #1 现在的空载输出是 {BENCH_V} V（{BENCH_DATE} 测，<code>microduck-sim/CURRENT-STATE.json</code>）；电池方案 README 里写的 6.80 V 是旧设定。</p>
</section>

<section id="meter"><h2>7. 第一次插上之前量一遍</h2>
<p class="goal">四个母头和两根机器人线都量过，电压对、正负对，然后才插到 OpenRB 和 A7Z 上。全部用手和万用表做，不用电脑。</p>
<ol class="do">
<li><b>不接电池，量短路。</b>蜂鸣档：D 的 XT30 母头两个孔之间、E 的 MR30 母头两边孔之间都不能一直响。</li>
<li><b>开关关着，插电池（接头 1），插 C（接头 2）。</b>直流电压档（DC V）：D 母头上应该是 0 V。</li>
<li><b>开关打开。</b>红表笔插漆点那个孔，黑表笔另一个：
  <div class="kv"><span>D（XT30 母）</span>+7.0 到 +8.4 V（电池电压）</div>
  <div class="kv"><span>E（MR30 母）</span>+4.95 到 +5.05 V</div>
  读数是负的 = 漆点或焊线反了，先别往下做。</li>
<li><b>量机器人线。</b>B 线插到 E 上，Dupont 那头悬空（不插 A7Z）：红端子对黑端子 +4.95 到 +5.05 V。关开关，再把 B 插到 A7Z pin 2、6。</li>
<li>A 线插到 D 上，两个裸线头悬空、互相别碰：红对黑 +7.0 到 +8.4 V。关开关，再把 A 拧进 J4（红 +，黑 −）。</li>
<li><b>桌面背包。</b>插上 5991：F 母头上约 {BENCH_V} V，G 母头上 +4.95 到 +5.10 V，正负同上。</li>
</ol>
<p class="warn">关机顺序（README 第 6 节）：先在 A7Z 上关机（<code>sudo shutdown -h now</code>），等 10–15 秒，扶住机器人，再按开关。开关一断舵机就没力。</p>
</section>

<section id="next"><h2>8. 装进背包、第一次用电池</h2>
<p class="goal">接下来按组装指南第 11 章 “Battery backpack” 的 5 步装：开关线的两个插头从底板孔穿上去、开关卡进底板、DFR1202 卡到前板后面、换下转换盒、插电池、盖盖子。</p>
<ul>
<li>组装指南：<a href="MICRODUCK-BUILD.html">MICRODUCK-BUILD.html</a>，第 11 章。</li>
<li>15 个舵机的 Shutdown 寄存器已经在 2026-10-15 改成 52（guide/README.md），满电 8.4 V 不会掉力。</li>
<li>电池只在背包外、用平衡充电器、放在防火袋里充，不在机器人上充，充的时候有人看着（README 第 7 节）。</li>
<li>完整方案和电流计算：<code>microduck-sim/build-pack-20260913/power/battery-backpack-20261015/README.md</code>。</li>
</ul>
</section>
'''

NAV = ''.join(f'<a href="#{i}">{t}</a>' for i, t in STEPS)

HTML = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>电池背包接线</title>
<style>
:root{{--bg:#fafaf7;--card:#fff;--ink:#1f2328;--mut:#5b6470;--line:#e2e2dc;--acc:#e65100;--ok:#2e7d32;--warn:#b71c1c}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,"PingFang SC","Helvetica Neue",sans-serif}}
header{{padding:20px 16px 8px;max-width:980px;margin:0 auto}}
h1{{font-size:24px;margin:0 0 6px}} header p{{margin:0;color:var(--mut)}}
nav{{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:8px 16px;
display:flex;gap:8px;overflow-x:auto;max-width:100%}}
nav a{{flex:0 0 auto;font-size:14px;padding:4px 10px;border:1px solid var(--line);border-radius:14px;color:var(--ink);text-decoration:none;background:#fff}}
main{{max-width:980px;margin:0 auto;padding:0 16px 60px}}
section{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:18px 0;scroll-margin-top:56px}}
h2{{font-size:20px;margin:0 0 8px}} h3{{font-size:17px;margin:16px 0 4px}}
.goal{{background:#e8f5e9;border-left:4px solid var(--ok);padding:8px 12px;border-radius:6px}}
.goal::before{{content:"这一步做完：";font-weight:600}}
#overview .goal::before,#next .goal::before{{content:""}}
.warn{{background:#ffebee;border-left:4px solid var(--warn);padding:8px 12px;border-radius:6px}}
.note{{color:var(--mut);font-size:15px}}
code{{background:#f1f1ec;padding:1px 5px;border-radius:4px;font-size:14px;overflow-wrap:anywhere}}
a{{color:#0b57d0;overflow-wrap:anywhere}}
.dg,.ph{{width:100%;height:auto;display:block}}
.dg{{border:1px solid var(--line);border-radius:10px;background:#fff;margin:8px 0}}
.zb{{fill:#fff3e0;stroke:#ffb74d;stroke-width:2}} .zr{{fill:#e3f2fd;stroke:#90caf9;stroke-width:2}}
.zg{{fill:#f5f5f5;stroke:#bdbdbd;stroke-width:2}}
.zt{{font-size:22px;font-weight:700;fill:#333}} .bx{{fill:#fff;stroke:#555;stroke-width:2}}
.bt{{font-size:22px;font-weight:700;text-anchor:middle;fill:#222}} .bs{{font-size:17px;text-anchor:middle;fill:#555}} .st{{text-anchor:start}} .en{{text-anchor:end;font-size:15px}}
.ld{{font-size:18px;font-weight:600;fill:#8a3c00}}
.pd{{fill:#ffe082;stroke:#8d6e00}} .pdt{{font-size:17px;font-weight:700;text-anchor:middle;fill:#333}}
.w{{fill:none;stroke:#f9a825;stroke-width:9;stroke-linecap:round}} .w5{{fill:none;stroke:#43a047;stroke-width:9;stroke-linecap:round}}
.wd{{fill:none;stroke:#9e9e9e;stroke-width:6;stroke-dasharray:12 9}}
.pl{{fill:#f9a825;stroke:#fff;stroke-width:3}} .pl5{{fill:#43a047;stroke:#fff;stroke-width:3}}
.plt{{font-size:20px;font-weight:700;fill:#fff;text-anchor:middle}}
.mk{{fill:#d50000;stroke:#fff;stroke-width:3;fill-opacity:.92}} .mkt{{fill:#fff;font-weight:700;text-anchor:middle}}
figure{{margin:10px 0}} figcaption{{font-size:14px;color:var(--mut);margin-top:4px}}
.narrow{{max-width:560px}} .slim{{max-width:340px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.lg{{list-style:none;padding:0;margin:8px 0 0}} .lg li{{display:flex;gap:8px;align-items:flex-start;margin:4px 0}}
.lg .n{{flex:0 0 24px;height:24px;border-radius:12px;background:#d50000;color:#fff;font-weight:700;font-size:14px;
display:flex;align-items:center;justify-content:center;margin-top:2px}}
.do li{{margin:6px 0}}
.leads{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0}}
.lead{{display:flex;gap:10px;border:1px solid var(--line);border-radius:10px;padding:10px;background:#fff}}
.lid{{flex:0 0 34px;height:34px;border-radius:8px;background:#37474f;color:#fff;font-weight:700;font-size:18px;
display:flex;align-items:center;justify-content:center}}
.kv{{font-size:15px}} .kv span{{display:inline-block;min-width:4.5em;color:var(--mut);margin-right:6px}}
.parts{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:8px 0}}
.part{{border:1px solid var(--line);border-radius:10px;padding:10px;font-size:15px;background:#fff}}
.part .src{{color:var(--mut);font-size:14px;overflow-wrap:anywhere}}
@media (max-width:700px){{.grid2,.leads,.parts{{grid-template-columns:1fr}} h1{{font-size:21px}} section{{padding:14px}}}}
</style></head>
<body>
<header><h1>MicroDuck 电池背包：怎么焊、怎么接</h1>
<p>2S 锂电池 → 开关 → DFR1202；舵机直接吃电池电压，A7Z 吃 DFR1202 的 5 V（DECISIONS.md D-010）。</p></header>
<nav>{NAV}</nav>
<main>{SECTIONS}
<p class="note">来源：电池方案 README（2026-10-15）第 5–7 节；组装指南第 11 章；零件照片取自各商品页（DFRobot、ROBOTIS、genstattu.com、racedayquads.com），2026-10-17 读取；开关照片是 Shawn 拍的。</p>
</main></body></html>'''

OUT.write_text(HTML, encoding='utf-8')
print(OUT, len(HTML) // 1024, 'KB')
