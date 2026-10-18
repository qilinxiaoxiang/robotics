from geometry import *
import json,itertools,time
records=json.loads((HERE.parent/'sources/openrb-solid-bounds.json').read_text());components=[]
for r in records:
 b=np.array(r['bounds_mm']);components.append(cub(b.mean(0),(b[1]-b[0])+1.0))
shape=manifold3d.Manifold.batch_boolean(components,manifold3d.OpType.Add)
R=np.array([[0,0,1],[1,0,0],[0,1,0]])
obs=add_pi(obstacles());res=[]
for x,y,z in itertools.product([23.5,24,24.5,25,25.5],[-1,0,1],[-23,-22,-21,-20,-19]):
 c=np.array([x,y,z]);mm=shape.transform(np.c_[R,c]);h=hits(mm,obs)
 res.append({'pcb_origin_mm':c.tolist(),'collisions':h})
valid=[r for r in res if not r['collisions']];print('valid_openrb',valid,flush=True)
(HERE/'openrb-clearance-candidates.json').write_text(json.dumps(res,indent=2)+'\n')
# Use selected manufacturer board position if possible. Expanded shape excludes PCB mount contact later.
c=np.array(valid[0]['pcb_origin_mm']) if valid else np.array([24.5,0,-22]);om=shape.transform(np.c_[R,c]);oo=obs+[('openrb_clearance',tri(om),om)]
# Speaker replaces original larger speaker at same centre and normal.
sc=[13.5,.714,13.5226];sd=[6,31,21];sm=cub(sc,sd);print('speaker',hits(sm,oo),flush=True)
oo.append(('new_speaker',box(sc,sd),sm))
res2={}
for name,d in [('amp',[12,22,21]),('imu',[8,28,25])]:
 out=[]
 for x,y,z in itertools.product(np.arange(15,30.1,2.5),np.arange(-32,32.1,4),np.arange(-45,20.1,5)):
  cc=[float(x),float(y),float(z)];lo=np.array(cc)-np.array(d)/2;hi=np.array(cc)+np.array(d)/2
  if lo[0]<-10 or hi[0]>37 or lo[1]<-43 or hi[1]>43 or lo[2]<-56 or hi[2]>32:continue
  if not hits(cub(cc,d),oo,detail=False):out.append(cc)
 res2[name]={'dims_mm':d,'candidates':out};print(name,len(out),out[:15],flush=True)
(HERE/'small-board-candidates.json').write_text(json.dumps({'openrb_pcb_origin_mm':c.tolist(),'speaker_center_mm':sc,'results':res2},indent=2)+'\n')
