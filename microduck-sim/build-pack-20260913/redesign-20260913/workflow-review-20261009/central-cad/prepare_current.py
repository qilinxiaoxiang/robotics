"""Current registered meshes, retained as meshes; no conversion to invented CAD solids."""
from pathlib import Path
import json,base64,array,hashlib,zipfile,html,struct,subprocess
D=Path(__file__).resolve().parent;R=D.parents[1];SIM=R.parents[1];G=R/'leg-guide-20261006';H=R/'head-redesign-20261008';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f=G/'full-build-data.json';h=H/'final-viewer-20261008/scene.json';data=json.loads(f.read_text());head=json.loads(h.read_text());parts={p['key']:p for p in data['parts'] if p['moduleId'] not in ['head','head-close','camera','electronics']}
for p in head['parts']:parts[p['key']]=p
legs={side:set(next(m for m in data['modules'] if m['id']==side+'-leg')['ownedPartKeys'])|{('ring10_torso' if side=='left' else 'ring5_torso')} for side in ['left','right']}
assert not legs['left']&legs['right'];(D/'current-mesh').mkdir(exist_ok=True)
rows=[]
for key,p in parts.items():
 a=array.array('f');a.frombytes(base64.b64decode(p['positionB64']));ix=array.array('I');ix.frombytes(base64.b64decode(p['indexB64']));dy=11 if key in legs['left'] else -11 if key in legs['right'] else 0
 bounds=[[min(a[i::3])for i in range(3)],[max(a[i::3])for i in range(3)]]
 record={k:v for k,v in p.items() if k not in ['positionB64','indexB64']};record.update(key=key,geometryRepresentation='triangle mesh; not native BREP',bounds=bounds,cLayoutTranslationMm=[0,dy,0],source=str(h if key in {x['key']for x in head['parts']}else f));rows.append(record)
 (D/'current-mesh'/f'{key}.json').write_text(json.dumps(p))
 if key in ['torso_base','power_support','shell_left','shell_right','regulator','regulator_insert','imu_clamp','fuse_carrier','motor5','motor10','yaw','right_yaw','ring10_torso','ring5_torso']:
  with (D/'current-mesh'/f'{key}.stl').open('wb')as out:
   out.write(b'CURRENT REGISTERED MESH / NOT NEW PRINT'.ljust(80,b' '));out.write(struct.pack('<I',len(ix)//3))
   for k in range(0,len(ix),3):out.write(struct.pack('<12fH',0,0,0,*[a[3*ix[k+j]+i]for j in range(3)for i in range(3)],0))
for conf in ['baseline','C']:
 zpath=D/f'current-duck-{conf}-mesh-reference.3mf'
 with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=3)as z:
  z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
  z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
  with z.open('3D/3dmodel.model','w') as stream:
   def write(s):stream.write(s.encode())
   write('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><metadata name="Title">Current duck '+conf+' mesh reference - NOT PRINTABLE</metadata><resources>')
   for num,(key,p)in enumerate(parts.items(),1):
    a=array.array('f');a.frombytes(base64.b64decode(p['positionB64']));ix=array.array('I');ix.frombytes(base64.b64decode(p['indexB64']));write(f'<object id="{num}" name="{html.escape(key)}" type="model"><mesh><vertices>')
    for k in range(0,len(a),3):write(f'<vertex x="{a[k]:.8g}" y="{a[k+1]:.8g}" z="{a[k+2]:.8g}"/>')
    write('</vertices><triangles>')
    for k in range(0,len(ix),3):write(f'<triangle v1="{ix[k]}" v2="{ix[k+1]}" v3="{ix[k+2]}"/>')
    write('</triangles></mesh></object>')
   if conf=='C':
    write(f'<object id="{len(parts)+1}" name="PB1033MI nominal battery CONCEPT" type="model"><mesh><vertices>')
    for x,y,z0 in [(x,y,z0)for z0 in [-38.95,26.95]for y in [-13,13]for x in [-45.45,35.45]]:write(f'<vertex x="{x}" y="{y}" z="{z0}"/>')
    write('</vertices><triangles>')
    for a,b,c in [(0,2,1),(1,2,3),(4,5,6),(5,7,6),(0,1,4),(1,5,4),(2,6,3),(3,6,7),(0,4,2),(2,4,6),(1,3,5),(3,7,5)]:write(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>')
    write('</triangles></mesh></object>')
   write('</resources><build>')
   for num,(key,p)in enumerate(parts.items(),1):
    dy=(11 if key in legs['left'] else -11 if key in legs['right'] else 0)if conf=='C'else 0
    write(f'<item objectid="{num}" transform="1 0 0 0 1 0 0 0 1 0 {dy} 0"/>')
   if conf=='C':write(f'<item objectid="{len(parts)+1}"/>')
   write('</build></model>')
report={'status':'REAL REGISTERED MESH REFERENCE / NOT PRINTABLE / NO WHOLE ASSEMBLY ACCEPTANCE','units':'mm','frame':'Current guide zero-joint world frame, trunk_base origin; X fore/aft, Y left/right, Z up. Positive Y left leg. No transform inferred from unrelated early humanoid STEP.','sourceVersionFinding':{'rejectedCompleteStep':str(SIM/'hardware-design-20260912/reference/microduck/cad/microduck.step'),'reason':'275-part earlier humanoid with shoulder/humerus/radius and pelvis/chest/trunk_top, not current duck. No valid whole-assembly registration.','communityCommit':subprocess.check_output(['git','-C',str(SIM/'Microduck-build-tutorial'),'rev-parse','HEAD'],text=True).strip(),'currentSourceCadAvailable':False,'nativeSource':'Community 3MF meshes; registered through guide sourceTransformWorld and FK body transforms.'},'leftShiftedKeys':sorted(legs['left']),'rightShiftedKeys':sorted(legs['right']),'translationPerLegMm':11,'invariant':'All vertices and relative transforms within each whole leg unchanged; corresponding fixed yaw rings moved too. Central mounting hardware must move with new interfaces; no designed replacement bridge yet.','legacyPowerOccupancy':'Old power_support, converter and eleven-fuse carrier retained as visible obstacles only. Power architecture under review, not presumed retained.','omissions':['Individual threaded screw bodies are not represented by the source mesh scene; screw attachment coordinates remain in the guide ledger.','BRep feature history unavailable for community printed solids; no faceted mesh misrepresented as analytic solid.'],'parts':rows,'sourceHashes':{str(p):sha(p)for p in [f,h,SIM/'hardware-design-20260912/whole-robot-20260912/assembly/body-transforms.json',Path(__file__)]},'outputs':{p.name:sha(p)for p in D.glob('*mesh-reference.3mf')}}
(D/'current-coordinate-contract.json').write_text(json.dumps(report,indent=2)+'\n');print('saved',len(parts),'parts',len(legs['left']),len(legs['right']))
