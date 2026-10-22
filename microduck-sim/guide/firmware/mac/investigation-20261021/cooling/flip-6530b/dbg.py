exec(open("b2b_fit.py").read().split("out=[]")[0])
Xc=68.0
rear,rw=cast(world(S,D,Xc-0.01),np.array([-1.0,0,0]))
for d0 in range(0,30,3):
    for s0 in range(0,65,8):
        m=(D>=d0)&(D<d0+3)&(S>=s0)&(S<s0+8)
        print(f"{rear[m].min():5.1f}{rw[m][np.argmin(rear[m])][:4]:>5}",end=' ')
    print('  d',d0,'z',ZTOP-d0)
need=np.where(fan,14.5,np.where(body|legs,11.5,np.where(plug,17.0,0)))
bad=(need+1-rear>0)&(rw.astype(str)=='head_cap')&~((S<6)|(S>59))
print('bad cells s',sorted(set(S[bad])),'d',sorted(set(D[bad])),'short',(need+1-rear)[bad].max())
front,fw=cast(world(S,D,Xc+1.61),np.array([1.0,0,0]))
for d0 in range(0,30,6):
    for s0 in range(0,65,8):
        m=(D>=d0)&(D<d0+6)&(S>=s0)&(S<s0+8); print(f"{front[m].min():5.1f}{fw[m][np.argmin(front[m])][:4]:>5}",end=' ')
    print(' front d',d0)
# board slab itself: top edge to roof, bottom edge down
up,uw=cast(np.column_stack([np.full(65,Xc-5), Y1-np.arange(0.5,65.5), np.full(65,ZTOP)]),np.array([0,0,1.0]))
print('roof above top edge at x=Xc-5: min',up.min().round(1),'median',np.median(up).round(1))
dn,dw=cast(np.column_stack([np.full(65,Xc+0.8), Y1-np.arange(0.5,65.5), np.full(65,ZTOP-30)]),np.array([0,0,-1.0]))
print('below bottom edge: min',dn.min().round(1),set(dw[dn<3]))
