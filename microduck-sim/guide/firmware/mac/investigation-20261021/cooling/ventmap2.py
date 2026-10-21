"""Vent map without ray casting: bin mesh vertices on a 1 mm grid.
Roof (top view): roof outer z(x,y) = max cap z in the cell; inner wall = outer - 1.7 mm (D-013 wall); highest internal
part top in the cell; free depth = inner - part top. Back (rear view): cap min x per (y,z) vs part min x. Sides likewise."""
import numpy as np, trimesh, json, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
W='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
A='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/a7z-head/'
F='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/face-a7z/'
cap=trimesh.load(A+'head_cap_a7z-world.stl'); bottom=trimesh.load(W+'head_bottom.stl')
P={k:trimesh.load(p) for k,p in {
 'a7z_pcb':A+'a7z_parts/a7z_pcb.stl','soc':A+'a7z_parts/soc_a733.stl','ram':A+'a7z_parts/ram.stl','wifi':A+'a7z_parts/wifi_module_fcu760k.stl',
 'usb_c_power':A+'a7z_parts/usb_c_power.stl','usb_c_otg':A+'a7z_parts/usb_c_otg_dp.stl','hdmi':A+'a7z_parts/micro_hdmi.stl','fan_conn':A+'a7z_parts/fan_connector.stl',
 'antenna':W+'antenna.stl','coax':W+'antenna_coax.stl','clip_cap':W+'clip_cap.stl','amplifier':W+'amplifier.stl','speaker':W+'speaker.stl','speaker_retainer':W+'speaker_retainer.stl',
 'pad_l1':W+'touch_pad_l1.stl','pad_r1':W+'touch_pad_r1.stl','pad_l2':W+'touch_pad_l2.stl','pad_r2':W+'touch_pad_r2.stl','pad_m':W+'touch_pad_m.stl','xiao':W+'touch_xiao.stl',
 'ribbon':W+'camera_ribbon.stl','camera':F+'camera_13m214.stl','face':F+'face_panel_a7z.stl','trim':F+'eye_trim_a7z.stl','jaw_frame':W+'jaw_frame.stl','clip_head':W+'clip_head.stl'}.items()}
# densify part surfaces so thin/large faces bin properly
def dense(m, n=20000):
    pts,_=trimesh.sample.sample_surface(m,n); return np.vstack([m.vertices,pts])
PV={k:dense(m) for k,m in P.items()}
CV=dense(cap,120000); BV=dense(bottom,60000)
WALL=1.7
def grid_max(pts, ai, bi, ci, lo, hi, step=1.0, fn='max'):
    """2-D grid over axes ai,bi; value = max (or min) of axis ci per cell."""
    na=int((hi[0]-lo[0])/step)+1; nb=int((hi[1]-lo[1])/step)+1
    g=np.full((na,nb), -np.inf if fn=='max' else np.inf)
    ia=((pts[:,ai]-lo[0])/step).astype(int); ib=((pts[:,bi]-lo[1])/step).astype(int)
    ok=(ia>=0)&(ia<na)&(ib>=0)&(ib<nb)
    if fn=='max': np.maximum.at(g,(ia[ok],ib[ok]),pts[ok,ci])
    else: np.minimum.at(g,(ia[ok],ib[ok]),pts[ok,ci])
    g[~np.isfinite(g)]=np.nan; return g
res={}
# ---- roof: x,y grid, z up ----
lo=(-31,-46); hi=(93,46)
roof=grid_max(CV,0,1,2,lo,hi)                      # cap outer z
capmin=grid_max(CV,0,1,2,lo,hi,fn='min')           # cap lowest z (rim)
best=np.full(roof.shape,-np.inf); who=np.full(roof.shape,'',dtype=object)
for k,v in PV.items():
    if k in ('face','trim','jaw_frame','clip_head'): continue
    g=grid_max(v,0,1,2,lo,hi); m=np.nan_to_num(g,nan=-np.inf)>best; best[m]=np.nan_to_num(g,nan=-np.inf)[m]; who[m]=k
