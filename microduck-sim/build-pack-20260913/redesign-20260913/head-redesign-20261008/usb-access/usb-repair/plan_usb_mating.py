"""Preserve the full 102.5 mm USB-C cable while withdrawing its free USB-A end.

Both board plugs remain seated; only the unrestrained USB-A end and cable bend
move. This is an arclength plan, not a collision or physical mating acceptance.
"""
from pathlib import Path
import hashlib, json, math
D=Path(__file__).resolve().parent
source=D/'positive-x225-usb-plan.json'
p=json.loads(source.read_text())
def sub(a,b):return [x-y for x,y in zip(a,b)]
def norm(a):return math.sqrt(sum(x*x for x in a))
def unit(a):return [x/norm(a) for x in a]
def length(w):
    lengths=[norm(sub(b,a)) for a,b in zip(w,w[1:])];cuts=[];arcs=[]
    for i in range(1,len(w)-1):
        u=unit(sub(w[i],w[i-1]));v=unit(sub(w[i+1],w[i]))
        angle=math.acos(max(-1,min(1,sum(x*y for x,y in zip(u,v)))))
        cuts.append(10*math.tan(angle/2));arcs.append(10*angle)
    for i,x in enumerate(lengths):
        if x < (cuts[i-1] if i else 0)+(cuts[i] if i<len(cuts) else 0)-1e-9:
            raise ValueError('Overlapping bends')
    return sum(lengths)-2*sum(cuts)+sum(arcs)+p['cEndArc']['lengthMm']
rows=[]
for row in p['rows']:
    samples=[]
    for i in range(61):
        offset=(60-i)*.25
        male=[x+offset*u for x,u in zip(row['usbAMaleCableExitMm'],p['scFinalDirection'])]
        def route(extra):
            w=[male,[male[0]-20-extra,male[1],male[2]],*row['acWaypointsMm'][2:]]
            return length(w),w
        try:
            valid=[]
            for trial in range(201):
                try:valid.append((trial*.5,route(trial*.5)[0]))
                except ValueError:continue
            brackets=[(x,y) for (x,lx),(y,ly) in zip(valid,valid[1:])
                      if y-x<=.500001 and lx<=102.5<=ly]
            assert brackets, 'No length root in valid fixed-topology family'
            lo,hi=brackets[0]
            for _ in range(45):
                mid=(lo+hi)/2
                if route(mid)[0]<102.5:lo=mid
                else:hi=mid
            actual,w=route((lo+hi)/2)
            assert abs(actual-102.5)<1e-7
            samples.append({'withdrawalMm':offset,'waypointsMm':w,'arcLengthMm':actual,'lengthSolved':True})
        except (AssertionError,ValueError) as error:
            samples.append({'withdrawalMm':offset,'lengthSolved':False,'reason':str(error)})
    rows.append({'spanMm':row['scFlexibleMm'],'samples':samples})
out={'allLengthsSolved':all(s['lengthSolved'] for r in rows for s in r['samples']),
     'strokeMm':15,'strokeBoundary':'Conservative exploratory withdrawal stroke, not a measured mating depth.',
     'radiusMm':10,'rows':rows,'sourceHashes':{str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in (source,Path(__file__))},
     'assemblyAccepted':False,'physicalVerified':False,
     'remaining':'Check the entire moving cable and male plug, the mating metal envelope, self contact, material continuity and restraint installation.'}
(D/'positive-x225-mating-plan.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'allLengthsSolved':out['allLengthsSolved'],'samples':sum(len(r['samples']) for r in rows)}))
