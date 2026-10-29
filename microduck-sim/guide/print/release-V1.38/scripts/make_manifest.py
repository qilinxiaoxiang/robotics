"""Write the V1.38 incremental release manifest (D-034, Shawn 2026-10-29: "为什么不贴着板子", "出文件"): one Orange plate with
the rear converter box cap. On the printed V1.20 cap the screw floors broke off while the screws were tightened: each 3 mm
floor ended 1.5 mm (low pair) or 0.75 mm (top pair) short of its board, so the screw pulled it across the gap. The four
columns now run onto the boards and the cap rim stops 0.3 mm short of the frame rim (back-plate/layout-F/build_f.py
RIM_GAP, CAP_COL, TOP_COL; checks in back-plate/lid-columns-20261029/). Same four M2 x 10; the frame is unchanged.
The row is the V1.20 rear_lid row (same pose, sourceToPrint and profile) with the regenerated STL. Profiles, baseline stock
and the delivery contract come from manifest-V1.37.json.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import copy, hashlib, json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
V137 = PRINT / 'release-V1.37/manifest-V1.37.json'
V120 = PRINT / 'release-V1.20/manifest-V1.20.json'
LF = PRINT / 'back-plate/layout-F'
LC = PRINT / 'back-plate/lid-columns-20261029'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


def printed(path, T):
    m = trimesh.load(path, force='mesh', process=False)
    m.apply_transform(np.array(T, float)); m.apply_translation([0, 0, -m.bounds[0, 2]])
    area = float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01].sum())
    return area, (m.bounds[1] - m.bounds[0]).round(2).tolist(), m.bounds[0]


def print_mesh(path, T):
    m = trimesh.load(path, force='mesh'); m.apply_transform(np.array(T, float)); m.apply_translation([0, 0, -m.bounds[0, 2]]); return m


def carried_thin_walls(world, T):
    """The 1.2 mm wall rule (2026-10-19) postdates the V1.17/V1.20 cap. Every thin region of the new cap must also be in the
    printed V1.20 cap (centre within 2 mm, same height band): those are unchanged geometry, allowed with their reason. A thin
    region the V1.20 cap does not have fails here."""
    import sys
    sys.path.insert(0, str(PRINT.parents[1] / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
    import wall_check
    regs = lambda p: [r for r in wall_check.check(print_mesh(p, T), (), 'rear_lid')['regions'] if r.get('status') == 'FAIL']
    new, old = regs(world), regs(REL / 'retired/rear_lid-V1.20.stl')
    # below print z 7.5 (robot x < -59.6, behind the new rim and the column fronts) the two caps are the same solid
    import manifold3d as m3
    man = lambda t: m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
    box = m3.Manifold.cube([200, 200, 7.5]).translate([-50, -50, -1])
    a, b_ = man(print_mesh(world, T)) ^ box, man(print_mesh(REL / 'retired/rear_lid-V1.20.stl', T)) ^ box
    same_below = float((a - b_).volume() + (b_ - a).volume())
    assert same_below < 0.5, f'rear_lid: caps differ below print z 7.5 by {same_below:.2f} mm3'
    axes = [np.array([y + 32.05, z + 36.02]) for y, z in (json.loads((LF / 'layout_f.json').read_text())['capScrew']['axisYZ'],
                                                          json.loads((LF / 'layout_f.json').read_text())['capScrew2']['axisYZ'],
                                                          *json.loads((LF / 'layout_f.json').read_text())['capTopScrews']['axesYZ'])]
    out = []
    for r in new:
        b = np.array(r['bbox']); c = b.mean(0)
        match = [o for o in old if np.linalg.norm(np.array(o['bbox']).mean(0) - c) <= 2.0 and abs(np.array(o['bbox'])[1, 2] - b[1, 2]) <= 1.0]
        on_wall = r['minMm'] >= 1.15          # the modelled 1.2 mm cap wall, measured a few hundredths under on a curve
        assert match or b[1, 2] < 7.5 or on_wall, f'rear_lid: thin region {r["bbox"]} is not in the printed V1.20 cap'
        if on_wall and not match and b[1, 2] >= 7.5:
            why = f'the modelled 1.2 mm cap wall at the rim corner, measured {r["minMm"]} on the curve (ray sampling), not a thinner wall'
        elif any(np.all(b[0, :2] - 0.5 <= a) and np.all(a <= b[1, :2] + 0.5) for a in axes):
            why = ('driver bore tube behind a screw seat (dia 4.4 bore in the dia 5.6 column, 0.6 mm wall), as printed in V1.17 and '
                   'V1.20; with the columns bearing on the boards (D-034) tightening no longer loads it')
        elif b[1, 2] <= 1.5:
            why = 'feathered edge where a side window cuts the rounded back edge on the bed face, as printed in V1.17 and V1.20'
        else:
            why = 'rounded rear edge where a side window cuts it, as printed in V1.17 and V1.20'
        out.append(dict(bbox=(b + [[-0.3] * 3, [0.3] * 3]).round(3).tolist(), minMm=max(0.05, round(r['minMm'] - 0.02, 3)), reason=why))
    return out


def main():
    m = json.loads(V137.read_text())
    lid = copy.deepcopy([p for p in json.loads(V120.read_text())['parts'] if p['key'] == 'rear_lid'][0])
    ck = json.loads((LC / 'checks.json').read_text())
    assert all(ck['ok'][k] is True for k in ('columnsBearOnBoards', 'frameClearMm', 'nothingElseTouched')) and abs(ck['ok']['rimGapMm'] - 0.3) < 0.01, ck['ok']
    world = LF / 'rear_lid-world.stl'; src = ref(world)
    assert src['sha256'] != lid['sha256'], 'rear_lid STL did not change since V1.20'
    area, size, lo = printed(world, lid['sourceToPrint'])
    assert area >= lid['flatContact']['minimumAreaMm2'], area
    lid.update(
        path=src['path'], sha256=src['sha256'], quantity=1,
        changeReason=('D-034 (Shawn 2026-10-29: "降压板背包盖子 打螺丝的时候直接把螺丝挡板打下来了", "为什么不贴着板子", "出文件"): the '
                      'four screw columns run onto the boards (low pair to the 5991 PCB face x -51.6, top pair to the 7 V XL4015 hole '
                      'pads x -51.86) and the cap rim stops 0.3 mm short of the frame rim, so the columns locate the cap and the screws '
                      'press each floor onto a board instead of pulling it across a gap. Floors 4.5 mm (low) and 3.74 mm (top); seats, '
                      'the four M2 x 10 and their thread engagement unchanged; the 7 V board is now clamped at its top corners. Ray-'
                      'checked: column fronts within 0.06 mm of the board on 99-100 % of the annulus, nearest other board part 4.65 mm '
                      'from a column axis, cap 0.249 mm from the frame at the closest (the flattened top columns, as V1.20). Print gate '
                      'passed 2026-10-29.'),
        poseOrigin=lid['poseOrigin'].replace('stand up to 4.5 mm proud of the rim', 'stand up to 7.8 mm proud of the rim')
                                    .replace('12.5 mm tall (open side up', '%.1f mm tall over the column fronts, rim at 7.7 mm (open side up' % size[2])
                                    .replace('1 mm floors bridging', 'floors bridging'),
        poseCheck=dict(printStl=ref(LF / 'rear_lid-print.stl'), bedContactMm2=round(area, 2), printSizeMm=size,
                       note='V1.38: contact from the regenerated world STL with the unchanged V1.20 sourceToPrint'),
        incrementalEvidence=ref(LC / 'checks.json'),
        evidenceAlso=[ref(LC / 'check_lid_columns.py'), ref(LC / 'DESIGN-CONTRACT.json'), ref(LF / 'checks.json'), ref(LF / 'layout_f.json'),
                      ref(LF / 'build_f.py'), ref(LF / 'raycast_cap_screws.json')],
        supersedes='rear_lid of release V1.20 (printed; its screw floors broke off while the screws were tightened)')
    lid['thinWallAllowances'] = carried_thin_walls(world, lid['sourceToPrint'])
    pl = [dict(key='rear_lid', copy=1, translation=[round(128.0 - size[0] / 2 - float(lo[0]), 4), round(128.0 - size[1] / 2 - float(lo[1]), 4), 0.0])]
    m.update(version='V1.38', parts=[lid], placements={'Orange': pl}, processOverrides={},
             processOverrideReason='No process overrides: the V1.20 Orange profile and pose for the box cap.',
             retiredParts=[{'part': 'rear_lid (V1.20)', 'printed': 'V1.20 (Orange)',
                            'reason': 'its screw floors hung short of the boards and broke off while the screws were tightened; replaced by the V1.38 cap whose columns bear on the boards (D-034)'}],
             prototypeScope='V1.38: the rear converter box cap on one Orange plate.',
             knownFitBoundary=('Column fronts on the boards with the cap rim 0.3 mm short of the frame rim; at +-0.2 mm print tolerance the rim '
                               'gap stays 0.1..0.5 mm. Printed sizes not measured.'))
    m.pop('deferred', None)
    m['deliveryContract'] = dict(m['deliveryContract'], colors=['Orange'], filesPerColor=2, fileCount=2, baseline='printed releases through V1.37',
                                 status='INCREMENTAL_REPLACEMENT', supersedes=['rear_lid of V1.20 (Orange)'])
    (REL / 'manifest-V1.38.json').write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(contact=round(area, 1), size=size, placements=pl)))


if __name__ == '__main__':
    main()
