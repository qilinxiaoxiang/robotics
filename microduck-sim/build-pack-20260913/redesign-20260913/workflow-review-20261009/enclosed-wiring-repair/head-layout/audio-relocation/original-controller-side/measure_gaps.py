from pathlib import Path
import os,json,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
Q=Path(__file__).resolve().parent;O=Q.parent;ns={'__file__':str(O/'check_one_pose.py')};exec((O/'check_one_pose.py').read_text().split('Tp=')[0],ns);load=ns['load'];read=ns['read'];sha=ns['sha'];np=ns['np'];r=read(Q/'inset05-check.json');amp=load(r['mesh']);result=[]
obs=[('cap',O/'positive-y13-native/closed-cap-Pi-audio-positive-y13-world.stl',np.eye(4))]+[(f'OpenRB_{x["component"]}',Path(x['file']),np.eye(4))for x in r['openrbRepresentation']]
for k,f,T in obs:
 ob=load(f).transform(T[:3]);a=np.array(amp.bounding_box()).reshape(2,3);b=np.array(ob.bounding_box()).reshape(2,3);lower=np.linalg.norm(np.maximum(np.maximum(a[0]-b[1],b[0]-a[1]),0));gap=float(lower)if lower>=2 else float(amp.min_gap(ob,2));result.append({'part':k,'gapMmCappedAt2':min(gap,2),'method':'bounds separation'if lower>=2 else'Mesh64 solid minimum distance'});del ob;gc.collect()
cap=result[0];controller=min(result[1:],key=lambda x:x['gapMmCappedAt2']);out={'cap':cap,'nearestController':controller,'rows':result,'sourceHashes':ns['hashes']|{str(Path(__file__)):sha(__file__)},'notManufacturingToleranceCertification':True};(Q/'gaps.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'cap':cap,'controller':controller}))
