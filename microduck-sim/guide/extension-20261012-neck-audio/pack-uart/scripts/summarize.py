"""Collect the headline numbers into ../pack-uart-study.json (each value tagged measured / official / inference)."""
import json
import uart_lib as U

S = json.loads((U.STUDY / 'sockets.json').read_text())
O = json.loads((U.STUDY / 'options.json').read_text())
sw = {}
for side in ('left', 'right'):
    p = U.STUDY / f'sweep-uart-{side}.json'
    if p.exists():
        d = json.loads(p.read_text())
        nf = lambda g: g if g < 99 else 'no frame within the 5.1 mm screen (>= 2 mm by the method bound)'
        sw[side] = {'adoptedFrames': d['adopted']['frames'], 'legMinGapMm': nf(round(d['adopted']['pitchChain']['minGapMm'], 2)),
                    'hipBodiesMinGapMm': '>= 8 (min_gap search cap)' if d['adopted']['hipBodies']['minGapMm'] >= 8 else round(d['adopted']['hipBodies']['minGapMm'], 2),
                    'allFramesLegMinGapMm': nf(round(d['allFramesIncludingExcludedRuns']['pitchChain']['minGapMm'], 2)),
                    'allFrames': d['allFramesIncludingExcludedRuns']['frames']}
J7 = {s['socket']: s for s in S['rows']['J7']['sockets']}; J6 = {s['socket']: s for s in S['rows']['J6']['sockets']}
w = lambda o: O[o]['worst']
out = {
    'problem': 'P5/P6: Pi <-> OpenRB-150 UART with Dupont jumpers in the V1.8 rear pack',
    'date': '2026-10-12',
    'measured': {
        'socketTopX': S['rows']['J7']['socketTopX'], 'coverInnerFaceX': -45.0, 'socketTopToCoverMm': round(S['rows']['J7']['socketTopX'] + 45.0, 2),
        'pitchMeasured': {'J6': S['rows']['J6']['pitchMeasured'], 'J7': S['rows']['J7']['pitchMeasured']},
        'J7': {n: {'name': J7[n]['name'], 'y': J7[n]['y'], 'z': J7[n]['z'], 'freeDepth': J7[n]['freeDepthBehindTopMm']} for n in (4, 6, 7)},
        'J6': {n: {'name': J6[n]['name'], 'y': J6[n]['y'], 'z': J6[n]['z'], 'freeDepth': J6[n]['freeDepthBehindTopMm']} for n in (3, 4)},
        'converterBox': S['regulatorBounds'],
        'socketTopToConverterBackMm': J7[7]['freeDepthBehindTopMm'].get('regulator'),
        'windowJ6': O['windows']['J6_A1A2'], 'windowJ7GND': O['windows']['J7_GND'],
        'shellBand': O['shellBand'], 'outsideRun': O['outsideRun'], 'wireLengths': O['wireLengths'],
    },
    'optionWorstPairs': {k: w(k) for k in ('D0', 'D1_minusY', 'D1_plusY', 'C', 'B', 'A', 'A+G', 'vin20_reroute')},
    'optionA_insertion': O['A']['insertion']['worst'], 'optionAG_insertion': O['A+G']['insertion']['worst'],
    'plugsVsGuideVin20Route': O['A+G']['withGuideVin20Route'],
    'bentPinBudget_inference': O['B']['bentPinBudget'],
    'walkingSweepAddedMaterial': sw or 'not run',
    'inference': ['Dupont housing 2.54 x 2.54 x 14 mm and about 6 mm of male pin (vendor listings; measure the owned jumpers)',
                  'wire OD 1.3 mm, 3 mm straight before a bend', 'bent-pin insertion 3.4 mm', 'firmware pad move compiles and runs (not built here)',
                  'common ground through the 5 V pairs is adequate at 1 Mbps (calculation, not measured)'],
}
U.jdump(out, U.STUDY / 'pack-uart-study.json')
print(json.dumps(out['optionWorstPairs'], indent=0)); print(sw)
