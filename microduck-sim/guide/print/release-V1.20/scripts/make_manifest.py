"""Write the V1.20 incremental release manifest (13-RELEASE-PIPELINE schema 1, pipeline v2).

V1.20 is one Orange plate with three parts. V1.19 (the two caps with 3.0 mm screw-head floors) was never printed
("1.19的两个没打", Shawn 2026-10-17), so its parts travel in this package and V1.19 is superseded unprinted.

- battery_backpack_frame: the V1.18 row (manifest-V1.18.json) with the regenerated frame. The switch in hand is a
  Swann 39 whose 11.5 mm body did not pass the V1.18 10.6 mm hole (Shawn 2026-10-17). The hole is now the Swann
  cutout 12.3 x 27.5 mm, the rocker pocket 14.4 mm wide for the 13.8 mm flange, and the battery pocket starts 0.3 mm
  behind the measured body, so the box is 0.7 mm deeper.
- battery_backpack_cap: the V1.19 row with the cap regenerated 0.7 mm further back (3.0 mm floors, M2 x 8, unchanged
  thread engagement).
- rear_lid: the V1.19 row unchanged (same STL, sha-checked): the layout F cap with 3.0 mm screw-head floors.

The plate is one row centred on the bed (128, 128), 12 mm gaps. Profiles, baseline stock and delivery rules come from
the released manifest-V1.19.json (pinned by sha256).

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.20.json]
"""
import argparse, copy, hashlib, json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
V118_PATH = PRINT / 'release-V1.18/manifest-V1.18.json'
V118_SHA = '4480228b061fab31c8f075773a4c32e3fc13b43427a7d53696bf7e8c80020c5c'
V119_PATH = PRINT / 'release-V1.19/manifest-V1.19.json'
V119_SHA = '7dcb023954c5b3200036a6a8f4b8fd2bbf12433be6d4bd5e82c1bbda97141fc4'
LF = PRINT / 'back-plate/layout-F'
BP = PRINT / 'back-plate/battery-backpack-20261015'
ORANGE = ['rear_lid', 'battery_backpack_frame', 'battery_backpack_cap']   # one row, 12 mm apart, centred on the bed (128, 128)
GAP_MM = 12.0


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    p = Path(p); assert p.is_file(), p
    return {'path': str(p.resolve()), 'sha256': sha(p)}


def printed(path, T):
    m = trimesh.load(path, force='mesh', process=False)
    v, inv = np.unique(m.vertices, axis=0, return_inverse=True)
    m = trimesh.Trimesh(v, inv.reshape(-1)[m.faces], process=False); m.apply_transform(np.array(T, float))
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    area = float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01].sum())
    return area, (m.bounds[1] - m.bounds[0]).round(2).tolist(), m.bounds[0]


def refresh(p, print_stl, note):
    area, size, _ = printed(p['path'], p['sourceToPrint'])
    assert p['flatContact']['minimumAreaMm2'] <= area, f"{p['key']}: bed contact {area:.1f} below {p['flatContact']['minimumAreaMm2']}"
    p['poseCheck'] = dict(printStl=ref(print_stl), bedContactMm2=round(area, 2), printSizeMm=size, note=note)
    p['incrementalEvidence'] = ref(p['incrementalEvidence']['path'])
    p['evidenceAlso'] = [ref(x['path']) for x in p.get('evidenceAlso', [])]
    return p


def reissue(row, world, print_stl, change, supersedes):
    p = copy.deepcopy(row)
    src = ref(world); assert src['sha256'] != row['sha256'], f"{row['key']}: STL did not change"
    p.update(path=src['path'], sha256=src['sha256'], changeReason=change, supersedes=supersedes)
    return refresh(p, print_stl, 'V1.20: contact from the regenerated world STL with the unchanged row sourceToPrint')


