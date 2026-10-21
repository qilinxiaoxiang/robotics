"""Depth maps of the official Open Duck Mini v2 head.stl and head_bot_sheet.stl from six sides: an opening shows as a
patch whose first hit is far deeper than the wall around it. Units as in the STL (mm assumed)."""
import sys, numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
d=sys.argv[1]; out=sys.argv[2]
H=trimesh.load(d+'/head.stl'); B=trimesh.load(d+'/head_bot_sheet.stl')
print('head bounds', H.bounds.round(1).tolist(), 'extents', H.extents.round(1).tolist(), 'watertight', H.is_watertight)
print('bot bounds', B.bounds.round(1).tolist())
def depth(m, axis, sign, step=0.5):
    lo,hi=m.bounds; a=[i for i in range(3) if i!=axis]
    u=np.arange(lo[a[0]],hi[a[0]],step); v=np.arange(lo[a[1]],hi[a[1]],step)
    U,V=np.meshgrid(u,v,indexing='ij'); o=np.zeros((U.size,3)); o[:,a[0]]=U.ravel(); o[:,a[1]]=V.ravel()
    o[:,axis]= (lo[axis]-5) if sign>0 else (hi[axis]+5)
    dirv=np.zeros(3); dirv[axis]=sign
    loc,ri,_=m.ray.intersects_location(o,np.tile(dirv,(len(o),1)),multiple_hits=False)
    dep=np.full(len(o),np.nan); dep[ri]=np.abs(loc[:,axis]-o[ri,axis])-5
    return dep.reshape(U.shape),(u,v),a
views=[(0,1,'from -X'),(0,-1,'from +X'),(1,1,'from -Y'),(1,-1,'from +Y'),(2,1,'from -Z (below)'),(2,-1,'from +Z (above)')]
fig,axs=plt.subplots(2,4,figsize=(20,9))
for k,(ax_,sg,t) in enumerate(views):
    dep,(u,v),a=depth(H,ax_,sg); ax=axs.flat[k]
    im=ax.imshow(dep.T,origin='lower',extent=[u[0],u[-1],v[0],v[-1]],cmap='magma_r',vmin=0,vmax=np.nanpercentile(dep,99)); ax.set_title('head.stl '+t+' (depth to first hit, mm)')
    ax.set_xlabel('axis %d'%a[0]); ax.set_ylabel('axis %d'%a[1]); fig.colorbar(im,ax=ax,shrink=0.7)
for k,(ax_,sg,t) in enumerate([(2,1,'from -Z'),(2,-1,'from +Z')]):
    dep,(u,v),a=depth(B,ax_,sg); ax=axs.flat[6+k]
    im=ax.imshow(dep.T,origin='lower',extent=[u[0],u[-1],v[0],v[-1]],cmap='magma_r'); ax.set_title('head_bot_sheet.stl '+t)
fig.tight_layout(); fig.savefig(out,dpi=80); print('saved',out)
