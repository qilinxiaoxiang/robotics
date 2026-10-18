"""Eight finite entrance-boundary probes; no new topology or mounting geometry."""
from pathlib import Path
import os,json,math,gc,ast
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);O=D/'fixed-pose-local-bend';read(Path(__file__));src=read(D/'check_fixed_camera_early_bend.py').decode();f=next(a for a in ast.parse(src).body if isinstance(a,ast.FunctionDef) and a.name=='prefix');code=ast.unparse(f).replace('8 + math.pi * R / 2','FREE + 4 + math.pi * R / 2').replace(', 4, 4 +',', FREE, FREE +').replace('s <= 4','s <= FREE').replace('s - 4','s - FREE').replace('4 + R *','FREE + R *').replace('4 + R,','FREE + R,');exec(code)
m=json.loads(read(D/'positive-x225/candidate-manifest.json'));base=json.loads(read(H/'viewer-candidate.json'));files=(base['replacementMeshes']|{q['key']:q['mesh'] for q in base['additionalParts']})|(m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']});files['head_cap']='gpio-audio-repair/speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl';files['amplifier']='gpio-audio-repair/amp16z2-closed-receiving-world.stl';keys=['camera_board','camera_retainer','camera_clamp_screw_1','camera_clamp_screw_2','camera_clamp_screw_3','face_panel','eye_trim','pi','zero_w_components','zero_w_gpio_male_receiving','zero_w_gpio_solder_tails','E-pi-01_revision_screw','E-pi-02_revision_screw','E-pi-04_revision_screw','head_cap','amplifier','head_bottom','motor15','jaw_support']
r={'integrationReady':False,'accepted':False,'scope':'Same R3 bend toward-X with0/1/2/3mm free straight, width16/11.5, thickness0.6. Early bend is geometric sensitivity, not evidence that reinforcement allows bending this early.','expectedCases':8,'cases':[],'sourceHashes':n['hashes']}
def save():(O/'entrance-boundary.json').write_text(json.dumps(r,indent=2)+'\n')
for FREE in [0.,1.,2.,3.]:
 for width in [16,11.5]:
  s=prefix(width,.6);row={'freeStraightMm':FREE,'widthMm':width,'thicknessMm':.6,'checks':[]};r['cases'].append(row)
  for key in keys:
   ob=load(H/files[key]) if key in files else n['source'](key);v,b=n['volume'](s,ob);row['checks'].append({'obstacle':key,'overlapMm3':v,'boundsMm':b,'minimumGapCapped2Mm':float(s.min_gap(ob,2))});del ob;gc.collect()
  row['mesh']=export(s,f'boundary-free{FREE}-width{width}');row['completedPairs']=len(row['checks']);row['expectedPairs']=len(keys);row['failures']=[q for q in row['checks'] if q['overlapMm3']>1e-5];save();print(FREE,width,row['failures'],flush=True);del s;gc.collect()
r['completedCases']=len(r['cases']);save()
