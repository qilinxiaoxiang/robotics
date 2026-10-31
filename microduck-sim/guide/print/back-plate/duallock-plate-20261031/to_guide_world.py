"""Put the Dual Lock back plate (DESIGN-CONTRACT.json, 2026-10-31) and both backpacks in their Dual Lock pose into
guide/print/world for build_guide_data.py and the print gate.

- duallock_plate.stl: build/duallock_plate-world.stl as built (x -48..-45 on the four pack posts, four M2 x 6).
- duallock_strips.stl: the mated Dual Lock pair as two pads on the plate's rear face, |y| <= 13.5 (inside the 27 mm
  between the screw heads), upper pad z 12..25.5, lower pad z -33..2 (off the battery backpack's lead window, z 4.6..9.4),
  DL_MM thick (x -48 - DL_MM .. -48). Strip size and mated thickness are not measured: the pads mark the area, not
  Shawn's strips.
- Both backpacks, unchanged prints, moved SHIFT_MM in x from their screwed pose: their front plate (x -47..-45) now sits
  on the Dual Lock at x -48 - DL_MM. Sources are the release-named world STLs of layout-F (bench box) and
  battery-backpack-20261015 (to_guide_world.py's list; the DFR1202 and its pads become one closed solid there too).
  bp_swap_plugs.stl is not written: the swap plugs leave the backpack at its lower left rear (CURRENT-STATE
  backpack_swap_plugs) and are no longer modelled in the pack channel.
The bench box cables (pw-15v, pw-15v-link, pw-7v, pi-lead) move with the box in build_guide_data.py, which reads
SHIFT_MM from guide-world.json written here.
    /tmp/microduck-cad-venv/bin/python to_guide_world.py"""
import hashlib, json, shutil
from pathlib import Path
import numpy as np, trimesh, manifold3d as m3

HERE = Path(__file__).resolve().parent
PRINT = HERE.parents[1]
WORLD = PRINT / 'world'
LF = PRINT / 'back-plate' / 'layout-F'
BP = PRINT / 'back-plate' / 'battery-backpack-20261015'
PLATE_REAR_X = -48.0          # build.json params X_REAR
OLD_SEAT_X = -45.0            # backpack front plates sat on the pack posts here (x -47..-45)
DL_MM = 5.7                   # 3M Dual Lock mated thickness, assumed (not measured)
SHIFT_MM = round(PLATE_REAR_X - DL_MM - OLD_SEAT_X, 3)   # -8.7

SHIFTED = {  # world name -> source in its screwed pose
    'rear_frame.stl': LF / 'rear_frame-world.stl', 'rear_lid.stl': LF / 'rear_lid-world.stl',
    'xl4015_left.stl': LF / 'xl4015_top_7V-world.stl', 'xl4015_right.stl': LF / 'xl4015_mid_5V-world.stl',
    'pd5991.stl': LF / 'pd5991_F-world.stl',
    'battery_backpack_frame.stl': BP / 'battery_backpack_frame-world.stl',
    'battery_backpack_cap.stl': BP / 'battery_backpack_cap-world.stl',
    'bp_switch.stl': BP / 'build/switch_swann-world.stl', 'bp_battery.stl': BP / 'build/battery-world.stl',
    'bp_plugs.stl': BP / 'build/plugs-world.stl'}
STRIPS = [((-48.0 - DL_MM, -13.5, 12.0), (-48.0, 13.5, 25.5)), ((-48.0 - DL_MM, -13.5, -33.0), (-48.0, 13.5, 2.0))]


def man(m):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))


def tri(u):
    u = u.to_mesh()
    t = trimesh.Trimesh(np.asarray(u.vert_properties)[:, :3], np.asarray(u.tri_verts), process=False)
    assert t.is_watertight and t.is_volume
    return t


def moved(m):
    m = m.copy(); m.apply_translation([SHIFT_MM, 0.0, 0.0]); return m


def main():
    out = {}
    shutil.copyfile(HERE / 'build/duallock_plate-world.stl', WORLD / 'duallock_plate.stl')
    out['duallock_plate.stl'] = 'build/duallock_plate-world.stl'
    s = None
    for lo, hi in STRIPS:
        b = trimesh.creation.box(bounds=[lo, hi]); s = man(b) if s is None else s + man(b)
    tri(s).export(WORLD / 'duallock_strips.stl')
    out['duallock_strips.stl'] = f'two pads |y| <= 13.5, z 12..25.5 and -33..2, x {-48.0 - DL_MM}..-48 (area, not measured strips)'
    for name, src in SHIFTED.items():
        moved(trimesh.load(src, force='mesh', process=False)).export(WORLD / name)
        out[name] = f'{src.relative_to(PRINT)} moved {SHIFT_MM} mm in x'
    d = tri(man(trimesh.load(BP / 'build/dfr1202-world.stl', force='mesh', process=True))
            + man(trimesh.load(BP / 'build/dfr_pads-world.stl', force='mesh', process=True)))
    moved(d).export(WORLD / 'bp_dfr1202.stl')
    out['bp_dfr1202.stl'] = f'back-plate/battery-backpack-20261015/build/dfr1202-world.stl + dfr_pads-world.stl moved {SHIFT_MM} mm in x'
    sha = {n: hashlib.sha256((WORLD / n).read_bytes()).hexdigest() for n in out}
    rec = {'world': str(WORLD), 'shiftMm': [SHIFT_MM, 0.0, 0.0], 'dualLockMatedMm': DL_MM, 'dualLockMeasured': False,
           'plateRearX': PLATE_REAR_X, 'oldSeatX': OLD_SEAT_X,
           'cableShift': {'cables': ['pw-15v', 'pw-15v-link', 'pw-7v', 'pi-lead'], 'pointsWithXBelow': OLD_SEAT_X},
           'notWritten': {'bp_swap_plugs.stl': 'swap plugs leave the backpack at its lower left rear (CURRENT-STATE backpack_swap_plugs); not modelled'},
           'sources': out, 'sha256': sha}
    (HERE / 'guide-world.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(WORLD, SHIFT_MM, {n: v[:12] for n, v in sha.items()})


if __name__ == '__main__':
    main()
