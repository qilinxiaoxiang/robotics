#!/usr/bin/env python3
"""Design contract check: the approved concept, written down, checked on the built geometry.

Why: on 2026-10-22 Shawn approved saddle concept B (header at the front edge, USB-C on the rear edge); the first
build_saddle.py written 31 minutes later had the board turned round (header rear, USB-C front, facing the neck) and
D-022 copied the CAD, not the approval. Nothing compared the build with what was approved. Also the CAD modelled a copper
block and a 30 mm fan that were never bought while the Radxa 6530B had been ordered that morning.

A CAD directory that implements an approved concept carries DESIGN-CONTRACT.json:
{
  "schema": "design-contract/1",
  "design": "...", "approved": {"by": "Shawn", "date": "YYYY-MM-DD", "quotes": ["..."]}, "concept_render": "...",
  "state_file": "relative path to the system's CURRENT-STATE.json",
  "parts": {"<parts fact>.<part id>": "<status substring required, e.g. 'in hand'>"},      # bought parts the design is built around
  "geometry": [ {"part": "<name>", "says": "...", "bounds": {"x_min|x_max|y_min|y_max|z_min|z_max": {"lt"|"gt": v}},
                 "size": {"x"|"y"|"z": [lo, hi]}} ],                                           # on build/<part>-world.stl, mm, robot frame
  "forbidden_parts": ["<name>"]                                                                # STLs that must not exist in build/
}
Run: python3 design_contract.py <cad dir>  -> exit 0 PASS, 1 FAIL (each failed line printed), 2 broken contract.
The bounded CAD runner runs this after every build in a directory that has a contract; a failed contract fails the job.
"""
import json, struct, sys
from pathlib import Path
import numpy as np


def stl_bounds(path: Path):
    data = path.read_bytes()
    if len(data) >= 84:
        n = struct.unpack('<I', data[80:84])[0]
        if 84 + n * 50 == len(data):
            arr = np.frombuffer(data[84:], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))
            v = arr['v'].reshape(-1, 3)
            return v.min(0), v.max(0)
    v = np.array([[float(x) for x in ln.split()[1:4]] for ln in data.decode('ascii', 'ignore').splitlines() if ln.strip().startswith('vertex')])
    return v.min(0), v.max(0)


def check(cad_dir: Path, out=print) -> int:
    cf = cad_dir / 'DESIGN-CONTRACT.json'
    try:
        c = json.loads(cf.read_text())
    except (OSError, json.JSONDecodeError) as e:
        out(f'{cf}: cannot read ({e})'); return 2
    if c.get('schema') != 'design-contract/1' or not c.get('approved', {}).get('quotes'):
        out(f'{cf}: needs schema design-contract/1 and approved.quotes'); return 2
    fails = []
    build = cad_dir / 'build'
    if c.get('parts'):
        sf = (cad_dir / c.get('state_file', '')).resolve()
        try:
            facts = json.loads(sf.read_text())['facts']
        except (OSError, KeyError, json.JSONDecodeError):
            out(f'{cf}: state_file {sf} unreadable'); return 2
        for key, need in c['parts'].items():
            fact, _, part = key.partition('.')
            val = facts.get(fact, {}).get('value')
            entry = val.get(part) if isinstance(val, dict) else None
            status = json.dumps(entry, ensure_ascii=False) if entry is not None else ''
            if need not in status:
                fails.append(f'part {key}: CURRENT-STATE says {status or "nothing"}, contract needs "{need}"')
    axes = {'x': 0, 'y': 1, 'z': 2}
    for g in c.get('geometry', []):
        f = build / f"{g['part']}-world.stl"
        if not f.exists():
            fails.append(f"{g['part']}: build/{f.name} missing ({g.get('says', '')})"); continue
        lo, hi = stl_bounds(f)
        for k, cond in (g.get('bounds') or {}).items():
            ax, end = k.split('_'); v = (lo if end == 'min' else hi)[axes[ax]]
            for op, lim in cond.items():
                ok = v < lim if op == 'lt' else v > lim
                if not ok:
                    fails.append(f"{g['part']}: {k} = {v:.1f}, contract needs {op} {lim} ({g.get('says', '')})")
        for ax, (a, b) in (g.get('size') or {}).items():
            s = (hi - lo)[axes[ax]]
            if not a <= s <= b:
                fails.append(f"{g['part']}: size {ax} = {s:.1f}, contract needs {a}..{b} ({g.get('says', '')})")
    for n in c.get('forbidden_parts', []):
        if (build / f'{n}-world.stl').exists():
            fails.append(f'{n}: build/{n}-world.stl exists but the contract forbids this part')
    for line in fails:
        out('FAIL ' + line)
    out(f"design contract {c.get('design', '')}: {'PASS' if not fails else str(len(fails)) + ' failure(s)'} ({cf})")
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(check(Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()))
