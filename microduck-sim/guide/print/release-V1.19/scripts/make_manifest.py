"""Write the V1.19 incremental release manifest (13-RELEASE-PIPELINE schema 1, pipeline v2).

V1.19 is a delta package on one Orange plate: the two screw caps with 3.0 mm screw-head floors. Shawn printed V1.18
(frame and cap) on 2026-10-15, so the backpack frame is not carried forward ("1.9里面, 1.8可以移除"). The plate is laid
out as one row and its whole footprint centred on the bed: the V1.18 plate printed 38 mm left and 63 mm forward of centre. Shawn's photo IMG_7004
(2026-10-15) shows the printed V1.17 box cap with the 1.0 mm floors under its two low hidden screws torn into open holes
after the cap was taken off ("螺丝挡板换成更厚的 相应螺丝也可以换成更长的"). The battery backpack cap of V1.18 has the
same 1.0 mm floor detail, so it is reissued too. Both frames are byte-identical to the printed V1.17 / V1.18 frames.

- rear_lid: the V1.17 row (manifest-V1.17.json) with the regenerated layout F cap; floors grow 2.0 mm forward, stock
  M2 x 10, seats and thread engagement unchanged.
- battery_backpack_cap: the V1.18 row (manifest-V1.18.json) with the regenerated cap; seats 2.0 mm further back,
  M2 x 6 -> M2 x 8, same tips and engagement.

Profiles, baseline stock and delivery rules come from the released manifest-V1.18.json (pinned by sha256).

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.19.json]
"""
import argparse, copy, hashlib, json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
V117_PATH = PRINT / 'release-V1.17/manifest-V1.17.json'
V117_SHA = '00af527717f3e4e7c5a0ba3042b2d0ac3958ab08d9603c6b6eb5fbad8736cb9d'
V118_PATH = PRINT / 'release-V1.18/manifest-V1.18.json'
V118_SHA = '4480228b061fab31c8f075773a4c32e3fc13b43427a7d53696bf7e8c80020c5c'
LF = PRINT / 'back-plate/layout-F'
BP = PRINT / 'back-plate/battery-backpack-20261015'
ORANGE = ['rear_lid', 'battery_backpack_cap']   # one row, 12 mm apart, the whole footprint centred on the bed (128, 128)
GAP_MM = 12.0
FRAMES = {'rear_frame': (V117_PATH, LF / 'rear_frame-world.stl'), 'battery_backpack_frame': (V118_PATH, BP / 'battery_backpack_frame-world.stl')}


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


