from pathlib import Path
f=Path(__file__).parent/'check_spacer2_full_ribbon.py'
exec(compile(f.read_text().split('keys=sorted(')[0],str(f),'exec'))
from matplotlib.path import Path as Poly
from scipy.ndimage import distance_transform_edt
xs=np.arange(64,82.01,.5);ys=np.arange(-40,40.01,.5);zs=np.arange(107,155.01,.5);xy=np.array(np.meshgrid(xs,ys,indexing='ij')).reshape(2,-1).T;occ=np.zeros((len(xs),len(ys),len(zs)),bool)
keys=sorted((set(n['P'])|set(files))-removed);done=[]
for key in keys:
 if key=='openrb':continue # maxX58.738 outsidefield; fullmesh exactgate stillmandatory.
 ob=load(H/files[key]) if key in files else n['source'](key)
 if key in shiftKeys:ob=ob.translate(delta)
 bb=np.array(ob.bounding_box()).reshape(2,3)
 if np.any(bb[1]<[64,-40,107]) or np.any(bb[0]>[82,40,155]):del ob;continue
 for k,z in enumerate(zs):
  if z<bb[0,2] or z>bb[1,2]:continue
  inside=np.zeros(len(xy),bool)
  for poly in ob.slice(float(z)).to_polygons():
   if len(poly)>=3:inside ^= Poly(poly).contains_points(xy)
  occ[:,:,k]|=inside.reshape(len(xs),len(ys))
 done.append(key);del ob;gc.collect()
sdf=(distance_transform_edt(~occ)-distance_transform_edt(occ))*.5
np.savez_compressed(O/'spacer2-field.npz',sdf=sdf.astype(np.float32),origin=[64,-40,107],step=.5)
(O/'spacer2-field.json').write_text(json.dumps({'purpose':'Candidateoptimizationonly; voxelapproximationnotacceptance','included':done,'sourceHashes':n['hashes']},indent=2)+'\n');print(len(done),float(occ.mean()))
