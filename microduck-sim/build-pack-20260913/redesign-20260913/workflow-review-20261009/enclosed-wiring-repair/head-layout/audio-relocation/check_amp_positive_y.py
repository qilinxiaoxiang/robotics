from pathlib import Path
O=Path(__file__).resolve().parent
exec((O/'check_one_pose.py').read_text().split('Tp=')[0])
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--dy',type=float,default=24);a=ap.parse_args()
cfg=read(O/'native-mount-spec.json');inv=[]
for r in cfg['references']:
 if r['name']=='REFERENCE current relocated amplifier and X1 terminal':continue
 inv.append({'id':r['name'],'file':r['file'],'sha256':r['sha256'],'worldTransform':r.get('worldTransform',np.eye(4).tolist())})
for k,p in [('current_cap',O/'native/closed-cap-Pi-audio-mounts-world.stl'),('current_cradle',O/'native/speaker-cradle-single-seat-adjustment.stl')]:inv.append({'id':k,'file':str(p),'sha256':sha(p),'worldTransform':np.eye(4).tolist()})
ampfile=O/'amplifier-front-free-bay-world.stl';amp=load(ampfile).translate([0,a.dy,0]);checks=[]
for r in inv:
 assert sha(r['file'])==r['sha256'];obs=load(r['file']).transform(np.array(r['worldTransform'])[:3]);q=amp^obs;v=max(0,q.volume());checks.append({'fixed':r['id'],'intersectionMm3':v,'boundsMm':list(q.bounding_box())if v>1e-7 else None});del obs;gc.collect()
out={'status':'STATIC_POSE_CHECKED','passed':not any(x['intersectionMm3']>1e-7 for x in checks),'dyMm':a.dy,'ampBoundsMm':list(amp.bounding_box()),'inventory':inv,'expectedPairCount':len(inv),'completePairCount':len(checks),'checks':checks,'hits':[x for x in checks if x['intersectionMm3']>1e-7],'sourceHashes':hashes,'scope':'Exactly one amplifier translation against every rigid item in one explicit current local inventory including actual MicroB receiving, individual Pi hardware, speaker/cradle/keeper, current closed cap and all current posts. Old amplifier itself replaced; no other part label omitted. No compound union.','wholeHeadAccepted':False};f=O/f'positive-y{a.dy:g}-check.json';f.write_text(json.dumps(out,indent=2));print(json.dumps({k:out[k]for k in ['passed','dyMm','ampBoundsMm','expectedPairCount','completePairCount','hits']},indent=2))
if out['passed']:pm.export(ctx,amp,O/f'amplifier-positive-y{a.dy:g}-world.stl')
