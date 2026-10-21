"""Where could vent slots go in the A7Z head? Vertical rays down through the head cap roof (and up through the lower
shell floor): outer wall, inner wall, first internal part under the inner wall. A roof cell is a vent candidate when
(a) the wall there is real roof (outer surface normal mostly up), (b) at least 5 mm of air sits between the inner wall and
the first part below, and (c) it is at least 3 mm from the antenna, touch pads, cap clip and the usb-service slot.
Writes vent_zones.json and the arrays for the figure."""
import json, sys, numpy as np, trimesh
A='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/a7z-head/'
W='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
F='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/face-a7z/'
out=sys.argv[1]
cap=trimesh.load(A+'head_cap_a7z-world.stl'); bot=trimesh.load(W+'head_bottom.stl')
parts={'a7z_pcb':A+'a7z_parts/a7z_pcb.stl','soc':A+'a7z_parts/soc_a733.stl','ram':A+'a7z_parts/ram.stl','wifi':A+'a7z_parts/wifi_module_fcu760k.stl',
 'usb_c_power':A+'a7z_parts/usb_c_power.stl','usb_c_otg':A+'a7z_parts/usb_c_otg_dp.stl','hdmi':A+'a7z_parts/micro_hdmi.stl','pmic':A+'a7z_parts/pmic_area.stl',
 'antenna':W+'antenna.stl','coax':W+'antenna_coax.stl','clip_cap':A+'clip_cap_a7z-world.stl','amplifier':W+'amplifier.stl','speaker':W+'speaker.stl',
 'speaker_retainer':W+'speaker_retainer.stl','pad_l1':W+'touch_pad_l1.stl','pad_r1':W+'touch_pad_r1.stl','pad_l2':W+'touch_pad_l2.stl',
 'pad_r2':W+'touch_pad_r2.stl','pad_m':W+'touch_pad_m.stl','xiao':W+'touch_xiao.stl','ribbon':W+'camera_ribbon.stl','camera':F+'camera_13m214.stl',
 'face':F+'face_panel_a7z.stl','trim':F+'eye_trim_a7z.stl','jaw_frame':W+'jaw_frame.stl','clip_head':W+'clip_head.stl'}
P={k:trimesh.load(p) for k,p in parts.items()}
step=1.0
xs=np.arange(-30.5,92.5,step); ys=np.arange(-45.5,46,step)
X,Y=np.meshgrid(xs,ys,indexing='ij'); n=X.size
o=np.column_stack([X.ravel(),Y.ravel(),np.full(n,200.0)]); dn=np.tile([0,0,-1.0],(n,1))
loc,ri,ti=cap.ray.intersects_location(o,dn,multiple_hits=True)
zout=np.full(n,np.nan); zin=np.full(n,np.nan); nz=np.full(n,np.nan)
order=np.lexsort((-loc[:,2],ri))
loc,ri,ti=loc[order],ri[order],ti[order]
first=np.r_[True,ri[1:]!=ri[:-1]]
idx_first=np.where(first)[0]
for k in idx_first:
    r=ri[k]; zout[r]=loc[k,2]; nz[r]=cap.face_normals[ti[k]][2]
    if k+1<len(ri) and ri[k+1]==r: zin[r]=loc[k+1,2]
# first internal part below the inner wall
zpart=np.full(n,-np.inf); who=np.array(['']*n,dtype=object)
o2=np.column_stack([X.ravel(),Y.ravel(),np.nan_to_num(zin,nan=-1e3)-0.05])
ok=np.isfinite(zin)
for k,m in P.items():
    l,r,_=m.ray.intersects_location(o2[ok],dn[ok],multiple_hits=False)
    if len(r)==0: continue
    rr=np.where(ok)[0][r]; z=l[:,2]; b=z>zpart[rr]; zpart[rr[b]]=z[b]; who[rr[b]]=k
# the lower shell floor below (if no part, the air column ends there)
l,r,_=bot.ray.intersects_location(o2[ok],dn[ok],multiple_hits=False)
zfloor=np.full(n,-np.inf); rr=np.where(ok)[0][r]; zfloor[rr]=l[:,2]
free=np.where(np.isfinite(zin), zin-np.maximum(zpart,zfloor), np.nan)
freewho=np.where(zpart>=zfloor, who, 'lower shell floor')
wall=zout-zin
# keep-outs: antenna, pads, cap clip, coax (all stuck to or hanging from the roof) + 3 mm; usb-service slot (14 x 8 at x~64, y -22)
def footprint(m,pad):
    b=m.bounds; return (X>=b[0,0]-pad)&(X<=b[1,0]+pad)&(Y>=b[0,1]-pad)&(Y<=b[1,1]+pad)
