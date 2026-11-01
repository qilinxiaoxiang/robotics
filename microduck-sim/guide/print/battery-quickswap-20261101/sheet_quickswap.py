"""Review sheet of the built quick-swap parts with Chinese labels: renders/review-sheet.png (run render_quickswap.py first).

    uv run --with matplotlib --with pillow python sheet_quickswap.py
"""
import json
from pathlib import Path
import numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from PIL import Image

HERE = Path(__file__).resolve().parent; R = HERE / 'renders'
ck = json.loads((HERE / 'build/build.json').read_text())
fm.fontManager.addfont('/Library/Fonts/Arial Unicode.ttf'); plt.rcParams['font.family'] = 'Arial Unicode MS'
img = lambda n, box: np.asarray(Image.open(R / n).convert('RGB').crop(box))

fig = plt.figure(figsize=(18, 12.5), facecolor='white')
fig.suptitle('电池快换（建模版）：顶盖连同后圆角一起掀开，卡扣在背后', fontsize=22, y=0.985)

def panel(pos, im, title, notes):
    ax = fig.add_axes(pos); ax.imshow(im); ax.axis('off'); ax.set_title(title, fontsize=16, loc='left', pad=6)
    for x, y, t, tx, ty in notes:
        ax.annotate(t, (x, y), (tx, ty), fontsize=12, arrowprops=dict(arrowstyle='->', color='#333', lw=1.2),
                    bbox=dict(boxstyle='round,pad=0.25', fc='white', ec='#999', lw=0.8))

panel([0.01, 0.49, 0.32, 0.42], img('1-closed.png', (250, 150, 950, 850)), '① 平时：顶盖和背后挡片扣住',
      [(220, 250, '蓝色顶盖：顶面和后圆角跟原来齐平', 0, 20), (220, 420, '背后挡片，下沿用指甲往外一拨', 0, 640), (360, 120, '电池线从缺口出来', 380, 30)])
panel([0.34, 0.49, 0.32, 0.42], img('2-rear-lifted.png', (250, 150, 950, 850)), '② 拨开挡片，后边抬起约 15 度',
      [(200, 370, '卡扣槽（盖子背面）', 0, 600), (330, 230, '前面两个小舌头勾在框架顶边下', 330, 30)])
panel([0.67, 0.49, 0.32, 0.42], img('3-battery-out.png', (300, 0, 900, 600)), '③ 顶盖往后取下，电池竖着抽出',
      [(250, 300, '电池抬起约 66 mm 就完全出来', 330, 60), (200, 470, '两根横条固定不拆', 0, 560)])
panel([0.01, 0.03, 0.32, 0.44], img('4-back.png', (100, 100, 1100, 1000)), '④ 背面：挡片 28 × 19 mm，凸出 1.2 mm',
      [(520, 400, '挡片内侧凸起 1.2 mm 卡进槽里', 560, 780), (300, 190, '引线缺口向后开，掀盖不用拔线', 0, 60)])
panel([0.34, 0.03, 0.32, 0.44], img('6-hatch-print.png', (100, 150, 1100, 950)), '⑤ 打印姿态：挡片平贴热床，不用支撑',
      [(650, 700, '挡片平放打印，弯曲顺着打印层', 480, 790), (480, 360, '压住电池的楔块（45 度，不用支撑）', 520, 120)])

f = ck['flap']; p = ck['print']
txt = (f"检查结果（全部通过）\n"
       f"· 关闭时和框架、盖子、横条、开关、DFR1202、电池都不干涉\n"
       f"· 掀到 18 度、往后抽 1.5 mm 的路径都不碰\n"
       f"· 电池竖直抽出 70 mm 不碰（盖子圆角处 0.07 mm³ 是原来就有的擦边）\n"
       f"· 楔块离电池顶 {ck['wedge_to_battery_mm']} mm，摔倒时电池窜不上来\n"
       f"· 卡扣挡片：长 {f['length_mm']} mm、厚 {f['thickness_mm']} mm，拨开 {f['release_pull_mm']} mm 时应变 {f['root_strain_pct']}%\n"
       f"· 前舌头勾住 {ck['tab_lip_engagement_mm']} mm\n"
       f"· 三个零件都没有新增的薄壁（1.2 mm 规则）\n"
       f"· 顶盖重 {ck['hatch_mass_g']} g，打印高 {p['battery_hatch']['print_height_mm']} mm\n\n"
       "要重打的件\n· 框架（顶上开口）：开关和 DFR1202 要挪过去\n· 盖子（开口、圆角缺口、卡扣槽）\n· 新的顶盖\n\n"
       "和概念图的区别\n· 盖子后上角是圆角，挡住电池后 2 mm，\n  所以顶盖要连圆角一起做\n· 卡扣从顶上侧面挪到背后，应变更低")
ax = fig.add_axes([0.68, 0.03, 0.31, 0.43]); ax.axis('off'); ax.text(0, 1, txt, va='top', fontsize=12.5, linespacing=1.45)
fig.savefig(R / 'review-sheet.png', dpi=90)
print('ok')
