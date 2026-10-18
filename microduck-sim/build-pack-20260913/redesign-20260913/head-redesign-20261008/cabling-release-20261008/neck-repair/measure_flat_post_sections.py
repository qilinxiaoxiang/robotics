"""Source-bound local material sections, not strength or full-route acceptance."""
import json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'flat-yaw-channel';rp=O/'136__head_bottom.json';r=json.loads(rp.read_text());p=Path(r['candidate']['file']);assert c.sha(p)==r['candidate']['sha256'];man=H/'camera-ribbon-repair/positive-x225/candidate-manifest.json';src=H/json.loads(man.read_text())['replacementMeshes']['head_bottom']
def read(p):
 m=trimesh.load(p,force='mesh');assert m.is_watertight and m.is_volume;s=mf.Manifold(mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32)));assert s.status()==mf.Error.NoError;return s
before=read(src);after=read(p);rows=[]
for x in r['protectedRegions']:
 if not x['id'].endswith(('03','04')) or 'center' not in x:continue
 cx,cy,cz=x['center'];sections=[]
 for zi in range(98*4,112*4):
  z=zi/4;slab=mf.Manifold.cylinder(.2,4,4,64).translate([cx,cy,z-.1]);a=before^slab;b=after^slab
  sections.append({'zMm':z,'originalAreaMm2':a.volume()/.2,'remainingAreaMm2':b.volume()/.2,'remainingConnectedBodies':len(b.decompose())})
 top=x['removedBounds'][5];threadtip=cz-6;above=[s for s in sections if s['zMm']>top+.1 and s['zMm']<threadtip-.1]
 rows.append({'id':x['id'],'removedMaterialTopZMm':top,'screwTipZMm':threadtip,'verticalSpaceBetweenSlotAndScrewTipMm':threadtip-top,'sectionRadiusMm':4,'sectionThicknessMm':.2,'minimumNativeAreaAboveSlotToScrewTipMm2':min(s['originalAreaMm2'] for s in above),'minimumRemainingAreaAboveSlotToScrewTipMm2':min(s['remainingAreaMm2'] for s in above),'allSectionsAboveSlotConnected':all(s['remainingConnectedBodies']==1 for s in above),'sections':sections})
out={'accepted':False,'scope':'Two posts, yaw+170 only. Material-area/continuity evidence, not load strength or all-poses approval.','rows':rows,'sourceHashes':{str(f):c.sha(f) for f in [Path(__file__),p,src,rp,man]}};c.save(O/'136-post-sections.json',out);print(json.dumps([{k:v for k,v in x.items() if k!='sections'} for x in rows]))
