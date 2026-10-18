import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from pathlib import Path; H=Path(__file__).parent; d=np.load(H/'cap_samples.npz'); P,N,clr=d['P'],d['N'],d['clr']
pads={'L1':(30,50,12,32),'L2':(2,26,20,34),'R1':(30,50,-32,-12),'R2':(2,26,-34,-20),'M':(42,54,-8,8)}
avoid={'A7Z WiFi antenna (keep 10 mm off)':(64,76,-21,21),'speaker':(-12,18,-10,10),'amplifier':(22,41,-9,9)}
fig,ax=plt.subplots(figsize=(9,6))
m=N[:,2]>0.3
s=ax.scatter(P[m,0],P[m,1],c=np.clip(clr[m],0,15),s=5,cmap='Greys_r',alpha=.6);plt.colorbar(s,label='space under the cap wall (mm)')
for k,(x0,x1,y0,y1) in pads.items():
    ax.add_patch(plt.Rectangle((x0,y0),x1-x0,y1-y0,fc='#d98c1f',alpha=.55,ec='#8a5200'));ax.text((x0+x1)/2,(y0+y1)/2,k,ha='center',va='center',fontsize=11,weight='bold')
for k,(x0,x1,y0,y1) in avoid.items():
    ax.add_patch(plt.Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec='r',ls='--'));ax.text(x0,y1+1.5,k,color='r',fontsize=8)
ax.add_patch(plt.Rectangle((-10,20),15,8,fc='#3b7dd8',alpha=.8));ax.text(-3,41,'XIAO ESP32-S3 (21 x 18) on the inner\nleft-rear wall, z 114-131, tilted 60 deg',fontsize=8,color='#1d4f99',ha='center')
ax.annotate('no pad on the back of the head:\nhead-roll servo 2 mm away',xy=(-27,0),xytext=(-48,-40),arrowprops=dict(arrowstyle='->'),fontsize=8,color='r')
ax.annotate('face / camera',xy=(90,0),xytext=(80,-44),fontsize=8)
ax.set_xlim(-50,100);ax.set_ylim(-48,48);ax.set_aspect('equal');ax.set_xlabel('x (mm, forward)');ax.set_ylabel('y (mm, left)')
ax.set_title('Head cap top view: touch pads = copper tape inside the cap')
plt.tight_layout();plt.savefig(H.parent/'touch_layout.png',dpi=120)
for k,(x0,x1,y0,y1) in pads.items():
    sel=m&(P[:,0]>x0)&(P[:,0]<x1)&(P[:,1]>y0)&(P[:,1]<y1)
    print(k,'samples',sel.sum(),'min clearance %.1f median %.1f'%(clr[sel].min(),np.median(clr[sel])))
sel=(N[:,0]<-0.5)&(P[:,2]>120)&(P[:,2]<135)&(abs(P[:,1])<15);print('N','samples',sel.sum(),'min %.1f med %.1f'%(clr[sel].min(),np.median(clr[sel])))
