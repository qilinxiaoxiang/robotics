"""Verify the active design; historical generators cannot accept a newer repair."""
from pathlib import Path
import argparse, subprocess, sys, json, datetime, os
P=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--scope',choices=['design','project'],default='design')
parser.add_argument('--cad-python',default=os.environ.get('MICRODUCK_CAD_PYTHON','/tmp/microduck-cad-venv/bin/python'))
parser.add_argument('--historical-baseline',action='store_true',help='Read an archived result only; never regenerate it or bypass an active repair')
args=parser.parse_args()
context=json.loads((P.parent.parent/'PROJECT-CONTEXT.json').read_text())
# Current design gate (2026-10-13): the guide/ pipeline and the released incremental print set. It supersedes the
# 2026-10-09 enclosed-wiring repair below, whose verifier checks a head layout that was never built.
gate=context.get('current_build',{}).get('design_gate')
if isinstance(gate,dict) and gate.get('verifier') and not args.historical_baseline:
    target=(P.parent.parent/gate['verifier']).resolve()
    if not target.is_file(): raise SystemExit('Design gate verifier is missing: '+str(target))
    raise SystemExit(subprocess.call([sys.executable,str(target),'--scope',args.scope]))
repair=context.get('current_build',{}).get('staged_review_20261009',{}).get('activeRepair')
if repair is not None:
    if not isinstance(repair,dict): raise SystemExit('Invalid activeRepair metadata; refusing historical generators.')
    verifier=repair.get('verifier')
    if verifier:
        target=(P.parent.parent/verifier).resolve()
        if not target.is_file(): raise SystemExit('Active repair verifier is missing: '+str(target))
        raise SystemExit(subprocess.call([sys.executable,str(target),'--scope',args.scope]))
    report={'checked_at':datetime.datetime.now().astimezone().isoformat(),'scope':args.scope,'passed':False,
            'revision':'enclosed-wiring-repair-20261009','physical_tests':0,
            'errors':['The active complete head/harness and incremental print release are not yet accepted. Historical fuse, rooftop-camera and cross-ankle generators cannot verify or overwrite this repair.'],
            'workflow':context['current_build']['staged_review_20261009'].get('workflow'),
            'historicalBaselineRequested':args.historical_baseline,
            'historicalGeneratorsExecuted':False}
    (P/'current-build-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));raise SystemExit(1)
# A historical read is never a write-capable rebuild, even if activeRepair is absent.
if args.historical_baseline:
    historical=P/'historical-baseline-verification.json'
    archived=json.loads(historical.read_text()) if historical.is_file() else None
    report={'scope':args.scope,'passed':False,'historicalBaselineOnly':True,
            'historicalBaselinePassed':bool(archived and archived.get('passed')),
            'historicalReceipt':str(historical) if archived else None,
            'historicalGeneratorsExecuted':False,'physical_tests':0,
            'errors':['Read-only historical result; it does not accept the current design or project.']}
    print(json.dumps(report,indent=2));raise SystemExit(1)
steps=[P/'build_design.py', P.parent/'procurement/build_bom.py',
       P.parent/'procurement/build_cart_plan.py', P.parent/'procurement/test_sourcing.py',
       P.parent/'procurement/verify_pack.py', P/'build_assembly_guide.py', P/'render_guide.py']
results=[]
cad=Path(args.cad_python)
if not cad.is_file():
    raise SystemExit('CAD Python unavailable. Create a venv from requirements-design.txt and pass --cad-python <venv>/bin/python; do not reuse stale geometry reports.')
for name in ['check_harness_reach.py','check_motor_harness_reach.py','check_gpio_housing.py','verify_print_queue.py',
             'fastener-audit/electronics_audit.py','fastener-audit/verify_joint_fasteners.py']:
    result=subprocess.run([str(cad),str(P/name)],capture_output=True,text=True)
    results.append({'step':'redesign-20260913/'+name,'passed':result.returncode==0})
    if result.returncode:
        print(result.stdout+result.stderr);raise SystemExit(result.returncode)
for step in steps:
    result=subprocess.run([sys.executable,str(step)],capture_output=True,text=True)
    results.append({'step':str(step.relative_to(P.parent)), 'passed':result.returncode==0})
    if result.returncode:
        print(result.stdout+result.stderr); raise SystemExit(result.returncode)
result=subprocess.run([sys.executable,str(P/'verify_design.py'),'--scope',args.scope],capture_output=True,text=True)
results.append({'step':'redesign-20260913/verify_design.py','passed':result.returncode==0})
print(result.stdout+result.stderr)
report={'checked_at':datetime.datetime.now().astimezone().isoformat(),'scope':args.scope,'passed':result.returncode==0,'steps':results,'physical_tests':0,'historicalBaselineOnly':bool(repair)}
(P/('historical-baseline-verification.json' if repair else 'current-build-verification.json')).write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(result.returncode)
