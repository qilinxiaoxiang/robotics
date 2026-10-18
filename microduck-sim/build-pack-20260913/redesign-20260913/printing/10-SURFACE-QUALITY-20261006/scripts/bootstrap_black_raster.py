from pathlib import Path
import sys,json,zipfile,xml.etree.ElementTree as E,random,time
import numpy as np
from scipy.signal import fftconvolve
from shapely import contains_xy
from shapely.affinity import rotate,translate
from shapely.geometry import box
from pack_surface_native import parse,N
from prepare_surface_projects import meshvertices,matrix
D=Path(__file__).resolve().parents[1];p=D/'projects/Elegoo/black/MicroDuck_Elegoo_black_SURFACE_editable.3mf';F=D/'intermediate/Elegoo/black';E.register_namespace('',N[1:-1]);E.register_namespace('p','http://schemas.microsoft.com/3dmanufacturing/production/2015/06')
manifest=json.loads((D/'projects/project-preparation.json').read_text());row=next(r for r in manifest['variants'] if r['printer']=='Elegoo' and r['group']=='black');orig=Path(row['source_archive']);probe=F/'three-rotated-probe/plate_1.gcode'
class TextPath:
 def __init__(self,text):self.text=text
 def open(self):import io;return io.StringIO(self.text)
 def read_bytes(self):return self.text.encode()
with zipfile.ZipFile(orig) as z:code=z.read(next(n for n in z.namelist() if n.endswith('.gcode'))).decode()
auditold,oldhulls,_,rold=parse(TextPath(code));auditprobe,probehulls,_,rprobe=parse(probe)
with zipfile.ZipFile(p) as z:files={n:z.read(n) for n in z.namelist()}
root=E.fromstring(files['3D/3dmodel.model']);st=E.fromstring(files['Metadata/model_settings.config']);names={o.get('id'):o.find("metadata[@key='name']").get('value') for o in st.findall('object')};objects={o.get('id'):o for o in root.find(N+'resources')};items=list(root.find(N+'build'));selected={'36':(42,42),'40':(112,42),'42':(182,42)};polys={}
for i,item in enumerate(items):
 oid=item.get('objectid');name=names[oid]
 if oid in selected:
  hit=next(k for k in probehulls if k.split('_id_')[0]==name);poly=probehulls[hit].buffer(rprobe);v=meshvertices(files,objects[oid]);m=matrix(item.get('transform'));vv=v@m[:3,:3].T+m[:3,3];cent=(vv.min(0)+vv.max(0))/2;shift=cent[:2]-selected[oid];poly=translate(poly,xoff=shift[0],yoff=shift[1])
 else:poly=oldhulls[f'{name}_id_{i}_copy_0'].buffer(rold)
 polys[oid]=poly
# Conservative raster cover: every cell intersecting buffered polygon is marked by expanding half cell diagonal.
res=1.;pad=2.25;cache={}
for oid,poly in polys.items():
 for angle in [0,90,180,270]:
  rotated=rotate(poly,angle,origin=(0,0));b=rotated.bounds;local=translate(rotated,xoff=-b[0]+pad,yoff=-b[1]+pad);w=int(np.ceil(b[2]-b[0]+2*pad));h=int(np.ceil(b[3]-b[1]+2*pad));xx,yy=np.meshgrid(np.arange(w)+.5,np.arange(h)+.5);mask=contains_xy(local.buffer(pad+.708),xx,yy).astype(float);cache[oid,angle]=(mask,b,rotated)
