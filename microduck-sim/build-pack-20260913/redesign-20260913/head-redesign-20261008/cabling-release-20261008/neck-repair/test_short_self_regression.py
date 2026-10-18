import os,json,hashlib
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
from short_path_worker import self_one
D=Path(__file__).resolve().parent;p=D/'compact-isolated-v2-self-failed/centerline.json';old=json.loads(p.read_text());r=self_one(old['points']);assert not r['passed']
report={'passed':True,'negativeControlDetected':True,'baselineCenterlineSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'detectorSha256':hashlib.sha256((D/'short_path_worker.py').read_bytes()).hexdigest(),'firstFailure':r['failures'][0],'failureSampleTruncated':r['truncated']}
(D/'short-self-negative-control.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