ko=np.zeros(X.shape,bool); kowho=np.array(['']*n,dtype=object).reshape(X.shape)
for k in ('antenna','pad_l1','pad_r1','pad_l2','pad_r2','pad_m','clip_cap','coax','xiao'):
    f=footprint(P[k],3.0); kowho[f&~ko]=k; ko|=f
usb=(np.abs(X-64.0)<=4+3)&(np.abs(Y+22.0)<=7+3); kowho[usb&~ko]='usb-service slot'; ko|=usb
roof=(nz.reshape(X.shape)>0.5)&np.isfinite(zin.reshape(X.shape))
F_=free.reshape(X.shape)
cand=roof&(~ko)&(F_>=5.0)
res={'grid_step_mm':step,'roof_cells':int(roof.sum()),'candidate_cells_mm2':int(cand.sum()),
     'wall_thickness_mm_median_on_roof':round(float(np.nanmedian(wall.reshape(X.shape)[roof])),2)}
# label candidate regions
from scipy import ndimage
lab,nl=ndimage.label(cand)
regions=[]
for i in range(1,nl+1):
    m=lab==i
    if m.sum()<20: continue
    regions.append({'area_mm2':int(m.sum()),'x':[round(float(X[m].min()),1),round(float(X[m].max()),1)],'y':[round(float(Y[m].min()),1),round(float(Y[m].max()),1)],
                    'free_below_min_mm':round(float(F_[m].min()),1),'free_below_median_mm':round(float(np.median(F_[m])),1),
                    'what_is_below':{str(a):int(b) for a,b in zip(*np.unique(freewho.reshape(X.shape)[m],return_counts=True))},
                    'distance_to_soc_centre_mm':round(float(np.min(np.hypot(X[m]-60.6,Y[m]-4.4))),1)})
res['roof_regions']=sorted(regions,key=lambda r:-r['area_mm2'])
# the column right above the SoC / the board-camera channel
ch=(X>=62)&(X<=70)&(Y>=-12)&(Y<=14)
res['above_board_camera_channel_x62-70_y-12..14']={'roof_free_min':round(float(np.nanmin(F_[ch])),1),'roof_free_median':round(float(np.nanmedian(F_[ch])),1),
    'keepout_share':round(float(ko[ch].mean()),2),'keepout_by':{str(a):int(b) for a,b in zip(*np.unique(kowho[ch&ko],return_counts=True))},
    'below':{str(a):int(b) for a,b in zip(*np.unique(freewho.reshape(X.shape)[ch],return_counts=True))}}
# lower shell floor: through-openings (rays up from below that never hit head_bottom inside its outline)
up=np.tile([0,0,1.0],(n,1)); o3=np.column_stack([X.ravel(),Y.ravel(),np.full(n,50.0)])
hb=bot.ray.intersects_any(o3,up).reshape(X.shape)
outline=(X>=bot.bounds[0,0]+3)&(X<=bot.bounds[1,0]-3)&(Y>=bot.bounds[0,1]+3)&(Y<=bot.bounds[1,1]-3)
# restrict to inside the convex outline of the shell in plan view
from matplotlib.path import Path as MPath
hull2=trimesh.convex.convex_hull(np.column_stack([bot.vertices[:,0],bot.vertices[:,1],np.zeros(len(bot.vertices))]+[]) ) if False else None
import scipy.spatial as sp
h=sp.ConvexHull(bot.vertices[:,:2]); path=MPath(bot.vertices[h.vertices,:2])
inside=path.contains_points(np.column_stack([X.ravel(),Y.ravel()])).reshape(X.shape)
open_floor=inside&(~hb)
lab2,nl2=ndimage.label(open_floor); fl=[]
for i in range(1,nl2+1):
    m=lab2==i
    if m.sum()<4: continue
    fl.append({'area_mm2':int(m.sum()),'x':[round(float(X[m].min()),1),round(float(X[m].max()),1)],'y':[round(float(Y[m].min()),1),round(float(Y[m].max()),1)]})
res['lower_shell_floor_openings']=sorted(fl,key=lambda r:-r['area_mm2'])
json.dump(res,open(out,'w'),indent=1); print(json.dumps(res,indent=1))
np.savez(out.replace('.json','.npz'),X=X,Y=Y,free=F_,roof=roof,ko=ko,cand=cand,open_floor=open_floor,wall=wall.reshape(X.shape))