orders=[];base=list(polys);rng=random.Random(930)
for key in [lambda k:polys[k].area,lambda k:max(polys[k].bounds[2]-polys[k].bounds[0],polys[k].bounds[3]-polys[k].bounds[1]),lambda k:(polys[k].bounds[2]-polys[k].bounds[0])*(polys[k].bounds[3]-polys[k].bounds[1])]:orders.append(sorted(base,key=key,reverse=True))
orders += [sorted(base,key=lambda k:-polys[k].area*rng.uniform(.6,1.4)) for _ in range(15)]
best=None;start=time.time()
for trial,order in enumerate(orders):
 occ=np.zeros((252,252));placed=[]
 # avoid printer lower-right excluded corner, with pad clearance
 occ[:21,244:]=1
 for oid in order:
  choice=None
  for angle in [0,90,180,270]:
   mask,b,rot=cache[oid,angle];h,w=mask.shape
   if h>252 or w>252:continue
   corr=fftconvolve(occ,mask[::-1,::-1],mode='valid');ys,xs=np.where(corr<.1)
   if len(xs)==0:continue
   usedw=max([q['x']+q['w'] for q in placed]or[0]);usedh=max([q['y']+q['h'] for q in placed]or[0]);ext=np.maximum(np.maximum(xs+w,usedw),np.maximum(ys+h,usedh));scores=ext*100000+(ys+h)*100+xs
   i=int(np.argmin(scores));score=float(scores[i]);x=int(xs[i]);y=int(ys[i])
   if choice is None or score<choice[0]:choice=(score,angle,x,y,w,h)
  if choice is None:break
  _,angle,x,y,w,h=choice;mask,b,rot=cache[oid,angle];occ[y:y+h,x:x+w]+=mask;placed.append(dict(oid=oid,angle=angle,x=x,y=y,w=w,h=h,tx=x-b[0]+pad+2,ty=y-b[1]+pad+2))
 print('trial',trial,'placed',len(placed),flush=True)
 if len(placed)==len(order):
  shapes=[translate(cache[q['oid'],q['angle']][2],xoff=q['tx'],yoff=q['ty']) for q in placed];bounds=[min(g.bounds[0]for g in shapes),min(g.bounds[1]for g in shapes),max(g.bounds[2]for g in shapes),max(g.bounds[3]for g in shapes)];dx=128-(bounds[0]+bounds[2])/2;dy=128-(bounds[1]+bounds[3])/2;shapes=[translate(g,xoff=dx,yoff=dy) for g in shapes];gap=min(g.distance(h) for i,g in enumerate(shapes) for h in shapes[i+1:]);bed=box(0,0,256,256);ex=box(246,0,256,20);valid=gap>=4.5 and all(bed.covers(g) and g.distance(ex)>=0.01 for g in shapes)
  if valid:best=(placed,dx,dy,gap,[min(g.bounds[0]for g in shapes),min(g.bounds[1]for g in shapes),max(g.bounds[2]for g in shapes),max(g.bounds[3]for g in shapes)]);break
 if time.time()-start>120:break
report={'bootstrap_envelopes':'new3 actual native rotated probes plus old47 native unrotated envelopes; complete50 native regen still required','old_native_archive':str(orig),'new_probe_gcode':str(probe),'feasible':best is not None,'trials':trial+1,'elapsed_seconds':time.time()-start,'method':'Conservative1mm raster hull packing; support/bead envelopes expanded2.25mm,0.708mm raster cover;4yaw orientations; exact polygon gap/bed/exclusion aftercenter.'}
if best:
 placed,dx,dy,gap,bounds=best;lookup={q['oid']:q for q in placed}
 for it in items:
  q=lookup[it.get('objectid')];a=np.deg2rad(q['angle']);R=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]]);T=np.eye(4);T[:3,:3]=R;T[:2,3]=[q['tx']+dx,q['ty']+dy];M=np.eye(4);M[:3,:]=np.array(list(map(float,it.get('transform').split()))).reshape(4,3).T;M=T@M;it.set('transform',' '.join(f'{v:.15g}'for v in M[:3,:].T.ravel()))
 files['3D/3dmodel.model']=E.tostring(root,encoding='utf-8',xml_declaration=True)
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for n,data in files.items():z.writestr(n,data)
 report.update(placements=placed,center_translation=[dx,dy],minimum_exact_support_hull_gap_mm=gap,bounds=bounds,project=str(p))
(D/'intermediate/Elegoo/black/black-packing-candidate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='placements'}),flush=True)
