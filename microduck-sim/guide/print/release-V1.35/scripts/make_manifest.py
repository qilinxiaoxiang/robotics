"""Write the V1.35 incremental release manifest: the A7Z saddle V3 of D-028 (print/a7z-saddle/build_saddle.py), body and lid,
one Orange plate (interim colour: white PLA is out at RoboClub, CURRENT-STATE.json print_filament_stock; scheme C white when
restocked). Replaces the printed V1.29 saddle body and lid (V1.33 White plate), which are superseded by D-028. V3: the saddle
floor itself carries the board on four bosses (board + 6530B screwed to it from below), the unit is taped to the shell roofs
with 3M 0.5 mm foam tape, and the lid is a cover that touches nothing; the V2 tray of the afternoon release was never printed
and is gone.

Poses (guide/print/orientation-study/PRINT-ORIENTATION-PRACTICE.md):
- saddle_body upright, open side up, the domed floor (it follows the shell roof) on the bed, as V1.29: one rear corner
  touches the bed, the whole floor underside stands on tree support; the walls, the four floor bosses, the rear port window,
  the +y bulge channel, the exhaust slots and the two side lid-screw holes print vertical and clean; the four head pockets
  open downward into the support. no_brim on the part (its own contact is inside the support footprint; Bambu trims the brim
  there, V1.29 brim review).
- saddle_lid upside down, plate top on the bed: the lip and the two screw bosses stand up from the plate; the grille is
  through the plate.

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
                                     '(shells pattern of PRINT-ORIENTATION-PRACTICE.md, as the printed V1.29 body). Walls, the four floor bosses, rear '
                                     'port window, +y bulge channel, exhaust slots and side lid-screw holes print vertical; the four head pockets in '
                                     'the floor underside open into the support.'),
                             minimum=2.0, brim_support=None,
                             objectSettings={'brim_type': 'no_brim'},
                             objectSettingsReason=('the part stands on tree support over its whole domed underside; its own first-layer contact is a '
                                                   'small rear corner inside the support footprint, and Bambu trims a part brim wherever support '
                                                   'stands within gap + width (V1.29 brim review: planned brim missing); the slicers brim the support themselves')),
         'saddle_lid': dict(T=np.diag([1.0, -1.0, -1.0, 1.0]), name='upside down, plate on the bed',
                            origin=('a7z-saddle/build_saddle.py world frame turned 180 deg about x: the lid plate top on the bed; the lip and the two '
                                    'lid-screw bosses stand up from the plate; the grille is through the plate. A cover only: no bars, no pads.'),
                            minimum=1000.0, brim_support=None)}


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
               changeReason=('D-028 (2026-10-25): saddle V3, board turned 180 deg (USB-C and HDMI through one rear-wall window, header at the front '
                             'in an open strip, front wall top lowered for the head wires), Radxa 6530B heatsink on the board, board + heatsink '
                             'screwed from below to four bosses of the saddle floor (one unit), the unit taped to the shell roofs with 3M 0.5 mm '
                             'foam tape (no screw), lid a cover over the heatsink end that touches nothing, antenna on the front wall, +y bulge for '
                             'the IPEX pigtail. The V1.29 body and lid (V1.33 White plate) '
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
         prototypeScope=('V1.35 delta package: one Orange plate with the two parts of the A7Z saddle V3, body and lid (D-028). The V1.29 saddle body '
                         'and lid of the V1.33 White plate are superseded; orange is the interim colour until white PLA is restocked.'),
         knownFitBoundary=('Board + Radxa 6530B screwed from below with four M2 x 6 through the saddle floor bosses (head pockets dia 4.2 from below '
                           'to z 46.5) and the board holes into the heatsink\'s threaded bosses, making saddle, board and heatsink one unit; the two '
                           'roof screws S-shell_pack-01/02 are driven into the pack bar before the unit is taped on (floor underside passes about '
                           '0.1 mm over their heads, ray cast 2026-10-25); the unit is held by 3M 0.5 mm foam tape under the floor edges, no screw; '
                           'the lid is a cover held by two M2 x 6 side screws at z 64.2 whose bosses end 1.0 mm above the heatsink. 6530B base '
                           'height (3.1) and fin-block start (d 6.4) are photo estimates, measured on the part before fitting. Printed sizes not '
                           'measured.'))
m.pop('deferred', None)
m['deliveryContract'].update(colors=['Orange'], filesPerColor=2, fileCount=2, baseline='printed releases through V1.34', status='INCREMENTAL_REPLACEMENT',
                             supersedes=['saddle_body and saddle_lid of V1.29 (printed on the V1.33 White plate)'])
(REL / 'manifest-V1.35.json').write_text(json.dumps(m, indent=1, ensure_ascii=False)); print('ok', [p['key'] for p in parts], pl)
