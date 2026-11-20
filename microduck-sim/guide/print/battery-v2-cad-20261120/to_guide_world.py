"""Put the battery backpack V2 rev M and the screwed bench box into guide/print/world for build_guide_data.py and the
print gate (guide chapter 12, rev M minimal backpack, 2026-11-20).

- bv2_*.stl: the rev M frame and cap and every bought part of the backpack, copied unchanged from build/ (guide frame =
  backpack frame: front face x -45 on the four OpenRB pack posts, screwed straight on; no Dual Lock plate, CURRENT-STATE
  backpack_swap_plugs 2026-11-10 "现在没装背板，是直接battery pack装在openRB盒子上的"). bv2_switch.stl is the Swann 39 body
  envelope only: its two snap wings are spring clips that fold through the cutout, so their keep-out box (checks.py)
  is not drawn as a solid in the guide (with it the bench push into the cap collides with the cap, run_gate 2026-11-20).
- Rev M has no dock: the dock base, leaves and jack (print/battery-dock-20261120/, deferred) are not drawn. Any bv2_* or
  dock_* file in world/ that this script does not write is stale and is removed, because the gate globs both prefixes.
- rear_frame.stl, rear_lid.stl, xl4015_left.stl, xl4015_right.stl, pd5991.stl: the bench box back in its screwed pose,
  copied unchanged from ../back-plate/layout-F/ (the Dual Lock plate is not fitted, so the box screws onto the posts as
  before 2026-10-31).
Writes world-sources.json here with the sha256 of every source and output.
    ~/.venvs/microduck-cad/bin/python to_guide_world.py"""
import hashlib, json
from pathlib import Path
import trimesh

HERE = Path(__file__).resolve().parent
PRINT = HERE.parent
WORLD = PRINT / 'world'
B = HERE / 'build'
LF = PRINT / 'back-plate' / 'layout-F'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

COPY = {
    'bv2_frame.stl': [B / 'battery_v2_frame-world.stl'],
    'bv2_cap.stl': [B / 'battery_v2_cap-world.stl'],
    'bv2_battery.stl': [B / 'parts/battery_2S_3000-world.stl'],
    'bv2_foam.stl': [B / 'parts/battery_foam_pad-world.stl'],
    'bv2_dfr1202.stl': [B / 'parts/DFR1202-world.stl'],
    'bv2_dfr_tape.stl': [B / 'parts/DFR1202_tape-world.stl'],
    'bv2_switch.stl': [B / 'parts/Swann_39_switch-world.stl'],
    'bv2_plug1.stl': [B / 'parts/plug_1-world.stl'],
    'bv2_plug2.stl': [B / 'parts/plug_2-world.stl'],
    'bv2_balance.stl': [B / 'parts/balance_plug-world.stl'],
    'rear_frame.stl': [LF / 'rear_frame-world.stl'],
    'rear_lid.stl': [LF / 'rear_lid-world.stl'],
    'xl4015_left.stl': [LF / 'xl4015_top_7V-world.stl'],
    'xl4015_right.stl': [LF / 'xl4015_mid_5V-world.stl'],
    'pd5991.stl': [LF / 'pd5991_F-world.stl'],
}


def main():
    out = {'files': {}, 'removedStale': []}
    for name, srcs in COPY.items():
        ms = [trimesh.load(src, force='mesh', process=False) for src in srcs]
        m = ms[0] if len(ms) == 1 else trimesh.util.concatenate(ms)
        m.export(WORLD / name)
        out['files'][name] = {'source': [str(src.relative_to(PRINT)) for src in srcs], 'sourceSha256': [sha(src) for src in srcs],
                              'sha256': sha(WORLD / name)}
    for p in sorted(list(WORLD.glob('bv2_*.stl')) + list(WORLD.glob('dock_*.stl'))):
        if p.name not in COPY:
            p.unlink(); out['removedStale'].append(p.name)
    (HERE / 'world-sources.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v['sha256'][:12] for k, v in out['files'].items()}, indent=1), out['removedStale'])


if __name__ == '__main__':
    main()
