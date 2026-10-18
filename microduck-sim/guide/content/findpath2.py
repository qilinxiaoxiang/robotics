import numpy as np, json, sys, heapq
from scipy import ndimage
occ=np.load(__import__('os').environ.get('OCC','occ')+'.npy'); meta=json.load(open(__import__('os').environ.get('OCC','occ')+'.json')); lo=np.array(meta['lo']); P=meta['P']
clear=float(sys.argv[1])  # required clearance radius mm
dist=ndimage.distance_transform_edt(~occ)*P
free=dist>=clear
def idx(p): return tuple(np.round((np.array(p)-lo)/P).astype(int))
def pt(i): return (np.array(i)*P+lo)
A=idx(json.loads(sys.argv[2])); B=idx(json.loads(sys.argv[3]))
# allow endpoints region: carve sphere of radius 3 around endpoints
for E in (A,B):
    sl=tuple(slice(max(0,e-3),e+4) for e in E)
    free[sl]=free[sl]|~occ[sl]
print('A free',free[A],'B free',free[B],'dist A',dist[A],'dist B',dist[B])
# A* 26-neighbour
nb=[(i,j,k) for i in (-1,0,1) for j in (-1,0,1) for k in (-1,0,1) if (i,j,k)!=(0,0,0)]
g={A:0}; came={}; h=lambda a: np.linalg.norm(np.subtract(a,B))
pq=[(h(A),A)]; seen=set()
while pq:
    f,c=heapq.heappop(pq)
    if c==B: break
    if c in seen: continue
    seen.add(c)
    for d in nb:
        n=(c[0]+d[0],c[1]+d[1],c[2]+d[2])
        if min(n)<0 or any(n[i]>=occ.shape[i] for i in range(3)) or not free[n]: continue
        # mild preference for staying away from walls
        cost=g[c]+np.linalg.norm(d)*(1+0.5/max(dist[n],0.5))
        if cost<g.get(n,1e18): g[n]=cost; came[n]=c; heapq.heappush(pq,(cost+h(n),n))
if B not in came: print('NO PATH'); sys.exit()
path=[B]
while path[-1]!=A: path.append(came[path[-1]])
path=[pt(p) for p in path[::-1]]
L=sum(np.linalg.norm(path[i+1]-path[i]) for i in range(len(path)-1))
print('length mm',round(L,1),'min clearance',round(min(dist[idx(p)] for p in path[3:-3]),2))
# simplify: print every ~10mm
acc=0; out=[path[0]]
for i in range(1,len(path)):
    acc+=np.linalg.norm(path[i]-path[i-1])
    if acc>=10: out.append(path[i]); acc=0
out.append(path[-1])
print(json.dumps([[round(float(x),1) for x in p] for p in out]))
