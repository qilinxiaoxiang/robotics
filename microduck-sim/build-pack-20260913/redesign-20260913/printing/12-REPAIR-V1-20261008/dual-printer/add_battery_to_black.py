from pathlib import Path
import sys,json,zipfile,hashlib,xml.etree.ElementTree as E
import numpy as np,trimesh as tm
D=Path(__file__).resolve().parent;src=Path(sys.argv[1]).resolve();m=tm.load(src,force='mesh',process=False);sourceBounds=m.bounds.copy();angle=0
# Input must already have its intended planar manufacturing base horizontal.
if np.ptp(m.vertices[:,0])>60 and np.ptp(m.vertices[:,1])<=60:
 T=np.array([[0,-1,0,0],[1,0,0,0],[0,0,1,0],[0,0,0,1]],float);m.apply_transform(T);angle=90
else:T=np.eye(4)
b=m.bounds;assert b[1,0]-b[0,0]<=60 and b[1,1]-b[0,1]<=150,b
shift=np.array([-(b[0,0]+b[1,0])/2,-(b[0,1]+b[1,1])/2,-b[0,2]]);m.vertices+=shift;T[:3,3]+=shift
v,inv=np.unique(m.vertices,axis=0,return_inverse=True);f=inv[m.faces];m=tm.Trimesh(v,f,process=False);assert m.is_watertight and m.is_winding_consistent
Q='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}';E.register_namespace('',Q[1:-1]);base=D/'Black_V1.4_base.3mf'
with zipfile.ZipFile(base)as z:data={n:z.read(n)for n in z.namelist()}
r=E.fromstring(data['3D/3dmodel.model']);res=r.find(Q+'resources');assert all(o.get('id')!='13'for o in res);obj=E.SubElement(res,Q+'object',{'id':'13','name':'battery_rear_carrier','type':'model'});mesh=E.SubElement(obj,Q+'mesh');verts=E.SubElement(mesh,Q+'vertices');faces=E.SubElement(mesh,Q+'triangles')
for vv in v:E.SubElement(verts,Q+'vertex',dict(zip(['x','y','z'],[format(float(x),'.15g')for x in vv])))
for ff in f:E.SubElement(faces,Q+'triangle',dict(zip(['v1','v2','v3'],map(str,ff))))
E.SubElement(r.find(Q+'build'),Q+'item',{'objectid':'13','transform':'1 0 0 0 1 0 0 0 1 208 95 0','printable':'1'})
s=E.fromstring(data['Metadata/model_settings.config']);o=E.SubElement(s,'object',{'id':'13'});E.SubElement(o,'metadata',{'key':'name','value':'battery_rear_carrier'});E.SubElement(o,'metadata',{'key':'extruder','value':'1'});p=E.SubElement(o,'part',{'id':'13','subtype':'normal_part'});E.SubElement(p,'metadata',{'key':'name','value':'battery_rear_carrier'});E.SubElement(p,'mesh_stat',{'face_count':str(len(f)),'edges_fixed':'0','degenerate_facets':'0','facets_removed':'0','facets_reversed':'0','backwards_edges':'0'});i=E.SubElement(s.find('plate'),'model_instance')
for k,val in [('object_id','13'),('instance_id','0'),('identify_id','2013')]:E.SubElement(i,'metadata',{'key':k,'value':val})
data['3D/3dmodel.model']=E.tostring(r,encoding='utf-8',xml_declaration=True);data['Metadata/model_settings.config']=E.tostring(s,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(base,'w',zipfile.ZIP_DEFLATED)as z:
 for n,b in data.items():z.writestr(n,b)
report={'source':str(src),'sourceSha256':hashlib.sha256(src.read_bytes()).hexdigest(),'sourceBounds':sourceBounds.tolist(),'inPlaneRotationDegrees':angle,'sourceToObject':T.tolist(),'buildTranslation':[208,95,0],'bounds':(m.bounds+np.array([208,95,0])).tolist(),'watertight':bool(m.is_watertight),'faces':len(f),'objects':9,'output':str(base),'outputSha256':hashlib.sha256(base.read_bytes()).hexdigest()};(D/'battery-addition.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
