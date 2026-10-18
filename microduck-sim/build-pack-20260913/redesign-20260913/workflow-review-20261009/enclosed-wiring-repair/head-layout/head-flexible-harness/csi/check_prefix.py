from pathlib import Path
import os,json,hashlib,ast,types,gc,math
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;NEW=D.parents[2];R=NEW.parents[1];H=R/'head-redesign-20261008';F=NEW/'power-sensor/head-controller-study/final-integration-20261009';SRC=F/'smt-header-package.json';cfg=json.loads(SRC.read_text());OLD=H/'gpio-audio-repair/ffc-terminal-adjustment/dogleg-0.25.json';pr=json.loads(OLD.read_text())['primitives'];bends=[{k:np.array(v)if isinstance(v,list)else v for k,v in x.items()}for x in pr if x['kind']=='cylindrical'];last=pr[-1];p=np.array(last['p']);t=np.array(last['t']);w=np.array(last['w']);L=last['s0']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(row):
 assert sha(row['file'])==row['sha256'];m=tm.load(row['file'],force='mesh');m.apply_transform(row['worldTransform']);s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
base=H/'camera-ribbon-repair/check_spacer2_tilted_complete.py';nodes=[n for n in ast.parse(base.read_text()).body if isinstance(n,ast.FunctionDef)and n.name in['at','width','build']];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(base),'exec'))
s=build(5,75);checks=[]
for row in cfg['parts']:
 ob=load(row)
 if row['key']=='current_amp':ob=ob.translate([0,1,-1.5])
 a=np.array(s.bounding_box()).reshape(2,3);b=np.array(ob.bounding_box()).reshape(2,3);v=0 if np.any(a[1]<b[0])or np.any(b[1]<a[0])else max(0,(s^ob).volume());checks.append({'part':row['key'],'volumeMm3':v,'bounds':list((s^ob).bounding_box())if v>1e-6 else None});del ob;gc.collect()
m=s.to_mesh64();p=D/'camera-prefix-s5-75.stl';p.write_text(tm.exchange.stl.export_stl_ascii(tm.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=False)));r={'sourceManifest':str(SRC),'sourceSha256':sha(SRC),'oldRoute':str(OLD),'oldRouteSha256':sha(OLD),'scriptSha256':sha(__file__),'mesh':str(p),'meshSha256':sha(p),'materialRangeMm':[5,75],'checks':checks,'hits':[q for q in checks if q['volumeMm3']>1e-6],'wholeRibbonAccepted':False};(D/'prefix-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['hits'],indent=2))
