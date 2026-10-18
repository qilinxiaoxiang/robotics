from pathlib import Path
import json,hashlib,runpy,html
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
for f in ['build_review.py','enhance_manifest.py']:runpy.run_path(str(D/f))
selfreceipt=read(D/'wire-geometry-check.json');assert selfreceipt['passed'] and selfreceipt['complete']
assert all(sha(f)==h for f,h in selfreceipt['sourceHashes'].items())
r=read(D/'integrated-harness.json');m=read(D/'body-distribution-manifest.json');z=read(D/'zone-feeds.json');h=read(D/'head-trunk.json')
receipts=[D/('head-trunk-check-'+p['key']+'.json')for p in h['parts']]
for f in receipts:
 c=read(f);assert c['complete'] and c['passedStatic'];assert c['sourceHashes'][str(D/'head-trunk.json')]==sha(D/'head-trunk.json')
r['status']='BODY_DISTRIBUTION_LEG_FEEDS_AND_OPEN_NECK_TRUNK_NEUTRAL_CHECKED;_HEAD_CONTINUATION_PENDING'
r['localGeometry']['scope']='DFR rear lands, two body distribution joints, both leg-zone feed pairs, and paired stationary head trunk to Z55; physical connectors, solder quality, cable handling and moving-neck continuation are not certified.'
r['localGeometry'].update(zoneFeedPairs=read(D/'zone-feed-check.json')['expectedPairs'],manufacturerMotorComponentPairs=36,headTrunkPairs=sum(read(f)['expectedPairs'] for f in receipts))
r['headDistribution']={'stationaryBodyTrunkAWG':18,'receivingDiameterMm':2.5,'designOperatingA':4.25,'basis':'2.25A head/neck motor zone plus2A shared nonmotor reserve; not a measured demand or wire manufacturer rating. Specify18AWG insulation/current rating suitable for this service.','ground':'Head electronics and head/neck motor returns meet in the head local distribution then follow this dedicated return; no motor return through the USB cable or OpenRB DXL contacts.','headSplicePosition':None,'geometryStatus':'Only body-to-open-boundary pair checked; head node is unplaced until adopted head layout.'}
for x in r['connections']:
 if x['id'] in ['converter-positive','converter-return']:x.update(neutralGeometryAccepted=True,physicalRouteAccepted=False)
 if x['id']=='zone-left-leg':x.update(installedLengthMm={p['net']:p['lengthMm']for p in z['parts']if 'left' in p['key']},neutralGeometryAccepted=True,physicalRouteAccepted=False,lengthEvidence='Complete installed neutral centerlines; termination/service allowances require unpowered fitting')
 if x['id']=='zone-right-leg':x.update(installedLengthMm={p['net']:p['lengthMm']for p in z['parts']if 'right' in p['key']},neutralGeometryAccepted=True,physicalRouteAccepted=False,lengthEvidence='Complete installed neutral centerlines; termination/service allowances require unpowered fitting')
