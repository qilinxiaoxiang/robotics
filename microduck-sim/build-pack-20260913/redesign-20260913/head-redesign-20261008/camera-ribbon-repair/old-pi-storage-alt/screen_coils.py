from pathlib import Path
import os;assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import json,hashlib,math,gc
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;C=D.parent;H=C.parent
manifest=json.loads((C/'positive-x225/candidate-manifest.json').read_text());files=manifest['replacementMeshes']|{x['key']:x['mesh'] for x in manifest['additionalParts']};hashes={};rows=[]
keys=['head_cap','pi','zero_w_components','zero_w_gpio_solder_tails','zero_w_gpio_male_receiving','amplifier','camera_board','camera_retainer','face_panel']+[x for x in files if x.startswith('gpio_pin_')]
# Existing source-complete conservative OpenRB enclosure is a valid negative separator; a hit is inconclusive.
files['openrb_conservative']='usb-access/usb-repair/openrb-conservative-convex-obstacle.stl';keys+=['openrb_conservative'];obstacles={}
for key in keys:
 if key not in files:continue
 p=H/files[key];hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();m=trimesh.load(p,force='mesh');assert m.is_watertight,(key,str(p));o=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)));assert o.status()==mf.Error.NoError;obstacles[key]=(o,np.array(o.bounding_box()).reshape(2,3));del m

def curve(theta,pitch):
 b=pitch/(2*math.pi);rx=3.4+b*theta;rz=3.25+b*theta;co=np.cos(theta);si=np.sin(theta)
 p=np.column_stack([rx*co,rz*si]);v=np.column_stack([b*co-rx*si,b*si+rz*co]);a=np.column_stack([-2*b*si-rx*co,2*b*co-rz*si]);speed=np.linalg.norm(v,axis=1);radius=speed**3/np.abs(v[:,0]*a[:,1]-v[:,1]*a[:,0]);return p,v,speed,radius
for thick in [.6,.3]:
 pitch=thick+.3
 for length in [80.,100.,130.]:
  lo,hi=0.,14*math.pi
  for j in range(40):
   end=(lo+hi)/2;ts=np.linspace(0,end,1601);_,_,sp,_=curve(ts,pitch);L=float(np.trapezoid(sp,ts))
   if L<length:lo=end
   else:hi=end
  end=(lo+hi)/2;ts=np.linspace(0,end,math.ceil(length/.15)+1);p,v,sp,radii=curve(ts,pitch);n=np.column_stack([-v[:,1],v[:,0]]);n/=np.linalg.norm(n,axis=1)[:,None]
  for cx,cz in [(59.5,124.),(60.5,123.5)]:
   verts=[]
   # 4 vertices per section, oriented rectangular width16 alongY and actual thickness along planar normal.
   for pt,nn in zip(p,n):
    for yy,sgn in [(-20,-1),(-4,-1),(-4,1),(-20,1)]:verts.append([cx+pt[0]+sgn*thick/2*nn[0],yy,cz+pt[1]+sgn*thick/2*nn[1]])
   faces=[]
   for i in range(len(ts)-1):
    for j in range(4):
     a=i*4+j;b=i*4+(j+1)%4;c=b+4;d=a+4;faces.extend([[a,b,c],[a,c,d]])
   faces.extend([[0,2,1],[0,3,2]]);a=(len(ts)-1)*4;faces.extend([[a,a+1,a+2],[a,a+2,a+3]])
   mesh=trimesh.Trimesh(verts,faces,process=True);trimesh.repair.fix_normals(mesh);assert mesh.is_watertight;solid=mf.Manifold(mf.Mesh64(np.array(mesh.vertices,np.float64),np.array(mesh.faces,np.uint64)));assert solid.status()==mf.Error.NoError;bb=np.array(solid.bounding_box()).reshape(2,3);hits={}
   for key,(ob,b) in obstacles.items():
    if np.any(bb[0]>=b[1]) or np.any(b[0]>=bb[1]):continue
    inter=solid^ob;vol=max(0.,float(inter.volume()))
    if vol>1e-6:hits[key]={'overlapMm3':vol,'bounds':inter.bounding_box(),'conservativeOnly':key=='openrb_conservative'}
   row={'thicknessMm':thick,'sensitivityOnly':thick!=.6,'lengthStoredMm':length,'turns':end/(2*math.pi),'pitchMm':pitch,'centerXZM': [cx,cz],'minimumSampledRadiusMm':float(min(radii)),'materialLengthNumericalMm':float(np.trapezoid(sp,ts)),'bounds':solid.bounding_box(),'hits':hits,'centerline':np.column_stack([cx+p[:,0],np.full(len(p),-12),cz+p[:,1]]).tolist()};rows.append(row)
   if not any(not h['conservativeOnly'] for h in hits.values()):
    out=D/f'coil-{thick}-{length}-{cx}.stl';mesh.export(out);row['mesh']=str(out);row['meshSha256']=hashlib.sha256(out.read_bytes()).hexdigest()
   del solid,mesh;gc.collect();(D/'coil-screen.json').write_text(json.dumps({'integrationReady':False,'widthMm':16,'sourceHashes':hashes,'candidateBudget':12,'rows':rows,'scope':'True developable elliptical spiral, storage only. No hidden shrink or rigid-body end twist. Leads to/from inner spiral end, self-clearance, reinforcement and exactly200mm entire cable still required; storage clearance alone is not a complete route.'},indent=2)+'\n');print(len(rows),thick,length,cx,{k:round(v['overlapMm3'],3) for k,v in hits.items()},flush=True)
