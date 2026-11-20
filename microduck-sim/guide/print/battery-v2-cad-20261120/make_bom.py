"""Write BOM.json and assembly-guide-ch12.json for the battery backpack V2 rev B from the built guide itself (2026-11-20).

BOM.json lists every item that a chapter 12 ('backpack') step of guide/data/guide-data.json puts in its prepare list, with
its quantity and the steps that use it, and nothing else. The source of each item comes from SOURCES below (purchase
records purchase-decision-20261120*.json, roboclub/INVENTORY.md, CURRENT-STATE); an item no rule matches gets
"source": null and is printed as UNSOURCED, so a part named in the guide without a source cannot pass silently.
    python3 make_bom.py [--live-url URL]"""
import argparse, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parents[1]
DATA = GUIDE / 'data' / 'guide-data.json'
HTML = GUIDE / 'dist' / 'MICRODUCK-BUILD.html'
RECEIPT = GUIDE / 'content' / 'interference-audit' / 'gate-receipt.json'
CHAPTER = 'backpack'

# (substring of the guide item text, source). First match wins, so specific rules come first.
SOURCES = [
    ('PV6F240SS-331', 'DigiKey EG4731-ND (purchase-decision-20261120.json)'),
    ('Pololu 2813', 'DigiKey 2183-2813-ND (purchase-decision-20261120.json)'),
    ('Crazepony', 'Amazon B08LZ8L4YD (purchase-decision-20261120.json)'),
    ('100 kΩ', 'DigiKey CF14JT100KCT-ND (purchase-decision-20261120.json)'),
    ('33 kΩ', 'DigiKey CF14JT33K0CT-ND (purchase-decision-20261120.json)'),
    ('10 kΩ', 'DigiKey CF14JT10K0CT-ND (purchase-decision-20261120.json)'),
    ('120 Ω', 'RoboClub cabinet D (INVENTORY.md: 120 Ω)'),
    ('1N4148', 'RoboClub cabinet F, "small-signal 100 V 0.2 A" (INVENTORY.md); marking to be checked'),
    ('1N5822', 'RoboClub cabinet F (INVENTORY.md: 1N5822 Schottky 40 V 3 A)'),
    ('B3B-XH-A', 'DigiKey 455-2248-ND (purchase-decision-20261120.json)'),
    ('异丙醇', 'consumable already used in earlier guide chapters (Isopropyl alcohol and a tissue)'),
    ('扳手或尖嘴钳', 'needle-nose pliers: RoboClub tool wall (not listed in INVENTORY.md)'),
    ('USB-C 数据线', 'owned: the USB-A to USB-C cable from the OMX-AI kit (chapter 1 list; used to flash the OpenRB)'),
    ('杜邦线 30 cm', 'owned: 30 cm jumper wires (chapter 1 list, head 5 V lead stock)'),
    ('XIAO SAMD21', 'RoboClub cabinet C drawer, 3 sealed (inventory 2026-10-20)'),
    ('Keystone 615', 'DigiKey 36-615-ND (purchase-decision-20261120-charging.json)'),
    ('Keystone 5209', 'DigiKey 36-5209-ND (purchase-decision-20261120-charging.json)'),
    ('PJ-005A', 'DigiKey CP-5-ND (purchase-decision-20261120-charging.json)'),
    ('Sortfle', 'Amazon B07J4CLKZ7 (purchase-decision-20261120-charging.json)'),
    ('XT30 公头', 'RoboClub stock (brief 2026-11-20: XT30 plugs from RoboClub)'),
    ('XT30 母头', 'RoboClub stock (brief 2026-11-20: XT30 plugs from RoboClub)'),
    ('AWG', 'RoboClub stock silicone wire (brief 2026-11-20: 16/20/26 AWG from RoboClub)'),
    ('DFR1202', 'owned: on the robot now, kept from the old backpack'),
    ('旧电池背包', 'owned: on the robot now (CURRENT-STATE backpack_swap_plugs)'),
    ('BatteryV2-B1', 'print: BatteryV2-B1 Orange plate (battery-v2-cad-20261120/slices)'),
    ('BatteryDock-A1', 'print: BatteryDock-A1 Orange plate (battery-dock-20261120/slices)'),
    ('HTRC B3', "owned: Shawn's HTRC B3 balance charger"),
    ('3M 泡沫', "Shawn's stock 3M foam tape"),
    ('M2 × 6 self-tapping', 'reused: the four M2 x 6 of the old backpack plus two from the M2 screw stock (even lengths 4/6/8/10)'),
    ('M2 × 8 self-tapping', 'M2 screw stock (even lengths 4/6/8/10)'),
    ('热缩管', 'RoboClub soldering bench; not listed in INVENTORY.md, to be checked'),
    ('电烙铁', 'RoboClub soldering bench (INVENTORY.md)'),
    ('万用表', 'chapter 1 tools: multimeter with continuity beep'),
    ('剥线钳', 'chapter 1 tools: wire stripper for 18 to 28 AWG'),
    ('螺丝刀', 'chapter 1 tools: Phillips #0 and #1 screwdrivers'),
    ('标签纸', 'chapter 1 tools: marker pen and masking tape'),
    ('胶布', 'chapter 1 tools: electrical tape'),
    ('异丙醇', None),
    ('19 mm 扳手', None),
    ('11 mm 扳手', None),
]


