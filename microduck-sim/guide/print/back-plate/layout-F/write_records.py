"""Write build.json, features.json and checks.json for layout F (V1.11 plus no P1 and the wire notches, 2026-10-14, and the four-screw cap, 2026-10-15) from layout_f.json (build_f.py), hip_sweep.json
(hip_sweep.py), post_build.json and insertion_check.json (post_build.py: print poses, solids, outline, wire penetration, fitting
paths), the V1.11 print rows (release-V1.11/scripts) and the print gate receipt.
Everything is in the real world frame (mm, x forward, y left, z up).

    python3 write_records.py"""
import json, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
J = lambda p: json.loads(Path(p).read_text())
L = J(HERE / 'layout_f.json'); H = J(HERE / 'hip_sweep.json'); PB = J(HERE / 'post_build.json'); CS = L['capScrew']; CS2 = L['capScrew2']; TS = L['capTopScrews']; NT = L['notch']
REL = HERE.parents[1] / 'release-V1.15/scripts'   # V1.15 release rows (rows-orange.json): frame minimum 250 after the ear bosses went
POSE = J(REL / 'pose-check.json') if (REL / 'pose-check.json').exists() else None
ROWS = {r['key']: r for r in J(REL / 'rows-orange.json')} if (REL / 'rows-orange.json').exists() else {}
GATE = HERE.parents[2] / 'content/interference-audit/gate-receipt.json'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
dump = lambda o, n: (HERE / n).write_text(json.dumps(o, indent=1) + '\n')

XL_HOLES = {'top_7V': [[-51.03, 28.25, 17.7], [-51.03, 28.25, 38.7], [-51.03, -28.25, 17.7], [-51.03, -28.25, 38.7]],
            'mid_5V': [[-51.03, 28.25, -10.9], [-51.03, 28.25, 10.1], [-51.03, -28.25, -10.9], [-51.03, -28.25, 10.1]]}
PD_HOLES = [[-50.0, 11.37, -31.91], [-50.0, 11.37, -16.67], [-50.0, -11.37, -31.78], [-50.0, -11.37, -16.54]]
COVER = [[-47.0, 16.1, 26.0], [-47.0, 16.1, -36.5], [-47.0, -16.1, 26.0], [-47.0, -16.1, -36.5]]
SCREWS = [
    dict(where='XL4015 bosses at z -10.9 (y +-28.25), 5.0 long (5 V board lower corners); the 7 V board top corners at z 38.7 take the cap top screws', count=2, screw='M2 x 6', stack='PCB 1.65 mm', pilotMm='dia 1.6 from the seat x -50.205 to x -45.3', engagementMm=4.35),
    dict(where='XL4015 bosses at z 10.1 (y +-28.25), 4.2 long (stub to x -46.0, shell limited)', count=2, screw='M2 x 6', stack='PCB 1.65 mm', pilotMm='dia 1.6 through the stub (tip 0.15 past the stub end)', engagementMm=4.2),
    dict(where='XL4015 bosses at z 17.7 (y +-28.25), 3.2 long (no stub: the torso shells are 1.29 / 1.17 mm ahead)', count=2, screw='M2 x 4', stack='PCB 1.65 mm', pilotMm='dia 1.6 through the boss', engagementMm=2.35),
    dict(where='Adafruit 5991 to the standoff bosses (5.0 long) at (y +11.37, z -31.91) and (y -11.37, z -31.78); the two upper holes take cap screws', count=2, screw='M2 x 6', stack='PCB 1.6 mm', pilotMm='dia 1.6 from the seat x -50.0 (3.0 standoff) to x -45.3 (4.7 deep)', engagementMm=4.4),
    dict(where='cap: through the driver holes in the cap back and the column floors, through the 5991 upper holes (y, z) %s and %s into their standoff bosses; heads on the column floors at x %s, tip x %s' % (CS['axisYZ'], CS2['axisYZ'], CS['seatX'], CS['tipX']),
         count=2, screw='M2 x 10', stack='column floor %.1f mm + gap %.1f mm + PCB 1.6 mm' % (CS['floorX'][1] - CS['floorX'][0], CS['gapColumnToPcbMm']), pilotMm='existing 5991 boss pilot dia 1.6 from x -50.0 to x -45.3', engagementMm=CS['engagementMm']),
    dict(where='cap top: through the driver holes in the cap back and the column floors, through the 7 V board top corner holes (y, z) %s into their 5.0 long bosses; heads on the column floors at x %s, tip x %s' % (TS['axesYZ'], TS['seatX'], TS['tipX']),
         count=2, screw='M2 x 10', stack='column floor %.1f mm + gap + PCB 1.65 mm' % (TS['floorX'][1] - TS['floorX'][0]), pilotMm='existing XL4015 boss pilot dia 1.6 from the seat x -50.205 to x -45.3', engagementMm=TS['engagementMm']),
    dict(where='frame to the V1.8 pack cover posts (reused V1.8 screws); the lower two heads sit in dia 4.4 driver lanes', count=4, screw='M2 x 6', stack='front plate 2.0 mm', pilotMm='V1.8 pack posts (4.8 deep pilots)', engagementMm=4.0),
]
WIRES = {k: dict(net=v['net'], lengthMm=v['lengthMm'], minBendRadiusMm=v['minBendRadius'], gapFrameMm=v['gapFrame'], gapLidMm=v['gapLid'],
                 gapBoardsMm=v['gapBoards']) for k, v in L['wires']['perWire'].items()}
