from pathlib import Path
import json, zipfile, hashlib, xml.etree.ElementTree as ET, re
import numpy as np
import trimesh
from shapely.geometry import Polygon, LineString, GeometryCollection
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D=Path(__file__).resolve().parent
C=D.parent/'04-FOUR-COLOR-20260929/07-COMPACT-CENTER-20260929'
PROJECT=C/'Elegoo/orange/MicroDuck_Elegoo_orange_COMPACT_editable.3mf'
ARCHIVE=C/'Elegoo/orange/MicroDuck_Elegoo_orange_COMPACT.gcode.3mf'
N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
PN='{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def matrix(s):
    a=np.eye(4);a[:3,:]=np.array(list(map(float,s.split()))).reshape(4,3).T;return a
def load_meshes():
    with zipfile.ZipFile(PROJECT) as z:
        root=ET.fromstring(z.read('3D/3dmodel.model'));objects={a.get('id'):a for a in root.find(N+'resources')}
        settings=ET.fromstring(z.read('Metadata/model_settings.config'))
        names={a.get('id'):a.find("metadata[@key='name']").get('value') for a in settings.findall('object')}
        meshes=[]
        for item in root.find(N+'build'):
            ob=objects[item.get('objectid')];parts=[]
            for comp in ob.find(N+'components'):
                child=ET.fromstring(z.read(comp.get(PN+'path').lstrip('/')))
                obj=next(a for a in child.find(N+'resources') if a.get('id')==comp.get('objectid'))
                me=obj.find(N+'mesh')
                v=np.array([[float(a.get(k)) for k in ('x','y','z')] for a in me.find(N+'vertices')])
                f=np.array([[int(a.get(k)) for k in ('v1','v2','v3')] for a in me.find(N+'triangles')])
                t=matrix(item.get('transform'))@matrix(comp.get('transform'))
                parts.append(trimesh.Trimesh(v@t[:3,:3].T+t[:3,3],f,process=True))
            mesh=trimesh.util.concatenate(parts);meshes.append((item.get('objectid'),names[item.get('objectid')],mesh))
    return meshes
def section_shape(mesh,z):
    path=mesh.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
    shape=GeometryCollection()
    if path is not None:
        for loop in path.discrete:
            if len(loop)>=4 and np.linalg.norm(loop[0]-loop[-1])<1e-4:
                poly=Polygon(loop[:,:2])
                if not poly.is_valid:poly=poly.buffer(0)
                shape=shape.symmetric_difference(poly)
    return shape
def first_layer_paths(code):
    cur=None;kind='Custom';x=y=z=0.;width=.4;paths={};names={};zs={}
    for line in code.splitlines():
        if line.startswith('EXCLUDE_OBJECT_DEFINE'):
            name=re.search(r'NAME=(\S+)',line)[1];names[name]=name.split('_id_')[0]
        if line.startswith('EXCLUDE_OBJECT_START'):cur=re.search(r'NAME=(\S+)',line)[1]
        if line.startswith('EXCLUDE_OBJECT_END'):cur=None
        if line.startswith(';TYPE:'):kind=line[6:].strip()
        if line.startswith(';WIDTH:'):width=float(line.split(':')[1])
        if not re.match(r'^G[0123] ',line):continue
        vals={k:float(v) for k,v in re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)',line.split(';')[0])}
        xx=vals.get('X',x);yy=vals.get('Y',y);zz=vals.get('Z',z)
        if cur and vals.get('E',0)>0 and abs(zz-.2)<1e-5 and (xx!=x or yy!=y) and kind!='Custom':
            pts=[(x,y),(xx,yy)]
            if line.startswith(('G2 ','G3 ')):
                cx=x+vals.get('I',0);cy=y+vals.get('J',0);r=np.hypot(x-cx,y-cy)
                a=np.arctan2(y-cy,x-cx);b=np.arctan2(yy-cy,xx-cx);sgn=1 if line.startswith('G3 ') else -1
                span=((b-a)*sgn)%(2*np.pi);span=span if span>1e-8 else 2*np.pi
                count=max(8,int(np.ceil(span*r/.1)));pts=[(cx+r*np.cos(a+sgn*span*i/count),cy+r*np.sin(a+sgn*span*i/count)) for i in range(count+1)]
            paths.setdefault(names[cur],{}).setdefault(kind,[]).append(LineString(pts).buffer(width/2))
        x,y,z=xx,yy,zz
    return {name:{kind:unary_union(v) for kind,v in kinds.items()} for name,kinds in paths.items()}
