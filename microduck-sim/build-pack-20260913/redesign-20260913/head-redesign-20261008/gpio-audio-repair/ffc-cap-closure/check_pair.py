"""One moving solid, one fixed accepted complete FFC, all161 translations."""
from pathlib import Path
import argparse,json,os,gc,sys
from contracts import sha,load_contract
p=argparse.ArgumentParser();p.add_argument('--inventory',type=Path,required=True);p.add_argument('--contract',type=Path,required=True);p.add_argument('--key',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1','Run through resource guard'
inv=json.loads(a.inventory.read_text());contract=load_contract(a.contract);offsets=inv['offsetsZMm'];assert offsets==[40-i*.25 for i in range(161)]
for f,h in inv['sourceHashes'].items():assert sha(f)==h,('stale inventory',f)
sourceHashes={str(a.inventory):sha(a.inventory),str(a.contract):sha(a.contract),str(Path(__file__)):sha(__file__),str(Path(__file__).with_name('contracts.py')):sha(Path(__file__).with_name('contracts.py')),contract['mesh']:contract['meshSha256']}
import numpy as np,trimesh as tm,manifold3d as mf

def load(path):
 m=tm.load(path,force='mesh');assert m.is_watertight and m.is_winding_consistent and m.volume>0,('invalid closed input',str(path))
 s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError and s.volume()>0,(str(path),str(s.status()))
 return s,{'watertight':True,'windingConsistent':True,'positiveVolumeMm3':float(s.volume()),'triangles':len(m.faces),'boundsMm':np.asarray(s.bounding_box()).reshape(2,3).tolist()}
ffc,ffcGeo=load(contract['mesh']);row=None;rows=[];result={'schemaVersion':1,'candidateOnly':contract.get('mode') in ('diagnostic','local-geometric-candidate'),'wholeHarnessAccepted':False,'key':a.key,'complete':False,'passed':False,'scope':'New fixed full FFC obstacle only','sourceHashes':sourceHashes,'ffcGeometry':ffcGeo,'rows':rows}
a.output.parent.mkdir(parents=True,exist_ok=True)
def save():
 temp=a.output.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2)+'\n');temp.replace(a.output)
if a.key=='validate-ffc':
 result.update(complete=True,passed=True);save();print(json.dumps({'key':a.key,'passed':True}));sys.exit(0)
row=next(r for r in inv['movingEntities']if r['key']==a.key);source=Path(row['path']);assert sha(source)==row['sha256'];sourceHashes[str(source)]=row['sha256'];result.update(group=row['group'],representation=row['representation']);moving,geo=load(source);result['movingGeometry']=geo
bb=np.array(ffcGeo['boundsMm']);ab0=np.array(geo['boundsMm']);eps=1e-7
for n,z in enumerate(offsets):
 ab=ab0+[0,0,z];separated=bool(np.any(ab[0]>=bb[1]) or np.any(bb[0]>=ab[1]));volume=0.
 if not separated:
  posed=moving.translate([0,0,z]);inter=posed^ffc;assert inter.status()==mf.Error.NoError;volume=max(0.,float(inter.volume()));del inter,posed
 rows.append({'index':n,'offsetWorldMm':[0,0,z],'aabbSeparated':separated,'intersectionVolumeMm3':volume,'clearWithinNumericalTolerance':volume<=eps})
 if n%8==0 or volume>eps:save()
 # No transformed-scene caching: one posed moving mesh/intersection at a time.
 if n%16==0:gc.collect()
peak=max(rows,key=lambda r:r['intersectionVolumeMm3']);result.update(complete=len(rows)==161,passed=all(r['clearWithinNumericalTolerance']for r in rows),sampleCount=161,peak=peak,numericalToleranceMm3=eps,contactAllowances=[],sampledPathBoundary='161 exact poses at.25mm; does not independently prove unsampled continuous clearance or strength.')
save();print(json.dumps({'key':a.key,'passed':result['passed'],'peak':peak}));sys.exit(0 if result['passed']else 2)