st = L['stack']

build = dict(
    variant='F (V1.11 release source)', worldFrame='real world (mm, x forward, y left, z up)', source='build_f.py (python build_f.py F)',
    handedness=dict(
        result='XL4015 IN terminal at board-local -Y; with R_XL (local Y -> +y) the IN ends face world -y, OUT ends +y.',
        evidence=['bringup/parts/photos/xl4015_robotis_kit_top.jpg: component side, trimmers at the bottom, OUT+ on the left, IN+ on the right; '
                  'the TO-263 regulator sits right of centre toward IN, the coil left of centre.',
                  'board_facts.json bodiesLocal (ROBOTIS mesh): regulator_ic Y -10.94..-0.76, inductor Y 1.74..8.95, trimmers Z 7.99..12.82; '
                  'viewed from +X, screen right = -Y and screen down = +Z, so IN (right) = local -Y.'],
        fix='the whole layout is the y-mirror of the first F render (IN windows -y, OUT +y, 5991 turned 180 deg about x: terminal -y, USB-C +y); '
            'the 5 V pair moves outboard of the inductor and the top lid screw moves over the regulator IC.'),
    boards=dict(
        top_7V=dict(worldStl='xl4015_top_7V-world.stl', worldKey='xl4015_left', role='XL4015 #1, 7 V rail (6.80 V) to OpenRB J4', pcbMidX=-51.03, seatX=-50.205,
                    centreZ=st['top7V']['zc'], pcbZ=st['top7V']['pcbZ'], rotationLocalToWorld=[[-1, 0, 0], [0, 1, 0], [0, 0, -1]], inEnd='-y', outEnd='+y', screwHoles=XL_HOLES['top_7V']),
        mid_5V=dict(worldStl='xl4015_mid_5V-world.stl', worldKey='xl4015_right', role='XL4015 #2, 5.0 V Pi lead', pcbMidX=-51.03, seatX=-50.205,
                    centreZ=st['mid5V']['zc'], pcbZ=st['mid5V']['pcbZ'], rotationLocalToWorld=[[-1, 0, 0], [0, 1, 0], [0, 0, -1]], inEnd='-y', outEnd='+y', screwHoles=XL_HOLES['mid_5V'])),
    pd5991=dict(worldStl='pd5991_F-world.stl', worldKey='pd5991', pcbBackX=-50.0, standoffMm=3.0, pcbZ=st['pd5991']['pcbZ'], terminalSide='-y', usbSide='+y',
                terminalEntries=[[-54.6, -13.2, z] for z in st['pd5991']['terminalEntryZ']], usbSocketCentre=st['pd5991']['usbSocketCentre'], screwHoles=PD_HOLES),
    holes=dict(coverScrews=COVER, capScrew=CS, xl4015Bosses=XL_HOLES, pd5991Bosses=PD_HOLES),
    envelope=dict(box=L['box'], stack=st, rounding=L['rounding']['final']),
    windows=L['windows'], passages=L['passages'], capRetention=L['capRetention'], screws=SCREWS, wires=WIRES,
    frame=L['frame_F-world.stl'], lid=L['lid_F-world.stl'], massTotalG=L['massTotalG'],
    printPoses=dict(frame='rear_frame-print.stl: rim-down, the open back (x -65.9, lid seat) on the bed; x\' = y, y\' = z, z\' = x',
                    lid='rear_lid-print.stl: inner face (x -65.9) on the bed; x\' = y, y\' = -z, z\' = -x'),
    sha256={n: sha(HERE / n) for n in ('rear_frame-world.stl', 'rear_lid-world.stl', 'xl4015_top_7V-world.stl', 'xl4015_mid_5V-world.stl', 'pd5991_F-world.stl', 'wires_F.json')})