r['connections'].append({'id':'power-head-trunk','from':'paired body distribution joints','to':'open neck boundary at Z55; not a head electrical connector','gaugeAWG':18,'installedLengthMm':{p['net']:p['lengthMm']for p in h['parts']},'neutralGeometryAccepted':True,'physicalRouteAccepted':False,'wholeHeadContinuationAccepted':False})
r['remainingEngineeringWork']=['Incoming VIN/tether internal termination and strain relief','DATA-only cross-zone boundary leads and insulated removed terminals','Head local power distribution, final endpoints and complete moving-neck service slack','Unpowered harness fit/retention, solder insulation, real stock and loaded commissioning']
r['sourceHashes'].update({str(f):sha(f)for f in [D/'wire-geometry-check.json',D/'zone-feed-check.json',D/'zone-feed-own-motors.json',D/'socket13-pin-order.json',D/'head-trunk.json',*receipts,Path(__file__)]})
for p in h['parts']:m['additionalParts'].append(dict(p,color='#e84c37'if p['net']=='5V'else '#262b34',name='Paired head supply to open neck boundary — '+p['net'],geometryKind='receiving-wire-route',coordinates='world mm; identity'))
m['connections'].append({'id':'power-head-trunk','tutorialStepIds':['power-03','power-05'],'partKeys':[p['key']for p in h['parts']],'focusPartKeys':['power_support','shell_left','shell_right','motor11','motor12'],'fromEndpoint':{'connectorType':'paired body solder splices','positionsMm':[[-7,-7,35.5],[-7,7,35.5]],'outwardAxis':None},'toEndpoint':{'connectorType':'open flexible harness boundary, not connector','positionsMm':[[6,-7.6,55],[6,-3.8,55]],'outwardAxis':[0,0,1],'poseVerified':False,'illustrativeOnly':True},'geometryAcceptedScope':'Stationary body neutral pose to Z55 only; no head terminal, moving-neck slack or complete harness claim','installedCenterlineLengthsMm':{p['net']:p['lengthMm']for p in h['parts']},'assembly':['Leave the head end free while fitting the torso. Carry the paired18AWG supply through the existing open central neck region.','Retain the insulated stationary segment near the support; leave the Z55 ends untied until full neck travel and adopted head entry are arranged.','Do not trim to the body segment length: the flexible moving-neck and head-end material is additional.']})
m['headTrunkReceipts']=[{'file':str(f),'sha256':sha(f)}for f in receipts]
m['integrationScope']='Neutral body distribution, two leg-zone paired feeds and stationary head trunk to open Z55 boundary. Exact STL illustration only; no whole-head or energized acceptance.'
r['passed']=True;r['acceptanceScope']=m['integrationScope'];r['selfCheckReceipt']={'file':str(D/'wire-geometry-check.json'),'sha256':sha(D/'wire-geometry-check.json')}
m['integrationReady']=True;m['status']='NEUTRAL_BODY_SUBSET_STATIC_AND_SELF_CHECKED'
(D/'integrated-harness.json').write_text(json.dumps(r,indent=2)+'\n');m['receiptSha256']=sha(D/'integrated-harness.json')
(D/'body-distribution-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
p=D/'POWER-WIRING.html';s=p.read_text().replace('converter-to-distribution body geometry is checked. Outgoing zone feeds, the final head/neck route and powered load testing remain open.','the converter-to-distribution leads, both leg-zone paired feeds and the stationary head trunk to the open neck boundary are checked in the neutral pose. DATA-only boundary leads, moving-neck slack, final head endpoints and powered load testing remain open.')
s=s.replace('<h2>What is checked in the body</h2>','<h2>Actual body route</h2><p>The paired feeds enter motor5 and motor10 at their source socket13, with pin1 GND, pin2 VDD and pin3 DATA identified from the keyed header. They pass around the original support’s front edge at X≈13mm, then rearward above the support. The eight existing leg cables remain unchanged. Four new feed conductors pass866 body/wire checks; the source motor solids independently resolve36 local checks without filling the socket cavities.</p><p>Paired18AWG supply continues to free ends at [6,−7.6,55]mm and [6,−3.8,55]mm, passing439 checks. This is a stationary neck-entry boundary, not a made-up head connector. It carries the4.25A design allowance for the head/neck motor zone and logic to a future head-local split; the full moving span remains additional.</p><h2>What is checked in the body</h2>')
s=s.replace('Place the three receiving-side motor injection adapters and set their actual lengths with motion slack.','Fit the two checked leg-zone feed routes and assemble the DATA-only boundary interfaces before closing; leave the head-zone endpoint pending its adopted layout.')
p.write_text(s)
# Lightweight contract/readback: exact meshes and translated source context, no hidden cable interpolation.
for p in m['additionalParts']:
 assert Path(p['file']).is_file();assert sha(p['file'])==p['sha256']
assert len({c['id']for c in m['connections']})==len(m['connections'])
keys={p['key']for p in m['additionalParts']}|{p['key']for p in m['contextParts']}
assert all(set(c['partKeys']+c['focusPartKeys'])<=keys for c in m['connections'])
assert m['receiptSha256']==sha(D/'integrated-harness.json')
assert '<html lang="en">' in s and '<svg' in s and '<table'not in s
out={'passed':True,'manifestSha256':sha(D/'body-distribution-manifest.json'),'receiptSha256':sha(D/'integrated-harness.json'),'pageSha256':sha(D/'POWER-WIRING.html'),'connectionIds':[c['id']for c in m['connections']],'routeMeshCount':len(m['additionalParts']),'wholeHarnessAccepted':False}
(D/'handoff-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