def source_of(item):
    for key, src in SOURCES:
        if key in item:
            return key, src
    return None, None


def qty_num(q):
    return q if isinstance(q, (int, float)) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--live-url', default='http://today.tailfc7c94.ts.net:8766/MICRODUCK-BUILD.html')
    ap.add_argument('--live-sha256', default=None)
    a = ap.parse_args()
    d = json.loads(DATA.read_text())
    steps = [s for s in d['steps'] if s['chapter'] == CHAPTER]
    items, order = {}, []
    for s in steps:
        for p in s.get('prepare', []) or []:
            it = p['item']
            if it not in items:
                key, src = source_of(it)
                items[it] = {'part': it, 'kind': p.get('kind'), 'source': src, 'qty': p['qty'], 'used_in_step': [],
                             'note': p.get('note')}
                order.append(it)
            row = items[it]
            if s['id'] not in row['used_in_step']:
                row['used_in_step'].append(s['id'])
                if len(row['used_in_step']) > 1:
                    a_, b_ = qty_num(row['qty']), qty_num(p['qty'])
                    if p.get('kind') == 'fastener' and a_ is not None and b_ is not None:
                        row['qty'] = a_ + b_          # screws: each step uses its own
                    elif a_ is not None and b_ is not None:
                        row['qty'] = max(a_, b_)      # the same part, tool or battery used again
    # the bundler moves screw rows out of prepare into d['screws'] (one record per screw, from fasteners.json)
    ids = {s['id'] for s in steps}
    for r in d.get('screws', []):
        if r['step'] not in ids:
            continue
        it = f"{r['spec'].replace(' TAP', '')} self-tapping screw (TAP)"
        if it not in items:
            key, src = source_of(it)
            items[it] = {'part': it, 'kind': 'fastener', 'source': src, 'qty': 0, 'used_in_step': [], 'note': None}
            order.append(it)
        items[it]['qty'] += 1
        if r['step'] not in items[it]['used_in_step']:
            items[it]['used_in_step'].append(r['step'])
    out = {'chapter': CHAPTER, 'generated_from': str(DATA.relative_to(GUIDE.parent)),
           'guide_data_sha256': hashlib.sha256(DATA.read_bytes()).hexdigest(),
           'items': [{k: v for k, v in items[i].items() if v is not None or k == 'source'} for i in order]}
    (HERE / 'BOM.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    chap = next(c for c in d['chapters'] if c['id'] == CHAPTER)
    receipt = json.loads(RECEIPT.read_text()) if RECEIPT.exists() else {}
    ev = {'chapter_id': CHAPTER, 'title': chap['title'], 'step_ids': [s['id'] for s in steps],
          'guide_revision': d.get('revision'),
          'guide_data_sha256': out['guide_data_sha256'],
          'build_html_sha256': hashlib.sha256(HTML.read_bytes()).hexdigest() if HTML.exists() else None,
          'gate_receipt': str(RECEIPT.relative_to(GUIDE.parent)),
          'gate_passed': receipt.get('passed'), 'gate_checked_at': receipt.get('checkedAt'),
          'gate_guide_revision': receipt.get('guideRevision'), 'gate_checks': receipt.get('checks'),
          'live_url': a.live_url, 'live_sha256': a.live_sha256,
          'live_is_this_build': bool(a.live_sha256) and HTML.exists() and a.live_sha256 == hashlib.sha256(HTML.read_bytes()).hexdigest(),
          'screws': [{'id': r['id'], 'spec': r['spec'], 'step': r['step']} for r in d.get('screws', [])
                     if r['step'] in {s['id'] for s in steps}]}
    (HERE / 'assembly-guide-ch12.json').write_text(json.dumps(ev, indent=1, ensure_ascii=False) + '\n')
    for i in order:
        r = items[i]
        print(('UNSOURCED ' if r['source'] is None else '') + f"{r['qty']} x {r['part']}  [{', '.join(r['used_in_step'])}]")
    print(len(order), 'items;', sum(1 for i in order if items[i]['source'] is None), 'unsourced')


if __name__ == '__main__':
    main()
