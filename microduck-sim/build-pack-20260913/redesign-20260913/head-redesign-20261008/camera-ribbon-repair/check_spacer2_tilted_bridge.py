from pathlib import Path
f=Path(__file__).parent/'check_spacer2_prefix_current.py';exec(compile(f.read_text().split("solid=load(O/")[0],str(f),'exec'))
import inspect,fit_spacer2_negative_edge as edge
src=inspect.getsource(edge.family).replace("('B',math.pi-alpha,0,-1,1)","('B',math.pi-alpha,-.04,-1,1)");env=edge.__dict__.copy();exec(src,env)
x=np.array([50.5,10,6,15,12,40,3,8,.07,.785,-.785,math.pi,0,math.pi]);_p,_t,_w,_L,bends,pr=env['family'](x);bends=bends[:3];p=pr[6]['p']+6*pr[6]['t'];t=pr[6]['t'];w=pr[6]['w'];L=pr[6]['s0']+6
solid=build(5,L);keys=sorted((set(n['P'])|set(files))-removed);r={'accepted':False,'localBridgeClear':False,'firstNearUBendObliquityRadians':-.04,'materialPrefixLengthMm':L,'endpoint':p.tolist(),'tangent':t.tolist(),'widthVector':w.tolist(),'expectedObstacles':len(keys),'completedObstacles':0,'checks':[],'sourceHashes':n['hashes']};read(D/'fit_spacer2_negative_edge.py');r['mesh']=export(solid,'spacer2-negative-end-tilted-bridge')
for key in keys:
 if key=='openrb':
  em=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));bb=np.array(solid.bounding_box()).reshape(2,3);v=0
  for z in em['components']:
   zb=np.array(z['bounds'])
   if np.any(bb[1]<zb[0]) or np.any(zb[1]<bb[0]):continue
   ob=load(Path(z['mesh']));v+=n['volume'](solid,ob)[0];del ob
  bounds=None
 else:
  ob=load(H/files[key]) if key in files else n['source'](key)
  if key in shiftKeys:ob=ob.translate(delta)
  v,bounds=n['volume'](solid,ob);del ob
 r['checks'].append({'obstacle':key,'overlapMm3':v,'bounds':bounds});r['completedObstacles']+=1;gc.collect()
 if v>1e-6:print(key,v,bounds,flush=True)
r['localBridgeClear']=r['completedObstacles']==r['expectedObstacles'] and not any(z['overlapMm3']>1e-6 for z in r['checks']);(O/'spacer2-negative-end-tilted-bridge.json').write_text(json.dumps(r,indent=2)+'\n');print('localClear',r['localBridgeClear'],p.tolist())
