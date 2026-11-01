import sys, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle, Polygon
from PIL import Image
D = sys.argv[1]; OUT = sys.argv[2]
fm.fontManager.addfont('/Library/Fonts/Arial Unicode.ttf')
plt.rcParams['font.family'] = 'Arial Unicode MS'

def crop(p, box):
    return np.asarray(Image.open(p).convert('RGB').crop(box))

fig = plt.figure(figsize=(18, 12.5), facecolor='white')
fig.suptitle('电池背包快换概念：电池从顶上抽出，顶盖一个卡扣，不用工具', fontsize=22, y=0.985)

def panel(pos, img, title, notes):
    ax = fig.add_axes(pos); ax.imshow(img); ax.axis('off')
    ax.set_title(title, fontsize=16, loc='left', pad=6)
    for (x, y, t, tx, ty) in notes:
        ax.annotate(t, (x, y), (tx, ty), fontsize=12, color='#111',
                    arrowprops=dict(arrowstyle='->', color='#333', lw=1.2),
                    bbox=dict(boxstyle='round,pad=0.25', fc='white', ec='#999', lw=0.8))
    return ax

c = crop(f'{D}/closed.png', (230, 260, 1000, 1030))
panel([0.01, 0.49, 0.32, 0.42], c, '① 平时：顶盖扣住，电池不会窜',
      [(260, 110, '蓝色顶盖', 20, 30), (330, 350, '粉色卡扣（按钮）', 360, 640), (190, 190, '电池线从盖子缺口出来', 330, 40),
       (160, 520, '橙色背包（不变）', 20, 720)])
o = crop(f'{D}/open.png', (230, 40, 1000, 810))
panel([0.34, 0.49, 0.32, 0.42], o, '② 拔插头，按卡扣，掀开顶盖',
      [(420, 130, '顶盖整块拿下', 420, 330), (300, 470, '电池（绿）在开口里', 20, 690)])
l = crop(f'{D}/lift.png', (200, 0, 970, 770))
panel([0.67, 0.49, 0.32, 0.42], l, '③ 拉拉带，电池竖着抽出',
      [(280, 300, '电池往上拿 62 mm', 420, 120), (480, 450, '两根横条一直拧着不拆', 330, 640)])
k = crop(f'{D}/latch.png', (0, 120, 1100, 1100))
panel([0.01, 0.03, 0.32, 0.45], k, '④ 卡扣近看（从后左上方）',
      [(500, 260, '按钮：往里推 1 mm', 560, 80), (520, 470, '钩子勾在后盖顶边下面', 600, 700),
       (330, 230, '舌头平躺在盖板里，横着弯', 20, 820)])

# ⑤ top view of the hatch, robot frame (x forward = right, y left = up)
ax = fig.add_axes([0.37, 0.07, 0.30, 0.38]); ax.set_aspect('equal'); ax.axis('off')
ax.set_title('⑤ 顶盖俯视（mm，前方朝右，缺口向后开口）', fontsize=16, loc='left')
ax.add_patch(Rectangle((-74.35, -16), 12.6, 32, fc='#dfe6e9', ec='#636e72', ls='--', lw=1.2))
ax.text(-68.0, 0.5, '下面是开口\n32 × 12.6', ha='center', fontsize=10, color='#636e72')
ax.add_patch(Rectangle((-75.35, -17.5), 14.6, 35, fc='#74b9ff', ec='#0984e3', alpha=0.55, lw=1.5))
for lo, hi, t in ((-11, -5, '主线缺口'), (9, 15, '平衡线缺口')):
    ax.add_patch(Rectangle((-75.5, lo), 9.5, hi - lo, fc='white', ec='none'))
    ax.plot([-75.35, -66.0, -66.0, -75.35], [lo, lo, hi, hi], color='#0984e3', lw=1)
    ax.text(-70.7, (lo + hi) / 2, t, ha='center', va='center', fontsize=9)
ax.add_patch(Rectangle((-75.5, -17.6), 13.9, 3.3, fc='white', ec='none'))
ax.add_patch(Rectangle((-75.35, -15.9), 13.75, 1.6, fc='#e84393', ec='#b33771'))
ax.add_patch(Rectangle((-75.0, -17.0), 3.5, 1.1, fc='#b33771'))
ax.text(-68.5, -19.6, '粉色舌头 15 × 1.6 mm，根部在前', ha='center', fontsize=10, color='#b33771')
for y in (-6, 8):
    ax.add_patch(Rectangle((-61.85, y - 3), 2.0, 6, fc='#0984e3'))
ax.text(-58.6, 1, '两个固定前舌\n勾在框架顶边下', fontsize=10, va='center')
ax.annotate('', (-75.35, 19.5), (-60.75, 19.5), arrowprops=dict(arrowstyle='<->'))
ax.text(-68, 20.3, '14.6', ha='center', fontsize=10)
ax.annotate('', (-77.3, -17.5), (-77.3, 17.5), arrowprops=dict(arrowstyle='<->'))
ax.text(-79.5, 0, '35', ha='center', fontsize=10, rotation=90)
ax.set_xlim(-82, -50); ax.set_ylim(-22, 23)

# ⑥ text
ax = fig.add_axes([0.69, 0.03, 0.30, 0.43]); ax.axis('off')
txt = ('换电池（约 15 秒，不用工具）\n'
       '1. 拔掉盒顶的 XT30 插头\n2. 粉色按钮往里推，掀起顶盖后边，往后拿下\n'
       '3. 拉电池下面的拉带，电池竖着出来\n4. 新电池放进去，拉带留在外面\n5. 顶盖前舌先插进去，压下后边，咔一声\n6. 插回 XT30\n\n'
       '改动\n· 去掉托架顶片，顶部开 32 × 12.6 开口\n· 新增一个顶盖（1.6 mm 厚，平放打印）\n'
       '· 两根横条变成固定件，不再拆\n· 背包盖、开关、DFR1202 不动\n\n'
       '卡扣按 PLA 算\n· 舌头 15 × 1.6 mm，扣住时伸直不受力\n· 钩子 1 mm，弯过去时应变约 1.1%\n· 扣住面是直角，靠剪切受力')
ax.text(0, 1, txt, va='top', fontsize=13, linespacing=1.45)
fig.savefig(OUT, dpi=90)
