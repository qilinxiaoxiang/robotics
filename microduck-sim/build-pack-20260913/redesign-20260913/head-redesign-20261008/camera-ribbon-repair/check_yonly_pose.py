from pathlib import Path
import os,json,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n)
np=n['np'];mf=n['mf'];read=n['read'];load=n['loadfile'];mesh=n['mesh'];vol=n['volume'];read(Path(__file__))
def precise(p):
 read(p);m=n['trimesh'].load(p,force='mesh');assert m.is_watertight;s=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
checks=[]
for key in ['pi','zero_w_components','zero_w_gpio_solder_tails','gpio_discrete12_receiving','csi_free_straight_receiving']:
 f=D/(key+'-lowered-pose-world.stl');read(f);s=load(f).translate([0,-2,0])
 for obstacle,path in [('native_cap',D.parent/'curved-head/community-curved-head-world.stl'),('current_cap',D.parent/'gpio-audio-repair/cap-amp16z2/cap-current-audio-usb-world.stl'),('upper_pad',None)]:
  ob=precise(path) if path else n['source']('upper_pad');v,bb=vol(s,ob);checks.append({'part':key,'obstacle':obstacle,'intersectionMm3':v,'boundsMm':bb});print(key,obstacle,v,flush=True);del ob;gc.collect()
 del s;gc.collect()
r={'integrationReady':False,'deltaFromFrozenLoweredMm':[0,-2,0],'scope':'One pose boundary only; no mounts or USB changes','expectedPairs':15,'completedPairs':len(checks),'checks':checks,'sourceHashes':n['hashes']};(D/'yonly-boundary-diagnostic.json').write_text(json.dumps(r,indent=2)+'\n')
