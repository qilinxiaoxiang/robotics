from pathlib import Path
import os,json,zipfile,xml.etree.ElementTree as E,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import trimesh as tm,numpy as np
D=Path(__file__).resolve().parent;R=D.parents[2];B=R.parent.parent;N='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';Q='{'+N+'}';E.register_namespace('',N)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bracket=R.parents[0]/'assembly/print-parts/community-24.stl'
spacer=D.parent/'neck-spacer-minimal/neck-M2-spacer-OD4-ID2p2-T1.stl'
a=tm.load(bracket,force='mesh');assert a.is_volume and a.is_watertight
b=tm.load(spacer,force='mesh');assert b.is_volume and b.is_watertight
# Source already uses print coordinates. Translation only; no rotation.
A=np.eye(4);A[:3,3]=[-a.bounds.mean(axis=0)[0],-a.bounds.mean(axis=0)[1],-a.bounds[0,2]];a.apply_transform(A)
y=128+a.extents[1]/2+10
placements=[('community_24',a,bracket,A,[128,128])]+[(f'neck_spacer_{i+1}',b,spacer,np.eye(4),[113+i*10,y]) for i in range(4)]
template=R/'printing/10-SURFACE-QUALITY-20261006/projects/Elegoo/black/MicroDuck_Elegoo_black_SURFACE_editable.3mf'
with zipfile.ZipFile(template) as z:cfg=json.loads(z.read('Metadata/project_settings.config'))
cfg['filament_colour']=['#202020'];cfg['filename_format']='Black_original_bracket_and_spacers.gcode'
root=E.Element(Q+'model',{'unit':'millimeter'});E.SubElement(root,Q+'metadata',{'name':'Application'}).text='OrcaSlicer-2.4.2';E.SubElement(root,Q+'metadata',{'name':'BambuStudio:3mfVersion'}).text='1'
resources=E.SubElement(root,Q+'resources');build=E.SubElement(root,Q+'build');settings=E.Element('config');plate=E.Element('plate')
for k,v in [('plater_id','1'),('plater_name','Black original bracket and four spacers'),('locked','false'),('bed_type',cfg['curr_bed_type'])]:E.SubElement(plate,'metadata',{'key':k,'value':v})
rows=[]
for i,(key,m,src,T,xy) in enumerate(placements,1):
 obj=E.SubElement(resources,Q+'object',{'id':str(i),'type':'model','name':key});mesh=E.SubElement(obj,Q+'mesh');vs=E.SubElement(mesh,Q+'vertices');fs=E.SubElement(mesh,Q+'triangles')
 for xyz in m.vertices:E.SubElement(vs,Q+'vertex',dict(zip(('x','y','z'),(format(float(x),'.17g') for x in xyz))))
 for f in m.faces:E.SubElement(fs,Q+'triangle',dict(zip(('v1','v2','v3'),map(str,f))))
 E.SubElement(build,Q+'item',{'objectid':str(i),'transform':f'1 0 0 0 1 0 0 0 1 {xy[0]} {xy[1]} 0','printable':'1'})
 so=E.SubElement(settings,'object',{'id':str(i)})
 for k,v in [('name',key),('extruder','1')]:E.SubElement(so,'metadata',{'key':k,'value':v})
 sp=E.SubElement(so,'part',{'id':str(i),'subtype':'normal_part'});E.SubElement(sp,'metadata',{'key':'name','value':key});E.SubElement(sp,'mesh_stat',{'face_count':str(len(m.faces)),'edges_fixed':'0','degenerate_facets':'0','facets_removed':'0','facets_reversed':'0','backwards_edges':'0'})
 ins=E.SubElement(plate,'model_instance')
 for k,v in [('object_id',str(i)),('instance_id','0'),('identify_id',str(2000+i))]:E.SubElement(ins,'metadata',{'key':k,'value':v})
 rows.append({'key':key,'source':str(src),'sourceSha256':sha(src),'dimensionsMm':m.extents.tolist(),'sourceToObjectTransform':T.tolist(),'placementXYMm':xy,'sourceGeometryUnchanged':True,'faces':len(m.faces)})
settings.append(plate);dest=D/'Black_editable.3mf'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
 z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
 z.writestr('3D/3dmodel.model',E.tostring(root));z.writestr('Metadata/model_settings.config',E.tostring(settings));z.writestr('Metadata/project_settings.config',json.dumps(cfg,indent=2))
report={'parts':rows,'projectSha256':sha(dest),'templateSha256':sha(template),'nativePending':True,'scope':'Standalone Black five-object plate; complete package released by parent only.'};(D/'plate-preparation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
