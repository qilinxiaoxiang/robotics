from pathlib import Path
import os,json,math,hashlib,zipfile,xml.etree.ElementTree as E
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
n=128;r=1.1/math.cos(math.pi/n)
v=[[rad*math.cos(2*math.pi*i/n),rad*math.sin(2*math.pi*i/n),z] for z in (0,1) for rad in (2,r) for i in range(n)]
f=[]
for i in range(n):
 j=(i+1)%n
 for a,b,c,d in [(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)]:f.extend([(a,b,c),(a,c,d)])
m=tm.Trimesh(vertices=v,faces=f);m.invert()
assert m.is_watertight and m.is_volume
solid=mf.Manifold(mf.Mesh64(np.asarray(m.vertices),np.asarray(m.faces,dtype=np.uint64)))
assert solid.status()==mf.Error.NoError and solid.volume()>0
stl=D/'neck-M2-spacer-OD4-ID2p2-T1.stl';stl.write_text(tm.exchange.stl.export_stl_ascii(m))
a=tm.load(stl,force='mesh');assert a.is_watertight and a.is_volume
N='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';Q='{'+N+'}';E.register_namespace('',N)
template=R/'printing/10-SURFACE-QUALITY-20261006/projects/Elegoo/black/MicroDuck_Elegoo_black_SURFACE_editable.3mf'
with zipfile.ZipFile(template) as z:cfg=json.loads(z.read('Metadata/project_settings.config'))
assert float(cfg['layer_height'])==.2
cfg['filament_colour']=['#202020'];cfg['filename_format']='Neck_spacer_diagnostic.gcode'
root=E.Element(Q+'model',{'unit':'millimeter'});E.SubElement(root,Q+'metadata',{'name':'Application'}).text='OrcaSlicer-2.4.2';E.SubElement(root,Q+'metadata',{'name':'BambuStudio:3mfVersion'}).text='1'
resources=E.SubElement(root,Q+'resources');build=E.SubElement(root,Q+'build');settings=E.Element('config');plate=E.Element('plate')
for k,val in [('plater_id','1'),('plater_name','Black spacer diagnostic'),('locked','false'),('bed_type',cfg['curr_bed_type'])]:E.SubElement(plate,'metadata',{'key':k,'value':val})
positions=[[123,123],[133,123],[123,133],[133,133]]
for i,(cx,cy) in enumerate(positions,1):
 name=f'neck_spacer_{i}';obj=E.SubElement(resources,Q+'object',{'id':str(i),'type':'model','name':name});mesh=E.SubElement(obj,Q+'mesh');vs=E.SubElement(mesh,Q+'vertices');fs=E.SubElement(mesh,Q+'triangles')
 for xyz in a.vertices:E.SubElement(vs,Q+'vertex',dict(zip(('x','y','z'),(format(float(x),'.17g') for x in xyz))))
 for face in a.faces:E.SubElement(fs,Q+'triangle',dict(zip(('v1','v2','v3'),map(str,face))))
 E.SubElement(build,Q+'item',{'objectid':str(i),'transform':f'1 0 0 0 1 0 0 0 1 {cx} {cy} 0','printable':'1'})
 so=E.SubElement(settings,'object',{'id':str(i)})
 for k,val in [('name',name),('extruder','1')]:E.SubElement(so,'metadata',{'key':k,'value':val})
 sp=E.SubElement(so,'part',{'id':str(i),'subtype':'normal_part'});E.SubElement(sp,'metadata',{'key':'name','value':name});E.SubElement(sp,'mesh_stat',{'face_count':str(len(a.faces)),'edges_fixed':'0','degenerate_facets':'0','facets_removed':'0','facets_reversed':'0','backwards_edges':'0'})
 ins=E.SubElement(plate,'model_instance')
 for k,val in [('object_id',str(i)),('instance_id','0'),('identify_id',str(2000+i))]:E.SubElement(ins,'metadata',{'key':k,'value':val})
settings.append(plate)
project=D/'Neck_spacers_editable.3mf'
with zipfile.ZipFile(project,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
 z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
 z.writestr('3D/3dmodel.model',E.tostring(root));z.writestr('Metadata/model_settings.config',E.tostring(settings));z.writestr('Metadata/project_settings.config',json.dumps(cfg,indent=2))
report={'passed':True,'quantity':4,'color':'Black','outerDiameterMaxMm':4,'holeInscribedDiameterMm':2.2,'thicknessMm':1,'facetsAround':n,'volumeMm3':a.volume,'watertight':bool(a.is_watertight),'positiveVolume':bool(a.is_volume),'manifoldStatus':str(solid.status()),'source':str(stl),'sourceSha256':sha(stl),'project':str(project),'projectSha256':sha(project),'templateSha256':sha(template),'printRotationMatrix':np.eye(3).tolist(),'positionsXYMm':positions,'boundaries':['No physical tolerance or available metal washer stock claim.','Independent spacer preserves original neck_pitch.','Native slice is diagnostic; combine four copies into final Black plate.']}
(D/'geometry-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
