#!/usr/bin/env python3
"""Build HEAD-3D.html: an interactive, exploded 3D view of the MicroDuck head with the V1.9 neck-route + audio extension.

Read-only on the design. V1.8 parts come from guide/data/guide-data.json. The V1.9 release solids (head cap, speaker
retainer, four clips, resistor envelope) come from guide/print/ext-v19/; every one is sha256-checked against
manifest-ext-v19.json (resistor-placement.json for the envelope) right before the build, and a mismatch stops it.
The amplifier, speaker and connector housings are still the audio study solids (../audio); the Pi screws come from
../pi-mount. Wire centrelines come from guide/print/ext-v19/route-v19.json (bundle, fan wires, audio jumpers).
The page is self-contained: three.js r164.1 and OrbitControls are inlined the same way guide/build_guide.py does it
(that module's load_three is reused), geometry is one gzip+base64 block, and a Content-Security-Policy blocks every
network request. Page text is Chinese; facts are taken from guide/print/ext-v19/README.md, the study READMEs and
HANDOFF-20261013.md.

Run:  /tmp/microduck-cad-venv/bin/python build_head3d.py [--out HEAD-3D.html] [--manifest build-summary.json]
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
EXT = HERE.parent
GUIDE = EXT.parent
SIM = GUIDE.parent
INT, AUD, PIM = EXT / 'integrated', EXT / 'audio', EXT / 'pi-mount'
V19 = GUIDE / 'print' / 'ext-v19'
SRC = HERE / 'src'
sys.path.insert(0, str(GUIDE))
from build_guide import DEFAULT_THREE, load_three, script_safe  # noqa: E402

CREASE_DEG = 32.0
LIFT = [0.0, 0.0, 60.0]

# --------------------------------------------------------------------------- V1.9 release solids (sha-checked)

MANIFEST = json.loads((V19 / 'manifest-ext-v19.json').read_text())
EXPECTED_SHA = {p['key']: p['sha256'] for p in MANIFEST['parts']}
EXPECTED_SHA['resistor_envelope_v19'] = json.loads((V19 / 'resistor-placement.json').read_text())['envelopeStl']['sha256']
V19_USED: dict[str, Path] = {}
# guide-data.json carries the V1.9 cap since guide-20261013; the V1.8 cap kept beside it is the comparison body.
V18_CAP = GUIDE / 'print' / 'world' / 'head_cap-v18.stl'


def v19(key: str) -> Path:
    """Path of a V1.9 release solid. Its sha256 is checked against the manifest in verify_v19(), right before the build."""
    path = V19 / f'{key}-world.stl'
    V19_USED[key] = path
    return path


def verify_v19() -> dict:
    """Re-hash every V1.9 solid the page uses and compare with manifest-ext-v19.json. Stops the build on a mismatch,
    so a solid that is being rebuilt (the torso clip at the time of writing) cannot slip in under a stale manifest."""
    out = {}
    bad = []
    for key, path in V19_USED.items():
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        exp = EXPECTED_SHA.get(key)
        out[key] = {'path': str(path), 'sha256': sha, 'manifestSha256': exp, 'matches': sha == exp}
        if sha != exp:
            bad.append(f'{key}: file {sha[:12]} vs manifest {str(exp)[:12]}')
    if bad:
        raise SystemExit('V1.9 solid does not match manifest-ext-v19.json (rebuild in progress?):\n  ' + '\n  '.join(bad))
    return out


# --------------------------------------------------------------------------- colour classes and change states

CLASSES = [
    {'id': 'changed', 'label': '改动的 V1.8 件（V1.9 新头盖）', 'color': '#f08c00'},
    {'id': 'newprint', 'label': '新打印件（压板、4 个卡扣）', 'color': '#7048e8'},
    {'id': 'elec', 'label': '外购电子件（功放、增益电阻、扬声器、Pi、摄像头）', 'color': '#2f9e44'},
    {'id': 'wire', 'label': '线和插头', 'color': '#e03131'},
    {'id': 'screw', 'label': '螺丝', 'color': '#343a40'},
    {'id': 'v18', 'label': 'V1.8 不变', 'color': '#a3aab0'},
    {'id': 'context', 'label': '背景：脖子', 'color': '#c3c9ce'},
]
CHANGES = {'new': '新增', 'changed': '改动', 'unchanged': 'V1.8 不变', 'replaced': '被替换', 'alt': '备选，不推荐'}

# Explode blocks. Phase A (slider 0-50 %) lifts every `lift` block by LIFT: the cap with the Pi, amp and speaker comes
# off as one unit, as it does on the robot. Phase B (50-100 %) adds each block's own offset.
BLOCKS = {
    'cap': {'lift': 1, 'off': [0, 0, 50]},
    'speaker': {'lift': 1, 'off': [0, 0, 30]},
    'retainer': {'lift': 1, 'off': [0, 0, 15]},
    'spkscrew': {'lift': 1, 'off': [0, 0, 3]},
    'amp': {'lift': 1, 'off': [0, 0, 19]},
    'ampscrew': {'lift': 1, 'off': [0, 0, 5]},
    'pi': {'lift': 1, 'off': [24, 0, 0]},
    'capclip': {'lift': 1, 'off': [30, 0, 0]},
    'piscrew': {'lift': 1, 'off': [36, 0, 0]},
    'hb': {'lift': 0, 'off': [0, 0, -45]},
    'js': {'lift': 0, 'off': [0, 0, -20]},
    'jaw': {'lift': 0, 'off': [30, 0, -35]},
    'mring': {'lift': 0, 'off': [30, -12, -35]},
    'm15': {'lift': 0, 'off': [0, 30, -12]},
    'cam': {'lift': 0, 'off': [18, 0, 0]},
    'face': {'lift': 0, 'off': [34, 0, 0]},
    'trim': {'lift': 0, 'off': [50, 0, 0]},
    'm14': {'lift': 0, 'off': [-32, 0, -8]},
    'yaw': {'lift': 0, 'off': [0, 0, -14]},
    'm13': {'lift': 0, 'off': [0, 0, -30]},
    'ringa': {'lift': 0, 'off': [-16, 0, -14]},
    'ringb': {'lift': 0, 'off': [16, 0, -14]},
    'neck': {'lift': 0, 'off': [0, 0, -48]},
}

SIG = {'VIN': '#e03131', 'GND': '#212529', 'BCLK': '#1c7ed6', 'LRC': '#f08c00', 'DIN': '#7048e8',
       'SPK1': '#c2255c', 'SPK2': '#f06595'}
CAP_ADDED = '#e6b400'
WIRING_ELEC = {'pi': '#b9e4c2', 'amp': '#69c17d', 'speaker': '#8fd19e'}

R19 = json.loads((V19 / 'route-v19.json').read_text())
ROUTES = R19['audioWires']['polylines']            # five jumpers + two speaker leads, as route-v19.json records them
ROUTES_AUD = json.loads((AUD / 'wire-routes.json').read_text())  # only for the rejected pin-14 ground alternative
WIRES = json.loads((AUD / 'wires.json').read_text())['wires']
BUNDLE = R19['routes'][0]
BUNDLE_PTS = [p[:3] for p in BUNDLE['points']]
BUNDLE_R = BUNDLE['groupRadiusMm']
# Segment boundaries, by point index in route-v19.json: 9 = the -y head slot, 16 = the head clip's window, 24 = the
# cap clip's channel entry, 32 = the gather point at the Pi header.
I_SLOT, I_HEADCLIP, I_CAPCLIP, I_END = 9, 16, 24, 32
FAN = R19['fanWires']


def wire_len(name: str) -> str:
    return f"{WIRES[name]['lengthMm']:.1f} mm"


def poly_len(pts: list) -> float:
    P = np.asarray(pts, float)
    return float(np.linalg.norm(P[1:] - P[:-1], axis=1).sum())


L_SEG1 = poly_len(BUNDLE_PTS[I_SLOT:I_HEADCLIP + 1])
L_SEG2 = poly_len(BUNDLE_PTS[I_HEADCLIP:I_CAPCLIP + 1])
L_SEG3 = poly_len(BUNDLE_PTS[I_CAPCLIP:I_END + 1])
L_HEAD = poly_len(BUNDLE_PTS[I_SLOT:I_END + 1])
L_ALL = poly_len(BUNDLE_PTS)
FAN_LENS = sorted(poly_len(p) for p in FAN['polylines'].values())


# --------------------------------------------------------------------------- the parts, in list order
# mesh source: ('gd', key) | ('gdm', [keys]) merged | ('stl', path) | ('stl', path, [dx,dy,dz]) | tube polyline
# Text: "{推测}" becomes an inference badge in the page.

S_INT = 'integrated/README.md'
S_AUD = 'audio/README.md'
S_PIM = 'pi-mount/README.md'
S_HO = 'HANDOFF-20261013.md'
S_GD = 'guide/data/guide-data.json（V1.8 装配指南）'
S_V19 = 'guide/print/ext-v19/README.md'
S_MAN = 'guide/print/ext-v19/manifest-ext-v19.json'
S_R19 = 'guide/print/ext-v19/route-v19.json'
S_RES = 'guide/print/ext-v19/resistor-placement.json'
S_BENCH = 'bringup/build/audio-bench/README.md'
CLIP_SHAPE = ('形状：2.0 mm 厚的带孔耳片压在原有螺丝头下面 + 一段线槽（内腔 4.8×4.8 mm，开口 2.4 mm，壁厚 1.2 mm）。'
              '8 根线从开口压进槽里，没有别的东西固定它。拆这颗螺丝之前先把线从槽里取出来。')
CLIP_UNCONFIRMED = '四个卡扣的形状 Shawn 还没确认，也都没试打过。'

# Gain resistor as the real part, at the U4 placement in resistor-placement.json (candidates.U4_detail.record). Robot
# frame at q = 0: header row along y at x 38.76 (GAIN y 0, Vin y 7.62), tails pointing -z below the board underside.
RES_PLACE = json.loads((V19 / 'resistor-placement.json').read_text())
RES_REC = RES_PLACE['candidates']['U4_detail']['record']
RES_BODY_L, RES_BODY_D = 6.3, 2.4          # YAGEO MFR-25 (1/4 W): L 6.3 mm, D 2.4 mm (yageo-mfr p3)
RES_SLEEVE_L, RES_SLEEVE_D = 7.0, 2.8      # heat-shrink sleeve after shrinking (bench README)
RES_LEAD_D = 0.6                           # lead 0.55 +/- 0.05 mm, drawn 0.6
RES_JOINT_R = 0.9                          # solder blob around each hooked tail


def _pts_tm(M) -> trimesh.Trimesh:
    mm = M.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts), process=False)


def _rod(a, b, r: float, n: int = 20):
    """manifold3d cylinder of radius r from a to b."""
    import manifold3d as m3
    a, b = np.asarray(a, float), np.asarray(b, float)
    tm = trimesh.creation.cylinder(radius=r, segment=[a, b], sections=n)
    return m3.Manifold(m3.Mesh(vert_properties=np.ascontiguousarray(tm.vertices, np.float32),
                               tri_verts=np.ascontiguousarray(tm.faces, np.uint32)))


def _wire(points: list, r: float):
    """Bent wire: a cylinder per segment and a sphere at every point, unioned."""
    import manifold3d as m3
    P = [np.asarray(p, float) for p in points]
    parts = [_rod(a, b, r) for a, b in zip(P[:-1], P[1:])]
    parts += [m3.Manifold.sphere(r, 20).translate(list(map(float, p))) for p in P]
    return m3.Manifold.batch_boolean(parts, m3.OpType.Add)


def amp_display_mesh() -> trimesh.Trimesh:
    """Amplifier as drawn on the page: the study model's 1.5 mm tail-allowance slab under the board is replaced by the
    seven real header tails (0.64 mm square posts, 1.5 mm long, on the row at x 38.76, GAIN at y 0), so the resistor
    legs, hooks and solder joints underneath are visible. Clearance checks keep using the study model."""
    amp = trimesh.load(AUD / 'study-solids' / 'amplifier-world.stl', force='mesh')
    zs = np.unique(np.round(amp.vertices[:, 2], 3))
    under = float(zs[1])
    body = trimesh.intersections.slice_mesh_plane(amp, plane_normal=[0, 0, 1], plane_origin=[0, 0, under], cap=True)
    row_x = RES_REC['legs']['GAIN']['hookCentre'][0]
    posts = [trimesh.creation.box(bounds=[[row_x - 0.32, (i - 3) * 2.54 - 0.32, under - 1.5],
                                          [row_x + 0.32, (i - 3) * 2.54 + 0.32, under]]) for i in range(7)]
    return trimesh.util.concatenate([body, *posts])


def resistor_leg_points(pin: str) -> list:
    """Lead path for the GAIN or Vin leg: out of the body end along the body axis, bend 90 degrees, run diagonally up
    to the header row, then hook three quarters round the pin tail (hook radius 0.67 mm, as resistor-placement.json)."""
    L = RES_REC['legs'][pin]
    c = np.asarray(RES_REC['bodyCentre'], float)
    sgn = -1.0 if pin == 'GAIN' else 1.0
    start = c + np.array([0.0, sgn * (RES_BODY_L / 2 - 0.3), 0.0])   # lead starts just inside the body end cap
    hc, hr = np.asarray(L['hookCentre'], float), L['hookRadiusMm']
    angles = [225, 270, 315, 360, 405, 450] if pin == 'GAIN' else [135, 90, 45, 0, -45, -90]
    hook = [hc + hr * np.array([np.cos(np.radians(t)), np.sin(np.radians(t)), 0.0]) for t in angles]
    return [start, np.asarray(L['bendAt'], float), np.asarray(L['reachesRowAt'], float)] + hook


_RES_CACHE: dict = {}


def resistor_parts() -> dict:
    """Closed trimesh solids of the fitted resistor: 'body' (6.3 x 2.4 mm), 'sleeve' (7 x 2.8 mm heat-shrink over it),
    'legs' (both U-bent 0.6 mm leads with their hooks) and 'joints' (a solder blob round each hooked tail)."""
    if _RES_CACHE:
        return _RES_CACHE
    import manifold3d as m3
    c = np.asarray(RES_REC['bodyCentre'], float)
    ax = np.asarray(RES_REC['bodyAxis'], float)
    body = _rod(c - ax * RES_BODY_L / 2, c + ax * RES_BODY_L / 2, RES_BODY_D / 2, 32)
    sleeve = _rod(c - ax * RES_SLEEVE_L / 2, c + ax * RES_SLEEVE_L / 2, RES_SLEEVE_D / 2, 32)
    legs = m3.Manifold.batch_boolean([_wire(resistor_leg_points(p), RES_LEAD_D / 2) for p in ('GAIN', 'Vin')], m3.OpType.Add)
    joints = []
    for p in ('GAIN', 'Vin'):
        hc = np.asarray(RES_REC['legs'][p]['hookCentre'], float)
        joints.append(_wire([hc + [0, 0, 0.05], hc + [0, 0, 0.45]], RES_JOINT_R))
    joints = m3.Manifold.batch_boolean(joints, m3.OpType.Add)
    _RES_CACHE.update(body=_pts_tm(body), sleeve=_pts_tm(sleeve), legs=_pts_tm(legs), joints=_pts_tm(joints))
    return _RES_CACHE


# Pi screw envelope at V1.9: the pi-mount study solid has E-pi-04 at the V1.8 M2 x 6 seat. V1.9 seats it 2.0 mm further
# out on the cap clip tab and makes it M2 x 8 (guide/content/fasteners.json E-pi-04), so the tip stays where it was.
def _fastener(fid: str) -> dict:
    def walk(o):
        if isinstance(o, dict):
            if o.get('id') == fid and 'center' in o:
                return o
            for v in o.values():
                r = walk(v)
                if r:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = walk(v)
                if r:
                    return r
        return None
    row = walk(json.loads((GUIDE / 'content' / 'fasteners.json').read_text()))
    if row is None:
        raise SystemExit(f'fasteners.json has no row {fid}')
    return row


def pi_screws_v19() -> trimesh.Trimesh:
    """A-pi_screws_envelope with its E-pi-04 body (the +y, upper one) replaced by the V1.9 M2 x 8 envelope: head
    (headDiameterMm x headHeightMm) behind the seat centre, shank diameterMm x lengthMm along the insertion axis."""
    env = trimesh.load(PIM / 'study-solids' / 'A-pi_screws_envelope-world.stl', force='mesh')
    bodies = env.split(only_watertight=False)
    keep = [b for b in bodies if not (b.bounds[0][1] > 0 and b.bounds[0][2] > 130)]
    if len(keep) != len(bodies) - 1:
        raise SystemExit(f'pi screw envelope: expected one E-pi-04 body, found {len(bodies) - len(keep)}')
    row = _fastener('E-pi-04')
    c, ax = np.asarray(row['center'], float), np.asarray(row['axis'], float)
    ax /= np.linalg.norm(ax)
    shank = trimesh.creation.cylinder(radius=row['diameterMm'] / 2, segment=[c, c + ax * row['lengthMm']], sections=24)
    head = trimesh.creation.cylinder(radius=row['headDiameterMm'] / 2, segment=[c - ax * row['headHeightMm'], c], sections=32)
    PI_SCREW_STATS.update(id='E-pi-04', spec=row['spec'], center=row['center'], axis=row['axis'], lengthMm=row['lengthMm'])
    return trimesh.util.concatenate(keep + [shank, head])


PI_SCREW_STATS: dict = {}

ITEMS: list[dict] = []


def item(**kw):
    kw.setdefault('notes', [])
    kw.setdefault('src', [])
    kw.setdefault('hidden', False)
    kw.setdefault('focus', False)
    kw.setdefault('noframe', False)
    ITEMS.append(kw)


# ---- changed V1.8
item(id='cap', name='V1.9 头盖', cls='changed', change='changed', block='cap',
     meshes=[{'src': ('stl', v19('head_cap_v19'))}],
     role='头的上半壳，Pi、功放、扬声器都装在它里面。相对 V1.8 头盖改了四处：后脑出线缺口和扎带罩补平；头顶靠后开 52 个 Ø1.8 mm 出声孔，'
          '内侧加扬声器围框和 2 个压板螺丝柱；内顶加 2 根 Ø4.0 mm 功放短柱；两根 Pi 立柱加固（连侧壁的筋、下凸台 55° 斜面、根部实心块）。',
     fix='和 V1.8 一样：3 颗 M2.5×8 自攻螺丝从下头壳的 3 个合盖耳片往上拧进头盖（两颗在前角，一颗在后部）。面板没有螺丝，也是靠头盖压住。',
     notes=['这是 V1.9 正式打印件 head_cap_v19-world.stl（橙色，打印姿态和 V1.8 头盖一样顶面朝下，加 4 mm 外圈 brim）。几何和整合研究的头盖相同，只修了网格：'
            '去掉 39 个零厚度/内部/反向面，补一条 2 面裂缝，体积只变 −0.001 mm³。网格检查全部通过。',
            '外观只变两处：后脑缺口补平，头顶多了出声孔。新加的材料都在壳里面，V1.8 外壳以外新增为 0。',
            '体积 35303.6 mm³（V1.8 是 30676.3 mm³）：加了 5054.9 mm³，去掉 427.6 mm³。',
            '+y 那片加强筋（靠下巴支架一侧）削掉了一点，静止和合盖下落时离下巴支架都 ≥1.05 mm（V1.8 是 1.09 mm）。'],
     src=[S_V19 + '（Parts、Fin check、Connection methods）', S_MAN, 'guide/print/ext-v19/checks/cap-build-v19.json',
          S_INT + '（Verdict、Numbers）', S_GD + '：合盖螺丝'])
item(id='cap_added', name='头盖上新加的材料（高亮）', cls='changed', change='changed', block='cap',
     meshes=[{'src': ('capadded',), 'ccol': CAP_ADDED}],
     role='把 V1.9 头盖里新加的部分单独标出来：扬声器围框和螺丝柱、功放短柱、Pi 立柱的加强筋、后脑缺口的补块。它和头盖是一体打印的，不是单独的零件。',
     fix='和头盖一体打印，没有单独的固定。',
     notes=['合计 5054.9 mm³。头盖勾选"半透明"时最容易看清。',
            '页面里的这块是用 V1.9 头盖减去 V1.8 头盖重新算的。两版重合的面上，布尔运算会留下没有厚度的薄片，显示出来像一根根长刺，这里已经去掉（体积不变）。'],
     src=['guide/print/ext-v19/head_cap_v19-world.stl 减 V1.8 head_cap', 'integrated/cap-build.json'])
item(id='cap_v18', name='V1.8 原头盖（对比用）', cls='v18', change='replaced', block='cap', hidden=True,
     meshes=[{'src': ('v18cap',)}],
     role='V1.8 已发布的头盖，后缘有出线缺口和扎带罩，没有出声孔。V1.9 用新头盖替换它。默认隐藏；要对比时勾上它、关掉"V1.9 头盖"。',
     fix='3 颗 M2.5×8 自攻，从下头壳耳片拧进头盖（和新头盖一样）。',
     src=[S_GD])

# ---- new printed parts
item(id='retainer', name='扬声器压板', cls='newprint', change='new', block='retainer',
     meshes=[{'src': ('stl', v19('speaker_retainer_v19'))}],
     role='一片 1.6 mm 厚的打印框，把扬声器压进头盖的围框，扬声器出声面和头盖之间垫一圈 1 mm 泡棉。',
     fix='2 颗 M2×6 自攻螺丝（H-speaker_retainer-01/02），拧进围框两侧的 2 个螺丝柱（柱径 5.2 mm，在扬声器两侧各 14.6 mm）。咬合 4.1 mm，不用胶，松两颗螺丝就能拆。',
     notes=['V1.9 正式打印件 speaker_retainer_v19-world.stl，588.2 mm³，打印时贴扬声器那面朝下平放。网格检查通过。',
            '装法（头盖倒扣在桌上）：泡棉圈放进围框 → 扬声器出声面朝下放进去，焊盘那头朝功放 → 盖上压板 → 拧 2 颗螺丝。',
            '离偏航连杆最近 4.66 mm（头横滚到最大时），离功放 1.80 mm。'],
     src=[S_V19 + '（Parts、Screws、Connection methods）', S_MAN, S_AUD + '（Recommended layout、Assembly order）'])
item(id='clip_torso', name='躯干线卡扣（S12-horn-025 下）', cls='newprint', change='new', block='neck', noframe=True,
     meshes=[{'src': ('stl', v19('clip_torso_v19'))}],
     role='四个卡扣里最下面的一个，在躯干右壳上，把 8 根线从背包缺口引到脖子根部。它在头以下，本页只画零件本身；勾"显示脖子"能看到它旁边的线。',
     fix='耳片压在躯干舵机盘螺丝 S12-horn-025 的螺帽下面，这颗螺丝从 M2×6 换成 M2×8（咬合 1.8 mm，尖端余量 1.2 mm）。'
         + CLIP_SHAPE + '这个卡扣的线槽比耳片高 1.9 mm，为了避开壳面。',
     notes=['V1.9 打印件 clip_torso_v19-world.stl，229.6 mm³。已定稿：网格检查报的 1 组重合面是两片 2e-5 mm² 的针状面（同法向），文件水密、manifold3d 无错误，按原样发布（sha 见 build-summary.json）。',
            '离 S12-horn-028 螺丝头 0.28 mm。装配顺序：先拧 S12-horn-026/027/028，最后拧 025 和这个卡扣；卡扣会挡住 117、118、028 的直向螺丝刀，要再拧它们得先取下卡扣。',
            CLIP_UNCONFIRMED],
     src=[S_V19 + '（Current state、Parts、Screws、Handoff）', S_MAN, 'guide/print/ext-v19/checks/clips-build-v19.json'])
item(id='clip_bracket', name='俯仰支架线卡扣（S11-horn-040 下）', cls='newprint', change='new', block='neck', noframe=True,
     meshes=[{'src': ('stl', v19('clip_bracket_v19'))}],
     role='第二个卡扣，在头部俯仰支架上、正好在头俯仰轴线上，这样头抬头低头时线不被拉扯。它在头以下，本页只画零件本身。',
     fix='耳片压在 S11-horn-040 的螺帽下面，这颗螺丝从 M2×6 换成 M2×8（咬合 2.6 mm，尖端余量 0.3 mm，和 V1.8 一样）。' + CLIP_SHAPE
         + '槽口四角倒圆 r 2.4，两端倒角 1.5 mm，让线进出时不被棱角磨。',
     notes=['V1.9 打印件 clip_bracket_v19-world.stl，192.3 mm³，网格检查通过。',
            CLIP_UNCONFIRMED],
     src=[S_V19 + '（Parts、Screws）', S_MAN, 'guide/print/ext-v19/checks/clips-build-v19.json'])
item(id='clip_head', name='头部线卡扣（下巴支架上）', cls='newprint', change='new', block='js',
     meshes=[{'src': ('stl', v19('clip_head_v19'))}],
     role='第三个卡扣，在下巴支架上。线从脖子的缝进头、翻过下巴支架的横墙以后，从这个卡扣的槽里往下走，在底板上转个弯，从 +y 侧的窗口出来往上去 Pi。',
     fix='耳片压在下巴支架螺丝 H-jaw_support-03 的螺帽下面，这颗螺丝从 M2.5×6 换成 M2.5×8（有库存；咬合 3.3 mm，尖端余量 5.7 mm）。不开新孔、不加新柱子。' + CLIP_SHAPE,
     notes=['V1.9 打印件 clip_head_v19-world.stl，426.2 mm³，网格检查通过。',
            '它在下头壳这边，掀头盖时不动。',
            CLIP_UNCONFIRMED],
     src=[S_V19 + '（Parts、Screws、Connection methods）', S_MAN, S_R19 + '（clipTies.head）'])
item(id='clip_cap', name='头盖线卡扣（Pi 的 E-pi-04 螺丝下）', cls='newprint', change='new', block='capclip',
     meshes=[{'src': ('stl', v19('clip_cap_v19'))}],
     role='第四个卡扣。线从 Pi 背后上来、翻过 Pi 顶边时从它的槽里经过。卡扣装在 Pi 上，Pi 装在头盖上，所以掀头盖时它跟着头盖走。',
     fix='耳片压在 Pi 的 E-pi-04 螺丝（+y 上角，正面看右上）下面。这颗螺丝定了：从 M2×6 换成 M2×8（耳片 2.0 mm 厚，螺丝尖位置不变；咬合 4.1 mm，尖端余量 1.0 mm）。'
         + CLIP_SHAPE + '线槽沿 Pi 板法线方向，在 y 18 处。',
     notes=['V1.9 打印件 clip_cap_v19-world.stl，251.8 mm³，网格检查通过。',
            f'沿线离头部卡扣 {L_SEG2:.1f} mm。',
            CLIP_UNCONFIRMED],
     src=[S_V19 + '（Parts、Screws、Connection methods）', S_MAN, S_R19 + '（clipTies.cap）'])

# ---- purchased electronics
item(id='amp', name='功放 MAX98357A（Adafruit 3006）', cls='elec', change='new', block='amp', focus=True,
     meshes=[{'src': ('ampdisplay',), 'wcol': WIRING_ELEC['amp']}],
     role='I2S 数字功放：把 Pi 发出的数字音频变成推扬声器的功率信号。从 Pi 的 5 V 取电，脖子里不用多走线。',
     fix='平挂在头顶内侧正中，元件面朝上。2 颗 M2×6 自攻螺丝（H-amplifier-01/02）从下往上，穿过板子的 2 个 Ø2.5 金属化孔，拧进头盖的 2 根 Ø4.0 短柱（咬合 4.15 mm）。不用胶。',
     notes=['模型仍是音频研究的外购件外形，不是打印件。板子位置在 V1.9 里没有变。',
            '你要焊：7 针 90° 弯针排针（插头朝 Pi 方向躺着）、板子背面的 100 kΩ 增益电阻（见单独条目）。2 针 3.5 mm 螺丝端子：2024-06-13 以后出的板子已经预焊，没焊就自己焊上。',
            '先把扬声器引线拧进端子，再装功放：端子螺丝朝上，装好后螺丝刀够不着。',
            '端子高度：Adafruit 链接的 4UCON 19963 图纸是 8.5 mm，装好后离头盖约 2.2 mm。3006 用的就是这款端子{推测}。'
            '模型里端子按 10 mm 估，所以模型上的间隙只有 0.71 mm。',
            'GAIN 通过 100 kΩ 接到 Vin：增益 3 dB（不接是 9 dB）。SD 不接，悬空时左右声道混成单声道{推测}。软件音量上限设 −3 dBFS{推测}。',
            '板子（含螺帽）离偏航连杆最近 2.09 mm（头横滚到最大时）。'],
     src=[S_V19 + '（Screws、Connection methods）', S_AUD + '（Amplifier、Gain and volume、Open items）', S_BENCH, S_HO])
item(id='resistor', name='100 kΩ 增益电阻（焊在功放背面）', cls='elec', change='new', block='amp', focus=True,
     meshes=[{'src': ('resistor', 'sleeve'), 'wcol': '#1b7f3b', 'sub': '电阻本体，外面套 7 mm 热缩管'},
             {'src': ('resistor', 'legs'), 'ccol': '#9aa3ab', 'sub': '两条 0.6 mm 引线，弯成 U 形，末端绕钩'},
             {'src': ('resistor', 'joints'), 'ccol': '#c9ced3', 'sub': '焊点（GAIN、Vin 针尾各一个）'}],
     role='一只 1/4 W 轴向电阻（YAGEO MFR-25FBF52-100K），接在功放排针的 GAIN 和 Vin 两脚之间，把功放增益从默认 9 dB 降到 3 dB，'
          '满幅输出约 0.40 W，配合 −3 dB 软件上限约 0.20 W，保护 1 W 的扬声器；万一焊点开路回到 9 dB 也只有 0.81 W。',
     fix='Shawn 自己焊，装功放之前在桌上焊好。电阻本体（长 6.3 mm、直径 2.4 mm）套一段 7 mm 长的热缩管（收紧后外径约 2.8 mm），'
         '躺在功放板背面（没有元件的那面），和排针那一排平行，离那排针约 3 mm，离板面约 1 mm。'
         '两条 0.6 mm 的腿弯成 U 形，末端各绕成小钩，钩住 GAIN 和 Vin 两根针尾（排针间距 2.54 mm，两针相隔 7.62 mm），在针尾上各焊一个焊点；'
         '最后用一条 Kapton 胶带盖住两条腿、两个钩子和那排针尾。'
         '焊之前单独量电阻应为 99–101 kΩ，焊完查两条腿到针脚导通、和相邻 SD、GND、DIN 针尾没有短路。',
     notes=['本页画的是电阻本身：套热缩管的本体、两条 U 形腿和两个焊点，位置按 resistor-placement.json 的 U4 摆法（本体中心 x 35.76、y 3.81、z 135.78，沿 y 方向）。',
            '排针顺序（从 −y 到 +y）：LRC、BCLK、DIN、GAIN、SD、GND、Vin。GAIN 在 y 0，Vin 在 y 7.62，电阻本体跨在 GAIN 到 Vin 之间，正好在 SD、GND 针尾旁边。',
            '按本页模型：热缩管离 SD、GND 针尾 1.45 mm，两条腿和焊点离 DIN、SD、GND 针尾至少 1.25 mm；腿压歪了就可能碰上，所以要套热缩管、盖 Kapton。',
            '头里的间隙按 4 mm 包络算过（见隐藏条目"电阻安装包络（4 mm，间隙检查用）"）：静止时包络离下巴支架 3.92 mm，头横滚时包络离偏航连杆 2.79 mm。电阻本身比包络小，实际间隙更大。',
            '它跟着功放走：掀头盖、拆功放都不用动它。'],
     src=[S_RES + '（candidates.U4_detail、facts）', S_BENCH + '（gain table、Numbers used on the page）', 'bringup/build/audio-bench/img/underside.png、endview.png', S_V19 + '（Resistor）'])
item(id='resistor_env', name='电阻安装包络（4 mm，间隙检查用）', cls='elec', change='new', block='amp', hidden=True,
     meshes=[{'src': ('stl', v19('resistor_envelope_v19')), 'ccol': '#8ce99a'}],
     role='增益电阻在功放板下面占的空间盒子（resistor_envelope_v19-world.stl）：板下 4.0 mm 厚、沿排针方向 10.0 mm、横向 6.2 mm。它不是零件，'
          '只是做间隙检查时用的保守外形，把电阻、热缩管、腿、焊点和 Kapton 都包在里面。默认隐藏；要对比时勾上它。',
     fix='不是实物，不用装。',
     notes=['用这个包络算的头里间隙：静止时离最近零件（下巴支架）3.918 mm，头横滚时离偏航连杆最近 2.788 mm，都在 0.5 / 0.3 mm 的门槛以上。板下叠高最多可到 6.49 mm{推测}。',
            '包络和功放研究模型重叠 89 mm³：功放模型把排针针尾画到板下 1.5 mm，这些针尾本来就在包络里面，不是碰撞。'],
     src=[S_RES + '（envelopeStl、recommendation.perCandidate.U4_box）', S_V19 + '（Resistor）'])
item(id='speaker', name='扬声器 CMS-30204-18SP', cls='elec', change='new', block='speaker', focus=True,
     meshes=[{'src': ('stl', AUD / 'study-solids' / 'speaker-world.stl'), 'wcol': WIRING_ELEC['speaker']}],
     role='发声。30×20×4.0 mm，8 Ω，额定 1.0 W（最大 1.2 W）。',
     fix='放在头盖内顶靠后，顺着顶面斜 14.3°，出声面朝上对着出声孔。头盖上的围框定位（四周留 0.2 mm），出声面下垫 1.0 mm 闭孔泡棉圈（压到约 0.6 mm），'
         '背面用打印压板 + 2 颗 M2×6 自攻压住。不用胶。',
     notes=['模型仍是音频研究的外购件外形。',
            '泡棉你自己找 1 mm 的，1 mm 泡棉双面胶也可以。剪成 30×20 mm、宽 1.5 mm 的圈。泡棉在本页模型里没有画。',
            '围框只留 0.2 mm 间隙，切片前最好先试打一小块围框。',
            '两根引线焊在扬声器自己的焊盘上（焊点在扬声器上，不在电路板上）。',
            '离偏航连杆最近 7.03 mm。出声孔加前腔的共振约 9.9 kHz，在语音频段以上{推测}（集总模型估算，没实测）。'],
     src=[S_AUD + '（Recommended layout、Grille proposal）', S_V19 + '（Connection methods）', S_HO + '（Decisions、Open items 7）'])
item(id='pi', name='Pi Zero W（含排针）', cls='elec', change='unchanged', block='pi', focus=True,
     meshes=[{'src': ('gdm', 'pi_group'), 'wcol': WIRING_ELEC['pi']}],
     role='头里的主控：跑程序、接摄像头、通过串口和 OpenRB 通信、给功放发 I2S 音频。',
     fix='位置和 V1.8 一样，竖着装在头盖里的两根立柱上（V1.9 立柱加固了）。4 颗螺丝：E-pi-01（−y 下）M2×6 自攻，E-pi-02（+y 下，microSD 那头）M2×4 自攻，'
         'E-pi-03（−y 上）M2×6 自攻，E-pi-04（+y 上）从 M2×6 换成 M2×8，下面压头盖线卡扣。',
     notes=['你断的是 −y 那根立柱（正面看左边），按受力最可能断在下凸台 E-pi-01{推测}。新头盖两根都加固，估计下排能承受约 15–30 N{推测}（原来约 2–3 N）。',
            '新头盖打出来之前先用 3 颗螺丝：插杜邦头时用手指从背后托住板子，螺丝拧到贴紧就停。',
            '排针占用：1、2、3、5、6、8、9、10 号接颈部线束；4、12、34、35、40 号接功放；其余空着。'],
     src=[S_V19 + '（Screws）', S_PIM, S_INT, S_HO])
item(id='camera', name='摄像头板', cls='elec', change='unchanged', block='cam',
     meshes=[{'src': ('gd', 'camera_board')}],
     role='眼睛里的摄像头，排线接到 Pi（排线本页没有画）。',
     fix='2 颗 M2×8 自攻从后面穿过摄像头板和面板，拧进眼圈装饰的底孔。',
     notes=['它属于下头壳这边。颈部线束散开的那一段专门避开了摄像头和面板正下方的区域，这样头盖才能竖直落下。'],
     src=[S_GD + '：camera 步', S_INT])

# ---- wires and connectors
item(id='bundle', name='颈部 8 根线（头里的 V1.9 路线）', cls='wire', change='changed',
     meshes=[
         {'tube': BUNDLE_PTS[I_SLOT:I_HEADCLIP + 1], 'r': BUNDLE_R, 'block': 'js',
          'sub': f'第 1 段：脖子的缝 → 翻过下巴支架横墙 → 头部卡扣的槽（{L_SEG1:.1f} mm）'},
         {'tube': BUNDLE_PTS[I_HEADCLIP:I_CAPCLIP + 1], 'r': BUNDLE_R, 'blocks': ['js', 'pi'],
          'sub': f'第 2 段：头部卡扣窗口 → 头盖卡扣（{L_SEG2:.1f} mm，掀头盖时被拉长的就是这段）'},
         {'tube': BUNDLE_PTS[I_CAPCLIP:I_END + 1], 'r': BUNDLE_R, 'block': 'pi',
          'sub': f'第 3 段：头盖卡扣 → 前下角汇集点（{L_SEG3:.1f} mm，跟头盖走）'}]
     + [{'tube': FAN['polylines'][p], 'r': FAN['radiusMm'], 'block': 'pi', 'sub': f'第 4 段：汇集点散开到 {p} 号针'}
        for p in sorted(FAN['polylines'], key=int)],
     role='躯干到头的 8 根线：Pi 供电 2 根（2 号针 5 V、6 号针 GND）、IMU 4 根（1、3、5、9 号针）、串口 2 根'
          '（8 号针 TXD → OpenRB J12 第 3 脚 Rx，绿线；10 号针 RXD ← J12 第 4 脚 Tx，白线）。不缠螺旋管，平排成一片从脖子里走，不再从后脑出。',
     fix='4 个打印卡扣压住：躯干 S12-horn-025、俯仰支架 S11-horn-040、头里下巴支架 H-jaw_support-03、头盖上 E-pi-04。四个卡扣本页都画了。'
         'Pi 那头是压接的杜邦母头。躯干那头串口 2 根焊进 OpenRB J12（第 3 脚 Rx ← Pi 8 号，第 4 脚 Tx → Pi 10 号）。',
     notes=['头里的走法：从 −y 的缝进头 → 翻过下巴支架的横墙 → 从头部卡扣的槽往下、在底板上转弯、从 +y 窗口出来 → 在 Pi 背后往上走，'
            '从功放插头下面穿过（比研究路线低 1.8 mm，这样排针针脚只高出板子 1.27 mm 的弯排针也不会碰到）→ 在 y 18 处翻过 Pi 顶边，经过头盖卡扣 → 沿 +y 前缘下来 → 前下角汇集点 (77, 27.5, 115.5) 散开。',
            f'整条路线 {L_ALL:.1f} mm（33 个点），头里（缝以上）{L_HEAD:.1f} mm，散开的 8 根各 {FAN_LENS[0]:.1f}–{FAN_LENS[-1]:.1f} mm。',
            '掀头盖时第 2 段要被拉长，至少多留 17 mm 的线；或者先拔掉 Pi 上的插头、把线从头盖卡扣的槽里取出再掀。"拆开"滑块拉到 50% 时能看到这一段被拉长。',
            '线束是 8 根线两层叠着走，画成半径 1.7 mm 的管子{推测}（8 根线合计 12.5 mm²，比 Ø3.4 的圆略大）；散开的每根半径 0.65 mm（26 AWG 硅胶线）。真实的线是软的。',
            '静止检查：线束离周围零件最窄 0.161 mm（折线）/ 0.173 mm（页面画的样条），散开的线 ≥0.364 mm，没有穿进任何零件。'
            '头盖直落 40 mm、走路帧都没有新的碰撞。下巴张开到 40° 不碰头里固定的线。',
            '脖子里那一段（缝以下，经过躯干卡扣和支架卡扣）在"显示脖子"里。'],
     src=[S_R19 + '（routes、fanWires）', S_V19 + '（Routes、Check numbers、Connection methods）', 'guide/print/ext-v19/checks/cable-check-v19.json', S_GD + '：cables'])
BUNDLE_PINS = (1, 2, 3, 5, 6, 8, 9, 10)
item(id='bundle_housings', name='线束的 Pi 端插头（8 个针位）', cls='wire', change='unchanged', block='pi',
     meshes=[{'src': ('gdm', [f'head_pi_gpio_pin_{p:02d}_receiving' for p in BUNDLE_PINS])}],
     role='8 根线在 Pi 那头的杜邦母头，插在 1、2、3、5、6、8、9、10 号针上。',
     fix='插拔。V1.9 定的分组：1×5 外壳插 1、3、5、9（7 号位空着），1×1 插 2，1×3 插 6、8、10。偶数排不能合成一个 1×5，因为 4 号针留给功放。',
     notes=['模型画的是 V1.8 的单针头，位置不变。合成三组时也和功放的插头不重叠。',
            '插这些头要在头盖掀起时插（面板挡住正面），和 V1.8 一样。先插线束的头，再插 4 号、12 号的功放线，比较好插{推测}。'],
     src=[S_V19 + '（Connection methods、Connector insertion）', S_INT + '（Ends of each wire）', 'integrated/housing-blocks.json'])

JUMPERS = [
    ('VIN', 'amp_vin_pin04', 4, '5 V', '功放 VIN ↔ Pi 4 号针（5 V）'),
    ('GND', 'alt_gnd_pin34', 34, 'GND', '功放 GND ↔ Pi 34 号针（GND）'),
    ('BCLK', 'amp_bclk_pin12', 12, 'GPIO18', '功放 BCLK ↔ Pi 12 号针（GPIO18）'),
    ('LRC', 'amp_lrc_pin35', 35, 'GPIO19', '功放 LRC ↔ Pi 35 号针（GPIO19）'),
    ('DIN', 'amp_din_pin40', 40, 'GPIO21', '功放 DIN ↔ Pi 40 号针（GPIO21）'),
]
item(id='jumpers', name='功放 ↔ Pi 杜邦线（5 根）', cls='wire', change='new', focus=True,
     meshes=[{'tube': ROUTES[rk], 'r': 0.7, 'blocks': ['amp', 'pi'], 'wcol': SIG[sig], 'sub': f'{text}，线长 {wire_len(rk)}'}
             for sig, rk, pin, fn, text in JUMPERS],
     role='Pi 给功放的电源和 I2S 数字音频信号。',
     fix='母对母杜邦线，两头都是插的：一头插功放的 7 针弯排针，另一头插 Pi 排针。功放那头要在装 Pi 之前插好（Pi 装上以后只剩 3.5 mm，插不进）。',
     notes=['走法：从功放插头出来，翻过 Pi 顶边，从 Pi 前面下来插到针上。路线和音频研究的一样，V1.9 的 route-v19.json 原样收录。',
            'GND 用 34 号（39 号也行），不用 14 号：14 号在摄像头后面，线要从插头下面钻过去，离下头壳只有 0.70 mm。',
            'BCLK 必须接 12 号针：GPIO18 是 Pi 唯一的 PCM 时钟脚。',
            '线长是模型中心线的长度。现成 10 cm 杜邦线每根会多出 30–50 mm；自己压约 75 mm 的线可以少很多余量。余量怎么收还没检查过。',
            '页面上的颜色只是为了区分，扩展文件没有规定线色。',
            '模型管子半径 0.7 mm，V1.9 静止检查里这些线离周围零件 ≥0.754 mm。'],
     src=[S_R19 + '（audioWires）', S_AUD + '（Amplifier header、Wires）', 'audio/wires.json', S_V19 + '（Check numbers）'])
item(id='pi_audio_housings', name='功放线的 Pi 端插头（4、12、34、35、40 号针）', cls='wire', change='new', block='pi', focus=True,
     meshes=[{'src': ('stl', AUD / 'study-solids' / f'pi_housing_pin{pin:02d}-world.stl'), 'wcol': SIG[sig], 'sub': f'{pin} 号针插头（{sig}）'}
             for sig, _, pin, _, _ in JUMPERS if pin != 34]
            + [{'src': ('stl', AUD / 'study-solids' / 'pi_housing_pin14-world.stl', [0.0, -25.4, 0.0]), 'wcol': SIG['GND'],
                'sub': '34 号针插头（GND）'}],
     role='5 根功放线在 Pi 那头的单针杜邦母头。',
     fix='插拔。',
     notes=['34 号针的插头：音频研究建的是 14 号，整合研究把它沿 y 平移 10 个针距（−25.4 mm）得到 34 号，并做了干涉检查。本页用同样的平移画出来。',
            '这些插头都在 Pi 上，掀头盖时跟着走。'],
     src=[S_AUD, 'integrated/scripts/route_scene.py（pin34_housing）', 'integrated/pairwise-scene.json'])
item(id='amp_housings', name='功放端插头（弯排针一侧）', cls='wire', change='new', block='amp', focus=True,
     meshes=[{'src': ('stl', AUD / 'study-solids' / 'amp_housings-world.stl'), 'wcol': '#495057'}],
     role='5 根杜邦线在功放这头的母头，插在 7 针弯排针上，朝 Pi 方向躺着。',
     fix='插拔。装 Pi 之前先插好。',
     notes=['排针顺序（从 −y 到 +y）：LRC、BCLK、DIN、GAIN、SD、GND、VIN。只插 LRC、BCLK、DIN、GND、VIN；GAIN 和 VIN 的针尾在板背面接增益电阻。',
            '模型外形把 GAIN 的位置也留出来了。插头末端离 Pi 3.47 mm。',
            '音频研究假设排针针脚中心高出板子 4.02 mm；如果用 Sullins 一类只高 1.27 mm 的弯排针，插头会低 2.75 mm，V1.9 的线束路线已经按这种情况留了位置。'],
     src=[S_AUD + '（Amplifier header, housings and mounting）', S_V19 + '（Routes、Check numbers）', 'audio/scripts/build_study.py'])
item(id='spk_leads', name='扬声器引线（2 根）', cls='wire', change='new', focus=True,
     meshes=[{'tube': ROUTES['spk_plus'], 'r': 0.6, 'blocks': ['speaker', 'amp'], 'wcol': SIG['SPK1'], 'sub': '引线（文件里叫 spk_plus）'},
             {'tube': ROUTES['spk_minus'], 'r': 0.6, 'blocks': ['speaker', 'amp'], 'wcol': SIG['SPK2'], 'sub': '引线（文件里叫 spk_minus）'}],
     role='扬声器到功放的两根线。',
     fix='扬声器那头焊在扬声器自己的 2 个焊盘上，从压板缺口出来做应力释放；功放那头剥线（可加冷压头）拧进 2 针 3.5 mm 螺丝端子。'
         '可选在中间加一对 2 针 JST-PH，拆扬声器就不用螺丝刀。',
     notes=['引线留 40–60 mm 长，这样功放拿在头盖外面也能拧端子；多出来的线绕在扬声器焊盘那头和功放之间，具体怎么收还没检查。',
            '模型只画了最短的直线路径（8.5 mm）。',
            '端子哪个口是 +、扬声器哪个焊盘是 +，扩展文件没有记录，按功放板和扬声器上的标记接。'],
     src=[S_R19 + '（audioWires）', S_AUD + '（Every connection method 5–7、Open items）'])
item(id='gnd14', name='备选：GND 走 14 号针', cls='wire', change='alt', hidden=True, focus=True,
     meshes=[{'tube': ROUTES_AUD['amp_gnd_pin14'], 'r': 0.7, 'blocks': ['amp', 'pi'], 'wcol': '#868e96', 'sub': f'GND ↔ Pi 14 号针，线长 {wire_len("amp_gnd_pin14")}'},
             {'src': ('stl', AUD / 'study-solids' / 'pi_housing_pin14-world.stl'), 'block': 'pi', 'wcol': '#868e96', 'sub': '14 号针插头'}],
     role='研究里比较过的另一种接地，V1.9 不用它，默认隐藏。',
     fix='母对母杜邦线，插拔。',
     notes=['线要从摄像头后面、插头下面钻过去，离下头壳 0.70 mm、离摄像头 0.78 mm，还要和 12 号线挤同一条道。V1.9 用 34 号。'],
     src=[S_AUD + '（GND pin choice）', 'audio/wire-routes.json'])

# ---- screws
item(id='spk_screws', name='压板螺丝（2 颗 M2×6 自攻）', cls='screw', change='new', block='spkscrew',
     meshes=[{'src': ('stl', AUD / 'study-solids' / 'speaker_screws_envelope-world.stl')}],
     role='把扬声器压板拧进围框的两个螺丝柱。V1.9 编号 H-speaker_retainer-01/02。',
     fix='M2×6 自攻，拧进 Ø1.7 盲孔，咬合 4.1 mm；螺丝尖到外壁还有 0.6 mm，不会钻穿。',
     notes=['和功放的 2 颗合起来一共新增 4 颗 M2×6 自攻，是 V1.8 里用得最多的规格，不用买新螺丝。'],
     src=[S_V19 + '（Screws）', 'guide/print/ext-v19/checks/screw-engagement-v19.json', S_AUD])
item(id='amp_screws', name='功放螺丝（2 颗 M2×6 自攻）', cls='screw', change='new', block='ampscrew',
     meshes=[{'src': ('stl', AUD / 'study-solids' / 'amp_screws_envelope-world.stl')}],
     role='把功放挂在头盖的两根短柱上。V1.9 编号 H-amplifier-01/02。',
     fix='M2×6 自攻，从下往上穿过功放板孔拧进短柱的 Ø1.7 盲孔，咬合 4.15 mm；螺丝尖到外面还有 1.07 mm。',
     src=[S_V19 + '（Screws）', 'guide/print/ext-v19/checks/screw-engagement-v19.json', S_AUD])
item(id='pi_screws', name='Pi 的 4 颗螺丝', cls='screw', change='changed', block='piscrew',
     meshes=[{'src': ('piscrews',)}],
     role='把 Pi 固定在头盖立柱上，V1.8 原有；V1.9 只把 E-pi-04 加长 2 mm。',
     fix='E-pi-01、E-pi-03 是 M2×6 自攻（咬合 4.1 mm），E-pi-02（+y 下）是 M2×4 自攻（咬合 2.15 mm），E-pi-04（+y 上）从 M2×6 换成 M2×8，下面压 2.0 mm 厚的头盖卡扣耳片，螺丝尖位置不变。',
     notes=['先拧 +y 下角的短 M2×4，再拧另外三颗。立柱底孔 1.7 mm，M2.5 会把它撑裂。',
            'E-pi-04 按 V1.9 画成 M2×8：螺丝头坐在头盖卡扣耳片上，比 V1.8 往外 2.0 mm，螺丝尖位置不变。',
            'V1.9 全机螺丝从 75 颗变 79 颗：M2×6 43→44，M2×8 8→11，M2.5×6 4→3，M2.5×8 3→4。'],
     src=[S_V19 + '（Screws）', 'guide/content/fasteners.json（E-pi-04）', S_PIM, S_GD + '：pi 步'])

# ---- V1.8 unchanged
item(id='head_bottom', name='下头壳', cls='v18', change='unchanged', block='hb',
     meshes=[{'src': ('gd', 'head_bottom')}],
     role='头的下半壳，托住下巴、舵机和面板。',
     fix='下巴支架用 4 颗 M2.5 自攻拧进它的凸台；合盖时 3 颗 M2.5×8 自攻从它的耳片拧进头盖。',
     notes=['V1.9 不改它。新头盖压在它上面的重叠 67.5 mm³（V1.8 是 63.0），多出来的是后脑缺口补平以后的密封带，是有意的。'], src=[S_GD, S_V19 + '（Check numbers）'])
item(id='jaw_support', name='下巴支架', cls='v18', change='unchanged', block='js',
     meshes=[{'src': ('gd', 'jaw_support')}],
     role='压住 ID15 和 ID14 两个舵机，盖住横滚支撑环的上半。',
     fix='4 颗 M2.5 自攻往下拧进下头壳，这 4 颗同时夹住 ID14 和 ID15。其中 H-jaw_support-03 下面要压头部线卡扣，从 M2.5×6 换成 M2.5×8；另外 3 颗仍是 M2.5×6。',
     notes=['线束进头最窄的缝在它和头部偏航叉之间。'], src=[S_GD, S_V19 + '（Screws）'])
item(id='jaw_frame', name='下巴（带下唇）', cls='v18', change='unchanged', block='jaw',
     meshes=[{'src': ('gd', 'jaw_frame')}],
     role='张合的下巴，由 ID15 带动。',
     fix='从下面弹进下头壳（两臂在壳外侧），+Y 臂用 4 颗 M2×6 自攻拧进 ID15 舵盘。',
     notes=['下巴张开会碰脖子：头朝正前方张满 40° 不碰；头一转会碰头部俯仰支架，最紧在偏航 ±60° 左右，张到 26.25° 就碰。'],
     src=[S_GD, S_HO + '（Findings）'])
item(id='mouth_ring', name='嘴部滑动环', cls='v18', change='unchanged', block='mring',
     meshes=[{'src': ('gd', 'mouth_sliding_ring')}],
     role='−Y 侧下巴转轴上的滑动环。',
     fix='推到下巴 −Y 臂内侧的凸台上（宽边朝臂），下巴支架的座落在它上面。', src=[S_GD])
item(id='face_panel', name='眼睛面板', cls='v18', change='unchanged', block='face',
     meshes=[{'src': ('gd', 'face_panel')}],
     role='头的正面白板，摄像头从眼孔往外看。',
     fix='没有螺丝：插进下头壳前部，合盖时被头盖压住。', src=[S_GD])
item(id='eye_trim', name='眼圈装饰', cls='v18', change='unchanged', block='trim',
     meshes=[{'src': ('gd', 'eye_trim')}],
     role='眼孔外圈的黑色装饰件。',
     fix='从前面压进面板的眼孔（紧配合），摄像头的 2 颗 M2×8 拧进它背面的底孔。', src=[S_GD])
item(id='motor15', name='ID15 下巴舵机', cls='v18', change='unchanged', block='m15',
     meshes=[{'src': ('gd', 'motor15'), 'decimate': 9000}],
     role='带动下巴张合。',
     fix='自己没有螺丝：从 +Y 侧滑进下巴支架，下巴支架拧紧后和下头壳一起夹住它。', src=[S_GD])
item(id='motor14', name='ID14 头部横滚舵机', cls='v18', change='unchanged', block='m14',
     meshes=[{'src': ('gd', 'motor14'), 'decimate': 9000}],
     role='让头左右歪（横滚）。',
     fix='自己没有螺丝：偏航叉用 4 颗 M2×6 自攻拧进它的舵盘，下巴支架拧紧后夹住它。', src=[S_GD])
item(id='motor13', name='ID13 头部偏航舵机', cls='v18', change='unchanged', block='m13',
     meshes=[{'src': ('gd', 'motor13'), 'decimate': 9000}],
     role='让头左右转（偏航）。属于脖子，大部分在头里。',
     fix='舵盘朝下，4 颗 M2×6 自攻从俯仰支架下面拧进舵盘；偏航叉用 4 颗 M2×10 自攻拧进它的外壳四角。', src=[S_GD])
item(id='yaw_link', name='头部偏航叉（偏航到横滚的连杆）', cls='v18', change='unchanged', block='yaw',
     meshes=[{'src': ('gd', 'head_yaw_link')}],
     role='连接 ID13（偏航）和 ID14（横滚）。',
     fix='4 颗 M2×10 自攻拧进 ID13 外壳四角；4 颗 M2×6 自攻穿过叉臂拧进 ID14 舵盘。',
     notes=['线束进头的缝在它旁边。增益电阻包络在头横滚时离它最近 2.79 mm。'], src=[S_GD, S_RES])
item(id='roll_rings', name='头部横滚支撑环（2 个）', cls='v18', change='unchanged', block=None,
     meshes=[{'src': ('gd', 'head_roll_ring_a'), 'block': 'ringa', 'decimate': 4000, 'sub': '后环'},
             {'src': ('gd', 'head_roll_ring_b'), 'block': 'ringb', 'decimate': 4000, 'sub': '前环'}],
     role='在横滚轴两侧托住头。',
     fix='松套在偏航叉的凸台上：下头壳托住下半，下巴支架盖住上半。', src=[S_GD])

# ---- neck context (toggle)
NECK_KEYS = ['neck_pitch', 'neck_pitch_ring', 'motor11', 'motor12', 'neck_link_a', 'neck_link_b', 'idler11', 'idler12',
             'idler_cap11', 'idler_cap12', 'shell_left', 'shell_right']
item(id='neck_ctx', name='脖子和躯干壳（背景）', cls='context', change='unchanged', block='neck', hidden=True, context=True,
     meshes=[{'src': ('gd', k), 'decimate': 6000 if k.startswith(('motor', 'idler', 'neck_pitch_ring', 'shell')) else None} for k in NECK_KEYS],
     role='头部俯仰支架、ID11、ID12、脖子侧连杆和躯干两片壳，只作位置参考：躯干卡扣坐在右壳上，支架卡扣坐在俯仰支架上。',
     fix='V1.8 原样，本页不展开。', src=[S_GD])
item(id='neck_route', name='脖子里的线（V1.9 路线，缝以下）', cls='context', change='changed', hidden=True, context=True,
     meshes=[{'tube': BUNDLE_PTS[:I_SLOT + 1], 'r': BUNDLE_R, 'blocks': ['neck', 'js'],
              'sub': f'背包缺口 → 躯干卡扣 → 沿脖子 −y 侧 → 支架卡扣 → 头底的缝（{poly_len(BUNDLE_PTS[:I_SLOT + 1]):.1f} mm）'}],
     role='8 根线在头以下的走法：从背包缺口出来，经躯干右壳上的躯干卡扣，沿脖子 −y 侧上去，穿过俯仰轴线上的支架卡扣，到头底的缝。ID11 外壳上原计划的扎带取消了。',
     fix='躯干卡扣 S12-horn-025、支架卡扣 S11-horn-040，两颗螺丝都从 M2×6 换成 M2×8。',
     notes=['这里画的是 route-v19.json 的路线中心线连成的管子，只示意位置。',
            '线的余量：策略动作需要 18.5 mm，抓取 12.8 mm，走路 11.4 mm。'],
     src=[S_R19 + '（routes.points 0–9）', S_V19 + '（Routes、Route slack）'])

PI_GROUP_EXCLUDE = {f'head_pi_gpio_pin_{p:02d}_receiving' for p in range(1, 41)}

# Labels drawn in the wiring view: Pi ends of the jumpers, and the amp, terminal and speaker.
LABELS = [{'text': f'{pin} 号针 · {fn} → {sig}', 'at': ROUTES[rk][-1], 'block': 'pi', 'color': SIG[sig]}
          for sig, rk, pin, fn, _ in JUMPERS]
LABELS += [
    {'text': '功放排针（LRC BCLK DIN GAIN SD GND VIN）', 'at': [56.53, 0.0, 143.82], 'block': 'amp', 'color': '#495057'},
    {'text': '功放螺丝端子 ← 扬声器引线', 'at': [21.75, 0.0, 142.8], 'block': 'amp', 'color': SIG['SPK1']},
    {'text': '扬声器焊盘', 'at': [16.56, 0.0, 142.92], 'block': 'speaker', 'color': SIG['SPK2']},
]

WIRING = {
    'jumpers': [{'sig': sig, 'color': SIG[sig], 'pin': pin, 'fn': fn, 'text': text, 'len': wire_len(rk)} for sig, rk, pin, fn, text in JUMPERS],
    'headerOrder': ['LRC', 'BCLK', 'DIN', 'GAIN', 'SD', 'GND', 'VIN'],
    'resistorPins': ['GAIN', 'VIN'],
    'spk': [{'color': SIG['SPK1'], 'name': 'spk_plus'}, {'color': SIG['SPK2'], 'name': 'spk_minus'}],
}

VIEWS = {'home': [1.0, -0.95, 0.75], 'front': [1.0, 0.0, 0.16], 'side': [0.0, -1.0, 0.12], 'top': [0.02, 0.0, 1.0],
         'rear': [-1.0, 0.8, 0.85], 'wiring': [0.95, 0.55, 0.9]}


# --------------------------------------------------------------------------- geometry

def guide_parts() -> dict:
    data = json.loads((GUIDE / 'data' / 'guide-data.json').read_text())
    return {p['key']: p for p in data['parts']}


def gd_mesh(p: dict) -> trimesh.Trimesh:
    v = np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3).astype(np.float64)
    f = np.frombuffer(base64.b64decode(p['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
    return trimesh.Trimesh(v, f, process=False)


def prep(tm: trimesh.Trimesh, target: int | None) -> tuple[np.ndarray, np.ndarray, int]:
    tm = trimesh.Trimesh(tm.vertices, tm.faces, process=True)
    tm.update_faces(tm.nondegenerate_faces())
    tm.remove_unreferenced_vertices()
    src_tris = len(tm.faces)
    if target and len(tm.faces) > target:
        tm = tm.simplify_quadric_decimation(face_count=target)
    sm = trimesh.graph.smooth_shade(tm, angle=np.radians(CREASE_DEG))
    return np.asarray(sm.vertices, np.float32), np.asarray(sm.faces, np.int64), src_tris


def cap_added_mesh(gp: dict) -> trimesh.Trimesh:
    """V1.9 release cap minus the V1.8 cap, recomputed with manifold3d.

    Where the two caps share a surface, the boolean leaves zero-volume "pancake" fins: pairs of coincident faces with
    opposite normals that span the cavity and render as long blades. A face is kept only when a point 0.02 mm behind
    it (against its normal) lies inside the V1.9 cap and outside the V1.8 cap, i.e. inside the added material.
    Fin faces have nothing behind them and are dropped. The volume is taken from the boolean, before face cleanup."""
    import manifold3d as m3

    def man(tm):
        tm = trimesh.Trimesh(tm.vertices, tm.faces, process=True)
        M = m3.Manifold(m3.Mesh(vert_properties=np.ascontiguousarray(tm.vertices, np.float32),
                                tri_verts=np.ascontiguousarray(tm.faces, np.uint32)))
        if M.status() != m3.Error.NoError:
            raise SystemExit(f'cap-added: input is not a manifold ({M.status()})')
        return M

    cap_i = man(trimesh.load(V19_USED['head_cap_v19'], force='mesh'))
    cap_v18 = man(trimesh.load(V18_CAP, force='mesh'))
    M = cap_i - cap_v18
    mm = M.to_mesh()
    tm = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts), process=False)
    far = [500.0, 431.0, 977.0]  # irregular far point so parity rays avoid mesh edges

    def inside(Ms, p):
        return len(Ms.ray_cast(p, far)) % 2 == 1

    behind = tm.triangles_center - 0.02 * tm.face_normals
    keep = np.array([inside(cap_i, q) and not inside(cap_v18, q) for q in behind.tolist()])
    out = trimesh.Trimesh(tm.vertices, tm.faces[keep], process=False)
    out.remove_unreferenced_vertices()
    CAP_ADDED_STATS.update(volumeMm3=round(M.volume(), 2), faces=int(len(tm.faces)), finFacesDropped=int((~keep).sum()),
                           finAreaMm2=round(float(tm.area_faces[~keep].sum()), 1))
    return out


CAP_ADDED_STATS: dict = {}


def poly_param(points: np.ndarray, poly: list, a: list, b: list) -> np.ndarray:
    """Weight 0..1 per point: arc-length position of its nearest polyline point between the points nearest a and b."""
    P = np.asarray(poly, float)
    seg = P[1:] - P[:-1]
    L = np.linalg.norm(seg, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(L)])

    def s_of(q):
        q = np.atleast_2d(q)
        d = q[:, None, :] - P[None, :-1, :]
        t = np.clip((d * seg[None]).sum(-1) / np.maximum(L ** 2, 1e-9)[None], 0, 1)
        near = P[None, :-1, :] + t[..., None] * seg[None]
        dist = np.linalg.norm(q[:, None, :] - near, axis=-1)
        k = dist.argmin(1)
        return cum[k] + t[np.arange(len(q)), k] * L[k]

    s0, s1 = float(s_of(np.array(a))[0]), float(s_of(np.array(b))[0])
    return np.clip((s_of(points) - s0) / (s1 - s0), 0.0, 1.0)


class Blob:
    def __init__(self) -> None:
        self.buf = bytearray()

    def add(self, arr: np.ndarray) -> list:
        raw = arr.tobytes()
        off = len(self.buf)
        self.buf += raw
        self.buf += b'\0' * ((-len(self.buf)) % 4)
        return [off, int(arr.size)]


def build_geometry() -> tuple[list, list, bytes, dict]:
    gp = guide_parts()
    pi_group = sorted(k for k in gp if (k == 'pi' or k.startswith('head_pi_')) and k not in PI_GROUP_EXCLUDE)
    blob = Blob()
    meshes, items_out = [], []
    stats = {'triangles': 0, 'sourceTriangles': 0, 'meshes': 0}
    for it in ITEMS:
        ids = []
        for m in it['meshes']:
            rec = {'item': it['id']}
            for k in ('sub', 'wcol', 'ccol', 'color'):
                if m.get(k):
                    rec[k] = m[k]
            if 'blocks' in m:
                rec['blocks'] = m['blocks']
            else:
                rec['block'] = m.get('block', it.get('block'))
            if 'tube' in m:
                rec['tube'] = [[round(float(c), 3) for c in p] for p in m['tube']]
                rec['r'] = m['r']
            else:
                src = m['src']
                if src[0] == 'gd':
                    tm = gd_mesh(gp[src[1]])
                    rec.setdefault('color', gp[src[1]]['color'])
                elif src[0] == 'capadded':
                    tm = cap_added_mesh(gp)
                elif src[0] == 'resistor':
                    tm = resistor_parts()[src[1]]
                elif src[0] == 'piscrews':
                    tm = pi_screws_v19()
                elif src[0] == 'ampdisplay':
                    tm = amp_display_mesh()
                elif src[0] == 'v18cap':
                    tm = trimesh.load(V18_CAP, force='mesh')
                    rec.setdefault('color', gp['head_cap']['color'])
                elif src[0] == 'gdm':
                    keys = pi_group if src[1] == 'pi_group' else src[1]
                    tm = trimesh.util.concatenate([gd_mesh(gp[k]) for k in keys])
                    rec.setdefault('color', gp[keys[0]]['color'])
                else:
                    tm = trimesh.load(src[1], force='mesh')
                    if len(src) > 2:
                        tm.apply_translation(src[2])
                v, f, n_src = prep(tm, m.get('decimate'))
                ib = 2 if len(v) < 65536 else 4
                rec['pos'] = blob.add(v.reshape(-1))
                rec['idx'] = blob.add(f.reshape(-1).astype(np.uint16 if ib == 2 else np.uint32)) + [ib]
                if 'weight' in m:
                    w = poly_param(v.astype(float), m['weight']['poly'], m['weight']['from'], m['weight']['to'])
                    rec['w'] = blob.add(np.round(w * 255).astype(np.uint8))
                stats['triangles'] += len(f)
                stats['sourceTriangles'] += n_src
            stats['meshes'] += 1
            ids.append(len(meshes))
            meshes.append(rec)
        out = {k: it[k] for k in ('id', 'name', 'cls', 'change', 'role', 'fix', 'notes', 'src', 'hidden', 'focus', 'noframe')}
        out['context'] = bool(it.get('context'))
        out['meshes'] = ids
        items_out.append(out)
    return items_out, meshes, bytes(blob.buf), stats


def alignment_summary() -> list[str]:
    path = HERE / 'alignment.json'
    if not path.is_file():
        return ['还没有运行 check_alignment.py，本页没有对齐检查结果。']
    c = json.loads(path.read_text())['checks']
    fr, ins, gr, se, cl = c['frame'], c['insideCap'], c['grilleOverSpeaker'], c['seats'], c['clipSeats']
    ok_inside = all(r.get('allVerticesInsideCapHull') and abs(r.get('overlapMm3', 1)) < 0.01 for r in ins.values())
    clips_ok = all(abs(r.get('overlapMm3', 1)) < 0.01 for r in cl.values())
    clip_gaps = '、'.join(f"{r['label']} {r['minGapMm']:.2f}" for r in cl.values())
    return [
        f"V1.9 头盖和 V1.8 头盖相比：多 {fr['addedMm3']:.1f} mm³、少 {fr['removedMm3']:.1f} mm³，和研究记录（{fr['recordedAddedMm3']:.1f} / {fr['recordedRemovedMm3']:.1f}）"
        f"{'一致，两套模型在同一坐标系里' if fr['matchesRecord'] else '不一致，请检查坐标'}。",
        f"功放、增益电阻、扬声器、压板、功放插头都在头盖里面，和头盖重叠 {'为 0' if ok_inside else '不为 0，请检查'}；扬声器离围框 {ins['speaker']['minGapMm']:.1f} mm。",
        f"从扬声器出声面往外打 {gr['raysFromSpeakerFace']} 条线：{gr['escapeIntegratedCap']} 条穿过新头盖的出声孔出去，V1.8 头盖挡住 {gr['raysFromSpeakerFace'] - gr['escapeV18Cap']} 条。",
        f"新头盖压在下头壳上的重叠 {se['cap_on_head_bottom']['overlapMm3']:.1f} mm³，就是记录里的两条 0.2 mm 密封带（67.5 mm³）。"
        f"Pi 贴在新立柱上（间隙 {se['pi_on_rails']['minGapMm']:.3f} mm），功放线插头都套在对应的排针上。",
        res_line(c),
        f"四个卡扣坐在各自的螺丝座上，和座零件重叠 {'为 0' if clips_ok else '不为 0，请检查'}，间隙（mm）：{clip_gaps}。",
    ]


def res_line(c: dict) -> str:
    r = c.get('resistorPart')
    if not r:
        return '增益电阻实物模型还没有检查结果，请重新运行 check_alignment.py。'
    rows = [v for part in ('body', 'sleeve', 'legs', 'joints') for k, v in r[part].items() if k != 'amplifier']
    clear = all(abs(v.get('overlapMm3', 1)) < 0.01 for v in rows)
    sl = r['sleeve']
    hous = min(v['minGapMm'] for k, v in sl.items() if 'housing' in k)
    tails = min(v['minGapMm'] for d in r['neighbourTails'].values() for v in d.values())
    return (f"增益电阻（本体、热缩管、腿、焊点）和头盖、Pi、插头都不重叠{'' if clear else '——有重叠，请检查'}：热缩管离头盖 {sl['head_cap_v19']['minGapMm']:.1f} mm、"
            f"离插头 {hous:.1f} mm、离 Pi 超过 {sl['pi']['minGapMm']:.0f} mm；热缩管离功放板面 {r['sleeveToBoardUndersideMm']:.2f} mm，腿和焊点离相邻针尾至少 {tails:.2f} mm。")


def gzip_b64(raw: bytes) -> str:
    packed = gzip.compress(raw, compresslevel=9, mtime=0)
    if gzip.decompress(packed) != raw:
        raise SystemExit('gzip readback differs')
    return base64.b64encode(packed).decode('ascii')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out', type=Path, default=HERE / 'HEAD-3D.html')
    ap.add_argument('--manifest', type=Path, default=HERE / 'build-summary.json')
    args = ap.parse_args(argv)

    v19_sources = verify_v19()
    items, meshes, blob, stats = build_geometry()
    data = {
        'title': 'MicroDuck 头部 V1.9 拓展版 3D 拆解',
        'built': dt.date.today().isoformat(),
        'classes': CLASSES, 'changes': CHANGES, 'blocks': BLOCKS, 'lift': LIFT,
        'items': items, 'meshes': meshes, 'labels': LABELS, 'wiring': WIRING, 'views': VIEWS,
        'alignment': alignment_summary(), 'capAdded': CAP_ADDED,
    }
    data_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    if '</' in data_json:
        data_json = data_json.replace('</', '<\\/')
    geo_b64 = gzip_b64(blob)
    three_js, orbit_js = load_three(DEFAULT_THREE)
    app_js = script_safe((SRC / 'app.js').read_text(encoding='utf-8'), 'app.js')
    css = (SRC / 'style.css').read_text(encoding='utf-8')
    tpl = (SRC / 'template.html').read_text(encoding='utf-8')
    for marker in ('/*__STYLE__*/', '<!--__SCRIPTS__-->', '__BUILD__'):
        if tpl.count(marker) != 1:
            raise SystemExit(f'template.html: marker {marker} must appear exactly once')
    sha = hashlib.sha256(blob).hexdigest()[:16]
    build_info = f'built={data["built"]}; three=0.164.1; meshes={stats["meshes"]}; triangles={stats["triangles"]}; geometry-sha256={sha}'
    head, tail = tpl.replace('__BUILD__', build_info).split('<!--__SCRIPTS__-->')
    head = head.replace('/*__STYLE__*/', css)
    tmp = args.out.with_name(args.out.name + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        f.write(head)
        f.write('<script>\n' + three_js + orbit_js + '</script>\n')
        f.write('<script type="application/json" id="head-data">' + data_json + '</script>\n')
        f.write('<script type="application/octet-stream" id="head-geometry" data-encoding="gzip+base64">' + geo_b64 + '</script>\n')
        f.write('<script>\n' + app_js + '\n</script>\n')
        f.write(tail)
    tmp.replace(args.out)
    summary = {'out': str(args.out), 'outBytes': args.out.stat().st_size, 'geometryBytes': len(blob),
               'geometryEmbeddedBytes': len(geo_b64), 'items': len(items), **stats, 'capAdded': CAP_ADDED_STATS,
               'piScrewV19': PI_SCREW_STATS, 'resistorPart': {'placement': 'resistor-placement.json candidates.U4_detail', 'bodyCentre': RES_REC['bodyCentre'],
                                                              'bodyMm': [RES_BODY_L, RES_BODY_D], 'sleeveMm': [RES_SLEEVE_L, RES_SLEEVE_D], 'leadDiameterMm': RES_LEAD_D},
               'v19Sources': v19_sources, 'route': {'file': str(V19 / 'route-v19.json'), 'points': len(BUNDLE_PTS),
                                                    'lengthMm': round(L_ALL, 1), 'inHeadMm': round(L_HEAD, 1)},
               'parts': [{'id': it['id'], 'name': it['name'], 'class': it['cls'], 'change': it['change'], 'hiddenByDefault': it['hidden']}
                         for it in items]}
    args.manifest.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'parts'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
