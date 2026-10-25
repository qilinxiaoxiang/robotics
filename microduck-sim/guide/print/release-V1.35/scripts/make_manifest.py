"""Write the V1.35 incremental release manifest: the A7Z saddle V2 of D-028 (print/a7z-saddle/build_saddle.py), body, lid and
tray, one Orange plate (interim colour: white PETG is out at RoboClub, CURRENT-STATE.json print_filament_stock; scheme C
white when restocked). Replaces the printed V1.29 saddle body and lid (V1.33 White plate), which are superseded by D-028.

Poses (guide/print/orientation-study/PRINT-ORIENTATION-PRACTICE.md):
- saddle_body upright, open side up, the domed floor (it follows the shell roof) on the bed, as V1.29: one rear corner
  touches the bed, the whole floor underside stands on tree support; the walls, the rear port window, the +y bulge channel,
  the exhaust slots, the roof-screw seats and the two side lid-screw holes print vertical and clean. no_brim on the part
  (its own contact is inside the support footprint; Bambu trims the brim there, V1.29 brim review).
- saddle_lid upside down, plate top on the bed: the lip, the two pressing bars, the corner pad and the two screw bosses
  stand up from the plate; the grille is through the plate.
- saddle_tray flat as built, plate underside on the bed: the four bosses stand up; the counterbores are 1.0 mm recesses in
  the bed face, the boss holes and the part cut-outs are vertical.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent; SIM = PRINT.parent.parent
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import wall_check  # noqa: E402
BASE = PRINT / 'release-V1.34/manifest-V1.34.json'; V117 = PRINT / 'release-V1.17/manifest-V1.17.json'
SAD = PRINT / 'a7z-saddle'; BUILD = SAD / 'build'; WORLD = PRINT / 'world'
WALL_REASON = ('wall-foot wedges where the 1.6 mm walls run down past the shell roof edge to meet the shell flank: the wall '
               'thins to a wedge over its last millimetres above the shell (build_saddle.py thinWallAllowances); the wedge sits '
               'on the shell and carries no load')
POSES = {'saddle_body': dict(T=np.eye(4), name='upright, dome down',
                             origin=('a7z-saddle/build_saddle.py world frame as printed: open side up, the domed floor underside (it follows the '
                                     'shell roof, 1.6 mm normal offset) on the bed; one rear corner touches, the whole underside stands on tree support '
                                     '(shells pattern of PRINT-ORIENTATION-PRACTICE.md, as the printed V1.29 body). Walls, rear port window, +y '
                                     'bulge channel, exhaust slots, roof-screw seats and side lid-screw holes print vertical.'),
                             minimum=2.0, brim_support=None,
                             objectSettings={'brim_type': 'no_brim'},
                             objectSettingsReason=('the part stands on tree support over its whole domed underside; its own first-layer contact is a '
                                                   'small rear corner inside the support footprint, and Bambu trims a part brim wherever support '
                                                   'stands within gap + width (V1.29 brim review: planned brim missing); the slicers brim the support themselves')),
         'saddle_lid': dict(T=np.diag([1.0, -1.0, -1.0, 1.0]), name='upside down, plate on the bed',
                            origin=('a7z-saddle/build_saddle.py world frame turned 180 deg about x: the lid plate top on the bed; the lip, the two '
                                    'pressing bars, the corner pad and the two lid-screw bosses stand up from the plate; the grille is through the plate.'),
                            minimum=1000.0, brim_support=None),
         'saddle_tray': dict(T=np.eye(4), name='flat, bosses up',
                             origin=('a7z-saddle/build_saddle.py world frame as built, dropped to the bed: the 1.4 mm plate underside on the bed with '
                                     'its four 1.0 mm counterbores as recesses in the bed face; the four bosses stand up, the boss holes and the '
                                     'cut-outs under the microSD, CSI, PCIe and button are vertical.'),
                             minimum=600.0, brim_support=None)}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


m = json.loads(BASE.read_text()); white = json.loads(V117.read_text())['processOverrides']
build = json.loads((BUILD / 'build.json').read_text())
GAP = 10.0
posed = {}
for key, pose in POSES.items():
    k = trimesh.load(WORLD / f'{key}.stl', force='mesh', process=False); k.apply_transform(pose['T']); k.apply_translation([0, 0, -k.bounds[0, 2]]); posed[key] = k
widths = [posed[k].bounds[1, 0] - posed[k].bounds[0, 0] for k in POSES]
parts = []; pl = []; x = 128.0 - (sum(widths) + GAP * (len(widths) - 1)) / 2      # footprint centred on the bed (pipeline tolerance 1 mm)
for key, pose in POSES.items():
    stl = WORLD / f'{key}.stl'; k = posed[key]
    pstl = BUILD / f'{key}-print.stl'; k.export(pstl)
    area = float(k.area_faces[np.max(np.abs(k.triangles[:, :, 2]), axis=1) <= .01].sum()); size = (k.bounds[1] - k.bounds[0]).round(2).tolist()
    assert area >= pose['minimum'], (key, area)
    regs = [g for g in wall_check.check(k.copy(), (), key)['regions'] if g['status'] == 'FAIL']
    allow = [dict(bbox=[[c - .05 for c in g['bbox'][0]], [c + .05 for c in g['bbox'][1]]], minMm=round(max(g['minMm'] - .005, 0.01), 3), reason=WALL_REASON) for g in regs]
    assert key == 'saddle_body' or not regs, (key, regs)
    row = dict(key=key, color='Orange', quantity=1, decision='addition', replacesStockIds=[],
               path=str(stl), sha256=sha(stl), sourceFrame='robot frame (mm, x forward, y left, z up; guide world at HOME)', sourceToPrint=pose['T'].tolist(),
               flatContact={'minimumAreaMm2': pose['minimum']}, poseName=pose['name'], poseOrigin=pose['origin'],
               poseCheck=dict(printStl=ref(pstl), bedContactMm2=round(area, 2), printSizeMm=size, note='world STL in the row pose, dropped to the bed'),
               changeReason=('D-028 (2026-10-25): saddle V2, board turned 180 deg (USB-C and HDMI through one rear-wall window, header at the front '
                             'in an open strip), Radxa 6530B heatsink on the board, board + heatsink screwed from below to a tray, lid over the '
                             'heatsink only, antenna on the front wall, +y bulge for the IPEX pigtail. The V1.29 body and lid (V1.33 White plate) '
                             'are superseded: their board faced the neck and modelled a copper block and fan that were never bought. Orange is the '
                             f'interim colour (white out). {key}: {build["parts"][key]["volume_mm3"] / 1000:.1f} cm3, bounds '
                             f'{build["parts"][key]["bounds"]} (a7z-saddle/build/build.json).'),
               incrementalEvidence=ref(BUILD / 'build.json'),
               evidenceAlso=[ref(SAD / 'guide-world.json'), ref(SAD / 'DESIGN-CONTRACT.json')],
               thinWallAllowances=allow)
    if pose.get('objectSettings'):
        row['objectSettings'] = pose['objectSettings']; row['objectSettingsReason'] = pose['objectSettingsReason']
    parts.append(row)
    w = k.bounds[1, 0] - k.bounds[0, 0]
    pl.append(dict(key=key, copy=1, translation=[round(x + w / 2 - (k.bounds[0, 0] + k.bounds[1, 0]) / 2, 4), round(128.0 - (k.bounds[0, 1] + k.bounds[1, 1]) / 2, 4), 0.0]))
    x += w + GAP
    print(key, 'contact', round(area, 1), 'size', size, 'wall FAIL regions', [(g['areaMm2'], g['minMm']) for g in regs])
orange = {k.replace('White_', 'Orange_'): v for k, v in white.items() if k.startswith('White_')}
m.update(parts=parts, placements={'Orange': pl}, processOverrides=orange, version='V1.35',
         retiredParts=[{'part': 'saddle_body (V1.29 layout)', 'printed': 'V1.33 (White)', 'reason': 'D-028: board faced the neck, copper block + fan never bought; superseded by the V2 body'},
                       {'part': 'saddle_lid (V1.29 layout)', 'printed': 'V1.33 (White)', 'reason': 'D-028: fan pocket for a fan that was never bought; superseded by the V2 lid over the 6530B'}],
         processOverrideReason=('The V1.17 White support-interface overrides (3 interface layers at 0.15 spacing, 0.2 top z, interface 40 mm/s, bridge '
                                '30 mm/s, support ironing, 0.2 first layer) applied to the Orange plate: the saddle body stands on tree support over its '
                                'whole underside, as the printed V1.29 body did on White.'),
         prototypeScope=('V1.35 delta package: one Orange plate with the A7Z saddle V2 body, lid and tray (D-028). The V1.29 saddle body and lid of '
                         'the V1.33 White plate are superseded; orange is the interim colour until white PETG is restocked.'),
         knownFitBoundary=('Board + Radxa 6530B screwed from below with four M2 x 6 through the tray bosses and the board holes into the heatsink\'s '
                           'threaded bosses; the tray drops in after the two roof screws S-shell_pack-01/02 (M2 x 10, heads 0.65 mm under the tray); '
                           'lid clamps the heatsink with two M2 x 6 side screws. 6530B base height (3.1) and fin-block start (d 6.4) are photo '
                           'estimates, measured on the part before fitting. Printed sizes not measured.'))
m.pop('deferred', None)
m['deliveryContract'].update(colors=['Orange'], filesPerColor=2, fileCount=2, baseline='printed releases through V1.34', status='INCREMENTAL_REPLACEMENT',
                             supersedes=['saddle_body and saddle_lid of V1.29 (printed on the V1.33 White plate)'])
(REL / 'manifest-V1.35.json').write_text(json.dumps(m, indent=1, ensure_ascii=False)); print('ok', [p['key'] for p in parts], pl)
