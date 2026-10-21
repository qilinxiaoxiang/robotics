"""Build ../A7Z-COOLING.html: open the MicroDuck head, stick a heatsink on the A733, solder a capacitor across the
5 V lead, close up and check (python3 + Pillow, no network). Shares the page parts, marked photos and CAD renders of
build_a7z_pages.py. Sources and the verification date: README.md ("A7Z-COOLING").
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import build_a7z_pages as B
import photos as P

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'A7Z-COOLING.html'

# A733 package centre and the SK hynix LPDDR4 chip centre on a7z-top.png (landscape, header along the top edge),
# read on the photo like the points in photos.py (the design-file s/d boxes land 4 to 5 mm off on this photo);
# checked on shots/check_cooling.png.
SOC = (1148, 323)
RAM = (1332, 283)

LAND_SOC = [('芯', SOC, 0, 620), ('M', RAM, 95, 930), ('A', P.IPEX_TOP, 22, 150)]
PX_MM = P.PITCH / 2.54 * P.SCALE   # portrait canvas pixels per mm (header pitch 2.54 mm)


def sink_figure() -> Image.Image:
    """The landmark photo with the 15 x 15 mm heatsink drawn on the A733. Its fins run perpendicular to the header row:
    the board hangs header-down in the head (bringup/a7z CAD side view; checks.json frame `ed`, up from the header edge,
    is (0.17, 0, 0.98)), so these fins stand vertical and the warm air rises along the slots (cooling study 2026-10-21)."""
    im = P.top_figure([(2, '#e53935'), (6, '#1d1d1f')], LAND_SOC).convert('RGBA')
    cx, cy = P.to_portrait(SOC)
    h = 7.5 * PX_MM
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rectangle([cx - h, cy - h, cx + h, cy + h], fill=(184, 115, 51, 150), outline=(255, 255, 255, 255), width=5)
    for k in range(7):
        y = cy - h + (k + 0.5) * 2 * h / 7
        d.rectangle([cx - h + 8, y - 0.5 * PX_MM, cx + h - 8, y + 0.5 * PX_MM], fill=(150, 85, 30, 245))
    ay = cy - h - 44   # "up in the closed head" = away from the header, toward the USB-C edge (left on this photo)
    d.rounded_rectangle([cx - h - 10, ay - 32, cx + h + 10, ay + 32], radius=12, fill=(255, 255, 255, 240))
    d.line([(cx - h + 40, ay), (cx - h + 84, ay)], fill='#0d47a1', width=9)
    d.polygon([(cx - h + 4, ay), (cx - h + 44, ay - 20), (cx - h + 44, ay + 20)], fill='#0d47a1')
    d.text((cx - h + 98, ay - 1), '合盖后朝上', font=ImageFont.truetype(P.FONT, 42), fill='#0d47a1', anchor='lm')
    return Image.alpha_composite(im, lay).convert('RGB')


FIG_SINK = sink_figure()
FIG_SINK.save(HERE / 'shots' / 'check_cooling.png')
IMG_SOC = B.uri(FIG_SINK, B.TOP_W)

LEGEND_SOC = [
    ('land', '芯', 'A733 主芯片：板上最大的黑方块（15 × 15 mm），中间一块亮的。图上的铜色方块就是散热片贴好的样子：盖满这块黑方块，<b>鳍片（深色横条）和右边那一排排针垂直</b>。'),
    ('land', 'M', 'SK hynix 内存（长方形黑块）：紧挨着主芯片。散热片<b>不要</b>压到它。'),
    ('pin', '2', '2 号针：5 V 线的红插头。'),
    ('pin', '6', '6 号针：5 V 线的黑插头（地）。电容焊在这两根线上。'),
    ('land', 'A', '天线插座那头 = 1、2 号针那头。'),
]

LEGEND_SIDE = [
    ('pin', '1', '天线，贴在头盖顶的内面'),
    ('pin', '2', '天线的线头'),
    ('pin', '3', 'A7Z 的天线插座'),
    ('pin', '4', '排针上的杜邦线（从躯干上来的 8 根）'),
]

CAP_SVG = '''
<svg viewBox="0 0 680 300" width="100%" role="img" aria-label="电容接法：正极接红线（5 V），负极接黑线（GND）">
  <style>text{font:21px "PingFang SC","Hiragino Sans GB",system-ui,sans-serif;fill:#1b1b1b}.s{font-size:18px;fill:#4a5a63}</style>
  <rect x="0" y="0" width="680" height="300" fill="#ffffff"/>
  <rect x="12" y="92" width="120" height="116" rx="8" fill="#f5f7f8" stroke="#cfd8dc"/>
  <text x="72" y="122" text-anchor="middle">降压板 #2</text><text x="72" y="146" text-anchor="middle" class="s">XL4015</text>
  <text x="72" y="168" text-anchor="middle" class="s">OUT+ / OUT−</text>
  <rect x="548" y="92" width="120" height="116" rx="8" fill="#f5f7f8" stroke="#cfd8dc"/>
  <text x="608" y="122" text-anchor="middle">A7Z 排针</text><text x="608" y="146" text-anchor="middle" class="s">2 号针 = 5 V</text>
  <text x="608" y="168" text-anchor="middle" class="s">6 号针 = GND</text>
  <line x1="132" y1="118" x2="548" y2="118" stroke="#e53935" stroke-width="6"/>
  <line x1="132" y1="184" x2="548" y2="184" stroke="#1d1d1f" stroke-width="6"/>
  <text x="200" y="106" class="s">红线 5 V（插 2 号针）</text>
  <text x="200" y="212" class="s">黑线 GND（插 6 号针）</text>
  <!-- capacitor across the two wires, 2 cm from the plugs -->
  <line x1="470" y1="118" x2="470" y2="138" stroke="#e53935" stroke-width="4"/>
  <line x1="470" y1="164" x2="470" y2="184" stroke="#1d1d1f" stroke-width="4"/>
  <line x1="440" y1="138" x2="500" y2="138" stroke="#1b1b1b" stroke-width="5"/>
  <path d="M440 164 Q470 150 500 164" fill="none" stroke="#1b1b1b" stroke-width="5"/>
  <circle cx="470" cy="118" r="7" fill="#e53935"/><circle cx="470" cy="184" r="7" fill="#1d1d1f"/>
  <text x="452" y="40" class="s">焊点：剪开线头</text><text x="452" y="62" class="s">离插头约 2 cm</text>
  <line x1="470" y1="70" x2="470" y2="108" stroke="#0d47a1" stroke-width="2"/>
  <text x="420" y="149" text-anchor="end">＋ 长脚 → 红线</text>
  <text x="420" y="172" text-anchor="end">－ 白条那边、短脚 → 黑线</text>
  <text x="12" y="262">电解电容 470 µF，16 V（10 V 也行）。有正负极，接反会鼓包。</text>
  <text x="12" y="286" class="s">两个焊点各套一段热缩管，不能互相碰到。</text>
</svg>'''

S_PARTS = B.step('parts', '第 1 步 · 5 分钟', '认零件和工具', '桌上摆齐下面的东西，认得电容的正负极。', f'''
<div class="card"><p><b>散热片（heatsink，带鳍片的小铜块）：</b>GeeekPi 纯铜 15 × 15 × 5 mm，8 片装，自带导热胶带（Amazon B0C7Z27Q3R，已在购物车，$12.99）。
RoboClub 零件柜里的树莓派散热片套件也行：要 15 × 15 mm 左右、高不超过 8 mm、背面有导热胶带的那种。</p>
<p>原理：芯片顶面只有 15 mm 见方，热散不出去；铜块贴上去先把热吸走，再从大得多的表面散到周围空气。头壳不通风，所以它主要是“缓冲”，让温度爬得慢，不是把热带出头壳。</p></div>
<div class="card"><p><b>电解电容（electrolytic capacitor，圆柱形，两条腿，有正负极）：</b>470 µF、16 V（10 V 也行，1000 µF 也行）。
例子：Panasonic EEU-FR1C471（470 µF 16 V，8 × 11.5 mm，脚距 3.5 mm；RoboClub 零件柜先找，没有的话 DigiKey 搜这个型号）。</p>
<p>原理：它像一个小水缸，装在 A7Z 这头的 5 V 线上；CPU 电流突然上一个台阶的那几毫秒，先由它顶住，线上的压降来不及把板子拉掉电。</p>
<p><b>认正负极：</b>两条腿里<b>长的是正极</b>（＋）；外壳上有一条<b>白色竖条纹</b>的那一侧是负极（−），负极腿短。接反会发热、鼓包。</p></div>
<div class="card"><p><b>工具：</b>十字小螺丝刀（头盖的三颗 M2.6 螺丝）；烙铁、焊锡、剥线钳或小刀、剪线钳；两小段热缩管（套得进 24 AWG 线的，约 2 mm 内径）或电工胶带；酒精和不掉毛的布（擦芯片）。可选：万用表（第 6 步）。</p></div>
''')

S_OFF = B.step('off', '第 2 步 · 1 分钟', '关机，断电', 'A7Z 已经关机，电源线已拔，ssh 连不上。', f'''
<ol class="acts">
<li>{B.tag('mac')}用 Microduck 应用的关机按钮（它先停掉正在跑的程序，再关机）；或者在终端里：</li>
</ol>
{B.cmd('mac', "ssh a7z 'sudo -n systemctl poweroff'", '（没有输出，几秒后 ssh 断开）')}
<ol class="acts" start="2">
<li>{B.tag('hand')}等 20 秒，再拔掉背后 5991 取电板上的 USB-C 线（或者关掉台式电源）。舵机和 A7Z 一起断电。</li>
<li>{B.tag('mac')}确认真的关了：</li>
</ol>
{B.cmd('mac', 'ssh -o ConnectTimeout=4 a7z true', 'ssh: connect to host ... Operation timed out')}
<div class="warn">头壳里的板子、线和舵机都在，<b>没断电不要拧螺丝</b>。杜邦插头碰到别的针会把 5 V 送进信号线。</div>
''')

S_OPEN = B.step('open', '第 3 步 · 5 分钟', '开头盖', '头盖掀起来了，A7Z 的元件面（芯片那一面）朝着你，8 根线还插着。', f'''
<div class="card"><p><b>先说清楚哪些东西跟着盖子走：</b>A7Z 板子（四颗螺丝在盖子内面的导轨上）、喇叭和功放（盖子顶的环和两根柱子）、天线（贴在盖子顶内面）和它那根 36 mm 的细线，<b>全都装在头盖上</b>。
掀盖子的时候它们整体一起起来，天线、喇叭都不用拆。芯片面朝脸那边，盖子一掀就露出来。</p></div>
{B.figure(B.cad('cad_side'), '头盖从侧面看：板子斜挂在盖子下面，元件面朝脸', '头盖从侧面看（CAD）。板子挂在盖子内面的导轨上，<b>元件面朝左（脸那边）</b>，排针在下。掀起盖子就能看到芯片。', LEGEND_SIDE)}
<ol class="acts">
<li>{B.tag('hand')}找头盖和下头壳接缝处的<b>三颗 ROBOTIS M2.6 × 6 螺丝</b>（下头壳有三个带孔的小耳朵，螺丝从下往上拧进盖子）。三颗都拧出来，放进小碟子。</li>
<li>{B.tag('hand')}<b>慢慢</b>把头盖抬起 3 到 4 cm。有两样东西连着下面：从躯干上来的 8 根杜邦线（IMU 4 根、串口 2 根、5 V 2 根，插在排针上），和<b>摄像头排线</b>（从脸上的摄像头板到 A7Z 背面的接口）。线够长就让它们插着。</li>
<li>{B.tag('hand')}摄像头排线被拉紧了就停：掰开摄像头板那头接口的小黑扣，把排线抽出来（记住金手指朝哪面），合盖时再插回去。杜邦线不够长就拔 5 V 的红（2 号针）和黑（6 号针）两根，第 5 步反正要在它们上面焊，插回去的位置见 <a href="A7Z-PINS.html#power">A7Z 插线页的 5 V 一节</a>。</li>
<li>{B.tag('hand')}把盖子翻过来，用一本书垫着放平，让板子的元件面朝上。现在应该看得到：最大的黑方块（主芯片）、挨着它的长方形内存、两个 USB-C 口、排针和上面的线。</li>
</ol>
<div class="warn">别去撕天线、别拔天线那个金色的小插头（IPEX）：它们本来就在盖子上，这一步用不着动。拔了再插容易把插座弄坏。</div>
''')

S_SINK = B.step('sink', '第 4 步 · 3 分钟', '贴散热片', '铜块稳稳贴在主芯片的黑方块上，鳍片和排针那一排垂直，没有压到内存，用手推不动。', f'''
{B.figure(IMG_SOC, 'A7Z 正面：散热片贴在主芯片上，鳍片和排针那一排垂直；内存和 2、6 号针的位置', 'A7Z 正面（Radxa 官方照片，竖放，天线插座那头在上），铜色方块是画上去的散热片。“芯”是主芯片，“M”是内存。合上盖子后板子是排针朝下挂着的，所以图上左边（USB-C 那条边）在头里朝上，横着的鳍片在头里就是竖的。', LEGEND_SOC)}
<ol class="acts">
<li>{B.tag('hand')}布蘸一点酒精，擦主芯片顶面（那块黑方块，中间有一小块亮的）。等 30 秒干透，不要再用手摸。</li>
<li>{B.tag('hand')}撕掉铜块背面导热胶带的保护膜。胶带只有一面露出来，露出来的那面朝芯片。</li>
<li>{B.tag('hand')}先看鳍片的方向：<b>鳍片要和排针那一排垂直</b>，也就是鳍片之间的槽从排针那条长边指向对面 USB-C 那条长边（上图的深色横条）。合盖后板子排针朝下挂着，这样槽就是上下方向的，热空气顺着槽往上走；鳍片横着的话，槽是水平的，热气会闷在鳍片中间。如果你的散热片是一根根小柱子（针状），方向就无所谓。</li>
<li>{B.tag('hand')}铜块按这个方向对准黑方块放上去：铜块 15 × 15 mm，黑方块也是 15 × 15 mm，四边对齐。<b>不要</b>压到旁边的内存，也不要盖到右边那几个小元件（晶振）。</li>
<li>{B.tag('hand')}用拇指压 10 秒。然后轻推一下：推不动就贴好了。</li>
</ol>
<div class="card"><p><b>高度够不够：</b>芯片顶面到前面摄像头板（背面的小元件）的空隙是 12.8 mm（头部 CAD 算出来的），铜块 5 mm 高、再加一层导热胶带，合盖后还剩约 7.5 mm。所以换别的散热片时，高度不要超过 8 mm。合盖时（第 7 步）再从缝里看一眼它没碰到摄像头板。</p>
<p><b>为什么只贴主芯片：</b>日志里发热的是 CPU 所在的这颗 A733；内存和电源芯片（AXP318，板子下方印着这个字）不热，不用贴。铜是导电的，所以铜块只能坐在黑方块上，不能搭到任何小元件。</p></div>
''')

S_CAP = B.step('cap', '第 5 步 · 先不做（2026-10-20 决定）', '焊电容', '电容焊在 5 V 红线和黑线上，离插头约 2 cm，正极在红线上，两个焊点各自套了热缩管。', f'''
<div class="warn"><b>这一步先跳过。</b>2026-10-20 决定先不焊电容：先看散热片和关大核能不能解决掉电，还掉电再回来做。下面留着备用。</div>
<div class="card">{CAP_SVG}</div>
<p>接法就是上面这张图：电容横跨在红线（5 V）和黑线（GND）之间，离 A7Z 的插头越近越好，因为它要顶住的是插头这一端的电压。焊在降压板那头没用，降压板自己已经有电容。</p>
<ol class="acts">
<li>{B.tag('hand')}先确认第 2 步断了电。把 2 号针的红插头和 6 号针的黑插头拔下来（记住：红 2、黑 6）。</li>
<li>{B.tag('hand')}在<b>离插头 2 cm</b> 的地方把红线剪断，两个断头各剥掉 4 mm 皮。先把一小段热缩管套到线上，推远一点。</li>
<li>{B.tag('hand')}把电容的<b>长脚（＋）</b>和红线的两个断头拧在一起，焊上。等焊点凉了，把热缩管推过来盖住焊点，用烙铁侧面或打火机烤缩。</li>
<li>{B.tag('hand')}黑线同样做一遍：离插头 2 cm 剪断，剥皮，套热缩管，把电容的<b>短脚（−，白条那边）</b>和黑线两个断头拧在一起焊上，热缩。</li>
<li>{B.tag('hand')}电容本体顺着线放，用一小圈电工胶带把它和两根线缠在一起，免得在头壳里晃。两个焊点不能互相碰到。</li>
<li>{B.tag('hand')}红插头插回 2 号针，黑插头插回 6 号针（都在外排，天线插座那头数第 1 和第 3 根）。</li>
</ol>
<div class="warn"><b>正负极再对一次：</b>长脚、没有白条的那边 → 红线；短脚、白条那边 → 黑线。接反了通电会发热鼓包。</div>
<div class="card"><p><b>记录：</b>这是机器人线束上新增的一个焊接项目（原先只有 J12 串口、功放线和触摸板，D-013）。你 2026-10-20 在聊天里定的；焊完后我写进 DECISIONS.md。</p></div>
''')

S_METER = B.step('meter', '第 6 步 · 可选 · 3 分钟', '开着盖子量一次 5 V', '满载 20 秒期间万用表读到的最低电压记下来了，A7Z 没有重启。', f'''
<p>头开着的时候，电容的两条腿就是 A7Z 这头的 5 V 和地，比排针好夹。这一步把 A7Z 满载跑 20 秒（只烧 CPU，不动舵机），同时看电压最低掉到多少。</p>
<ol class="acts">
<li>{B.tag('hand')}盖子还开着、线都插好。插回 USB-C 电源线，等 60 秒开机。</li>
<li>{B.tag('hand')}万用表拨到直流电压挡，按 MIN/MAX 键进最小值保持（min hold）。红表笔夹电容的长脚（＋），黑表笔夹短脚（−）。</li>
<li>{B.tag('mac')}跑满载测试（脚本我开机后先放到 A7Z 上）：</li>
</ol>
{B.cmd('mac', "ssh a7z '~/duck/a7z_load_test.sh 20'", "00:12:01.123 # load test 20s boot_id 5de0e183-... nproc 8\n00:12:01.140 before: temps 62 61 ... MHz p0 1404/1794 p6 1008/1404 vin ...\n00:12:02.2 t=1s temps 64 ... MHz p0 1794/1794 p6 1404/1404 ... load 7.9\n...\n00:12:21.5 after: temps 78 ... boot_id 5de0e183-...\n00:12:21.5 # done: same boot_id means no reset\n（数字是示例；p0、p6 是两组 CPU，斜线前后是当前/上限 MHz）")}
<div class="card"><p><b>怎么读：</b>前后两个 boot_id 一样 = 没重启。万用表的最小值 ≥ 4.9 V = 这头的 5 V 顶得住；&lt; 4.75 V = 5 V 这一路还是不够，告诉我数值。</p>
<p><b>万用表的局限：</b>普通万用表的最小值保持每秒只采样几次，几毫秒的瞬间凹陷它看不到。所以“没量到低电压”不等于没有；“量到了”才算数。真要看毫秒级的凹陷，用 RoboClub 的示波器，单次触发设在 4.75 V 以下。</p></div>
''')

S_CLOSE = B.step('close', '第 7 步 · 5 分钟', '合头盖，验证', '三颗螺丝拧回去，Wi-Fi 信号和打开时差不多，开机 5 分钟后的温度记下来了。', f'''
<ol class="acts">
<li>{B.tag('hand')}断电（第 2 步的做法）。如果第 3 步拔过摄像头排线，先插回去：金手指方向和拔的时候一样，推到底再扣上小黑扣。</li>
<li>{B.tag('hand')}把杜邦线顺着插头往下折（和 <a href="A7Z-PINS.html">插线页</a>合盖那步一样），把盖子扣回去。扣到一半时从缝里看一眼：<b>铜块没有碰到摄像头板</b>。</li>
<li>{B.tag('hand')}三颗 M2.6 × 6 拧回下头壳的三个耳朵。拧到贴住就停，PLA 的孔拧过头会滑牙。</li>
<li>{B.tag('hand')}插回电源，等 60 秒。</li>
<li>{B.tag('mac')}看 Wi-Fi 信号（和天线页第 6 步一样）：</li>
</ol>
{B.cmd('mac', "ssh a7z 'iw dev wlan0 link | grep signal'", 'signal: -55 dBm   （数值和开盖前差不多就行）')}
<ol class="acts" start="6">
<li>{B.tag('mac')}开机 5 分钟后看温度（10 Hz 的温度日志一直在后台写）：</li>
</ol>
{B.cmd('mac', "ssh a7z 'tail -1 ~/duck-logs/thermal.log'", '1792470520.72 80.5 79.9 79.9 80.5 79.8 78.0 79.8 40.1 load 0.46 p0 780/1508 p6 1008/1404\n（温度是 2026-10-20 的真实读数，频率是示例。前 8 个数是芯片各区温度 °C；p0、p6 是两组 CPU，p 后面是这组的第一个 CPU 编号，斜线前后是当前/上限 MHz；某组 CPU 全关了显示 off）', '格式')}
<div class="card"><p><b>对照：</b>2026-10-20 凌晨没贴散热片时，热重启后 4 分钟空闲是 80 到 81 °C（上面那行的温度就是那时的）。贴了以后冷开机 5 分钟的数值发给我，我和跑步时的曲线一起对。</p></div>
''')

SOURCES = '''
<section class="step" id="sources"><h2>依据</h2><ul class="src">
<li>芯片位置和空隙：guide/print/a7z-head/build_a7z_head.py 的 soc_a733（离 1 号针那端 20.4 到 35.8 mm，离排针边 10.0 到 25.3 mm）。PCB 顶面到摄像头模型 guide/print/face-a7z/camera_13m214.stl 沿板子法线最近 13.73 mm（2026-10-21 散热研究，0.5 mm 网格），减去 A733 封装高度 0.951 mm（Allwinner A733 数据手册 3.12 节：ED-FCCSP 570 球，15 × 15 mm，最高 0.951 mm），得 12.8 mm。照片上的散热片按 15 × 15 mm 画在 Radxa 官方正面照 a7z-top.png 上，核对图 bringup/a7z/shots/check_cooling.png。</li>
<li>鳍片竖放：头里板子排针朝下、元件面朝脸（guide/print/a7z-head/checks.json 的板子坐标系，离开排针边的方向是 (0.17, 0, 0.98)，几乎竖直向上）；头壳里的空气从脖子口进、往上走，鳍片竖着槽才顺着气流（2026-10-21 散热研究，guide/firmware/mac/investigation-20261021/findings-cooling.md Q3 a）。</li>
<li>头盖怎么固定：组装指南 guide/content/steps.py（V1.9 头盖“closes with the same three ROBOTIS M2.6 × 6”；下头壳的三个 cap-screw tabs）。板子、喇叭、功放、天线都在盖子上：同一文件的 V1.17 头盖说明和 A7Z-ANTENNA.html。</li>
<li>5 V 线在 2、6 号针，功放 Vin 在 4 号：bringup/a7z/README.md 的最终针位表（2026-10-15）；Radxa 原理图 V1.11 第 14 页 J11 的 2、4 脚是 VCC5V0_SYS。</li>
<li>发热和降频：Radxa Cubie A7Z 产品手册 Rev 1.1 第 6 节（内部调频让 CPU 不超过 85 °C；持续重载可能需要额外散热）；Radxa 论坛 “Extreme throttling introduced on A733”（60 °C 降到 416 MHz，官方说热量不可避免、建议散热片）；LinuxLinks 实测整板空闲 2.2 W、CPU 满载 5.4 W。</li>
<li>掉电证据：guide/firmware/mac/robot-runs-20261019-a7z/README.md（四次复位的时间线：板子凉、不降频的 35 分钟没掉；之后 82 到 88 °C、频率来回跳，四次全掉，三次在策略启动瞬间；舵机那路 7.1 到 7.3 V 没塌）。</li>
<li>电容型号：Panasonic EEU-FR1C471 规格（470 µF 16 V，8 × 11.5 mm，脚距 3.5 mm，105 °C）来自 Future Electronics 和 RS 的产品页，2026-10-20 查。</li>
<li>满载测试脚本：guide/firmware/pi/a7z_load_test.sh（2026-10-20；2026-10-21 起每秒记录两组 CPU 的频率）。</li>
<li>核对日期：2026-10-21。</li></ul></section>'''

LEAD = ('<p class="lead">A7Z 装在头盖内面，喇叭、功放、天线也都在盖子上：拧下三颗螺丝掀起盖子，芯片那一面就朝着你，什么都不用撕。'
        '这一页的主线是给主芯片贴一块 15 × 15 mm 的铜散热片，然后合上盖子验证；焊电容那一步先不做，留着备用。全程断电操作，只有第 6 步（可选）要通电量一次。</p>')
NAV = [('parts', '1 认零件'), ('off', '2 断电'), ('open', '3 开头盖'), ('sink', '4 贴散热片'), ('cap', '5 焊电容（先不做）'), ('meter', '6 量 5 V（可选）'), ('close', '7 合盖验证')]
BODY = S_PARTS + S_OFF + S_OPEN + S_SINK + S_CAP + S_METER + S_CLOSE + SOURCES

if __name__ == '__main__':
    OUT.write_text(B.page('A7Z 散热片和电容', 'A7Z 散热片和电容：开头盖、贴铜块、焊电容、合盖验证', LEAD, NAV, BODY), encoding='utf-8')
    print(OUT, OUT.stat().st_size)