def carry(row, world, print_stl, change, supersedes):
    p = copy.deepcopy(row)
    assert sha(world) == row['sha256'], f"{row['key']}: STL changed since V1.19; reissue it instead"
    p.update(changeReason=change, supersedes=supersedes)
    return refresh(p, print_stl, 'V1.20: the unprinted V1.19 row, STL unchanged (sha checked)')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.20.json'); a = ap.parse_args()
    assert sha(V118_PATH) == V118_SHA, 'manifest-V1.18.json changed since V1.20 was set up'
    assert sha(V119_PATH) == V119_SHA, 'manifest-V1.19.json changed since V1.20 was set up'
    m18 = json.loads(V118_PATH.read_text()); m = json.loads(V119_PATH.read_text())
    frame = [p for p in m18['parts'] if p['key'] == 'battery_backpack_frame'][0]
    cap = [p for p in m['parts'] if p['key'] == 'battery_backpack_cap'][0]
    lid = [p for p in m['parts'] if p['key'] == 'rear_lid'][0]
    parts = [
        carry(lid, LF / 'rear_lid-world.stl', LF / 'rear_lid-print.stl',
              'V1.20: the V1.19 layout F cap, unprinted, carried unchanged. ' + lid['changeReason'].removeprefix('V1.19: '),
              lid['supersedes'] + '; the unprinted rear_lid of V1.19'),
        reissue(frame, BP / 'battery_backpack_frame-world.stl', BP / 'battery_backpack_frame-print.stl',
                'V1.20: the V1.18 battery backpack frame refitted to the switch in hand, a Swann 39 (SPST 15 A 125 VAC, solder lugs). Its '
                '11.5 mm body (Shawn 2026-10-17) did not pass the V1.18 10.6 mm hole (REV-31-1387 cutout). The floor hole is now the '
                'Swann cutout 12.3 x 27.5 mm (Swann catalogue 27.4 x 12.3 mm for the same family), the rocker pocket 14.4 mm wide for '
                'the 13.8 mm flange, and the battery pocket starts 0.3 mm behind the measured body, so the box is 27.45 mm deep '
                '(V1.18 26.75). Single watertight body, 713 mm2 rim contact; print gate passed 2026-10-17. Evidence: '
                'back-plate/battery-backpack-20261015/build/build.json, bp_checks.json, README.md.',
                'battery_backpack_frame of release V1.18 (printed 2026-10-15; the switch does not fit its hole)'),
        reissue(cap, BP / 'battery_backpack_cap-world.stl', BP / 'battery_backpack_cap-print.stl',
                'V1.20: the unprinted V1.19 battery backpack cap moved 0.7 mm back with the deeper V1.20 frame. Same 3.0 mm screw-head '
                'floors and three stock M2 x 8; seats and tips move with the cap, 5.0 mm of frame boss thread unchanged. Evidence: '
                'back-plate/battery-backpack-20261015/bp_checks.json screws.',
                'battery_backpack_cap of release V1.18 (printed) and the unprinted V1.19 cap'),
    ]
    by = {p['key']: p for p in parts}
    sizes = {k: printed(by[k]['path'], by[k]['sourceToPrint']) for k in ORANGE}
    width = sum(sizes[k][1][0] for k in ORANGE) + GAP_MM * (len(ORANGE) - 1)
    x0 = 128.0 - width / 2; pl = []
    for key in ORANGE:
        _, size, lo = sizes[key]; y0 = 128.0 - size[1] / 2
        assert 18.0 <= x0 and x0 + size[0] <= 238.0 and 28.0 <= y0 and y0 + size[1] <= 238.0, (key, x0, y0, size)
        pl.append(dict(key=key, copy=1, translation=[round(x0 - float(lo[0]), 4), round(y0 - float(lo[1]), 4), 0.0]))
        x0 += size[0] + GAP_MM
    m['parts'] = parts
    m['placements'] = {'Orange': pl}
    m['processOverrideReason'] = 'No process overrides: V1.20 carries only the Orange plate.'
    m['retiredParts'] = [
        {'part': 'battery_backpack_frame (V1.18)', 'printed': 'V1.18 (Orange)', 'reason': 'the Swann 39 switch body (11.5 mm) does not pass its 10.6 mm hole; replaced by the V1.20 frame with the 12.3 x 27.5 mm Swann cutout'},
        {'part': 'battery_backpack_cap (V1.18)', 'printed': 'V1.18 (Orange)', 'reason': '1.0 mm screw floors and the old box depth; replaced by the V1.20 cap (3.0 mm floors, three M2 x 8)'},
        {'part': 'rear_lid (V1.17)', 'printed': 'V1.17 (Orange)', 'reason': 'its two low 1.0 mm screw floors tore through (IMG_7004); replaced by the V1.20 cap (the unprinted V1.19 design) on the same four M2 x 10'},
    ]
    m['version'] = 'V1.20'
    m['prototypeScope'] = ('V1.20 delta package on one Orange plate: the battery backpack frame refitted to the Swann 39 switch, its cap, and '
                           'the rear converter box cap with 3.0 mm screw-head floors (V1.19, never printed, folded in here).')
    m['knownFitBoundary'] = (m['knownFitBoundary'] + ' V1.20 frame: the Swann 39 switch snaps up through the 12.3 x 27.5 mm floor hole from the '
                             'rocker pocket; wire the switch lead before inserting it.')
    dc = m['deliveryContract']
    dc.update(colors=['Orange'], fileCount=2,
              baseline='printed V1.8 set, the V1.9 Orange plate, V1.17 and V1.18 (both printed 2026-10-15); V1.19 never printed',
              supersedes=['V1.19 (unprinted; its two caps are in this plate)', 'battery_backpack_frame of V1.18', 'battery_backpack_cap of V1.18', 'rear_lid of V1.17'])
    a.out.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(out=str(a.out), orange=[(p['key'], p['poseCheck']['bedContactMm2'], p['poseCheck']['printSizeMm']) for p in parts],
                          placements=pl), indent=1))


if __name__ == '__main__':
    main()