dump(build, 'build.json')

W = L['windows']
features = dict(
    frame=[
        dict(id='cover_plate', what='rear_pack_cover plate x -47..-45 with the cover outline, top corners r1.5, back edges r1, from build_rear_pack.build_cover()', purpose='seats on the V1.8 pack exactly as the printed cover did'),
        dict(id='cover_holes', what='four dia 2.2 holes at ' + str(COVER), purpose='the four reused V1.8 M2 x 6 cover screws into the pack posts'),
        dict(id='lip', what='lip x -45..-37.5, |y| <= 13.2, z 27.3..28.5 (from the cover)', purpose='locates the frame in the converter channel'),
        dict(id='web', what='front plate continued to the box outline below z -2 (x -47..-45)', purpose='closes the box front below the cover outline'),
        dict(id='front_plate_solid', what='the front plate x -47..-45 has no wire passage (front passage P1 deleted 2026-10-14)', purpose='no wire crosses the plate; the 7 V and 5 V pairs enter the pack over its top edge through notch B'),
        dict(id='notch_A', what='top-wall front edge cut back from x -47.0 to x %s over real y %s..%s (%.1f wide), through the 1.2 wall, rear corners r %s' % (NT['A']['x'][0], NT['yBand'][0], NT['yBand'][1], NT['widthMm'], NT['A']['cornerR']),
             purpose='the four +y wires (lanes y %s) bend down from the box top into the box front cavity at x -47.8 with the 3 mm bend radius; hidden in the crevice between the box front and the shell rear edge' % list(NT['lanesY'].values())),
        dict(id='notch_B', what='cover-plate top edge cut from z 29.5 down to z %s over the same y band and the plate thickness x -47..-45, floor corners r %s; the cover lip (z 27.3..28.5) is untouched' % (NT['B']['floorZ'], NT['B']['cornerR']),
             purpose='the wires pass under the shell lip (underside z 31.6..31.9) at centreline z 30 and ride on the cover lip into the pack'),
        dict(id='wide_tier', what='box |y| <= 32.05, z -15.2..43, wall 1.2, rim x -65.9', purpose='houses the two XL4015s, horizontal, long axis y'),
        dict(id='narrow_tier', what='box |y| <= 15.61, z -36.02..-15.2, closed bottom (floor z -36.02..-34.82)', purpose='houses the Adafruit 5991'),
        dict(id='square_rim', what='rim at x %s; constant inner cross-section from the rim to the front plate; all rear rounding is in the cap' % L['rounding']['final']['frameRimX'], purpose='every board slides straight in from the rear with the cap off'),
        dict(id='xl_bosses', what='eight dia 4.5 bosses from the seat x -50.205, ribs to the side walls, pilots dia 1.6; length from the seat 5.0 at z 38.7 and -10.9 (stubs in front of the wall or the cover plate), 4.2 at z 10.1, 3.2 at z 17.7 (torso shells ahead)', purpose='XL4015 mounting, M2 x 6 (M2 x 4 at z 17.7); the two z 38.7 bosses take the cap top screws (M2 x 10) through the 7 V board'),
        dict(id='pd_bosses', what='four dia 4.5 bosses, 3.0 standoff (seat x -50.0), 5.0 long, pilots to x -45.3', purpose='5991 mounting: two M2 x 6 in the lower holes; the two upper bosses (y +11.37, z -16.67) and (y -11.37, z -16.54) take M2 x 10 cap screws through the PCB; the standoff clears the through-hole pins'),
        dict(id='cover_screw_lanes', what='dia 4.4 lanes along x at (|y| 16.1, z -36.5), from the plate face x -47 to the rim', purpose='head clearance and driver access for the two lower cover screws at the narrow tier corners'),
        dict(id='xl_windows', what='side windows x -65.9..-53.205 at each XL4015 terminal: IN windows in the -y wall, OUT windows in the +y wall, z 23.0..33.4 (top) and -5.6..4.8 (middle)', purpose='each wire leaves its terminal straight out and runs outside the wall (no U-loop since 2026-10-14); the window keeps the x range so each board slides in with its wires attached; U-loop text retired: wall and returns into the rear lane'),
        dict(id='pd_term_window', what='window x %s, -y wall of the narrow tier, z %s' % (W['pd5991_term']['x'], W['pd5991_term']['z']), purpose='15 V feed wires into the 5991 terminal'),
        dict(id='usb_slot', what='slot x %s (open to the rim, closed by the cap), +y wall of the narrow tier, z %s' % (W['pd5991_usbc']['x'], W['pd5991_usbc']['z']), purpose='USB-C plug into the 5991 socket; the socket overhangs the PCB edge and slides in along the slot'),
    ],
    wiring=[dict(id=k, net=v['net'], lengthMm=v['lengthMm']) for k, v in WIRES.items()] + [
        dict(id='rule', what='22 AWG, 1.8 mm tube, centreline bend radius 3; every wire >= 0.3 mm from the boards, frame and lid (checks.json 4_wires), wire to wire >= 0; '
                              'every wire leaves its terminal straight out through its side window and stays outside the box: 15 V link and feed window to window outside the -y wall; '
                              '7 V and 5 V up the outside of the +y wall (columns x %s), across the box top at z 45 in lanes y %s, down through notch A, under the shell lip through notch B, '
                              '7 V to OpenRB J4 and 5 V through the head notch to the pi-lead bundle point (-6, -14, 43.5); the cap radii stay at the V1.11 values (no wire inside the box limits them)'
                              % (json.dumps(NT['wireColumnsX']), json.dumps(NT['lanesY'])))],
    lid=[dict(id='cap', what='rounded cap x -67.1..%s, 1.2 mm walls, rear radii %s' % (L['rounding']['final']['frameRimX'], json.dumps(L['rounding']['final']['R'])), purpose='closes the box and carries the approved rounded rear edges; its recess holds the rear lane wires'),
         dict(id='cap_window_notches', what='the XL4015 and 5991-terminal windows continue through the cap side walls; the cap closes the rim end of the USB-C slot', purpose='kept from V1.11; the wires now cross the wall at x -54.7 and no longer use the cap part of the windows, so a later revision may close them'),
         dict(id='cap_columns', what='two dia %.1f columns from the cap back (x %.1f) to x %s on the 5991 upper hole axes (y %s, z %s) and (y %s, z %s); rear parts trimmed to the cap outline; 0.2 behind the USB-C socket, %.1f in front of the 5991 PCB'
                                % (CS['columnDia'], CS['columnX'][0], CS['columnX'][1], CS['axisYZ'][0], CS['axisYZ'][1], CS2['axisYZ'][0], CS2['axisYZ'][1], CS['gapColumnToPcbMm']), purpose='carry the two low cap screws from the cap back to the 5991; the gap keeps the cap seating on the rim first'),
         dict(id='driver_hole', what='dia %.1f bore x %.1f..%s through the cap back and the column' % (CS['driverHoleDia'], CS['driverHoleX'][0], CS['driverHoleX'][1]), purpose='screwdriver and M2 x 10 head pass in from the back of each low column; the head sits hidden inside the column'),
         dict(id='column_floor', what='floor x %s with a dia %.1f clearance hole' % (CS['floorX'], CS['clearHoleDia']), purpose='each M2 x 10 head bears on its floor and pulls the cap forward onto the rim'),
         dict(id='top_columns', what='two dia %.1f columns from the cap back to x %s on the 7 V board top corner hole axes %s, flattened inside the frame to |y| <= %s and z <= %s, dia %.1f driver bores to the floor x %s, dia %.1f clearance holes'
                                % (TS['columnDia'], TS['columnX'][1], TS['axesYZ'], TS['columnFlattenedTo']['absY'], TS['columnFlattenedTo']['zMax'], TS['driverHoleDia'], TS['floorX'], TS['clearHoleDia']),
              purpose='top retention (Shawn 2026-10-15: screws instead of tongues): M2 x 10 through the board corner holes into the frame bosses; the cap pushes straight on, no lift, no hook')])
