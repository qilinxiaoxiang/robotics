from pathlib import Path
import json,hashlib,zipfile,xml.etree.ElementTree as E
D=Path(__file__).resolve().parent;P=D.parent.parent/'printing/11-ASSEMBLY-REPAIR-20261008';N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
r=json.loads((D/'jaw-blocker-native-toolpaths.json').read_text());old=json.loads((D/'jaw-native-toolpaths.json').read_text());a=Path(r['archives'][0]['archive']);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(a)==r['archives'][0]['archiveSha256']
ori=json.loads((P/'orientation-preparation.json').read_text());expected={'main-60-pilot','main-76-pilot','S15-horn-045','S15-horn-046','S15-horn-047'};rows=[]
for name in sorted(expected):
 new=next(f for f in r['features'] if f['name']==name);base=next(f for f in old['features'] if f['name']==name)
 assert len(base['supportPotentialIntersectLines'])>0
 assert not new['supportPotentialIntersectLines'],name
 assert new['support']['radialInnerBoundMm']>new['radius'],name
 rows.append({'feature':name,'baselineSupportIntersectLines':len(base['supportPotentialIntersectLines']),'revisedSupportIntersectLines':0,'supportGapOutsideNominalHoleLowerBoundMm':new['support']['radialInnerBoundMm']-new['radius']})
with zipfile.ZipFile(a) as z:
 model=E.fromstring(z.read('3D/3dmodel.model'));meta=E.fromstring(z.read('Metadata/model_settings.config'));build={n.get('objectid'):list(map(float,n.get('transform').split())) for n in model.find(N+'build')}
 for obj in meta.findall('object'):
  name=obj.find("metadata[@key='name']").get('value');o=next(v for v in ori['parts'] if v['key']==name);b=build[obj.get('id')]
  assert all(abs(b[9+i]-o['placementXYMm'][i])<1e-5 for i in range(2))
  types=[v.get('subtype') for v in obj.findall('part')]
  assert types.count('normal_part')==1
  assert types.count('support_blocker')==(5 if name=='jaw_frame' else 0)
 assert hashlib.sha256(z.read('Metadata/plate_1.gcode')).hexdigest()==r['archives'][0]['gcodeSha256']
core=json.loads((D/'jaw-blocker-pilot-support-core.json').read_text());assert all(not v['segmentsWhoseCenterIsInsidePilotCore'] for v in core)
report={'passed':True,'scope':'Closes five local support-in-hole failures on exact revised native Yellow slice; unchanged externally removable supports and physical tolerance boundary remain.','archive':str(a),'archiveSha256':sha(a),'gcodeSha256':r['archives'][0]['gcodeSha256'],'sourceHashes':{str(p):sha(p) for p in [D/'audit_jaw_blocker_toolpaths.py',Path(__file__),D/'jaw-blocker-native-toolpaths.json',D/'jaw-blocker-pilot-support-core.json',D/'jaw-native-toolpaths.json',P/'orientation-preparation.json']},'rows':rows,'newBlindPilotActualCoreSupportSegments':[0,0],'nativeMultipartReadback':'jaw_frame:1 normal +5 support_blocker; cheek:1 normal; exact current placement checked','decision':'Keep existing orientation and use Yellow_blockers.3mf instead of the failed Yellow_preflight.3mf. No support remains in the five affected holes, including conservative bead envelopes.','remainingFinishing':'Remove externally accessible supports from central output opening and cheek head pockets. Check actual screw passage/seat fit; this is no dimensional-calibration claim.'}
(D/'jaw-blocker-functional-print-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'report':str(D/'jaw-blocker-functional-print-report.json'),'rows':rows},indent=2))
