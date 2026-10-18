"""Build the current assembly handoff from measured connection records."""
from pathlib import Path
import collections
import hashlib
import html
import json
import markdown

P = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    reports = []
    for name in ('electronics-fasteners.json', 'joint-fasteners.json'):
        path = P / 'fastener-audit' / name
        report = json.loads(path.read_text())
        if not report['passed']:
            raise ValueError(f'Unfinished or failed connection audit: {name}')
        reports.append((path, report))
    connections = []
    for path, report in reports:
        for row in report['connections']:
            if not row.get('passed') or not row.get('spec') or row['quantity'] <= 0:
                raise ValueError(f'Unverified installed connection: {row.get("id")}')
            connections.append(dict(row, audit_file=str(path.relative_to(P))))
    ids = [r['id'] for r in connections]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate connection identity')
    totals = collections.Counter()
    for row in connections:
        totals[row['spec']] += row['quantity']
    schedule = ['# Fastener schedule', '',
                'Use the connection name to locate each group. Quantities below are installed quantities; printed spare copies and unopened hardware packs are not counted as installed.', '',
                '## Grouped screw requirements', '']
    schedule += [f'- **{spec}: {qty} screws.**' for spec, qty in totals.items()]
    schedule += ['', '**Additional installed hardware:** 14 M2 nuts; 3 M3 nuts; 4 M3 washers (ID 3.2 mm, OD 7 mm, thickness 0.5 mm); 4 small M2.5 metal washers (DIN 433 / ISO 7092, ID 2.7 mm, OD 5 mm, thickness 0.5 mm) at servo IDs 1, 4, 6 and 9. The small washers set rear-center screw depth and must not be omitted.', '']
    schedule += ['', 'Nuts and washers are specified with each connection below. A thread/type change requires rechecking the mating interface.', '', '## Connection locations and fit', '']
    for row in connections:
        schedule += [f'### {row["id"]} — {row.get("component", row["id"])}', '',
                     f'**{row["quantity"]} × {row["spec"]}.**', '']
        if row.get('washer_spec'):
            schedule += [f"Required washer: {row['washer_spec']}; {row.get('washer_mm', 0)} mm thick.", '']
        extras = []
        for label, key in [('nuts', 'nut_quantity'), ('washers', 'washer_quantity')]:
            if row.get(key):
                extras.append(f'{row[key]} {label}')
        if extras:
            schedule += ['Also required: ' + ', '.join(extras) + '.', '']
        for key, label in [('source_ids', 'Original design part IDs'), ('part_ids', 'Printed part IDs'), ('servo_ids', 'Servo IDs'),
                           ('stack_mm', 'Clamped stack dimensions (mm)'),
                           ('engagement_mm', 'Thread engagement (mm)'),
                           ('tip_beyond_nut_mm', 'Tip beyond nut (mm)'),
                           ('tip_to_blind_end_mm', 'Blind-end clearance (mm)'), ('hole_centers_mm', 'Hole center coordinates (mm)'), ('frame', 'Coordinate frame'), ('coordinate_frame', 'Coordinate frame'), ('axis', 'Screw axis')]:
            if key == 'stack_mm' and row.get('category') == 'rear_center':
                label = 'Screw-bearing seat X coordinate in motor-local frame (mm)'
            if key in row:
                schedule += [f'{label}: {json.dumps(row[key], ensure_ascii=False)}.', '']
        schedule += [f'[Geometric evidence]({row["audit_file"]}).', '']
    schedule_text = '\n'.join(schedule)
    (P / 'FASTENERS.md').write_text(schedule_text)
    ledger = {'problem_ids': ['P5', 'P6'], 'connections': connections,
              'screw_totals_by_spec': dict(totals),
              'source_reports': {str(path.relative_to(P)): sha(path) for path, _ in reports},
              'physical_assembly_verified': False}
    (P / 'assembly-fasteners.json').write_text(json.dumps(ledger, indent=2) + '\n')
    text = (P / 'ASSEMBLY-STEPS.md').read_text() + '\n\n' + (P / 'ASSEMBLY-WIRING.md').read_text() + '\n\n' + schedule_text.replace('# Fastener schedule', '# Connection-by-connection fastener schedule', 1)
    body = markdown.markdown(text, extensions=['toc'])
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MicroDuck current assembly guide</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f5f7f4;color:#18353e;font:18px/1.65 system-ui,sans-serif}main{max-width:1060px;margin:auto;padding:36px 30px 90px}h1{font-size:36px;line-height:1.2}h2{margin-top:48px;border-top:1px solid #ccd9d8;padding-top:20px}h3{margin-top:32px}a{color:#146a77}img{max-width:100%;height:auto}code{overflow-wrap:anywhere;background:#e6eded;padding:2px 4px}li{margin:10px 0}p{overflow-wrap:anywhere}nav{padding:16px 0}nav a{margin-right:20px}@media print{body{background:white}main{padding:0}h2,h3{break-after:avoid}img{max-height:70vh;object-fit:contain}}</style><main><nav><a href="leg-guide-20261006/LEFT-LEG.html">Interactive assembly and wiring</a><a href="START-HERE.html">Current hardware and wiring</a><a href="PRINTING/README.md">Current print jobs</a><a href="output/pdf/MicroDuck_Assembly_Manual.pdf">Printable assembly manual</a><a href="assembly-fasteners.json">Connection data</a></nav>''' + body + '</main></html>'
    (P / 'ASSEMBLY.html').write_text(page)
    print(json.dumps({'guide_generated': True, 'connection_groups': len(connections),
                      'files': ['ASSEMBLY.html', 'FASTENERS.md', 'assembly-fasteners.json']}))

if __name__ == '__main__':
    build()
