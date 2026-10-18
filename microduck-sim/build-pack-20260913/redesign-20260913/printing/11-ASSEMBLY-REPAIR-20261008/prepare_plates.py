"""Prepare color plates from explicit frozen meshes and retained printer profiles.

This staging builder does not release incomplete plates or start a printer.
Transforms are proper rigid rotations/translations only. Native slicing follows.
"""
from pathlib import Path
import hashlib,json,os,zipfile,xml.etree.ElementTree as E
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm
D=Path(__file__).resolve().parent;R=D.parent.parent;SIM=R.parents[1]
N='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';Q='{'+N+'}'
E.register_namespace('',N)
source=SIM/'Microduck-build-tutorial/microduck3D打印.3mf'
with zipfile.ZipFile(source) as z:original=E.fromstring(z.read('3D/3dmodel.model'))
def transform(s):
    m=np.eye(4);m[:3,:]=np.array(list(map(float,s.split()))).reshape(4,3).T;return m
original_build={i.get('objectid'):transform(i.get('transform')) for i in original.find(Q+'build')}
prep=json.loads((D/'preparation.json').read_text());cache=R/'head-redesign-20261008/usb-access/usb-repair/robot-source-cache'
blockers={}
if prep.get('supportBlockerManifest'):
    bpath=R/prep['supportBlockerManifest'];bdata=json.loads(bpath.read_text())
    for b in bdata['blockers']:blockers.setdefault(b['owner'],[]).append(b)
