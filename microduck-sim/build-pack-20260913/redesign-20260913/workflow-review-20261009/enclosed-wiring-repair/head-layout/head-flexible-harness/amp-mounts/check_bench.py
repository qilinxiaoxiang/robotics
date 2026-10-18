from pathlib import Path
import os,json,hashlib,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;cfg=json.loads((D/'amp-mount-fragment.json').read_text());SRC=Path(cfg['sourceManifest']);rows=json.loads(SRC.read_text())['parts']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(q):
 assert sha(q['file'])==q['sha256'];m=tm.load(q['file'],force='mesh');m.apply_transform(q['worldTransform']);s=mf.Manifold(mf.Mesh64(np.array(m.vertices),np.array(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
pmap={q['key']:q for q in cfg['parts']};amp=load(pmap['amplifier_plusY1']);obs=[q for q in rows if q['key']=='current_cap'or q.get('group')in['mounts','speaker_mounts']]+[pmap['amp_roof_post_'+str(i)]for i in range(2)];checks=[]
for q in obs:
 ob=load(q);b=np.array(ob.bounding_box()).reshape(2,3)
 for d in np.linspace(-10,0,41):
  s=amp.translate([0,0,d]);a=np.array(s.bounding_box()).reshape(2,3);v=0 if np.any(a[1]<b[0])or np.any(b[1]<a[0])else max(0,(s^ob).volume());allow=d==0 and q['key'].startswith('amp_roof_post_')and v<=.00006;checks.append({'moving':'amplifier','fixed':q['key'],'offsetZMm':float(d),'volumeMm3':v,'seatNumericalContact':bool(allow),'failed':v>1e-6 and not allow})
 del ob;gc.collect()
r={'sourceManifest':str(SRC),'sourceSha256':sha(SRC),'fragmentSha256':sha(D/'amp-mount-fragment.json'),'scriptSha256':sha(__file__),'capBenchPriorState':[q['key']for q in obs],'prewiredAmplifierInsertion':{'fromOffsetMm':[0,0,-10],'toOffsetMm':[0,0,0],'sampleCount':41},'checks':checks,'passed':not any(q['failed']for q in checks),'wholeHeadAccepted':False,'requiredOrder':'Amp on detached cap before controller/Pi/speaker are fitted. Pre-solder input leads and tighten speaker terminal screws while amplifier is loose.'};(D/'bench-acceptance.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':r['passed'],'checks':len(checks),'hits':[q for q in checks if q['failed']]}))
