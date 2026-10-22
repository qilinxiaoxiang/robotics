import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family']='PingFang SC'
exec(open('rear_free.py').read().split("ss=np.arange")[0].replace("sys.argv","[0,'x']"))
z=np.load('free.npz',allow_pickle=True); S,D,R=z['S'],z['D'],z['rear']
K=8.0; HS=13.0; FAN=16.0
COL={'jaw_support':'#c0392b','motor15':'#c0392b','clip_head':'#c0392b','camera_board':'#2ca02c','speaker':'#1f77b4','speaker_retainer':'#1f77b4'}
fig,axs=plt.subplots(1,3,figsize=(19,6.0),gridspec_kw={'width_ratios':[1,1,1.05]})
def section(ax,y0,title,new=True):
    for k,m in ms.items():
        sec=m.section(plane_origin=[0,y0,0],plane_normal=[0,1,0])
        if sec is None: continue
        c=COL.get(k,'#888'); lw=1.6 if c=='#c0392b' else 0.8
        for e in sec.discrete: ax.plot(e[:,0],e[:,2],color=c,lw=lw)
    s=O[1]-y0; P=lambda d,h: O+s*ES+d*ED+h*N
    poly=lambda pts,**kw: ax.fill(np.array(pts)[:,0],np.array(pts)[:,2],**kw)
    old=[P(0,0),P(30,0),P(30,1.6),P(0,1.6)]; poly(old,fc='none',ec='#2e7d32',ls='--',lw=1,label='现在的板子位置')
    poly([P(0,K),P(30,K),P(30,K+1.6),P(0,K+1.6)],color='#2e7d32',label='新位置：芯片朝后，往前挪 8 mm')
    poly([P(0,K+1.6),P(30,K+1.6),P(30,K+5.5),P(0,K+5.5)],color='#b7e1b9',alpha=0.6,label='板子背面零件（摄像头插座 3.9 mm）')
    poly([P(0,K),P(24,K),P(24,K-HS),P(0,K-HS)],color='#e67e22',alpha=0.55,label='6530B（13 mm）')
    poly([P(0,K-HS),P(24,K-HS),P(24,K-FAN),P(0,K-FAN)],color='#f5cba7',alpha=0.6,hatch='//',label='风扇进风 3 mm')
    poly([P(24.5,K),P(29.5,K),P(29.5,K-17),P(24.5,K-17)],color='#8e44ad',alpha=0.35,label='排针 + 杜邦插头朝后（17 mm）')
    ax.set_title(title,fontsize=12); ax.set_aspect('equal'); ax.set_xlim(-15,95); ax.set_ylim(95,162); ax.grid(alpha=0.2)
    ax.set_xlabel('x（mm，向右是机器人前方）'); ax.set_ylabel('z（mm，向上）')
section(axs[0],4.4,'剖面 y = 4.4 mm（穿过芯片）')
axs[0].annotate('摄像头',xy=(76,128),xytext=(80,104),color='#2ca02c',arrowprops=dict(arrowstyle='->',color='#2ca02c'))
axs[0].annotate('下巴机构，这里已经够了',xy=(51,120),xytext=(-12,103),color='#c0392b',arrowprops=dict(arrowstyle='->',color='#c0392b'))
axs[0].legend(loc='upper left',fontsize=8)
section(axs[1],20.0,'剖面 y = 20 mm（靠 1 号针那头）')
axs[1].annotate('下巴舵机 motor15',xy=(50,122),xytext=(-12,103),color='#c0392b',arrowprops=dict(arrowstyle='->',color='#c0392b'))
ax=axs[2]; RR=R+K
im=ax.imshow(np.clip(RR,0,30).T,origin='lower',extent=[0,65,0,30],cmap='RdYlGn',vmin=0,vmax=26,aspect='equal')
cs=ax.contour(S,D,RR,levels=[HS,FAN],colors=['k','k'],linestyles=['-','--'],linewidths=1.2); ax.clabel(cs,fmt={HS:'13',FAN:'16'},fontsize=9)
ax.add_patch(plt.Rectangle((0,0),65,24,fill=False,ec='#e67e22',lw=2.5)); ax.add_patch(plt.Rectangle((0,24),65,6,fill=False,ec='#8e44ad',lw=2))
ax.text(33,27,'排针（插头朝后，95% 够 17 mm）',ha='center',fontsize=9.5,bbox=dict(fc='white',ec='none',alpha=0.8))
ax.text(36,5,'左下角（下巴舵机）和右下两小块\n还差 0-3.4 mm，其余够',ha='center',fontsize=10,bbox=dict(fc='white',ec='none',alpha=0.8))
ax.text(2.5,15,'两端：头盖\n导轨，要重画',fontsize=8.5,color='white')
ax.set_title('新位置下板子背后有多深（mm）\n橙框 = 6530B，紫框 = 排针；实线 13 mm，虚线 16 mm',fontsize=11)
ax.set_xlabel('沿板子长边（mm）'); ax.set_ylabel('从板子下边往上（mm）')
plt.colorbar(im,ax=ax,fraction=0.03,pad=0.02,label='背后空间 mm')
fig.suptitle('芯片朝后、和摄像头背靠背（往前挪 8 mm，排针在上）：6530B 91% 放得下，只有 1 号针那头的下角被下巴舵机挡住 3.4 mm 以内（只看现有 CAD）',fontsize=13.5)
plt.tight_layout(); plt.savefig('back-to-back.png',dpi=120,bbox_inches='tight')
