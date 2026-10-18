from pathlib import Path
import os,json,hashlib,ast,types,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;NEW=D.parents[2];R=NEW.parents[1];H=R/'head-redesign-20261008';F=NEW/'power-sensor/head-controller-study/final-integration-20261009';SRC=F/'smt-header-package.json';cfg=json.loads(SRC.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
base=H/'gpio-audio-repair/check_speaker_rewire.py';node=next(n for n in ast.parse(base.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='tube');ns={'c':types.SimpleNamespace(np=np,tm=tm,mf=mf)};exec(compile(ast.Module(body=[node],type_ignores=[]),str(base),'exec'),ns);tube=ns['tube']
def load(row):
 assert sha(row['file'])==row['sha256'];m=tm.load(row['file'],force='mesh');m.apply_transform(row['worldTransform']);s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
routes=[]
for q in cfg['gpioHeaderProposal']['piPorts']:
 if q['physicalPin']not in[12,20,35,40]:continue
 p=np.array(q['wireExitWorldMm']);n=np.array(q['outwardAxis'])
 for name,v in [('up',[0,0,1]),('plusY',[0,1,0]),('minusY',[0,-1,0]),('down',[0,0,-1])]:
  v=np.array(v,float);v-=np.dot(v,n)*n;v/=np.linalg.norm(v);pts=[p+2*(np.sin(a)*n+(1-np.cos(a))*v)for a in np.linspace(0,np.pi/2,33)];pts.append(pts[-1]+v*4);routes.append({'pin':q['physicalPin'],'direction':name,'points':np.array(pts),'solid':tube(pts,.4)})
checks=[]
for row in cfg['parts']:
 ob=load(row)
 if row['key']=='current_amp':ob=ob.translate([0,1,-1.5])
 b=np.array(ob.bounding_box()).reshape(2,3)
 for route in routes:
  s=route['solid'];a=np.array(s.bounding_box()).reshape(2,3);v=0 if np.any(a[1]<b[0])or np.any(b[1]<a[0])else max(0,(s^ob).volume());
  if v>1e-6:checks.append({'pin':route['pin'],'direction':route['direction'],'part':row['key'],'volumeMm3':v,'bounds':list((s^ob).bounding_box())})
 del ob;gc.collect()
out={'sourceManifest':str(SRC),'sourceSha256':sha(SRC),'scriptSha256':sha(__file__),'receivingWireDiameterMm':.8,'illustrativeBendRadiusMm':2,'checksPerCandidate':len(cfg['parts']),'candidates':[{'pin':q['pin'],'direction':q['direction'],'centerlineMm':q['points'].tolist(),'hits':[x for x in checks if x['pin']==q['pin']and x['direction']==q['direction']]}for q in routes]};(D/'first-bends.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps([{'pin':q['pin'],'direction':q['direction'],'hits':q['hits']}for q in out['candidates']],indent=2))