def reissue(row, world, print_stl, change, supersedes):
    p = copy.deepcopy(row)
    src = ref(world); assert src['sha256'] != row['sha256'], f"{row['key']}: STL did not change"
    area, size, _ = printed(src['path'], p['sourceToPrint'])
    assert p['flatContact']['minimumAreaMm2'] <= area, f"{row['key']}: bed contact {area:.1f} below {p['flatContact']['minimumAreaMm2']}"
    p.update(path=src['path'], sha256=src['sha256'], changeReason=change, supersedes=supersedes)
    p['poseCheck'] = dict(printStl=ref(print_stl), bedContactMm2=round(area, 2), printSizeMm=size,
                          note='V1.19: contact from the regenerated world STL with the unchanged row sourceToPrint')
    p['incrementalEvidence'] = ref(p['incrementalEvidence']['path'])
    p['evidenceAlso'] = [ref(x['path']) for x in p.get('evidenceAlso', [])]
    return p


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.19.json'); a = ap.parse_args()
    assert sha(V117_PATH) == V117_SHA, 'manifest-V1.17.json changed since V1.19 was set up'
    assert sha(V118_PATH) == V118_SHA, 'manifest-V1.18.json changed since V1.19 was set up'
    m17 = json.loads(V117_PATH.read_text()); m = json.loads(V118_PATH.read_text())
    for key, (man, stl) in FRAMES.items():   # the frames stay as released: only the caps are reprinted
        row = [p for p in json.loads(man.read_text())['parts'] if p['key'] == key][0]
        assert sha(stl) == row['sha256'], f'{key}: frame changed; V1.19 reissues only the caps'
    lid = [p for p in m17['parts'] if p['key'] == 'rear_lid'][0]
    cap = [p for p in m['parts'] if p['key'] == 'battery_backpack_cap'][0]
    parts = [
        reissue(lid, LF / 'rear_lid-world.stl', LF / 'rear_lid-print.stl',
                'V1.19: the V1.17 layout F cap with each of its four screw-head floors thickened from 1.0 to 3.0 mm. The printed V1.17 '
                'cap\'s two low floors tore into open holes when it was taken off (Shawn 2026-10-15, IMG_7004). The floors grow 2.0 mm '
                'forward (column fronts x -53.1 low, -52.6 top), so the head seats (x -56.1 / -55.6), the four stock M2 x 10 and the '
                'thread engagement (3.9 / 4.6 mm) are unchanged; the +y low column is flattened to 0.5 mm above the USB-C socket. '
                'Gaps: 1.5 mm to the 5991 PCB, 1.25 mm to the 7 V board, cap to boards 0.287 mm (unchanged walls). Evidence: '
                'back-plate/layout-F/raycast_cap_screws.json and post_build.json.',
                'rear_lid of release V1.17 (printed 2026-10-15; its two low screw floors tore) and V1.16 / V1.15 / V1.14 / V1.13 / V1.11'),
        reissue(cap, BP / 'battery_backpack_cap-world.stl', BP / 'battery_backpack_cap-print.stl',
                'V1.19: the V1.18 battery backpack cap with its three screw-head floors thickened from 1.0 to 3.0 mm, the same detail '
                'that tore on the printed V1.17 box cap (Shawn 2026-10-15, IMG_7004). The seats move 2.0 mm back (x -69.35) and the '
                'screws go from M2 x 6 to M2 x 8 (stock), so the tips (x -61.35) and the 5.0 mm of frame boss thread are unchanged. '
                'Evidence: back-plate/battery-backpack-20261015/bp_checks.json screws.',
                'battery_backpack_cap of release V1.18'),
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
    m['processOverrideReason'] = 'No process overrides: V1.19 carries only the Orange plate.'
    m['retiredParts'] = [
        {'part': 'rear_lid (V1.17)', 'printed': 'V1.17 (Orange)', 'reason': 'its two low 1.0 mm screw floors tore through (IMG_7004); replaced by the V1.19 cap with 3.0 mm floors on the same four M2 x 10'},
        {'part': 'battery_backpack_cap (V1.18)', 'printed': 'V1.18 (Orange)', 'reason': 'same 1.0 mm screw floors; replaced by the V1.19 cap with 3.0 mm floors and three M2 x 8'},
    ]
    m['version'] = 'V1.19'
    m['prototypeScope'] = ('V1.19 delta package: the rear converter box cap and the battery backpack cap with 3.0 mm screw-head floors on one '
                           'Orange plate (Shawn 2026-10-15, IMG_7004: the V1.17 cap floors tore). Both frames stay as printed in V1.17 / V1.18.')
    m['knownFitBoundary'] = (m['knownFitBoundary'].replace('cap 3 x M2 x 6, fixing 4 x M2 x 6', 'cap 3 x M2 x 8, fixing 4 x M2 x 6')
                             + ' V1.19 caps: the box cap takes the same four M2 x 10 as V1.17 and fits the printed V1.17 frame; tighten until the '
                             'cap sits on the rim and stop, the heads bear on printed floors.')
    dc = m['deliveryContract']
    dc.update(colors=['Orange'], fileCount=2,
              baseline='printed V1.8 set, the V1.9 Orange plate, V1.17 and V1.18 (both printed 2026-10-15)',
              supersedes=['rear_lid of V1.17', 'battery_backpack_cap of V1.18'])
    a.out.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(out=str(a.out), orange=[(p['key'], p['poseCheck']['bedContactMm2'], p['poseCheck']['printSizeMm']) for p in parts],
                          placements=pl), indent=1))


if __name__ == '__main__':
    main()
