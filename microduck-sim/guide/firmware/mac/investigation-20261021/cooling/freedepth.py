"""Free depth under the head cap: for sample points on the cap's outer surface, the distance along the inward normal
to the first internal part (board, SoC, antenna, clip, amp, speaker, pads, XIAO, ribbon, coax, camera, face, jaw).
Writes a JSON of candidate vent zones and a PNG sketch (roof top view, rear view, side section)."""
import numpy as np, trimesh, json, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
W='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
A='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/a7z-head/'
F='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/face-a7z/'
U='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/a7z-head/usb-service/'
cap=trimesh.load(A+'head_cap_a7z-world.stl')
bottom=trimesh.load(W+'head_bottom.stl')
parts={k:trimesh.load(p) for k,p in {
 'a7z_pcb':A+'a7z_parts/a7z_pcb.stl','soc':A+'a7z_parts/soc_a733.stl','ram':A+'a7z_parts/ram.stl','wifi':A+'a7z_parts/wifi_module_fcu760k.stl',
 'usb_c_power':A+'a7z_parts/usb_c_power.stl','usb_c_otg':A+'a7z_parts/usb_c_otg_dp.stl','hdmi':A+'a7z_parts/micro_hdmi.stl','fan_conn':A+'a7z_parts/fan_connector.stl',
 'antenna':W+'antenna.stl','coax':W+'antenna_coax.stl','clip_cap':W+'clip_cap.stl','amplifier':W+'amplifier.stl','speaker':W+'speaker.stl','speaker_retainer':W+'speaker_retainer.stl',
 'pad_l1':W+'touch_pad_l1.stl','pad_r1':W+'touch_pad_r1.stl','pad_l2':W+'touch_pad_l2.stl','pad_r2':W+'touch_pad_r2.stl','pad_m':W+'touch_pad_m.stl','xiao':W+'touch_xiao.stl',
 'ribbon':W+'camera_ribbon.stl','camera':F+'camera_13m214.stl','face':F+'face_panel_a7z.stl','trim':F+'eye_trim_a7z.stl','jaw_frame':W+'jaw_frame.stl','clip_head':W+'clip_head.stl','usb_plug':U+'usb_plug_envelope.stl'}.items()}
for k in ('speaker','xiao'):
    parts[k]=parts[k].convex_hull
inner=trimesh.util.concatenate([m for k,m in parts.items() if k not in ('face','trim','jaw_frame')])
labels=[]; faces=[]
for k,m in parts.items():
    labels+= [k]*len(m.faces)
labels=np.array(labels)
allparts=trimesh.util.concatenate(list(parts.values()))
def sample_outer(mesh, n=60000):
    pts,fi=trimesh.sample.sample_surface(mesh,n)
    nrm=mesh.face_normals[fi]
    return pts,nrm
pts,nrm=sample_outer(cap)
# keep only outward-facing samples: outward = the point + 0.3*normal is outside the cap
outside=~cap.contains(pts+nrm*0.4)
pts,nrm=pts[outside],nrm[outside]
# the inner wall: ray from the sample point inward through the cap wall; first hit is the wall's inner face
loc,ri,_=cap.ray.intersects_location(pts+nrm*0.01,-nrm,multiple_hits=False)
# depth from the inner face to the first internal part
wall=np.full(len(pts),np.nan); free=np.full(len(pts),np.nan); who=np.array(['']*len(pts),dtype=object)
inner_pts=np.full((len(pts),3),np.nan)
for p,i in zip(loc,ri):
    wall[i]=np.linalg.norm(p-pts[i]); inner_pts[i]=p
ok=~np.isnan(wall)
o=inner_pts[ok]+(-nrm[ok])*0.05
loc2,ri2,fi2=allparts.ray.intersects_location(o,-nrm[ok],multiple_hits=False)
idx=np.where(ok)[0]
for p,i,f in zip(loc2,ri2,fi2):
    j=idx[i]; free[j]=np.linalg.norm(p-inner_pts[j]); who[j]=labels[f]
