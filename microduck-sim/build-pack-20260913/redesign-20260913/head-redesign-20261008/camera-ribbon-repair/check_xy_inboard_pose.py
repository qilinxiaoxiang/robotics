from pathlib import Path
import os,json,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n)
np=n['np'];mf=n['mf'];read=n['read'];load=n['loadfile'];mesh=n['mesh'];vol=n['volume'];read(Path(__file__))
def precise(p):
 read(p);m=n['trimesh'].load(p,force='mesh');assert m.is_watertight;s=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
checks=[]
pieces=[(k,D/(k+'-lowered-pose-world.stl')) for k in ['pi','zero_w_components','zero_w_gpio_solder_tails','csi_free_straight_receiving']]+[(q['key'],D.parent/q['mesh']) for q in json.loads(read(D/'gpio-individual-receiving-manifest.json'))['additionalParts']]
for key,f in pieces:
 read(f);s=precise(f).translate([-2,-2,0])
 for obstacle,path in [('native_cap',D.parent/'curved-head/community-curved-head-world.stl'),('current_cap',D.parent/'gpio-audio-repair/cap-amp16z2/cap-current-audio-usb-world.stl'),('upper_pad',None),('jaw_support',None),('motor15',None),('head_bottom',D/'head-bottom-pi-receiver-world.stl')]:
  ob=precise(path) if path else n['source'](obstacle);v,bb=vol(s,ob);checks.append({'part':key,'obstacle':obstacle,'intersectionMm3':v,'boundsMm':bb});print(key,obstacle,v,flush=True);del ob;gc.collect()
 del s;gc.collect()
r={'integrationReady':False,'deltaFromFrozenLoweredMm':[-2,-2,0],'scope':'One pose boundary only; no mounts or USB changes','expectedPairs':len(pieces)*6,'completedPairs':len(checks),'checks':checks,'sourceHashes':n['hashes']};(D/'xy-inboard-boundary-diagnostic.json').write_text(json.dumps(r,indent=2)+'\n')
