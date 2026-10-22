"""Change sketch for the back-to-back A7Z layout (board turned 180 deg about its long axis, header on top, 8 mm forward).
Read-only: fixed head parts from guide-data; board parts from build_a7z_head.py's measured TOP/BOTTOM boxes."""
import numpy as np, matplotlib, sys
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
plt.rcParams['font.family']='PingFang SC'
exec(open('rear_free.py').read().split("ss=np.arange")[0].replace("sys.argv","[0,'x']"))
src=open('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/a7z-head/build_a7z_head.py').read()
TOP=eval(src.split('TOP = ')[1].split('\n}')[0]+'\n}'); BOT=eval(src.split('BOTTOM = ')[1].split('\n}')[0]+'\n}')
K=8.0; T=1.6
def Pold(s,d,h): return O+s*ES+d*ED+h*N
def Pnew(s,d,h): return O+s*ES+(30-d)*ED+(T-h+K)*N        # turn about the long axis, then 8 mm forward
MOVED=('clip_cap','clip_head','camera_ribbon','antenna_coax')
fig=plt.figure(figsize=(20,7.4)); g=fig.add_gridspec(1,3,width_ratios=[1,1,1.15])
def fixed(ax,y0,skip=()):
    for k,m in ms.items():
        if k in skip: continue
        sec=m.section(plane_origin=[0,y0,0],plane_normal=[0,1,0])
        if sec is None: continue
        c={'camera_board':'#2ca02c','jaw_support':'#b03a2e','motor15':'#b03a2e'}.get(k,'#999')
        for e in sec.discrete: ax.plot(e[:,0],e[:,2],color=c,lw=0.8)
def quad(ax,P,s,d0,d1,h0,h1,**kw):
    q=np.array([P(s,d0,h0),P(s,d1,h0),P(s,d1,h1),P(s,d0,h1)]); ax.fill(q[:,0],q[:,2],**kw)
def board(ax,P,y0,new):
    s=O[1]-y0
    quad(ax,P,s,0,30,0,T,color='#2e7d32')
    quad(ax,P,s,10,25.3,T,T+1.6,color='#555')                       # SoC
    quad(ax,P,s,0,5,T,T+8.5,color='#222')                           # header pins
    quad(ax,P,s,0,5,T+2.5,T+14.5,color='#8e44ad',alpha=0.45)         # Dupont plugs
    if new: quad(ax,P,s,10.2,25.2,T+1.6,T+1.6+5,color='#d35400',alpha=0.75)   # 15x15x5 copper sink
def deco(ax,title):
    ax.set_aspect('equal'); ax.set_xlim(-12,92); ax.set_ylim(98,160); ax.grid(alpha=0.15); ax.set_title(title,fontsize=12.5)
    ax.set_xlabel('x（mm，向右是机器人前方）'); ax.set_ylabel('z（mm，向上）')
a=fig.add_subplot(g[0]); fixed(a,4.4); board(a,Pold,4.4,False); deco(a,'现在：芯片朝前，排针在下，杜邦线往前插')
a.annotate('摄像头',xy=(76,126),xytext=(80,104),color='#2ca02c',arrowprops=dict(arrowstyle='->',color='#2ca02c'))
a.annotate('杜邦插头（紫）\n夹在板子和摄像头之间',xy=(68,118),xytext=(10,152),arrowprops=dict(arrowstyle='->'),fontsize=9.5)
b=fig.add_subplot(g[1]); fixed(b,4.4,MOVED); board(b,Pnew,4.4,True); deco(b,'改后：芯片朝后，排针在上，背面贴着摄像头')
def tag(ax,n,xy,txt=None,off=(0,0)):
    ax.add_patch(Circle(xy,2.6,color='#c0392b',zorder=5)); ax.text(xy[0],xy[1],str(n),color='white',ha='center',va='center',fontsize=9,zorder=6)
    if txt: ax.text(xy[0]+3.6+off[0],xy[1]+off[1],txt,fontsize=9,va='center',zorder=6)
tag(b,4,(50,149)); tag(b,5,(54,128)); tag(b,6,(71.8,134)); tag(b,9,(58,155))
b.plot([Pold(28,0,0)[0],Pold(28,30,0)[0]],[Pold(28,0,0)[2],Pold(28,30,0)[2]],ls='--',color='#2e7d32',lw=1)
b.text(2,103,'绿色虚线 = 现在的板子位置；红圈编号见清单',fontsize=9,color='#2e7d32')
c=fig.add_subplot(g[2]); c.set_title('改后从后面看板子（芯片面朝你；虚线是朝摄像头那面的零件）',fontsize=12)
c.add_patch(Rectangle((0,0),65,30,color='#2e7d32',alpha=0.25))
for (s_,d_) in [(3.5,3.5),(3.5,26.5),(61.5,3.5),(61.5,26.5)]:
    c.add_patch(Circle((s_,30-d_),1.375,fc='white',ec='k')); c.add_patch(Circle((s_,30-d_),3.0,fc='none',ec='#c0392b',lw=1.5))
names={'wifi_module_fcu760k':'Wi-Fi','soc_a733':'A733 芯片','ram':'内存','pmic_area':'电源','micro_hdmi':'HDMI','usb_c_otg_dp':'USB-C','usb_c_power':'USB-C J16',
       'fan_connector':'','ipex_socket':''}
for k,(s0,s1,d0,d1,hh) in TOP.items():
    c.add_patch(Rectangle((s0,30-d1),s1-s0,d1-d0,fc='#bbb',ec='k',lw=0.6)); c.text((s0+s1)/2,30-(d0+d1)/2,names.get(k,k),ha='center',va='center',fontsize=8)
for k,(s0,s1,d0,d1,hh) in BOT.items():
    c.add_patch(Rectangle((s0,30-d1),s1-s0,d1-d0,fc='none',ec='#1f618d',ls='--',lw=1.1))
c.text(-0.5,30-23.5,'摄像头插座（朝前）',fontsize=7.5,color='#1f618d',rotation=90); c.text(52,30-22,'microSD（朝前）',fontsize=7.5,color='#1f618d')
c.add_patch(Rectangle((8.37-1.3,25),52.5,5,fc='#222',alpha=0.7)); c.text(34,27.5,'40 针排针（插头朝你）',color='white',ha='center',va='center',fontsize=8.5)
c.add_patch(Rectangle((20.4-0.3,30-25.5),15.6,15.6,fc='none',ec='#d35400',lw=2)); c.text(28.1,3.2,'15 mm 铜散热片',color='#d35400',ha='center',fontsize=8)
tag(c,1,(-4,15)); tag(c,1,(69,15)); c.text(-9,22.5,'① 四个孔的固定垫',fontsize=8.5)
tag(c,2,(2,-4.5),'摄像头插座直对摄像头，排线短 U 形',off=(0,0))
tag(c,3,(60,-4.5)); c.text(43,-9.5,'③ microSD 槽往前挪',fontsize=8.5)
tag(c,7,(2,34),'左边两个小方块：天线座、风扇座（都在朝你这面）',off=(0,0))
tag(c,8,(48,-12)); c.text(51.6,-12,'⑧ USB-C 口朝下了',fontsize=8.5,va='center')
c.set_xlim(-12,72); c.set_ylim(-16,38); c.set_aspect('equal'); c.axis('off')
c.text(-11,-15.5,'左 = 1 号针那头（机器人左边）     下 = 朝脖子',fontsize=8.5,color='#555')
fig.suptitle('背靠背布局要改的地方（示意图，零件和 CAD 都没改）',fontsize=14)
plt.tight_layout(); plt.savefig('change-sketch.png',dpi=120,bbox_inches='tight')