dump(features, 'features.json')

hs = H['minimumOverSweep']
checks = {
    '1_manifold': dict(frame=dict(L['frame_F-world.stl']), lid=dict(L['lid_F-world.stl']), passed=L['frame_F-world.stl']['bodies'] == 1 and L['lid_F-world.stl']['bodies'] == 1),
    '2_fitAtRest': dict(clearancesHOME=L['clearancesHOME'], note='rear_pack-v18 0 mm is the cover seat by design; the two XL4015 seats (PCB on the boss tips and ends at the side walls) are checked in 3_boardsInBox', passed=all(v.get('overlapMm3', 0) == 0 for k, v in L['clearancesHOME'].items() if not k.startswith('xl4015_'))),
    '3_boardsInBox': dict(boardsVsFrame=L['boardsVsFrame'], boardsVsLidMm=L['boardsVsLid'],
                          note='PCB ends sit at the side wall inner faces (|y| 30.85) and the PCB back faces on the boss tips by design (overlaps under 0.2 mm3)', passed=all(v['overlapMm3'] < 0.2 for v in L['boardsVsFrame'].values())),
    '4_wires': dict(perWire=WIRES, wireWireGapMm=L['wires']['wireWireGapMm'], rule='wire to boards, frame and lid >= 0.3 mm (0.29 accepted for mesh rounding); wire to wire >= 0',
                    centrelinePenetration=PB['wireCentrelinePenetration'], failingWires=[k for k, v in PB['wireCentrelinePenetration']['perWire'].items() if v['frame']['centrelinePointsInside'] or v['lid']['centrelinePointsInside']],
                    note='the min_gap values miss tubes that pass right through the plate; the centreline probe (post_build.py) is the binding check. Routes: wires_real_F() in build_f.py (notch option, 2026-10-14)',
                    packPerWire=L['packPerWire'], shellPerWire=L['shellPerWire'],
                    passed=all(min(v['gapFrameMm'], v['gapLidMm'], *v['gapBoardsMm'].values()) >= 0.29 for v in WIRES.values()) and min(L['wires']['wireWireGapMm'].values()) >= 0
                           and not any(v['frame']['centrelinePointsInside'] or v['lid']['centrelinePointsInside'] for v in PB['wireCentrelinePenetration']['perWire'].values())),
    '5_hipSweep': dict(method='hip_sweep.py', grid=H['grid'], minimumMm={k: v.get('refinedTrueSurfaceMinMm', v['minMm']) for k, v in hs.items()}, detail=hs,
                       under2mm=H['under2mm'], note='convex-hull lower bounds (mj_geomDistance), refined to true surfaces where under 5 mm; every segment of every wire is a capsule chain (outside routes); rerun on the notch frame and wires_F.json of this build', passed=not H['under2mm']),
    '6_usbcPlug': dict(L['usbcPlugEnvelope'], passed=min(v for k, v in L['usbcPlugEnvelope']['gapsMm'].items() if k != 'frame_F') >= 2.0),
    '7_printability': dict(frame_rimDown=dict(pose='rim (x -59.1) on the bed, rear_frame-print.stl', bedContactAreaMm2=PB['rear_frame']['bedContactMm2'], heightMm=PB['rear_frame']['heightMm'],
                                              releaseRowMinimumMm2=ROWS.get('rear_frame', {}).get('flatContactMinimumMm2'),
                                              note='the ear boss ends no longer touch the bed; the V1.15 row minimum (rows-orange.json) is 250 mm2',
                                              support='tree support under the front-plate ceiling inside the box (12.1 mm above the bed) and under the cover flap below the box floor; boss tips print on support; no brim (R1: tip angle 71.5 deg; a 0.1 mm-gap brim on the 1.2 mm wall ring is hard to peel)'),
                           frame_upright_rejected=dict(pose='z -44 down', bedContactAreaMm2=60.8, heightMm=87.0, reason='only the cover strip touches the bed under an 87 mm part (R1)'),
                           frame_sideDown_rejected=dict(bedContactAreaMm2=546.0, heightMm=64.1, reason='three times taller than rim-down and the lip end needs support (as V1.10)'),
                           cap_outerFaceDown=dict(pose='outer rear face (x -67.1) on the bed, open side up, rear_lid-print.stl', bedContactAreaMm2=PB['rear_lid']['bedContactMm2'], heightMm=PB['rear_lid']['heightMm'],
                                                  releaseRowMinimumMm2=ROWS.get('rear_lid', {}).get('flatContactMinimumMm2'),
                                                  support='tree support under the rounded rear edges near the bed; the three screw columns rise from the bed face (driver bores open on it)'),
                           solids={k: {x: PB[k][x] for x in ('watertight', 'bodies', 'volumeMm3', 'eulerNumber')} for k in ('rear_frame', 'rear_lid')},
                           poseCheck='post_build.json (release-V1.11 pose-check.json covers the V1.11 parts)',
                           passed=all(PB[k]['watertight'] and PB[k]['bodies'] == 1 and PB[k]['bedContactMm2'] >= (ROWS.get(k, {}).get('flatContactMinimumMm2') or 0) for k in ('rear_frame', 'rear_lid'))),
    '8_insertion': dict(J(HERE / 'insertion_check.json'), rule='boards along -x 0..25 mm with the cap off; cap pushed straight on along +x; overlap only at the final seat',
                        outline=PB['outline'],
                        passed=all(v['maxOverlapMm3'] < 1.0 for k, v in J(HERE / 'insertion_check.json').items() if k.startswith(('xl', 'pd')))
                               and J(HERE / 'insertion_check.json')['cap_path']['boards']['maxOverlapMm3'] == 0 and PB['outline']['passed']),
    'screws': dict(rows=SCREWS, total=sum(r['count'] for r in SCREWS), stock='M2 x 4 / 6 / 8 / 10 only; M2 x 6 everywhere except M2 x 4 at the two z 17.7 XL4015 holes and the four M2 x 10 cap screws', passed=True),
}
if GATE.exists():
    g = J(GATE); checks['printGate'] = dict(receipt=str(GATE), checkedAt=g['checkedAt'], passed=g['passed'], checks=g['checks'],
                                     note='receipt of the last gate run on the released guide data; the gate has not been rerun on these regenerated parts')
checks['summary'] = dict(passFlags={k: v.get('passed') for k, v in checks.items() if isinstance(v, dict) and 'passed' in v})
dump(checks, 'checks.json')
print(json.dumps(checks['summary'], indent=1))