# no hit = ray leaves the head (open seam) -> treat as large free depth
free[ok & np.isnan(free)]=99
np.savez(sys.argv[1]+'.npz',pts=pts,nrm=nrm,wall=wall,free=free,who=who.astype(str))
# zones: roof (nz>0.6), back (nx<-0.6), left/right sides (|ny|>0.7), front (nx>0.6)
zones={'roof':nrm[:,2]>0.6,'back':nrm[:,0]<-0.6,'left':nrm[:,1]>0.7,'right':nrm[:,1]<-0.7,'front':nrm[:,0]>0.6}
rep={}
for z,msk in zones.items():
    m=msk&ok
    rep[z]={'samples':int(m.sum()),'wall_mm_median':round(float(np.nanmedian(wall[m])),2),'free_ge_6mm_share':round(float((free[m]>=6).mean()),2),'free_ge_10mm_share':round(float((free[m]>=10).mean()),2)}
    # what is behind the shell most often (first hit)
    u,c=np.unique(who[m],return_counts=True); rep[z]['first_hit']={str(a):int(b) for a,b in sorted(zip(u,c),key=lambda t:-t[1])[:8]}
print(json.dumps(rep,indent=1))
# SoC position and the roof directly above it
soc=parts['soc']; sc=soc.centroid; print('SoC centroid',sc.round(1),'top x',soc.bounds[1,0].round(1))
json.dump({'zones':rep,'soc_centroid':sc.round(1).tolist(),'soc_bounds':soc.bounds.round(1).tolist()},open(sys.argv[1],'w'),indent=1)
# ---- sketch ----
fig,axs=plt.subplots(1,3,figsize=(17,6))
def scatter(ax,xi,yi,msk,title,xl,yl):
    m=msk&ok
    sc_=ax.scatter(pts[m,xi],pts[m,yi],c=np.clip(free[m],0,20),s=3,cmap='viridis',vmin=0,vmax=20)
    ax.set_title(title); ax.set_xlabel(xl); ax.set_ylabel(yl); ax.set_aspect('equal'); return sc_
# roof: top view x,y
s_=scatter(axs[0],0,1,zones['roof'],'Cap roof, top view (colour = free depth under the wall, mm)','x forward (mm)','y left (mm)')
# overlay footprints
def rect(ax,b,xi,yi,c,lab):
    ax.add_patch(plt.Rectangle((b[0][xi],b[0][yi]),b[1][xi]-b[0][xi],b[1][yi]-b[0][yi],fill=False,ec=c,lw=1.5,label=lab))
for k,c in (('soc','red'),('antenna','orange'),('clip_cap','brown'),('amplifier','purple'),('speaker_retainer','blue'),('pad_l1','green'),('pad_r1','green'),('pad_l2','green'),('pad_r2','green'),('pad_m','green'),('usb_c_power','magenta'),('hdmi','gray'),('xiao','cyan'),('wifi','black')):
    rect(axs[0],parts[k].bounds,0,1,c,k)
axs[0].legend(fontsize=6,loc='lower left')
scatter(axs[1],1,2,zones['back'],'Cap back, rear view','y left (mm)','z up (mm)')
for k,c in (('amplifier','purple'),('speaker_retainer','blue'),('pad_l2','green'),('pad_r2','green'),('xiao','cyan')):
    rect(axs[1],parts[k].bounds,1,2,c,k)
# side section at y = SoC centroid: cap outline + parts bounds in x,z
y0=sc[1]
sec=cap.section(plane_origin=[0,y0,0],plane_normal=[0,1,0])
if sec is not None:
    for e in sec.discrete:
        axs[2].plot(e[:,0],e[:,2],'k-',lw=1)
secb=bottom.section(plane_origin=[0,y0,0],plane_normal=[0,1,0])
if secb is not None:
    for e in secb.discrete: axs[2].plot(e[:,0],e[:,2],'k-',lw=0.8)
for k,c in (('a7z_pcb','gray'),('soc','red'),('camera','magenta'),('face','black'),('antenna','orange'),('amplifier','purple'),('speaker_retainer','blue'),('pad_m','green'),('jaw_frame','olive')):
    rect(axs[2],parts[k].bounds,0,2,c,k)
axs[2].set_title(f'Side section at y={y0:.1f} (through the SoC)'); axs[2].set_xlabel('x forward (mm)'); axs[2].set_ylabel('z up (mm)'); axs[2].set_aspect('equal'); axs[2].legend(fontsize=6)
fig.colorbar(s_,ax=axs[0],shrink=0.6,label='free depth (mm)')
fig.tight_layout(); fig.savefig(sys.argv[2],dpi=110)
print('saved',sys.argv[2])
