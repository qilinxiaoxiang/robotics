"""Three causal OpenRB translations, all original-body obstacles, native cap closed."""
import os,json,sys,hashlib,types,gc
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parents[2];H=R/'head-redesign-20261008';W=R/'workflow-review-20261009'
sys.path.insert(0,str(H/'gpio-audio-repair'));import precision_mesh as pm
c=types.SimpleNamespace(np=np,tm=tm,mf=mf);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
mp=W/'original-body-converter/fusion-import-manifest.json';man=json.loads(mp.read_text());ep=H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json';en=json.loads(ep.read_text());cp=H/'usb-access/full-harness/openrb-usb-c-published-envelope-world.stl'
parts=[]
for row in en['components']:
 p=Path(row['mesh']);assert sha(p)==row['meshSha256'];parts.append(pm.load(c,p))
board=mf.Manifold.batch_boolean(parts,mf.OpType.Add);del parts
plug=pm.load(c,cp);assert board.status()==mf.Error.NoError
cases=[{'dxMm':v,'hits':[],'clearPairs':0,'exactPairs':0}for v in [6,8,10]]
ob=[]
for x in man['parts']:
 if x['key'] in ['openrb','openrb_usb_receiving']:continue
 if x['key']=='head_cap':x=dict(x,file=str(H/'curved-head/community-curved-head-world.stl'),sha256=sha(H/'curved-head/community-curved-head-world.stl'))
 ob.append(x)
for row in ob:
 p=Path(row['file']);assert sha(p)==row['sha256'],row['key'];m=tm.load(p,force='mesh');m.apply_translation(row.get('importTranslationMm',[0,0,0]));bb=m.bounds;s=None
 for case in cases:
  for label,base in [('OpenRB',board),('USB-C-27mm',plug)]:
   q=base.translate([case['dxMm'],0,0]);b=np.array(q.bounding_box()).reshape(2,3)
   if np.any(b[1]<bb[0])or np.any(bb[1]<b[0]):case['clearPairs']+=1;continue
   if s is None:
    s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError,(row['key'],s.status())
   hit=q^s;v=max(0,hit.volume());case['exactPairs']+=1
   if v>1e-6:case['hits'].append({'moving':label,'fixed':row['key'],'volumeMm3':v,'boundsMm':list(hit.bounding_box())})
   else:case['clearPairs']+=1
 del s,m;gc.collect()
 (D/'openrb-forward-progress.json').write_text(json.dumps(cases,indent=2)+'\n')
report={'status':'FINITE_CLOSED_CAP_LAYOUT_SCREEN','cases':cases,'expectedPairsPerCase':2*len(ob),'movingRepresentation':'All142 individually proven conservative OpenRB components combined; actual4472 official27mm length/12mm width, thickness7mm receiving assumption remains.','fixedRepresentation':'Every current original-body part except movingOpenRB and retiredOpenRBUSBreceiving. Current cap replaced by original community closed cap. Old screws remain, source cap has no relocated board posts; support rebuild is separate.','sourceHashes':{str(p):sha(p)for p in [mp,ep,cp,H/'curved-head/community-curved-head-world.stl',Path(__file__)]},'physicalValidated':False}
(D/'openrb-forward-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(cases))
