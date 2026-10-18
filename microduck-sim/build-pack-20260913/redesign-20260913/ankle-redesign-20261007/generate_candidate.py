from pathlib import Path
import json,base64,hashlib,numpy as np,trimesh,manifold3d as mf
from scipy.spatial.transform import Rotation
import cadquery as cq
R=Path(__file__).resolve().parent;G=R.parent/'leg-guide-20261006';SIM=R.parents[2];D=json.loads((G/'full-build-data.json').read_text());ROWS={p['key']:p for p in D['parts']}
for p in ['STL','CAD','evidence']: (R/p).mkdir(exist_ok=True)
SPLIT=-1.6;LUGS=[[-12.,2.],[12.,2.]];PEGS=[]
def solid(key,T):
 p=ROWS[key];m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),dtype='<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),dtype='<u4').reshape(-1,3),process=True).apply_transform(np.linalg.inv(T));a=mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)));assert a.status()==mf.Error.NoError;return a

def cyl(r,z0,z1,xy=(0,0)):
 return mf.Manifold.cylinder(z1-z0,r,r,96).translate([*xy,z0])
def box_z(z0,z1):return mf.Manifold.cube([200,200,z1-z0]).translate([-100,-100,z0])
def mesh(a):
 m=a.to_mesh();return trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=True)
def export(a,key,T):
 m=mesh(a);p=R/'STL'/f'{key}-local.stl';m.export(p);w=m.copy().apply_transform(T);p=R/'STL'/f'{key}-world.stl';w.export(p);return str(p)
cleanup=[]
def clean(a,key):
 cs=a.decompose();big=[c for c in cs if c.volume()>1e-5];assert len(big)==1,(key,[c.volume() for c in cs]);tiny=[c for c in cs if c.volume()<=1e-5];cleanup.append({'part':key,'inputComponents':len(cs),'outputComponents':1,'discardedVolumeMm3':sum(max(0.,c.volume()) for c in tiny),'discardedTriangles':sum(c.num_tri() for c in tiny),'thresholdMm3':1e-5});return big[0]
frames={};parts={};manifest={'schemaVersion':1,'prototypeOnly':True,'sourceOverwrite':False,'sides':{}}
for side,ankle,lower,motor,ring in [('left','ankle','lower','motor6','smallring'),('right','right_ankle','right_lower','motor1','right_smallring')]:
 sign=1 if side=='left' else -1;T=np.eye(4);T[:3,:3]=np.array([[sign,0,0],[0,0,-sign],[0,1,0]]);T[:3,3]=[-31.7771,sign*33.8,-81.5];frames[side]=T
 old=solid(ankle,T);parts[side]={k:solid(k,T) for k in [ankle,lower,motor,ring]}
 originalBase=old^box_z(-100,SPLIT);originalCap=old^box_z(SPLIT,3.)
 wings=old^(mf.Manifold.cube([100,200,200]).translate([11,-100,-100])+mf.Manifold.cube([100,200,200]).translate([-111,-100,-100]));wings=wings^box_z(SPLIT,3.)
 base=originalBase+wings;cap=originalCap-wings
 for x,_ in LUGS:
  post=mf.Manifold.cube([4,6.5,5.45]).translate([x-2,-4.5,1.65]);base=base+post
  # A continuous open-top channel permits axial cap approach.
  slot=mf.Manifold.cube([2.2,.55,100]).translate([x-1.1,1.5,1.65]);base=base-slot
  cap=cap-mf.Manifold.cube([4.2,6.6,100]).translate([x-2.1,-4.55,-50])
  tab=mf.Manifold.cube([7,4,5.45]).translate([x-4,2.,1.65]) if x>0 else mf.Manifold.cube([7,4,5.45]).translate([x-3,2.,1.65])
  tongue=mf.Manifold.cube([2,.4,5.45]).translate([x-1,1.6,1.65]);cap=cap+tab+tongue
  # Transverse Y clearance and blind TAP pilot; no shaft enters case/lower axial slab.
  Ry=Rotation.from_euler('x',-90,degrees=True).as_matrix()
  pilot=mf.Manifold.cylinder(4.2,.8,.8,96).transform(np.c_[Ry,[x,-2.5,4.5]])
  clearance=mf.Manifold.cylinder(4.55,1.15,1.15,96).transform(np.c_[Ry,[x,1.5,4.5]])
  base=base-pilot;cap=cap-clearance
 base=clean(base,side+'-base');cap=clean(cap,side+'-cheek')
 assert base.status()==mf.Error.NoError and cap.status()==mf.Error.NoError
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
(R/'evidence/mesh-component-cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
(R/'preview-data.json').write_text(json.dumps(manifest,indent=2)+'\n')



from finalize_manifest import finalize
finalize(manifest)