best[~np.isfinite(best)]=np.nan
free_roof=roof-WALL-best
# only where the cap really has a roof (outer z above the rim by > 3 mm) 
valid=np.isfinite(roof)&((roof-np.nan_to_num(capmin,nan=roof))>3)
free_roof[~valid]=np.nan
free_roof_nan=np.where(np.isnan(best)&valid, 60.0, free_roof)   # nothing under the roof in this column: open to the lower shell
# ---- back: y,z grid, x backward ----
lo2=(-46,110); hi2=(46,158)
back=grid_max(CV,1,2,0,lo2,hi2,fn='min')
bestx=np.full(back.shape,np.inf); whox=np.full(back.shape,'',dtype=object)
for k,v in PV.items():
    if k in ('face','trim','jaw_frame','clip_head','camera','ribbon'): continue
    g=grid_max(v,1,2,0,lo2,hi2,fn='min'); m=np.nan_to_num(g,nan=np.inf)<bestx; bestx[m]=np.nan_to_num(g,nan=np.inf)[m]; whox[m]=k
bestx[~np.isfinite(bestx)]=np.nan
free_back=bestx-(back+WALL)
free_back=np.where(np.isnan(bestx)&np.isfinite(back),60.0,free_back)
# ---- summary of the SoC column and candidate zones ----
soc=P['soc'].bounds; sc=P['soc'].centroid
def cell(g,x,y,lo,step=1.0): return g[int((x-lo[0])/step), int((y-lo[1])/step)]
res['soc']={'bounds':soc.round(1).tolist(),'centroid':sc.round(1).tolist(),
            'roof_outer_z_above_soc':round(float(np.nanmean([cell(roof,x,y,lo) for x in np.arange(soc[0,0],soc[1,0]) for y in np.arange(soc[0,1],soc[1,1])])),1),
            'first_part_under_roof_above_soc':{str(k):int(v) for k,v in zip(*np.unique([cell(who,x,y,lo) for x in np.arange(soc[0,0],soc[1,0]) for y in np.arange(soc[0,1],soc[1,1])],return_counts=True))}}
# zone statistics: rectangles on the roof to evaluate
zones={'roof behind antenna, centre (x 54-63, |y|<13)':(54,63,-13,13),'roof right shoulder over J16 (x 62-76, y -34..-22)':(62,76,-34,-22),
       'roof left shoulder over HDMI (x 62-76, y 24..34)':(62,76,24,34),'roof over antenna (x 64-76, |y|<21)':(64,76,-21,21),
       'roof rear dome (x -25..10, |y|<35)':(-25,10,-35,35),'roof between pads L1/R1 and M (x 30-42, |y|<12)':(30,42,-12,12),'roof over clip (x 61-69, y 14-32)':(61,69,14,32)}
res['roof_zones']={}
for n,(x0,x1,y0,y1) in zones.items():
    sub=free_roof_nan[int((x0-lo[0])):int((x1-lo[0])), int((y0-lo[1])):int((y1-lo[1]))]
    w=who[int((x0-lo[0])):int((x1-lo[0])), int((y0-lo[1])):int((y1-lo[1]))]
    u,c=np.unique(w,return_counts=True)
    res['roof_zones'][n]={'free_depth_min':round(float(np.nanmin(sub)),1),'free_depth_median':round(float(np.nanmedian(sub)),1),'first_part_below':{str(a):int(b) for a,b in sorted(zip(u,c),key=lambda t:-t[1])[:4]}}
bz={'back dome centre (|y|<15, z 125-150)':(-15,15,125,150),'back low left (y 15-40, z 115-135)':(15,40,115,135),'back low right (y -40..-15, z 115-135)':(-40,-15,115,135),'back high (|y|<30, z 150-157)':(-30,30,150,157)}
res['back_zones']={}
for n,(y0,y1,z0,z1) in bz.items():
    sub=free_back[int(y0-lo2[0]):int(y1-lo2[0]), int(z0-lo2[1]):int(z1-lo2[1])]
    w=whox[int(y0-lo2[0]):int(y1-lo2[0]), int(z0-lo2[1]):int(z1-lo2[1])]
    u,c=np.unique(w,return_counts=True)
    res['back_zones'][n]={'free_depth_min':round(float(np.nanmin(sub)),1),'free_depth_median':round(float(np.nanmedian(sub)),1),'first_part_behind_wall':{str(a):int(b) for a,b in sorted(zip(u,c),key=lambda t:-t[1])[:4]}}
