#!/usr/bin/env python3
"""Check proposed steps.py data fixes in memory, without editing steps.py.

Patches a copy of steps.py source (string replacements listed in PATCHES), rebuilds the step list with the
same Ctx that build_guide_data.py uses (part bounds from guide-data.json, cable lengths from routes.json), and
re-runs the drawn-versus-present state check from steps_audit.py on both the current and the patched steps.
Writes step-fix-check.json. The approach-vector part of the fix is checked by steps_audit.py run on the
patched step list (--sweep).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types

from ia_lib import GUIDE, HERE, load_guide
from steps_audit import INVENTORY, physical_state, resolve

CONTENT = GUIDE / 'content'

PATCHES = [
    # 1. Inventory steps must not install anything (their adds leaked into every later default `show`).
    ("    step('parts', 'start', 'Gather the electronics and kit cables',\n         show=LEGS,",
     "    step('parts', 'start', 'Gather the electronics and kit cables',\n         show=LEGS, bench=True,"),
    ("    step('prints', 'start', 'Print the 13 new parts',\n         show=[], add=new_prints, context=LEGS + TORSO,",
     "    step('prints', 'start', 'Print the 13 new parts',\n         show=[], add=new_prints, context=LEGS, bench=True,"),
    # 2. The XT30 male is soldered on in the converter step but was never installed, so it vanished after chapter 3.
    ("         add=['regulator_insert', 'regulator'],\n         approach={'regulator_insert': [0, 0, 40], 'regulator': [0, 0, 48]},",
     "         add=['regulator_insert', 'regulator'] + ctx.keys('xt30_robot'),\n         approach={'regulator_insert': [-40, 0, 0], 'regulator': [-48, 0, 0], 'xt30_robot': [-20, 0, 0]},"),
    # 3. Harness bench before the torso exists: no torso ghost.
    ("         show=[], add=ctx.keys('xt30_robot'), context=LEGS + TORSO, bench=True, cables=['tether'],",
     "         show=[], add=ctx.keys('xt30_robot'), context=[], bench=True, cables=['tether'],"),
]


def load_ctx():
    spec = importlib.util.spec_from_file_location('bgd', CONTENT / 'build_guide_data.py')
    bgd = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(CONTENT))
    spec.loader.exec_module(bgd)
    g = load_guide()
    parts = {p['key']: {'bounds': p['bounds'], 'module': p['module']} for p in g['parts']}
    routes = json.loads((CONTENT / 'routes.json').read_text())
    _, L = bgd.build_cables(routes)
    return bgd.Ctx(parts, L), g


def build_steps(src: str, ctx):
    mod = types.ModuleType('steps_patched')
    exec(compile(src, 'steps_patched', 'exec'), mod.__dict__)
    _, steps, _ = mod.build(ctx)
    return steps


def state(g, steps):
    gg = dict(g, steps=steps)
    rs, mods = resolve(gg)
    phys = physical_state(rs, mods)
    out = {}
    for s in rs:
        if s['id'] in INVENTORY:
            continue
        drawn = set(s['add']) | set(s['show']) | set(s['ctx'])
        st = phys[s['id']]
        present = set(st['installedBefore']) | set(s['add']) | (set(st['bench'][1]) if st['bench'] else set())
        out[s['id']] = sorted(drawn - present)
    return out, rs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write-patched', help='write the patched steps list (guide-data steps format) to this JSON path')
    args = ap.parse_args()
    ctx, g = load_ctx()
    src = (CONTENT / 'steps.py').read_text()
    patched = src
    applied = []
    for old, new in PATCHES:
        ok = old in patched
        applied.append({'old': old.strip()[:90], 'applied': ok})
        if ok:
            patched = patched.replace(old, new)
    before_steps = build_steps(src, ctx)
    after_steps = build_steps(patched, ctx)
    same_as_data = [s['id'] for s in before_steps] == [s['id'] for s in g['steps']] and all(
        a.get('show') == b.get('show') and a.get('add') == b.get('add') for a, b in zip(before_steps, g['steps']))
    b, _ = state(g, before_steps)
    a, rs_after = state(g, after_steps)
    final_after = next(s for s in rs_after if s['id'] == 'unpowered')
    res = {'patches': applied, 'currentStepsRebuildEqualsGuideData': same_as_data,
           'drawnButNotPresent': {'before': {k: v for k, v in b.items() if v}, 'after': {k: v for k, v in a.items() if v}},
           'countsBefore': sum(len(v) for v in b.values()), 'countsAfter': sum(len(v) for v in a.values()),
           'xt30InFinalStepsAfter': 'xt30_robot' in final_after['show'] or 'xt30_robot' in final_after['add']}
    (HERE / 'step-fix-check.json').write_text(json.dumps(res, indent=1))
    if args.write_patched:
        from pathlib import Path
        Path(args.write_patched).write_text(json.dumps(after_steps))
    print(json.dumps({k: res[k] for k in ('patches', 'currentStepsRebuildEqualsGuideData', 'countsBefore', 'countsAfter', 'xt30InFinalStepsAfter')}, indent=1))
    print('after:', json.dumps(res['drawnButNotPresent']['after'], indent=0)[:3000])


if __name__ == '__main__':
    main()
