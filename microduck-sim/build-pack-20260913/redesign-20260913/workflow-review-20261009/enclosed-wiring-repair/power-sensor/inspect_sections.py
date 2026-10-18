from pathlib import Path
import json,trimesh
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent;W=D.parents[1]
obs={p['key']:p for p in json.loads((W/'original-body-converter/fusion-import-manifest.json').read_text())['parts']}
fig,axes=plt.subplots(1,2,figsize=(12,6));keys=['power_support','regulator_insert','shell_left','shell_right','regulator','motor5','motor10','torso_base']
colors=dict(zip(keys,['#287ab4','#d12cb7','#777777','#ff9800','#4eaa55','#111111','#111111','#a26220']))
for key in keys:
 p=obs[key];m=trimesh.load(p['file'],force='mesh');m.apply_translation(p.get('importTranslationMm',[0,0,0]))
 for ax,origin,normal,idx in [(axes[0],[-22,0,0],[1,0,0],[1,2]),(axes[1],[0,-6,0],[0,1,0],[0,2])]:
  s=m.section(plane_origin=origin,plane_normal=normal)
  if s is not None:
   for n,line in enumerate(s.discrete):ax.plot(line[:,idx[0]],line[:,idx[1]],label=key if n==0 else None,color=colors[key])
for ax in axes:ax.set_aspect('equal');ax.grid();ax.legend(fontsize=7)
axes[0].set(xlabel='Y mm',ylabel='Z mm',title='X = -22: existing bracket cross-section',ylim=(-40,50),xlim=(-40,40))
axes[1].set(xlabel='X mm',ylabel='Z mm',title='Y = -6: true roof and support clearance',xlim=(-50,10),ylim=(20,50))
fig.tight_layout();fig.savefig(D/'structural-sections.png',dpi=130)