# SoC to camera PCB back along x and along the board normal
n=np.array([0.9848,0,-0.1736]); soc_top=P['soc'].vertices[np.argmax(P['soc'].vertices@n)]
cam=P['camera'].vertices; cam_back=cam[(abs(cam[:,1]-sc[1])<8)&(abs(cam[:,2]-sc[2])<8)]
res['soc_top_to_camera']={'along_x_mm':round(float(cam_back[:,0].min()-P['soc'].bounds[1,0]),1),'along_normal_mm':round(float((cam_back@n).min()-soc_top@n),1)}
res['board_to_amp_along_x_mm']=round(float(P['a7z_pcb'].bounds[0,0]-P['amplifier'].bounds[1,0]),1)
json.dump(res,open(sys.argv[1],'w'),indent=1); print(json.dumps(res,indent=1))
# ---- sketch ----
fig,axs=plt.subplots(1,3,figsize=(18,6.2))
ext=[lo[1],hi[1],lo[0],hi[0]]
im=axs[0].imshow(np.clip(free_roof_nan,0,25),origin='lower',extent=[lo[1],hi[1],lo[0],hi[0]],cmap='viridis',vmin=0,vmax=25,aspect='equal')
axs[0].set_title('Head cap roof, seen from above\ncolour = free air under the wall (mm); dark = part right under the roof'); axs[0].set_xlabel('y left (mm)'); axs[0].set_ylabel('x forward (mm)')
axs[0].invert_xaxis()
def rect(ax,b,ai,bi,c,lab,ls='-'):
    ax.add_patch(plt.Rectangle((b[0][ai],b[0][bi]),b[1][ai]-b[0][ai],b[1][bi]-b[0][bi],fill=False,ec=c,lw=1.6,ls=ls,label=lab))
for k,c in (('soc','red'),('antenna','orange'),('clip_cap','saddlebrown'),('amplifier','purple'),('speaker_retainer','blue'),('pad_l1','lime'),('pad_r1','lime'),('pad_l2','lime'),('pad_r2','lime'),('pad_m','lime'),('usb_c_power','magenta'),('hdmi','white'),('xiao','cyan'),('wifi','black')):
    rect(axs[0],P[k].bounds,1,0,c,k)
axs[0].add_patch(plt.Rectangle((-22-4,63.9-7),8,14,fill=False,ec='magenta',ls='--',lw=1.6,label='usb-service slot (candidate)'))
axs[0].legend(fontsize=6.5,loc='lower right',ncol=2); fig.colorbar(im,ax=axs[0],shrink=0.7,label='free depth (mm)')
im2=axs[1].imshow(np.clip(free_back,0,25).T,origin='lower',extent=[lo2[0],hi2[0],lo2[1],hi2[1]],cmap='viridis',vmin=0,vmax=25,aspect='equal')
axs[1].set_title('Head cap back, seen from behind\ncolour = free air inside the rear wall (mm)'); axs[1].set_xlabel('y left (mm)'); axs[1].set_ylabel('z up (mm)')
for k,c in (('amplifier','purple'),('speaker_retainer','blue'),('pad_l2','lime'),('pad_r2','lime'),('xiao','cyan'),('a7z_pcb','gray')):
    rect(axs[1],P[k].bounds,1,2,c,k)
axs[1].legend(fontsize=6.5,loc='lower right')
y0=sc[1]
for mesh,lw in ((cap,1.2),(bottom,0.8)):
    sec=mesh.section(plane_origin=[0,y0,0],plane_normal=[0,1,0])
    if sec is not None:
        for e in sec.discrete: axs[2].plot(e[:,0],e[:,2],'k-',lw=lw)
for k,c in (('a7z_pcb','gray'),('soc','red'),('ram','black'),('camera','magenta'),('face','dimgray'),('trim','dimgray'),('antenna','orange'),('amplifier','purple'),('speaker_retainer','blue'),('pad_m','lime'),('jaw_frame','olive')):
    rect(axs[2],P[k].bounds,0,2,c,k)
axs[2].annotate('',xy=(P['camera'].bounds[0,0]+6.2,sc[2]),xytext=(soc[1,0],sc[2]),arrowprops=dict(arrowstyle='<->',color='red'))
axs[2].text(soc[1,0]+1,sc[2]+2,f"{res['soc_top_to_camera']['along_x_mm']} mm to camera PCB",color='red',fontsize=8)
axs[2].set_title(f'Side section at y = {y0:.1f} mm (through the SoC), seen from the left\nboard leans 10 deg, chips face the face panel'); axs[2].set_xlabel('x forward (mm)'); axs[2].set_ylabel('z up (mm)'); axs[2].set_aspect('equal'); axs[2].legend(fontsize=6.5,loc='lower left')
fig.tight_layout(); fig.savefig(sys.argv[2],dpi=110); print('saved',sys.argv[2])
