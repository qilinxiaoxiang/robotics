from pathlib import Path
import os,json,hashlib,ast,types,gc,math
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;NEW=D.parents[2];R=NEW.parents[1];H=R/'head-redesign-20261008';F=NEW/'power-sensor/head-controller-study/final-integration-20261009';SRC=F/'smt-header-package.json';cfg=json.loads(SRC.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
base=H/'gpio-audio-repair/check_speaker_rewire.py';node=next(n for n in ast.parse(base.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='tube');ns={'c':types.SimpleNamespace(np=np,tm=tm,mf=mf)};exec(compile(ast.Module(body=[node],type_ignores=[]),str(base),'exec'),ns);tube=ns['tube']
base2=D.parent/'speaker-lines/check.py';node=next(n for n in ast.parse(base2.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='fillet');exec(compile(ast.Module(body=[node],type_ignores=[]),str(base2),'exec'))
def load(row):
 assert sha(row['file'])==row['sha256'];m=tm.load(row['file'],force='mesh');m.apply_transform(row.get('worldTransform',np.eye(4)));s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
ports={q['physicalPin']:q for q in cfg['gpioHeaderProposal']['piPorts']};first=json.loads((D/'first-bends.json').read_text());routes=[]
for i,(pin,net,px) in enumerate([(12,'BCLK',31.07999939),(20,'GND',20.91999939),(35,'LRCLK',33.61999939),(40,'DIN',28.53999939)]):
 q=next(q for q in first['candidates']if q['pin']==pin and q['direction']=='up');pts=np.array(q['centerlineMm']);a=pts[-1];end=[px,31.257000885,134.0849994]
 z=126.5+i*.9;edge=34.5 if pin in[12,20]else-35.5
 nodes=[a,[a[0]+(z-a[2])*math.tan(math.radians(10)),a[1],z]]
 xx=nodes[-1][0];nodes += [[xx,edge,z],[57-i*.8,edge,z]]
 if pin in[12,20]:nodes += [[57-i*.8,25+i,z],[57-i*.8,25+i,141+i*.9],[px,25+i,141+i*.9],[px,31.257000885,141+i*.9],end]
 else:nodes += [[57-i*.8,-20-i,z],[57-i*.8,-20-i,145.5+(i-2)*.9],[65+(i-2)*1.1,-20-i,145.5+(i-2)*.9],[65+(i-2)*1.1,21+i,145.5+(i-2)*.9],[px,21+i,145.5+(i-2)*.9],[px,21+i,140.5+i*.2],[px,31.257000885,140.5+i*.2],end]
 # Remove the first collinear point; its first bend already supplies the upward tangent.
 tail=fillet(nodes,1.2);pts=np.vstack([pts,tail[1:]]);s=tube(pts,.4);routes.append({'pin':pin,'net':net,'points':pts,'solid':s,'end':end})
extra=json.loads((D.parent/'speaker-lines/speaker-wiring-manifest.json').read_text())['additionalParts'];m=json.loads((D.parent/'amp-mounts/amp-mount-fragment.json').read_text());extra += [q for q in m['parts']if q['key'].startswith(('amp_roof_post','amp_screw'))];pc=json.loads((D.parent/'csi/prefix-check.json').read_text());extra += [{'key':'csi_camera_prefix','file':pc['mesh'],'sha256':pc['meshSha256']}];checks=[]
for row in cfg['parts']+extra:
 ob=load(row)
 if row['key']=='current_amp':ob=ob.translate([0,1,-1.5])
 b=np.array(ob.bounding_box()).reshape(2,3)
 for route in routes:
  s=route['solid'];a=np.array(s.bounding_box()).reshape(2,3);v=0 if np.any(a[1]<b[0])or np.any(b[1]<a[0])else max(0,(s^ob).volume());outside=v
  if v and row['key']=='gpio-smt-solder-pin-'+str(route['pin']):outside=max(0,((s^ob)-mf.Manifold.cube([1.2,1.2,1.2],True).translate(route['points'][0])).volume())
  if v and row['key']=='current_amp':outside=max(0,((s^ob)-mf.Manifold.cube([1.2,1.2,2.4],True).translate(route['end'])).volume())
  if outside>1e-6:checks.append({'pin':route['pin'],'part':row['key'],'volumeMm3':v,'outsideInterfaceMm3':outside,'bounds':list((s^ob).bounding_box())})
 del ob;gc.collect()
pairs=[]
for i in range(4):
 for j in range(i):pairs.append({'pins':[routes[j]['pin'],routes[i]['pin']],'volumeMm3':max(0,(routes[j]['solid']^routes[i]['solid']).volume())})
for q in routes:
 s=q.pop('solid');pts=q.pop('points');q['centerlineMm']=pts.tolist();q['lengthMm']=float(np.linalg.norm(np.diff(pts,axis=0),axis=1).sum());m=s.to_mesh64();p=D/('i2s-'+str(q['pin'])+'.stl');p.write_text(tm.exchange.stl.export_stl_ascii(tm.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=False)));q.update(file=str(p),sha256=sha(p))
r={'sourceManifest':str(SRC),'sourceSha256':sha(SRC),'scriptSha256':sha(__file__),'routes':routes,'expectedObstacleCount':len(cfg['parts']+extra),'hits':checks,'wirePairs':pairs,'wholeHeadAccepted':False};(D/'complete-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'hits':checks,'pairs':pairs},indent=2))
