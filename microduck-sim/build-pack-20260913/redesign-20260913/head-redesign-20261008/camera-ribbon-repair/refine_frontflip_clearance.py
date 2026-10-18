from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(Path(__file__))
from scipy.optimize import least_squares
r=json.loads(read(D/'occupancy-layout/frontFlip-0/report.json'));parts={r['key']:load(H/r['mesh']) for r in r['parts']};rb=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));ob={'native_cap':load(H/'curved-head/community-curved-head-world.stl'),'camera':load(D/'positive-x225/camera_flip180-world.stl'),'amp':load(H/'gpio-audio-repair/amp16z2-closed-receiving-world.stl'),'head_bottom':n['source']('head_bottom')}
for i in [65,28,141]:ob['OpenRB_'+str(i)]=load(Path(rb['components'][i]['mesh']))
pairs=[(c['part'],c['obstacle']) for c in r['checks'] if c['gapCapped2']<1.8];history=[]
def f(x):
 vals=[]
 for a,b in pairs:
  s=parts[a].translate(x);v,_=n['volume'](s,ob[b]);g=float(s.min_gap(ob[b],1));vals.append(max(0,.55-g)+max(0,v)**.5)
 history.append({'deltaMm':list(x),'maxResidual':max(vals)});return np.r_[vals,np.array(x)*.005]
fit=least_squares(f,[0,0,0],bounds=([-2,-2,-2],[2,2,2]),max_nfev=70,diff_step=.001,ftol=1e-8,xtol=1e-8,gtol=1e-8);T=np.array(r['candidate']['worldTransform']);T[:3,3]+=fit.x;out={'integrationReady':False,'purpose':'local three translation variables, four original limiting obstacles; exact fullscene rerun required','deltaMm':fit.x.tolist(),'worldTransform':T.tolist(),'residual':f(fit.x).tolist(),'pairs':pairs,'history':history,'sourceHashes':n['hashes']};(D/'occupancy-layout/frontFlip-refinement.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['history','sourceHashes']},indent=2))
