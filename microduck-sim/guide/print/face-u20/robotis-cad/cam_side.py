import numpy as np, trimesh, json, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MP
B='omxf-step/'; W='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
AY,AZ=json.load(open('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/face-u20/checks.json'))['axis']['used']
P={'face panel (White)':(trimesh.load(W+'face_panel.stl'),'#cfcfcf'),'eye trim (Black)':(trimesh.load(W+'eye_trim.stl'),'#333333')}
fig,axs=plt.subplots(1,2,figsize=(15,6.2))
for ax,(f,t) in zip(axs,[('u20cam-world-B_v130_board.stl','V1.30 as printed: board where the bosses end now\nlens front x 95.6, sticks out 6.2 mm past the trim'),
                         ('u20cam-world-A_flush.stl','Fix: board 6.6 mm further back, bosses 14.3 mm long\nlens front x 89.0, flush with the trim as designed')]):
    parts=dict(P); parts['U20CAM, ROBOTIS OMX-F CAD']=(trimesh.load(B+f),'#1e88e5')
    for lab,(m,col) in parts.items():
        s=m.section(plane_origin=[0,AY,0],plane_normal=[0,1,0])
        if s is None: continue
        for d in s.discrete:
            ax.fill(d[:,0],d[:,2],fc=col,ec=col,alpha=.75,label=lab)
    ax.axvline(89.4,color='r',ls='--',lw=1,label='trim front x 89.4')
    ax.set_xlim(55,100); ax.set_ylim(AZ-22,AZ+22); ax.set_aspect('equal'); ax.grid(alpha=.3); ax.set_title(t,fontsize=11); ax.set_xlabel('x mm (forward)'); ax.set_ylabel('z mm (up)')
h,l=axs[0].get_legend_handles_labels(); u=dict(zip(l,h)); fig.legend(u.values(),u.keys(),loc='lower center',ncol=4)
fig.suptitle('Side cut through the eye (camera model from ROBOTIS OMX-AI-Follower.stp, part CAMERA_INNOMAKER_720P)',fontsize=12)
plt.tight_layout(rect=(0,.07,1,.95)); plt.savefig(sys.argv[1],dpi=85)
