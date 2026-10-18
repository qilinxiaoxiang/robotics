from assembly_fk import *
from compact_search import intersect
import json,itertools
from pathlib import Path
OUT=Path(__file__).parent
REMOVE=['np_f970','elec_rpi_robot_hat_pcb','speaker','lens','m12_lens_holder','noenoeil']
obs=[(g,raw(g['mesh']).apply_transform(g['local'])) for g in fk()[1] if g['body']=='jaw_soft' and g['mesh'] not in REMOVE]
def collisions(box):return [(g['mesh'],v) for g,m in obs if (v:=intersect(box,m))>.001]
def box(c,d):return trimesh.creation.box(d).apply_translation(c)
for name,c,d in [('pi_ports',[15.435,-.011,-62.0],[30,65,8]),('openrb',[25.5,0,-28],[21,68,27]),('reg1',[25,0,8],[11,43.2,31.8]),('speaker',[14,0,14],[6,31,21])]:print(name,c,d,collisions(box(c,d)),flush=True)
res={}
for name,d,zrange in [('openrb',[21,68,27],[-37,-34,-31,-28,-25,-22,-19]),('reg1',[11,43.2,31.8],[-20,-10,0,8,12,18]),('reg2',[9.7,22.9,22.9],[-40,-20,0,20]),('amp',[12,22,21],[-40,-20,0,20])]:
 candidates=[]
 for x,y,z in itertools.product(np.arange(20,30.1,2.5),[0,-12,12,-24,24],zrange):
  c=[x,y,z];b=box(c,d)
  # shell enclosure rough bounds; actual shell overlap checked
  if max(abs(b.bounds[:,1]))>44 or b.bounds[1,0]>40 or b.bounds[1,2]>36 or b.bounds[0,2]<-55:continue
  if not collisions(b):candidates.append(c)
 res[name]={'dims':d,'candidates':candidates};print(name,len(candidates),candidates[:8],flush=True)
OUT.joinpath('head-layout-candidates.json').write_text(json.dumps(res,indent=2))
