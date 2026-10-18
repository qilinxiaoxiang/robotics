"""Exact solid intersections, all new parts across rigid bodies, recorded final trajectory."""
from assembly_fk import *
import argparse,json,time,hashlib,itertools,mujoco,manifold3d as md
from pathlib import Path
O=Path(__file__).parent;DYN=O.parent/'dynamics';H=O.parent/'electrical/head-layout/final';C=O/'compact-battery';I=O/'trunk-imu'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--trajectory',type=Path,default=DYN/'final-batteryremove60-headremove15.json')
parser.add_argument('--output-dir',type=Path,default=O/'full-assembly')
args=parser.parse_args();OUT=args.output_dir;OUT.mkdir(parents=True,exist_ok=True)
trajpath=args.trajectory;trajbytes=trajpath.read_bytes();datajson=json.loads(trajbytes)
config=datajson['config'];geom=json.loads(Path(config['geometry_manifest']).read_text());hmanifest=json.loads((H/'head-mesh-mass-manifest.json').read_text());removed=set(geom['remove_meshes']);items=[]
def manifold(m):
 if not m.is_winding_consistent:m.fix_normals()
 M=md.Manifold(md.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
 if M.status()!=md.Error.NoError:raise ValueError('Invalid manifold '+str(M.status()))
 return M

def add(name,body,m,new,source,kind='physical'):
 # Raw STL is mm, body-local. Whole physical OpenRB source uses a verified unioned component envelope.
 M=manifold(m);bounds=m.bounds;corners=np.array(list(itertools.product(*zip(bounds[0],bounds[1]))))
 items.append(dict(name=name,body=body,mesh=m,solid=M,corners=corners,new=new,source=source,kind=kind,sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest() if Path(source).is_file() else None))
for g in fk()[1]:
 if g['mesh'] in removed:continue
 m=raw(g['mesh']).apply_transform(g['local']);add(f"retained/{g['body']}/{g['mesh']}/{g['index']}",g['body'],m,False,str(ROBOT/'assets'/f"{g['mesh']}.stl"))
for piece in hmanifest['pieces']:
 if piece['id']=='pi_retained':continue
 path=Path(piece['mesh_file']);kind='physical'
 if piece['id']=='openrb':path=H/'openrb_component_reservation_assembly.stl';kind='conservative component envelope'
 m=trimesh.load(path,force='mesh');T=np.eye(4);T[:3,:3]=piece['rotation_matrix'];T[:3,3]=piece['position_mm'];m.apply_transform(T)
 add('new/head/'+piece['id'],piece['body'],m,True,str(path),kind)
extras=['head_fastener_reference_assembly.stl','openrb_usb_plug_reservation_assembly.stl','pi_usb_data_plug_reservation_assembly.stl','pi_usb_power_plug_reservation_assembly.stl','pi_camera_connector_reservation_assembly.stl','pi_gpio_connection_reservation_assembly.stl','pi_inside_components_reservation_assembly.stl','camera_ribbon_keepout_assembly.stl']
for name in extras:
 p=H/name
 if name=='head_fastener_reference_assembly.stl' and any(x['name']=='new/head/head_fasteners' for x in items):continue
 if p.exists() and not any(Path(x['source'])==p for x in items):add('new/head/'+p.stem,'jaw_soft',trimesh.load(p,force='mesh'),True,str(p),'fastener reference' if name.startswith('head_fastener') else 'connector/component keepout')
for piece in geom['parts']:
 if piece['body']!='trunk_base':continue
 p=Path(piece['mesh']);add('new/trunk/'+p.stem,'trunk_base',trimesh.load(p,force='mesh'),True,str(p))
p=C/'two-retention-ties-envelope.stl';add('new/trunk/ties','trunk_base',trimesh.load(p,force='mesh'),True,str(p),'tie band envelope, buckle excluded')
# Same-body pairs do not change during articulation. Audit once, and retain every excluded pair explicitly.
same=[];cross=[]
for a,b in itertools.combinations(range(len(items)),2):
 x,y=items[a],items[b]
 if not (x['new'] or y['new']):continue
 if x['body']==y['body']:same.append((a,b))
 else:cross.append((a,b))
def volume(a,b):return max(0.,float((a^b).volume()))
def aabb_overlap(A,B):return bool(np.all(A[1]>=B[0]) and np.all(B[1]>=A[0]))
static_same=[]
for a,b in same:
 x,y=items[a],items[b];v=volume(x['solid'],y['solid']) if aabb_overlap(x['mesh'].bounds,y['mesh'].bounds) else 0.
 static_same.append({'a':x['name'],'b':y['name'],'body':x['body'],'intersection_mm3':v,'exclusion':'same rigid body; no relative joint motion; kept as fixed assembly/fastener/contact audit rather than repeated in sweep'})
(OUT/'same-body-exclusions.json').write_text(json.dumps(static_same,indent=2))
print('INVENTORY',len(items),'new',sum(x['new'] for x in items),'cross pairs',len(cross),'same',len(same),'same overlaps',sum(x['intersection_mm3']>.005 for x in static_same),flush=True)
M=mujoco.MjModel.from_xml_path(str(XML));D=mujoco.MjData(M);root=M.body('trunk_base').id;bodyids={x['body']:M.body(x['body']).id for x in items}
indices=np.linspace(0,len(datajson['rows'])-1,250,dtype=int);collisions=[];counter=0;booleans=0;start=time.time()
for idx,fi in enumerate(indices):
 row=datajson['rows'][int(fi)];D.qpos[:]=row['qpos'];mujoco.mj_forward(M,D);R=D.xmat[root].reshape(3,3);origin=D.xpos[root]*1000;poses={}
 for body,bi in bodyids.items():
  T=np.eye(4);T[:3,:3]=R.T@D.xmat[bi].reshape(3,3);T[:3,3]=R.T@(D.xpos[bi]*1000-origin);poses[body]=T
 bounds=[];solids={}
 for x in items:
  T=poses[x['body']];pts=x['corners']@T[:3,:3].T+T[:3,3];bounds.append(np.array([pts.min(axis=0),pts.max(axis=0)]))
 for a,b in cross:
  counter+=1
  if not aabb_overlap(bounds[a],bounds[b]):continue
  booleans+=1
  for k in [a,b]:
   if k not in solids:solids[k]=items[k]['solid'].transform(poses[items[k]['body']][:3,:4])
  v=volume(solids[a],solids[b])
  if v>.005:collisions.append({'frame':int(fi),'time':row['time'],'a':items[a]['name'],'b':items[b]['name'],'intersection_mm3':v})
 if idx%50==0:print('FRAME',idx,'hits',len(collisions),'exact booleans',booleans,flush=True)
result={'trajectory':str(trajpath),'trajectory_sha256':hashlib.sha256(trajbytes).hexdigest(),'source_frames':len(datajson['rows']),'sampled_frames':len(indices),'sample_indices':indices.tolist(),'maximum_sample_gap_s':max(np.diff([datajson['rows'][int(i)]['time'] for i in indices])),'mujoco_version':mujoco.__version__,'threshold_mm3':.005,'inventory_count':len(items),'new_parts_count':sum(x['new'] for x in items),'cross_body_pairs_per_frame':len(cross),'pair_checks':counter,'exact_boolean_checks':booleans,'cross_body_collisions':collisions,'same_body_exclusions_file':'same-body-exclusions.json','same_body_pairs':len(same),'same_body_overlaps_above_threshold':sum(x['intersection_mm3']>.005 for x in static_same),'removed_original_meshes':sorted(removed),'retained_pi':True,'elapsed_seconds':time.time()-start,'inventory':[{k:v for k,v in x.items() if k not in ['mesh','solid','corners']} for x in items],'scope':'All new physical head/camera/trunk/IMU parts and specified connector reservations versus retained other rigid bodies and other new rigid bodies. Same-body pairs audited once; no rigid-body sweep needed. Sampled trajectory, not continuous swept volumes or physical strength.'}
(OUT/'full-assembly-final-trajectory.json').write_text(json.dumps(result,indent=2));print('DONE collisions',len(collisions),'checks',counter,'wall',time.time()-start,flush=True)
