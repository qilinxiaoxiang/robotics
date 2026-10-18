import sys, json, numpy as np, trimesh, shapely, shapely.geometry.polygon, manifold3d as m3
from PIL import Image, ImageDraw, ImageFont
G = '/Users/xiangzheng/code/robotics/microduck-sim/guide'
sys.path.insert(0, G + '/content/interference-audit'); sys.path.insert(0, G + '/print/rear-pack')
from ia_lib import CACHE
from raster import render
S = str(__import__('pathlib').Path(__file__).resolve().parent) + '/'
FONT = '/System/Library/Fonts/Hiragino Sans GB.ttc'
fT = ImageFont.truetype(FONT, 30); fS = ImageFont.truetype(FONT, 23); fL = ImageFont.truetype(FONT, 22)
ORA = (243, 154, 74); ORA2 = (225, 120, 45); BRN = (181, 101, 29); BLU = (40, 100, 220); RED = (215, 40, 40)
GRY = (120, 120, 128); SCR = (40, 90, 230); DRK = (70, 70, 78)


def mesh(k):
    z = np.load(CACHE / f'solid-{k}.npz'); return trimesh.Trimesh(z['v'], z['f'], process=False)


def M(t):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))


def T(m):
    o = m.to_mesh(); return trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3], np.asarray(o.tri_verts), process=False)


def box(lo, hi):
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    return m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def cyl(p0, p1, r, n=48):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); v = p1 - p0; L = np.linalg.norm(v)
    c = trimesh.creation.cylinder(radius=r, height=L, sections=n)
    c.apply_translation([0, 0, L / 2])
    z = np.array([0, 0, 1.0]); a = v / L
    R = trimesh.geometry.align_vectors(z, a); c.apply_transform(R); c.apply_translation(p0)
    return M(c)


def screw(seat, axis, L, head_d=4.0, head_h=1.5):
    seat = np.asarray(seat, float); a = np.asarray(axis, float)
    head = cyl(seat - a * head_h, seat, head_d / 2)
    shank = cyl(seat, seat + a * L, 1.0)
    return head + shank


def clip(t, lo, hi):
    return T(M(t) ^ box(lo, hi))


def canvas_for(img, meta, title, notes, w=None):
    W, H = img.size; top = 64; bot = 28 + 33 * len(notes)
    tw = max([fT.getlength(title)] + [fS.getlength(t) for t in notes]) + 30
    cw = int(max(W, w or 0, tw))
    c = Image.new('RGB', (cw, H + top + bot), (255, 255, 255)); ox = (cw - W) // 2; c.paste(img, (ox, top))
    d = ImageDraw.Draw(c); d.text((12, 12), title, font=fT, fill=(0, 0, 0))
    for i, t in enumerate(notes):
        d.text((12, H + top + 14 + 33 * i), t, font=fS, fill=(25, 25, 25))
    lo, hi, ppm, r, u = meta

    def P(p):
        p = np.asarray(p, float); return (ox + (p @ r - lo[0]) * ppm, top + (hi[1] - p @ u) * ppm)
    return c, d, P


def render2(layers, view, ppm, ghost=None, up=(0, 0, 1), light=None):
    v = -np.asarray(view, float); v /= np.linalg.norm(v)
    L = light if light is not None else tuple(v + np.array([0, 0, 0.6]) + np.cross(v, [0, 0, 1]) * 0.3)
    img, meta = render(layers, view, up=up, px_per_mm=ppm, ghost=ghost, light=L)
    return img, meta


def tag(d, xy, text, col=(0, 0, 0), anchor=None, font=None):
    d.text(xy, text, font=font or fL, fill=col, stroke_width=3, stroke_fill=(255, 255, 255), anchor=anchor)


def arrow(d, a, b, col=RED, w=4):
    d.line([a, b], fill=col, width=w); v = np.array(b) - np.array(a); v = v / (np.linalg.norm(v) + 1e-9); n = np.array([-v[1], v[0]])
    tip = np.array(b); d.polygon([tuple(tip), tuple(tip - v * 18 + n * 9), tuple(tip - v * 18 - n * 9)], fill=col)


def ring(d, xy, rad, col=RED, w=4):
    x, y = xy; d.ellipse([x - rad, y - rad, x + rad, y + rad], outline=col, width=w)


def hstack(ims, gap=30):
    H = max(i.height for i in ims); W = sum(i.width for i in ims) + gap * (len(ims) - 1)
    c = Image.new('RGB', (W, H), (255, 255, 255)); x = 0
    for i in ims:
        c.paste(i, (x, 0)); x += i.width + gap
    return c


