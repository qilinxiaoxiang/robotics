from pathlib import Path
import json,base64,hashlib,numpy as np,trimesh,manifold3d as mf
from scipy.spatial.transform import Rotation
import cadquery as cq
R=Path(__file__).resolve().parent;G=R.parent/'leg-guide-20261006';SIM=R.parents[2];D=json.loads((G/'full-build-data.json').read_text());ROWS={p['key']:p for p in D['parts']}
for p in ['STL','CAD','evidence']: (R/p).mkdir(exist_ok=True)
SPLIT=-1.6;LUGS=[[-12.,2.],[12.,2.]];PEGS=[]
# Shawn 2026-10-19: the side's sleeve-capture lip (from the stock bracket) is 0.25-0.5 mm thick, one or two layers, and
# snaps. It is raised to LIP_TOP over its ring (r LIP_R_IN..LIP_R_OUT) wherever the side exists; its lower face, the
# sleeve's axial stop at z 1.5, does not move.
# The ring sits 0.05 mm inside the lip's existing bore (r 7.0) and outer face (r 9.2), so the union makes no coincident
# slivers; the bore steps out 0.05 mm above the old lip top.
LIP_R_IN,LIP_R_OUT,LIP_Z0,LIP_TOP=7.05,9.15,1.5,2.7
def solid(key,T):
 p=ROWS[key];m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),dtype='<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),dtype='<u4').reshape(-1,3),process=True).apply_transform(np.linalg.inv(T));a=mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)));assert a.status()==mf.Error.NoError;return a

def cyl(r,z0,z1,xy=(0,0)):
 return mf.Manifold.cylinder(z1-z0,r,r,96).translate([*xy,z0])
def box_z(z0,z1):return mf.Manifold.cube([200,200,z1-z0]).translate([-100,-100,z0])
def mesh(a):
 m=a.to_mesh();return trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=True)
def export(a,key,T):
 m=mesh(a);p=R/'STL'/f'{key}-local.stl';m.export(p);w=m.copy().apply_transform(T);p=R/'STL'/f'{key}-world.stl';w.export(p);return str(p)
cleanup=[];corners=[]
def clean(a,key):
 cs=a.decompose();big=[c for c in cs if c.volume()>1e-5];assert len(big)==1,(key,[c.volume() for c in cs]);tiny=[c for c in cs if c.volume()<=1e-5];cleanup.append({'part':key,'inputComponents':len(cs),'outputComponents':1,'discardedVolumeMm3':sum(max(0.,c.volume()) for c in tiny),'discardedTriangles':sum(c.num_tri() for c in tiny),'thresholdMm3':1e-5});return big[0]
def trim_wing_tips(base,old,side,z_top=1.65,run=1.6,out=.3,dz=.05):
 """Cut each acute end of the base's wing face (x = +-11) square to the outer surface, 1.6 mm along it, over the heights
 where that end exists (sampled every dz; one prism per end, from the split up to at most the post underside)."""
 from shapely.geometry import Polygon,LineString,Point
 from shapely.geometry.polygon import orient
 from shapely.ops import unary_union
 tips={}
 for zs in np.arange(SPLIT+.01,z_top,dz):
  sec=unary_union([Polygon(r).buffer(0) for r in old.slice(zs).to_polygons()])
  for X in (11.,-11.):
   fx=np.array([np.sign(X),0.])
   wing=sec.intersection(Polygon([(X,-60),(X+60*fx[0],-60),(X+60*fx[0],60),(X,60)]))
   for w in getattr(wing,'geoms',[wing]):
    if w.area<1: continue
    ring=LineString(list(w.exterior.coords));face=[c for c in w.exterior.coords[:-1] if abs(c[0]-X)<1e-3]
    if len(face)<2: continue
    for tip,v in ((max(face,key=lambda c:c[1]),np.array([0.,-1.])),(min(face,key=lambda c:c[1]),np.array([0.,1.]))):
     t=np.array(tip);d0=ring.project(Point(tip))
     cand=[ring.interpolate((d0+k*run)%ring.length) for k in (1,-1)]
     cand=[np.array([c.x,c.y]) for c in cand if abs(c.x-X)>.2]
     if not cand: continue
     a=cand[0];u=(a-t)/np.linalg.norm(a-t)
     tip_deg=float(np.degrees(np.arccos(np.clip(u@v,-1,1))))
     if not 5<tip_deg<80: continue
     key=(X,round(float(t[1]),1))
     if key in tips: tips[key]['z1']=zs;continue
     n=np.array([-u[1],u[0]])
     if n@v<0: n=-n                                   # into the wing, on the face side of the outer surface
     I=a+n*((X-a[0])/n[0])                            # square to the surface at a, back to the split face
     tips[key]=dict(t=t,a=a,I=I,n=n,fx=fx,deg=tip_deg,z0=zs,z1=zs)
 trims=[];v0=base.volume()
 for (X,_),d in sorted(tips.items()):
  t,a,I,n,fx=d['t'],d['a'],d['I'],d['n'],d['fx']
  # the prism's faces stay off the base's own faces (split plane, split height, post underside) so no sliver triangles form
  z0=SPLIT-.05 if d['z0']<SPLIT+dz else d['z0']-dz;z1=min(d['z1']+dz,z_top)+(.05 if d['z1']+dz>=z_top else 0)
  Iext=I+(I-a)/np.linalg.norm(I-a)*out
  P=orient(Polygon([tuple(t-out*n-out*fx),tuple(a-out*n),tuple(a),tuple(Iext),tuple(t-out*fx)]).buffer(0),1.)
  vb=base.volume();base=base-mf.CrossSection([np.asarray(P.exterior.coords[:-1],float)]).extrude(z1-z0).translate([0,0,z0])
  trims.append({'side':side,'x':X,'tipMm':np.round(t,2).tolist(),'tipAngleDeg':round(d['deg'],1),'squareFaceMm':[np.round(a,2).tolist(),np.round(I,2).tolist()],
                'zMm':[round(float(z0),2),round(float(z1),2)],'removedMm3':round(vb-base.volume(),3)})
 return base.simplify(1e-4),trims
