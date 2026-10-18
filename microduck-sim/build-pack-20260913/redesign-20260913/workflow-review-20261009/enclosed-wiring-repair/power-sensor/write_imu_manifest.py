from pathlib import Path
import json,hashlib,struct
D=Path(__file__).resolve().parent
I=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bounds(p):
 data=Path(p).read_bytes();n=struct.unpack_from('<I',data,80)[0];lo=[1e30]*3;hi=[-1e30]*3
 for i in range(n):
  v=struct.unpack_from('<12f',data,84+50*i)
  for j in [3,6,9]:
   for a in range(3):lo[a]=min(lo[a],v[j+a]);hi[a]=max(hi[a],v[j+a])
 return [lo,hi]
report=D/'imu-assembly-check.json';check=json.loads(report.read_text());assert check['passed'] and check['complete']
for p,h in check['sourceHashes'].items():assert sha(p)==h,p
reg=json.loads((D/'bno085-endpoint-registration.json').read_text());route=json.loads((D/'body-routes.json').read_text());ret=json.loads((D/'imu-retention.json').read_text())
parts=[]
def add(key,name,step,mesh,color,T=I,role='solid'):
 step=D/step;mesh=D/mesh
 parts.append({'key':key,'name':name,'file':str(step),'sha256':sha(step),'format':'STEP','units':'mm','sourceToWorld':T,'coordinates':'world millimetres,identity transform' if T==I else 'manufacturer board-local millimetres; apply sourceToWorld once','meshFile':str(mesh),'meshSha256':sha(mesh),'meshCoordinates':'world millimetres; no extra transform','expectedFinalBoundsMm':bounds(mesh),'color':color,'group':'BNO085 complete local assembly','role':role})
add('imu_clamp','IMU holder: registered side port and PCB locating seats','imu-clamp-retained-world.step','imu-clamp-retained-world.stl','#ff8000')
add('imu_cover','IMU rear cover: mounting-hole stops and integral tie land','imu-cover-retained-world.step','imu-cover-retained-world.stl','#202020')
add('imu_board','Adafruit4754 BNO085: official native55-solid model','sources/bno085.step','bno085-valid-native-world.stl','#277d4a',reg['sourceToWorld'])
add('imu_sh4_receiving','JST SH4 published housing receiving volume','jst-sh4-receiving-world.step','jst-sh4-receiving-world.stl','#ddd7c5',role='connector-receiving-envelope')
colors={'gnd':'#242424','3v3':'#d8423b','sda':'#3fa66c','scl':'#ddb831'}
lengths={}
for p in route['parts']:
 if not p['key'].startswith('imu_'):continue
 add(p['key'],f"BNO085 {p['net']} body-side lead",Path(p['nativeStep']).name,Path(p['file']).name,colors[p['key'][4:]],role='wire')
 lengths[p['net']]={'routedLengthMm':p['lengthMm'],'nominalCableLengthMm':150,'conservativeConnectorReserveMm':19.25,'remainingNominalMm':150-19.25-p['lengthMm'],'freeBoundaryWorldMm':p['toFreeNeckBoundary']}
m={'title':'BNO085 local assembly: registered board, keyed port, retention and rear closure','problemIds':['P0','P5','P6'],'units':'mm','parts':parts,'localDigitalAssemblyAccepted':True,'acceptance':{'report':str(report),'sha256':sha(report),'checks':len(check['checks']),'zeroUnintendedIntersections':True,'scope':check['scope']},'sourceCoordinateContract':'Only official BNO STEP uses sourceToWorld; all other STEP files and ALL meshFile assets are alreadyworld coordinates. The correct3x3 rotation determinant is+1.','assemblyOrder':ret['assemblyOrder']+['Thread one4.8mm nylon tie through the integral cover slots after closure to retain the four insulated leads.','The four free ends stop at the open neck-root boundary. Do not treat them as seated Pi connectors.'],'hardware':'Reuse the original fourM2 rear-cover screws. No new screw or separate printed clip. One nylon tie receiving path; spare stock not asserted.','wireLengthBoundary':lengths,'notAcceptedByThisReceipt':['Head connection and full wire continuation','Articulated neck service loop','Power distribution and electrical commissioning','Printed physical tolerances and tool usability on the actual specimen'],'physicalFitVerified':False,'wholeHarnessAccepted':False,'currentPrintPackageModified':False,'supersededEvidence':{'invalidOldRegistrationSha256':'c442b23d878d98b50bc50943fcc314b8d0afbdbee2274a183952fcdc8316e9ea','cause':'Historical transform determinant−1 mirrored the board; all reports bound to that registration are invalid for installation acceptance.'},'sourceHashes':{str(D/f):sha(D/f) for f in ['bno085-endpoint-registration.json','imu-retention.json','sources/jst-sh.pdf','sources/bno085.brd','write_imu_manifest.py']}}
(D/'imu-local-manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps({'file':str(D/'imu-local-manifest.json'),'sha256':sha(D/'imu-local-manifest.json'),'parts':len(parts),'checks':len(check['checks'])}))
