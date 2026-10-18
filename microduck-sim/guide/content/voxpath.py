import pickle, numpy as np, trimesh, sys, json, collections
from scipy import ndimage
s=pickle.load(open('current.pkl','rb'))
P=1.0
lo=np.array([-95,-40,-62.]); hi=np.array([45,40,62.])
shape=np.ceil((hi-lo)/P).astype(int)+1
occ=np.zeros(shape,bool)
skip=set(sys.argv[1].split(',')) if len(sys.argv)>1 and sys.argv[1] else set()
mods={'torso','power','imu','neck','right-leg','left-leg'}
for k,p in s.items():
    if p['module'] not in mods or k in skip: continue
    m=trimesh.Trimesh(p['v'].astype(float),p['f'],process=False)
    try:
        vg=m.voxelized(P)
        vg=vg.fill()
        pts=vg.points
    except Exception as e:
        pts=m.sample(20000)
    idx=np.round((pts-lo)/P).astype(int)
    ok=np.all((idx>=0)&(idx<shape),1); idx=idx[ok]
    occ[idx[:,0],idx[:,1],idx[:,2]]=True
np.save('occ.npy',occ); json.dump({'lo':lo.tolist(),'P':P,'shape':shape.tolist()},open('occ.json','w'))
print('occupied voxels',occ.sum())
