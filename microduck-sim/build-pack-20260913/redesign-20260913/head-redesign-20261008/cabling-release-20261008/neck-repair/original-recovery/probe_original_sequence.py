from pathlib import Path
exec((Path(__file__).parent/'check_mouth_ring.py').read_text().split("report={'accepted'")[0])
out={}
for k,s in [('support',S),('jaw',J),('bottom',V)]:
 m=(R^s).to_mesh64();v=np.asarray(m.vert_properties)[:,:3];out[k]={'bounds':None if not len(v) else [v.min(0).tolist(),v.max(0).tolist()],'vol':(R^s).volume()}
report={'routes':{}}
exec((D/'check_mouth_ring.py').read_text().split('def scan(')[1].split("scan('ring_over")[0].join(['def scan(', '']))
for v in [[0,0,30],[30,0,0],[-30,0,0]]:
 scan('jaw_ring_into_bottom_'+str(v),{'jaw':J,'ring':R},{'V1':V},v)
scan('support_down_into_jaw_motor_bottom',{'support':S},{'jaw':J,'ring':R,'motor':M,'V1':V},[0,0,30])
scan('motor15_down_into_jaw_bottom',{'motor':M},{'jaw':J,'V1':V},[0,0,30])
for od in [14.5,14.4]:
 r=ring(10.4,od,2.6,-39.65);out[str(od)]={'bottomVol':(r^V).volume(),'bottomGap':r.min_gap(V,1),'supportGap':r.min_gap(S,1)}
out['routes']=report['routes'];c.save(D/'original-sequence-probe.json',out);print(json.dumps(out))
