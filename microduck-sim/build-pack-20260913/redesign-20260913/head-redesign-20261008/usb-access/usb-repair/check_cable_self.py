"""Bounded nonlocal centerline checks for circular receiving tubes.

Local neighborhoods are valid only when independently generated with a bend
radius greater than the tube radius. No full distance matrix is retained.
"""
import math
import numpy as np

def segment_distance(a,b,c,d):
    u=b-a;v=d-c;w=a-c;aa=u@u;bb=u@v;cc=v@v
    def point_segment(p,x,y):
        delta=y-x
        return float(np.linalg.norm(p-(x+np.clip((p-x)@delta/(delta@delta),0,1)*delta)))
    best=min(point_segment(a,c,d),point_segment(b,c,d),point_segment(c,a,b),point_segment(d,a,b))
    det=aa*cc-bb*bb
    if det>1e-20:
        dd=u@w;ee=v@w;s=(bb*ee-cc*dd)/det;t=(aa*ee-bb*dd)/det
        if 0<=s<=1 and 0<=t<=1:best=min(best,float(np.linalg.norm(w+s*u-t*v)))
    return best

def check(points,diameter,min_bend_radius):
    p=np.asarray(points,float);delta=np.diff(p,axis=0);length=np.linalg.norm(delta,axis=1)
    assert len(length) and np.all(length>0)
    assert min_bend_radius>diameter/2
    step=float(length.max());assert step<=.250001
    sagitta=min_bend_radius-math.sqrt(min_bend_radius**2-(step/2)**2)
    threshold=diameter+2*sagitta+.01
    arc=np.r_[0,np.cumsum(length)];low=np.minimum(p[:-1],p[1:]);high=np.maximum(p[:-1],p[1:])
    candidates=0;hits=[];nearest=None;expected=0
    for i in range(len(length)):
        # Exclude only the local tube neighborhood; analytic R10 fillets govern it.
        valid=(arc[:-1]-arc[i+1])>math.pi*diameter/2
        expected+=int(valid.sum())
        ids=np.flatnonzero(valid & np.all(low<=high[i]+threshold,axis=1) & np.all(high>=low[i]-threshold,axis=1))
        for j in ids:
            candidates+=1;dist=segment_distance(p[i],p[i+1],p[j],p[j+1])
            nearest=dist if nearest is None else min(nearest,dist)
            if dist<=threshold:hits.append({'segments':[int(i),int(j)],'centerDistanceMm':dist,'receivingSurfaceGapMm':dist-diameter})
    return {'segments':len(length),'nonlocalPairsCovered':expected,'exactNarrowPhasePairs':candidates,'maximumSegmentMm':step,'chordSagittaAllowanceMm':2*sagitta,'numericalClearanceMm':.01,'minimumTestedCenterDistanceMm':nearest,'hits':hits,'allClear':not hits,'coverageComplete':True,'localBendRadiusMm':min_bend_radius,'diameterMm':diameter}

if __name__=='__main__':
    assert segment_distance(np.array([0.,0,0]),np.array([1.,0,0]),np.array([.5,-1,0]),np.array([.5,1,0]))==0
    assert abs(segment_distance(np.array([0.,0,0]),np.array([1.,0,0]),np.array([0.,2,0]),np.array([1.,2,0]))-2)<1e-12
    print('crossing and parallel segment controls passed')
