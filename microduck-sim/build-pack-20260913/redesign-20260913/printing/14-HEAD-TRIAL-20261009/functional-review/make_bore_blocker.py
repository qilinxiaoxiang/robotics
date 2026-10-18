from pathlib import Path
import math,json,hashlib,struct
D=Path(__file__).resolve().parent;P=D.parent
r=json.loads((D/'hole-readback.json').read_text());f=next(f for f in r['results'][0]['features'] if f['name']=='pi-pilot-1-0')
prep=json.loads((P/'run/preparation.json').read_text());place=next(p['translation'] for p in prep['rows'][0]['placements'] if p['key']=='head_cap')
c=[a-b for a,b in zip(f['originPlate'],place)];a=f['axisPlate'];lo=-.25;hi=5.15;radius=1.05
cross=lambda u,v:[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
u=cross(a,[0,0,1]);n=math.sqrt(sum(x*x for x in u));u=[x/n for x in u];v=cross(a,u)
ends=[[c[k]+a[k]*t for k in range(3)]for t in(lo,hi)];rings=[[[p[k]+radius*(u[k]*math.cos(i*2*math.pi/48)+v[k]*math.sin(i*2*math.pi/48))for k in range(3)]for i in range(48)]for p in ends];tris=[]
for i in range(48):
 j=(i+1)%48;tris.extend([(rings[0][i],rings[0][j],rings[1][j]),(rings[0][i],rings[1][j],rings[1][i]),(ends[0],rings[0][j],rings[0][i]),(ends[1],rings[1][i],rings[1][j])])
p=D/'pi-positive-y-upper-hole-support-blocker-print.stl'
with p.open('wb')as out:
 out.write(b'Local non-printing support blocker; native hole evidence'.ljust(80,b'\0'));out.write(struct.pack('<I',len(tris)))
 for t in tris:
  n=cross([t[1][k]-t[0][k]for k in range(3)],[t[2][k]-t[0][k]for k in range(3)]);l=math.sqrt(sum(x*x for x in n));out.write(struct.pack('<12fH',*[x/l for x in n],*sum((list(x)for x in t),[]),0))
h=hashlib.sha256(p.read_bytes()).hexdigest();manifest=P/'head-trial.json';d=json.loads(manifest.read_text());part=next(x for x in d['parts']if x['key']=='head_cap');part['supportBlockers']=[dict(path=str(p),sha256=h,machines=['Bambu'],reason='Keep the single positive-Y upper Pi mounting pilot free of internal support; actual first Bambu slice had 15 support core segments. Non-printing slicer modifier only.')];manifest.write_text(json.dumps(d,indent=2)+'\n')
(D/'blocker-spec.json').write_text(json.dumps(dict(sourceReadbackSha256=hashlib.sha256((D/'hole-readback.json').read_bytes()).hexdigest(),feature=f['name'],printFrameOriginMm=c,axis=a,rangeMm=[lo,hi],diameterMm=radius*2,file=str(p),sha256=h,scope='One Bambu support exclusion; no printable solid changed'),indent=2)+'\n')
print(json.dumps(dict(manifest=str(manifest),manifestSha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),blockerSha256=h)))
