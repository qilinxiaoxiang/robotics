#!/usr/bin/env python3
"""Battery backpack V2 rev M assembly guide (Chinese, standalone page): writes guide-data.json for the shared guide-kit viewer.

    /tmp/microduck-cad-venv/bin/python microduck-sim/guide/print/battery-v2-cad-20261120/guide/build_backpack_guide.py
    python3 guide-kit/build_guide.py --data microduck-sim/guide/print/battery-v2-cad-20261120/guide/guide-data.json \
        --out microduck-sim/guide/print/battery-v2-cad-20261120/guide/dist/BATTERY-PACK-BUILD.html

Shawn 2026-11-20: "新电池包的3D打印件和拼装指南也单独出一份吧". One source for the steps: chapter 12 of the MicroDuck guide
(guide/content/steps.py), read here from the built guide/data/guide-data.json (same meshes, same screws, same guide frame,
audited by the MicroDuck print gate). This page takes the chapter's steps as they are, the backpack parts and screws, and
the rest of the robot as grey context (the same body set as the flight-pack page), and puts a first page in front of them
with what to print (times and grams from slices/release-BatteryV2-M1), what to buy and what moves over from the old backpack.
The bench converter box is not drawn: the robot carries the old battery backpack today, which the guide does not model.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAD = HERE.parent
SIM = CAD.parents[2]
SRC = SIM / 'guide' / 'data' / 'guide-data.json'
REL = CAD / 'slices' / 'release-BatteryV2-M1'
OUT = HERE / 'guide-data.json'

BODY_ZH = {'left-leg': '左腿（鸭子原有）', 'right-leg': '右腿（鸭子原有）', 'neck': '脖子（鸭子原有）',
           'head': '头（鸭子原有）', 'camera': '脸和眼眶（鸭子原有）', 'torso': '躯干（鸭子原有）'}
BODY_TORSO = {'torso_base', 'ring10_torso', 'ring5_torso'}
BODY_KEYS = {'rear_pack': 'OpenRB 盒子（躯干后面，背包拧在它的四根柱子上）', 'shell_left': '左侧壳（鸭子原有）',
             'shell_right': '右侧壳（鸭子原有）', 'saddle_body': 'A7Z 座（躯干顶上）', 'sd_a7z_pcb': 'A7Z 板',
             'sd_heatsink_6530b': 'A7Z 散热器', 'head_bottom': '头的下壳（鸭子原有）', 'head_cap': '头盖（鸭子原有）'}
GREY = '#c9ced6'
PRINTERS = (('X1C-CoolPlate', 'Bambu X1C（Cool Plate 光面板）'), ('Elegoo', 'Elegoo Centauri Carbon'), ('H2S', 'Bambu H2S'))
CHAPTERS = [
    {'id': 'start', 'title': '0. 开始之前', 'intro': False,
     'summary': '要打印的一盘、要买的一块电池、从旧背包上拆下来再用的东西和工具。'},
    {'id': 'move', 'title': '1. 拆旧背包，装新框架和 DFR1202',
     'summary': '拆下旧背包，留下开关、DFR1202 和全部插头线（不剪、不焊）；新框架用四颗 M2 × 6 拧到 OpenRB 盒子上，贴好 DFR1202。'},
    {'id': 'fit', 'title': '2. 装电池、开关和后盖',
     'summary': '电池竖着推进电池柱，开关卡进新后盖，接好插头 2 和插头 1，盖上后盖，接插头 3 和 4。'},
    {'id': 'use', 'title': '3. 开机和充电',
     'summary': '按开关开机；充电时关开关，把白色 3 针插头从后盖右上缺口勾出来插到 HTRC B3 上，不开盖。'},
]
CHAPTER_OF = {'bv2-strip': 'move', 'bv2-frame': 'move', 'bv2-dfr': 'move',
              'bv2-battery': 'fit', 'bv2-switch': 'fit', 'bv2-plugs-inside': 'fit', 'bv2-cap': 'fit', 'bv2-plugs': 'fit',
              'bv2-power-up': 'use', 'bv2-charge': 'use'}


def print_times() -> list[str]:
    """One line per printer from the Downloads-format delivery the release wrote (file names carry the slicer's time)."""
    lines = []
    deliv = REL / 'run' / 'delivery-folder'
    files = sorted(deliv.rglob('*.gcode*')) + sorted((REL / 'delivery-x1c-cool').glob('*.gcode*')) + sorted((REL / 'delivery-h2s').glob('*.gcode*'))
    grams = {}
    for name, gpath in (('X1C-CoolPlate', REL / 'run-x1c-cool/Orange/plate_1.gcode'), ('H2S', REL / 'run-h2s/Orange/plate_1.gcode'),
                        ('Elegoo', REL / 'run/native/Orange_Elegoo/plate_1.gcode')):
        m = re.search(r'(?:total filament weight \[g\] :|total filament used \[g\] =) ([\d.]+)', gpath.read_text(errors='ignore'))
        grams[name] = float(m.group(1))
    for key, label in PRINTERS:
        hit = [f for f in files if (key == 'X1C-CoolPlate' and 'X1C-CoolPlate' in f.name) or (key == 'Elegoo' and 'Elegoo' in f.name)
               or (key == 'H2S' and 'H2S' in f.name)]
        assert hit, f'no sliced file for {key}'
        t = re.search(r'_(\d+h\d+m|\d+m)\.gcode', hit[0].name).group(1).replace('h', ' h ').replace('m', ' min')
        lines.append(f'· {label}：{t}，{grams[key]:.0f} g，文件 {key}/{hit[0].name}')
    return lines


def main():
    g = json.loads(SRC.read_text())
    ch12 = [s for s in g['steps'] if s['chapter'] == 'backpack']
    assert [s['id'] for s in ch12] == list(CHAPTER_OF), [s['id'] for s in ch12]
    bv2 = {p['key']: p for p in g['parts'] if p['key'].startswith('bv2_')}
    body = {}
    for p in g['parts']:
        k, mod = p['key'], p.get('module')
        if k in BODY_KEYS:
            body[k] = dict(p, name=BODY_KEYS[k], color=GREY, module='duck', status='assembled')
        elif mod in BODY_ZH and (mod != 'torso' or k in BODY_TORSO):
            body[k] = dict(p, name=BODY_ZH[mod], color=GREY, module='duck', status='assembled')
    keep = set(bv2) | set(body)
    steps = []
    for s in ch12:
        t = copy.deepcopy(s)
        t['chapter'] = CHAPTER_OF[s['id']]
        for f in ('add', 'show', 'context'):
            t[f] = [k for k in t.get(f, []) if k in keep]
        if not t.get('bench'):
            t['show'] = [k for k in body if k not in t['add']] + [k for k in t['show'] if k not in body]
        t.pop('remove', None)
        if s['id'] == 'bv2-strip':
            t['still'] = 'the old backpack comes off; the old backpack is not drawn, the robot is shown without it'
        steps.append(t)
    times = print_times()
    overview = {
        'id': 'overview', 'chapter': 'start', 'title': '新电池背包：先把东西备齐',
        'still': 'inventory page: the finished robot with the new backpack is shown, nothing is installed',
        'show': list(body) + list(bv2), 'add': [], 'context': [],
        'instructions': [
            '图里是装好新背包的鸭子：灰色是鸭子原有的部分，彩色是这份指南要装的东西。',
            '这次只换大电池、重做背包：开关、DFR1202 和全部插头线从旧背包上拆下来照原样再用，不剪线、不焊接。充电不用开盖：关开关，把电池的白色 3 针插头从后盖右上缺口勾出来，直接插到 HTRC B3 上。',
            '一、要打印（橙色一盘：背包框架和后盖，共两件，不用支撑；文件在 ~/Downloads/zhengxia_MicroDuck_BatteryV2-M1/，每台机器一个文件夹，Orange-plate.png 是这一盘的样子）：',
            *times,
            '· 打印好不用修、不用钻、不用锉，拿下来直接用。',
            '二、要买（只有这一样）：',
            '· Crazepony 2S 3000 mAh 锂电池（Amazon B08LZ8L4YD），一块。带 XT30 主插头、白色 3 针平衡插头和一根不用的 DC5.5 线。',
            '三、从旧背包上拆下来再用（第 1 章拆）：',
            '· 船型开关（Swann 39），连着它的开关线，开关线两头各一个 XT30（插头 1 和插头 2 的开关一侧）。',
            '· DFR1202 5 V 降压板，连着它的三根线：输入线（XT30 公头）、插头 3 线（XT30 母头，去舵机）、插头 4 线（MR30 母头，去 A7Z）。',
            '· 四颗 M2 × 6 自攻螺丝（旧框架拧在 OpenRB 盒子上的那四颗），新框架原样拧回去。',
            '四、自己的库存：',
            '· M2 自攻螺丝：M2 × 8 两颗、M2 × 6 两颗（后盖用）。',
            '· 3M 1 mm 泡沫双面胶（贴 DFR1202 和电池背面）、异丙醇和布、一小段胶布（包 DC5.5 圆头）。',
            '· HTRC B3 平衡充电器（充电用）。',
            '五、工具：细杆螺丝刀（杆径不超过 4 mm）、万用表（量新电池电压）、剪刀。',
        ],
        'warnings': ['锂电池压坏或短路会起火：装的时候不要硬塞，不要压引线；充电时人不要走开。'],
    }
    screws = [s for s in g['screws'] if s['step'] in CHAPTER_OF]
    assert {s['step'] for s in screws} == {'bv2-frame', 'bv2-cap'}, {s['step'] for s in screws}
    data = dict(schemaVersion=1, lang='zh', title='MicroDuck 电池背包 V2（rev M）组装',
                subtitle='2S 3000 mAh 电池竖装，旧开关卡在后盖上，充电只插白色 3 针头',
                revision='BatteryV2-M1', units='mm', frame='x 向前，y 向左，z 向上（MicroDuck 指南坐标）',
                parts=list(body.values()) + list(bv2.values()), chapters=CHAPTERS, steps=[overview] + steps,
                cables=[], screws=screws, legend=[])
    OUT.write_text(json.dumps(data, ensure_ascii=False))
    print(json.dumps(dict(parts=len(data['parts']), steps=len(data['steps']), screws=len(screws), times=times,
                          kb=round(OUT.stat().st_size / 1024)), ensure_ascii=False))


if __name__ == '__main__':
    main()
