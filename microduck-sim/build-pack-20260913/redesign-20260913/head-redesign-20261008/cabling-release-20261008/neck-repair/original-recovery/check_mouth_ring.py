"""Finite original-interface check; one separate ring, no support/jaw modification."""
import sys,json,base64,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;sys.path.insert(0,str(D.parent));import short_path_worker as c;c.guard()
import numpy as np,trimesh,manifold3d as mf
H=D.parents[2];CACHE=H/'usb-access/usb-repair/robot-source-cache';idx=json.loads((CACHE/'index.json').read_text());inputs=[Path(__file__),D/'source-export.json',CACHE/'index.json']
def cv(m):
 s=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)));assert s.status()==mf.Error.NoError and s.volume()>0
 t=s.to_mesh64();r=trimesh.Trimesh(t.vert_properties[:,:3],t.tri_verts,process=False);assert r.is_watertight and r.is_volume;return s
def stl(n):
 p=D/n;inputs.append(p);return cv(trimesh.load(p,force='mesh'))
def source(k):
 p=CACHE/idx['parts'][k];inputs.append(p);j=json.loads(p.read_text());return cv(trimesh.Trimesh(np.frombuffer(base64.b64decode(j['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(j['indexB64']),'<u4').reshape(-1,3),process=True))
def ring(id,od,t,y):
 s=mf.Manifold.cylinder(t,od/2,od/2,128)-mf.Manifold.cylinder(t+.2,id/2,id/2,128).translate([0,0,-.1]);return s.rotate([-90,0,0]).translate([26.1,y,118.6146])
S=stl('original-support-world.stl');J=stl('original-jaw_frame-world.stl');P=stl('original-lower_pad-world.stl');M=source('motor15');B=source('head_bottom');V=cv(trimesh.load(H/'camera-ribbon-repair/positive-x225/head_bottom_x225_receiver-world.stl',force='mesh'));inputs.append(H/'camera-ribbon-repair/positive-x225/head_bottom_x225_receiver-world.stl');R=ring(10.4,14.6,2.6,-39.65);stock=ring(9.65,14.6,3,-40)
report={'accepted':False,'ringDimensionsMm':{'inner':10.4,'outer':14.6,'thickness':2.6,'axis':'world +Y','seatStart':[26.1,-39.65,118.6146]},'sourceStockNegative':{'approximateSourceRingID':9.65,'intersectionJawMm3':(stock^J).volume()},'static':{},'routes':{}}
for k,s in [('support',S),('jaw',J),('pad',P),('motor15',M),('head_bottom',B),('head_bottom_v1',V)]:
 it=R^s;report['static'][k]={'volumeMm3':it.volume(),'gapSearch2Mm':R.min_gap(s,2)}
def scan(name,moving,fixed,v):
 rows=[];maxes={}
 for f in np.linspace(1,0,121):
  offset=np.array(v)*f;hits={}
  for k,s in moving.items():
   for q,b in fixed.items():
    it=s.translate(offset)^b;vol=it.volume();assert it.status()==mf.Error.NoError
    if vol>1e-7:hits[k+'--'+q]=vol;maxes[k+'--'+q]=max(maxes.get(k+'--'+q,0),vol)
  if hits:rows.append({'fraction':float(f),'hits':hits})
 report['routes'][name]={'expected':121,'completed':121,'start':v,'peakMm3':maxes,'firstHits':rows[:3]}
scan('ring_over_loose_jaw_boss',{'ring':R},{'jaw':J},[0,30,0])
scan('jaw_ring_motor_pad_into_original_loose_support',{'jaw':J,'ring':R,'motor15':M,'pad':P},{'support':S},[0,0,-30])
scan('jaw_ring_without_pad_into_shell',{'jaw':J,'ring':R},{'head_bottom':B},[0,0,-30])
m=R.to_mesh64();mesh=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);assert mesh.is_watertight and mesh.is_volume;p=D/'mouth-sliding-ring-world.stl';p.write_text(trimesh.exchange.stl.export_stl_ascii(mesh));read=trimesh.load(p,force='mesh');assert read.is_watertight and read.is_volume;report['export']={'world':str(p),'sha256':c.sha(p),'singleClosedBody':len(read.split())==1}
pr=ring(10.4,14.6,2.6,-39.65).translate([-26.1,39.65,-118.6146]).rotate([90,0,0]);m=pr.to_mesh64();mesh=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);p=D/'mouth-sliding-ring-print.stl';p.write_text(trimesh.exchange.stl.export_stl_ascii(mesh));report['export']['print']=str(p);report['export']['printSha256']=c.sha(p)
report['sourceHashes']={str(p.resolve()):c.sha(p) for p in inputs};c.save(D/'mouth-ring-probe.json',report);print(json.dumps({k:v for k,v in report.items() if k!='sourceHashes'}))
