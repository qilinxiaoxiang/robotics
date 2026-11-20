#!/usr/bin/env python3
"""Flight-pack assembly guide (Chinese): writes guide-data.json for the shared guide-kit viewer.

    /tmp/microduck-cad-venv/bin/python microduck-sim/extensions/flight-20261110/guide/build_flight_guide.py
    python3 guide-kit/build_guide.py --data microduck-sim/extensions/flight-20261110/guide/guide-data.json \
        --out microduck-sim/extensions/flight-20261110/guide/dist/FLIGHT-PACK-BUILD.html

Sources, all read, none written:
- cad/build/*-world.stl (printed parts and bought-part dummies), cad/build/screws.json, cad/build-access/*.stl (the duck as
  built, battery backpack already moved to its place behind the wing centre), cad/checks/lead_lengths.json (routes and cut
  lengths), cad/build_pack.py constants (ESC and FC boxes of the stack dummy);
- wiring/build_wiring.py (wiring-kit benches with the makers' board pictures, netlist, current lead lengths);
- ../../CURRENT-STATE.json fact parts_flight_pack (what is carted, ordered or in hand);
- cad/slices/release-FlightPack-D1/ (print times, only when the slice manifest matches the current STLs).
The page is a separate guide: the MicroDuck guide (guide/data/guide-data.json) is not touched.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
FLIGHT = HERE.parent
CAD = FLIGHT / 'cad'
B = CAD / 'build'
SIM = FLIGHT.parents[1]
WORLD = SIM / 'guide' / 'print' / 'world'
STATE = SIM / 'CURRENT-STATE.json'
REL = CAD / 'slices' / 'release-FlightPack-D1'
OUT = HERE / 'guide-data.json'

sys.path.insert(0, str(CAD))
sys.path.insert(0, str(FLIGHT / 'wiring'))
import build_pack as BP        # noqa: E402  constants only (FCB_X, FC_BOSS, FC_CENTRE, STACK)
import check_parts as CP       # noqa: E402  BACKPACK, BACKPACK_SHIFT (the backpack's flight pose, as the CAD checks place it)
import flight_params as Pm     # noqa: E402
import build_wiring as W       # noqa: E402  benches, netlist, FAN_LEN / BAT_LEN from lead_lengths.json
sys.path.insert(0, str(HERE))
import bench_figures as BF     # noqa: E402  SVG cut list (to scale) and bullet-soldering figure for the bench steps

LL = json.loads((CAD / 'checks' / 'lead_lengths.json').read_text())
SCREWS = json.loads((B / 'screws.json').read_text())
PARTS_STATE = json.loads(STATE.read_text())['facts']['parts_flight_pack']['value']

ORANGE, BLACK = '#ef7d22', '#3b3d42'
GREEN, RED = '#2e9e5b', '#d64545'


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------- parts
PARTS: dict[str, dict] = {}


def add_part(key, name, color, module, status, mesh: trimesh.Trimesh, kit=None):
    assert mesh.is_watertight, f'{key}: mesh not closed'
    v = np.asarray(mesh.vertices, dtype='<f4')
    f = np.asarray(mesh.faces, dtype='<u4')
    p = dict(key=key, name=name, color=color, module=module, status=status,
             positionB64=base64.b64encode(v.tobytes()).decode(), indexB64=base64.b64encode(f.tobytes()).decode(),
             bounds=[[round(float(x), 3) for x in mesh.bounds[0]], [round(float(x), 3) for x in mesh.bounds[1]]])
    if kit:
        p['kit'] = kit
    PARTS[key] = p


def stl(path: Path) -> trimesh.Trimesh:
    return trimesh.load(path, force='mesh')


def box(lo, hi) -> trimesh.Trimesh:
    lo, hi = np.array(lo, float), np.array(hi, float)
    m = trimesh.creation.box(extents=hi - lo)
    m.apply_translation((lo + hi) / 2)
    return m


PRINTED = [  # key, name, plate colour
    ('wing_plate', '翼板（橙色，一整块，中间夹在 OpenRB 盒子和背包之间，左右伸出两条臂）', ORANGE),
    ('tray_L', '左电池托盘（橙色平板，带两对绑带槽）', ORANGE),
    ('tray_R', '右电池托盘（橙色平板，带两对绑带槽）', ORANGE),
    ('fc_bracket', '飞控支架（橙色竖板，四个圆柱凸台，下面带一个小平台）', ORANGE),
    ('nacelle_inner_L', '左机舱内半（黑色，带往里伸的方块耳朵）', BLACK),
    ('nacelle_outer_L', '左机舱外半（黑色，外侧有五个沉孔）', BLACK),
    ('nacelle_inner_R', '右机舱内半（黑色，带往里伸的方块耳朵）', BLACK),
    ('nacelle_outer_R', '右机舱外半（黑色，外侧有五个沉孔）', BLACK),
]
for key, name, col in PRINTED:
    add_part(key, name, col, 'flight-printed', 'new-print', stl(B / f'{key}-world.stl'))

# fans: left-front and right-rear turn clockwise seen from above (green motor, sold as "CW"), the other two counterclockwise
FANS = {'fan_FL': ('front_L', '左前风扇（绿色电机，CW）', GREEN), 'fan_RL': ('rear_L', '左后风扇（红色电机，CCW）', RED),
        'fan_FR': ('front_R', '右前风扇（红色电机，CCW）', RED), 'fan_RR': ('rear_R', '右后风扇（绿色电机，CW）', GREEN)}
for key, (dummy, name, col) in FANS.items():
    add_part(key, name, col, 'flight-fans', 'purchased', stl(B / f'dummy_fan_{dummy}-world.stl'),
             kit='ARESWEI HDS001 绿色电机（CW）' if col == GREEN else 'ARESWEI HDS001 红色电机（CCW）')

# stack: the ESC and FC envelopes of build_pack.dummies()["fc_esc_stack"], kept as two parts so they go on one at a time
x0 = BP.FCB_X[0] - BP.FC_BOSS
yc, zc = BP.FC_CENTRE
st = BP.STACK
xe0 = x0 - 6.0
xe1 = xe0 - st['esc_h']
xf0 = xe0 - st['esc_pcb'] - st['spacer'] + st['fc_under']
xf1 = xf0 - st['fc_h']
add_part('esc', 'MicoAir 55A 四合一电调（堆叠下层，电池片朝上）', '#30343a', 'flight-electronics', 'purchased',
         box((xe1, yc - 20.5, zc - 20.5), (xe0, yc + 20.5, zc + 20.5)))
fc_mesh = trimesh.util.concatenate([box((xf1, yc - 18.0, zc - 18.0), (xf0, yc + 18.0, zc + 18.0))])
add_part('fc', 'MicoAir743v2 飞控（堆叠上层）', '#1f5fbf', 'flight-electronics', 'purchased', fc_mesh)
add_part('mtf01', 'MTF-01 光流模块（小方块，镜头朝下）', '#6b4fa0', 'flight-electronics', 'purchased', stl(B / 'dummy_mtf01-world.stl'))
add_part('capacitor', '1000 µF 电容（圆柱，躺在右臂顶上）', '#24324a', 'flight-electronics', 'purchased', stl(B / 'dummy_esc_capacitor-world.stl'))
# the foam tape strip under the capacitor (cad build_pack dummies cap_tape; the D1 tie slots cannot take a tie, features.json cap_slots)
add_part('cap_tape', '1 mm 双面泡棉胶条（电容底下）', '#f2efe6', 'flight-electronics', 'owned', stl(B / 'dummy_cap_tape-world.stl'))
add_part('battery_L', '左 4S 电池（CNHL 1300）', '#4a5560', 'flight-batteries', 'purchased', stl(B / 'dummy_battery_L-world.stl'), kit='CNHL 4S 1300 电池')
add_part('battery_R', '右 4S 电池（CNHL 1300）', '#4a5560', 'flight-batteries', 'purchased', stl(B / 'dummy_battery_R-world.stl'), kit='CNHL 4S 1300 电池')

# the duck as built (backpack in its new place 6.9 mm further back, as check_parts.py / make_access_spec.py place it)
DUCK = [
    ('rear_pack', 'OpenRB 盒子（躯干后面的黑盒）'), ('shell_left', '左侧壳'), ('shell_right', '右侧壳'),
    ('saddle_body', 'A7Z 座（躯干顶上）'), ('sd_a7z_pcb', 'A7Z 板'), ('sd_heatsink_6530b', 'A7Z 散热器'),
    ('sd_dupont_housings', 'A7Z 排针上的杜邦头'),
    ('battery_backpack_frame', '电池背包外框'), ('battery_backpack_cap', '电池背包后盖'),
    ('battery_backpack_bars', '背包里压电池的两根横条'), ('battery_hatch', '背包顶上的舱盖'), ('bp_battery', '鸭子自己的 2S 电池'),
    ('bp_dfr1202', '背包里的 DFR1202 板'), ('bp_switch', '背包底下的开关'), ('bp_plugs', '背包顶上的插头 1'),
    ('bp_plug2', '背包里的插头 2'), ('bp_swap_plugs', '插头 3、4（OpenRB 盒子线槽里）'),
    ('head_bottom', '头的下壳'), ('head_cap', '头盖'),
]
BACKPACK_BODY = ['battery_backpack_cap', 'battery_backpack_bars', 'battery_hatch', 'bp_battery', 'bp_plugs']
for key, name in DUCK:
    m = stl(WORLD / f'{key}.stl')
    if (key + '.').startswith(CP.BACKPACK):      # the backpack group sits CP.BACKPACK_SHIFT forward of its Dual Lock world pose
        m.apply_translation([CP.BACKPACK_SHIFT, 0, 0])
    add_part(key, name, '#c9ced6' if not key.startswith(('bp_', 'battery_')) else '#9fb3c8', 'duck', 'assembled', m)

DUCK_ALL = [k for k, _ in DUCK]

DUCK_CTX = ['rear_pack', 'shell_left', 'shell_right', 'saddle_body', 'head_bottom']
FLIGHT_FRAME = ['wing_plate', 'fc_bracket', 'mtf01', 'esc', 'fc', 'cap_tape', 'capacitor']


# ---------------------------------------------------------------------------------------------- screws
def screw_spec(s):
    sp = s['spec']
    if sp.startswith('M2 x 12 (with M2 washer)'):
        return 'M2 × 12 内六角 + M2 垫片', 'tap', 12.0, 'M2 垫片'
    if sp.startswith('M2 x 12'):
        return 'M2 × 12 内六角', 'machine', 12.0, None
    if sp.startswith('M3 x 6 male-female'):
        return 'M3 × 6 金属公母柱', 'machine', 12.0, None
    if sp.startswith('M3 x 8 male-female'):
        return 'M3 × 8 金属公母隔离柱', 'machine', 14.0, None
    if sp.startswith('M3 x 8 metal screw'):
        return 'M3 × 8 螺丝', 'machine', 8.0, None
    m = re.match(r'(M[23]) x (\d+)$', sp)
    assert m, sp
    return f'{m.group(1)} × {m.group(2)}', 'tap', float(m.group(2)), None


WHERE = {
    'post': '穿过背包前板和翼板中间，拧进 OpenRB 盒子的柱子',
    'tray': '从臂后面穿过臂板，拧进托盘的竖边',
    'nac': '从机舱外半的沉孔拧进内半',
    'lug': '从臂后面穿过臂板，拧进机舱内半的方块耳朵',
    'fcb': '从支架背面穿过，拧进右臂的四个凸台',
    'fc-standoff': '公头拧进支架的凸台（先手拧，再用 5.5 mm 扳手或尖嘴钳拧紧）',
    'esc-fc-spacer': '公头穿过电调的孔，拧进下面的金属柱（5.5 mm 扳手或尖嘴钳）',
    'fc-screw': '穿过飞控的胶圈孔，拧进隔离柱（拧到飞控不晃就停）',
    'mtf': '从下往上穿过光流的孔，拧进小平台',
}
STEP_OF = {}   # filled from the step list: screws.json step name -> guide step id
SCREW_LIST = []


def screws_for(step_name, step_id, ids=None):
    out = []
    for s in SCREWS:
        if s['step'] != step_name or (ids and not any(s['id'].startswith(i) for i in ids)):
            continue
        spec, kind, length, washer = screw_spec(s)
        prefix = s['id'].rsplit('-', 1)[0]
        prefix = prefix if prefix in WHERE else prefix.split('-')[0]
        e = dict(step=step_id, spec=spec, kind=kind, center=s['seat'], axis=s['axis'], diameterMm=3.0 if spec.startswith('M3') else 2.0,
                 lengthMm=length, where=WHERE[prefix], id=s['id'])
        if washer:
            e['washer'] = washer
        out.append(e)
    assert out, (step_name, ids)
    SCREW_LIST.extend(out)
    return out


# ---------------------------------------------------------------------------------------------- cables (routes from lead_lengths.json)
CABLES = []


def cable(cid, label, kind, color, pts, radius, length=None, note=None, frm='', to=''):
    c = dict(id=cid, label=label, kind=kind, color=color, radius=radius, path=[[round(float(a), 2) for a in p] for p in pts],
             **({'from': frm, 'to': to}))
    if length:
        c['lengthMM'] = length
    if note:
        c['note'] = note
    CABLES.append(c)


L = LL['leads']
cable('c-batL', f'左电池尾线（红黑 12 AWG，{W.BAT_LEN["L"]["pigtail_mm"]} mm）', 'power-20v', '#c62828', L['battery L']['pts'], 2.4,
      W.BAT_LEN['L']['pigtail_mm'], frm='左电池 XT60', to='电调电池片')
cable('c-batR', f'右电池尾线（红黑 12 AWG，{W.BAT_LEN["R"]["pigtail_mm"]} mm）', 'power-20v', '#c62828', L['battery R']['pts'], 2.4,
      W.BAT_LEN['R']['pigtail_mm'], frm='右电池 XT60', to='电调电池片')
for nm, zh in (('FL', '左前'), ('RL', '左后'), ('FR', '右前'), ('RR', '右后')):
    cable(f'c-{nm}', f'{zh}风扇线（红黄黑 16 AWG，{W.FAN_LEN[nm]["ext_mm"]} mm，加风扇自带线）', 'power-15v', '#c99a00',
          L[f'fan {nm}']['pts'], 2.2, W.FAN_LEN[nm]['ext_mm'], frm='电调焊盘', to=f'{zh}风扇子弹头')
# lead_lengths.json needs 170 mm; the kit's only SH-to-female-Dupont leads are 15 and 20 cm (its 30 cm lead is SH at both ends)
assert L['A7Z to FC']['needed_mm'] <= 200, L['A7Z to FC']
cable('c-a7z', 'A7Z ↔ 飞控线（SH1.0 转杜邦，20 cm，三根）', 'uart', '#1f9d55', L['A7Z to FC']['pts'], 1.5, 200,
      frm='飞控 UART1', to='A7Z 14、16、18 号针')
LEGEND = [{'kind': 'power-20v', 'color': '#c62828', 'label': '电池尾线（12 AWG 红黑）'},
          {'kind': 'power-15v', 'color': '#c99a00', 'label': '风扇线（16 AWG，三根一束）'},
          {'kind': 'uart', 'color': '#1f9d55', 'label': 'A7Z ↔ 飞控串口线'}]


# ---------------------------------------------------------------------------------------------- wiring benches (wiring-kit, makers' pictures)
def only(bench, groups=None, wires=None, title=None, caption=None):
    b = copy.deepcopy(bench)
    if groups is not None:
        b['wires'] = [w for w in b['wires'] if w.get('group') in groups]
    if wires is not None:
        b['wires'] = [w for w in b['wires'] if w['id'] in wires]
    used = {e.split('.')[0] for w in b['wires'] for e in (w['from'], w['to'])}
    b['modules'] = [m for m in b['modules'] if m['id'] in used]
    b['placements'] = [p for p in b['placements'] if p['module'] in used]
    gids = {w.get('group') for w in b['wires']}
    if 'groups' in b:
        b['groups'] = [g for g in b['groups'] if g['id'] in gids]
    out = {'bench': b}
    if title:
        out['title'] = title
    if caption:
        out['caption'] = caption
    return out


BENCH_FANS = W.bench_fans()
BENCH_POWER = W.bench_power()
BENCH_SIGNAL = W.bench_signal()
# The A7Z lead is made on the bench (step b-a7zlead, 2026-11-12: Shawn "线我们可以自己做"): three 5 cm SH1.0 kit wires in
# a 4-pin housing at positions 1, 3, 4, each soldered to a club M-F Dupont jumper (male end cut): black / blue / yellow.
# Position 2 (FC 5 V) stays empty.
KIT_COL = {'mvGND': ('#1d1d1f', '黑', 1), 'mvTX1': ('#1f6fd1', '蓝', 3), 'mvRX1': ('#c99a00', '黄', 4)}
for w in BENCH_SIGNAL['wires']:
    if w['id'] in KIT_COL:
        col, zh, pos = KIT_COL[w['id']]
        w['color'] = col
        a7z = {'mvGND': '14', 'mvTX1': '18', 'mvRX1': '16'}[w['id']]
        role = {'mvGND': '地', 'mvTX1': '飞控发 → A7Z 收', 'mvRX1': 'A7Z 发 → 飞控收'}[w['id']]
        w['label'] = f'SH 插头第 {pos} 位（{zh}线）→ A7Z {a7z} 号针（{role}）'


# ---------------------------------------------------------------------------------------------- what to print, buy, fetch
def print_rows():
    man = REL / 'manifest-FlightPack-D1.json'
    times, ok = {}, False
    if man.exists():
        m = json.loads(man.read_text())
        ok = all(Path(r['path']).exists() and sha(Path(r['path'])) == r['sha256'] for r in m['parts'])
        for f in sorted(REL.rglob('*FlightPack-D1_*')):
            mt = re.search(r'FlightPack-D1_(Orange|Black)_([A-Za-z0-9-]+?)_(\d+h\d+m)', f.name)
            if mt:
                times.setdefault(mt.group(1), {})[mt.group(2)] = mt.group(3)
    def t(colour):
        if not ok or colour not in times:
            return '【打印时间待定：切片文件 release-FlightPack-D1 还没发布或和当前 CAD 对不上，发布后重建本页自动填入】'
        return '打印时间 ' + '，'.join(f'{k} {v}' for k, v in sorted(times[colour].items()))
    return [
        f'橙色一盘：翼板、左右电池托盘、飞控支架（按 100% 填充打印，切片文件里已经设好）。{t("Orange")}',
        f'黑色一盘：左右机舱的内半和外半，共四块。{t("Black")}',
        '打印好不用修、不用钻、不用锉：拿下来去掉支撑直接用。',
    ]


ZH_STATUS = [('in hand', '已到手'), ('fitted', '已装'), ('ordered', '已下单'), ('carted', '在购物车里，还没下单'),
             ('unticked', '在购物车里但没勾选，还没买'), ('removed', '不买')]


def status_zh(s):
    s = s.lower()
    if 'removed' in s or 'not bought' in s and 'roboclub' in s:
        return '不买'
    if 'unticked' in s:
        return '在购物车里没勾选，还没买'
    for k, z in (('in hand', '已到手'), ('fitted', '已装上')):
        if s.startswith(k):
            return z
    if s.startswith('ordered'):
        m = re.search(r'arriving (?:\w+ )?(\d{4}-\d{2}-\d{2})', s)
        return '已下单' + (f'，预计 {m.group(1)} 到' if m else '') + '，还没到手'
    if s.startswith('carted'):
        return '在购物车里，还没下单'
    return '状态见 CURRENT-STATE.json'


BUY = [  # CURRENT-STATE key, Chinese line
    ('edf_fans_areswei_hds001_4650kv', '4 个 ARESWEI HDS001 50 mm 涵道风扇：2 个绿色电机（CW）+ 2 个红色电机（CCW）'),
    ('batteries_cnhl_4s_1300_130c', '2 块 CNHL 4S 1300 mAh 电池（XT60 头）'),
    ('fc_esc_micoair743v2_stack', 'MicoAir 743 V2 堆叠：飞控 + 55A 四合一电调'),
    ('optical_flow_mtf01', 'MicoAir MTF-01 光流模块'),
    ('fan_bullets_amass_3p5mm', 'Amass 3.5 mm 子弹头 20 对（用 12 个母头）'),
    ('sh1_cable_kit', 'SH1.0 硅胶线套装（电调↔飞控 8 针线、飞控↔光流 4 针线，还有自己做 A7Z 线用的 3 根 5 cm 线和 1 个 4 针外壳）'),
    ('battery_straps', '2 根 16 × 250 mm 电池绑带'),
    ('charger_htrc_b6_v2', 'HTRC B6 V2 平衡充电器'),
]


def buy_rows():
    rows = []
    for key, zh in BUY:
        rows.append(f'{zh}：{status_zh(PARTS_STATE[key]["status"])}')
    return rows


def club_rows():
    l12 = W.BAT_LEN['L']['pigtail_mm'] + W.BAT_LEN['R']['pigtail_mm']
    l16 = sum(W.FAN_LEN[n]['ext_mm'] for n in ('FL', 'RL', 'FR', 'RR'))
    return [
        '2 个 XT60 公头（焊杯式）。',
        f'12 AWG 硅胶线：红、黑各至少 {l12} mm（两根电池尾线）。',
        f'16 AWG 硅胶线：红、黄、黑各至少 {l16} mm（12 根风扇线）。',
        '1 个 1000 µF 35 V 电解电容，直径 13 mm、长 21 mm（俱乐部 Tnisesm 电容盒里那颗，已拿到）。',
        '4 个 M3 × 6 金属公母柱、4 个 M3 × 8 金属公母隔离柱（外螺纹都是 6 mm，长度差 1 到 2 mm 也行）、4 颗 M3 × 8 螺丝。',
        '3 根杜邦公母线（一头公针、一头母头，20 cm 左右；最好一根黑、一根黄、一根蓝）。',
        '热缩管：5 mm（子弹头）和 6 mm（XT60）各约半米。',
        '焊锡、助焊剂、几根小扎带。',
        f'{N_LUG} 颗 {LUG_ZH} 螺丝（机舱耳朵拧到臂上，每边 3 颗；焊接台 Craftsman 柜里有 M3 螺丝，清单上只写明了 M3×10，'
        f'找不到 {LUG_ZH} 就用 M3 × 10）。',
    ]


LUG_SPECS = sorted({s['spec'] for s in SCREWS if s['id'].startswith('lug-')})
assert len(LUG_SPECS) == 1 and LUG_SPECS[0].startswith('M3 x '), LUG_SPECS
LUG_ZH = LUG_SPECS[0].replace(' x ', ' × ')                       # 'M3 × 12' (Shawn 2026-11-11 '改成 M3')
N_LUG = sum(s['id'].startswith('lug-') for s in SCREWS)
N_POST = sum(s['spec'].startswith('M2 x 12 (existing') for s in SCREWS)
N_CLAMP = sum(s['spec'].startswith('M2 x 12 (with M2 washer)') for s in SCREWS)
N_M2 = {n: sum(re.fullmatch(f'M2 x {n}', s['spec']) is not None for s in SCREWS) for n in (4, 8, 10)}
assert N_POST == 4 and N_CLAMP and all(N_M2.values()), (N_POST, N_CLAMP, N_M2)
TOOLS = [
    '烙铁（焊 12 AWG 和 XT60 要用大烙铁头、温度调高）、焊锡、助焊剂、夹线的第三只手',
    '剥线钳（12 AWG、16 AWG）、斜口钳',
    '5.5 mm 扳手或尖嘴钳（拧 M3 金属柱的六角）',
    '热风枪（或打火机）缩热缩管',
    f'1.5 mm 内六角起子（拧 {N_POST + N_CLAMP} 颗 M2 × 12 内六角螺丝）',
    '平时拧 M2 螺丝用的小螺丝刀（M2 × 4、× 8、× 10）',
    f'配 {LUG_ZH} 螺丝头的螺丝刀（按从俱乐部拿到的螺丝选）',
    '1 mm 厚双面泡棉胶（3M 那种）和剪刀',
    f'Zuorery M2 螺丝盒里的 M2 × 12 内六角螺丝 {N_POST + N_CLAMP} 颗和 M2 垫片 {N_CLAMP} 个',
    'Mac 和一根 USB-C 数据线（转向检查时连飞控）',
    '一条细纸条（转向检查时看风往哪边吹）',
]


# ---------------------------------------------------------------------------------------------- steps
STEPS = []
CHAPTERS = [
    dict(id='start', title='0. 开始之前', summary='要打印、要买、要从俱乐部拿的东西和工具。', intro=False),
    dict(id='bench', title='1. 在桌上：焊线、装飞控、装风扇', summary='全部焊接都在桌上做完，翼板、支架、飞控堆叠和两个机舱在桌上装好，机器人不动。'),
    dict(id='robot', title='2. 装到鸭子上', summary='翼板组件和背包用 4 颗 M2 × 12 一起装上，再装托盘、机舱、走线、电池，最后检查转向和间隙。'),
]


def step(**kw):
    kw.setdefault('show', [])
    kw.setdefault('add', [])
    kw.setdefault('context', [])
    STEPS.append(kw)
    return kw


ALL_FLIGHT = [k for k, _, _ in PRINTED] + list(FANS) + ['esc', 'fc', 'mtf01', 'cap_tape', 'capacitor', 'battery_L', 'battery_R']

step(id='overview', still='inventory page: everything shown, nothing installed yet', chapter='start', title='飞行背包：先把东西备齐',
     show=ALL_FLIGHT + DUCK_ALL,
     instructions=['这一章装的东西：四个 50 mm 涵道风扇装在左右两个机舱里，机舱和两块 4S 电池挂在一块翼板上，翼板夹在 OpenRB 盒子和电池背包之间；飞控堆叠和光流装在右臂后面。',
                   '一、要打印：'] + ['· ' + r for r in print_rows()] +
                  ['二、要买（状态来自 CURRENT-STATE.json）：'] + ['· ' + r for r in buy_rows()] +
                  ['三、去俱乐部拿：'] + ['· ' + r for r in club_rows()] +
                  ['四、工具和自备的东西：'] + ['· ' + r for r in TOOLS] +
                  [f'M2 × 12 内六角一共 {N_POST + N_CLAMP} 颗，都从 Zuorery 盒里拿，是同一种螺丝：{N_CLAMP} 颗夹两个机舱（每颗配一个 M2 垫片），{N_POST} 颗把翼板和背包拧到 OpenRB 盒子上。',
                   f'其它 M2 是自攻螺丝：M2 × 10 {N_M2[10]} 颗、M2 × 8 {N_M2[8]} 颗、M2 × 4 {N_M2[4]} 颗。',
                   f'{LUG_ZH} {N_LUG} 颗，只用在两个机舱耳朵上（每边 3 颗）。'],
     warnings=['全部焊接都在第 1 章桌上做完，XT60 头也在桌上焊好。焊好的线带着 XT60 从后面放进翼板的开口槽、穿过支架的方窗，不用拆线。',
               '首次上电（除了第 2 章的转向检查）和第一次飞行不在这一章。'])

# ---- chapter 1: bench
FL, RL, FR, RR = (W.FAN_LEN[n]['ext_mm'] for n in ('FL', 'RL', 'FR', 'RR'))
BL, BR = W.BAT_LEN['L']['pigtail_mm'], W.BAT_LEN['R']['pigtail_mm']
step(id='b-cut', still='cutting and labelling leads on the bench (drawn in the pictures)', chapter='bench', bench=True, title='剪好 16 根线，每根贴上名字', stage='images',
     images=[dict(src=BF.cut_list({n: W.FAN_LEN[n]['ext_mm'] for n in ('FL', 'RL', 'FR', 'RR')},
                                  {n: W.BAT_LEN[n]['pigtail_mm'] for n in ('L', 'R')}),
                  caption='剪线清单（按比例画）：每组线一样长，贴一张写名字的胶带。')],
     prepare=[dict(item='16 AWG 硅胶线（红、黄、黑）', qty=1, kind='cable'), dict(item='12 AWG 硅胶线（红、黑）', qty=1, kind='cable'),
              dict(item='斜口钳、剥线钳、胶带和笔', qty=1, kind='tool')],
     instructions=[f'16 AWG 剪 12 根：红、黄、黑各 1 根 {FL} mm，每根贴胶带写“左前”。',
                   f'16 AWG 再剪：红、黄、黑各 1 根 {RL} mm，写“左后”。',
                   f'16 AWG 再剪：红、黄、黑各 1 根 {FR} mm，写“右前”。',
                   f'16 AWG 再剪：红、黄、黑各 1 根 {RR} mm，写“右后”。',
                   f'12 AWG 剪 4 根：红、黑各 1 根 {BL} mm，写“左电池”。',
                   f'12 AWG 再剪：红、黑各 1 根 {BR} mm，写“右电池”。',
                   '16 根线两头都剥掉一小段皮：一头剥到线芯刚好填满焊杯（子弹头、XT60），另一头剥 2 mm（焊盘）；12 AWG 两头都剥到填满焊杯。',
                   '所有线头蘸助焊剂，用烙铁上一层薄锡。'],
     checks=['桌上一共 16 根线，每根都有名字。'])

step(id='b-bullets', still='soldering bullets onto loose leads (drawn in the pictures)', chapter='bench', bench=True, title='12 根风扇线的长头各焊一个 3.5 mm 母子弹头', stage='images',
     images=[dict(src=u, caption=c) for u, c in zip(BF.bullet_steps(), ('剥皮长的那头接子弹头；剥 2 mm 的短头留到下一步焊电调。',
                                                                       '灰色是化满的锡。', '锡凝固前线不要动。', '12 根线都这样做。'))],
     prepare=[dict(item='3.5 mm 母子弹头', qty=12, kind='electronic'), dict(item='5 mm 热缩管，每段比子弹头长一点', qty=12, kind='other'),
              dict(item='烙铁、焊锡、热风枪', qty=1, kind='tool')],
     instructions=['每根 16 AWG 线先套一段 5 mm 热缩管，推到离线头远的地方。',
                   '母子弹头焊杯朝上夹在第三只手上，焊杯里先化满锡。',
                   '把剥皮长的那头线插进焊杯，等锡流满再拿开烙铁，线不要动，直到锡凝固。',
                   '冷了以后把热缩管推上来盖住焊杯，母头的插口露在外面，用热风枪缩紧。',
                   '12 根都这样做。'],
     checks=['每个子弹头用力拉一下不松。', '插口里没有锡，也没有被热缩管盖住。'])

step(id='b-pads', chapter='bench', bench=True, stage='wiring', title='12 根风扇线的短头焊到电调的四组电机焊盘', add=['esc'],
     wiring=only(BENCH_FANS, title='电调四组焊盘 → 四个风扇', caption='从机器人后面往前看。第 1、2 组在右边（外侧），第 3、4 组在左边。'),
     prepare=[dict(item='MicoAir 55A 四合一电调', qty=1, kind='electronic')],
     instructions=['电调元件面朝上平放，两片金色电池片朝远离你的方向，和上图一样。',
                   '第 1 组焊盘焊“右前”三根线，第 2 组焊“右后”，第 3 组焊“左前”，第 4 组焊“左后”。',
                   '每组三块焊盘按 a、b、c 依次焊 红、黄、黑。',
                   '焊法：焊盘先上一点锡，把线头压在焊盘上，烙铁压住线头直到锡化开把线吃进去，再拿开烙铁。'],
     checks=['12 根线都焊牢，拉一下不动。', '相邻焊盘之间没有锡连在一起。'],
     warnings=['风扇的转向不在这里定。第 2 章的转向检查里，转反了的风扇对调两根子弹头就行，不用重焊。'])

step(id='b-tabs', chapter='bench', bench=True, stage='wiring', title='两根电池尾线和电容焊到电调的两片电池片', show=['esc'], add=['capacitor'],
     wiring=only(BENCH_POWER, title='两块电池并联到电调', caption='红线全部到 + 片，黑线全部到 − 片。XT60 头这一步还不焊。'),
     prepare=[dict(item='1000 µF 电容', qty=1, kind='electronic')],
     instructions=['认电容的脚：长脚是 +，罐身上有白条的那一侧是 −。',
                   '认电调的两面：有白色 8 针插座、两片电池片中间有一块银色电阻（0m25）的那面叫“元件面”，另一面叫“背面”。装上机后背面朝支架，元件面朝飞控。',
                   '两根尾线一面一根：“右电池”尾线焊在两片的背面，“左电池”尾线焊在两片的元件面。装上机后右尾线从支架和电调中间的缝里上来，左尾线从电调上方下来，各自正好落在自己那面。',
                   '烙铁换最大的扁头（约 5 mm），温度调到 400～450 ℃。电池片很厚、吸热快，小尖头化不开锡。',
                   '四根 12 AWG 线头各剥 4 mm，每根抹助焊剂、上锡，上到锡把线芯吃透、表面发亮。',
                   '两片电池片的两面都抹助焊剂，每面上一层薄锡。',
                   '背面 + 片：“右电池”红线平贴在片上，线芯头朝片尖、离片尖留约 1 mm，线皮贴着电调背面往板子中间走。烙铁压在线芯上，等锡化开把线吃进去，补锡到线芯被包住，拿开烙铁后数 5 秒别动。',
                   '背面 − 片：“右电池”黑线同样焊上。',
                   '用第三只手（或夹子）夹住右尾线，让它不受力：接下来焊元件面时，热量会穿过电池片把背面的锡再化开。',
                   '元件面 + 片：“左电池”红线平贴在片上，线芯头朝板子、线皮从片尖那头伸出去（朝上）。同样压烙铁、补锡、数 5 秒；再焊 − 片的“左电池”黑线。',
                   '电容的两只脚弯一下，长脚搭到背面 + 片的焊点外侧，另一只脚搭到背面 − 片的焊点外侧，罐底离电调背面留约 3 mm；各点一下烙铁，让脚沉进焊点。脚多出来的剪掉。',
                   '全部焊点凉透（数 10 秒）再松开夹子。'],
     checks=['背面：+ 片右尾线红线加电容长脚，− 片右尾线黑线加电容白条一侧的脚；元件面：+ 片左尾线红线，− 片左尾线黑线。',
             '背面的线芯和锡都没有伸出片尖：片尖外面装机后就是电容。',
             '+ 片和 − 片之间两面都没有锡、没有线头搭着。',
             '焊点圆润发亮、看得到线芯轮廓被锡包住；每根线单独用力拉一下都不动，两面都拉。'],
     warnings=['红黑接反、或者 + − 搭在一起，插上电池时电容会炸、电调会烧。焊完这一步之前不要靠近任何电池。',
               '每次加热别超过 10 秒，化不开就换更大的头或调高温度，不要一直压着：两片中间那块银色电阻（0m25）也是焊上去的，烫久了会松。'])

step(id='b-mtf', chapter='bench', bench=True, title='光流模块拧到支架下面的小平台', add=['fc_bracket', 'mtf01'], approach={'mtf01': [0, 0, -25]},
     screws=screws_for('flow module', 'b-mtf'),
     prepare=[dict(item='飞控支架（橙色竖板）', qty=1, kind='printed'), dict(item='MTF-01 光流', qty=1, kind='electronic'),
              dict(item='SH1.0 套装里 4 针、10 cm 的线', qty=1, kind='cable')],
     instructions=['先把 4 针、10 cm 的 SH 线一头插进光流背面的插座。',
                   '支架竖板平放在桌上，带小平台的那头朝你，平台下面悬空。',
                   '光流镜头朝下，贴在平台下面，四个孔对准平台上的四个小孔。',
                   '四颗 M2 × 4 从下往上穿过光流的孔，拧进平台，拧到光流贴平就停。'],
     checks=['镜头朝下、前面没有挡住；线从光流上伸出来。'])

step(id='b-xt60', still='soldering XT60 plugs onto loose leads (wiring drawing)', chapter='bench', bench=True, stage='wiring', title='两根电池尾线的另一头各焊一个 XT60 公头', show=['esc', 'capacitor'],
     wiring=only(BENCH_POWER, wires={'pig_Rp', 'pig_Rn', 'pig_Lp', 'pig_Ln'}, title='两根电池尾线'),
     prepare=[dict(item='XT60 公头', qty=2, kind='electronic'), dict(item='6 mm 热缩管', qty=4, kind='other')],
     instructions=['“右电池”红、黑两根线的空头，每根套一段 6 mm 热缩管，推远。',
                   'XT60 公头夹在第三只手上，认清头上印的 + 号。',
                   '红线焊进 + 焊杯，黑线焊进 − 焊杯，焊法和子弹头一样。',
                   '热缩管推上来盖住焊杯，缩紧。',
                   '“左电池”两根线同样焊另一个 XT60 公头。'],
     checks=['两个 XT60 都是红线在 + 号那边。', '两个 XT60 各连在写着“左电池”“右电池”的线上。'])

step(id='b-a7zlead', still='making a loose lead on the bench (wiring drawing)', chapter='bench', bench=True, stage='wiring', title='自己做 A7Z ↔ 飞控线：SH 4 针插头 + 三根杜邦母头', show=['fc'],
     wiring=only(BENCH_SIGNAL, groups={'mav'}, title='做好的线：SH 插头第 1、3、4 位 → 三个杜邦母头',
                 caption='SH 插头第 2 位空着（那是飞控的 5 V，不接）。'),
     prepare=[dict(item='SH1.0 套装里 5 cm 的线', qty=3, kind='cable'), dict(item='SH1.0 套装里 4 针的白色外壳', qty=1, kind='other'),
              dict(item='杜邦公母线（黑、黄、蓝各一根，20 cm 左右）', qty=3, kind='cable'), dict(item='最细的热缩管', qty=3, kind='other')],
     instructions=['三根 5 cm 的 SH 线，每根两头都带小金属端子。每根只留一头的端子，另一头连端子剪掉，剥出 3 mm 线芯。',
                   '白色 4 针外壳按插进去的方向，对准飞控上沿的 UART1 插座比一下：对着插座 GND 针（接线图里第 1 位）的孔是第 1 位，往另一头依次是第 2、3、4 位。用笔在第 1 位旁边点一下。',
                   '三根线留着的端子，分别推进第 1、3、4 位，听到“咔”一声，轻拉不掉出来。第 2 位空着。',
                   '三根杜邦公母线，把公针那头剪掉，剥出 3 mm 线芯，各套一段热缩管推远。',
                   '黑色杜邦线焊到第 1 位那根线上，蓝色焊到第 3 位，黄色焊到第 4 位：线芯拧在一起，上锡。',
                   '热缩管推上来盖住焊点，缩紧。',
                   '颜色不全就用别的颜色，在每根杜邦头上贴胶带写上“1”“3”“4”。'],
     checks=['SH 插头第 2 位是空的。', '三根线轻拉都不会从 SH 外壳里掉出来。', '每根线从 SH 插头量到杜邦头，至少 20 cm。'])

step(id='b-bracket', chapter='bench', bench=True, title='支架拧到翼板右臂背后', show=['fc_bracket', 'mtf01'], add=['wing_plate'],
     approach={'wing_plate': [30, 0, 0]}, screws=screws_for('FC bracket on wing (before the stack)', 'b-bracket'),
     prepare=[dict(item='翼板（橙色）', qty=1, kind='printed')],
     instructions=['翼板正面（平的那面）朝下放在桌上，右臂在你右手边。',
                   '支架的平面贴住右臂背后的四个小凸台，小平台和光流在下（靠翼板底边）。',
                   '四颗 M2 × 8 从支架背面穿过，拧进四个凸台，拧到支架贴平就停。'],
     checks=['支架四角都贴着凸台，不晃。'])

step(id='b-standoffs', chapter='bench', bench=True, title='四个 M3 × 6 金属柱拧进支架的四个圆凸台', show=['wing_plate', 'fc_bracket', 'mtf01', 'esc', 'capacitor'],
     screws=screws_for('stack', 'b-standoffs', ids=['fc-standoff']),
     prepare=[dict(item='5.5 mm 扳手或尖嘴钳', qty=1, kind='other')],
     instructions=['四个 M3 × 6 金属公母柱，公头朝支架，先用手拧进四个圆凸台的孔里，拧到拧不动。',
                   '再用 5.5 mm 扳手（或尖嘴钳）夹住六角，拧到柱子底面贴住凸台就停。'],
     checks=['四个柱子都竖直、一样高，底面贴着凸台。'],
     warnings=['贴住凸台就停手，再拧塑料螺纹会滑丝。'])

step(id='b-esc', chapter='bench', bench=True, title='电调套到金属柱上，插上 8 针线，再拧四个隔离柱',
     show=['wing_plate', 'fc_bracket', 'mtf01', 'capacitor'], add=['esc'], approach={'esc': [-25, 0, 0]},
     screws=screws_for('stack', 'b-esc', ids=['esc-fc-spacer']),
     wiring=only(BENCH_SIGNAL, groups={'escfc'}, title='电调 ↔ 飞控 8 针直通线'),
     prepare=[dict(item='飞控电调套装盒里那根 3 cm 的 8 针线（两头都是白色 SH1.0 小插头）', qty=1, kind='cable')],
     instructions=['先把 8 针线的一头插进电调的 8 针插座。',
                   '“右电池”尾线的 XT60 头竖着，从支架中间偏下的方窗塞过去，落进右臂背后的格子里。',
                   '电调四个角孔里如果有黑色胶圈，留着别拿掉。',
                   '电调元件面朝外（朝你），两片电池片朝上，四个角孔套进四个金属柱；右电池尾线夹在支架和电调之间往下走。',
                   '电容顺势躺到右臂顶上，罐子沿着臂的方向放进两个小槽之间。',
                   '四个 M3 × 8 金属隔离柱，公头朝下穿过电调的四个角孔，先用手拧进下面的金属柱，再用扳手轻轻带紧，拧到电调被夹住不晃。'],
     checks=['电池片在上沿，8 针线从电调下沿伸出来。', '尾线从支架方窗里出来，没有被电调压住。',
             '八个金属柱都没有碰到电调上的焊盘、焊点和元件。'],
     warnings=['金属柱导电：哪个柱子贴到了焊盘或元件，先拆下来把那根线或元件拨开再装。'])

step(id='b-fc', chapter='bench', bench=True, title='飞控插好两根线，扣到隔离柱上，拧四颗 M3 螺丝',
     show=['wing_plate', 'fc_bracket', 'mtf01', 'esc', 'capacitor'], add=['fc'], approach={'fc': [-25, 0, 0]},
     screws=screws_for('stack', 'b-fc', ids=['fc-screw']),
     wiring=only(BENCH_SIGNAL, groups={'escfc', 'mtf'}, title='电调 ↔ 飞控，飞控 ↔ 光流', caption='两根都是直通线：第 1 位对第 1 位。'),
     prepare=[dict(item='MicoAir743v2 飞控（带四个胶圈）', qty=1, kind='electronic')],
     instructions=['8 针线的另一头插进飞控的 ESC 插座。',
                   '光流线的另一头插进飞控的 UART4 插座。',
                   '飞控和电调同一个方向（ESC 插座都在下沿），四个胶圈孔套到四个隔离柱上。',
                   '四颗 M3 × 8 螺丝穿过胶圈，拧进隔离柱，拧到飞控不晃就停，胶圈不要压扁。'],
     checks=['8 针线在两块板的下沿，没有被夹在两块板中间。', '飞控 UART1 插座（上沿）空着，留给 A7Z 线。'])

step(id='b-cap', chapter='bench', bench=True, title='一条泡棉胶把电容粘在右臂顶上',
     show=['wing_plate', 'fc_bracket', 'mtf01', 'esc', 'fc'],
     add=['cap_tape', 'capacitor'], approach={'cap_tape': [0, 0, 20], 'capacitor': [0, 0, 30]},
     prepare=[dict(item='1 mm 双面泡棉胶，剪一条 12 × 6 mm', qty=1, kind='other')],
     instructions=['右臂顶面靠后那段先用酒精擦干净。',
                   '泡棉胶剪一条 12 × 6 mm，顺着翼板前后方向贴在右臂顶面两个小方槽中间。',
                   '电容放平压在胶条上，两只脚朝电调，按住数 10 秒。'],
     warnings=['顶面上那两个小方槽不用穿扎带：下面有加强筋挡着，扎带绕不过去。'],
     checks=['电容两只脚没有被拉直，焊点不受力。', '轻推电容不滚、不动。'])

for side, zh, front, rear in (('L', '左', 'fan_FL', 'fan_RL'), ('R', '右', 'fan_FR', 'fan_RR')):
    fz = '左前' if side == 'L' else '右前'
    rz = '左后' if side == 'L' else '右后'
    fcol = '绿色电机' if side == 'L' else '红色电机'
    rcol = '红色电机' if side == 'L' else '绿色电机'
    out = [0, 30, 0] if side == 'L' else [0, -30, 0]
    step(id=f'b-fans-{side}', chapter='bench', bench=True, title=f'{zh}机舱内半贴泡棉胶，放进两个风扇',
         add=[f'nacelle_inner_{side}', front, rear], approach={front: [0, 45 if side == 'L' else -45, 0], rear: [0, 45 if side == 'L' else -45, 0]},
         prepare=[dict(item=f'{zh}机舱内半（黑色）', qty=1, kind='printed'), dict(item=f'{fcol}风扇（放前面）', qty=1, kind='electronic'),
                  dict(item=f'{rcol}风扇（放后面）', qty=1, kind='electronic'), dict(item='1 mm 双面泡棉胶', qty=1, kind='other')],
         instructions=[f'{zh}机舱内半侧躺在桌上，剖面（将来贴外半的那一面，平的）朝上，两个半圆槽朝上；用一只手扶住。',
                       '每个半圆槽里贴一层 1 mm 泡棉胶：沿着槽壁并排贴满，从槽的上沿贴到下沿，不要叠两层。',
                       '槽壁上的小方坑（耳槽）和侧面的长缝（出线缝）不要贴住。',
                       '撕掉泡棉胶的离型纸。',
                       f'{fcol}的风扇放进前面的槽（离方块耳朵远的那个）：进风口（带尖头的那头）朝机舱的上沿，出风口朝打印时贴床的那个平面；转到风扇的两只小耳朵一只在槽的前端、一只在后端，落进剖面上的两个耳槽。',
                       f'{rcol}的风扇放进后面的槽（靠方块耳朵的那个），同样进风口朝上沿、两只耳朵落进耳槽。',
                       '每个风扇的三根线从最近的出线缝出来。'],
         checks=[f'{fz}是{fcol}，{rz}是{rcol}。', '两个风扇都坐到底，耳朵在耳槽里。'])
    step(id=f'b-close-{side}', chapter='bench', bench=True, title=f'盖上{zh}机舱外半，五颗 M2 × 12 加垫片轻轻夹住风扇',
         show=[f'nacelle_inner_{side}', front, rear], add=[f'nacelle_outer_{side}'], approach={f'nacelle_outer_{side}': out},
         screws=screws_for(f'nacelle {side}', f'b-close-{side}'),
         prepare=[dict(item=f'{zh}机舱外半（黑色）', qty=1, kind='printed'),
                  dict(item='M2 × 12 内六角（Zuorery 盒）', qty=5, kind='fastener'), dict(item='M2 垫片', qty=5, kind='fastener'),
                  dict(item='1.5 mm 内六角起子', qty=1, kind='tool')],
         instructions=['外半的两个半圆槽也同样贴一层 1 mm 泡棉胶，撕掉离型纸。',
                       '外半剖面朝下，盖到两个风扇上，风扇耳朵的另一半落进外半的耳槽。',
                       '五颗 M2 × 12 内六角各套一个 M2 垫片，从外半的五个沉孔拧进去。',
                       '五颗先都拧到刚吃上，再轮流每颗拧半圈。',
                       '拧到两半把风扇夹稳、用手转不动风扇壳就停：大约是平时手拧紧的一半力气。'],
         checks=['五颗都只拧到两半夹稳风扇，一颗都没有拧紧。',
                 '两半之间留一条缝是正常的（风扇细就缝小，粗就缝大），不要为了合缝继续拧。'],
         warnings=['只用平时手拧紧一半的力气，夹稳风扇就停。绝对不要拧紧：拧紧机舱夹圈会裂。'])

# ---- chapter 2: on the robot
OPEN_CTX = DUCK_CTX + ['sd_a7z_pcb', 'sd_heatsink_6530b']
step(id='r-open', still='opening the backpack: parts come off, nothing is installed', chapter='robot', title='关机，打开电池背包，把背包从 OpenRB 盒子上拿下来',
     show=DUCK_CTX + ['bp_swap_plugs', 'sd_a7z_pcb', 'sd_heatsink_6530b', 'sd_dupont_housings', 'head_cap'],
     instructions=['A7Z 关机，再按背包底下的开关把背包关掉。',
                   '拔开背包顶上的插头 1。',
                   '取下背包顶上的舱盖（和换电池时一样）。',
                   '拧下背包后盖上的三颗 M2 × 8，把后盖连同里面的电池和两根横条一起往后拿下来，螺丝留着。',
                   '在背包里面，前板上有四颗螺丝把背包固定在 OpenRB 盒子的柱子上：拧下这四颗，以后不再用。',
                   '把背包外框往后拉开，从 OpenRB 盒子背面的线槽里拔开插头 3（XT30）和插头 4（MR30），外框拿下来放在旁边。'],
     checks=['OpenRB 盒子背面露出四个螺丝孔，线槽里插头 3、4 的机器人这一侧还留在原处。'])

step(id='r-wing', chapter='robot', title='翼板组件贴到 OpenRB 盒子背面', context=OPEN_CTX,
     show=['bp_swap_plugs'], add=FLIGHT_FRAME,
     group={'label': '第 1 章装好的翼板（带支架、光流、飞控堆叠和电容）', 'approach': [-90, 0, 0]},
     instructions=['两个机舱先放在桌上，后面再装。拿翼板时一手托住支架和飞控，电池尾线和风扇线让它们垂着。',
                   '翼板正面（平的那面）贴住 OpenRB 盒子背面，中间那块的四个孔对准盒子上的四个螺丝孔。',
                   '翼板的上沿在 A7Z 座后窗下面，不碰座子。',
                   '鸭子左侧那根摄像头 USB 线在 A7Z 座后面往里拐：翼板贴上去时，把这根线从侧面放进左臂根部上角的小缺口里，不要压在翼板下面。',
                   '一只手按住翼板，下一步装背包时不要松手；或者请人扶住。'],
     checks=['四个孔对齐，翼板没有压到两边侧壳的后沿。', '摄像头 USB 线在左臂根部的缺口里，没有被夹住。'],
     warnings=['这一步翼板只是贴着，还没有螺丝，松手会掉。'])

step(id='r-backpack', chapter='robot', title='背包外框贴到翼板背面，四颗 M2 × 12 一起拧进 OpenRB 盒子', context=OPEN_CTX,
     show=FLIGHT_FRAME + ['bp_swap_plugs'], add=['battery_backpack_frame', 'bp_dfr1202', 'bp_switch', 'bp_plug2'],
     group={'label': '背包外框（连着里面的 DFR1202 和开关）', 'approach': [-40, 0, 0]},
     screws=screws_for('wing plate and backpack on the pack', 'r-backpack'),
     prepare=[dict(item='M2 × 12 内六角（Zuorery 盒）', qty=4, kind='fastener'),
              dict(item='1.5 mm 内六角起子', qty=1, kind='tool')],
     instructions=['插头 3（XT30）和插头 4（MR30）背包这一侧的头，插头朝前，从后面穿过翼板中间的扁窗，和线槽里的机器人一侧插回去（XT30 对 XT30，MR30 对 MR30）。',
                   '背包外框前板贴住翼板背面，前板的四个孔对准翼板的四个孔。',
                   '从背包里面，4 颗 M2 × 12 穿过背包前板和翼板，拧进 OpenRB 盒子的柱子。',
                   '四颗先都拧到刚吃上，再轮流拧到背包和翼板都贴紧、不晃。'],
     checks=['四颗都是 M2 × 12，不是 × 10。', '翼板和背包一起不晃。'],
     warnings=['这里只能用 M2 × 12：M2 × 10 咬不住柱子，翼板会掉。'])

step(id='r-bpclose', chapter='robot', title='背包后盖装回去，舱盖盖好', context=OPEN_CTX,
     show=FLIGHT_FRAME + ['battery_backpack_frame', 'bp_dfr1202', 'bp_switch', 'bp_plug2', 'bp_swap_plugs'],
     add=BACKPACK_BODY, group={'label': '背包后盖（连着鸭子的 2S 电池和两根横条）', 'approach': [-40, 0, 0]},
     instructions=['后盖带着电池对准外框，直着往前推到边缘贴住外框一圈。',
                   '原来的三颗 M2 × 8 从后盖背面拧回去，拧到后盖贴紧。',
                   '舱盖照原样盖上。插头 1 先不插（鸭子保持关机）。'],
     checks=['后盖下半截的背面是平的、空着：下一步线束要贴着它横过去。'])

for side, zh in (('L', '左'), ('R', '右')):
    step(id=f'r-tray-{side}', chapter='robot', title=f'{zh}电池托盘拧到{zh}臂正面', context=OPEN_CTX,
         show=FLIGHT_FRAME + ['battery_backpack_frame'], add=[f'tray_{side}'],
         approach={f'tray_{side}': [40, 0, 0]}, screws=screws_for(f'tray {side} on wing', f'r-tray-{side}'),
         prepare=[dict(item=f'{zh}电池托盘（橙色平板）', qty=1, kind='printed')],
         instructions=[f'{zh}托盘平放，带竖边的那头朝后，竖边贴住{zh}臂正面，竖边上的三个小孔对准臂上的三个孔。']
                      + (['左托盘竖边靠里的上角有一个小缺口：摄像头 USB 线放在这个缺口里，托盘贴上去时不要夹住它。'] if side == 'L' else [])
                      + ['三颗 M2 × 10 从臂背后的格子里穿过臂板，拧进托盘竖边，拧到托盘贴紧。'],
         checks=['托盘平，不往下垂。'] + (['摄像头 USB 线在托盘缺口里，没有被压扁。'] if side == 'L' else []))

for side, zh, front, rear in (('L', '左', 'fan_FL', 'fan_RL'), ('R', '右', 'fan_FR', 'fan_RR')):
    up = [0, 60 if side == 'L' else -60, 40]
    step(id=f'r-nac-{side}', chapter='robot', title=f'{zh}机舱拧到{zh}臂外端', context=OPEN_CTX,
         show=FLIGHT_FRAME + ['battery_backpack_frame', 'tray_L', 'tray_R'] + (['nacelle_inner_L', 'nacelle_outer_L', 'fan_FL', 'fan_RL'] if side == 'R' else []),
         add=[f'nacelle_inner_{side}', f'nacelle_outer_{side}', front, rear],
         group={'label': f'{zh}机舱（两个风扇已经夹在里面）', 'approach': up},
         screws=screws_for(f'nacelle {side} on wing', f'r-nac-{side}'),
         instructions=[f'{zh}机舱进风口朝上，内半上往里伸的方块耳朵贴住{zh}臂外端的正面，耳朵上的三个小孔对准臂上的三个孔。',
                       f'三颗 {LUG_ZH} 从臂背后最外面的格子里穿过臂板，拧进{zh}机舱内半的方块耳朵，拧到机舱贴紧不晃。'],
         checks=['机舱比托盘高，进风口上面什么都没有。'])

step(id='r-left-wires', still='routing flexible leads (drawn as cables)', chapter='robot', title='左边的线束：从电调绕到背包后面，再沿背包左侧进左臂',
     context=OPEN_CTX, show=[k for k in ALL_FLIGHT if not k.startswith('battery')] + ['battery_backpack_frame'] + BACKPACK_BODY,
     cables=['c-batL', 'c-FL', 'c-RL'],
     prepare=[dict(item='小扎带', qty=1, kind='other')],
     instructions=['“左电池”尾线、“左后”和“左前”风扇线，三束一起从电调背后往下，到背包后盖背面的最下面，贴着后盖横到左边，再沿背包左侧壁外面往前到左臂背后。',
                   '左臂背后有三片竖筋，靠中间的两片上的方窗朝后开口。把三束线从后面一起按进这两个开口槽：先最靠中间那片，再第二片。',
                   '“左电池”尾线的 XT60 头留在第二、三片筋之间的格子里，正对臂板上的大方窗（电池线从这个窗过来）。',
                   '“左后”风扇线的子弹头一端穿过第三片筋（最外面那片）的方窗，停在最外面的格子里。',
                   '“左前”风扇线也穿过第三片筋的方窗，再绕过左臂的外端到正面，沿左托盘外侧的边往前到左前风扇。不要放在托盘上面，电池会压住它。',
                   '背包后面，线束在后盖最下面，舱盖下沿以下，不要挡住舱盖。',
                   '在背包后面线束往上拐向电调的地方，一根扎带绕住线束和飞控支架下面小平台靠里的那条边：扎带从飞控下面穿过，不要套住光流，拉紧，剪平尾巴。'],
     checks=['背包后面的线束整齐贴着后盖，没有绕到腿能踢到的地方。', '三束线都在两个开口槽里。', '扎带没有套住光流，也没有压在飞控上。'])

step(id='r-right-wires', still='routing flexible leads (drawn as cables)', chapter='robot', title='右边的线：右前、右后风扇线绕过支架外侧进右臂',
     context=OPEN_CTX, show=[k for k in ALL_FLIGHT if not k.startswith('battery')] + ['battery_backpack_frame'] + BACKPACK_BODY,
     cables=['c-batR', 'c-FR', 'c-RR'],
     instructions=['“右后”三根风扇线从电调右边，绕过支架外侧的边（不要从支架和飞控前面过），进右臂最外面的格子。',
                   '“右前”三根风扇线同样绕过支架外侧进最外面的格子，再绕过右臂的外端到正面，沿右托盘外侧的边往前到右前风扇。不要放在托盘上面。',
                   '“右电池”尾线的 XT60 已经在右臂背后的格子里：把它放在第二、三片筋之间，正对臂板上的大方窗。'],
     checks=['支架外侧的线没有压在飞控上。'])

step(id='r-bullets', still='plugging bullet connectors on flexible leads (drawn as cables)', chapter='robot', title='12 个子弹头插上，多出来的风扇线扎好',
     context=OPEN_CTX, show=[k for k in ALL_FLIGHT if not k.startswith('battery')] + ['battery_backpack_frame'],
     cables=['c-FL', 'c-RL', 'c-FR', 'c-RR'],
     prepare=[dict(item='小扎带', qty=4, kind='other')],
     instructions=['每个风扇自带的三根线（公子弹头）插进写着它名字的那三个母头里，三根之间的顺序随便。',
                   '每个风扇多出来的线折成小 S，用扎带扎在同一侧臂最外面的格子里，剪平扎带尾巴。'],
     checks=['12 个子弹头都插到底，露出的金属部分都在热缩管里。', '没有线垂在机舱进风口上方。'])

step(id='r-batt', chapter='robot', title='两块 4S 电池放到托盘上绑好，XT60 先不插', context=OPEN_CTX,
     show=[k for k in ALL_FLIGHT if not k.startswith('battery')] + ['battery_backpack_frame'],
     add=['battery_L', 'battery_R'], approach={'battery_L': [0, 0, 40], 'battery_R': [0, 0, 40]},
     prepare=[dict(item='CNHL 4S 1300 电池', qty=2, kind='electronic'), dict(item='16 × 250 mm 绑带', qty=2, kind='other')],
     instructions=['每个托盘上穿两根绑带：从托盘下面穿过一对绑带槽。',
                   '电池放到托盘上，引线那头朝后（朝翼板），贴住托盘竖边。',
                   '电池的 XT60 线和平衡线从臂板上的大方窗穿到后面的格子里。',
                   '左电池的绑带拉紧之前，把摄像头 USB 线往里（朝鸭子中间）推，让它在绑带里侧，不被绑带压住。',
                   '两根绑带绕过电池拉紧扣好；平衡线压在绑带下面。',
                   'XT60 先不插。'],
     checks=['电池推不动、也不往外滑。', '摄像头 USB 线在左电池绑带的里侧，没有被压住。'])

step(id='r-spin', still='powered direction check, nothing installed', chapter='robot', title='转向检查：一次转一个风扇，看风向和转向',
     context=OPEN_CTX, show=[k for k in ALL_FLIGHT] + ['battery_backpack_frame'],
     instructions=['前提：飞控已经刷好固件、设好参数（参数表见 wiring/wiring.html 第八节），不做完不要开始这一步。',
                   '搬鸭子只抓身体，不要抓风扇、机舱或翼板的臂。',
                   '鸭子放稳在桌上，四个风扇上方和下方 30 cm 内没有东西，手不要伸到风扇附近。',
                   '只插右电池：右电池的 XT60 插上右尾线的 XT60。左电池不插。',
                   'USB-C 线连 Mac 和飞控，打开地面站的电机测试（Motor Test），油门 5%、时间 2 秒，一次只转一个。',
                   '依次测 A、B、C、D：A 应该是右前风扇转，B 右后，C 左后，D 左前。哪个字母转错了风扇，停下来查电调焊盘那一步。',
                   '风向：转的时候把纸条放在进风口上方，纸条应该被吸向进风口。纸条被吹开，说明这个风扇反了：拔掉 XT60，对调这个风扇的任意两个子弹头，再测。',
                   '转向：风向对了以后，从上往下看进风口：左前和右后应该顺时针转，右前和左后应该逆时针转。',
                   '测完拔掉 XT60 和 USB-C。'],
     checks=['四个风扇都是纸条被吸进去。', '从上看：左前、右后顺时针；右前、左后逆时针。'],
     warnings=['如果风向都对、但绿色电机从上看是逆时针：卖家说的 CW 是从电机那头看的。那就要把每个机舱里前后两个风扇对调（拆外半、换位置、重贴泡棉胶），这一步还没测到之前不要飞。',
               '转向检查是这一章唯一一次通电。首次正式上电和起飞见飞行设置文档（不在本章）。'])

step(id='r-a7z', still='plugging a flexible lead (drawn as a cable and a wiring drawing)', chapter='robot', title='A7Z ↔ 飞控线：一头插飞控 UART1，三根杜邦头插 A7Z 的 14、16、18 号针',
     context=OPEN_CTX + ['sd_dupont_housings'], show=FLIGHT_FRAME + ['battery_backpack_frame'], cables=['c-a7z'],
     wiring=only(BENCH_SIGNAL, groups={'mav'}, title='飞控 UART1 → A7Z 排针',
                 caption='A7Z 从上往下看。SH 插头第 2 位（5 V）空着。'),
     prepare=[dict(item='第 1 章自己做的 A7Z ↔ 飞控线', qty=1, kind='cable')],
     instructions=['SH 插头插进飞控上沿的 UART1 插座。',
                   'A7Z 排针：靠前边的那一排，从左边（天线座那头）数第 7、8、9 根针，就是 14、16、18 号针。',
                   '黑线的杜邦头插 14 号针。',
                   '黄线的杜邦头插 16 号针。',
                   '蓝线的杜邦头插 18 号针。',
                   '线从排针往右，在座盖前面翻过 A7Z 座的右侧壁。',
                   '然后贴着右侧壁外侧的上棱往后走，在座盖边的外面，不要压在座盖上。',
                   '到座子后面，越过电调顶上，到飞控上沿的 UART1 插座；多出来的线绕成小圈，用扎带扎在支架上。'],
     checks=['A7Z 上原来插着的线一根都没动。', 'SH 插头第 2 位是空的。'],
     warnings=['先开鸭子、后开飞行电池；关的时候先拔飞行电池。'])

step(id='r-final', still='final inspection, nothing installed', chapter='robot', title='最后检查：腿、头、进风口',
     context=['rear_pack', 'shell_left', 'shell_right', 'saddle_body'], show=ALL_FLIGHT + ['battery_backpack_frame'] + BACKPACK_BODY + ['head_bottom', 'head_cap'],
     cables=['c-batL', 'c-batR', 'c-FL', 'c-RL', 'c-FR', 'c-RR', 'c-a7z'],
     instructions=['鸭子断电、扶住，用手把左腿慢慢往后摆到头：腿碰到的只能是塑料（背包、翼板），不能碰到任何线。',
                   '右腿同样做一遍。',
                   '用手把头往左、往右、往上、往下各转到头：头不碰翼板、托盘高起来的那块和机舱。',
                   '看四个进风口周围：没有松的线、没有扎带尾巴、没有胶带头。',
                   '两块飞行电池的 XT60 都拔着，平衡线压在绑带下。'],
     checks=['两条腿往后摆到头都只碰塑料。腿往后、往里摆到很偏的角度时，大腿或小腿可能擦到翼板中间下面靠螺丝的那个角：这是已经接受的（正常站立和弯腰时离它 22 mm 以上）。',
             '头转到头都不碰飞行背包。头往后仰到底时，嘴先碰到 A7Z 座和散热器，碰不到臂顶：这也是已经接受的。',
             '进风口周围什么都没有。',
             '以后拿起鸭子只抓身体，不要抓风扇、机舱或翼板的臂。'],
     warnings=['首次上电和第一次飞行不在这一章，见飞行设置文档。'])

# ---------------------------------------------------------------------------------------------- assemble
used = {s['id'] for s in SCREWS}
placed = {s['id'] for s in SCREW_LIST}
assert used == placed, f'screws.json entries not placed in any step: {sorted(used - placed)}'
SCREWS_OUT = [{k: v for k, v in s.items() if k != 'id'} for s in SCREW_LIST]


BODY_ZH = {'left-leg': '左腿（鸭子原有，已装好）', 'right-leg': '右腿（鸭子原有，已装好）', 'neck': '脖子（鸭子原有，已装好）',
           'head': '头（鸭子原有，已装好）', 'camera': '脸和眼眶（鸭子原有，已装好）', 'torso': '躯干（鸭子原有，已装好）'}
BODY_TORSO = {'torso_base', 'ring10_torso', 'ring5_torso', 'saddle_lid'}


def add_duck_body() -> list[str]:
    """The rest of the robot (legs, neck, head, face) for the overview's whole-body view, standalone page only: the MicroDuck
    guide's own meshes (guide/data/guide-data.json, same guide frame, audited by its print gate), copied as they are. No later
    step shows them, and main_fragment() never sees them (the MicroDuck guide build imports this module before writing that file)."""
    src = SIM / 'guide' / 'data' / 'guide-data.json'
    assert src.exists(), f'{src} missing: build the MicroDuck guide first (guide/content/build_guide_data.py)'
    keys = []
    for p in json.loads(src.read_text())['parts']:
        mod, k = p.get('module'), p['key']
        if mod not in BODY_ZH or k in PARTS or (mod == 'torso' and k not in BODY_TORSO):
            continue
        PARTS[k] = dict(key=k, name=BODY_ZH[mod], color='#c9ced6', module='duck', status='assembled',
                        positionB64=p['positionB64'], indexB64=p['indexB64'], bounds=p['bounds'])
        keys.append(k)
    ov = next(s for s in STEPS if s['id'] == 'overview')
    ov['show'] += keys
    ov['instructions'].insert(0, '图里是整只鸭子装好背包后的样子：灰色是鸭子原有的部分（腿、身体、脖子、头），彩色是这一章要装的东西。')
    return keys


def standalone() -> dict:
    return dict(schemaVersion=1, lang='zh', title='MicroDuck 飞行背包组装', subtitle='四个 50 mm 涵道风扇、两块 4S 电池、飞控堆叠',
                revision='FlightPack-D1',
                units='mm', frame='x 向前，y 向左，z 向上（MicroDuck 指南坐标）',
                parts=list(PARTS.values()), chapters=CHAPTERS, steps=STEPS, cables=CABLES, screws=SCREWS_OUT, legend=LEGEND)


# The same chapter inside the MicroDuck guide (guide/data/guide-data.json), so the MicroDuck print gate audits the flight pack
# with the whole robot: printed parts read from guide/print/world (copies of cad/build/*-world.stl), bought parts and the
# backpack in its flight pose under fp_ keys (the backpack moves 1.8 mm forward from the guide's Dual Lock pose: no back plate,
# CAD P-BACKPACK rev 2), duck parts by their guide keys. The first robot step takes the guide's backpack and Dual Lock plate off.
BOUGHT = list(FANS) + ['esc', 'fc', 'mtf01', 'capacitor', 'cap_tape', 'battery_L', 'battery_R']
REMOUNT = BACKPACK_BODY + ['battery_backpack_frame', 'bp_dfr1202', 'bp_switch', 'bp_plug2']
GUIDE_BACKPACK = ['battery_backpack_frame', 'battery_backpack_cap', 'battery_hatch', 'battery_backpack_bars', 'bp_switch', 'bp_battery',
                  'bp_dfr1202', 'bp_plug2', 'bp_plugs', 'duallock_plate', 'duallock_strips']
NOT_IN_GUIDE = {'bp_swap_plugs'}


def main_fragment(world: Path, guide_keys: set) -> dict:
    ren = {k: f'fp_{k}' for k in BOUGHT + REMOUNT}
    def r(lst):
        return [ren.get(k, k) for k in lst if k not in NOT_IN_GUIDE]
    parts = []
    for p in PARTS.values():
        k = p['key']
        if k in ren:
            q = dict(p, key=ren[k])
            parts.append(q)
        elif p['module'] == 'flight-printed':
            src = world / f'{k}.stl'
            assert sha(src) == sha(B / f'{k}-world.stl'), f'{src} differs from cad/build/{k}-world.stl'
            parts.append(p)
        else:
            assert k in guide_keys or k in NOT_IN_GUIDE, f'duck part {k} not in the MicroDuck guide'
    chapters = [dict(c, id='fp-' + c['id'], title='13.' + c['title']) for c in CHAPTERS]
    steps = []
    for s in STEPS:
        t = copy.deepcopy(s)
        t['id'] = 'fp-' + s['id']
        t['chapter'] = 'fp-' + s['chapter']
        for f in ('add', 'show', 'context'):
            t[f] = r(t.get(f, []))
        if 'approach' in t:
            t['approach'] = {ren.get(k, k): v for k, v in t['approach'].items()}
        if s['id'] == 'overview':
            t['show'] = []
        if s['id'] == 'r-open':
            t['remove'] = [k for k in GUIDE_BACKPACK if k in guide_keys]
        steps.append(t)
    screws = [dict(sc, step='fp-' + sc['step']) for sc in SCREWS_OUT]
    cables = copy.deepcopy(CABLES)
    # the kit's cable kinds are a fixed list and the legend holds one label per kind; the MicroDuck legend already labels
    # power-15v and uart, so both flight power leads go under the unused power-20v and the A7Z lead keeps uart unlabelled
    for c in cables:
        c['kind'] = 'uart' if c['kind'] == 'uart' else 'power-20v'
    legend = [{'kind': 'power-20v', 'color': '#c62828', 'label': '飞行背包电源线（电池尾线 12 AWG 红黑，风扇线 16 AWG 红黄黑）'}]
    keys = [p['key'] for p in parts]
    alternates = [{'id': 'flight-pack', 'label': 'Flight pack (four EDFs, wing plate on the pack posts, backpack 6.9 mm behind it, no back plate)',
                   'parts': keys, 'cables': [c['id'] for c in cables], 'neverWith': ['duallock_plate', 'duallock_strips']}]
    return dict(parts=parts, chapters=chapters, steps=steps, screws=screws, cables=cables, legend=legend, alternates=alternates)


if __name__ == '__main__':
    add_duck_body()
    OUT.write_text(json.dumps(standalone(), ensure_ascii=False))
    print(json.dumps(dict(parts=len(PARTS), steps=len(STEPS), screws=len(SCREW_LIST), cables=len(CABLES),
                          lengths=dict(fans={k: v['ext_mm'] for k, v in W.FAN_LEN.items()}, pigtails={k: v['pigtail_mm'] for k, v in W.BAT_LEN.items()}),
                          kb=round(OUT.stat().st_size / 1024)), ensure_ascii=False))
