from pathlib import Path
import json,zipfile,hashlib,xml.etree.ElementTree as E
import numpy as np,trimesh as tm
D=Path(__file__).resolve().parent;V=D.parent;R=V.parent.parent;H=R/'head-redesign-20261008';N='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';Q='{'+N+'}';E.register_namespace('',N)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=V/'delivery-V1.3-Incremental/Black/Black_V1.3_editable.3mf';orient=H/'gpio-audio-repair/orientation-readonly-review/neck-integral-orientation.json';o=json.loads(orient.read_text());src=Path(o['sourceFrameMesh']);assert sha(src)==o['sourceFrameSha256'];m=tm.load(src,force='mesh',process=False);T=np.array(o['sourceFrameToPrintTransform']);m.apply_transform(T)
originalTriangles=m.vertices[m.faces].copy();originalVertexCount=len(m.vertices)
uniqueVertices,inverse=np.unique(m.vertices,axis=0,return_inverse=True)
m=tm.Trimesh(vertices=uniqueVertices,faces=inverse[m.faces],process=False)
assert np.array_equal(originalTriangles,m.vertices[m.faces])
assert m.is_watertight and m.is_winding_consistent
topology={'originalVertexCount':originalVertexCount,'sharedVertexCount':len(m.vertices),'triangleCoordinatesExactlyUnchanged':True,'watertight':True,'consistentWinding':True}
assert m.bounds[0,2]>-1e-4 and m.bounds[0,2]<1e-4
with zipfile.ZipFile(p)as z:members={n:z.read(n)for n in z.namelist()}
root=E.fromstring(members['3D/3dmodel.model']);res=root.find(Q+'resources');build=root.find(Q+'build');settings=E.fromstring(members['Metadata/model_settings.config']);removed={'4','5','6','7'}
for r in list(res):
 if r.get('id')in removed:res.remove(r)
for r in list(build):
 if r.get('objectid')in removed:build.remove(r)
 if r.get('objectid')=='2':r.set('transform','1 0 0 0 -1 0 0 0 -1 104 145.55 2.4')
for r in list(settings):
 if r.tag=='object' and r.get('id')in removed:settings.remove(r)
plate=settings.find('plate')
for r in list(plate):
 if r.tag=='model_instance'and r.find("metadata[@key='object_id']").get('value')in removed:plate.remove(r)
id='12';obj=E.SubElement(res,Q+'object',{'id':id,'type':'model','name':'neck_pitch_integral'});mesh=E.SubElement(obj,Q+'mesh');verts=E.SubElement(mesh,Q+'vertices');faces=E.SubElement(mesh,Q+'triangles')
for v in m.vertices:E.SubElement(verts,Q+'vertex',dict(zip(['x','y','z'],[format(float(x),'.12g')for x in v])))
for f in m.faces:E.SubElement(faces,Q+'triangle',dict(zip(['v1','v2','v3'],map(str,f))))
# Replace now-free four-spacer row with one original-orientation neck support.
E.SubElement(build,Q+'item',{'objectid':id,'transform':'1 0 0 0 1 0 0 0 1 128 216.85 0','printable':'1'})
so=E.SubElement(settings,'object',{'id':id});E.SubElement(so,'metadata',{'key':'name','value':'neck_pitch_integral'});E.SubElement(so,'metadata',{'key':'extruder','value':'1'});sp=E.SubElement(so,'part',{'id':id,'subtype':'normal_part'});E.SubElement(sp,'metadata',{'key':'name','value':'neck_pitch_integral'});E.SubElement(sp,'mesh_stat',{'face_count':str(len(m.faces)),'edges_fixed':'0','degenerate_facets':'0','facets_removed':'0','facets_reversed':'0','backwards_edges':'0'})
ins=E.SubElement(plate,'model_instance')
for k,v in [('object_id',id),('instance_id','0'),('identify_id','2012')]:E.SubElement(ins,'metadata',{'key':k,'value':v})
objects={x.get('id'):x for x in res};bounds=[]
for i in build:
 a=np.array(list(map(float,i.get('transform').split()))).reshape(4,3).T;v=np.array([[float(x.get(k))for k in ['x','y','z']]for x in objects[i.get('objectid')].findall('.//'+Q+'vertex')]);w=v@a[:,:3].T+a[:,3];bb=[w.min(0).tolist(),w.max(0).tolist()];assert np.min(w[:,:2])>18 and np.max(w[:,:2])<248;assert w[:,2].min()>-1e-4;bounds.append({'id':i.get('objectid'),'name':objects[i.get('objectid')].get('name'),'bounds':bb})
assert len(bounds)==8
members['3D/3dmodel.model']=E.tostring(root,encoding='utf-8',xml_declaration=True);members['Metadata/model_settings.config']=E.tostring(settings,encoding='utf-8',xml_declaration=True)
out=D/'Black_V1.4_base.3mf'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)as z:
 for n,b in members.items():z.writestr(n,b)
(D/'black-v14-change.json').write_text(json.dumps({'source':str(p),'sourceSha256':sha(p),'neckSource':str(src),'neckSourceSha256':sha(src),'orientationEvidence':str(orient),'orientationEvidenceSha256':sha(orient),'neckTransform':T.tolist(),'neckTopology':topology,'removedObjectIds':sorted(removed),'cameraRetainerFlip':'1 0 0 0 -1 0 0 0 -1 104 145.55 2.4','bounds':bounds,'objects':8,'output':str(out),'outputSha256':sha(out)},indent=2)+'\n');print('BLACK8 READY',bounds[-1])
