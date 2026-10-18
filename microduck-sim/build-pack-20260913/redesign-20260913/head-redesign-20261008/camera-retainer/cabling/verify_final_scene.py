from pathlib import Path
import json,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parent;C=R.parent/'curved-head'
def solid(p):
 m=trimesh.load_mesh(p,process=True);return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
fixed_names=['curved-cap-final-candidate','openrb-curved-layout','speaker-curved-layout','amplifier-curved-layout','audio-roof-posts','speaker-cradle','speaker-keeper','zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails','cap-eight-screw-heads-four-nuts']
fixed={n:solid(C/(n+'-world.stl')) for n in fixed_names};files=[C/(n+'-world.stl') for n in fixed_names];out={}
for label,folder in [('baseline_upward_exit',R),('rotated_side_exit',D/'rotated-camera-candidate')]:
 rows={}
 for n in ['camera-retainer','camera-shifted-reference','camera-ribbon-shifted-reference','camera-all-six-screw-envelopes']:
  p=folder/(n+'-world.stl');files.append(p);s=solid(p);rows[n]={k:max(0,(s^o).volume()) for k,o in fixed.items()}
 out[label]={'checksMm3':rows,'passesStatic':all(v<1e-5 for r in rows.values() for v in r.values()),'driverStage':'All six screws tightened on detached face subassembly before Pi, cap, OpenRB and audio are present. Existing shaft/handle/grip tests use exactly that bench obstacle set.','fullRibbonPass':False}
report={'date':'2026-10-08','variants':out,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'scope':'Final installed electronics/shell static only, plus earlier detached-bench driver checks; full SC1892 route remains blocked.'}
(D/'final-scene-camera-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(out,indent=2));assert all(v['passesStatic'] for v in out.values())
