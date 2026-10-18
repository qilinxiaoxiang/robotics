from pathlib import Path
import sys,json,random,zipfile,xml.etree.ElementTree as E
import numpy as np
from native_tools import parse,N
D=Path(__file__).resolve().parent
E.register_namespace('',N[1:-1]);E.register_namespace('p','http://schemas.microsoft.com/3dmanufacturing/production/2015/06')
def pack(items,W,H):
 free=[(0.,0.,W,H)];placed=[]
 for p in items:
  w,h=p['w'],p['h'];best=None
  for rotated in [False,True]:
   w,h=(p['h'],p['w']) if rotated else (p['w'],p['h'])
   for x,y,fw,fh in free:
    if w<=fw+1e-9 and h<=fh+1e-9:
     score=(min(fw-w,fh-h),max(fw-w,fh-h),y,x)
     if best is None or score<best[0]:best=(score,x,y,w,h,rotated)
  if best is None:return None
  _,x,y,w,h,rotated=best;placed.append(dict(p,x=x,y=y,w=w,h=h,rotated=rotated));new=[]
  for fx,fy,fw,fh in free:
   if x>=fx+fw or x+w<=fx or y>=fy+fh or y+h<=fy:new.append((fx,fy,fw,fh));continue
   if x>fx:new.append((fx,fy,x-fx,fh))
   if x+w<fx+fw:new.append((x+w,fy,fx+fw-x-w,fh))
   if y>fy:new.append((fx,fy,fw,y-fy))
   if y+h<fy+fh:new.append((fx,y+h,fw,fy+fh-y-h))
  free=[a for i,a in enumerate(new) if not any(i!=j and a[0]>=b[0] and a[1]>=b[1] and a[0]+a[2]<=b[0]+b[2] and a[1]+a[3]<=b[1]+b[3] and (a!=b or i>j) for j,b in enumerate(new))]
 return placed

def run(printer,group,gcode):
 p=D/printer/group/f'MicroDuck_{printer}_{group}_REPRINT_editable.3mf'
 with zipfile.ZipFile(p) as z:files={n:z.read(n) for n in z.namelist()}
 root=E.fromstring(files['3D/3dmodel.model']);st=E.fromstring(files['Metadata/model_settings.config']);names={o.get('id'):o.find("metadata[@key='name']").get('value') for o in st.findall('object')}
 if printer=='Elegoo':
  audit,hulls,_,rad=parse(Path(gcode));ordered=[it.get('objectid') for it in root.find(N+'build')]; boxes={oid:list(hulls[f'{names[oid]}_id_{i}_copy_0'].buffer(rad).bounds) for i,oid in enumerate(ordered)}
 else:
  sys.path.insert(0,str(D.parent/'04-FOUR-COLOR-20260929/05-BAMBU-WHITE-YELLOW'));from audit_bambu_spacing import audit_archive
  audit=audit_archive(Path(gcode),len(names));labels={i.find("metadata[@key='object_id']").get('value'):i.find("metadata[@key='identify_id']").get('value') for i in st.findall('plate/model_instance')};by={r['object_label']:r['extrusion_bounds_mm'] for r in audit['objects']};boxes={k:by[v] for k,v in labels.items()}
 gap=5.;items=[{'oid':oid,'box':b,'w':b[2]-b[0]+gap,'h':b[3]-b[1]+gap} for oid,b in boxes.items()]
 orders=[sorted(items,key=lambda p:-p[k]) for k in ['w','h']]+[sorted(items,key=lambda p:-(p['w']*p['h']))]+[sorted(items,key=lambda p:-max(p['w'],p['h']))]
 rng=random.Random(930);orders += [rng.sample(items,len(items)) for _ in range(156)]
 lower=max(max(max(p['w'],p['h']) for p in items),sum(p['w']*p['h'] for p in items)**.5);best=None;trials=0
 for order in orders:
  lo=lower;hi=252.;good=pack(order,hi,hi);trials+=1
  if good is None:continue
  while hi-lo>.3:
   mid=(lo+hi)/2;pl=pack(order,mid,mid);trials+=1
   if pl is None:lo=mid
   else:hi=mid;good=pl
  w=max(q['x']+q['w'] for q in good)-gap;h=max(q['y']+q['h'] for q in good)-gap;score=(max(w,h),w*h)
  if best is None or score<best[0]:best=(score,w,h,good)
 assert best,'No safe single-plate candidate at5mm gap'
 _,w,h,placed=best;moves={}
 for q in placed:
  box=q['box'];T=np.eye(4)
  if q['rotated']:T[:2,:2]=[[0,-1],[1,0]];box=[-box[3],box[0],-box[1],box[2]]
  T[0,3]=128-w/2+q['x']-box[0];T[1,3]=128-h/2+q['y']-box[1];moves[q['oid']]=T
 changes=[]
 for item in root.find(N+'build'):
  oid=item.get('objectid');v=list(map(float,item.get('transform').split()));old=v[:];M=np.eye(4);M[:3,:]=np.array(v).reshape(4,3).T;M=moves[oid]@M;v=M[:3,:].T.ravel().tolist();item.set('transform',' '.join(f'{q:.15g}' for q in v));changes.append({'oid':oid,'before':old,'after':v})
 files['3D/3dmodel.model']=E.tostring(root,encoding='utf-8',xml_declaration=True)
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for n,v in files.items():z.writestr(n,v)
 report={'printer':printer,'group':group,'trials':trials,'reserved_gap_mm':gap,'predicted_bounds':[128-w/2,128-h/2,128+w/2,128+h/2],'prior_native_audit':audit,'changes':changes,'method':'160 deterministic MaxRects orderings, binary square-size search; XY translations and 90-degree yaw only; bottom direction unchanged. Finite candidate result, not global optimality.'};(p.parent/'packing.json').write_text(json.dumps(report,indent=2));print(printer,group,'predicted',w,h,'margin',(256-max(w,h))/2,'trials',trials,flush=True)
if __name__=='__main__':run(*sys.argv[1:])