colors={'Yellow':'#FFFF00','White':'#FFFFFF','Orange':'#FF8000','Black':'#202020'}
all_rows=[]
for color in colors:
    parts=[p for p in prep['frozenGeometry'] if p['color']==color]
    if not parts:continue
    machine='Bambu' if color in ('Yellow','White') else 'Elegoo';group='WHITE' if color=='White' else color.lower()
    template=D.parent/'10-SURFACE-QUALITY-20261006/projects'/machine/group/f'MicroDuck_{machine}_{group}_SURFACE_editable.3mf'
    with zipfile.ZipFile(template) as z:cfg=json.loads(z.read('Metadata/project_settings.config'))
    assert cfg['nozzle_diameter']==['0.4'] and cfg['filament_type']==['PLA']
    assert cfg['filament_ids'] and all(cfg['filament_ids'])
    cfg['filament_colour']=[colors[color]];cfg['filename_format']=f'MicroDuck_{color}_ASSEMBLY.gcode'
    root=E.Element(Q+'model',{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'en-US'})
    E.SubElement(root,Q+'metadata',{'name':'Application'}).text='BambuStudio-02.08.02.61' if machine=='Bambu' else 'OrcaSlicer-2.4.2'
    E.SubElement(root,Q+'metadata',{'name':'BambuStudio:3mfVersion'}).text='1'
    resources=E.SubElement(root,Q+'resources');build=E.SubElement(root,Q+'build');settings=E.Element('config')
    plate=E.Element('plate')
    for k,v in [('plater_id','1'),('plater_name',color+' assembly repair'),('locked','false'),('bed_type',cfg['curr_bed_type'])]:E.SubElement(plate,'metadata',{'key':k,'value':v})
    prepared=[]
    for i,part in enumerate(parts,1):
        f=R/part['source'];m=tm.load(f,force='mesh');assert m.is_watertight and m.is_volume
        key=part.get('orientationSourceKey', 'jaw_frame' if part['key']=='jaw_passive_cheek' else part['key'])
        if 'printRotationMatrix' in part:
            T=np.eye(4);T[:3,:3]=np.asarray(part['printRotationMatrix'])
        else:
            item=json.loads((cache/(key+'.json')).read_text())
            T=original_build[str(item['sourceId'])]@np.linalg.inv(item['sourceTransformWorld'])
        if part['key']=='jaw_passive_cheek':
            # The split cheek is a new part. Put its passive bearing axis
            # vertical and its inner capture surface upward, not on a tiny
            # curved edge inherited from the unsplit jaw's print orientation.
            T=tm.geometry.align_vectors([0,-1,0],[0,0,-1])
        # Preserve the source print orientation, then lay its actual lower
        # plane flat instead of only dropping a tilted part to the bed.
        T[:3,3]=0;v=m.copy().apply_transform(T)
        normals=np.asarray(v.face_normals);centers=v.triangles_center
        low=centers[:,2]<=v.bounds[0,2]+1.0
        candidates=np.flatnonzero(low & (normals[:,2]<-.98))
        adjustment=np.eye(4)
        if len(candidates):
            groups={}
            for j in candidates:
                normal=tuple(np.round(normals[j],5));groups[normal]=groups.get(normal,0)+v.area_faces[j]
            selected=np.array(max(groups,key=groups.get));selected/=np.linalg.norm(selected)
            adjustment=tm.geometry.align_vectors(selected,[0,0,-1]);T=adjustment@T;v=m.copy().apply_transform(T)
        assert np.allclose(T[:3,:3].T@T[:3,:3],np.eye(3),atol=2e-7) and np.linalg.det(T[:3,:3])>.999999
        T[:3,3]=[-v.bounds.mean(axis=0)[0],-v.bounds.mean(axis=0)[1],-v.bounds[0,2]]
        v=m.copy().apply_transform(T)
        flat=np.all(v.triangles[:,:,2]<.01,axis=1)
        record={**part,'sourceSha256':hashlib.sha256(f.read_bytes()).hexdigest(),'printTransform':T.tolist(),
                'dimensionsMm':v.extents.tolist(),'planarBedContactAreaMm2':float(v.area_faces[flat].sum()),
                'orientationBoundary':'Retained original source print orientation with actual near-bed planar face aligned. Native support/functional-face check remains required.',
                'geometryChanged':False,'sourceVolumeMm3':float(m.volume),'preparedVolumeMm3':float(v.volume)}
        assert abs(m.volume-v.volume)<max(1e-4,m.volume*1e-6)
        prepared.append((i,v,record))
    # Bounded shelf packing: retain each functional print orientation. Evaluate
    # a small finite set of shelf widths rather than placing a long single row.
    layouts=[]
    for available in range(110,231,5):
        rows=[];row=[];used=0.;rowheight=0.
        for i,m,record in sorted(prepared,key=lambda a:-a[1].extents[1]):
            w,h=m.extents[:2]
            if w>available:break
            if row and used+18+w>available:
                rows.append((row,used,rowheight));row=[];used=0.;rowheight=0.
            row.append((i,used+(18 if row else 0)+w/2))
            used+=w+(18 if len(row)>1 else 0);rowheight=max(rowheight,h)
        else:
            if row:rows.append((row,used,rowheight))
            totalheight=sum(r[2] for r in rows)+18*(len(rows)-1)
            if totalheight<=230:
                layouts.append((max(r[1] for r in rows)*totalheight,rows,totalheight))
    assert layouts,'Parts need an additional plate; never overflow the bed'
    _,rows,totalheight=min(layouts,key=lambda a:a[0]);positions={};bottom=128-totalheight/2
    for row,width,height in rows:
        for oid,x in row:positions[oid]=(128-width/2+x,bottom+height/2)
        bottom+=height+18
    shift=prep.get('nativeMaterialCenterCorrectionMm',{}).get(color,[0,0])
    for i,m,record in prepared:
        cx,cy=positions[i];cx+=shift[0];cy+=shift[1]
        obj=E.SubElement(resources,Q+'object',{'id':str(i),'type':'model','name':record['key']})
        volumes=[(m,record['key'],'normal_part',None)]
        for blocker in blockers.get(record['key'],[]):
            spec=blocker['meshFrames']['world'];bf=Path(spec['path'])
            assert hashlib.sha256(bf.read_bytes()).hexdigest()==spec['sha256']
            bm=tm.load(bf,force='mesh');assert bm.is_watertight
            bm.apply_transform(record['printTransform'])
            volumes.append((bm,blocker['name'],'support_blocker',spec))
        def addmesh(parent,model):
            mesh=E.SubElement(parent,Q+'mesh');verts=E.SubElement(mesh,Q+'vertices');faces=E.SubElement(mesh,Q+'triangles')
            for xyz in model.vertices:E.SubElement(verts,Q+'vertex',dict(zip(('x','y','z'),(format(float(x),'.12g') for x in xyz))))
            for face in model.faces:E.SubElement(faces,Q+'triangle',dict(zip(('v1','v2','v3'),map(str,face))))
        if len(volumes)>1:
            components=E.SubElement(obj,Q+'components');volume_ids=[]
            for j,(model,name,subtype,spec) in enumerate(volumes):
                vid=10000+i*100+j;volume_ids.append(vid)
                child=E.SubElement(resources,Q+'object',{'id':str(vid),'type':'model','name':name});addmesh(child,model)
                E.SubElement(components,Q+'component',{'objectid':str(vid),'transform':'1 0 0 0 1 0 0 0 1 0 0 0'})
        else:addmesh(obj,m);volume_ids=[i]
        E.SubElement(build,Q+'item',{'objectid':str(i),'transform':f'1 0 0 0 1 0 0 0 1 {cx:.9f} {cy:.9f} 0','printable':'1'})
        so=E.SubElement(settings,'object',{'id':str(i)})
        for k,v in [('name',record['key']),('extruder','1')]:E.SubElement(so,'metadata',{'key':k,'value':v})
        E.SubElement(so,'metadata',{'face_count':str(len(m.faces))})
        for vid,(model,name,subtype,spec) in zip(volume_ids,volumes):
            sp=E.SubElement(so,'part',{'id':str(vid),'subtype':subtype});E.SubElement(sp,'metadata',{'key':'name','value':name})
            E.SubElement(sp,'mesh_stat',{'face_count':str(len(model.faces)),'edges_fixed':'0','degenerate_facets':'0','facets_removed':'0','facets_reversed':'0','backwards_edges':'0'})
        record['supportBlockers']=[{'name':name,'subtype':subtype,'source':spec} for _,name,subtype,spec in volumes[1:]]
        inst=E.SubElement(plate,'model_instance')
        for k,v in [('object_id',str(i)),('instance_id','0'),('identify_id',str(2000+i))]:E.SubElement(inst,'metadata',{'key':k,'value':v})
        record['placementXYMm']=[cx,cy];all_rows.append(record)
    settings.append(plate)
    dest=D/'staging-projects'/f'MicroDuck_{machine}_{color}_ASSEMBLY_editable.3mf';dest.parent.mkdir(exist_ok=True)
    contents='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'
    rels='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',contents);z.writestr('_rels/.rels',rels)
        z.writestr('3D/3dmodel.model',E.tostring(root,encoding='utf-8',xml_declaration=True))
        z.writestr('Metadata/model_settings.config',E.tostring(settings,encoding='utf-8',xml_declaration=True))
        z.writestr('Metadata/project_settings.config',json.dumps(cfg,indent=2))
    print(json.dumps({'color':color,'objects':len(parts),'project':str(dest),'stagingOnly':True}),flush=True)
(D/'orientation-preparation.json').write_text(json.dumps({'status':'STAGING_NOT_RELEASED','parts':all_rows},indent=2)+'\n')
