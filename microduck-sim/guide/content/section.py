import pickle, numpy as np, trimesh, sys, json
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
s=pickle.load(open(sys.argv[1],'rb')); cfg=json.loads(sys.argv[2])
axis=cfg['axis']; vals=cfg['values']; keys=cfg.get('keys'); out=cfg['out']; lim=cfg.get('lim')
n={'x':[1,0,0],'y':[0,1,0],'z':[0,0,1]}[axis]
dims={'x':(1,2),'y':(0,2),'z':(0,1)}[axis]
fig,axs=plt.subplots(1,len(vals),figsize=(7*len(vals),7))
if len(vals)==1: axs=[axs]
for ax,val in zip(axs,vals):
    for k,p in s.items():
        if keys and k not in keys and p.get('module') not in keys: continue
        m=trimesh.Trimesh(p['v'].astype(float),p['f'],process=False)
        o=[0,0,0]; o['xyz'.index(axis)]=val
        sec=m.section(plane_origin=o,plane_normal=n)
        if sec is None: continue
        c=np.array(p['color'])/255
        for ent in sec.entities:
            pts=sec.vertices[ent.points][:,dims]
            ax.fill(pts[:,0],pts[:,1],color=c,alpha=0.5,lw=0.5,ec='k')
        cen=sec.vertices[:,dims].mean(0)
        ax.text(cen[0],cen[1],k[:14],fontsize=6)
    ax.set_aspect('equal'); ax.grid(True,lw=0.3); ax.set_title(f'{axis}={val}')
    if lim: ax.set_xlim(lim[0]); ax.set_ylim(lim[1])
plt.tight_layout(); plt.savefig(out,dpi=110)
