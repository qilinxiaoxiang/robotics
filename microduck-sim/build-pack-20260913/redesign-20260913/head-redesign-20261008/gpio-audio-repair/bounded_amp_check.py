#!/usr/bin/env python3
"""One amplifier candidate, one obstacle and one pose at a time.

--describe and --self-test use only the Python standard library. Geometry work
requires the parent-owned run_bounded_cad.py token. No scene/transform cache.
"""
import argparse,base64,gc,hashlib,json,os,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent;C=H/'cabling-release-20261008';G=H.parent/'leg-guide-20261006'
SOURCE=G/'full-build-data.json';CONFIG=H/'viewer-candidate.json';DOMAIN=H/'usb-access/usb-repair/rigid-domain.json'
OVERRIDES={'head_cap':C/'cap-neck-slot-closure-candidate-world.stl','amplifier':D/'amplifier-terminal-receiving-world.stl','curved_cap_hardware':C/'hardware-audio-rotation-candidate-world.stl','speaker_keeper':C/'speaker-keeper-wire-relief-candidate-world.stl','speaker_wire_0':D/'speaker-wire-0-world.stl','speaker_wire_1':D/'speaker-wire-1-world.stl','zero_w_components':H/'curved-head/zero_w_components-world.stl','zero_w_gpio_solder_tails':H/'curved-head/zero_w_gpio_solder_tails-world.stl'}

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def atomic_json(p,x):
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,indent=2)+'\n');os.replace(tmp,p)
def fingerprint(paths):return {str(p.resolve()):sha(p) for p in sorted(set(map(Path,paths)))}
def scene_index(data,config):
 # Metadata only. World STLs need no source transform; explicit config
 # transforms still apply to baseline replacements exactly as in the viewer.
 rows={}
 for p in data['parts']:
  k=p['key']
  if k in config['removedParts'] or k=='zero_w_populated_receiving':continue
  rows[k]={'key':k,'body':p.get('body','jaw_soft'),'data':p,'path':H/config['replacementMeshes'][k] if k in config['replacementMeshes'] else None,'transform':config.get('transforms',{}).get(k)}
 for p in config['additionalParts']:
  if p['key']=='zero_w_populated_receiving':continue
  rows[p['key']]={'key':p['key'],'body':p.get('body','jaw_soft'),'path':H/p['mesh'],'transform':None}
 for k,p in OVERRIDES.items():rows[k]={'key':k,'body':rows.get(k,{}).get('body','jaw_soft'),'path':p,'transform':None}
 return rows

def guarded_import():
 if os.environ.get('MICRODUCK_BOUNDED_CAD')!='1':raise SystemExit('CAD refused: parent must launch through H/run_bounded_cad.py; no direct run.')
 # These are intentionally absent from --describe/--self-test.
 global np,tm,mf
 import numpy as np
 import trimesh as tm
 import manifold3d as mf

def solid(row):
 if row.get('path'):m=tm.load(row['path'],file_type='stl',force='mesh')
 else:
  p=row['data'];m=tm.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
 if row.get('transform') is not None:m.apply_transform(row['transform'])
 s=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
 if s.status()!=mf.Error.NoError:raise ValueError('Invalid manifold '+row.get('key','mesh'))
 del m;return s

def volume_pair(a,b):
 aa=np.array(a.bounding_box()).reshape(2,3);bb=np.array(b.bounding_box()).reshape(2,3)
 if np.any(aa[0]>=bb[1]) or np.any(bb[0]>=aa[1]):return 0.,None
 intersection=a^b;v=max(0.,float(intersection.volume()))
 bounds=list(intersection.bounding_box()) if v>1e-4 else None
 del intersection;return v,bounds

def export(s,p):
 q=s.to_mesh();m=tm.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True)
 if not m.is_watertight:raise ValueError('Output is not watertight: '+str(p))
 m.export(p);del m,q

