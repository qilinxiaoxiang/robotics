"""Inspect embedded 3MF meshes, model assignments, plate limits and process settings."""
from pathlib import Path
import json,zipfile,hashlib,xml.etree.ElementTree as E
import numpy as np
O=Path(__file__).resolve().parent;file=O/'current-print-queue.3mf';z=zipfile.ZipFile(file)
ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'};prod='{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
cache={}
def root(p):
 if p not in cache:cache[p]=E.fromstring(z.read(p))
 return cache[p]
def transform(s):
 T=np.eye(4)
 if s:T[:3,:]=np.asarray([float(x) for x in s.split()]).reshape(4,3).T
 return T
def points(p,id):
 obj=next(x for x in root(p).findall('m:resources/m:object',ns) if x.get('id')==id)
 v=obj.find('m:mesh/m:vertices',ns)
 if v is not None:return np.array([[float(x.get(a)) for a in 'xyz'] for x in v])
 out=[]
 for c in obj.findall('m:components/m:component',ns):
  cp=c.get(prod+'path',p).lstrip('/');T=transform(c.get('transform'));pts=points(cp,c.get('objectid'));out.append(pts@T[:3,:3].T+T[:3,3])
 return np.vstack(out)
model='3D/3dmodel.model';build={}
for b in root(model).findall('m:build/m:item',ns):
 T=transform(b.get('transform'));pts=points(model,b.get('objectid'));pts=pts@T[:3,:3].T+T[:3,3];build[b.get('objectid')]=pts
settings=E.fromstring(z.read('Metadata/model_settings.config'));plates=[]
for p in settings.findall('plate'):
 md={m.get('key'):m.get('value') for m in p.findall('metadata')};ids=[i.find("metadata[@key='object_id']").get('value') for i in p.findall('model_instance')]
 pts=np.vstack([build[i] for i in ids]);bounds=[pts.min(0).tolist(),pts.max(0).tolist()]
 plates.append({'plate':int(md['plater_id']),'ids':ids,'bounds_mm':bounds,'metadata':md})
project=json.loads(z.read('Metadata/project_settings.config'))
print(json.dumps({'plates':plates,'printable_area':project.get('printable_area'),'printable_height':project.get('printable_height'),'exclude_area':project.get('bed_exclude_area'),'objects':len(build),'settings':{k:project.get(k) for k in ['wall_loops','sparse_infill_density','sparse_infill_pattern','layer_height','enable_support','support_type','printer_model','nozzle_diameter','curr_bed_type']}},indent=2))
from shapely.geometry import MultiPoint,box as rect
# Recorded Bambu arrangement coordinates: 3 columns, 307.2 mm plate pitch.
origins={1:(0.,0.),2:(307.2,0.),3:(614.4,0.),4:(0.,-307.2),5:(307.2,-307.2),6:(614.4,-307.2)}
assert len(plates)==6
summaries=[];errors=[]
for pl in plates:
    origin=np.array(origins[pl['plate']]);hulls={};minimum_margin=999.;zmax=0
    for oid in pl['ids']:
        pts=build[oid].copy();pts[:,:2]-=origin;hull=MultiPoint(pts[:,:2]).convex_hull;hulls[oid]=hull
        if not rect(0,0,256,256).buffer(.0001).covers(hull):errors.append('object outside plate '+oid)
        if hull.intersection(rect(0,0,18,28)).area>.001:errors.append('object inside exclusion '+oid)
        if pts[:,2].min()<-.001 or pts[:,2].max()>250:errors.append('object vertical limit '+oid)
        minimum_margin=min(minimum_margin,float(pts[:,0].min()),float(pts[:,1].min()),float(256-pts[:,0].max()),float(256-pts[:,1].max()))
        zmax=max(zmax,float(pts[:,2].max()))
    gap=999.
    ids=list(hulls)
    for i,a in enumerate(ids):
        for b in ids[i+1:]:
            if hulls[a].intersection(hulls[b]).area>.001:errors.append('overlapping conservative footprints '+a+'/'+b)
            gap=min(gap,hulls[a].distance(hulls[b]))
    summaries.append({'plate':pl['plate'],'instances':len(ids),'origin_in_3mf_mm':origin.tolist(),'minimum_bed_edge_margin_mm':minimum_margin,'minimum_convex_footprint_gap_mm':gap,'maximum_part_height_mm':zmax})
settings_expected={'wall_loops':'4','sparse_infill_density':'30%','sparse_infill_pattern':'gyroid','layer_height':'0.2','enable_support':'1','support_type':'tree(auto)','printer_model':'Bambu Lab X1 Carbon','nozzle_diameter':['0.4'],'curr_bed_type':'Cool Plate'}
for k,v in settings_expected.items():
    if project.get(k)!=v:errors.append('preset mismatch '+k)
man=json.loads((O/'print-manifest.json').read_text());
for r in man['instances']:
    if hashlib.sha256(Path(r['file']).read_bytes()).hexdigest()!=r['sha256']:errors.append('source hash mismatch '+r['file'])
object_names=[a.find("metadata[@key='name']").get('value') for a in settings.findall('object')]
for target in ['head-cap-usb-service-print.stl','regulator-open-insert-print.stl','camera_pitch_foot.stl','camera_cradle.stl','audio_carrier_print.stl']:
    if object_names.count(target)!=1:errors.append('new part not embedded exactly once '+target)
if 'head-cap-mouth-clearance-print.stl' in object_names:errors.append('old cap still embedded')
if any('voltage-alarm' in n for n in object_names):errors.append('alarm accidentally added')
if sum(x['instances'] for x in summaries)!=89:errors.append('instance count')
result={'project':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'manifest':str(O/'print-manifest.json'),'manifest_sha256':hashlib.sha256((O/'print-manifest.json').read_bytes()).hexdigest(),'slicer_version':'BambuStudio 02.07.01.62','mode':'Editable arranged project; no slicing or machine toolpaths','instances':89,'plates':summaries,'settings':settings_expected,'embedded_gcode_files':[n for n in z.namelist() if n.endswith('.gcode')],'source_hashes_verified':True,'included_new_parts_once':True,'no_alarm_or_old_headcap':True,'errors':errors,'passed':not errors,'physical_print_completed':False,'scope':'Embedded 3MF mesh footprints and height within six 256 mm beds, excluded corner avoided, no pairwise convex-footprint overlap. Support footprints and actual printer/material require slicing for that machine.'}
(O/'print-queue-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
assert result['passed'],errors
