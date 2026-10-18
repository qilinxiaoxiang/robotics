"""Orange-only manifest copy of V1.6 with a new head_cap sourceToPrint. Other Orange parts unchanged; Orange placements
dropped so the pipeline's arrange() lays the plate out with 12 mm model gaps (the cap footprint changed).
Usage: make_manifest.py POSE_NAME OUT.json [CAP_STL]"""
import json, sys, hashlib, numpy as np
from pathlib import Path
P = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print')
m = json.load(open(P / 'release-V1.6/complete-incremental-V1.6.json'))
poses = {r['name'].split(' ')[0]: r for r in json.load(open(P / 'release-V1.6-cap-pose/pose-candidates.json'))}
pose = poses[sys.argv[1]]
m['parts'] = [p for p in m['parts'] if p['color'] == 'Orange']
cap = next(p for p in m['parts'] if p['key'] == 'head_cap')
if len(sys.argv) > 3:
    cap['path'] = str(Path(sys.argv[3]).resolve()); cap['sha256'] = hashlib.sha256(open(sys.argv[3], 'rb').read()).hexdigest()
T = np.array(pose['sourceToPrint']); assert np.allclose(T[:3, :3].T @ T[:3, :3], np.eye(3), atol=1e-9)
cap['sourceToPrint'] = T.tolist()
cap['poseNote'] = f"{pose['name']}: bed-facing robot-frame direction {pose['bedFacingWorldDir']}; flat contact {pose['flatContactMm2']} mm2 within 0.02 mm, hull {pose['hullMm2']} mm2, height {pose['heightMm']} mm, CoM height {pose['comHeightMm']} mm."
cap['flatContact'] = {'minimumAreaMm2': 100}
m.pop('placements', None)
m['prototypeScope'] = 'V1.6 Orange plate only, head_cap re-posed for a stable bed face (' + pose['name'] + '). ' + m['prototypeScope']
json.dump(m, open(sys.argv[2], 'w'), indent=1)
print(sys.argv[2], [p['key'] for p in m['parts']], cap['sha256'])