def prepare(delta):
 guarded_import()
 # Only four solids are live. The cap is reconstructed from its actual native
 # curved skin; original skin is not cut when retiring the two old amp pillars.
 files=[Path(__file__),OVERRIDES['head_cap'],OVERRIDES['amplifier'],OVERRIDES['curved_cap_hardware'],H/'curved-head/community-curved-head-world.stl',C/'audio-route-candidate.json']
 bindings=fingerprint(files);progress=D/'amp-preparation.json'
 report={'candidateDeltaMm':delta,'inputHashes':bindings,'prepared':False,'completedSteps':[],'integrationReady':False}
 atomic_json(progress,report)
 native=solid({'path':files[4]});cap=solid({'path':OVERRIDES['head_cap']});audio=json.loads((C/'audio-route-candidate.json').read_text());old=np.array(audio['newAmpHoleBottomMm']);new=old+np.array(delta)
 for i,p in enumerate(old):
  column=mf.Manifold.cylinder(30,2.01,circular_segments=48).translate(p)
  cap=(cap-(column-native)).as_original();del column
  report['completedSteps'].append('retired-old-pillar-'+str(i));atomic_json(progress,report);gc.collect()
 # Material is bounded by the exact local native roof patch swept downward.
 # Fold one translated patch at a time; never cache 30 transformed meshes.
 posts=None
 for i,p in enumerate(new):
  near=native^mf.Manifold.cube([4.02,4.02,60],True).translate([p[0],p[1],140]);filled=near
  for z in range(1,31):
   shifted=near.translate([0,0,-z]);filled=(filled+shifted).as_original();del shifted;gc.collect()
  raw=mf.Manifold.cylinder(30,2,circular_segments=48).translate(p)
  bore=mf.Manifold.cylinder(7.2,1.05,circular_segments=48).translate(p-[0,0,.1])
  post=((raw^filled)-bore).as_original();del raw,bore,near,filled
  posts=post if posts is None else (posts+post).as_original();cap=(cap+post).as_original()
  report['completedSteps'].append('created-new-pillar-'+str(i));atomic_json(progress,report);gc.collect()
 export(posts,D/'amp-relocated-posts-world.stl');export(cap,D/'cap-relocated-amp-world.stl');del posts,cap,native;gc.collect()
 amp=solid({'path':OVERRIDES['amplifier']}).translate(delta);export(amp,D/'amp-relocated-world.stl');del amp;gc.collect()
 hardware=solid({'path':OVERRIDES['curved_cap_hardware']});new_screws=None
 for a,b in zip(old,new):
  # Exact old modeled amp screw body, not a broad cube that could erase
  # neighboring OpenRB or speaker hardware.
  old_screw=mf.Manifold.cylinder(8,1.25,circular_segments=48).translate(a-[0,0,1.57])+mf.Manifold.cylinder(1.7,2.5,circular_segments=48).translate(a-[0,0,3.27])
  hardware=(hardware-old_screw).as_original()
  new_screw=old_screw.translate(delta);new_screws=new_screw if new_screws is None else (new_screws+new_screw).as_original();del old_screw,new_screw
 hardware=(hardware+new_screws).as_original();export(hardware,D/'hardware-relocated-amp-world.stl');export(new_screws,D/'amp-relocated-screws-world.stl');del hardware,new_screws;gc.collect()
 outputs=['amp-relocated-posts-world.stl','cap-relocated-amp-world.stl','amp-relocated-world.stl','hardware-relocated-amp-world.stl','amp-relocated-screws-world.stl']
 report.update(prepared=True,newMountAxesMm=new.tolist(),outputHashes={f:sha(D/f) for f in outputs},threadGeometry={'spec':'M2.5 x8 TAP','quantity':2,'shaftRadiusMm':1.25,'headRadiusMm':2.5,'headHeightMm':1.7,'boreRadiusMm':1.05,'boreDepthMm':7.2},adoptionBoundary='Preparation is not placement/path/wiring/retention acceptance. Existing speaker wires must be rerouted to relocated terminals before prewired group verification.')
 atomic_json(progress,report);print(json.dumps({'prepared':True,'candidateDeltaMm':delta}),flush=True)

def job_pairs(phase,keys,cases):
 # Obstacle-major order reuses one base mesh, never transformed scene lists.
 for k in keys:
  for i,q in enumerate(cases if phase=='domain' else [{}]):yield k,i,q