def vstack(ims, gap=30):
    W = max(i.width for i in ims); H = sum(i.height for i in ims) + gap * (len(ims) - 1)
    c = Image.new('RGB', (W, H), (255, 255, 255)); y = 0
    for i in ims:
        c.paste(i, (0, y)); y += i.height + gap
    return c


sl, sr, rp = mesh('shell_left'), mesh('shell_right'), mesh('rear_pack')
SL, SR, RP = M(sl), M(sr), M(rp)
report = {}

# ------------------------------------------------------------------ ② shoulders behind the pack's T-head
YZ = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)


def sec(t, x):
    s = t.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0]); p, _ = s.to_2D(to_2D=YZ)
    return shapely.unary_union(list(p.polygons_full))


plate = sec(rp, -20.0)
shells_min = None
for x in np.arange(-24.0, -18.99, 0.5):          # tightest shell profile over the extruded length
    s = sec(sl, x).union(sec(sr, x))
    shells_min = s if shells_min is None else shells_min.union(s)
region = shapely.box(15.3, 28.0, 33, 45).union(shapely.box(-33, 28.0, -15.3, 45))
grown = plate.buffer(0.40, join_style=2).intersection(region).difference(shells_min.buffer(0.15))
grown = grown.buffer(-0.05).buffer(0.05)
polys = [g for g in (grown.geoms if hasattr(grown, 'geoms') else [grown]) if g.area > 1.0]
blue = None
for g in polys:
    g = shapely.geometry.polygon.orient(g, 1.0)
    pts = np.array(g.exterior.coords)[:-1]
    cs = m3.CrossSection([pts.tolist()])
    ex = m3.Manifold.extrude(cs, 5.0)                      # z of extrude = world x after mapping
    v = ex.to_mesh(); V = np.asarray(v.vert_properties)[:, :3]; F = np.asarray(v.tri_verts)
    W_ = np.c_[V[:, 2] - 24.0, V[:, 0], V[:, 1]]           # (y,z,h) -> (x=-24+h, y, z)
    tm = trimesh.Trimesh(W_, F, process=False)
    if tm.volume < 0: tm.invert()
    mm = M(tm)
    blue = mm if blue is None else blue + mm
blue = blue - RP
ov = (blue ^ (SL + SR)).volume()
gap_now = plate.distance(sec(sl, -20.0).union(sec(sr, -20.0)))
report['shoulder'] = dict(volume=round(blue.volume(), 1), overlap_shells=round(ov, 3), gap_now=round(gap_now, 2),
                          gap_new=round(shapely.unary_union(polys).union(plate.buffer(0.4).intersection(region)).distance(shells_min), 2))
print('shoulder', report['shoulder'])
BL = T(blue)
blk = T(SL ^ box([-23.6, 21.0, 12], [-19.4, 27.0, 33.5]))
blk_r = T(SR ^ box([-23.6, -27.0, 12], [-19.4, -21.0, 33.5]))
sl_rest = T(SL - box([-23.6, 21.0, 12], [-19.4, 27.0, 33.5]))

# panel ②a: left shell from inside, rib in red
VIEW_IN = (0.35, 1.0, 0.18)
img, meta = render2([(clip(sl_rest, [-48, -5, -5], [5, 40, 45]), ORA), (blk, RED)], VIEW_IN, 7.0)
c, d, P = canvas_for(img, meta, '② 先看你手里的左侧壳：里面后半截有一块小凸台',
                     ['红色 = 小凸台（左右壳各一块），在壳后半截的内侧墙上。',
                      '现在背包上没有东西压住它：侧壳后半截只靠前面的螺丝挂着，',
                      '和背包之间留着 0.55 mm 的缝。'])
tag(d, P([-21.5, 24, 35.5]), '小凸台', RED)
tag(d, P([-40, 20, 41]), '后', (0, 0, 0)); tag(d, P([0, 20, 41]), '前 →', (0, 0, 0))
pa = c

# panel ②b: pack with the blue shoulders, rear-left-top view
VIEW_PK = (1.0, -0.75, -0.55)
img, meta = render2([(clip(rp, [-50, -30, -2], [0, 30, 45]), BRN), (BL, BLU)], VIEW_PK, 7.0)
c, d, P = canvas_for(img, meta, '要加的：背包 T 形顶的两个肩膀往后加厚 3 mm',
                     ['蓝色 = 加在背包上的部分（和背包一起打印，不是单独零件）。',
                      '肩膀外边再往外长 0.4 mm，和侧壳的缝从 0.55 mm 变成 0.15 mm。',
                      '中间走线的缺口和 OpenRB 的位置都不动。'])
