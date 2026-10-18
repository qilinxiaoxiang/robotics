"""Short-lived CAD workers; one source obstacle per child, no scene cache."""
from pathlib import Path
import os,json,subprocess,sys,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent;cfg=json.loads((H/'viewer-candidate.json').read_text());cache=json.loads((D/'head-source-cache/index.json').read_text());keys=list(dict.fromkeys(list(cache['parts'])+list(cfg['replacementMeshes'])+[p['key'] for p in cfg['additionalParts']]));skip=set(cfg['removedParts'])|{'pi','zero_w_populated_receiving','pi_usb_receiving'};keys=[k for k in keys if k not in skip]
p=D/'inboard-pose-pair-checks.json'
if p.exists():p.unlink()
for i,k in enumerate(keys):subprocess.run([sys.executable,str(D/'check_inboard_pose.py'),k]+(['--export'] if i==len(keys)-1 else []),check=True)
r=json.loads(p.read_text());r['status']='ALL_SINGLE_OBSTACLE_CHECKS_COMPLETE_NOT_ASSEMBLY_RELEASE';r['completedAllObstacles']=True;r['allObstacleKeys']=keys;r['sourceHashes'][str(Path(__file__).resolve())]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();r['sourceHashes'][str((D/'check_inboard_pose.py').resolve())]=hashlib.sha256((D/'check_inboard_pose.py').read_bytes()).hexdigest();p.write_text(json.dumps(r,indent=2)+'\n');print('DONE',len(keys),'obstacles',len(r['remainingPairs']),'contacts')
