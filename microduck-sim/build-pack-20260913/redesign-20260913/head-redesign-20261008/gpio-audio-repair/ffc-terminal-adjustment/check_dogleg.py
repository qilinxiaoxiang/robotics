from pathlib import Path
import json,os,hashlib,gc,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
A=Path(__file__).resolve().parent;H=A.parents[1];C=H/'camera-ribbon-repair';sys.path.insert(0,str(C));src=C/'check_spacer2_tilted_complete.py';ns={'__file__':str(src),'__name__':'independent'};exec(compile(src.read_text().split('keys=sorted(')[0],str(src),'exec'),ns)
np=ns['np'];mf=ns['mf'];tm=ns['tm'];read=ns['read'];load=ns['load'];n=ns['n'];files=ns['files'];removed=ns['removed'];delta=ns['delta'];shiftKeys=ns['shiftKeys'];fit=json.loads(read(A/'dogleg-0.25.json'));assert fit['maxConstraintResidual']<1e-6
pr=[{k:np.array(v)if isinstance(v,list)else v for k,v in row.items()}for row in fit['primitives']];ns['bends']=[r for r in pr if r['kind']=='cylindrical'];last=pr[-1];ns['p']=last['p']+last['t']*(last['s1']-last['s0']);ns['t']=last['t'];ns['w']=last['w'];ns['L']=fit['materialLengthMm'];build=ns['build'];solid=build(75,195.6)
def save():
 r['sourceHashes']=n['hashes'];(A/'dogleg-0.25-check.json').write_text(json.dumps(r,indent=2)+'\n')
r={'accepted':False,'complete':False,'materialLengthMm':fit['materialLengthMm'],'fullWidthFlatMm':fit['fullWidthFlatMm'],'changedMaterialScopeMm':[75,200],'static':[],'self':[],'expectedSelfPairs':0,'completedSelfPairs':0}
occfile=H/'cabling-release-20261008/neck-repair/pi-local-components/local-occupancy.json';occ=json.loads(read(occfile));T=np.array(json.loads(read(C/'fixed-pose-local-bend/pi-spacer2-pose.json'))['worldTransform']);B=np.array([[0,0,-1,8.1],[0,1,0,0],[1,0,0,115.6146],[0,0,0,1]],float);Cmat=np.array([[0,1,0,.435],[1,0,0,-32.511],[0,0,1,-59.21],[0,0,0,1]],float);M=T@B@Cmat;xy=np.array(occ['localReplacementWindowOfficialXYMm']);window=mf.Manifold.cube([*(xy[1]-xy[0]),10]).translate([*xy[0],-1]).transform(M[:3]);old=load(H/files['zero_w_components']).translate(delta);remaining=old-window
r['static'].append({'key':'components-outside-window','overlapMm3':n['volume'](solid,remaining)[0]})
for row in occ['rows']:
 ob=mf.CrossSection([row['footprintOfficialXYMm']]).offset(row['xyExpansionMm'],mf.JoinType.Round).extrude(row['heightAbovePcbMm']).transform(M[:3])^window;r['static'].append({'key':row['key'],'overlapMm3':n['volume'](solid,ob)[0]});del ob
for key in sorted((set(n['P'])|set(files))-removed-{'zero_w_components','openrb'}):
 ob=load(H/files[key])if key in files else n['source'](key)
 if key in shiftKeys:ob=ob.translate(delta)
 r['static'].append({'key':key,'overlapMm3':n['volume'](solid,ob)[0]});del ob;gc.collect();save()
# AllOpenRB142 components accounted; no shrinking or dropping nonadjacent cable segments.
em=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));bb=np.array(solid.bounding_box()).reshape(2,3)
for row in em['components']:
 b=np.array(row['bounds']);v=0
 if np.all(bb[1]>=b[0])and np.all(b[1]>=bb[0]):ob=load(Path(row['mesh']));v=n['volume'](solid,ob)[0];del ob
 r['static'].append({'key':'openrb-'+str(row['index']),'overlapMm3':v})
del solid,old,remaining;gc.collect();chunks=[]
for a in np.arange(0,200,2):
 s=build(a,min(a+2,200));chunks.append((a,s,np.array(s.bounding_box()).reshape(2,3)))
for i,(a,s,bb) in enumerate(chunks):
 for j in range(i+2,len(chunks)):
  b,z,zb=chunks[j]
  if b+2<=75:continue
  r['expectedSelfPairs']+=1
  if np.all(bb[1]>=zb[0])and np.all(zb[1]>=bb[0]):
   v,ib=n['volume'](s,z)
   if v>1e-6:r['self'].append({'s1':float(a),'s2':float(b),'overlapMm3':v})
  r['completedSelfPairs']+=1
 save()
n['hashes'][str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
r['wholeHarnessAccepted']=False;r['printingUnlocked']=False;r['complete']=True;r['staticClear']=all(x['overlapMm3']<1e-6 for x in r['static']);r['selfClear']=not r['self'];r['localGeometricCandidatePassed']=r['staticClear']and r['selfClear'];r['accepted']=False;r['note']='Finite twoamplitude family. Only0.25 satisfies endpoint/200mm constraints. Does not prove allflexible routes impossible iffailed; no printgeometrychanges.';save();print(json.dumps({k:v for k,v in r.items()if k not in ['static','sourceHashes','self']}));print('collisions',[x for x in r['static']if x['overlapMm3']>1e-6]);print('self',r['self'])

if r['localGeometricCandidatePassed']:
 full=build(0,200);m=full.to_mesh64();out=A/'dogleg-0.25-full200-world.stl'
 with out.open('w')as f:
  f.write('solid ribbon\n')
  for tri in m.tri_verts:
   f.write('facet normal 0 0 0\nouter loop\n')
   for i in tri:f.write('vertex '+' '.join(format(float(v),'.17g')for v in m.vert_properties[i,:3])+'\n')
   f.write('endloop\nendfacet\n')
  f.write('endsolid ribbon\n')
 readback=tm.load(out,force='mesh');assert readback.is_watertight and readback.is_winding_consistent and readback.volume>0
 r['fullMesh']=str(out);r['fullMeshSha256']=hashlib.sha256(out.read_bytes()).hexdigest();r['fullMeshTopology']={'watertight':True,'windingConsistent':True,'volumeMm3':float(readback.volume),'triangles':len(readback.faces)};r['numericalBoundaries']={'assumedInsertionMm':4.4,'fullWidthOutsideStraightMm':fit['fullWidthFlatMm']-4.4,'minimumBendRadiusMm':1,'materialThicknessMm':.3,'receivingAssumptionsNotManufacturerMinima':True};save();print('fullmesh',r['fullMeshSha256'])
