"""Merge the partial check outputs into checks.json (and add the coordinator conditions to features.json)."""
import json, datetime
import numpy as np
import pack_lib as P

OUT = P.OUT
J = lambda n: json.loads((OUT / n).read_text())
fit = J('check_fit.json'); asm = J('check_assembly.json'); prn = J('check_print.json'); build = J('build.json'); feats = J('features.json')
swl = J('sweep-v3-left.json'); swr = J('sweep-v3-right.json')
rss = {}
for side in ('left', 'right'):
    for line in (OUT / f'sweep_v3_{side}.log').read_text().splitlines():
        if 'maximum resident set size' in line:
            rss[side] = int(line.split()[0])
bm = P.load_stl(OUT / 'rear_pack-world.stl'); cm = P.load_stl(OUT / 'rear_pack_cover-world.stl')
V = bm.vertices
sil = {
    'maxAbsY_z_between_-40_and_30': round(float(np.abs(V[(V[:, 2] >= -40 - 1e-6) & (V[:, 2] <= 30)][:, 1]).max()), 3),
    'maxAbsY_z_below_-40': round(float(np.abs(V[V[:, 2] < -40 - 1e-6][:, 1]).max()), 3),
    'maxAbsY_z_above_32': round(float(np.abs(V[V[:, 2] > 32 + 1e-6][:, 1]).max()), 3),
    'maxAbsY_z_30_to_32': round(float(np.abs(V[(V[:, 2] > 30 + 1e-6) & (V[:, 2] <= 32 + 1e-6)][:, 1]).max()), 3),
    'topZ': round(float(V[:, 2].max()), 3), 'bottomZ': round(float(V[:, 2].min()), 3), 'minX': round(float(V[:, 0].min()), 3),
    'maxAbsY_x_behind_-21': round(float(np.abs(V[V[:, 0] < -21 - 1e-6][:, 1]).max()), 3),
    'coverMinX': round(float(cm.vertices[:, 0].min()), 3), 'coverMaxAbsY': round(float(np.abs(cm.vertices[:, 1]).max()), 3),
}
# the lower-front corner region: which features intersect it
B = P.mesh_to_m(bm)
corner_box = P.box((-30.0, -15.4, -44.0), (-19.0, 15.4, -35.0))
plain = P.union([P.box((-21.0, -15.3, -44.0), (-19.0, 15.3, -35.0)), P.box((-30.0, -15.3, -44.0), (-19.0, 15.3, -42.8)),
                 P.box((-30.0, 13.6, -44.0), (-19.0, 15.3, -35.0)), P.box((-30.0, -15.3, -44.0), (-19.0, -13.6, -35.0))])
plain = plain - P.box((-31.4, -7.3, -45.0), (-23.9, 6.7, -42.0))
extra = (B ^ corner_box) - plain
corner = dict(regionBox=[[-30, -15.3, -44], [-19, 15.3, -35]],
              materialInRegionMm3=round(float((B ^ corner_box).volume()), 2), plainShellMm3=round(float((plain ^ corner_box).volume()), 2),
              featureMaterialBeyondPlainShellMm3=round(float(extra.volume()), 2),
              featureMaterialBounds=np.round(P.from_m(extra).bounds, 2).tolist() if not extra.is_empty() else None,
              note='material beyond the plain shell in this region is the two lower OpenRB pads on the plate rear face (x -24.8..-21, z -42.25..-37.25) and nothing else; they sit inside the bay')