tag(d, P([-23, 22, 39]), '左肩', BLU); tag(d, P([-23, -24, 39]), '右肩', BLU)
pb = c

# panel ②c: cutaway at x = -21.6 (through the rib and the new shoulder), seen from behind
X0 = -21.6
cut = lambda t: clip(t, [X0, -40, 12], [5, 40, 45])
img, meta = render2([(cut(sl_rest), ORA), (cut(sr), ORA), (cut(blk), RED), (cut(blk_r), RED), (cut(rp), BRN), (cut(BL), BLU)],
                    (1.0, 0.0, -0.12), 7.5)
c, d, P = canvas_for(img, meta, '装好后从背后切开看（切在小凸台的位置）',
                     ['壳顶压在背包顶上：后半截不能往下掉。',
                      '小凸台卡在蓝色肩膀下面：后半截不能往上翘。',
                      '装法不变：侧壳照原来从旁边推上去，凸台顺着滑进肩膀下面，不加螺丝。'])
tag(d, P([X0, 25, 26]), '凸台', RED, anchor='mm'); tag(d, P([X0, -25, 26]), '凸台', RED, anchor='mm')
tag(d, P([X0, 21, 34.5]), '肩膀', BLU, anchor='mm'); tag(d, P([X0, -21, 34.5]), '肩膀', BLU, anchor='mm')
pc = c
fig2 = hstack([pa, pb, pc])
fig2.save(S + 'fig-2-shoulders.png')
print('fig2', fig2.size)

# ------------------------------------------------------------------ ③ horn screw counterbores (left shell, ID12 side)
d_ = json.load(open(G + '/content/fasteners.json'))
horn = [f for f in d_['screws'] if f['id'] in ('S12-horn-029', 'S12-horn-030', 'S12-horn-031', 'S12-horn-032')]
cb = None; sc_old = None; sc_new = None
for f in horn:
    c0 = np.array(f['center']); a = np.array(f['axis'])
    k = cyl(c0 - a * 3.0, c0 + a * 2.0, 2.2)
    cb = k if cb is None else cb + k
    so = screw(c0, a, 6.0); sn = screw(c0 + a * 2.0, a, 4.0)
    sc_old = so if sc_old is None else sc_old + so
    sc_new = sn if sc_new is None else sn + sc_new
SLc = SL - cb
report['counterbore_left_volume'] = round((SL ^ cb).volume(), 2)
m12 = mesh('motor12'); m12 = m12.convex_hull if False else m12
VIEW_LOBE = (0.95, -1.0, -0.15)
lobe = lambda t: clip(t, [14, 10, 20], [38, 40, 45])
img, meta = render2([(lobe(sl), ORA), (T(sc_old), SCR)], VIEW_LOBE, 16.0)
c, d, P = canvas_for(img, meta, '③ 现在：左侧壳外面这 4 颗蓝色螺丝',
                     ['孔口是平的，螺丝头整个露在壳外面。',
                      '拧的时候螺丝没有东西扶，容易歪，要一直对准。'])
p3a = c
img, meta = render2([(lobe(T(SLc)), ORA), (T(sc_new), SCR)], VIEW_LOBE, 16.0)
c, d, P = canvas_for(img, meta, '改后：每个孔口挖一个圆坑',
                     ['坑 4.4 mm 宽、2 mm 深，螺丝头正好放进去，坑壁把螺丝扶正。',
                      '右侧壳（被动轴那边）的 4 个孔也一样改。'])
p3b = c

