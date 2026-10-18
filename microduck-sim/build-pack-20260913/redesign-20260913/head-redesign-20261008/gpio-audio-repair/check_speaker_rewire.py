"""Guarded low-memory speaker route build and one-obstacle-at-a-time checks."""
import argparse,json,gc,os
from pathlib import Path
import bounded_amp_check as c
import bounded_amp_static as b
import precision_mesh as pm
D=Path(__file__).resolve().parent; H=D.parent; O=D/'speaker-rewire'; O.mkdir(exist_ok=True)
P=D/'speaker-rewire-amp16z2p0-proposal.json'; A=D/'cap-amp16z2'
def scene():
 idx=b.rows()
 for k in ['fullFFC','pi_csi_end','csi_free_straight_receiving']:idx.pop(k,None)
 overlay=json.loads((A/'placement-overlay.json').read_text())
 for k,f in {**overlay['replacementMeshes'],**overlay['referenceSceneOverrides']}.items():idx[k]={'key':k,'path':H/f}
 for k in overlay['removedParts']:idx.pop(k,None)
 C=H/'camera-ribbon-repair'
 idx['face_panel']={'key':'face_panel','path':C/'face-mounts124-cap-clearance-world.stl'}
 for k in list(idx):
  if k.startswith('E-pi-') or 'pi_mount_screw' in k:idx.pop(k)
 for n in ['01','02','04']:
  k='E-pi-'+n;idx[k]={'key':k,'path':C/f'E-pi-{n}-mounts124-screw-world.stl'}
 return idx

def tube(points,r):
 np=c.np; raw=np.array(points);keep=[0]
 for i in range(1,len(raw)-1):
  u=raw[i]-raw[i-1];v=raw[i+1]-raw[i]
  if np.linalg.norm(np.cross(u,v))>1e-9:keep.append(i)
 keep.append(len(raw)-1);pts=raw[keep];ts=np.diff(pts,axis=0);ts/=np.linalg.norm(ts,axis=1)[:,None]
 tangent=np.vstack([ts[0],ts[:-1]+ts[1:],ts[-1]]);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
 side=np.cross(tangent[0],[1,0,0] if abs(tangent[0,0])<.9 else [0,1,0]);side/=np.linalg.norm(side)
 verts=[];faces=[];n=16
 # Circumscribed16-gon plus0.005mm covers <=.25mm/R3 arc sag and ring rotation.
 r=(r+.005)/np.cos(np.pi/n)
 for p,t in zip(pts,tangent):
  side-=np.dot(side,t)*t;side/=np.linalg.norm(side);other=np.cross(t,side)
  for j in range(n):
   a=j*2*np.pi/n;verts.append(p+r*(np.cos(a)*side+np.sin(a)*other))
 for i in range(len(pts)-1):
  for j in range(n):
   a=i*n+j;bb=i*n+(j+1)%n;dd=a+n;cc=bb+n;faces.extend([[a,bb,cc],[a,cc,dd]])
 for j in range(1,n-1):faces.append([0,j+1,j]);a=(len(pts)-1)*n;faces.append([a,a+j,a+j+1])
 m=c.tm.Trimesh(verts,faces,process=True)
 if m.volume<0:m.invert()
 assert m.is_watertight
 s=c.mf.Manifold(c.mf.Mesh64(c.np.asarray(m.vertices,c.np.float64),c.np.asarray(m.faces,c.np.uint64)));assert s.status()==c.mf.Error.NoError
 return s

def solid(row):
 if row.get('path'):return pm.load(c,Path(row['path']))
 return c.solid({'data':json.loads(Path(row['dataFile']).read_text()),'transform':row.get('transform')})
def run(a):
 c.guarded_import();routes=json.loads(P.read_text())['routes'];route=routes[a.wire];f=O/f'speaker-wire-{a.wire}-world.stl'
 if a.mode=='build':
  s=tube(route['centerlineMm'],.75);r=pm.export(c,s,f);r.update(sourceHashes=c.fingerprint([P,Path(__file__)]),outputSha256=c.sha(f),integrationReady=False,diameterMm=1.5,radiusMm=3);c.atomic_json(f.with_suffix('.json'),r);print(json.dumps(r));return
 plan=json.loads((O/'scene-plan.json').read_text())
 for p,h in plan['inputHashes'].items():
  if c.sha(p)!=h:raise ValueError('Stale scene '+p)
 local=json.loads((b.C/'local-candidate-manifest.json').read_text());import hashlib
 projection={k:local[k] for k in ['replacementMeshes','additionalParts','removedParts']}
 if hashlib.sha256(json.dumps(projection,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=plan['localGeometrySha256']:raise ValueError('Local geometry mapping changed')
 idx=plan['rows'];target=pm.load(c,f);rows=[];inputs=[P,f,Path(__file__),O/'scene-plan.json']
 report={'mode':a.mode,'wire':a.wire,'inputHashes':c.fingerprint(inputs),'rows':rows,'complete':False,'passed':False,'integrationReady':False,'excluded':['unreleased FFC and diagnostic CSI geometry','obsolete speaker routes'],'interfaceScope':'Only local terminal mouth and actual solder pad receiving regions; no entire speaker/amp waiver.'}
 if a.key:idx={a.key:idx[a.key]}
 out=O/f'{a.mode}-{a.wire}{"-"+a.key if a.key else ""}.json'
 for k,row in idx.items():
  tb=list(target.bounding_box());rb=row['boundsMm']
  if not b.compare([tb[:3],tb[3:]],rb)['aabbOverlap']:
   rows.append({'key':k,'aabbDisjoint':True,'outsideInterfaceMm3':0,'failed':False});c.atomic_json(out,report);continue
  obstacle=solid(row);raw=target^obstacle;v=max(0,float(raw.volume()));allowed=None
  if k=='speaker':allowed=c.mf.Manifold.cube([3.4,3.4,2.6],True).translate(route['speakerPadWorldMm'])
  if k=='amplifier':allowed=c.mf.Manifold.cube([2,2.2,2.6],True).translate(route['terminalMouthWorldMm'])
  outside=max(0,float((raw-allowed).volume())) if allowed is not None else v
  rr={'key':k,'volumeMm3':v,'outsideInterfaceMm3':outside,'bounds':list(raw.bounding_box()) if v>1e-4 else None,'failed':outside>1e-4};rows.append(rr);c.atomic_json(out,report);del obstacle,raw;gc.collect()
  if rr['failed']:break
 report['complete']=len(rows)==len(idx);report['passed']=report['complete'] and not any(r['failed'] for r in rows);c.atomic_json(out,report);print(json.dumps({'file':str(out),'passed':report['passed'],'rows':len(rows),'failed':[r for r in rows if r['failed']]}));raise SystemExit(0 if report['passed'] else 2)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['build','static'],required=True);p.add_argument('--wire',type=int,choices=[0,1],required=True);p.add_argument('--key');run(p.parse_args())
