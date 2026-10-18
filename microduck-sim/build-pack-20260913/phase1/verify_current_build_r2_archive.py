"""Regenerate and verify the current hardware handoff from canonical selections."""
from pathlib import Path
import subprocess,sys,json,datetime,argparse
P=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--scope',choices=['project','bringup'],default='project')
args=parser.parse_args()
steps=['test_project_context.py','../procurement/build_bom.py','../procurement/build_cart_plan.py','../procurement/test_sourcing.py','../procurement/test_system.py','../procurement/test_compare_orders.py','../procurement/compare_orders.py','power_screen.py','../procurement/verify_pack.py','build_guide.py','verify_guide.py']
results=[]
for step in steps:
 result=subprocess.run([sys.executable,str(P/step)],capture_output=True,text=True)
 results.append({'step':step,'passed':result.returncode==0})
 if result.returncode:
  print(result.stdout+result.stderr);raise SystemExit(result.returncode)
goal=subprocess.run([sys.executable,str(P/'check_project_context.py'),'--scope',args.scope],capture_output=True,text=True)
results.append({'step':'check_project_context.py','passed':goal.returncode==0})
context=json.loads((P/'project-context-review.json').read_text())
r={'checked_at':datetime.datetime.now().astimezone().isoformat(),'revision':'phase1-single-source-r2','scope':args.scope,'passed':goal.returncode==0,'project_handoff_ready':context['project_handoff_ready'],'steps':results,'physical_tests':0,'orders_placed_by_assistant':False}
(P/'audit-20260913/repair-verification.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
if goal.returncode:
 print(goal.stdout+goal.stderr)
 raise SystemExit(goal.returncode)
