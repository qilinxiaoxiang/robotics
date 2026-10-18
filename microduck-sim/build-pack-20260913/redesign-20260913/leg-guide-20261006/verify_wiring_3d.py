#!/usr/bin/env python3
"""Independent electrical/spatial, delivered-UI and original-server acceptance.

Does not regenerate the diagram, operate a browser, or access robot hardware.
--source-only is an interim check and intentionally emits no completion marker.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import math
import re
import sys

G = Path(__file__).resolve().parent
R = G.parent

def read(path):
    return json.loads(Path(path).read_text())

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise AssertionError(message)

def close(a, b, tolerance=1e-6):
    return len(a) == len(b) and max(abs(float(x)-float(y)) for x, y in zip(a, b)) <= tolerance

def source_check():
    w = read(G/'wiring-guide-data.json')
    s = read(G/'wiring-spatial-data.json')
    d = read(G/'full-build-data.json')
    h = read(R/'motor-harness-reach.json')
    carrier = read(R.parent/'assembly/service-mounts/design.json')
    require(len(w['connections']) == len(s['connections']) == 51, '51 source connections required')
    require(len(s['nodes']) == 40 and len(w['nodes']) == 38, '38 original nodes plus two distinct auxiliary endpoints')
    nodes = {n['id']:n for n in s['nodes']}
    parts = {p['key']:p for p in d['parts']}
    require(len(nodes) == 40, 'duplicate node identity')
    require(set(n['id'] for n in w['nodes']) <= set(nodes), 'original electrical endpoint omitted')
    require(set(s['auxiliaryNodeIds']) == {'ground-star','otg'}, 'ground/OTG identities')
    require(nodes['ground-star']['position'] != nodes['star']['position'], 'positive and ground junction coincide')
    actual = {'regulator':'regulator','pi':'pi','openrb':'openrb','camera':'camera_board','imu':'imu_board','amp':'amplifier','speaker':'speaker'}
    actual.update({f'motor{i}':f'motor{i}' for i in range(1,16)})
    for nid, key in actual.items():
        p = parts[key]
        center = [(p['bounds'][0][i]+p['bounds'][1][i])/2 for i in range(3)]
        require(nodes[nid]['partKeys'] == [key] and close(nodes[nid]['position'],center), 'source CAD anchor mismatch '+nid)
        require('not' in nodes[nid]['anchorEvidence'].lower() and 'connector' in nodes[nid]['anchorEvidence'].lower(), 'centre falsely labeled exact connector '+nid)
    for n in nodes.values():
        require(len(n['position']) == 3 and all(math.isfinite(x) for x in n['position']), 'invalid node position')
        require(set(n['partKeys']) <= set(parts), 'missing assembly source')
        require(n['connectorOrientationVerified'] is False, 'unmeasured connector pose claimed verified')
        if n['kind'] in ['external-schematic','proposed-installation','cable-end-schematic']:
            require(n.get('proxyDimensionsIllustrative') is True, 'illustrative fitting dimensions mislabeled')
    for i in range(11):
        nid = f'F{i}'
        require(close(nodes[nid]['position'],carrier['fuses'][i]['center_mm']), 'fuse source envelope mismatch '+nid)
        require(nodes[nid]['slotAssignmentVerifiedInSource'] == (i < 9), 'unverified physical F9/F10 allocation claimed exact')
    require([c['id'] for c in s['connections']] == [c['id'] for c in w['connections']], 'source connection order changed')
    require([c['id'] for step in w['steps'] for c in step['connections']] == [c['id'] for c in w['connections']], '51 source connections not navigable exactly once')
    sc = {c['id']:c for c in s['connections']}
    wc = {c['id']:c for c in w['connections']}
    require(sum(len(c['segments']) for c in sc.values()) == s['segmentCount'] == 85, '85 spatial conductor segments required')
    for cid,c in sc.items():
        require(c['sourceConnectionId'] == cid and c['endpointPins'] == wc[cid]['pins'] and c['wire'] == wc[cid]['wire'], 'source pin/wire metadata changed '+cid)
        require(c['powered'] is False and c['physicalCableIdentificationConfirmed'] is False, 'hardware action claimed')
        require(c['segments'], 'empty connection '+cid)
        for seg in c['segments']:
            require(seg['from'] in nodes and seg['to'] in nodes, 'unknown endpoint '+cid)
            points = seg['points']
            require(len(points) >= 2 and all(len(q)==3 and all(math.isfinite(x) for x in q) for q in points), 'invalid route '+cid)
            require(close(points[0],nodes[seg['from']]['position']) and close(points[-1],nodes[seg['to']]['position']), 'route endpoints do not bind their anchors '+cid)
            require(sum(math.dist(a,b) for a,b in zip(points,points[1:])) > .05, 'zero-length invisible cable '+cid)
            require(seg['actualConnectorCoordinates'] is False and seg['routeEvidence'], 'unverified cable routing claimed actual '+cid)
    def edges(cid):
        return [(v['from'],v['to'],v['signal']) for v in sc[cid]['segments']]
    require(edges('charger-usb') == [('charger','receiver','USB power negotiation')], 'source negotiation cable endpoints')
    require(edges('input-fuse') == [('receiver','inputFuse','20 V'),('inputFuse','xt30','20 V')], '20 V input fuse bypass')
    require(edges('input-return') == [('receiver','xt30','GND')], '20 V unfused return')
    require(edges('regulator-input') == [('xt30','regulator','20 V'),('xt30','regulator','GND')], 'regulator input polarity topology')
    require(edges('motor-main') == [('star','F0','5 V')]+[('F0',f'F{i}','5 V') for i in range(1,9)], 'main fuse bypass or branch sharing wrong')
    require(edges('pi-fuse') == [('star','F9','5 V')] and edges('audio-fuse') == [('star','F10','5 V')], 'logic/audio fused branches wrong')
    require(edges('star-output') == [('regulator','star','5 V'),('regulator','ground-star','GND')], 'positive/ground converter junctions mixed')
    powered = collections.Counter()
    for g in h['power_groups']:
        expected = [(a,f'motor{i}',signal) for i in g['servo_ids'] for a,signal in [(g['fuse'],'5 V'),('ground-star','GND')]]
        require(edges('motor-'+g['fuse']) == expected, 'motor fuse allocation or unfused return wrong '+g['fuse'])
        powered.update(g['servo_ids'])
    require(powered == collections.Counter(range(1,16)), 'each motor must have one assigned branch')
    chain = ['openrb']+[f'motor{i}' for i in h['data_chain'][1:]]
    for j,(a,b) in enumerate(zip(chain,chain[1:]),1):
        require(edges(f'data-{j:02d}') == [(a,b,'TTL DATA')], 'DATA-only lead bridges VDD or has incorrect order')
    bridge = sc['data-11']['segments'][0]['points'][1:-1]
    require(len(bridge) == len(h['ankle_bridge_routed_path_servo_centers'])-2, 'ankle DATA route shortcut')
    for point,sid in zip(bridge,h['ankle_bridge_routed_path_servo_centers'][1:-1]):
        require(close(point,nodes[f'motor{sid}']['position']), 'ankle bridge misses documented torso tour')
    require(edges('openrb-ground') == [('openrb','ground-star','GND')], 'OpenRB return reaches positive junction')
    for pin in [2,4]:
        require(edges(f'pi-5v-{pin}') == [('F9','pi','5 V')], 'Pi supply pin branch')
        require(sc[f'pi-5v-{pin}']['segments'][0]['toPin'] == str(pin), 'physical Pi 5 V contact')
    for pin in [6,14]:
        require(edges(f'pi-gnd-{pin}') == [('ground-star','pi','GND')], 'Pi unfused ground')
        require(sc[f'pi-gnd-{pin}']['segments'][0]['toPin'] == str(pin), 'physical Pi ground contact')
    require(edges('audio-vin') == [('F10','amp','5 V')] and edges('audio-return') == [('ground-star','amp','GND')], 'amplifier power topology')
    require(edges('pi-otg') == [('pi','otg','USB data + 5 V')] and edges('openrb-usb') == [('otg','openrb','USB data + 5 V')], 'distinct finished USB joints omitted')
    for cid in ['imu-vin','imu-sda','imu-scl','imu-gnd','audio-12','audio-35','audio-40','audio-20']:
        pin = wc[cid]['pins'][0]
        require(edges(cid) == [('pi','imu' if cid.startswith('imu-') else 'amp',pin['signal'])], 'sensor/audio signal mismatch')
        require(sc[cid]['segments'][0]['fromPin'] == pin['from'] and sc[cid]['segments'][0]['toPin'] == pin['to'], 'physical pin identity mismatch '+cid)
    require(edges('camera-ribbon') == [('camera','pi','CSI data + power')], 'camera/Zero adapter endpoints')
    require(edges('audio-gain') == [('amp','amp','3 dB gain')], 'gain resistor loop omitted')
    require('100' in sc['audio-gain']['segments'][0]['toPin'], 'gain resistor value omitted')
    require(edges('speaker') == [('amp','speaker',p['signal']) for p in wc['speaker']['pins']], 'floating speaker output grounded or omitted')
    require([p['physical_pin'] for p in w['pi_header_pins']] == list(range(1,41)), 'complete physical header numbering')
    require({p['physical_pin'] for p in w['pi_header_pins'] if p['used']} == {1,2,3,4,5,6,9,12,14,20,35,40}, 'header assignments changed')
    for path,digest in s['sourceHashes'].items(): require(sha(path) == digest, 'stale spatial source '+path)
    require(sha(w['local_contract']) == w['local_contract_sha256'], 'stale wiring contract')
    require(s['physicalRoutingVerified'] is False and s['actualConnectorOrientationsVerified'] is False and s['energizingPerformed'] is False, 'physical commissioning falsely accepted')
    html = (G/'LEFT-LEG.html').read_text()
    for name, expected in [('SPATIAL',s),('WIRING',w)]:
        token = 'const '+name+'='
        require(token in html, 'missing bundled '+name)
        bundled,_ = json.JSONDecoder().raw_decode(html[html.index(token)+len(token):])
        require(bundled == expected, 'delivered HTML has stale '+name)
    require((G/'wiring3d.js').read_text() in html and (G/'viewer.js').read_text() in html, 'stale delivered UI renderer')
    return dict(connections=51,segments=85,nodes=40,headerContacts=40,sourceAnchors=len(actual),fullModelMeshes=len(parts))

def server_check():
    baseline = read(G/'server-blocking-baseline.json')
    live = read(G/'server-regression-live.json')
    require(baseline['baseline_single_thread_blocks_normal_HEAD'] is True, 'original failure not reproduced')
    require(live['passed'] and live['host']=='127.0.0.1' and live['port']==8766, 'original server URL not tested')
    require(live['script_sha256'] == sha(G/'serve_guide.py'), 'server evidence stale')
    for label in ['normal_HEAD_while_idle_incomplete_and_slow_reader_connections_open','normal_GET_while_idle_incomplete_and_slow_reader_connections_open','idle_times_out_and_closes','incomplete_headers_times_out_and_closes']:
        row = next((c for c in live['checks'] if c['check']==label),None)
        require(row and row['passed'], 'missing original failure regression '+label)
    sys.path.insert(0,str(G))
    from test_serve_guide import verify
    result = verify(8766)  # Actual current URL while incomplete requests remain open.
    require(result['passed'], 'current server failed bounded concurrency readback')
    return dict(url='http://127.0.0.1:8766/LEFT-LEG.html', checks=len(result['checks']), htmlSha256=sha(G/'LEFT-LEG.html'))

def ui_check():
    receipt = read(G/'wiring-3d-ui-20261007.json')
    require(receipt.get('passed') is True, '3D UI acceptance missing/failed')
    require(receipt.get('url') == 'http://127.0.0.1:8766/LEFT-LEG.html', 'wrong visible user destination')
    require(receipt.get('htmlSha256') == sha(G/'LEFT-LEG.html'), 'visible UI receipt does not bind delivered HTML')
    for name,digest in receipt['artifactHashes'].items(): require(sha(G/name)==digest, 'stale tested renderer/data '+name)
    if receipt.get('priorCapture'):
        # Prove the dependency-preserving repair is EXACTLY one conditional
        # expression. Installed/connector/trace results remain applicable;
        # header results below must be fresh after this changed branch.
        prior = receipt['priorCapture']
        new = "const c=wireMode==='header'?null:wireCurrent;const detail="
        old = 'const c=wireCurrent;const detail='
        js = (G/'wiring3d.js').read_text(); html = (G/'LEFT-LEG.html').read_text()
        require(js.count(new)==html.count(new)==1, 'header repair scope is not one expression')
        require(hashlib.sha256(js.replace(new,old,1).encode()).hexdigest()==prior['artifactHashes']['wiring3d.js'], 'unreviewed renderer change since 51×2 capture')
        require(hashlib.sha256(html.replace(new,old,1).encode()).hexdigest()==prior['htmlSha256'], 'unreviewed HTML change since 51×2 capture')
        for name,digest in prior['artifactHashes'].items():
            if name!='wiring3d.js': require(sha(G/name)==digest, 'changed dependency invalidates prior capture '+name)
    w = read(G/'wiring-guide-data.json'); s = read(G/'wiring-spatial-data.json')
    sc = {c['id']:c for c in s['connections']}
    require([c['id'] for c in receipt['connections']] == [c['id'] for c in w['connections']], '51 actual navigation pairs missing/duplicated')
    require(len(receipt['stages'])==len(w['steps'])==11, '11 actual stages missing')
    for capture,step in zip(receipt['stages'],w['steps']):
        require(capture['count']==len(step['connections']) and capture['state']['dataset']['wiringStep']==step['id'], 'stage navigation/count mismatch')
        require(capture['state']['canvas'] is True, 'stage canvas absent')
    for capture,c in zip(receipt['connections'],w['connections']):
        spatial = sc[c['id']]; installed = capture['installed']; connector = capture['connector']
        for mode,row in [('installed',installed),('connector',connector)]:
            data = row['dataset']
            require(row['canvas'] is True and data['connection']==c['id'] and data['wireMode']==mode, 'wrong actual 3D connection/mode '+c['id'])
            require('3D' in row['heading'] and c['purpose'] in row['detail'], 'connection details mismatch '+c['id'])
            require(any(v['display']=='block' for v in row['labels']), 'no visible endpoint/pin labels '+c['id'])
        data = installed['dataset']
        expected_segments = [{k:v[k] for k in ['from','to','signal','points']} for v in spatial['segments']]
        require(json.loads(data['wireSegments'])==expected_segments, 'actual rendered route differs from source '+c['id'])
        require(int(data['wireTubeCount'])==len(expected_segments), 'invisible/missing tube '+c['id'])
        require(set(json.loads(data['wireVisibleNodes']))=={v[k] for v in expected_segments for k in ['from','to']}, 'rendered endpoint coverage '+c['id'])
        require(set(json.loads(data['wireHighlightedParts']))==set(spatial['focusPartKeys']), 'component highlight source mismatch '+c['id'])
        require(set(spatial['focusPartKeys'])<=set(json.loads(data['visibleParts'])), 'highlighted source component hidden '+c['id'])
        data = connector['dataset']
        if ('pi' in c['fromNodeIds'] or 'pi' in c['toNodeIds']) and c['pins'] and c['id']!='camera-ribbon':
            detail,pins,tubes = 'pi-header-to-peripheral',40,len(c['pins'])
        elif c['id'].startswith('data-'): detail,pins,tubes = 'data-only-servo',6,1
        elif c['id'].startswith('motor-F'):
            motors = sum(v.startswith('motor') for v in c['toNodeIds'])
            detail,pins,tubes = 'individual-motor-power-tails',motors*3+2,motors*2
        elif c['id']=='camera-ribbon': detail,pins,tubes = 'camera-ribbon',37,0
        else:
            count = max(1,len(c['pins']))
            detail,pins,tubes = 'named-terminal-pair',count*2,count
        require(data['wireDetail']==detail and int(data['wirePinCount'])==pins and int(data['wireTubeCount'])==tubes, 'connector topology/contact diagram mismatch '+c['id'])
    header = receipt['header']
    require(header['dataset']['wireMode']=='header' and header['dataset']['wirePinCount']=='40', 'actual full header missing')
    visible_pin_labels = {int(re.match(r'^(\d+)',v['text'])[1]) for v in header['labels'] if v['display']=='block' and re.match(r'^\d+',v['text'])}
    require(visible_pin_labels==set(range(1,41)), '40 physical pin labels not visible')
    require('Click any pin' in header['detail'] and 'Gain setting' not in header['detail'] and 'Motor bus reference' not in header['detail'], 'stale connection card in header mode')
    for key,pin in [('headerSelection12',12),('headerSelection',40)]:
        row = receipt[key]; role = next(p['role'] for p in w['pi_header_pins'] if p['physical_pin']==pin)
        require(row['dataset']['selectedPin']==str(pin) and f'Physical pin {pin}' in row['detail'] and role in row['detail'], 'actual pin selection wrong')
        require('Gain setting' not in row['detail'] and 'Motor bus reference' not in row['detail'], 'pin selection mixed with unrelated wiring')
    endpoint_rows = {v['id']:v for v in receipt['endpoints']}
    require(set(endpoint_rows)=={'pi-gnd-6','pi-otg','openrb-usb','openrb-ground'}, 'endpoint regression controls missing')
    for cid,row in endpoint_rows.items():
        require((row['from'],row['to'])==(sc[cid]['segments'][0]['from'],sc[cid]['segments'][-1]['to']), 'endpoint selection misbound '+cid)
    trace = {key:v['dataset'] for key,v in receipt['trace'].items()}
    start,paused,later,resumed,finished = [trace[k] for k in ['start','paused','pausedLater','resumed','finished']]
    require(0<float(start['wireTraceProgress'])<float(paused['wireTraceProgress'])<1, 'trace did not progress')
    require(start['wireTracing']=='true' and paused['wireTracing']==later['wireTracing']=='false', 'trace pause controls')
    require(paused['wireTraceProgress']==later['wireTraceProgress'] and paused['renderedFrames']==later['renderedFrames'], 'paused animation still running')
    require(float(resumed['wireTraceProgress'])>float(paused['wireTraceProgress']) and resumed['wireTracing']=='true', 'trace did not resume')
    require(float(finished['wireTraceProgress'])==1 and finished['wireTracing']=='false', 'trace did not finish')
    idle = receipt['idle']
    require(idle['before']['dataset']['renderedFrames']==idle['after']['dataset']['renderedFrames'] and idle['shaBefore']==idle['shaAfter'], 'idle viewer changes without input')
    screenshots = {Path(v['path']).name:v for v in receipt['screenshots']}
    require({'wiring-3d-installed.png','wiring-3d-connector.png','wiring-3d-pi-header.png','wiring-3d-resistor.png','wiring-3d-idle-a.png','wiring-3d-idle-b.png'}<=set(screenshots), 'visible 3D evidence missing')
    for image in screenshots.values(): require(sha(image['path'])==image['sha256'], 'screenshot hash mismatch')
    require(sha(G/'wiring-3d-idle-a.png')==sha(G/'wiring-3d-idle-b.png')==idle['shaBefore'], 'idle pictures differ')
    require(receipt['errors']==[], 'browser errors recorded')
    require('Left leg' in receipt['assemblyReturn']['heading'] and set(json.loads(receipt['assemblyReturn']['dataset']['visibleParts']))=={'thigh','plate','motor7','motor8'}, 'assembly return regression')
    require(receipt['washerReturn']['dataset']['inspection']=='washer6' and 'washer6' in json.loads(receipt['washerReturn']['dataset']['visibleParts']), 'washer view return regression')
    return dict(actualConnectionModes=102,actualStages=11,selectedPins=[12,40],endpointRegressions=4,tracePauseResume=True,idleStable=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-only',action='store_true')
    args = parser.parse_args()
    source = source_check()
    if args.source_only:
        print('WIRING_3D_SOURCE_PASS',json.dumps(source))
        return
    ui = ui_check()
    server = server_check()
    print('WIRING_3D_CHECK_PASS',json.dumps(dict(source,ui=ui)))
    print('GUIDE_SERVER_CHECK_PASS',json.dumps(server))

if __name__ == '__main__':
    main()