frames={};parts={};manifest={'schemaVersion':1,'prototypeOnly':True,'sourceOverwrite':False,'sides':{}}
for side,ankle,lower,motor,ring in [('left','ankle','lower','motor6','smallring'),('right','right_ankle','right_lower','motor1','right_smallring')]:
 sign=1 if side=='left' else -1;T=np.eye(4);T[:3,:3]=np.array([[sign,0,0],[0,0,-sign],[0,1,0]]);T[:3,3]=[-31.7771,sign*33.8,-81.5];frames[side]=T
 old=solid(ankle,T);parts[side]={k:solid(k,T) for k in [ankle,lower,motor,ring]}
 originalBase=old^box_z(-100,SPLIT);originalCap=old^box_z(SPLIT,3.)
 wings=old^(mf.Manifold.cube([100,200,200]).translate([11,-100,-100])+mf.Manifold.cube([100,200,200]).translate([-111,-100,-100]));wings=wings^box_z(SPLIT,3.)
 base=originalBase+wings;cap=originalCap-wings
 for x,_ in LUGS:
  post=mf.Manifold.cube([4,6.5,5.45]).translate([x-2,-4.5,1.65]);base=base+post
  # Shawn 2026-10-19: no tongue and no slot. The 0.4 mm tongue was split by the screw hole and the slot left 0.9 mm walls;
  # the side is located sideways by the two screws in their 2.3 mm holes and radially by the sleeve in its pocket.
  cap=cap-mf.Manifold.cube([4.2,6.6,100]).translate([x-2.1,-4.55,-50])
  tab=mf.Manifold.cube([7,4,5.45]).translate([x-4,2.,1.65]) if x>0 else mf.Manifold.cube([7,4,5.45]).translate([x-3,2.,1.65])
  cap=cap+tab
  # Transverse Y clearance and blind TAP pilot; no shaft enters case/lower axial slab.
  Ry=Rotation.from_euler('x',-90,degrees=True).as_matrix()
  pilot=mf.Manifold.cylinder(4.55,.8,.8,96).transform(np.c_[Ry,[x,-2.5,4.5]])   # to the post face at y 2.0 (no slot in front of it)
  clearance=mf.Manifold.cylinder(4.55,1.15,1.15,96).transform(np.c_[Ry,[x,1.5,4.5]])
  base=base-pilot;cap=cap-clearance
 # Shawn 2026-10-19, minimum wall 1.2 mm: the x=+-11 split crosses the stock outer surface at 40-50 deg, so each end of
 # the base's wing face is a knife edge (0.25-0.6 mm, wall check). Each acute tip is cut off by a face square to the
 # outer surface, 1.6 mm along it, from the split up to the post underside; the side is not touched.
 base,trims=trim_wing_tips(base,old,side);corners.extend(trims)
 lip=(cyl(LIP_R_OUT,LIP_Z0,LIP_TOP)-cyl(LIP_R_IN,LIP_Z0-1,LIP_TOP+1))^cap.project().extrude(LIP_TOP-LIP_Z0).translate([0,0,LIP_Z0]);cap=(cap+lip).simplify(1e-4)
 base=clean(base,side+'-base');cap=clean(cap,side+'-cheek')
 assert base.status()==mf.Error.NoError and cap.status()==mf.Error.NoError
 for nm,q in (('side',cap),('base',base)):
  mq=mesh(q);print('MESHCHECK',side,nm,mq.is_watertight,mq.is_winding_consistent,float(mq.area_faces.min()),int((mq.area_faces<=1e-9).sum()),flush=True)
  assert mq.is_watertight and mq.is_winding_consistent and (mq.area_faces>1e-9).all(),(side,nm,'mesh not watertight or has zero-area faces')
 ringCad=cq.Workplane('XZ').polyline([(5.4,-1.4),(7.1,-1.4),(7.3,-1.2),(7.3,1.2),(7.1,1.4),(5.4,1.4),(5.2,1.2),(5.2,-1.2)]).close().revolve(360,(0,0),(0,1));cq.exporters.export(ringCad,str(R/'STL'/f'{side}-sleeve-local.stl'),tolerance=.002,angularTolerance=.02);rs=trimesh.load(R/'STL'/f'{side}-sleeve-local.stl',force='mesh',process=True);sleeve=mf.Manifold(mf.Mesh(np.asarray(rs.vertices,dtype=np.float32),np.asarray(rs.faces,dtype=np.uint32)));assert sleeve.status()==mf.Error.NoError
 parts[side].update(base=base,cheek=cap,sleeve=sleeve)
 manifest['sides'][side]={'frameWorld':T.tolist(),'parts':[],'contextKeys':[lower,motor,'foot' if side=='left' else 'right_foot'],'steps':[],'fasteners':[]}
 for name,a in [('base',base),('cheek',cap),('sleeve',sleeve)]:
  key=f'{side}_{name}';p=export(a,f'{side}-{name}',T);manifest['sides'][side]['parts'].append({'key':key,'name':f'{side.title()} removable ankle {name}','color':'#ff8000' if name!='sleeve' else '#222222','stl':p,'coordinateFrame':'guide-world-mm','localStl':str(R/'STL'/f'{side}-{name}-local.stl'),'triangles':len(mesh(a).faces),'volumeMm3':a.volume()})
 print('GENERATED',side,'vol',[base.volume(),cap.volume(),sleeve.volume()],flush=True)
 # Probe complete preassembled package; source case contacts remain internal.
 for distance in [30,20,12,8,4,2,1,.5,0]:
  ovs={k:float((a.translate([0,distance,0])^base).volume()) for k,a in [(lower,parts[side][lower]),(motor,parts[side][motor]),('sleeve',sleeve)]};print('PACKAGE_TOP',side,distance,ovs,flush=True)
 # Probe insertion of lower+sleeve after a bare motor is loose in the base.
 for distance in [12,8,4,2,1,.5,0]:
  moving=parts[side][lower].translate([0,0,distance]);sv=sleeve.translate([0,0,distance]);print('INSERT',side,distance,'lower/base',(moving^base).volume(),'lower/motor',(moving^parts[side][motor]).volume(),'sleeve/base',(sv^base).volume(),'sleeve/motor',(sv^parts[side][motor]).volume(),flush=True)
 for distance in [12,8,4,2,1,.5,0]:
  a=cap.translate([0,0,distance]);print('CAP',side,distance,'base',(a^base).volume(),'lower',(a^parts[side][lower]).volume(),'sleeve',(a^sleeve).volume(),'motor',(a^parts[side][motor]).volume(),flush=True)
 foot=solid('foot' if side=='left' else 'right_foot',T);parts[side]['foot']=foot
 for label,q in [('base',base),('cap',cap)]:print('FOOT_PART',side,label,'added',( (q-old)^foot).volume(),'total',(q^foot).volume(),'components',len(mesh(q).split()),flush=True)
 Ry=Rotation.from_euler('x',-90,degrees=True).as_matrix();screws=mf.Manifold()
 for x,_ in LUGS:
  screw=mf.Manifold.cylinder(8,1,1,48).transform(np.c_[Ry,[x,-2,4.5]])+mf.Manifold.cylinder(1.72,2,2,48).transform(np.c_[Ry,[x,6,4.5]]);screws=screws+screw
  tool=mf.Manifold.cylinder(15,1.75,1.75,48).transform(np.c_[Ry,[x,7.72,4.5]])
  print('HEAD_FOOT',side,x,(screw^foot).volume(),'TOOL',sum((tool^p).volume() for p in [base,cap,parts[side][lower],parts[side][motor],foot]),flush=True)
 for ang in [-90,-75,-70,-60,-45,-30,0,30,45,60,70,75,90]:
  rot=Rotation.from_euler('z',ang,degrees=True).as_matrix();q=(base+cap).transform(np.c_[rot,[0,0,0]]);orig=old.transform(np.c_[rot,[0,0,0]]);extra=((base+cap)-old).transform(np.c_[rot,[0,0,0]]);sr=screws.transform(np.c_[rot,[0,0,0]])
  print('SWEEP',side,ang,'added/lower',(extra^parts[side][lower]).volume(),'added/motor',(extra^parts[side][motor]).volume(),'shaft/lower',(sr^parts[side][lower]).volume(),'shaft/motor',(sr^parts[side][motor]).volume(),'candidate/lower',(q^parts[side][lower]).volume(),'original/lower',(orig^parts[side][lower]).volume(),flush=True)
manifest['meshComponentCleanup']=cleanup
manifest['radialWingCorners']=corners;print('CORNERS',corners)
(R/'evidence/mesh-component-cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
(R/'preview-data.json').write_text(json.dumps(manifest,indent=2)+'\n')



from finalize_manifest import finalize
finalize(manifest)
