"""Put the battery backpack Shawn builds next into guide/print/world: the battery-on-cap redesign (D-037, Michael Lin,
qilinxiaoxiang/microduck_rl 8bce48af) with the V1.40 tool-free battery hatch (print/battery-quickswap-20261101/, approved
by Shawn 2026-11-01), in the guide's Dual Lock pose (D-036, SHIFT_MM from ../duallock-plate-20261031/guide-world.json).

- battery_backpack_frame.stl, battery_backpack_cap.stl, battery_hatch.stl: the V1.40 release parts
  (battery-quickswap-20261101/build/*-world.stl, team-repo robot frame, front plate at x -45) moved SHIFT_MM in x.
- battery_backpack_bars.stl: the two retainer bars from the team repo (cmu/hardware/battery-backpack/stl/
  battery_backpack_bar-world.stl, both bars in one file, unchanged by V1.40), moved SHIFT_MM.
- bp_battery.stl: the battery seat of the redesign (x -74.05..-62.05, |y| <= 15.5, z -22.51..34.49; listing size
  57 x 31 x 12 mm, not measured) as a box, moved SHIFT_MM.
- bp_plugs.stl: plug 1 and the balance plug lying on top of the box, bp_plug2.stl: plug 2 in the front bay; the parking
  boxes of the team checks (cmu/hardware/battery-redesign/checks/checks.json 'plugs'; approximate, plug 1 is not fixed
  to anything), moved SHIFT_MM.
- bp_switch.stl and bp_dfr1202.stl stay as ../duallock-plate-20261031/to_guide_world.py writes them: the redesign keeps
  the switch and DFR1202 holders of V1.20 unchanged.
The V1.20 files these replace are kept once, in their Dual Lock pose, as battery_backpack_frame-v120.stl,
battery_backpack_cap-v120.stl, bp_battery-v120.stl and bp_plugs-v120.stl (not drawn, not audited).
Run after ../duallock-plate-20261031/to_guide_world.py:
    /tmp/microduck-cad-venv/bin/python to_guide_world.py"""
import hashlib, json, shutil
from pathlib import Path
import numpy as np, trimesh

HERE = Path(__file__).resolve().parent
PRINT = HERE.parents[1]
WORLD = PRINT / 'world'
SIM = PRINT.parents[1]
TEAM = SIM / 'microduck_rl' / 'cmu' / 'hardware'
TEAM_COMMIT = '8bce48af'
QS = PRINT / 'battery-quickswap-20261101' / 'build'
DL = json.loads((PRINT / 'back-plate' / 'duallock-plate-20261031' / 'guide-world.json').read_text())
SHIFT_MM = DL['shiftMm'][0]
BAT_LO, BAT_HI = (-74.05, -15.5, -22.51), (-62.05, 15.5, 34.49)   # battery-quickswap build_quickswap.py BAT_LO/BAT_HI
HISTORY = ('battery_backpack_frame.stl', 'battery_backpack_cap.stl', 'bp_battery.stl', 'bp_plugs.stl')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def moved(m):
    m = m.copy(); m.apply_translation([SHIFT_MM, 0.0, 0.0]); return m


def boxes(bounds):
    m = trimesh.util.concatenate([trimesh.creation.box(bounds=[lo, hi]) for lo, hi in bounds])
    assert m.is_watertight and m.is_volume
    return m


def main():
    # keep the V1.20 files once, only while they are still the Dual Lock script's output
    for name in HISTORY:
        old, rec = WORLD / name, WORLD / name.replace('.stl', '-v120.stl')
        if not rec.exists():
            assert sha(old) == DL['sha256'][name], f'{name} is not the V1.20 Dual Lock file; refusing to keep it as v120'
            shutil.copyfile(old, rec)
    plugs = json.loads((TEAM / 'battery-redesign' / 'checks' / 'checks.json').read_text())['plugs']
    src = {'battery_backpack_frame.stl': QS / 'battery_backpack_frame-world.stl',
           'battery_backpack_cap.stl': QS / 'battery_backpack_cap-world.stl',
           'battery_hatch.stl': QS / 'battery_hatch-world.stl',
           'battery_backpack_bars.stl': TEAM / 'battery-backpack' / 'stl' / 'battery_backpack_bar-world.stl'}
    out = {}
    for name, p in src.items():
        m = trimesh.load(p, force='mesh', process=False)
        moved(m).export(WORLD / name)
        out[name] = {'source': str(p.relative_to(SIM)), 'sourceSha256': sha(p), 'moveMm': [SHIFT_MM, 0.0, 0.0]}
    moved(boxes([(BAT_LO, BAT_HI)])).export(WORLD / 'bp_battery.stl')
    out['bp_battery.stl'] = {'source': 'box at the redesign battery seat (listing size, not measured)', 'bounds': [BAT_LO, BAT_HI],
                             'moveMm': [SHIFT_MM, 0.0, 0.0]}
    top = ['plug 1 (on top of the box)', 'balance plug (on top of the box)']
    moved(boxes([(plugs[k]['lo'], plugs[k]['hi']) for k in top])).export(WORLD / 'bp_plugs.stl')
    out['bp_plugs.stl'] = {'source': 'microduck_rl cmu/hardware/battery-redesign/checks/checks.json plugs (approximate parking boxes)',
                           'boxes': {k: plugs[k] for k in top}, 'moveMm': [SHIFT_MM, 0.0, 0.0]}
    k2 = 'plug 2 (front bay)'
    moved(boxes([(plugs[k2]['lo'], plugs[k2]['hi'])])).export(WORLD / 'bp_plug2.stl')
    out['bp_plug2.stl'] = {'source': 'microduck_rl cmu/hardware/battery-redesign/checks/checks.json plugs (approximate parking box)',
                           'boxes': {k2: plugs[k2]}, 'moveMm': [SHIFT_MM, 0.0, 0.0]}
    for name in out:
        m = trimesh.load(WORLD / name, force='mesh', process=True)
        out[name]['closed'] = bool(m.is_watertight and m.is_volume)
        out[name]['bounds'] = np.round(m.bounds, 3).tolist()
        out[name]['sha256'] = sha(WORLD / name)
    rec = {'world': str(WORLD), 'teamRepo': f'qilinxiaoxiang/microduck_rl {TEAM_COMMIT}', 'release': 'V1.40 (Orange: frame, cap, hatch)',
           'shiftMm': [SHIFT_MM, 0.0, 0.0], 'shiftFrom': '../duallock-plate-20261031/guide-world.json',
           'history': {n.replace('.stl', '-v120.stl'): f'V1.20 {n} in the Dual Lock pose (not drawn, not audited)' for n in HISTORY},
           'files': out}
    (HERE / 'guide-world.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({n: [v['closed'], v['bounds']] for n, v in out.items()}))


if __name__ == '__main__':
    main()
