"""Two reversible spacer candidates. Single-pose rigid clearance only, no new geometry."""
from pathlib import Path
import os,json,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(Path(__file__))
m=json.loads(read(D/'positive-x225/candidate-manifest.json'));pg=json.loads(read(D/'positive-x225/pi-geometry-manifest.json'));pose=json.loads(read(D/'positive-x225-pose.json'));T=np.array(pose['worldTransform']);direction=-T[:3,0];files=m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']};files['head_cap']='gpio-audio-repair/speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl'
keys=['motor15','camera_board','camera_retainer','face_panel','eye_trim','head_cap','head_bottom','jaw_support','upper_pad','lower_pad','amplifier','openrb']
r={'integrationReady':False,'accepted':False,'purpose':'Spacer2/3mm between existingPi rear face and unchangedface posts; movePi towardcomponentnormal. Does not establish stock,8/9mm screw choice, spacer strength, port/window/routing or installation.','spacerDirectionWorld':direction.tolist(),'baseTransform':T.tolist(),'expectedCandidates':2,'candidates':[],'sourceHashes':n['hashes']}
out=D/'fixed-pose-local-bend/pi-spacer-feasibility.json'
def save():out.write_text(json.dumps(r,indent=2)+'\n')
for d in [2.,3.]:
 row={'spacerMm':d,'translationWorldMm':(direction*d).tolist(),'checks':[],'expectedPairs':len(pg['parts'])*len(keys),'movingCount':len(pg['parts'])};r['candidates'].append(row)
 for p in pg['parts']:
  s=load(H/p['mesh']).translate(direction*d);sb=np.array(s.bounding_box()).reshape(2,3)
  for key in keys:
   if key=='openrb':
    em=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));vs=[]
    for e in em['components']:
     obb=np.array(e['bounds']);gap=float(np.linalg.norm(np.maximum(np.maximum(sb[0]-obb[1],obb[0]-sb[1]),0)))
     if gap>0:vs.append(0.);continue
     ob=load(Path(e['mesh']));v,_=n['volume'](s,ob);vs.append(v);del ob;gc.collect()
    row['checks'].append({'moving':p['key'],'obstacle':key,'overlapMm3':sum(vs),'componentsChecked':len(vs)});continue
   ob=load(H/files[key]) if key in files else n['source'](key);v,b=n['volume'](s,ob);row['checks'].append({'moving':p['key'],'obstacle':key,'overlapMm3':v,'boundsMm':b});del ob;gc.collect()
  del s;gc.collect();save()
 row['completedPairs']=len(row['checks']);row['failures']=[q for q in row['checks'] if q['overlapMm3']>1e-5];save();print(d,row['failures'],flush=True)
r['completedCandidates']=len(r['candidates']);save()
