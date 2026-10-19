"""Write the V1.21 incremental release manifest (13-RELEASE-PIPELINE schema 1, pipeline v2).

V1.21 is one Orange plate with the two hot-glue sole molds (tools, not robot parts). V1.20 is printed (Shawn
2026-10-19), so nothing earlier travels in this package. The molds come from
build-pack-20260913/procurement/feet-sole-20261018/hotglue_mold.py, which writes them in the foot STL frame with the
cavity up and the flat bottom at z = -4: the print pose is that frame (sourceToPrint identity; the pipeline drops it
to the bed). They are not robot geometry, so the assembly-guide print gate has nothing to check for them.

The plate is one row centred on the bed (128, 128), 12 mm gap. Profiles, baseline stock and the deferred V2.0 head
parts come from the released manifest-V1.20.json (pinned by sha256). Process overrides on both machines: 0.12 mm
layers with top ironing and the seam at the back for a smooth cavity, 6 top layers, 40 % infill.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.21.json]
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
V120_PATH = PRINT / 'release-V1.20/manifest-V1.20.json'
V120_SHA = 'b912b3c7eea53f81b96ccf861f4f04cee46eeffe8bf42259f75b0a839b8ce171'
SOLE = PRINT.parents[1] / 'build-pack-20260913/procurement/feet-sole-20261018'
ORANGE = ['hotglue_mold_left', 'hotglue_mold_right']
GAP_MM = 12.0
IDENTITY = np.eye(4).tolist()
MOLD_OVERRIDES = {'layer_height': '0.12', 'ironing_type': 'top', 'seam_position': 'back',
                  'top_shell_layers': '6', 'sparse_infill_density': '40%'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    p = Path(p); assert p.is_file(), p
    return {'path': str(p.resolve()), 'sha256': sha(p)}


def printed(path):
    m = trimesh.load(path, force='mesh', process=False)
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    area = float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01].sum())
    return area, (m.bounds[1] - m.bounds[0]).round(2).tolist(), m.bounds[0]


def mold_row(side, foot_stl):
    stl = SOLE / f'hotglue-mold-{side}.stl'
    area, size, _ = printed(stl)
    src = ref(stl)
    return dict(
        key=f'hotglue_mold_{side}', color='Orange', quantity=1, decision='addition', replacesStockIds=[],
        path=src['path'], sha256=src['sha256'],
        sourceFrame=f'{foot_stl} frame (mm; foot flat bottom at z = 0, foot above); mold cavity up, mold bottom at z = -4',
        sourceToPrint=IDENTITY, flatContact={'minimumAreaMm2': 3600},
        poseOrigin=('Cavity up, flat mold bottom on the bed: the cavity is a height field seen from above, so every surface '
                    'faces up or is vertical and nothing needs support; the cavity floor and the curved wall print as '
                    'ironed top surfaces.'),
        poseCheck=dict(printStl=src, bedContactMm2=round(area, 2), printSizeMm=size,
                       note='V1.21: print pose = source frame (identity), dropped to the bed'),
        changeReason=(f'V1.21: new tool, the {side} foot hot-glue sole mold. Cavity = the {foot_stl} bottom offset 1.0 mm '
                      'along the normal up to 3.0 mm above the flat, sealed by the 3.0 mm top plane, three conical depth '
                      'pins, eight vents to a moat, four locating tabs 0.4 mm outside the foot outline, a raised ' + side[0].upper() + ' (0.6 mm, 6.5 mm tall) on the heel strip, its top towards the toe. Seated foot: no '
                      'overlap, coat 1.00 mm (hotglue-mold-check.json). Process: feet-sole-20261018/README.md.'),
        supersedes='nothing (new tool)',
        incrementalEvidence=ref(SOLE / 'hotglue-mold-check.json'),
        evidenceAlso=[ref(SOLE / 'hotglue_mold.py'), ref(SOLE / 'README.md')],
    )


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.21.json'); a = ap.parse_args()
    assert sha(V120_PATH) == V120_SHA, 'manifest-V1.20.json changed since V1.21 was set up'
    m = json.loads(V120_PATH.read_text())
    parts = [mold_row('left', 'community-44.stl'), mold_row('right', 'community-46.stl')]
    by = {p['key']: p for p in parts}
    sizes = {k: printed(by[k]['path']) for k in ORANGE}
    width = sum(sizes[k][1][0] for k in ORANGE) + GAP_MM * (len(ORANGE) - 1)
    x0 = 128.0 - width / 2; pl = []
    for key in ORANGE:
        _, size, lo = sizes[key]; y0 = 128.0 - size[1] / 2
        assert 18.0 <= x0 and x0 + size[0] <= 238.0 and 28.0 <= y0 and y0 + size[1] <= 238.0, (key, x0, y0, size)
        pl.append(dict(key=key, copy=1, translation=[round(x0 - float(lo[0]), 4), round(y0 - float(lo[1]), 4), 0.0]))
        x0 += size[0] + GAP_MM
    m['parts'] = parts
    m['placements'] = {'Orange': pl}
    m['processOverrides'] = {'Orange_Bambu': dict(MOLD_OVERRIDES), 'Orange_Elegoo': dict(MOLD_OVERRIDES)}
    m['processOverrideReason'] = ('Hot-glue molds: the cavity face becomes the sole face, so 0.12 mm layers, ironed top surfaces '
                                  'and the seam at the back keep it smooth; 6 top layers and 40 % infill keep the floor stiff '
                                  'under a pressed foot. Any PLA spool works; the plate is named Orange only because the '
                                  'pipeline groups plates by spool colour.')
    m['retiredParts'] = []
    m['version'] = 'V1.21'
    m['prototypeScope'] = ('V1.21 delta package on one Orange plate: the left and right hot-glue sole molds (tools). V1.20 is printed '
                           '(Shawn 2026-10-19).')
    m['knownFitBoundary'] = ('Molds are tools: wipe a thin release film into the cavity, fill about 2.5 cm3 of hot glue, press the '
                             'sanded, clean foot between the tabs onto the three pins, cool fully, lift straight up '
                             '(build-pack-20260913/procurement/feet-sole-20261018/README.md). Not cast or tested yet.')
    dc = m['deliveryContract']
    dc.update(colors=['Orange'], fileCount=2,
              baseline='printed V1.8 set, the V1.9 Orange plate, V1.17, V1.18 and V1.20 (V1.20 printed by 2026-10-19); V1.19 never printed',
              supersedes=['nothing: two new tools'], status='INCREMENTAL_REPRINT')
    a.out.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(out=str(a.out), orange=[(p['key'], p['poseCheck']['bedContactMm2'], p['poseCheck']['printSizeMm']) for p in parts],
                          placements=pl), indent=1))


if __name__ == '__main__':
    main()
