from pathlib import Path
D=Path(__file__).resolve().parent;OLD=D.parent/'full-harness';ns={'__file__':str(OLD/'build_harness.py')};exec((OLD/'build_harness.py').read_text().split('# PUBLISHED_CONNECTOR_FROM_SOURCE_SHOULDER')[0],ns)
globals().update({k:v for k,v in ns.items() if not k.startswith('__')});D=OLD.parent/'usb-repair'
SIM=H.parent.parents[1];sys.path.insert(0,str(SIM/'hardware-design-20260912/whole-robot-20260912/assembly'));from assembly_fk import fk
B,_=fk();bodymap={p['key']:p.get('body','jaw_soft') for p in data['parts']};native=man(load(C/'community-curved-head-world.stl'))
for q,p,k in [({'head_roll':-20},'head_cap','motor13'),({'head_roll':-20},'head_cap','head_yaw_link'),({'head_yaw':90,'head_roll':20},'head_bottom','neck_pitch')]:
 posed,_=fk({k:np.deg2rad(v) for k,v in q.items()});Ta=posed['jaw_soft']@np.linalg.inv(B['jaw_soft']);b=bodymap[k];Tb=posed[b]@np.linalg.inv(B[b]);ob=obs[k].transform((np.linalg.inv(Ta)@Tb)[:3]);hit=obs[p]^ob
 print(json.dumps({'q':q,'parts':[p,k],'volume':hit.volume(),'bounds':hit.bounding_box(),'nativeCapIntersection':hits(native,ob) if p=='head_cap' else None}),flush=True)
