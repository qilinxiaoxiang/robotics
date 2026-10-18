"""A finite prewired output turn beside the unchanged original controller."""
from pathlib import Path
import os,json,math,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
Q=Path(__file__).resolve().parent;O=Q.parent;ns={'__file__':str(O/'check_one_pose.py')};exec((O/'check_one_pose.py').read_text().split('Tp=')[0],ns);np=ns['np'];tm=ns['tm'];mf=ns['mf'];load=ns['load'];read=ns['read'];pm=ns['pm'];ctx=ns['ctx'];sha=ns['sha']
b=read(Q/'inset05-check.json');wires={};R=2;rad=.75/math.cos(math.pi/16)+.003
for i,p in enumerate(b['terminalMouthsMm']):
 p=np.array(p);ss=[]
 for a in np.linspace(0,math.pi/2,33):ss.append((p+[0,-R*math.sin(a),-R*(1-math.cos(a))],np.array([0,-math.cos(a),-math.sin(a)])))
 ss.append((ss[-1][0]+[0,0,-2],np.array([0,0,-1])))
 vs=[]
 for c,t in ss:
  w=np.array([1.,0,0]);n=np.cross(t,w)
  for a in np.arange(16)*math.tau/16:vs.append(c+rad*(w*math.cos(a)+n*math.sin(a)))
 fs=[]
 for j in range(len(ss)-1):
  for k in range(16):a=j*16+k;z=j*16+(k+1)%16;fs += [[a,z,z+16],[a,z+16,a+16]]
 for k in range(1,15):fs += [[0,k+1,k],[(len(ss)-1)*16,(len(ss)-1)*16+k,(len(ss)-1)*16+k+1]]
 m=tm.Trimesh(vs,fs,process=True);m.fix_normals();assert m.is_watertight;s=mf.Manifold(mf.Mesh64(np.array(m.vertices),np.array(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;wires['speaker_output_'+str(i)]=s;pm.export(ctx,s,Q/f'speaker-output-{i}-downward.stl')
obs=[]
for row in b['inventory']:
 if row['id']=='current_amp':continue
 obs.append((row['id'],row['file'],row['worldTransform']))
for row in b['openrbRepresentation']:obs.append(('original_OpenRB_'+str(row['component']),row['file'],np.eye(4).tolist()))
rows=[]
for k,f,T in obs:
 ob=load(f).transform(np.array(T)[:3])
 for n,s in wires.items():
  a=np.array(s.bounding_box()).reshape(2,3);bb=np.array(ob.bounding_box()).reshape(2,3);sep=np.any(a[1]<bb[0])or np.any(bb[1]<a[0]);q=None if sep else s^ob;v=0 if sep else max(0,q.volume());rows.append({'wire':n,'obstacle':k,'volumeMm3':v,'bounds':list(q.bounding_box())if v>1e-6 else None})
 del ob;gc.collect()
r={'scope':'Two local illustrative OD1.5 R2 downward output lead turns, prewired on the bench. Not full speaker routes or manufacturer minimum bend limits. Own terminal intentional wire seating excluded.','radiusMm':R,'wireDiameterReceivingMm':1.5,'rows':rows,'hits':[x for x in rows if x['volumeMm3']>1e-6],'sourceHashes':ns['hashes']|{str(Path(__file__)):sha(__file__)}};r['clear']=not r['hits'];(Q/'terminal-exit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'clear':r['clear'],'pairs':len(rows),'hits':r['hits']},indent=2))
