import os,sys,json,hashlib,types,gc
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
O=Path(__file__).resolve().parent;D=O.parent;R=D.parents[2];H=R/'head-redesign-20261008';W=R/'workflow-review-20261009';A=H/'gpio-audio-repair'
sys.path.insert(0,str(A));import precision_mesh as pm
ctx=types.SimpleNamespace(np=np,tm=tm,mf=mf);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();hashes={str(Path(__file__)):sha(__file__)}
def read(p):
 hashes[str(p)]=sha(p);return json.loads(Path(p).read_text())
def load(p):
 hashes[str(p)]=sha(p);return pm.load(ctx,Path(p))
rows={r['key']:r for r in read(W/'original-body-converter/fusion-import-manifest.json')['parts']}
def source(k):
 r=rows[k];return load(r['file']).translate(r.get('importTranslationMm',[0,0,0]))
Tp=np.array(read(D/'pi-front-up05-pose.json')['piCurrentWorldDelta']);piT=np.array(read(H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json')['worldTransform'])
delta=np.array([-29.,17.2,0]);amp=load(A/'amp16z2-closed-receiving-world.stl').translate(delta)
export=O/'amplifier-front-free-bay-world.stl';pm.export(ctx,amp,export)
holes=[(np.array(read(A/f'cap-amp16z2/amp-new-post-{i}.json')['holeBottomMm'])+delta).tolist() for i in [0,1]]
routes=read(A/'speaker-rewire-amp16z2p0-proposal.json');ports=[];tools=[]
for r,t in zip(routes['routes'],routes['terminalTools']):
 p=(np.array(r['terminalMouthWorldMm'])+delta).tolist();q=(np.array(t['receivingTopWorldMm'])+delta).tolist();ports.append({'pin':r['terminalPin'],'net':r['net'],'mouthMm':p,'outwardAxis':[-1,0,0],'insertionAxis':[1,0,0],'terminalScrewTopReceivingMm':q,'toolOutwardAxis':[0,0,1]})
 tools.append((f'terminal_driver_{r["terminalPin"]}',mf.Manifold.cylinder(45,1.5,circular_segments=32).translate(q)))
 # Eight mm straight receiving lead along -X; not a claim of actual minimum free length.
 tools.append((f'terminal_lead_{r["terminalPin"]}',mf.Manifold.cylinder(8,.75,circular_segments=32).rotate([0,-90,0]).translate(p)))
for i,p in enumerate(holes):tools.append((f'mount_driver_{i}',mf.Manifold.cylinder(30,1.5,circular_segments=32).translate([p[0],p[1],p[2]-1.57-30])))
checks=[]
def test(name,s,key,obs,role):
 a=np.array(s.bounding_box()).reshape(2,3);b=np.array(obs.bounding_box()).reshape(2,3);sep=np.any(a[1]<b[0])or np.any(b[1]<a[0]);q=None if sep else s^obs;v=0 if sep else max(0,q.volume());checks.append({'moving':name,'fixed':key,'role':role,'volumeMm3':v,'method':'AABB separation'if sep else'independent solid intersection','intersectionBoundsMm':list(q.bounding_box())if v>1e-7 else None})
fixed=['head_cap','jaw_support','jaw_frame','upper_pad','lower_pad','head_bottom','motor13','motor14','motor15','head_yaw_link','face_panel','camera_retainer','camera_board','eye_trim','speaker','speaker_cradle','speaker_keeper']+[k for k in rows if k.startswith('camera_clamp_screw_')]
for key in fixed:
 obs=load(D/'pi-roof-mounts/closed-cap-with-pi-bosses-world.stl') if key=='head_cap' else load(H/'camera-ribbon-repair/positive-x225/face_three_screw_camera-world.stl') if key=='face_panel' else source(key)
 test('amplifier',amp,key,obs,'final seated');
 for name,s in tools:test(name,s,key,obs,'tool or terminal lead receiving')
 del obs;gc.collect()
for key in rows:
 if not(key=='pi' or key.startswith(('zero_w_','gpio_pin_','component_'))):continue
 obs=source(key)
 if key.startswith('gpio_pin_'):obs=(obs.transform(np.linalg.inv(piT)[:3])^mf.Manifold.cube([200,400,400]).translate([50.52,-200,-100])).transform(piT[:3])
 obs=obs.transform(Tp[:3]);test('amplifier',amp,key,obs,'final seated')
 for name,s in tools:test(name,s,key,obs,'tool or terminal lead receiving')
 del obs;gc.collect()
# Native cap now explicitly retained, including any old features; no label-based removal.
hits=[x for x in checks if x['volumeMm3']>1e-7];out={'status':'ONE_SPECIFIED_POSE_CHECKED','integrationReady':False,'physicalFitVerified':False,'deltaFromAmp16z2Mm':delta.tolist(),'ampBoundsMm':list(amp.bounding_box()),'mesh':str(export),'meshSha256':sha(export),'mountHoleTopCentersMm':holes,'pcbStackMm':1.57,'mountHoleBottomCentersMm':[[x,y,z-1.57] for x,y,z in holes],'terminalPorts':ports,'checks':checks,'hits':hits,'ampStaticClear':not any(x['moving']=='amplifier' for x in hits),'sourceHashes':hashes,'scope':'One specified amplifier translation only. Source whole cap including Pi posts retained. Individual real male pins and twelve16.79mm female class receiving bodies; no full-row margin brick. Source terminal body included, screws/tools still dimensioned receiving. No mounting geometry change or new wire route accepted.'}
(O/'one-pose-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['ampBoundsMm','mountHoleTopCentersMm','terminalPorts','ampStaticClear','hits']},indent=2))
