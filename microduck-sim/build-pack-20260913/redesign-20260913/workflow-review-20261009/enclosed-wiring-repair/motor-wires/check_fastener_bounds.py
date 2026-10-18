from pathlib import Path
exec(Path(__file__).with_name('local_route.py').read_text().split('rows=[];solids=[]')[0])
G=D.parents[2]/'leg-guide-20261006/full-build-data.json';data=json.loads(G.read_text());rows=[]
for rf in ['local-route.json','mirror-route.json']:
 a=json.loads((D/rf).read_text());checks=[]
 for r in a['strands']:
  m=trimesh.load_mesh(r['file'],process=True);s=solid(m)
  for screw in data['screws']:
   if screw.get('moduleId')not in ['left-leg','right-leg']:continue
   c=np.array(screw['world_center_mm']);axis=np.array(screw['world_axis']);end=c+axis*3;start=c-axis*max(14,screw['length_mm']);lo=np.minimum(start,end)-3;hi=np.maximum(start,end)+3
   if np.any(m.bounds[1]<lo)or np.any(hi<m.bounds[0]):continue
   # Entire generous fastener AABB receives shaft + head + optional seat/washer offsets.
   b=mf.Manifold.cube(hi-lo).translate(lo);v=(s^b).volume();checks.append({'wire':r['id'],'screwId':screw['id'],'boxMm':[lo.tolist(),hi.tolist()],'intersectionMm3':v})
 rows.append({'route':a['route'],'routeSha256':sha(D/rf),'nearFastenerChecks':checks,'passed':all(x['intersectionMm3']<1e-7 for x in checks)})
 print(a['route'],checks)
(D/'fastener-clearance.json').write_text(json.dumps({'sourceSha256':sha(G),'envelope':'Shaft up to14mm inward (or source length when larger), head/seat3mm outward, radius3mm axis-aligned box. Conservative clearance only; collision not equivalent to actual screw collision.','routes':rows},indent=2))
