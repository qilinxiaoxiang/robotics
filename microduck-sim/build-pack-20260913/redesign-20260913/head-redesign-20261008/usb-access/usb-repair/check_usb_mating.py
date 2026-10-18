"""One current obstacle versus the full moving USB-A end and constant-length lead."""
from pathlib import Path
import hashlib,json,os,runpy,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent
ns=runpy.run_path(str(D/'check_planned_usb.py'))
a=ns['args'];assert a.obstacle not in ('self','export') and not a.domain and not a.pose_indices
np=ns['np'];p=ns['plan'];u=np.asarray(p['scFinalDirection']);row=ns['row']
plan=json.loads((D/'positive-x225-mating-plan.json').read_text())
for f,h in plan['sourceHashes'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
samples=next(r['samples'] for r in plan['rows'] if r['spanMm']==a.span)
assert all(r['lengthSolved'] for r in samples)
ob=ns['ob'];bb=np.asarray(ob.bounding_box()).reshape(2,3);checks=[]
for s in samples:
    points,L=ns['fillet_polyline'](s['waypointsMm'],10)
    end=p['cEndArc'];arc,arcL=ns['circular_arc'](end['startMm'],end['incoming'],end['outgoing'],10)
    assert np.linalg.norm(points[-1]-arc[-1])<1e-7
    points=np.vstack([points,arc[-2::-1]])
    assert abs(L+arcL-102.5)<1e-7
    mate=np.asarray(row['usbAMatingPointMm'])+u*s['withdrawalMm']
    moving={
        'acFlexibleReceiving':ns['solid'](ns['tube'](points,4.5,start_tangent=u,end_tangent=-np.asarray(end['incoming']))),
        'acMaleReceiving':ns['box'](mate,u,22.9,12,20),
        'acMaleMetalExploratory':ns['box'](mate-u*15,u,15,4.5,12),
    }
    for key,part in moving.items():
        mb=np.asarray(part.bounding_box()).reshape(2,3);volume=0.
        if np.all(mb[0]<bb[1]) and np.all(bb[0]<mb[1]):
            intersection=part^ob
            assert intersection.status()==ns['mf'].Error.NoError
            volume=max(0.,intersection.volume())
        checks.append({'withdrawalMm':s['withdrawalMm'],'moving':key,'overlapMm3':volume})
    if any(r['overlapMm3']>1e-5 for r in checks[-3:]):break
hashes=dict(ns['hashes'])
for f in (Path(__file__),D/'positive-x225-mating-plan.json'):
    hashes[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
report={'spanMm':a.span,'obstacle':a.obstacle,'checks':checks,
        'coverageComplete':len(checks)==len(samples)*3,
        'allClear':len(checks)==len(samples)*3 and all(r['overlapMm3']<=1e-5 for r in checks),
        'sourceHashes':hashes,'assemblyAccepted':False,
        'boundary':'Exact102.5mm length/R10 at61 discrete withdrawal samples; full moving lead and male receiving boxes. Exploratory metal envelope15x12x4.5mm is not measured. Female socket mating contact, self contact, continuous motion and restraints remain separate.'}
(ns['outdir']/(a.obstacle+'-mating.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'matingClear':report['allClear'],'pairs':len(checks),'hits':[r for r in checks if r['overlapMm3']>1e-5][:3]}))
