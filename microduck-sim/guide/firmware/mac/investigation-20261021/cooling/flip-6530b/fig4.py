"""Proposed back-to-back pose (vertical, header on top, rear face x = 68) with the 6530B envelope and the front-ear mounting."""
import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
plt.rcParams['font.family']='PingFang SC'
exec(open('b2b_fit.py').read().split("ss=np.arange")[0])
XC=68.0; T=1.6
HIDE=('clip_cap','clip_head')
fig,axs=plt.subplots(1,3,figsize=(20,7),gridspec_kw={'width_ratios':[1,1,0.95]})
def sec(ax,y0,title):
    for k,m in ms.items():
        if k in HIDE: continue
        s_=m.section(plane_origin=[0,y0,0],plane_normal=[0,1,0])
        if s_ is None: continue
        c={'camera_board':'#2ca02c','jaw_support':'#b03a2e','motor15':'#b03a2e','amplifier':'#7d3c98'}.get(k,'#999')
        for e in s_.discrete: ax.plot(e[:,0],e[:,2],color=c,lw=0.8)
    R=lambda x0,x1,z0,z1,**kw: ax.add_patch(Rectangle((x0,z0),x1-x0,z1-z0,**kw))
    s=Y1-y0
    R(XC,XC+T,ZTOP-30,ZTOP,color='#2e7d32')
    R(XC+T,XC+T+2,ZTOP-30+9,ZTOP-30+20,color='#7fb3d5')                 # underside parts band (CSI / microSD)
    if 0<=s<=65:
        legs=s<7 or s>58
        R(XC-11.5,XC,ZTOP-30,ZTOP-(0 if legs else 6),color='#2b2b2b',alpha=0.55)
        if 4<=s<=27: R(XC-14.5,XC-11.5,ZTOP-29,ZTOP-7,fc='#f5cba7',alpha=0.7,hatch='//')
        if 7<=s<=58: R(XC-17,XC,ZTOP-5.5,ZTOP-0.5,color='#8e44ad',alpha=0.4)
    ax.set_aspect('equal'); ax.set_xlim(-15,95); ax.set_ylim(98,160); ax.grid(alpha=0.15); ax.set_title(title,fontsize=12)
    ax.set_xlabel('x（mm，向右是机器人前方）'); ax.set_ylabel('z（mm，向上）')
sec(axs[0],4.4,'剖面 y = 4.4（板子中间）')
a=axs[0]
a.annotate('6530B（黑）',xy=(62,125),xytext=(30,104),arrowprops=dict(arrowstyle='->'))
a.annotate('杜邦插头朝后',xy=(56,142),xytext=(22,156),arrowprops=dict(arrowstyle='->'))
a.annotate('下巴舵机座：离散热器 4.2 mm，\n离风扇进风区 1.2 mm',xy=(52,129),xytext=(-12,112),color='#b03a2e',arrowprops=dict(arrowstyle='->',color='#b03a2e'))
a.annotate('摄像头，板子背面离它 5.1 mm',xy=(75,135),xytext=(52,104),color='#2ca02c',arrowprops=dict(arrowstyle='->',color='#2ca02c'))
sec(axs[1],29.0,'剖面 y = 29（穿过 1 号针那头的两个孔）')
b=axs[1]
for zz in (ZTOP-3.5,ZTOP-26.5):
    b.add_patch(Rectangle((XC+T,zz-3.2),2.0,6.4,color='#e74c3c'))          # printed ear in front of the board
    b.plot([XC+T+2+1.4,XC-2.4],[zz,zz],color='k',lw=2.2); b.add_patch(Rectangle((XC+T+2,zz-1.9),1.4,3.8,color='k'))
b.annotate('头盖伸出的"耳朵"（红）\nM2×6 从前面穿过耳朵、板子孔，\n拧进 6530B 自带的螺纹孔',xy=(XC+3,ZTOP-3.5),xytext=(4,150),fontsize=9.5,arrowprops=dict(arrowstyle='->'))
c=axs[2]; c.set_title('从前面看（面板和摄像头拿掉）',fontsize=12)
c.add_patch(Rectangle((-32.5,ZTOP-30),65,30,color='#2e7d32',alpha=0.35))
c.add_patch(Rectangle((-16.1,ZTOP-29.5),32.2,32,fc='none',ec='#2ca02c',lw=2,ls='--')); c.text(0,ZTOP+4,'摄像头 32×32 位置',color='#2ca02c',ha='center')
for s_,d_ in [(3.5,3.5),(3.5,26.5),(61.5,3.5),(61.5,26.5)]:
    y=Y1-s_; z=ZTOP-d_
    c.add_patch(Rectangle((y-4.5,z-3.2),9.0,6.4,color='#e74c3c',alpha=0.85))
    c.add_patch(Circle((y,z),1.1,color='k'))
c.text(0,ZTOP-15,'板子背面（摄像头插座、microSD 朝你）',ha='center',fontsize=9)
c.text(-40,ZTOP-37,'红块 = 头盖伸出的耳朵；右边 = 1 号针那头（机器人左边）',fontsize=8.5,color='#555')
c.set_xlim(-46,46); c.set_ylim(ZTOP-40,ZTOP+8); c.set_aspect('equal'); c.axis('off')
fig.suptitle('定案候选：竖直、背靠背、排针在上、板子背面 x = 68；6530B 处处够（下巴座最近 1.2 mm，头盖导轨要重画）',fontsize=13.5)
plt.tight_layout(); plt.savefig('b2b-mount.png',dpi=120,bbox_inches='tight')
