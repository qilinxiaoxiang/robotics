"""Repair -101 conflicts with new3 actual native footprints + prior47 envelopes.
This is a placement proposal only; reslice whole50 and remeasure all actual paths.
"""
from pathlib import Path
import json,zipfile,xml.etree.ElementTree as E,random,sys,numpy as np,hashlib
from pack_surface_native import pack,parse,N
from prepare_surface_projects import matrix,meshvertices
D=Path(__file__).resolve().parents[1];p=D/'projects/Elegoo/black/MicroDuck_Elegoo_black_SURFACE_editable.3mf';manifest=json.loads((D/'projects/project-preparation.json').read_text());row=next(r for r in manifest['variants'] if r['printer']=='Elegoo' and r['group']=='black');orig=Path(row['source_archive']);probe=D/'intermediate/Elegoo/black/three-rotated-probe/plate_1.gcode';E.register_namespace('',N[1:-1]);E.register_namespace('p','http://schemas.microsoft.com/3dmanufacturing/production/2015/06')
class TextPath:
 def __init__(self,text):self.text=text
 def open(self):import io;return io.StringIO(self.text)
 def read_bytes(self):return self.text.encode()
with zipfile.ZipFile(orig) as z:code=z.read(next(n for n in z.namelist() if n.endswith('.gcode'))).decode()
auditold,oldhulls,_,rold=parse(TextPath(code));auditprobe,probehulls,_,rprobe=parse(probe)
with zipfile.ZipFile(p) as z:members={n:z.read(n) for n in z.namelist()}
rt=E.fromstring(members['3D/3dmodel.model']);st=E.fromstring(members['Metadata/model_settings.config']);names={o.get('id'):o.find("metadata[@key='name']").get('value') for o in st.findall('object')};objects={o.get('id'):o for o in rt.find(N+'resources')};selected={'36':(42,42),'40':(112,42),'42':(182,42)};boxes={};evidence=[]
for i,item in enumerate(rt.find(N+'build')):
 oid=item.get('objectid');name=names[oid]
 if oid in selected:
  hit=next(k for k in probehulls if k.split('_id_')[0]==name);box=np.array(probehulls[hit].buffer(rprobe).bounds);v=meshvertices(members,objects[oid]);m=matrix(item.get('transform'));vv=v@m[:3,:3].T+m[:3,3];cent=(vv.min(0)+vv.max(0))/2;shift=cent[:2]-selected[oid];box[[0,2]]+=shift[0];box[[1,3]]+=shift[1];kind='new_exact_native_probe'
 else:box=np.array(oldhulls[f'{name}_id_{i}_copy_0'].buffer(rold).bounds);kind='prior_native_unrotated_part'
 boxes[oid]=box.tolist();evidence.append({'object_id':oid,'name':name,'envelope_source':kind,'box':box.tolist()})
gap=5.;items=[{'oid':oid,'box':box,'w':box[2]-box[0]+gap,'h':box[3]-box[1]+gap} for oid,box in boxes.items()];orders=[sorted(items,key=lambda q:-q[k]) for k in ['w','h']]+[sorted(items,key=lambda q:-q['w']*q['h'])]+[sorted(items,key=lambda q:-max(q['w'],q['h']))];rng=random.Random(106);orders +=[rng.sample(items,len(items)) for _ in range(156)];lower=max(max(max(q['w'],q['h']) for q in items),sum(q['w']*q['h'] for q in items)**.5);best=None;trials=0
for order in orders:
 lo=lower;hi=252;good=pack(order,hi,hi);trials+=1
 if good is None:continue
 while hi-lo>.3:
  mid=(lo+hi)/2;pl=pack(order,mid,mid);trials+=1
  if pl is None:lo=mid
  else:hi=mid;good=pl
 w=max(q['x']+q['w'] for q in good)-gap;h=max(q['y']+q['h'] for q in good)-gap;score=(max(w,h),w*h)
 if best is None or score<best[0]:best=(score,w,h,good)
assert best,'No oneplate bootstrap placement feasible at5mm reservation'
_,w,h,placed=best;moves={};changes=[]
for q in placed:
 box=q['box'];T=np.eye(4)
 if q['rotated']:T[:2,:2]=[[0,-1],[1,0]];box=[-box[3],box[0],-box[1],box[2]]
 T[0,3]=128-w/2+q['x']-box[0];T[1,3]=128-h/2+q['y']-box[1];moves[q['oid']]=T
for item in rt.find(N+'build'):
 oid=item.get('objectid');old=matrix(item.get('transform'));new=moves[oid]@old;item.set('transform',' '.join(f'{v:.15g}' for v in new[:3,:].T.ravel()));changes.append({'oid':oid,'before':old[:3,:].T.ravel().tolist(),'after':new[:3,:].T.ravel().tolist(),'yaw_degrees':90 if abs(moves[oid][0,0])<.1 else 0})
members['3D/3dmodel.model']=E.tostring(rt,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
 for n,data in members.items():z.writestr(n,data)
report={'printer':'Elegoo','group':'black','cause':'CLI_GCODE_PATH_CONFLICTS -101 from original tight positions after pose/interface changes','reserved_gap_mm':5,'predicted_bounds':[128-w/2,128-h/2,128+w/2,128+h/2],'evidence':evidence,'changes':changes,'trials':trials,'new_probe_gcode_sha256':hashlib.sha256(probe.read_bytes()).hexdigest(),'prior_native_archive_sha256':hashlib.sha256(orig.read_bytes()).hexdigest(),'acceptance_pending_whole50_native_reslice':True};(D/'intermediate/Elegoo/black/packing-bootstrap.json').write_text(json.dumps(report,indent=2)+'\n');print('predicted',w,h,'trials',trials)
