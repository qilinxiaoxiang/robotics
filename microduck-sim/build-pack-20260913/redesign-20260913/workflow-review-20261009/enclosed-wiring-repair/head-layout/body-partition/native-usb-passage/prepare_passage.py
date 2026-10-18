import pathlib,json,hashlib,struct,math
S=pathlib.Path('/Users/xiangzheng/code/robotics/microduck-sim');R=S/'build-pack-20260913/redesign-20260913';W=R/'workflow-review-20261009';D=W/'enclosed-wiring-repair/head-layout/body-partition/native-usb-passage';sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest();man=json.loads((W/'original-body-converter/fusion-import-manifest.json').read_text());rows={q['key']:q for q in man['parts']};g=json.loads((R/'leg-guide-20261006/full-build-data.json').read_text());gp={q['key']:q for q in g['parts']}
def tris(p):
 with open(p,'rb')as f:
  f.seek(80);n=struct.unpack('<I',f.read(4))[0]
  if pathlib.Path(p).stat().st_size==84+50*n:
   for _ in range(n):
    a=struct.unpack('<12fH',f.read(50));yield [a[3:6],a[6:9],a[9:12]]
  else:
   f.seek(0);t=[]
   for l in f:
    a=l.split()
    if a[:1]==[b'vertex']:
     t.append(list(map(float,a[1:4])))
     if len(t)==3:yield t;t=[]
def clip(poly,axis,lim,sign):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ia=sign*(a[axis]-lim)>=-1e-9;ib=sign*(b[axis]-lim)>=-1e-9
  if ia:out.append(a)
  if ia!=ib:
   t=(lim-a[axis])/(b[axis]-a[axis]);out.append([a[k]+t*(b[k]-a[k])for k in range(3)])
 return out
def roofcheck(file,rect):
 polys=[];total=0;minz=1e9
 for vs in tris(file):
  nx=(vs[1][0]-vs[0][0])*(vs[2][1]-vs[0][1])-(vs[1][1]-vs[0][1])*(vs[2][0]-vs[0][0])
  if nx<=1e-12 or min(v[2]for v in vs)<35:continue
  p=vs
  for ax,lim,sgn in [(0,rect[0],1),(0,rect[2],-1),(1,rect[1],1),(1,rect[3],-1)]:
   p=clip(p,ax,lim,sgn)
   if not p:break
  if len(p)<3:continue
  area=abs(sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(p,p[1:]+p[:1])))/2
  if area>1e-10:total+=area;minz=min(minz,min(v[2]for v in p));polys.append(p)
 return {'rectMm':rect,'roofProjectedAreaMm2':total,'rectAreaMm2':(rect[2]-rect[0])*(rect[3]-rect[1]),'minimumUpperRoofZMm':minz,'sourceUpwardRoofTrianglesOnly':True,'note':'Source facet projection proves candidate rails below sampled clipped original top-roof facets; native connectivity and other-part interference separately required.'}
shells=[]
for k in ['shell_left','shell_right']:
 row=rows[k];assert row['importTranslationMm']==[0,0,0]
 ys=[0,9]if k=='shell_left'else[-9,-2]
 rects=[[-32.77,ys[0],-30.77,ys[1]],[-30.77,7,-21.8,9]if k=='shell_left'else[-30.77,-9,-21.8,-7]]
 rails=[]
 for rect in rects:
  rc=roofcheck(row['file'],rect)
  rc.update(originMm=[rect[0],rect[1],37],sizeMm=[rect[2]-rect[0],rect[3]-rect[1],2.5]);rc['eligibleRoofEnvelope']=abs(rc['roofProjectedAreaMm2']-rc['rectAreaMm2'])<.001 and rc['minimumUpperRoofZMm']>=39.7
  rails.append(rc)
 shells.append({'key':k,'file':row['file'],'sha256':sha(row['file']),'worldCoordinatesAlreadyApplied':True,'importTranslationMm':[0,0,0],'originalCommunitySourceId':gp[k]['sourceId'],'originalCommunitySourceName':gp[k]['sourceName'],'originalSourceToWorld':gp[k]['sourceTransformWorld'],'rails':rails})
b=json.loads((D.parent/'shift-minus05-exact.json').read_text());pr=json.loads((D.parent/'report.json').read_text());refs=[{'key':q['key'],'file':q['file'],'sha256':q['sha256'],'worldTranslationMm':[-.5,0,0]}for q in pr['meshes']if q['key'].startswith('USB_C_')]
step=S/'hardware-design-20260912/whole-robot-20260912/electrical/sources/openrb-official.step'
out={'schemaVersion':1,'status':'PREPARED_FOR_FUSION_NOT_EXECUTED','units':'mm','shells':shells,'opening':{'kind':'U_NOTCH_CONNECTED_TO_EXISTING_OPENING','xRearMm':-30.77,'xFrontMm':-19.8,'yMinMm':-7,'yMaxMm':7,'rearCornerRadiusMm':2,'zStartMm':37,'zEndMm':44,'flatSideNominalClearanceMm':1,'conservativeRectangularPlugCornerClearanceMm':2-math.sqrt(2),'note':'Enlarge existing upper opening with rear-R2 U-notch, remove0.89–1.02mm thin bridge rather than create adjacent isolated hole. No exterior bulge/body widening.'},'openrbReference':{'file':str(step),'sha256':sha(step),'nativeToWorld':b['nativeOpenRBToWorld']},'plugReferences':refs,'fastenerProximityReceipt':str(D.parent/'corridor-fastener-proximity.json'),'sourceHashes':{str(p):sha(p)for p in [D.parent/'shift-minus05-exact.json',D.parent/'corridor-fastener-proximity.json',W/'original-body-converter/fusion-import-manifest.json']},'reinforcementPolicy':'Attempt rear and side2mm inner rails per half only when upper-roof envelope gate and native body/plug clearance and native attachment pass; otherwise leave cut unreinforced and state why. No rail bridges the shell seam. No FEA or physical strength claim.'}
(D/'passage-spec.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps([(q['key'],q['rails'])for q in shells],indent=2))
