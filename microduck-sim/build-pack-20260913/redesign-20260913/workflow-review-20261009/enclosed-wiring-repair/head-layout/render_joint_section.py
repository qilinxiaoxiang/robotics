import os,json,sys
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
D=Path(__file__).resolve().parent;R=D.parents[2];H=R/'head-redesign-20261008';W=R/'workflow-review-20261009'
rows={r['key']:r for r in json.loads((W/'original-body-converter/fusion-import-manifest.json').read_text())['parts']};case=json.loads((D/'joint-first/report.json').read_text())['candidate'];Tp=np.array(case['pi']['currentWorldDelta']);Tr=np.array(case['openrb']['currentWorldDelta']);fig,axs=plt.subplots(1,3,figsize=(15,6));axes=[(0,1),(0,2),(1,2)]
def draw(path,color,alpha=.3,T=None,label=None):
 m=tm.load(path,force='mesh');v=np.asarray(m.vertices)
 if T is not None:v=v@T[:3,:3].T+T[:3,3]
 for ax,(a,b) in zip(axs,axes):
  p=v[:,[a,b]]
  try:q=p[ConvexHull(p).vertices];ax.fill(q[:,0],q[:,1],color=color,alpha=alpha,label=label);ax.plot(*np.vstack((q,q[0])).T,color=color,lw=.6)
  except Exception:pass
for k in ['jaw_support','motor15','camera_board','camera_retainer']:
 draw(rows[k]['file'],'#777777',.18,label=k)
draw(D/'native-cap-registered-world.stl','#d97c1c',.07,label='Closed original cap silhouette')
draw(rows['amplifier']['file'],'#cb2233',.35,label='Existing amplifier')
draw(rows['pi']['file'],'#226db0',.45,Tp,'Pi PCB / components')
for k in rows:
 if k.startswith('gpio_pin_'):draw(rows[k]['file'],'#226db0',.5,Tp)
ep=json.loads((H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json').read_text())
for row in ep['components']:draw(row['mesh'],'#20975d',.22,Tr)
draw(H/'usb-access/full-harness/openrb-usb-c-published-envelope-world.stl','#683a99',.6,Tr,'Seated USB-C plug')
for ax,(a,b) in zip(axs,axes):
 ax.set_aspect('equal');ax.set_xlabel('XYZ'[a]+' (mm)');ax.set_ylabel('XYZ'[b]+' (mm)');ax.grid(alpha=.2);ax.set_xlim((-35,95) if a==0 else(-50,50));ax.set_ylim((-50,50) if b==1 else(105,162))
axs[0].legend(fontsize=7,loc='lower left');fig.suptitle('Packaging diagnosis: first stacked candidate — not accepted\nActual component projections; cap outline is a silhouette, not its inner clearance boundary')
fig.tight_layout();fig.savefig(D/'joint-first/packaging-three-views.png',dpi=150)