def verify(args):
 guarded_import()
 data=json.loads(SOURCE.read_text());config=json.loads(CONFIG.read_text());index=scene_index(data,config)
 if args.placement_only:
  if args.target!='amplifier' or args.phase!='domain':raise ValueError('Placement-only is amplifier/domain only')
  prep={'candidateDeltaMm':args.delta,'prepared':False}
  target_file=OVERRIDES['amplifier'];target=solid({'path':target_file}).translate(args.delta)
 else:
  prep=json.loads((D/'amp-preparation.json').read_text())
  if not prep.get('prepared'):raise ValueError('Candidate preparation incomplete')
  for f,h in prep['inputHashes'].items():
   if sha(Path(f))!=h:raise ValueError('Stale preparation input: '+f)
  for f,h in prep['outputHashes'].items():
   if sha(D/f)!=h:raise ValueError('Changed candidate output: '+f)
  mapping={'amplifier':'amp-relocated-world.stl','posts':'amp-relocated-posts-world.stl','screws':'amp-relocated-screws-world.stl','cap':'cap-relocated-amp-world.stl'}
  target_file=D/mapping[args.target];target=solid({'path':target_file})
 # New geometry is tested with its actual companion parts at the same pose.
 if not args.placement_only:
  index['amplifier']={'key':'amplifier','path':D/'amp-relocated-world.stl','body':'jaw_soft'}
  index['head_cap']={'key':'head_cap','path':D/'cap-relocated-amp-world.stl','body':'jaw_soft'}
  index['curved_cap_hardware']={'key':'curved_cap_hardware','path':D/'hardware-relocated-amp-world.stl','body':'jaw_soft'}
 # Existing wire routes end at the old amplifier and are deliberately not
 # silently moved. Static placement phase excludes them and retains this gate.
 omit={'speaker_wire_0','speaker_wire_1'}
 self_keys={'amplifier':{'amplifier'},'posts':{'head_cap'},'cap':{'head_cap'},'screws':{'curved_cap_hardware','head_cap','amplifier'}}[args.target]
 keys=sorted(k for k in index if k not in omit|self_keys)
 SIM=H.parent.parents[1];fkpath=SIM/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py';sys.path.insert(0,str(fkpath.parent));from assembly_fk import fk
 B,_=fk();inv={k:np.linalg.inv(v) for k,v in B.items()}
 unknown={k:r['body'] for k,r in index.items() if r['body'] not in B}
 for k in unknown:index[k]['body']='trunk_base'
 if args.phase=='domain':keys=[k for k in keys if index[k]['body'] in B and index[k]['body']!='jaw_soft']
 if args.only_obstacle:
  if args.only_obstacle not in keys:raise ValueError('Obstacle unavailable in requested scope')
  keys=[args.only_obstacle]
 domain=json.loads(DOMAIN.read_text());cases=[r['jointDegrees'] for r in domain['samples']]
 inputs=[Path(__file__),SOURCE,CONFIG,DOMAIN,fkpath,target_file]
 if not args.placement_only:inputs.append(D/'amp-preparation.json')
 inputs.extend(index[k]['path'] for k in keys if index[k].get('path'))
 bindings=fingerprint(inputs);name=args.name or (('placement-' if args.placement_only else '')+args.target+'-'+args.phase+('-'+args.only_obstacle if args.only_obstacle else ''))
 if not name.replace('-','').replace('_','').isalnum():raise ValueError('Unsafe job name')
 state_path=D/(name+'-checkpoint.json');trace_path=D/(name+'-pairs.jsonl')
 total=len(keys)*(len(cases) if args.phase=='domain' else 1)
 expected={'unmatchedBodiesAssignedTrunkBase':unknown,'placementOnly':args.placement_only,'target':args.target,'phase':args.phase,'keys':keys,'candidateDeltaMm':prep['candidateDeltaMm'],'inputHashes':bindings}
 if state_path.exists():
  state=json.loads(state_path.read_text())
  if state['job']!=expected:raise ValueError('Refuse stale resume; use a new job name')
 else:
  state={'job':expected,'complete':False,'passed':False,'nextPair':0,'totalPairs':total,'failedPairs':0,'peakContactsMm3':{},'nativeClearFailedPairs':0,'omittedOldWireRoutes':sorted(omit),'integrationReady':False}
  if trace_path.exists():raise ValueError('Orphan trace needs explicit review, not silent overwrite')
  atomic_json(state_path,state)
 if state['complete']:print(json.dumps(state),flush=True);return 0 if state['passed'] else 2
 # After guard termination, an appended trace line may predate its atomic
 # checkpoint commit. Keep exactly the committed prefix before resuming.
 if trace_path.exists():
  with trace_path.open('r+b') as f:
   for i in range(state['nextPair']):
    line=f.readline()
    if not line or json.loads(line)['pair']!=i:raise ValueError('Checkpoint trace prefix missing or out of order')
   f.truncate(f.tell())
 elif state['nextPair']:raise ValueError('Checkpoint trace is missing')
 last=None;obstacle=None;tested=0;start=time.monotonic()
 with trace_path.open('a') as trace:
  for cursor,(key,pose_index,q) in enumerate(job_pairs(args.phase,keys,cases)):
   if cursor<state['nextPair']:continue
   if tested>=args.max_pairs:break
   if key!=last:
    if obstacle is not None:del obstacle;gc.collect()
    obstacle=solid(index[key]);last=key
   if args.phase=='domain':
    poses,_=fk({k:np.deg2rad(v) for k,v in q.items()});Th=poses['jaw_soft']@inv['jaw_soft'];relative=np.linalg.inv(Th)@poses[index[key]['body']]@inv[index[key]['body']];moved=obstacle.transform(relative[:3])
   else:moved=obstacle
   volume,bounds=volume_pair(target,moved)
   # No dynamic obstacle, contact history, or transformed scene retained.
   if args.phase=='domain':del moved,poses,relative,Th
   native_clear=not bool(domain['samples'][pose_index].get('nativeShellOriginalBottomIntersectionsMm3',{})) if args.phase=='domain' else None
   result={'pair':cursor,'obstacle':key,'poseIndex':pose_index,'jointDegrees':q,'volumeMm3':volume,'intersectionBoundsInHeadFrameMm':bounds,'nativeShellSourceBottomClear':native_clear,'failed':volume>1e-4}
   trace.write(json.dumps(result,separators=(',',':'))+'\n');trace.flush();os.fsync(trace.fileno())
   if result['failed']:
    state['failedPairs']+=1;state['peakContactsMm3'][key]=max(volume,state['peakContactsMm3'].get(key,0));state['nativeClearFailedPairs']+=int(native_clear is True)
   state.update(nextPair=cursor+1,lastCompletedPair=result,elapsedThisChunkSeconds=round(time.monotonic()-start,3));tested+=1
   state['complete']=state['nextPair']==total;state['passed']=state['complete'] and not state['failedPairs'];atomic_json(state_path,state);gc.collect()
   if args.stop_on_hit and result['failed']:break
 print(json.dumps({'checkpoint':str(state_path),'pairsThisRun':tested,'nextPair':state['nextPair'],'totalPairs':total,'complete':state['complete'],'failedPairs':state['failedPairs']}),flush=True)
 return 0 if not state['complete'] or state['passed'] else 2

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--describe',action='store_true');p.add_argument('--self-test',action='store_true');p.add_argument('--prepare',action='store_true');p.add_argument('--placement-only',action='store_true');p.add_argument('--delta',type=float,nargs=3,default=[12,0,0]);p.add_argument('--target',choices=['amplifier','posts','screws','cap'],default='amplifier');p.add_argument('--phase',choices=['static','domain'],default='domain');p.add_argument('--only-obstacle');p.add_argument('--max-pairs',type=int,default=80);p.add_argument('--stop-on-hit',action='store_true');p.add_argument('--name');a=p.parse_args()
 if a.describe:print(json.dumps({'candidateDeltaMm':a.delta,'defaultMaxPairs':a.max_pairs,'requiresParentCadToken':True,'inputExists':{str(x.relative_to(H)):x.exists() for x in [SOURCE,CONFIG,DOMAIN] if x.is_relative_to(H)},'noGeometryImports':True},indent=2));return 0
 if a.self_test:
  assert list(job_pairs('domain',['a','b'],[{'q':1},{'q':2}]))==[('a',0,{'q':1}),('a',1,{'q':2}),('b',0,{'q':1}),('b',1,{'q':2})]
  assert list(job_pairs('static',['a'],[{'q':1}]))==[('a',0,{})]
  assert not any(x in sys.modules for x in ['numpy','trimesh','manifold3d'])
  print('LIGHTWEIGHT_HELPER_CHECK_PASS; no CAD imports');return 0
 if a.max_pairs<1:p.error('--max-pairs must be positive')
 if a.prepare:prepare(a.delta);return 0
 return verify(a)
if __name__=='__main__':sys.exit(main())
