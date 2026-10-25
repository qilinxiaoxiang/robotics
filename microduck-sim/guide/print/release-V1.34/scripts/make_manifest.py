"""Write the V1.34 incremental release manifest: the left and right sole press molds with their screw-down lids, one
Black plate, nothing else
(V1.33 is printed, Shawn 2026-10-24). The molds are tools for gluing the bike inner tube sole onto the printed feet with
E6000 (build-pack-20260913/procurement/feet-sole-20261018/press_mold.py, README "Inner tube sole in a press mold").
Profiles, baseline stock and the delivery contract come from manifest-V1.33.json (pinned by sha256). The molds print
cavity up in their source frame (identity, dropped to the bed) with a fast tool process (FAST): Shawn (2026-10-24) rejected 5-6 h
for a tool. The stock Black profile is 0.1 mm layers, 4 walls, 30 % infill (6 h, mostly internal solid infill under the
height-field terraces); the rubber takes up 0.28 mm steps.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import hashlib, json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
V133 = PRINT / 'release-V1.33/manifest-V1.33.json'
SOLE = PRINT.parents[1] / 'build-pack-20260913/procurement/feet-sole-20261018'
GAP_MM = 12.0
FAST = {'layer_height': '0.28', 'wall_loops': '3', 'sparse_infill_density': '10%', 'top_shell_layers': '3',
        'bottom_shell_layers': '3', 'enable_support': '0'}
FOOT = {'left': 'community-44.stl', 'right': 'community-46.stl'}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


def printed(path):
    m = trimesh.load(path, force='mesh', process=False)
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    area = float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01].sum())
    return area, (m.bounds[1] - m.bounds[0]).round(2).tolist(), m.bounds[0]


def mold_row(side, check):
    stl = SOLE / f'press-mold-{side}.stl'
    area, size, _ = printed(stl); src = ref(stl); c = check[side]
    return dict(
        key=f'press_mold_{side}', color='Black', quantity=1, decision='addition', replacesStockIds=[],
        path=src['path'], sha256=src['sha256'],
        sourceFrame=f'{FOOT[side]} frame (mm; foot flat bottom at z = 0, foot above); cavity up',
        sourceToPrint=np.eye(4).tolist(), flatContact={'minimumAreaMm2': round(0.95 * area, 1)},
        poseName='cavity up, flat bottom on the bed',
        poseOrigin=('Cavity up, flat mold bottom on the bed (as the V1.21 molds): the cavity is a height field seen from above, so '
                    'every surface faces up or is vertical and nothing needs support; floor and curved wall print as ironed tops.'),
        poseCheck=dict(printStl=src, bedContactMm2=round(area, 2), printSizeMm=size, note='print pose = source frame (identity), dropped to the bed'),
        changeReason=(f'New tool: {side} press mold for the inner tube sole (Shawn 2026-10-24: E6000 grabs too slowly and the cut tube '
                      'lifts on the rounded edge; clamp the glued tube in a printed mold, leave it to cure, trim after). Cavity = the '
                      f'foot bottom offset {c["T_mm"]} mm along the normal (tube 0.7 mm between ribs, 0.8 on a rib, measured by Shawn), '
                      f'one plane over the flat; it ends at the plane {c["top_plane_mm"]} mm, where the rim stays '
                      f'{c["seated"]["rim_normal_gap_mm"]["min"]} mm from the foot so the rubber is not pinched and the excess leaves over '
                      f'the top. Dry, the foot lands on the flat floor and a pencil on the mold top marks the {c["glue_edge_mm"]} mm glue '
                      f'line. Tabs {c["tab_clearance_mm"]} mm outside the foot, raised {side[0].upper()}; one heel post is keyed so only the {side} lid fits, one way round. press-mold-check.json.'),
        supersedes='nothing (new tool; the V1.21 hot-glue molds are a different tool)',
        incrementalEvidence=ref(SOLE / 'press-mold-check.json'),
        evidenceAlso=[ref(SOLE / 'press_mold.py'), ref(SOLE / 'hotglue_mold.py')],
    )


def lid_row(side, check):
    stl = SOLE / f'press-lid-{side}.stl'
    area, size, _ = printed(stl); src = ref(stl); c = check[side]['lid']
    return dict(
        key=f'press_lid_{side}', color='Black', quantity=1, decision='addition', replacesStockIds=[],
        path=src['path'], sha256=src['sha256'],
        sourceFrame=f'lid print frame: {c["print_pose"]} ({FOOT[side]} frame)',
        sourceToPrint=np.eye(4).tolist(), flatContact={'minimumAreaMm2': round(0.95 * area, 1)},
        poseName='top face on the bed',
        poseOrigin=('Lid top face on the bed, underside up: the underside is a height field seen from below, so printed this way '
                    'every surface faces up or is vertical and nothing needs support; the four M2 clearance holes are vertical.'),
        poseCheck=dict(printStl=src, bedContactMm2=round(area, 2), printSizeMm=size, note='STL written in its print pose (identity)'),
        changeReason=(f'New tool: screw-down lid of the {side} press mold (Shawn 2026-10-24: no weights or clamps at hand, screw a top half '
                      f'down). Underside = the top of the slip-fit foot lowered {c["squeeze_mm"]} mm where it is above {c["bear_above_mm"]} mm '
                      f'(bears on {c["bearing_area_mm2"]} mm2: the rim and the toe block, right over the curved edge). Four M2 x 10 TAP '
                      f'through {c["screw"]["lid_hole_d_mm"]} mm holes into the {c["screw"]["pilot_d_mm"]} mm post pilots; seated on the posts '
                      f'the foot sits {c["squeeze_mm"]} mm below the nominal seat, so the rubber is pressed. One heel hole is keyed to the {side} mold; {c["key"]["letter"]} engraved in the top. press-mold-check.json.'),
        supersedes='nothing (new tool)',
        incrementalEvidence=ref(SOLE / 'press-mold-check.json'),
        evidenceAlso=[ref(SOLE / 'press_mold.py')],
    )


def main():
    m = json.loads(V133.read_text())
    check = {r['side']: r for r in json.loads((SOLE / 'press-mold-check.json').read_text())}
    parts = [mold_row('left', check), mold_row('right', check), lid_row('left', check), lid_row('right', check)]
    sizes = {p['key']: printed(p['path']) for p in parts}
    grid = [['press_mold_left', 'press_mold_right'], ['press_lid_left', 'press_lid_right']]   # molds back row, lids front
    cw = max(sizes[k][1][0] for r in grid for k in r); rh = max(sizes[k][1][1] for r in grid for k in r)
    pl = []
    for i, row in enumerate(grid):
        for j, key in enumerate(row):
            _, size, lo = sizes[key]
            x0 = 128.0 - (2 * cw + GAP_MM) / 2 + j * (cw + GAP_MM) + (cw - size[0]) / 2
            y0 = 128.0 + GAP_MM / 2 + (rh - size[1]) / 2 - i * (rh + GAP_MM)
            assert 18.0 <= x0 and x0 + size[0] <= 238.0 and 18.0 <= y0 and y0 + size[1] <= 238.0, (key, x0, y0, size)
            pl.append(dict(key=key, copy=1, translation=[round(x0 - float(lo[0]), 4), round(y0 - float(lo[1]), 4), 0.0]))
    m.update(version='V1.34', parts=parts, placements={'Black': pl}, retiredParts=[],
             processOverrides={'Black_Bambu': dict(FAST), 'Black_Elegoo': dict(FAST)},
             processOverrideReason=('Tools, speed over finish (Shawn 2026-10-24): 0.28 mm layers, 3 walls (material round the M2 pilots), '
                                    '10 % infill, 3 top and bottom layers, no support (every surface faces up or is vertical; the 0.6 mm '
                                    'letter recess in the lid bed face is a short bridge).'),
             prototypeScope='V1.34: the left and right sole press molds with their screw-down lids (tools, four M2 x 10 each), one Black plate. V1.33 is printed.',
             knownFitBoundary=('Tools. Cavity 0.70 mm on the 0.7 mm tube plus glue film, so the rubber is pressed a little; printed '
                               'cavity size not measured. If the dry foot rocks or sits high, the print is off; the sole is not glued yet.'))
    m['deliveryContract'].update(colors=['Black'], fileCount=2, baseline='printed releases through V1.33',
                                 supersedes=[], status='INCREMENTAL_REPRINT')
    (REL / 'manifest-V1.34.json').write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(parts=[(p['key'], p['poseCheck']['bedContactMm2'], p['poseCheck']['printSizeMm']) for p in parts], placements=pl), indent=1))


if __name__ == '__main__':
    main()
