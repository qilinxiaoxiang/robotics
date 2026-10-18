"""One exploratory span: whole-cable self/contact checks while mating USB-A."""
from pathlib import Path
import hashlib,json,os,runpy,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent
ns=runpy.run_path(str(D/'check_planned_usb.py'))
a=ns['args'];assert a.obstacle=='self'
np=ns['np'];p=ns['plan'];u=np.asarray(p['scFinalDirection']);row=ns['row']
plan=json.loads((D/'positive-x225-mating-plan.json').read_text())
for f,h in plan['sourceHashes'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
samples=next(r['samples'] for r in plan['rows'] if r['spanMm']==a.span)
from check_cable_self import check as self_check
fixed={k:s for k,s in ns['parts'].items() if k.startswith('sc') or k=='acUsbCReceiving'}
checks=[];last_markers=None;max_shift=0.
for sample in samples:
    points,L=ns['fillet_polyline'](sample['waypointsMm'],10)
    end=p['cEndArc'];arc,arcL=ns['circular_arc'](end['startMm'],end['incoming'],end['outgoing'],10)
    points=np.vstack([points,arc[-2::-1]]);assert abs(L+arcL-102.5)<1e-7
    mate=np.asarray(row['usbAMatingPointMm'])+u*sample['withdrawalMm']
    flex=ns['solid'](ns['tube'](points,4.5,start_tangent=u,end_tangent=-np.asarray(end['incoming'])))
    moving={'acFlexibleReceiving':flex,'acMaleReceiving':ns['box'](mate,u,22.9,12,20),
            'acMaleMetalExploratory':ns['box'](mate-u*15,u,15,4.5,12)}
    pairs=[]
    for key,solid in moving.items():
        for other,ob in fixed.items():
            if key=='acMaleMetalExploratory' and other=='scFemaleReceiving':
                # This solid female envelope has no socket cutout. Preserve the
                # mating overlap separately instead of silently treating it clear.
                continue
            overlap=solid^ob;assert overlap.status()==ns['mf'].Error.NoError
            pairs.append({'moving':key,'other':other,'overlapMm3':max(0.,overlap.volume())})
    overlap=moving['acMaleReceiving']^flex
    assert overlap.status()==ns['mf'].Error.NoError
    pairs.append({'moving':'acFlexibleReceiving','other':'acMaleReceiving','overlapMm3':max(0.,overlap.volume())})
    nonlocal_check=self_check(points,4.5,10)
    # Fixed normalized arc markers detect topology/root jumps between samples.
    # Exact length is proved analytically above; chord markers are only a
    # numerical continuity diagnostic, not an inter-sample motion proof.
    lengths=np.linalg.norm(np.diff(points,axis=0),axis=1);s=np.r_[0,np.cumsum(lengths)]
    marks=np.column_stack([np.interp(np.linspace(0,s[-1],501),s,points[:,i]) for i in range(3)])
    if last_markers is not None:max_shift=max(max_shift,float(np.linalg.norm(marks-last_markers,axis=1).max()))
    last_markers=marks
    mating_overlap=max(0.,(moving['acMaleMetalExploratory']^fixed['scFemaleReceiving']).volume())
    checks.append({'withdrawalMm':sample['withdrawalMm'],'pairs':pairs,'nonlocalCable':nonlocal_check,
                   'intendedMetalFemaleReceivingOverlapMm3':mating_overlap,
                   'clearOutsideMatingInterface':all(x['overlapMm3']<=1e-5 for x in pairs) and nonlocal_check['allClear']})
    if not checks[-1]['clearOutsideMatingInterface']:break
hashes=dict(ns['hashes'])
for f in (Path(__file__),D/'positive-x225-mating-plan.json',D/'check_cable_self.py'):
    hashes[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
out={'spanMm':a.span,'checks':checks,'coverageComplete':len(checks)==len(samples),
     'clearOutsideMatingInterface':len(checks)==len(samples) and all(r['clearOutsideMatingInterface'] for r in checks),
     'maximumAdjacentMarkerDisplacementMm':max_shift,'sourceHashes':hashes,'assemblyAccepted':False,
     'boundary':'Sampled whole cable/plug mating motion, with analytic constant length. The female socket is a solid receiving envelope; intended metal insertion is reported, not certified. Physical mating depth, force, strain and inter-sample motion remain unverified.'}
(ns['outdir']/'mating-self.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'clearOutsideMatingInterface':out['clearOutsideMatingInterface'],'completed':len(checks),'maximumMarkerStepMm':max_shift}))