checks = {
 'meta': dict(generated=datetime.datetime.now().isoformat(timespec='seconds'), frame='mm, x forward, y left, z up (guide = MuJoCo trunk_base)',
              body=str(OUT / 'rear_pack-world.stl'), cover=str(OUT / 'rear_pack_cover-world.stl'),
              scripts=['build_rear_pack.py (geometry + features.json)', 'pack_lib.py', 'check_fit.py (checks 1-4)', 'pack_sweep2.py (check 5)',
                       'check_assembly.py (check 6)', 'check_print.py (check 7)', 'render_views.py / render_pack.py / raster.py (renders)', 'assemble_checks.py'],
              python='/tmp/microduck-cad-venv/bin/python (trimesh 5.1.1, manifold3d, shapely 2.2, mujoco 3.15)',
              boardsFixedLayoutL=dict(openrb=build['params']['openrb_holes_yz'], dfr=[list(P.DFR_BOX[0]), list(P.DFR_BOX[1])])),
 'check1_manifold': dict(result=fit['manifold'], reloadedStl=dict(bodyWatertight=bool(bm.is_watertight), coverWatertight=bool(cm.is_watertight),
                         bodyVolumeMm3=round(float(bm.volume), 2), coverVolumeMm3=round(float(cm.volume), 2)),
                         ok=all(fit['manifold'][k]['watertight'] and fit['manifold'][k]['bodies'] == 1 and fit['manifold'][k]['manifoldStatus'] == 'Error.NoError' for k in ('body', 'cover'))),
 'check2_interfaceFidelity': dict(screws=fit['interfaceFidelity'], tabNeighbourGaps=fit['tabNeighbourGaps'],
                                  upperGussetBoxes={k: v for k, v in prn.items() if k.startswith('upperGussetBox')},
                                  notes=['fidelity boxes sit in front of the new plate (x -19..-13.5); the box |y| 6.6..14.5 holds the lugs, holes and gussets: XOR 0 on all four',
                                         'the box |y| 4.5..14.5 also holds the retired small-regulator holder of the integrated power_support and the thin centre web (removed for the IMU board), hence the non-zero XOR on the upper screws',
                                         'seat faces and hole diameters identical to the current power_support; dia 2.5 shank and dia 4 head test cylinders give the same (tiny, polygonal) overlaps on both parts',
                                         'the pads of the lower lugs touch torso_base (gap 0) only through the plate front face at x -19, the same plane the base plate ends on; the lugs themselves keep the 0.257 mm of the current part'],
                                  ok=all(s['fidelityBox_y6.6_14.5']['xorVolMm3'] < 0.01 for s in fit['interfaceFidelity'])),
 'check3_boardsAndRooms': dict(result=fit['boardsAndRooms'],
                               allowedContacts={'openrb_model gap 0': 'PCB back face rests on the four pads (seat)', 'imu_model gap 0': 'board bottom edge rests on the shelf; slot-only clearance 0.185',
                                                'dfr_box gap 0': 'the planning box touches the lips, feet and cover lip that locate the board', 'room_usb gap 0': 'the bottom-wall opening equals the room footprint',
                                                'dfr_pad_room overlap': 'the two corner feet specified in the brief (|y| 10.3..13.6, z -7.3..-3) sit inside the pad-wire room; the three pads stay inside |y| <= 10',
                                                'openrb_body_box overlap': 'the box reaches x -22.4 (trimmed solder tails); the pads occupy x -24.8..-21 behind the real PCB back face at x -24.8; the model itself has zero overlap'},
                               ok=all(v['body']['overlapMm3'] < 1e-6 and v['cover']['overlapMm3'] < 1e-6 for k, v in fit['boardsAndRooms'].items()
                                        if k in ('openrb_model', 'imu_model', 'dfr_box', 'j_box', 'room_leg_plugs', 'room_neck_plug', 'room_terminal', 'room_usb', 'room_imu_plug_top', 'room_imu_socket_top'))),
 'check4_guideParts': dict(retired=P.RETIRED, under2mm=fit['guidePartsUnder2mm'], overlaps=fit['guidePartsOverlap'], all=fit['guideParts'],
                           notes=['motor10 / motor5 0.224 mm = the current power_support lugs (identical donor geometry)', 'torso_base 0 = plate front face on the base-plate edge plane x -19 (allowed by the brief)',
                                  'shells: body 0.55 / 0.70 mm at the head top edge (edge lowered 0.6 below the shell rear-top edge), cover 1.40 / 1.90 mm'],
                           ok=len(fit['guidePartsOverlap']) == 0),
 'check5_walkingSweep': dict(method='torso-fit/pack_sweep.py (leg_reach.py): all 304253 recorded phase-1 frames, 283500 adopted; 1 mm distance-field screening then exact manifold min_gap on flagged frames; hip yaw/roll bodies on the unique (yaw, roll) grid',
                             obstacle='rear_pack-world.stl + rear_pack_cover-world.stl + neck plug room box', targetMm=2.0,
                             left=dict(adopted=swl['adopted'], allFrames=swl['allFramesIncludingExcludedRuns'], flagged=swl['flagged'], elapsed_s=swl['elapsed_s'], rssBytes=rss.get('left')),
                             right=dict(adopted=swr['adopted'], allFrames=swr['allFramesIncludingExcludedRuns'], flagged=swr['flagged'], elapsed_s=swr['elapsed_s'], rssBytes=rss.get('right')),
                             fitStudyReference='4.50 / 5.32 mm (hull of Layout L)',
                             ok=min(swl['adopted']['pitchChain']['minGapMm'], swl['adopted']['hipBodies']['minGapMm'], swr['adopted']['pitchChain']['minGapMm'], swr['adopted']['hipBodies']['minGapMm']) >= 2.0),
 'check6_assembly': dict(result=asm,
                         notes=['pack: body alone, +x 30 mm, legs and shells off', 'cover: +x 15 mm with the boards in, shells off and on',
                                'OpenRB straight +x 20 mm fails by design: the channel feet, the lips and the corner posts sit in its shadow; the board goes in from above at x -3 (tails clear the pads) and then +x 3 mm onto the pads, which passes',
                                'DFR1202: 35 mm from above; IMU: 30 mm from above; J: +x 20 mm from the rear into its pocket (cover off)',
                                'screwdriver dia 6 x 60 along +x: lower OpenRB screws pass with 0.05 mm to the bottom wall; upper screws: the dia 6 shaft touches the OpenRB''s own components next to the holes (see shaftRadiusLimits), the pack itself leaves 0.06 / 0.64 mm; cover screws pass'],
                         ok=all(asm[k]['pass'] for k in ('pack_body_plus_x_30', 'cover_plus_x_15_shells_off', 'openrb_drop_in_z30_at_xminus3_then_plus_x_3', 'dfr_from_above_35', 'imu_from_above_30'))),
 'check7_printability': dict(result={k: v for k, v in prn.items() if k in ('body', 'cover')}, bedContactTargetMm2=300,
                             ok=prn['body']['bedContactAreaMm2'] >= 300 and prn['cover']['bedContactAreaMm2'] >= 300),
 'check8_features': dict(file=str(OUT / 'features.json'), bodyFeatures=len(feats['body']), coverFeatures=len(feats['cover']), ok=True),
 'coordinatorConditions': {
  '1_notUgly': dict(outerSilhouette=sil, requirement='|y| <= 21.3 below z 30 (plate), 15.3 behind the plate below z -40, cover flush',
                    coverFlush=dict(coverBodyGapMm=fit['manifold']['coverBodyGapMm'], coverBodyOverlapMm3=fit['manifold']['coverBodyOverlapMm3'],
                                    coverHalfWidth=18.6, postsHalfWidth=18.6, note='cover outline = post outline (18.6 above z -36.7, 45-degree corners to 15.3 at z -40, 15.3 below)'),
                    featuresWithPurpose=len(feats['body']) + len(feats['cover']), strayFeatures='none: every boss, rib, slot and opening is listed in features.json with its purpose',
                    ok=sil['maxAbsY_z_between_-40_and_30'] <= 21.3 + 1e-3 and sil['maxAbsY_z_below_-40'] <= 15.3 + 1e-3),
  '2_lowerFrontCornerChamferable': dict(region=corner, freeToChamfer=['plate front face x = -19 for |y| <= 15.3, z -44..-35 (plain, no feature)', 'bottom face z = -44 for x -30..-19, |y| <= 15.3 (plain; the USB opening starts at x -23.9 inside the wall)',
                                                                      'the front-bottom edge between them (x -19, z -44)'],
                                       parameter='build_rear_pack.py CHAMFER (cx, cz): plane through (x -19-cx, z -44) and (x -19, z -44+cz), full width',
                                       limits=['cx <= 4.9 keeps the cut in front of the USB opening (x -23.9)', 'cz * (1 - 2/cx) <= 1.2 for cx > 2 keeps the cut below the bay floor (z -42.8) behind the plate (x < -21); for cx <= 2 the cut stays in the plate slab and cz may reach 9',
                                               'the lower OpenRB pads (z >= -42.25 at x -24.8..-21) are then automatically clear'],
                                       reachResult='coordinator hip-pitch reach check: the bay corner is not a limiter (contacts at 24-26 deg occur where the original battery touched at 10 deg); no chamfer applied (cx = cz = 0)', ok=True),
  '3_easyToAssembleAndPlug': dict(portsFaceOpenBack='OpenRB components (all four DXL ports, terminal) face -x = the open back of the bay; DFR1202 components and pads face -x = the cover side; cover off gives straight access',
                                  neckPortFingerRoom=dict(windowXmm=6.7, windowZmm=12.5, requiredMm=6.6, nothingOutsideWall=True),
                                  boardsEnterFromRearOrAbove={'OpenRB': 'from above at x -3 then +x 3 onto the pads (cover off): pass', 'DFR1202': 'from above: pass', 'IMU': 'from above: pass', 'cover': '+x: pass'},
                                  screwHeadsFromBehind={'cover screws': 'four heads on the flat back face, straight dia 6 driver passes', 'OpenRB screws': 'heads on the component side, straight lane from the back with the DFR out; dia 6 passes the pack, the board''s own components limit the shaft near the upper holes (see check6)'},
                                  noScrewHiddenBehindCable='cover screws sit at |y| 16.1 outside the wiring volume (|y| <= 13.6); the OpenRB lanes (|y| 7..13.5) run beside the central cable paths (terminal |y| <= 4.8, centre ports |y| <= 4.3, tether |y| <= 3) and the OpenRB is screwed before any cable is plugged',
                                  onlyClampIsFourHipYawScrews=True, noFuses=True,
                                  belowShellsVsBatteryDepth=dict(packBottomZ=-44.0, originalBatteryFloorZ=-39.38, deeperByMm=4.62, coverBackX=-47.0, originalBatteryBackX=-46.83,
                                                                 ok=False, note='the brief fixes the OpenRB at z -42 with a 2 mm wall below it, so the pack bottom cannot stay within the original 39 mm battery depth without moving the boards; recorded as a deviation'),
                                  ok=True),
 },
 'junctionJRemoved': dict(reason='2026-10-12 decision: servo power goes through the OpenRB-150 DXL ports as on the original MicroDuck (and on Microban, whose HAT carries the whole servo chain on two ports); the 3 A port rating is to be checked by summing XL330 Present Current while walking, not pre-empted with a bypass',
                          choice='J pocket (floor, divider, front stop) removed; the +y wall window is back to z -29..-16.5 (neck plug room only); the 5 V leads to the OpenRB terminal and the Pi leave the DFR1202 5V/GND pads directly',
                          sweepNote='the walking sweep ran on the geometry with the J pocket and the z -29 window; removing the pocket only takes material away, so the sweep clearances still bound this body'),
 'deviationsFromBrief': [
  'OpenRB pads are 3.8 mm tall (x -24.8..-21) with M2x6 screws, not 1.4 mm / M2x4: the model PCB back face is at x -24.8 (the brief''s -22.4 is the trimmed solder-tail plane)',
  'OpenRB hole centres at z -39.75 / 21.75 (model), 0.45 below the brief''s -39.3 / 22.2; y -10.54 / 9.96',
  'cover posts: the brief''s dia 5 posts at y +-13.8 would sit inside the DFR1202 corners; the posts are corner blocks |y| 13.6..18.6 with pilots at (+-16.1, 26.0) and (+-16.1, -36.5), the cover is 37.2 wide above z -36.7',
  'side walls are 1.7 thick with the inner face at |y| 13.6 (not 13..15) and the bottom wall 1.2 thick (z -44..-42.8): both leave the dia 6 screwdriver lane to the lower OpenRB screws',
  'DFR lips span |y| 11.9..13.6 and z -3.5..18 only: outside the OpenRB drop-in shadow and the upper driver lane; feet stop at x -38.5 for the same reason',
  'the original upper-tab thin web (|y| < 6.6) is removed so the IMU board can stand through it; lugs, holes, seats and gussets are the original ones',
  'head top edge lowered 0.6 mm under the shell rear-top edge (38.8 at the notch instead of 39.4); notch 12 x 6.1',
  'no junction J: the servos take power through the OpenRB ports (see junctionJRemoved)',
  'pack bottom z -44 is 4.62 mm below the original battery floor (z -39.38); cover back x -47 is 0.17 behind the battery back',
  'IMU four-pin pattern not used: the pins would run along y through the slot; the board is held by the edge slot, the shelf and one zip tie',
 ],
 'notVerified': [
  'DFR1202 product page could not be fetched (wrong product id / bot check); the pad side (three pads on one 26 mm edge, VIN-GND-5V) comes from the guide step text',
  'OpenRB screw heads on the component side: checked only against the guide board model (dia 4 x 2 head cylinders, zero overlap)',
  'print tolerances (slot and channel clearances 0.19-0.6 mm) are nominal CAD values',
  'cable routing inside the bay was not modelled; the sweeps use the brief''s plug rooms only',
 ],
}
def _ren(o):
    if isinstance(o, dict):
        return {('pass' if k == 'ok' else k): _ren(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_ren(v) for v in o]
    return o
checks = _ren(checks)
P.jdump(checks, OUT / 'checks.json')
feats['coordinatorConditions'] = {k: {kk: vv for kk, vv in v.items() if kk in ('requirement', 'pass', 'freeToChamfer', 'portsFaceOpenBack', 'noScrewHiddenBehindCable', 'strayFeatures')} for k, v in checks['coordinatorConditions'].items()}
feats['junctionJ'] = checks['junctionJRemoved']['choice']
P.jdump(feats, OUT / 'features.json')
print(json.dumps({k: v.get('pass') for k, v in checks.items() if isinstance(v, dict) and 'pass' in v}, indent=1))
print(json.dumps({k: v.get('pass') for k, v in checks['coordinatorConditions'].items()}, indent=1))
print('silhouette', sil); print('corner', corner)
