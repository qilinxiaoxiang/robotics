import numpy as np, trimesh, matplotlib, json, base64
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
W='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
d=json.load(open('/Users/xiangzheng/code/robotics/microduck-sim/guide/data/guide-data.json'))
P=d['parts']; P={p['key']:p for p in P} if isinstance(P,list) else P
p=P['motor13']; v=np.frombuffer(base64.b64decode(p['positionB64']),dtype='<f4').reshape(-1,3); f=np.frombuffer(base64.b64decode(p['indexB64']),dtype='<u4').reshape(-1,3)
jaw=trimesh.load(W+'jaw_frame-v18.stl')
# cut 2 mm off the boss end: remove material y > -39.0 within r<5.2
cutter=trimesh.creation.cylinder(radius=5.2,height=4,transform=trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0],[0,0,0]))
cutter.apply_translation([26.1,-37.0,118.62])
jaw2=jaw.difference(cutter)
parts=[(jaw2,'#e8c84a'),(trimesh.load(W+'head_bottom.stl'),'#f2e6a0'),(trimesh.load(W+'jaw_support.stl'),'#555'),(trimesh.Trimesh(v,f,process=False),'#9ab')]
ZC=118.62
fig,ax=plt.subplots(figsize=(7.5,6.4))
for m,c in parts:
    s=m.section(plane_origin=[26.1,0,0],plane_normal=[1,0,0])
    for poly in s.discrete: ax.fill(poly[:,1],poly[:,2],color=c,alpha=0.75,ec='k',lw=0.4)
red='#d33'
for sgn in [1,-1]:
    z0=ZC if sgn>0 else ZC-8
    # flange y -39.9..-39.6 r 6.25..8 ; sleeve y -39.6..-37.0 r 5.25..7 ; end plate y -39.0..-37.0 r 0.8..5.25
    ax.add_patch(Rectangle((-39.9,ZC+sgn*6.25 if sgn>0 else ZC-8),0.3,1.75,color=red,ec='k',lw=0.5))
    ax.add_patch(Rectangle((-39.6,ZC+5.25 if sgn>0 else ZC-7),2.6,1.75,color=red,ec='k',lw=0.5))
    ax.add_patch(Rectangle((-39.0,ZC+0.8 if sgn>0 else ZC-5.25),2.0,4.45,color=red,ec='k',lw=0.5))
ax.add_patch(Rectangle((-44.06,ZC-1),8.0,2,color='#888',ec='k',lw=0.6))
ax.add_patch(Rectangle((-45.66,ZC-1.9),1.6,3.8,color='#888',ec='k',lw=0.6))
ax.axvline(-37.0,color='g',ls=':',lw=1)
ax.annotate('one-piece capped ring (new print):\nsame flange and sleeve as the old ring,\nclosed 2.0 mm end, pilot 1.6',xy=(-38,ZC+3),xytext=(-36,ZC+11),arrowprops=dict(arrowstyle='->'),fontsize=8.5)
ax.annotate('boss end cut back 2 mm\n(-37.0 -> -39.0)',xy=(-39.2,ZC-3),xytext=(-52,ZC-13),arrowprops=dict(arrowstyle='->'),fontsize=8.5)
ax.annotate('M2 x 8 from outside,\nhole drilled to 2.5',xy=(-45,ZC+1.5),xytext=(-52,ZC+11),arrowprops=dict(arrowstyle='->'),fontsize=8.5)
ax.annotate('green line: inner end today\n(nothing goes past it,\nso springing the jaw in\nneeds no extra bend)',xy=(-37.0,ZC-9),xytext=(-34.5,ZC-17),arrowprops=dict(arrowstyle='->'),fontsize=8)
ax.set_xlim(-53,-20); ax.set_ylim(ZC-19,ZC+16); ax.set_aspect('equal')
ax.set_title('One-piece option: capped ring screwed to the right jaw arm',fontsize=10)
ax.set_xlabel('Y (mm)  outside <-  -> inside'); ax.set_ylabel('Z (mm)')
plt.tight_layout(); plt.savefig('jaw_ring_onepiece.png',dpi=150)
