"""Two ordinary tie envelopes: whole-thigh anchor and loose loop keeper."""
from pathlib import Path
import json,math,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).parent;O=D.parents[1]/'roof-wiring-stage/motor-wires/obstacles'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def solid(m):
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert str(a.status())=='Error.NoError' and a.volume()>0;return a
def contour(x0,x1,y0,y1,r):
 return [[x+r*math.cos(math.radians(q)),y+r*math.sin(math.radians(q))] for x,y,st in [(x1-r,y1-r,0),(x0+r,y1-r,90),(x0+r,y0+r,180),(x1-r,y0+r,270)] for q in np.linspace(st,st+90,49,endpoint=False)]
def ring(bounds,r,t,width):
 x0,x1,y0,y1=bounds
 return (mf.CrossSection([contour(x0,x1,y0,y1,r)])-mf.CrossSection([contour(x0+t,x1-t,y0+t,y1-t,r-t)])).extrude(width)
parts={
 'thigh-body-tie':ring([-46.0,18.65,-72.0,-40.95],2,1.3,4.8).translate([0,0,-35.4]),
 'thigh-body-lock':mf.Manifold.cube([6.5,7,4.8]).translate([18.65,-59,-35.4]),
 'loop-keeper-tie':ring([15.5,51.,-37.,-28.5],1.6,.8,2.5).transform([[1,0,0,0],[0,0,1,-45.25],[0,1,0,0]]),
 'loop-keeper-lock':mf.Manifold.cube([5,5,3]).translate([51,-46.5,-34.5]),
}
rows=[]
for key,a in parts.items():
 tm=a.to_mesh64();m=trimesh.Trimesh(tm.vert_properties,tm.tri_verts,process=True);m.fix_normals();assert m.is_watertight
 f=D/(key+'.stl');m.export(f);checks=[]
 for p in O.glob('*.json'):
  o=json.loads(p.read_text());bb=np.array(o['expectedFinalBoundsMm'])
  if np.any(m.bounds[1]<bb[0])or np.any(bb[1]<m.bounds[0]):continue
  b=trimesh.load_mesh(o['file'],process=True);b.apply_translation(o.get('importTranslationMm',[0,0,0]));cut=a^solid(b);v=cut.volume();checks.append({'key':o['key'],'sourceSha256':o['sha256'],'volumeMm3':v,'bounds':list(cut.bounding_box()) if v>1e-7 else None})
 for i in range(1,4):
  p=D/f'local-04-03-wire-{i}.stl';b=solid(trimesh.load_mesh(p));cut=a^b;checks.append({'key':p.name,'sourceSha256':sha(p),'volumeMm3':cut.volume()})
 rows.append({'key':key,'file':str(f),'sha256':sha(f),'bounds':m.bounds.tolist(),'checks':checks});print(key,[(x['key'],round(x['volumeMm3'],6))for x in checks],flush=True)
selfs=[{'a':a,'b':b,'volumeMm3':(x^y).volume()} for i,(a,x)in enumerate(parts.items())for j,(b,y)in enumerate(parts.items())if i<j]
print('self',selfs)
(D/'body-keeper.json').write_text(json.dumps({'status':'candidate only; nominal neutral receiving envelopes','parts':rows,'self':selfs,'body':'upper_leg_right','primaryTie':{'quantityPerLeg':1,'minimumLengthMm':210,'bodyMaxWidthMm':4.8,'bodyMaxThicknessMm':1.3,'lockReceivingMm':[6.5,7,4.8]},'secondaryTie':{'quantityPerLeg':1,'minimumLengthMm':110,'bodyMaxWidthMm':2.5,'bodyMaxThicknessMm':.8,'lockReceivingMm':[5,5,3]},'stock':'Club-supply requirement, inventory not confirmed, no purchase authorized. Existing allocations are not silently reassigned.','scope':'Loose secondary keeper captures the three U loops and the primary thigh tie on the moving upper leg. Envelope is not a prediction of a cinched flexible shape. Do not cinch the service loops rigidly across the joint; actual manual joint sweep sets final slack.'},indent=2))
