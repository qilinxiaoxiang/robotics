#!/usr/bin/env python3
"""Verify the current MicroDuck design: the released incremental print set, the guide built from the same geometry,
the print gate on that guide, the screw stock rule and the live pages. Read-only; it never rebuilds anything.

--scope design   passes when every digital check passes.
--scope project  runs the design checks, then lists the physical work that no file can prove (printing and fitting the
                 current release, bench bring-up, commissioning, the visual-pickup goal). It passes only when
                 PROJECT-CONTEXT.json records each of those as accepted with evidence.
--offline        skips the live-page hash comparison (for use without the tailnet).

Sources: PROJECT-CONTEXT.json current_build.current_incremental_print_release (release) and current_build.design_gate
(served files, physical acceptance); guide/content/interference-audit/gate-receipt.json (run_gate.py).
Writes guide/current-design-verification.json and prints it; exit 0 on pass.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

GUIDE = Path(__file__).resolve().parent
SIM = GUIDE.parent
STOCK_M2 = {4, 6, 8, 10}          # memory microduck-screw-stock: even M2 lengths only
# M2.6x6 and M2.6x8: loose screws in the OMX kit bags (Shawn, 2026-10-13); M2.6x8 is also each XL330's factory rear centre.
STOCK_OTHER = {'M2.5x6', 'M2.5x8', 'M2.6x6', 'M2.6x8'}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: str | Path) -> Path:
    p = Path(str(p)).expanduser()
    return p if p.is_absolute() else SIM / p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scope', choices=['design', 'project'], default='design')
    ap.add_argument('--offline', action='store_true')
    args = ap.parse_args()
    ctx = json.loads((SIM / 'PROJECT-CONTEXT.json').read_text())
    cb = ctx['current_build']
    rel_ = cb['current_incremental_print_release']
    gate_cfg = cb['design_gate']
    errors: list[dict] = []
    checks: dict[str, dict] = {}

    def fail(check: str, code: str, detail) -> None:
        errors.append({'check': check, 'code': code, 'detail': detail})

    # 1. Release: manifest parts are the current files; binding, native review and archives match the context.
    c = checks['release'] = {'version': rel_['version'], 'status': rel_['status']}
    if rel_['status'] != 'RELEASED':
        fail('release', 'not_released', rel_['status'])
    manifest = json.loads(rel(rel_['manifest']).read_text())
    if manifest.get('version') != rel_['version']:
        fail('release', 'manifest_version', [manifest.get('version'), rel_['version']])
    c['parts'] = len(manifest['parts'])
    for part in manifest['parts']:
        p = rel(part['path'])
        if not p.is_file() or sha(p) != part['sha256']:
            fail('release', 'part_changed_since_release', part['key'])
    binding = json.loads(rel(rel_['sourceBoundVerification']).read_text())
    c['binding'] = binding.get('status')
    if binding.get('status') != 'RELEASED':
        fail('release', 'binding_not_released', binding.get('status'))
    # Every released plate is centred on the 256 mm bed (Shawn 2026-10-15: the printed V1.18 plate was 38 / 63 mm off centre).
    # Recomputed from the preparation model bounds, so releases prepared before the pipeline check are covered too.
    prep = json.loads((rel(rel_['sourceBoundVerification']).parent / 'preparation.json').read_text())
    offsets = {}
    for row in prep['rows']:
        b = [np.array(x) for x in row['modelBounds']]
        lo = np.min([x[0][:2] for x in b], axis=0); hi = np.max([x[1][:2] for x in b], axis=0)
        offsets[f"{row['color']}_{row['machine']}"] = ((lo + hi) / 2 - 128).round(2).tolist()
    c['plateCentreOffsetMm'] = offsets
    off_centre = {k: v for k, v in offsets.items() if max(abs(x) for x in v) > 1.0}
    if off_centre:
        fail('release', 'plate_not_centred', off_centre)
    native = json.loads(rel(rel_['nativeReview']).read_text())
    c['nativeReviewPassed'] = native.get('passed')
    if native.get('passed') is not True:
        fail('release', 'native_review', native.get('passed'))
    p = rel(rel_['archive'])
    if not p.is_file() or sha(p) != rel_['archiveSha256']:
        fail('release', 'archive_hash', str(p))
    # Downloads copy: the SD zip itself, or (Shawn 2026-10-14, no zip) the folder from print/make_delivery_folder.py: one subfolder per printer holding exactly
    # the delivered machine files, byte for byte.
    p = rel(rel_['downloadsCopy'])
    if p.is_dir():
        index = json.loads((rel(rel_['archive']).parent / 'delivery-index.json').read_text())
        want = sorted((f['filename'], f['sha256']) for f in index['files'])
        have = sorted((f.name, sha(f)) for sub in ('X1C', 'Elegoo') for f in (p / sub).glob('*') if f.is_file() and not f.name.startswith('.'))
        extra = sorted(f.name for f in p.iterdir() if f.is_file() and not f.name.startswith('.'))
        previews = sorted(f'{col}-plate.png' for col in {f['color'] for f in index['files']})   # make_delivery_folder.py
        c['downloadsFolderFiles'] = len(have)
        if have != want or extra != previews or sorted(x.name for x in p.iterdir() if x.is_dir()) != ['Elegoo', 'X1C']:
            fail('release', 'downloadsCopy_folder', str(p))
    elif not p.is_file() or sha(p) != rel_['archiveSha256']:
        fail('release', 'downloadsCopy_hash', str(p))
    world = {p.name: sha(p) for p in (GUIDE / 'print/world').glob('*.stl')}
    # A colour-only reprint (pipeline v2 colourOnlyReprint) is the exact 10/1 stock STL of the instances it replaces, so the
    # guide keeps drawing that part from the full build; it must match its stock record instead of a world file.
    stock = {str(r['object_id']): r['sha256'] for r in json.loads(rel(manifest['baselineStock']['path']).read_text())['copy_records']
             if 'manifest_instance_index' in r} if manifest.get('baselineStock') else {}
    colour_only = [pt for pt in manifest['parts'] if str(pt.get('colourOnlyReprint', '')).strip()]
    c['colourOnlyReprints'] = len(colour_only)
    for pt in colour_only:
        if not pt.get('replacesStockIds') or any(stock.get(str(i)) != pt['sha256'] for i in pt['replacesStockIds']):
            fail('release', 'colour_only_reprint_not_stock', pt['key'])
    released = {sha(rel(pt['path'])) for pt in manifest['parts'] if rel(pt['path']).is_file() and pt not in colour_only}
    c['partsInGuideWorld'] = sum(1 for h in released if h in world.values())
    if c['partsInGuideWorld'] != len(released):
        fail('release', 'released_part_missing_from_guide_geometry', len(released) - c['partsInGuideWorld'])

    # 2. Print gate receipt bound to the current guide data and world STLs.
    receipt_p = GUIDE / 'content/interference-audit/gate-receipt.json'
    receipt = json.loads(receipt_p.read_text()) if receipt_p.is_file() else {}
    c = checks['printGate'] = {'checkedAt': receipt.get('checkedAt'), 'guideRevision': receipt.get('guideRevision'),
                               'results': {k: v.get('passed') for k, v in receipt.get('checks', {}).items()}}
    if not receipt.get('passed') or not receipt.get('ranJobs'):
        fail('printGate', 'gate_not_passed', receipt.get('checks') and {k: v for k, v in receipt['checks'].items() if not v['passed']})
    data_sha = sha(GUIDE / 'data/guide-data.json')
    if receipt.get('inputs', {}).get('guideData') != data_sha:
        fail('printGate', 'guide_data_changed_since_gate', 'rerun content/interference-audit/run_gate.py')
    if receipt.get('inputs', {}).get('world') != world:
        changed = sorted(set(world.items()) ^ set(receipt.get('inputs', {}).get('world', {}).items()))
        fail('printGate', 'world_geometry_changed_since_gate', [n for n, _ in changed][:10])

    # 3. Guide HTML built from the current guide data.
    html = (GUIDE / 'dist/MICRODUCK-BUILD.html').read_text(errors='ignore')
    checks['guide'] = {'dataSha256': data_sha[:16], 'embedded': data_sha in html}
    if data_sha not in html:
        fail('guide', 'html_not_built_from_current_data', 'rerun build_guide.py')

    # 4. Screws: only stocked lengths in fasteners.json and the step text.
    fast = json.loads((GUIDE / 'content/fasteners.json').read_text())
    specs = []
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ('spec', 'screw') and isinstance(v, str):
                    specs.append(v)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(fast)
    text = (GUIDE / 'content/steps.py').read_text()
    bad = set()
    for s in specs + re.findall(r'M2(?:\.\d)?\s*[x×]\s*\d+', text):
        m = re.match(r'M(2(?:\.\d)?)\s*[x×]\s*(\d+)', s.replace(' ', ''))
        if not m:
            continue
        d, l = m.group(1), int(m.group(2))
        if (d == '2' and l not in STOCK_M2) or (d != '2' and f'M{d}x{l}' not in STOCK_OTHER):
            bad.add(f'M{d}x{l}')
    checks['screws'] = {'specsRead': len(specs), 'unstocked': sorted(bad)}
    if bad:
        fail('screws', 'unstocked_screw', sorted(bad))

    # 5. Live pages: the served bytes equal the local files.
    live = checks['live'] = {'skipped': args.offline, 'files': {}}
    if not args.offline:
        for route, local in gate_cfg['servedFiles'].items():
            want = sha(rel(local))
            r = subprocess.run(['curl', '-sf', '-H', 'Accept-Encoding: identity', gate_cfg['baseUrl'] + route],
                               capture_output=True, timeout=120)
            got = hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None
            live['files'][route] = got == want
            if got != want:
                fail('live', 'served_bytes_differ' if got else 'not_served', route)

    # 6. Project scope: physical acceptance recorded in the context.
    pending = []
    if args.scope == 'project':
        for item in gate_cfg['physicalAcceptance']:
            if not (item.get('accepted') is True and item.get('evidence')):
                pending.append(item['id'])
        checks['physical'] = {'pending': pending}
        for p in pending:
            fail('physical', 'not_accepted', p)

    report = {'checkedAt': datetime.datetime.now().astimezone().isoformat(timespec='seconds'), 'scope': args.scope,
              'passed': not errors, 'release': rel_['version'], 'checks': checks, 'errors': errors}
    (GUIDE / 'current-design-verification.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
