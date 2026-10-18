#!/usr/bin/env python3
"""Build EXTENSION-REVIEW.html: the owner-facing review page of the neck-route + audio + Pi-mount extension.

Self-contained (images inlined as base64). Content is Chinese per the owner's page preference; numbers come from the
study JSON/README files in the sibling folders (neck-route/, audio/, pi-mount/, integrated/, pack-uart/).
Run: python3 build_page.py  (needs Pillow)
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from PIL import Image

from ask_section import ask_section
from power_section import CSS as POWER_CSS, power_section

HERE = Path(__file__).resolve().parent
EXT = HERE.parent
OUT = HERE / 'EXTENSION-REVIEW.html'


def img(path: Path, alt: str, caption: str, width: int = 1400) -> str:
    im = Image.open(path).convert('RGB')
    # trim the plain white margin around matplotlib figures (keep 12 px)
    from PIL import ImageChops
    box = ImageChops.difference(im, Image.new('RGB', im.size, (255, 255, 255))).point(lambda v: 255 if v > 12 else 0).getbbox()
    if box:
        m = 12
        im = im.crop((max(0, box[0]-m), max(0, box[1]-m), min(im.width, box[2]+m), min(im.height, box[3]+m)))
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=86, optimize=True)
    data = base64.b64encode(buf.getvalue()).decode()
    return (f'<figure><a href="data:image/jpeg;base64,{data}" target="_blank" rel="noopener">'
            f'<img src="data:image/jpeg;base64,{data}" alt="{alt}" loading="lazy"></a>'
            f'<figcaption>{caption}</figcaption></figure>')


SECTIONS = []

SECTIONS.append(('power', '供电：要不要换成 OMX 的 12 V', power_section()))
SECTIONS.append(('ask', '串口焊线、接线端子、泡棉', ask_section(img, EXT / 'pack-uart' / 'png')))

SECTIONS.append(('decided', '你已经定下的', f'''
<ul class="facts">
<li><b>降压板 DFR1202</b>：它只有焊盘，没有插座。在焊盘上焊一小段短引线，每根引线末端接插头。这段引线算降压板的一部分，换降压板时连引线一起换。其他线都插拔。</li>
<li><b>ID11 舵机外壳上的卡扣</b>：不加。脖子上剩 4 个卡扣。</li>
<li><b>OpenRB 串口</b>：后盖不开洞。拆掉 J12 上的座子，把两根线直接焊进去（这是唯一一处焊在板子上的线）。</li>
<li><b>V1.8</b>：保持不变，照常打印装配。下面所有改动都是拓展版，现在还是研究件，没有出打印文件。</li>
</ul>'''))

SECTIONS.append(('neck', '改动 1：线从脖子里走，头盖去掉后脑缺口', f'''
<div class="change"><p><span class="tag old">原来</span>8 根线（Pi 供电 2 根、IMU 4 根、串口 2 根）缠螺旋管，粗约 6.7 mm。从躯干后上方出来，在脖子后面外侧挂一个约 130 mm 的软弧，从头盖后缘的缺口和扎带罩进头。</p>
<p><span class="tag new">现在</span>不缠螺旋管，8 根线排成扁平的一片，沿脖子右侧（按鸭子自己的左右）上来，从头底下巴支架旁边一条缝进头。头盖后缘补平，没有缺口和扎带罩。</p></div>
{img(HERE / 'caps-rear.png', '头盖外观对比', '左：V1.8 头盖，后缘有出线缺口和扎带罩。右：拓展版头盖，后缘补平，头顶靠后多了扬声器的出声孔。')}
<h3>为什么现在走得通</h3>
<p>当初开后脑缺口，是因为线里有一根 USB 线，它的 USB-C 插头约 8×12 mm，穿不过脖子那条缝。后来改成细的串口线，就过得去了：</p>
<ul>
<li>最窄处在下巴支架和头部偏航连杆之间，静止时宽 4.4 到 4.55 mm。头往左歪 5° 以上，会开到 20 mm 以上。</li>
<li>8 根线平排着能过（这个宽度能并排放 18 根 1.7 mm 的线）。6.7 mm 的圆捆过不去，所以不缠螺旋管。</li>
<li>单针、1×4、1×5 的杜邦头侧着都能穿过去。</li>
</ul>
{img(EXT / 'neck-route/png/narrowest-sections.png', '最窄处剖面', '左图是这条路线最窄的地方。浅绿是能走线的空间，黑圈是能放下的最大圆（4.55 mm），红虚线圈是原来 6.7 mm 的线捆，放不下。')}
<h3>头里怎么走</h3>
<p>进头后先被下巴支架上的卡扣压住，然后在 Pi 背后往上走，从功放插头下方穿过，翻过 Pi 顶端。头盖上 Pi 右上那颗螺丝下面有第二个卡扣，过了它线从 Pi 前侧下来，在前下角散开，插到排针上。</p>
{img(EXT / 'integrated/png/integrated-side.png', '整合后的头部侧视', '侧视（从鸭子右边看，前方在右）。红色是 8 根线，橙色是扬声器和功放，蓝色是功放的杜邦线，绿色是 Pi，黑色是卡扣。')}
{img(EXT / 'integrated/png/integrated-top.png', '整合后的头部俯视', '俯视（前方在右）。左边带两个耳朵的椭圆是扬声器，中间是功放，右边竖着的绿条是 Pi。')}
<h3>线怎么固定</h3>
<ul>
<li><b>4 个小打印卡扣</b>，每个都是带一个孔的小片，压在已有螺丝的螺帽下面，钩住扁平的线。不开新孔、不加新柱子。卡扣下面那颗螺丝加长 1 mm，螺丝尖还在原来的位置：
<ul>
<li>躯干：S12-horn-025，M2×6 换成 M2×7；</li>
<li>俯仰支架：S11-horn-040，M2×6 换成 M2×7；</li>
<li>下巴支架（头里）：H-jaw_support-03，M2.5×6 换成 M2.5×8；</li>
<li>头盖上 Pi 右上螺丝 E-pi-04：M2×6 换成 M2×7。这一颗的长度是推断，试装时确认。</li>
</ul></li>
<li><b>偏航关节</b>：线压在 ID13 舵机外壳下沿，套一小段套管护住。这里留 35 到 40 mm 的余量，平铺成一道弧，不要垂着一个圈。</li>
<li><b>余量</b>：走里面只要 21 到 35 mm，原来外挂要 60 到 80 mm。下巴在所有能达到的姿态下离线都至少 6.1 mm，低头叼东西不受影响。</li>
</ul>
<h3>Pi 那头的插头</h3>
<p>现成的单针杜邦头可以直接用，一根根穿过去。如果你有空的多针外壳，可以合成三组，拆头时少拔几次：1×5 插 1、3、5、9 号针（7 号位空着），1×1 插 2 号针，1×3 插 6、8、10 号针。4 号针留给功放，所以偶数针那一排不能合成一个 1×5。</p>
<h3>装和拆</h3>
<ol>
<li>断电，用手把头往左歪 5 到 10°，缝就变宽了。</li>
<li>把线一根根穿过去，依次压进 4 个卡扣，最后插到 Pi 排针上。</li>
<li>拆头：拧开头盖，拔下 Pi 上的插头，把头盖卡扣上的线取下来，再把线往下抽。躯干和支架上的卡扣不用动。</li>
<li>只掀头盖不拆线的话，两个卡扣之间的线要多留约 25 mm（推断），否则先拔插头再掀。</li>
</ol>'''))

SECTIONS.append(('pi', '改动 2：Pi 立柱加固', f'''
<div class="change"><p><span class="tag old">原来</span>Pi 竖着装在两根从头顶垂下来的细杆上。杆中段截面只有约 2.0×3.2 mm，长约 30 mm。头盖是顶朝下打印的，这两根杆像细柱一样立在打印板上，层纹正好横切杆身，这是打印件最弱的方向。下排螺丝孔在杆的末端，撬一下支撑就可能断。估算约 2 到 3 N 的撬力就会断（推断）。</p>
<p><span class="tag new">现在</span>杆还在原位，每根加一片连到侧壁的筋，下排凸台的直角台阶改成 55° 斜面，杆根部和头顶连实。杆上需要支撑的面积几乎降到零，螺丝孔重新开。</p></div>
<ul>
<li><b>你断的那根</b>：正面看左边，就是鸭子自己的右边那根杆。按受力算，最可能断的是下排那个螺丝凸台（E-pi-01）。新设计两根杆都加固，所以方案不变。新头盖打出来之前，三颗螺丝先这样用：插杜邦头时用手指从背后托住 Pi，螺丝拧到贴紧就停。</li>
<li><b>强度</b>：横穿层纹方向的应力降到原来的约六分之一（每 1 N 推力从 9.1 MPa 降到 1.4 MPa），估计下排能承受约 15 到 30 N。这是梁的静力估算，没做实测。</li>
<li><b>螺丝和装法不变</b>：三颗 M2×6，+y 下排一颗 M2×4。E-pi-04 因为压了卡扣改成 M2×7。</li>
<li><b>离下巴支架</b>：靠下巴支架那一侧的筋削掉一点，静止和合盖下落时都留 1.05 mm 以上，和原来的 1.09 mm 差不多。</li>
<li><b>外形</b>：头盖外面一点不变，加的材料都在里面。</li>
</ul>
<p class="note"><b>你现在这个断了一根的头盖</b>：先用三颗螺丝没问题，Pi Zero 只有约 9 克。插杜邦头时用手指从背面托住板子；螺丝拧到贴紧就停；别在剩下的柱子附近撬。如果断的是 +y 下排那颗，看一下没固定的那个角别碰到下巴支架。</p>'''))

SECTIONS.append(('speaker', '改动 3：扬声器回到头里，头顶开出声孔', f'''
<div class="change"><p><span class="tag old">原来</span>V1.6 把扬声器夹在两片打印件（托架和压圈）之间，挂在头盖右侧两根顶柱上，没有出声孔，声音闷在头里。V1.8 把它整个撤掉了。这次复查发现，那个老位置在头部横滚 15 到 25° 时会撞到偏航连杆，不能沿用。</p>
<p><span class="tag new">现在</span>扬声器移到头盖内顶靠后，出声面朝上，正对头顶的一片小孔。</p></div>
<ul>
<li><b>固定</b>：头盖内顶打印一圈围框，扬声器放进去，出声面和头盖之间垫一圈 1 mm 闭孔泡棉（不带背胶），下面压一片 1.6 mm 的打印压板，用 2 颗 M2×6 自攻螺丝拧进头盖。拆的时候松两颗螺丝。不用胶。</li>
<li><b>为什么要泡棉压紧</b>：扬声器正面和背面发出的声音相位相反，如果在头里混到一起会互相抵消，声音变小。泡棉把正面封在出声孔这边，背面的声音留在头里。这是一般的声学道理，没做实测。</li>
<li><b>出声孔</b>：52 个 1.8 mm 圆孔，六边形排布，左右对称，开孔面积约是扬声器自带网罩的 1.2 倍。孔轴离打印方向只差 10°，打出来是圆孔，不用支撑。</li>
<li><b>接线</b>：扬声器只有焊盘，所以两根引线焊在扬声器自己的焊盘上（焊在扬声器上，不在电路板上），另一头拧进功放的接线端子。中间可以选加一个 2 针 JST-PH 插头，拆扬声器就不用螺丝刀了。</li>
</ul>
<p class="note">围框和扬声器之间只留 0.2 mm 的定位间隙。正式出图前最好先试打一小块围框，确认扬声器放得进去。</p>'''))

SECTIONS.append(('amp', '改动 4：功放 MAX98357A', f'''
<div class="change"><p><span class="tag old">原来</span>V1.6 时功放在头盖左侧两根顶柱上，上方只有 1.5 到 6.5 mm，竖着插的 14 mm 杜邦头根本放不下。V1.8 把它撤掉了。</p>
<p><span class="tag new">现在</span>功放平放在头顶下方正中，元件面朝上，用 2 颗 M2×6 自攻螺丝拧进头盖上的两根短柱。排针用弯针（90°），插头朝 Pi 的方向躺着，就放得下了。</p></div>
<ul>
<li><b>你要焊的</b>：7 针弯针排针，焊在功放板上（是接插件，符合你的规则）。2 针接线端子：2024 年 6 月以后出的板子已经预焊，如果你手上的没焊，也焊上。</li>
<li><b>Pi 到功放的 5 根杜邦线</b>（全插拔）：
<ul>
<li>Pi 4 号针（5 V）接 VIN；</li>
<li>Pi 34 号针（GND）接 GND，用 34 号是因为它的线走得更宽松，离摄像头更远；</li>
<li>Pi 12 号针接 BCLK；</li>
<li>Pi 35 号针接 LRC；</li>
<li>Pi 40 号针接 DIN。</li>
</ul></li>
<li><b>GAIN 和 SD 不接</b>：默认增益 9 dB，左右声道混成单声道。软件音量上限设在 −3 dBFS，满幅约 1 W 时停住，保护 1 W 的扬声器。不需要任何额外零件。</li>
<li><b>供电</b>：功放从 Pi 的 5 V 取电，脖子里不多走线。</li>
</ul>
<p class="note">功放上方最紧的地方是接线端子顶到头盖。Adafruit 官方图纸上端子高 8.5 mm，装好后还空约 2.2 mm（原来按 10 mm 估，只剩 0.71 mm）。端子的螺丝朝上，装进头以后够不着，所以先把扬声器线拧好再装功放。</p>'''))

SECTIONS.append(('pack', '改动 5：OpenRB 串口改焊 J12', '''
<div class="change"><p><span class="tag old">原来</span>串口杜邦线插 OpenRB 侧边的 D13、D14。装进背包后这两个孔被降压板挡住，插不进去。</p>
<p><span class="tag new">现在</span>你定的：拆掉 J12 上的座子，两根线直接焊进 J12 的 Rx、Tx，OpenRB 换 J12 版固件。背包和后盖都不改。图和步骤见上面"串口焊线"那一节。</p></div>'''))

SECTIONS.append(('count', '比 V1.8 多出来的东西', '''
<ul>
<li><b>重打</b>：头盖（去缺口、加扬声器围框和出声孔、加功放短柱、加固 Pi 立柱）。</li>
<li><b>新打印件 5 个</b>：扬声器压板 1 个，线卡扣 4 个。</li>
<li><b>新螺丝</b>：4 颗 M2×6 自攻（扬声器 2、功放 2）。</li>
<li><b>加长螺丝 4 颗</b>：两颗 M2×7、一颗 M2.5×8、E-pi-04 一颗 M2×7，都是设计里已有的规格。</li>
<li><b>小料</b>：1 mm 闭孔泡棉一小片，偏航关节处一小段套管。可选 2 针 JST-PH 插头一对。</li>
<li><b>串口</b>：两根杜邦线剪掉公头焊进 J12；OpenRB 换 J12 版固件。背包不改。</li>
<li><b>不再需要</b>：螺旋管，头盖后缘的扎带。</li>
</ul>'''))

SECTIONS.append(('open', '还没定、要你做的', '''
<ul>
<li><b>装扬声器时备好</b>：1 mm 厚泡棉双面胶一小块（你去找）。</li>
<li><b>试打</b>：扬声器围框一小块，卡扣一个（看钩子大小合不合适）。</li>
<li><b>供电</b>：手上有没有圆口母座转接线端子（见"供电"一节的图）？</li>
<li><b>下巴碰脖子</b>：你看到的和模型一致。头朝正前方时，下巴张满 40° 也不碰；头一转，下巴就会碰到头部俯仰支架。转 60° 左右最紧，张到 26.25° 就碰。训练好的策略最多只张 18.33°，所以把下巴限制在 25° 以内，转到哪个角度都不会碰，叼东西也不受影响。不用改打印件。做法：Pi 控制程序里把 ID15 的命令限制在 25°；再在机器人上实测一次（头转到约 60°，手掰下巴到刚碰支架，读位置，往回留 2° 设成 ID15 的位置上限）。另外，模拟里放球时头会往上仰到 71° 到 85°，这时下巴张着会撞 ID12 和外壳。所以下巴张开时，头的俯仰角要压在 65° 以下，放球动作要按这个限制重新验收。</li>
</ul>'''))


CSS = '''
:root{--bg:#f6f7f5;--card:#fff;--ink:#1d2a26;--muted:#5b6b66;--line:#dfe5e2;--accent:#c96a12;--old:#8a6d3b;--oldbg:#fbf3e4;--new:#1f7a52;--newbg:#e7f5ee;--note:#fff8e6;--noteline:#e9c46a}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Noto Sans SC",sans-serif;overflow-wrap:anywhere}
header{background:#fff;border-bottom:1px solid var(--line);padding:20px 16px}
header h1{margin:0 auto;max-width:860px;font-size:22px;line-height:1.35}
header p{margin:8px auto 0;max-width:860px;color:var(--muted);font-size:15px}
nav{position:sticky;top:0;z-index:2;background:rgba(246,247,245,.96);border-bottom:1px solid var(--line);padding:8px 16px;overflow-x:auto;white-space:nowrap}
nav a{display:inline-block;margin-right:14px;color:var(--accent);text-decoration:none;font-size:14px}
main{max-width:860px;margin:0 auto;padding:12px 16px 48px}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0}
h2{font-size:19px;margin:0 0 10px}
h3{font-size:16px;margin:18px 0 6px}
ul,ol{padding-left:22px;margin:6px 0}
li{margin:4px 0}
.change p{margin:8px 0;padding:10px 12px;border-radius:8px}
.change p:first-child{background:var(--oldbg)}
.change p:last-child{background:var(--newbg)}
.change p:only-child{background:var(--oldbg)}
.tag{display:inline-block;font-size:13px;font-weight:600;border-radius:4px;padding:0 6px;margin-right:8px}
.tag.old{color:#fff;background:var(--old)}
.tag.new{color:#fff;background:var(--new)}
.note,.pending{background:var(--note);border-left:4px solid var(--noteline);padding:10px 12px;border-radius:6px}
figure{margin:14px 0}
figure img{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:#fff}
figcaption{font-size:14px;color:var(--muted);margin-top:6px}
.facts li{margin:8px 0}
footer{max-width:860px;margin:0 auto;padding:0 16px 32px;color:var(--muted);font-size:13px}
''' + POWER_CSS


def build() -> None:
    nav = ''.join(f'<a href="#{sid}">{title.split("：")[0]}</a>' for sid, title, _ in SECTIONS)
    body = ''.join(f'<section id="{sid}"><h2>{title}</h2>{html}</section>' for sid, title, html in SECTIONS)
    page = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MicroDuck 拓展版评审</title><style>{CSS}</style></head><body>
<header><h1>MicroDuck 拓展版：线从脖子走，扬声器回到头里，Pi 立柱加固</h1>
<p>2026-10-12。研究阶段：几何检查已通过，还没有出打印文件。V1.8 保持不变。请看每一节的"原来 → 现在"，确认后再出正式打印件。</p></header>
<nav>{nav}</nav><main>{body}</main>
<footer>点图可以看大图。坐标和数字来自 guide/extension-20261012-neck-audio/ 下各研究的脚本输出；标"推断"的是估算，没有实测。</footer>
</body></html>'''
    OUT.write_text(page, encoding='utf-8')
    print(OUT, OUT.stat().st_size)


if __name__ == '__main__':
    build()
