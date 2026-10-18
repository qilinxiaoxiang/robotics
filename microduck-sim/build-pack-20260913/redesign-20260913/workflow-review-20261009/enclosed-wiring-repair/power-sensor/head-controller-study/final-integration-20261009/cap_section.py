from pathlib import Path
import json,numpy as np,trimesh
F=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study/final-integration-20261009');r=json.loads((F/'joint-package.json').read_text());q=next(q for q in r['parts']if q['key']=='current_cap');m=trimesh.load_mesh(q['file']);svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="900" viewBox="0 0 1000 900"><rect width="100%" height="100%" fill="white"/>'];out=[]
for j,z in enumerate([130,140,146,149]):
 xoff=170+500*(j%2);yoff=170+430*(j//2);s=m.section([0,0,1],[0,0,z]);svg.append(f'<text x="{xoff-120}" y="{yoff-130}" font-size="20">Original closed cap Z={z} mm</text>')
 for line in s.discrete:
  pts=' '.join(f'{xoff+2.6*p[0]},{yoff-2.6*p[1]}' for p in line);svg.append(f'<polyline points="{pts}" fill="none" stroke="#444" stroke-width="1.5"/>')
 for x in [0,13.6219,40,80]:svg.append(f'<line x1="{xoff+2.6*x}" y1="{yoff-110}" x2="{xoff+2.6*x}" y2="{yoff+110}" stroke="#bbb"/><text x="{xoff+2.6*x}" y="{yoff+125}" font-size="10">X{x:.1f}</text>')
 out.append({'z':z,'lines':[x.tolist()for x in s.discrete]})
svg.append('</svg>');(F/'original-cap-sections.svg').write_text(''.join(svg));(F/'original-cap-sections.json').write_text(json.dumps(out))
