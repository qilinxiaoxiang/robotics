import json, base64, numpy as np, trimesh, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ('PingFang SC','Hiragino Sans GB','Arial Unicode MS','Heiti SC','STHeiti'):
    if any(f==x.name for x in font_manager.fontManager.ttflist): plt.rcParams['font.family']=f; break
exec(open('rear_free.py').read().split("ss=np.arange")[0].replace("sys.argv","[0,'x']"))
z=np.load('free.npz',allow_pickle=True); S,D,R=z['S'],z['D'],z['rear']
HS=13.0; FAN=16.0; D0=6.0   # 6530B: body depth from the component face incl. pad; plus 3 mm fan inlet gap; header strip d<6 left open
GREY={'head_cap':'#555','head_bottom':'#555','jaw_support':'#c0392b','motor15':'#c0392b','jaw_frame':'#999','amplifier':'#777','speaker':'#1f77b4',
      'speaker_retainer':'#1f77b4','camera_board':'#2ca02c','face_panel':'#333','eye_trim':'#333','clip_head':'#c0392b','motor13':'#aaa','head_yaw_link':'#aaa'}
fig,axs=plt.subplots(1,3,figsize=(19,6.0),gridspec_kw={'width_ratios':[1,1,1.05]})
def section(ax,y0,title):
    for k,m in ms.items():
        sec=m.section(plane_origin=[0,y0,0],plane_normal=[0,1,0])
        if sec is None: continue
        c=GREY.get(k,'#bbb'); lw=1.6 if c=='#c0392b' else 0.8
        for e in sec.discrete: ax.plot(e[:,0],e[:,2],color=c,lw=lw)
    s=(O[1]-y0)  # s along -y from the pin-1 end
    P=lambda d,h: O+s*ES+d*ED+h*N
    pcb=np.array([P(0,0),P(30,0),P(30,1.6),P(0,1.6),P(0,0)]); ax.fill(pcb[:,0],pcb[:,2],color='#2e7d32')
    hs=np.array([P(D0,0),P(30,0),P(30,-HS),P(D0,-HS),P(D0,0)]); ax.fill(hs[:,0],hs[:,2],color='#e67e22',alpha=0.55,label='6530B 散热器（翻面后在板子背后）')
    gap=np.array([P(D0,-HS),P(30,-HS),P(30,-FAN),P(D0,-FAN),P(D0,-HS)]); ax.fill(gap[:,0],gap[:,2],color='#f5cba7',alpha=0.6,hatch='//',label='风扇进风要留的 3 mm')
    ax.set_title(title,fontsize=12); ax.set_aspect('equal'); ax.set_xlim(-15,95); ax.set_ylim(95,162)
    ax.set_xlabel('x（mm，向右是机器人前方）'); ax.set_ylabel('z（mm，向上）'); ax.grid(alpha=0.2)
section(axs[0],4.4,'剖面 y = 4.4 mm（板子中间，穿过芯片）')
axs[0].annotate('下巴舵机座 jaw_support\n挡住散热器下半段',xy=(47,127),xytext=(2,104),color='#c0392b',arrowprops=dict(arrowstyle='->',color='#c0392b'))
axs[0].annotate('头盖顶',xy=(62,152),xytext=(25,158),arrowprops=dict(arrowstyle='->'))
axs[0].annotate('摄像头',xy=(76,130),xytext=(78,104),color='#2ca02c',arrowprops=dict(arrowstyle='->',color='#2ca02c'))
axs[0].annotate('功放',xy=(35,140),xytext=(20,150))
axs[0].legend(loc='lower right',fontsize=9)
section(axs[1],20.0,'剖面 y = 20 mm（靠 1 号针那头）')
axs[1].annotate('下巴舵机 motor15\n（舵机本体，不能削）',xy=(48,124),xytext=(-12,104),color='#c0392b',arrowprops=dict(arrowstyle='->',color='#c0392b'))
ax=axs[2]
im=ax.imshow(np.clip(R,0,30).T,origin='lower',extent=[0,65,0,30],cmap='RdYlGn',vmin=0,vmax=26,aspect='equal')
cs=ax.contour(S,D,R,levels=[HS,FAN],colors=['k','k'],linestyles=['-','--'],linewidths=1.2)
ax.clabel(cs,fmt={HS:'13 mm',FAN:'16 mm'},fontsize=9)
ax.add_patch(plt.Rectangle((0,D0),65,30-D0,fill=False,ec='#e67e22',lw=2.5,ls='-'))
ax.text(33,2.2,'排针（散热器不盖）',fontsize=9.5,ha='center',bbox=dict(fc='white',ec='none',alpha=0.8))
ax.text(33,8.6,'这条带只剩 4-10 mm（下巴机构）',fontsize=10,color='#1b1b1b',ha='center',bbox=dict(fc='white',ec='none',alpha=0.8))
ax.text(33,25,'这块够深（13-30 mm 以上）',fontsize=10,color='white',ha='center')
ax.set_title('板子背后还剩多深（mm），橙框 = 6530B 盖住的范围\n实线 13 mm = 散热器本体，虚线 16 mm = 加上风扇进风',fontsize=11)
ax.set_xlabel('沿板子长边 s（mm，0 = 1 号针那头）'); ax.set_ylabel('沿板子竖直方向 d（mm，0 = 排针那条边）')
plt.colorbar(im,ax=ax,fraction=0.03,pad=0.02,label='背后空间 mm（≥26 都画成深绿）')
fig.suptitle('板子翻面、6530B 放到背后：上面 60% 放得下，下面一条被下巴机构挡住（只看现有 CAD，零件没改）',fontsize=14)
plt.tight_layout(); plt.savefig('flip-6530b.png',dpi=120,bbox_inches='tight')
