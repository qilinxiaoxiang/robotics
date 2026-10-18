"""Finite .25mm sampling of exact bench assembly state; no cable or full closure claim."""
from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(D/'build_reverse_nut_camera.py');m=json.loads(read(O/'candidate-manifest.json'));files=m['replacementMeshes']|{x['key']:x['mesh'] for x in m['additionalParts']};clampReport=json.loads(read(O/'camera-three-screw-clamp-report.json'));piReport=json.loads(read(O/'pi-support-report.json'));normal=np.array(m['piWorldTransform'])[:3,0]
def get(k):return load(H/files[k])
face=get('face_panel');eye=get('eye_trim');cam=get('camera_board');frame=get('camera_retainer');cameraHardware={x['id']:get(x['id']) for x in clampReport['screws']};results=[]
steps=[('camera_into_face',['camera_board'],{'face':face,'eye':eye},np.array([-30.,0,0])),('rear_clamp',['camera_retainer'],{'face':face,'eye':eye,'camera':cam},np.array([-30.,0,0])),('populated_pi',['pi','zero_w_components','zero_w_gpio_solder_tails']+[x['key'] for x in json.loads(read(O/'pi-geometry-manifest.json'))['parts'] if x['key'].startswith('gpio_') or x['key']=='zero_w_gpio_male_receiving'],{'face':face,'eye':eye,'camera':cam,'clamp':frame}|cameraHardware,-normal*30)]
for sid,moving,fixed,vector in steps:
 traces=[]
 for key in moving:
  solid=get(key)
  for fk,obs in fixed.items():
   maxv=0;bad=[]
   for i in range(121):
    q=solid.translate(vector*(1-i/120));v,bb=n['volume'](q,obs)
    if v>maxv:maxv=v
    if v>1e-5:bad.append({'sample':i,'fraction':i/120,'overlapMm3':v,'boundsMm':bb})
   traces.append({'moving':key,'fixed':fk,'sampleCount':121,'maxOverlapMm3':maxv,'failedSamples':bad})
  del solid;gc.collect()
 results.append({'id':sid,'samples':121,'spacingMm':.25,'vectorStartMm':vector.tolist(),'movingKeys':moving,'fixedKeys':list(fixed),'traces':traces})
 (O/'bench-verification-progress.json').write_text(json.dumps({'integrationReady':False,'steps':results},indent=2)+'\n')
# Actual source-derived screwdriver shaft:3mm diameter,45mm usable,18mm handle by60mm.
def cylaxis(a,d,length,r):
 d=np.asarray(d)/np.linalg.norm(d);u=np.cross(d,[0,0,1]);u/=np.linalg.norm(u);vv=np.cross(d,u);return mf.Manifold.cylinder(length,r,circular_segments=48).transform(np.column_stack([u,vv,d,a]))
tools=[]
for row in piReport['screws']:
 a=np.array(row['headSeatMm']);out=np.array(row['outwardAxis']);tool=cylaxis(a+out*1.5,out,45,1.5)+cylaxis(a+out*46.5,out,60,9)
 for fk in ['face_panel','eye_trim','camera_board','camera_retainer','pi','zero_w_components','zero_w_gpio_solder_tails']+list(cameraHardware):
  obs=get(fk);v,bb=n['volume'](tool,obs);tools.append({'screwId':row['id'],'obstacle':fk,'overlapMm3':v,'boundsMm':bb})
for row in clampReport['toolChecks']:tools.append(row)
fails=[x for s in results for x in s['traces'] if x['maxOverlapMm3']>1e-5];toolFails=[x for x in tools if x['overlapMm3']>1e-5];r={'integrationReady':False,'acceptedBenchOnly':not fails and not toolFails,'wholeAssemblyAccepted':False,'sequence':['Face and eye supported on bench; original exterior protected','Place camera on two locator pegs and four bearing lands','Add full rear clamp from-X; tighten three perimeter M2x4 TAP before Pi','Insert full populated Pi16-piece group along its board normal; tighten01/02/04, support03 passively'],'steps':results,'toolChecks':tools,'omissions':['No full FFC or GPIO loose leads included; harness installation is not accepted','No full head closure or joint-domain certification'],'sourceHashes':n['hashes']};(O/'bench-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'acceptedBenchOnly':r['acceptedBenchOnly'],'motionFailures':fails,'toolFailures':toolFails},indent=2))
