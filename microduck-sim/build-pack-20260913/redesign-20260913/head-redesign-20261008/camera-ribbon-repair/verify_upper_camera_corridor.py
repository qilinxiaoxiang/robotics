from pathlib import Path
import ast
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(Path(__file__))
from scipy.optimize import root
import developable_x225_dogleg as dr
trimesh=tm
exec((D/'fit_upper_camera_corridor.py').read_text().split('lo=[')[0]);read(D/'fit_upper_camera_corridor.py');O=D/'camera-quarter-rolls/90';fitrows=json.loads(read(O/'upper-corridor-fits.json'))['candidates'];pr=json.loads(read(D/'positive-x225/pi-geometry-manifest.json'))
for a in ast.parse((D/'optimize_x225_u80.py').read_text()).body:
 if isinstance(a,ast.FunctionDef) and a.name=='construct':exec(compile(ast.Module(body=[a],type_ignores=[]),'<mesh>','exec'))
read(D/'optimize_x225_u80.py')
for row in fitrows:
 desired=row['lengthMm'];x=np.array(row['parameters'])
 p,t,w,L,bends,ops=dr.family(x);solid=construct(4.4,L,.3,x,16);name='upper_corridor_'+str(round(desired));path=export(solid,name);checks=[]
 obstacles=[('native_cap',H/'curved-head/community-curved-head-world.stl'),('camera',D/'camera-quarter-rolls/90/camera-world.stl'),('amp',H/'gpio-audio-repair/amp16z2-closed-receiving-world.stl'),('face',D/'positive-x225/face_three_screw_camera-world.stl')]+[(r['key'],H/r['mesh']) for r in pr['parts'] if True]
 for k in ['motor13','motor14','motor15','jaw_support','jaw_frame','head_yaw_link','speaker','head_bottom','upper_pad','lower_pad']:
  if k in n['P'] or k in n['files']:obstacles.append((k,None))
 rb=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));obstacles += [('OpenRB_'+str(r['index']),Path(r['mesh'])) for r in rb['components']]
 for k,path2 in obstacles:
  o=load(path2) if path2 else n['source'](k)
  if k=='camera':o-=mf.Manifold.cube([.6,16,5],True).translate([75.63,-.0913766914184464,138.07659913253173])
  v,bb=n['volume'](solid,o);checks.append({'obstacle':k,'overlapMm3':v,'boundsMm':bb,'gapCapped2':float(solid.min_gap(o,2))});del o
 slabs=[construct(a,min(a+2,L),.5,x,16) for a in np.arange(4.4,L,2)];selfhits=[]
 for i,a in enumerate(slabs):
  for j in range(i+2,len(slabs)):
   v,bb=n['volume'](a,slabs[j])
   if v>1e-5:selfhits.append({'slabs':[i,j],'overlapMm3':v})
 del slabs;gc.collect();r={'integrationReady':False,'targetLength':desired,'materialLengthMm':float(L),'radii':[3]*len(bends),'width':16,'parameters':x.tolist(),'endpointErrorMm':float(np.linalg.norm(p-dr.target)),'tangent':t.tolist(),'widthAxis':w.tolist(),'mesh':path,'boundsMm':list(solid.bounding_box()),'checks':checks,'selfHits':selfhits,'expectedObstacles':len(obstacles),'completedObstacles':len(checks),'sourceHashes':n['hashes'],'miniInserted4p4NotYetExported':True,'contactNormalStart':np.cross(dr.initial[1],dr.initial[2]).tolist(),'contactNormalEnd':np.cross(t,w).tolist()};(O/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'name':name,'length':L,'radii':r['radii'],'parameters':x.tolist(),'hits':[(a['obstacle'],a['overlapMm3']) for a in checks if a['overlapMm3']>1e-5],'selfHits':selfhits,'bounds':r['boundsMm']},indent=2),flush=True)