def main():
    with zipfile.ZipFile(ARCHIVE) as z:code=z.read('Metadata/plate_1.gcode').decode()
    paths=first_layer_paths(code);results=[];fig,axs=plt.subplots(2,4,figsize=(15,7))
    for col,(oid,name,mesh) in enumerate(load_meshes()):
        floor=float(mesh.bounds[0,2]);tris=mesh.triangles
        mask=np.max(np.abs(tris[:,:,2]-floor),axis=1)<=1e-4
        contact=unary_union([Polygon(t[:,:2]) for t in tris[mask] if Polygon(t[:,:2]).area>1e-9])
        cuts={};shapes={}
        for h in [.0001,.01,.05,.1,.2,.4,.75,1.0]:
            shape=section_shape(mesh,floor+h);shapes[h]=shape
            cuts[str(h)]={'area_mm2':float(shape.area),'components':len(shape.geoms) if hasattr(shape,'geoms') else (1 if not shape.is_empty else 0)}
        kinds=paths.get(name,{})
        model_types={k:v for k,v in kinds.items() if not any(t in k.lower() for t in ['support','brim','skirt'])}
        first=unary_union(list(model_types.values()));support=unary_union([v for k,v in kinds.items() if k not in model_types])
        height=float(mesh.extents[2]);volume=float(abs(mesh.volume))
        # Integrate cross-sections of the hypothetical discarded 0.75 mm slab.
        zs=np.linspace(.0001,.75,76);areas=np.array([section_shape(mesh,floor+q).area for q in zs]);removed=float(np.trapezoid(areas,zs))
        row={'object_id':oid,'name':name,'watertight':bool(mesh.is_watertight),'print_bounds_mm':mesh.bounds.tolist(),'minimum_z_mm':floor,'height_mm':height,'volume_mm3':volume,'coplanar_bottom_triangle_count':int(mask.sum()),'coplanar_bottom_area_mm2':float(contact.area),'sections':cuts,'first_layer_z_mm':.2,'first_layer_model_area_mm2':float(first.area),'first_layer_model_types':{k:float(v.area) for k,v in model_types.items()},'first_layer_support_brim_area_mm2':float(support.area),'hypothetical_075_cut_removed_volume_mm3':removed,'hypothetical_075_cut_volume_percent':100*removed/volume,'hypothetical_075_height_reduction_percent':100*.75/height,'mesh_sha256':hashlib.sha256(mesh.vertices.tobytes()+mesh.faces.tobytes()).hexdigest()}
        results.append(row)
        def paint(ax,shape,color):
            shapes=list(shape.geoms) if hasattr(shape,'geoms') else [shape]
            for p in shapes:
                if p.geom_type=='Polygon':
                    x,y=p.exterior.xy;ax.fill(x,y,color=color,alpha=.7)
                    for ring in p.interiors:x,y=ring.xy;ax.fill(x,y,color='white')
        paint(axs[0,col],contact,'#ef8b35');paint(axs[1,col],shapes[.75],'#3483b9')
        for ax in axs[:,col]:
            ax.set_aspect('equal');ax.set_xlim(mesh.bounds[0,0]-2,mesh.bounds[1,0]+2);ax.set_ylim(mesh.bounds[0,1]-2,mesh.bounds[1,1]+2);ax.grid(alpha=.2)
        axs[0,col].set_title(f'{name}\nExisting flat contact {contact.area:.1f} mm²')
        axs[1,col].set_title(f'Hypothetical 0.75 mm cut\nSection {shapes[.75].area:.1f} mm²')
    fig.suptitle('Current print orientation: existing bottom contact versus hypothetical trim\nNo print files changed; white regions include designed holes/voids');fig.tight_layout();fig.savefig(D/'bottom-contact-comparison.png',dpi=140)
    out={'problem_ids':['P5','P6'],'project':str(PROJECT),'project_sha256':sha(PROJECT),'archive':str(ARCHIVE),'archive_sha256':sha(ARCHIVE),'method':'Transformed exact current 3MF meshes, coplanar bottom triangles within 0.0001mm; parity of closed mesh sections; native positive first-layer XY extrusion with bead width; hypothetical slab volume integrated in0.01mm increments, not an exported cut.','parts':results}
    (D/'geometry-analysis.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(results,indent=2))
if __name__=='__main__':main()