# section through screw 029 (z = 38.4), before and after, seen from above
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
FP = FontProperties(fname=FONT)
XY = np.eye(4)
fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.3))
for ax, (shell, scr, ttl) in zip(axs, ((sl, sc_old, '现在：M2×6，头在壳外'), (T(SLc), sc_new, '改后：M2×4，头沉进坑里'))):
    for t, col in ((m12, '#9aa3ad'), (shell, '#f39a4a'), (T(scr), '#2a5ad8')):
        s = t.section(plane_origin=[0, 0, 38.4], plane_normal=[0, 0, 1])
        if s is None: continue
        p, _ = s.to_2D(to_2D=XY)
        for poly in p.polygons_full:
            ax.fill(*poly.exterior.xy, color=col, ec='k', lw=0.4)
            for h in poly.interiors: ax.fill(*h.xy, color='white', ec='k', lw=0.4)
    ax.axhline(17.9 - 6.0, color='red', lw=1.2, ls='--')
    ax.text(26.6, 17.9 - 6.0 + 0.25, '螺丝尖：两种一样深', fontproperties=FP, fontsize=10, color='red')
    ax.set_xlim(18, 34); ax.set_ylim(10.5, 21); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(ttl, fontproperties=FP, fontsize=13)
    ax.text(18.3, 20.2, '壳外面', fontproperties=FP, fontsize=10); ax.text(18.3, 13.6, '灰 = ID12 舵盘', fontproperties=FP, fontsize=10)
plt.tight_layout(); plt.savefig(S + 'sec3.png', dpi=110); plt.close()
s3 = Image.open(S + 'sec3.png').convert('RGB')
c = Image.new('RGB', (s3.width, s3.height + 64 + 28 + 33 * 2), (255, 255, 255)); c.paste(s3, (0, 64)); dd = ImageDraw.Draw(c)
dd.text((12, 12), '从上往下切开看一颗', font=fT, fill=(0, 0, 0))
dd.text((12, 64 + s3.height + 14), '螺丝头往里沉了 2 mm，所以螺丝也短 2 mm：M2×6 换成 M2×4。', font=fS, fill=(25, 25, 25))
dd.text((12, 64 + s3.height + 47), '拧进舵盘的深度和现在完全一样；壳在螺丝头下面还剩 1.3 mm。', font=fS, fill=(25, 25, 25))
p3c = c

# ------------------------------------------------------------------ ① cross screw, M2 x 6
seat = np.array([-38.0, 2.05, 34.96]); ax_ = np.array([0, -1.0, 0])
bore = cyl([-38.0, 2.05, 34.96], [-38.0, 33.0, 34.96], 2.2)
SLb = SL - bore
report['cross_bore_removed'] = round((SL ^ bore).volume(), 2)
xs = screw(seat, ax_, 6.0)
report['cross_screw_tip_y'] = round(float(seat[1] - 6.0), 2)
# outside view of the left shell rear with the tunnel mouth
VIEW_REAR = (0.55, -1.0, -0.35)
img, meta = render2([(T(SLb), ORA)], VIEW_REAR, 6.0)
c, d, P = canvas_for(img, meta, '① 左侧壳后上角，外面这个小洞',
                     ['原版就有，现在 3.5 mm，螺丝头进不去；改成 4.4 mm。',
                      '1 颗 M2×6 从这里放进去，拧进右侧壳。'])
q = P([-38.0, 30.5, 34.96]); ring(d, q, 22)
tag(d, (q[0] + 28, q[1] - 14), '小洞', RED)
p1a = c
# cutaway: keep z <= 34.96, seen from above
cutz = lambda t: clip(t, [-50, -40, 20], [-26, 40, 34.96])
img, meta = render2([(cutz(T(SLb)), ORA), (cutz(sr), ORA2), (cutz(T(xs)), SCR)], (0.0, 0.0, -1.0), 9.0, up=(1, 0, 0))
c, d, P = canvas_for(img, meta, '从上往下切开看这条孔',
                     ['左壳的孔是一条 25 mm 长的通道，螺丝头停在通道底。',
                      '螺丝穿过左壳，拧进右壳 3.2 mm，尖不出头。',
                      '装法：机器人左侧朝上放，螺丝丢进洞里自己掉到底，',
                      '用杆子细于 4 mm、长 30 mm 以上的十字螺丝刀伸进去拧。'])
tag(d, (P([-38, 13, 34.96])[0], P([-38, 13, 34.96])[1] - 40), '左壳通道（扩到 4.4 mm）', (0, 0, 0), anchor='mm')
tag(d, (P([-38, -9, 34.96])[0], P([-38, -9, 34.96])[1] - 40), '右壳', (0, 0, 0), anchor='mm')
tag(d, (P([-38, 0, 34.96])[0] + 40, P([-38, 0, 34.96])[1] + 30), 'M2×6', SCR)
p1b = c
fig1 = vstack([hstack([p1a, p1b]), hstack([p3a, p3b, p3c])], gap=40)
fig1.save(S + 'fig-1-3-screws.png')
print('fig1', fig1.size)
json.dump(report, open(S + 'fig-report.json', 'w'), indent=1)
print(report)
