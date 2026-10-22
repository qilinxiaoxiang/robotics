"""Write the V1.29 incremental release manifest: the A7Z roof saddle of D-022 (print/a7z-saddle/build_saddle.py), body and
lid, white (scheme C: white shells, thighs and head cap), on one plate. Additions: nothing in the 89-stock is replaced.

Poses (guide/print/orientation-study/PRINT-ORIENTATION-PRACTICE.md):
- saddle_body upright, open side up, the domed floor (it follows the shell roof) on the bed: the shells pattern ("put the
  open side up, or the dome on the bed; accept support under the dome when that keeps every post and pilot end clean").
  Only one rear corner touches the bed (2.3 mm2, tip angle -55 deg), the whole floor underside stands on the White
  profiles' tree support; it is the hidden face that mates the shell roof. The board posts, their pilots, the two roof
  screw seats and holes, the lid screw bosses and the side slots all print vertical and clean (R2, R3, R6). On a flank
  (real flat base, R1) the opposite flank would be a 40 x 36 mm ceiling on 65 mm of tree support inside the open box,
  every pilot horizontal; open side down would trap support under the floor. Flat-contact minimum 2 mm2; the R1 default
  brim would go round that corner, but Bambu trims a part brim where support stands within gap + width (first V1.29
  slice: planned brim missing), so the row sets no_brim and the slicers brim the support themselves.
- saddle_lid upside down, plate top on the bed (2380 mm2), 10.2 mm tall: the lip ring, fan-pocket bars, rear stop and
  the two lid screw bosses stand up from the plate; the 0.6 mm snap lips are the only overhangs.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent; SIM = PRINT.parent.parent
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import wall_check  # noqa: E402
V128 = PRINT / 'release-V1.28/manifest-V1.28.json'; V117 = PRINT / 'release-V1.17/manifest-V1.17.json'
SAD = PRINT / 'a7z-saddle'; BUILD = SAD / 'build'; WORLD = PRINT / 'world'
WALL_REASON = ('wall-foot wedges where the 1.6 mm walls run down past the shell roof edge to meet the shell flank: the wall '
               'thins to a wedge over its last millimetres above the shell (a7z-saddle/build/wall_check.out; build_saddle.py '
               'thinWallAllowances); the wedge sits on the shell and carries no load')
POSES = {'saddle_body': dict(T=np.eye(4), name='upright, dome down',
                             origin=('a7z-saddle/build_saddle.py world frame as printed: open side up, the domed floor underside (it follows the '
                                     'shell roof, 1.6 mm normal offset) on the bed. One rear corner touches (2.3 mm2, tip angle -55 deg); the whole '
                                     'underside stands on tree support (shells pattern of PRINT-ORIENTATION-PRACTICE.md: dome on the bed, support '
                                     'under the dome keeps every post and pilot end clean). Board posts and pilots, roof-screw seats and holes, '
                                     'lid-screw bosses and side slots print vertical. Flank-down rejected: the far flank becomes a 40 x 36 mm '
                                     'ceiling on 65 mm of tree support inside the box with every pilot horizontal; open side down rejected: '
                                     'support trapped under the floor.'),
                             minimum=2.0, brim_support=None,
                             objectSettings={'brim_type': 'no_brim'},
                             objectSettingsReason=('the part stands on tree support over its whole domed underside; its own first-layer contact is a '
                                                   '2.3 mm2 rear corner inside the support footprint, and Bambu trims a part brim wherever support '
                                                   'stands within gap + width, so the R1 outer brim (tip angle -55 deg) came out empty on the first '
                                                   'V1.29 slice (brim review: planned brim missing); the slicers brim the support themselves')),
         'saddle_lid': dict(T=np.diag([1.0, -1.0, -1.0, 1.0]), name='upside down, plate on the bed',
                            origin=('a7z-saddle/build_saddle.py world frame turned 180 deg about x: the lid plate top on the bed (2380 mm2), '
                                    '10.2 mm tall; lip ring, fan-pocket bars, rear stop and the two lid-screw bosses stand up from the plate; '
                                    'the 0.6 mm snap lips under the front corners are the only overhangs.'),
                            minimum=2000.0, brim_support=None)}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


m = json.loads(V128.read_text()); white = json.loads(V117.read_text())['processOverrides']
build = json.loads((BUILD / 'build.json').read_text())
parts = []; pl = []
for i, (key, pose) in enumerate(POSES.items()):
    stl = WORLD / f'{key}.stl'
    k = trimesh.load(stl, force='mesh', process=False); k.apply_transform(pose['T']); k.apply_translation([0, 0, -k.bounds[0, 2]])
    pstl = BUILD / f'{key}-print.stl'; k.export(pstl)
    area = float(k.area_faces[np.max(np.abs(k.triangles[:, :, 2]), axis=1) <= .01].sum()); size = (k.bounds[1] - k.bounds[0]).round(2).tolist()
    assert area >= pose['minimum'], (key, area)
    regs = [g for g in wall_check.check(k.copy(), (), key)['regions'] if g['status'] == 'FAIL']
    allow = [dict(bbox=[[c - .05 for c in g['bbox'][0]], [c + .05 for c in g['bbox'][1]]], minMm=round(max(g['minMm'] - .005, 0.01), 3), reason=WALL_REASON) for g in regs]
    row = dict(key=key, color='White', quantity=1, decision='addition', replacesStockIds=[],
               path=str(stl), sha256=sha(stl), sourceFrame='robot frame (mm, x forward, y left, z up; guide world at HOME)', sourceToPrint=pose['T'].tolist(),
               flatContact={'minimumAreaMm2': pose['minimum']}, poseName=pose['name'], poseOrigin=pose['origin'],
               poseCheck=dict(printStl=ref(pstl), bedContactMm2=round(area, 2), printSizeMm=size, note='world STL in the row pose, dropped to the bed'),
               changeReason=('D-022 (2026-10-22): the A7Z leaves the head after the closed-head soak (D-021) and rides in a roof saddle on the '
                             'shell dome behind the neck, fan on the lid, Dupont leads straight into the header, antenna strip on the rear wall. '
                             f'{key}: {build["parts"][key]["volume_mm3"] / 1000:.1f} cm3, bounds {build["parts"][key]["bounds"]} (a7z-saddle/build/build.json).'),
               incrementalEvidence=ref(BUILD / 'build.json'),
               evidenceAlso=[ref(SAD / 'guide-world.json'), ref(BUILD / 'wall_check.out'), ref(SAD / 'head_sweep_final.out'), ref(SAD / 'balance/run.log')],
               thinWallAllowances=allow)
    if pose['brim_support']:
        row['brimAlongSupportReason'] = pose['brim_support']
    if pose.get('objectSettings'):
        row['objectSettings'] = pose['objectSettings']; row['objectSettingsReason'] = pose['objectSettingsReason']
    parts.append(row)
    pl.append(dict(key=key, copy=1, translation=[round(128.0 - 26.0 + 52.0 * i - (k.bounds[0, 0] + k.bounds[1, 0]) / 2, 4), round(128.0 - (k.bounds[0, 1] + k.bounds[1, 1]) / 2, 4), 0.0]))
    print(key, 'contact', round(area, 1), 'size', size, 'wall FAIL regions', [(g['areaMm2'], g['minMm']) for g in regs])
m.update(parts=parts, placements={'White': pl}, processOverrides={k: v for k, v in white.items() if k.startswith('White_')}, retiredParts=[], version='V1.29',
         processOverrideReason=('V1.17 White overrides kept: 3 support interface layers at 0.15 spacing, 0.2 top z, interface 40 mm/s, bridge 30 mm/s, '
                                'support ironing, 0.2 first layer; the saddle body stands on tree support over its whole underside.'),
         prototypeScope=('V1.29 delta package: one White plate with the A7Z roof saddle body and lid (D-022). Nothing in the printed set is replaced; '
                         'the V1.17 A7Z head clip (clip_cap) is no longer used (the head keeps its cap; the camera face is reprinted later for the USB camera).'),
         knownFitBoundary=('Board posts take M2 x 4 self-tapping into 1.6 mm pilots (dia 2.2 board holes +0.3); the floor underside is a 1.6 mm '
                           'normal offset of the ray-cast shell roof with 0.3 mm clearance, printed on support (rough side down); the roof screws '
                           'S-shell_pack-01/02 become M2 x 10 through the saddle floor into the pack shoulder bar (pilot drilled 0.3 mm deeper). '
                           'Fan 30 x 30 x 8 held by the lid pocket bars; USB camera plug notch 12 x 10 mm at the front wall. Printed sizes not measured.'))
m.pop('deferred', None)
m['deliveryContract'].update(colors=['White'], filesPerColor=2, fileCount=2, baseline='printed releases through V1.28', status='INCREMENTAL_ADDITION',
                             supersedes=['the V1.17 A7Z head clip (clip_cap), no longer fitted'])
(REL / 'manifest-V1.29.json').write_text(json.dumps(m, indent=1, ensure_ascii=False)); print('ok', [p['key'] for p in parts], pl)
