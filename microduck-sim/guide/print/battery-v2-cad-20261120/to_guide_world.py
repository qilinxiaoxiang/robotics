"""Put the battery backpack V2 rev B, its dock base and the screwed bench box into guide/print/world for build_guide_data.py
and the print gate (guide chapter 12 rewrite, 2026-11-20).

- bv2_*.stl: the rev B frame and cap and every bought part of the backpack, copied unchanged from build/ (guide frame =
  backpack frame: front face x -45 on the four OpenRB pack posts, screwed straight on; no Dual Lock plate, CURRENT-STATE
  backpack_swap_plugs 2026-11-10 "现在没装背板，是直接battery pack装在openRB盒子上的").
- dock_*.stl: the dock base and its two Keystone 5209 leaves and the PJ-005A jack from ../battery-dock-20261120/build/,
  whose z is height above the floor with the robot seated. Seated, the pads sit 10.9 mm above the floor and at guide
  z -46, so the dock is drawn DOCK_DZ = -46 - 10.9 - 4.0 in z: 4 mm lower than seated, so the leaves show uncompressed
  and clear of the pads in the standing guide pose.
- rear_frame.stl, rear_lid.stl, xl4015_left.stl, xl4015_right.stl, pd5991.stl: the bench box back in its screwed pose,
  copied unchanged from ../back-plate/layout-F/ (the Dual Lock plate is not fitted, so the box screws onto the posts as
  before 2026-10-31). duallock_plate.stl and duallock_strips.stl stay on disk as a record; the guide no longer draws them.
Writes world-sources.json here with the sha256 of every source and output.
    ~/.venvs/microduck-cad/bin/python to_guide_world.py"""
import hashlib, json
from pathlib import Path
import trimesh

HERE = Path(__file__).resolve().parent
PRINT = HERE.parent
WORLD = PRINT / 'world'
B = HERE / 'build'
DOCK = PRINT / 'battery-dock-20261120' / 'build'
LF = PRINT / 'back-plate' / 'layout-F'
DOCK_DZ = -46.0 - 10.9 - 4.0
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

COPY = {
    'bv2_frame.stl': B / 'battery_v2_frame-world.stl',
    'bv2_cap.stl': B / 'battery_v2_cap-world.stl',
    'bv2_battery.stl': B / 'parts/battery_2S_3000-world.stl',
    'bv2_foam.stl': B / 'parts/battery_foam_pad-world.stl',
    'bv2_pololu.stl': B / 'parts/Pololu_2813-world.stl',
    'bv2_pololu_tape.stl': B / 'parts/Pololu_tape-world.stl',
    'bv2_dfr1202.stl': B / 'parts/DFR1202-world.stl',
    'bv2_dfr_tape.stl': B / 'parts/DFR1202_tape-world.stl',
    'bv2_xiao.stl': B / 'parts/XIAO_SAMD21-world.stl',
    'bv2_xiao_tape.stl': B / 'parts/XIAO_tape-world.stl',
    'bv2_button.stl': B / 'parts/16_mm_LED_button-world.stl',
    'bv2_diode.stl': B / 'parts/Schottky_1N5822-world.stl',
    'bv2_pad_plus.stl': B / 'parts/contact_pad_plus-world.stl',
    'bv2_pad_minus.stl': B / 'parts/contact_pad_minus-world.stl',
    'rear_frame.stl': LF / 'rear_frame-world.stl',
    'rear_lid.stl': LF / 'rear_lid-world.stl',
    'xl4015_left.stl': LF / 'xl4015_top_7V-world.stl',
    'xl4015_right.stl': LF / 'xl4015_mid_5V-world.stl',
    'pd5991.stl': LF / 'pd5991_F-world.stl',
}
MOVED = {
    'dock_base.stl': DOCK / 'dock_base-world.stl',
    'dock_leaf_plus.stl': DOCK / 'parts/keystone_5209_plus-world.stl',
    'dock_leaf_minus.stl': DOCK / 'parts/keystone_5209_minus-world.stl',
    'dock_jack.stl': DOCK / 'parts/pj005a-world.stl',
}


def main():
    out = {'dockDzMm': DOCK_DZ, 'files': {}}
    for name, src in COPY.items():
        m = trimesh.load(src, force='mesh', process=False)
        m.export(WORLD / name)
        out['files'][name] = {'source': str(src.relative_to(PRINT)), 'sourceSha256': sha(src), 'sha256': sha(WORLD / name)}
    for name, src in MOVED.items():
        m = trimesh.load(src, force='mesh', process=False)
        m.apply_translation([0.0, 0.0, DOCK_DZ])
        m.export(WORLD / name)
        out['files'][name] = {'source': str(src.relative_to(PRINT)), 'sourceSha256': sha(src), 'moveMm': [0.0, 0.0, DOCK_DZ],
                              'sha256': sha(WORLD / name)}
    (HERE / 'world-sources.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v['sha256'][:12] for k, v in out['files'].items()}, indent=1))


if __name__ == '__main__':
    main()
