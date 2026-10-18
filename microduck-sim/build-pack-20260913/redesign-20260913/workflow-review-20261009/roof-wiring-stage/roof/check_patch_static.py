"""Bounded incremental check: native reconstruction patch against current scene."""
import os,sys,json,hashlib,types,gc
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parents[2];H=R/'head-redesign-20261008'
sys.path.insert(0,str(H/'gpio-audio-repair'));import precision_mesh as pm
c=types.SimpleNamespace(np=np,tm=tm,mf=mf);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=R/'workflow-review-20261009/original-body-converter/fusion-import-manifest.json'
source=json.loads(manifest.read_text());patchpath=D/'native-roof-reconstruction-patch-world.stl';patch=pm.load(c,patchpath)
b=np.array(patch.bounding_box()).reshape(2,3);rows=[];hashes={str(manifest):sha(manifest),str(patchpath):sha(patchpath)}
for r in source['parts']:
 p=Path(r['file']);assert sha(p)==r['sha256'],r['key'];hashes[str(p)]=r['sha256']
 if r['key']=='head_cap':continue
 if r['key'] in ['zero_w_usb_moulding','pi_usb_receiving','sc_micro_b_receiving']:
  rows.append({'key':r['key'],'status':'REMOVED_ARCHITECTURE_PI_USB_UNUSED'});continue
 m=tm.load(p,force='mesh');m.apply_translation(r.get('importTranslationMm',[0,0,0]));bb=m.bounds
 separated=bool(np.any(b[1]<bb[0]) or np.any(bb[1]<b[0]))
 row={'key':r['key'],'boundsMm':bb.tolist(),'method':'exact mesh bounds separation' if separated else 'Mesh64 solid intersection'}
 if separated:row.update(passed=True,intersectionVolumeMm3=0)
 else:
  s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)))
  assert s.status()==mf.Error.NoError,(r['key'],s.status())
  v=max(0,(s^patch).volume());row.update(intersectionVolumeMm3=v,passed=v<1e-6)
  del s
 rows.append(row);del m;gc.collect()
 (D/'patch-static-progress.json').write_text(json.dumps(rows,indent=2)+'\n')
report={'status':'COMPLETE','passed':all(x.get('passed',True)for x in rows),'scope':'Restored native patch versus every non-cap part in current original-body manifest, at current seated pose only. Patch includes 0.02mm overlap rim and is stronger than only the added material. No old whole-scene acceptance transferred.','sourceHashes':hashes,'scriptSha256':sha(Path(__file__)),'patchBoundsMm':b.tolist(),'expectedParts':len(source['parts'])-1,'completeParts':len(rows),'rows':rows,'architecture':'Mac USB to OpenRB rear port; Pi USB empty. Runtime migration not validated.','physicalFitVerified':False}
(D/'patch-static-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'parts':len(rows),'solidPairs':[x for x in rows if x.get('method')=='Mesh64 solid intersection'],'bounds':b.tolist()}))
