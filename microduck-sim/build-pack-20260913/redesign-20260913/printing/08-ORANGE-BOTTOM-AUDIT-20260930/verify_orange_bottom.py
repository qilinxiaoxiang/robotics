from pathlib import Path
import json,zipfile,re,base64,io,sys,itertools
import numpy as np
from PIL import Image
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import analyze_bottom as a
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent/'04-FOUR-COLOR-20260929'))
from audit_spacing import parse
old=a.PROJECT; new=D/'MicroDuck_Elegoo_orange_FLAT_editable.3mf'; native=D/'MicroDuck_Elegoo_orange_FLAT.gcode.3mf'; out=D/'MicroDuck_Elegoo_orange_FLAT.gcode'
base=json.loads((D/'geometry-analysis.json').read_text());assert a.sha(old)==base['project_sha256'];assert a.sha(a.ARCHIVE)==base['archive_sha256']
with zipfile.ZipFile(old) as z,zipfile.ZipFile(new) as n:
 for name in z.namelist():
  if name.startswith('3D/') and name!='3D/3dmodel.model':assert z.read(name)==n.read(name),name
 assert z.read('Metadata/project_settings.config')==n.read('Metadata/project_settings.config')
 assert z.read('Metadata/model_settings.config')==n.read('Metadata/model_settings.config')
orig=a.load_meshes();a.PROJECT=new;changed=a.load_meshes();rigid=[]
for (oid,name,m),(nid,nname,n) in zip(orig,changed):
 assert oid==nid and name==nname
 assert m.is_watertight and n.is_watertight
 assert abs(m.volume-n.volume)<1e-5
 assert abs(n.bounds[0,2])<1e-7
 assert np.array_equal(m.faces,n.faces)
 assert np.allclose(m.edges_unique_length,n.edges_unique_length,atol=1e-6)
 if name!='community-8.stl':assert np.allclose(m.vertices,n.vertices,atol=1e-7)
 rigid.append({'name':name,'volume_preserved':True,'triangle_edge_lengths_preserved':True,'on_bed':True})
with zipfile.ZipFile(native) as z:
 data=z.read('Metadata/plate_1.gcode');out.write_bytes(data);cfg=json.loads(z.read('Metadata/project_settings.config'))
code=data.decode();assert 'Centauri' in code and 'M82' not in code
assert cfg['nozzle_diameter']==['0.4'];assert cfg['filament_type']==['PLA'];assert cfg['print_sequence']=='by layer'
hit=re.search(r'^; thumbnail begin 144x144 (\d+)\s*\n(.*?)^; thumbnail end\s*$',code,re.M|re.S);assert hit
b64=''.join(s.lstrip('; ').strip() for s in hit[2].splitlines());assert len(b64)==int(hit[1]);png=base64.b64decode(b64);im=Image.open(io.BytesIO(png));assert im.size==(144,144) and np.array(im).std()>5
(D/'native-thumbnail.png').write_bytes(png)
spacing,*_=parse(out);assert spacing['passed_nonoverlap_and_inside_bed'];assert spacing['object_count']==4;assert spacing['minimum_interobject_extrusion_gap_lower_bound_mm']>=4;assert spacing['minimum_bed_edge_margin_mm']>60
b=spacing['actual_extrusion_bounds_conservative_mm'];assert abs((b[0]+b[2])/2-128)<.5 and abs((b[1]+b[3])/2-128)<.5
with zipfile.ZipFile(a.ARCHIVE) as z: before=a.first_layer_paths(z.read('Metadata/plate_1.gcode').decode())
after=a.first_layer_paths(code);rows=[]
fig,axs=plt.subplots(1,2,figsize=(10,4.5))
for stage,paths,ax in [('Before',before,axs[0]),('After',after,axs[1])]:
 kinds=paths['community-8.stl'];model=unary_union([v for k,v in kinds.items() if 'support' not in k.lower()]);support=unary_union([v for k,v in kinds.items() if 'support' in k.lower()])
 row={'stage':stage,'model_first_layer_area_mm2':model.area,'support_first_layer_area_mm2':support.area,'bottom_surface_area_mm2':kinds.get('Bottom surface',model.intersection(support).difference(model)).area};rows.append(row)
 for shape,color in [(support,'#d0d6db'),(model,'#ef8525')]:
  for p in getattr(shape,'geoms',[shape]):
   if p.geom_type!='Polygon':continue
   ax.fill(*p.exterior.xy,color=color)
   for ring in p.interiors:ax.fill(*ring.xy,color='white')
 ax.set_aspect('equal');ax.set_xlim(72,168);ax.set_ylim(58,114);ax.set_title(f'{stage}: model footprint {model.area:.0f} mm²');ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)');ax.grid(alpha=.15)
assert rows[1]['model_first_layer_area_mm2']>rows[0]['model_first_layer_area_mm2']*8
assert rows[1]['bottom_surface_area_mm2']>1000
fig.suptitle('Left shell — native first layer at Z=0.20 mm\nOrange: model extrusion; gray: support. Same geometry, corrected orientation.');fig.tight_layout();fig.savefig(D/'first-layer-before-after.png',dpi=150)
time=re.search(r'; estimated printing time \(normal mode\) = (.+)',code)
report={'passed':True,'scope':'Digital orientation and native slice acceptance; physical adhesion remains an on-machine observation.','source_project_sha256':a.sha(old),'final_project_sha256':a.sha(new),'native_archive_sha256':a.sha(native),'gcode_sha256':a.sha(out),'embedded_thumbnail_size':im.size,'cut_mm':0,'parts':rigid,'left_shell_native_first_layer':rows,'spacing':spacing,'estimated_time':time[1] if time else None,'sources':['https://help.prusa3d.com/article/place-on-face-tool_1781','https://help.prusa3d.com/article/move-rotate-scale-tools_1914','https://github.com/OrcaSlicer/OrcaSlicer/wiki/keyboard_shortcuts']}
(D/'final-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('ORANGE_BOTTOM_ACCEPTANCE_PASS',json.dumps(report))
