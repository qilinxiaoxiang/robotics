"""One outward diagonal180 fold, six bounded entrance cases, existing fixed scene."""
from pathlib import Path
import os,json,math,gc,ast
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);O=D/'fixed-pose-local-bend';trimesh=tm
import developable_ribbon_inner_entry as dr
read(Path(__file__));read(D/'developable_ribbon_inner_entry.py');src=read(D/'optimize_x225_u80.py').decode();f=next(a for a in ast.parse(src).body if isinstance(a,ast.FunctionDef) and a.name=='construct');exec(ast.unparse(f).replace('np.linspace(-8, 8, width_step + 1)','np.linspace(-WIDTH/2, WIDTH/2, width_step + 1)').replace('0.3 * norms','THICKNESS/2 * norms'))
def family(x):
 p=np.array([75.63,9.3706236,131.1145958]);t=np.array([0.,1,0]);w=np.array([0.,0,1]);phi=0.;angle=math.pi-.07;R=dr.R;n0=np.cross(t,w);e=w;q=t;p=p+t*FREE;L=R*angle;b={'s0':FREE,'s1':FREE+L,'p':p.copy(),'t':t.copy(),'w':w.copy(),'n':n0,'e':e,'q':q,'angle':angle,'phi':phi,'sign':-1,'R':R};p=p+q*R*math.sin(angle)-n0*R*(1-math.cos(angle));t=q*math.cos(angle)-n0*math.sin(angle);L+=FREE+24;p=p+t*24;return p,t,w,L,[b],[]
dr.family=family
m=json.loads(read(D/'positive-x225/candidate-manifest.json'));base=json.loads(read(H/'viewer-candidate.json'));files=(base['replacementMeshes']|{q['key']:q['mesh'] for q in base['additionalParts']})|(m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']});files['head_cap']='gpio-audio-repair/speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl';files['amplifier']='gpio-audio-repair/amp16z2-closed-receiving-world.stl';keys=['camera_board','camera_retainer','camera_clamp_screw_1','camera_clamp_screw_2','camera_clamp_screw_3','face_panel','eye_trim','pi','zero_w_components','zero_w_gpio_male_receiving','zero_w_gpio_solder_tails','E-pi-01_revision_screw','E-pi-02_revision_screw','E-pi-04_revision_screw','head_cap','amplifier','head_bottom','motor15','jaw_support']
r={'integrationReady':False,'accepted':False,'scope':'One inward near180 U with7e-2rad return tilt following Pi-camera gap,then24mm along-Y. Width16/11.5 andthickness0.2/0.3/0.4/0.6 sensitivity.4mm free straight,R0.25or0.35 centerline are NOT physical cable measurements or bend certification.','expectedCases':8,'cases':[],'sourceHashes':n['hashes']}
def save():(O/'inclined-return-entrance.json').write_text(json.dumps(r,indent=2)+'\n')
for WIDTH in [16,11.5]:
 for THICKNESS in [.2,.3,.4,.6]:
  dr.R=.25 if THICKNESS<.5 else .35;FREE=4.
  p,t,w,L,b,_=family(None);s=construct(0,L,.03,None,24);row={'radiusMm':dr.R,'widthMm':WIDTH,'thicknessMm':THICKNESS,'centerlineFirstStraightMm':FREE,'minimumFreeStraightAcross16mmWidthMm':FREE,'endMm':p.tolist(),'endTangent':t.tolist(),'materialPrefixLengthMm':L,'checks':[]};r['cases'].append(row)
  for key in keys:
   ob=load(H/files[key]) if key in files else n['source'](key);v,bb=n['volume'](s,ob);row['checks'].append({'obstacle':key,'overlapMm3':v,'boundsMm':bb,'minimumGapCapped2Mm':float(s.min_gap(ob,2))});del ob;gc.collect()
  row['expectedPairs']=len(keys);row['completedPairs']=len(row['checks']);row['mesh']=export(s,f'inclined-return-w{WIDTH}-t{THICKNESS}');row['failures']=[q for q in row['checks'] if q['overlapMm3']>1e-5];save();print(dr.R,FREE,[(q['obstacle'],q['overlapMm3']) for q in row['failures']],flush=True);del s;gc.collect()
r['completedCases']=len(r['cases']);save()
