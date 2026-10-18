from pathlib import Path
import contextlib,io,json,runpy,math
D=Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()): a=runpy.run_path(str(D/'audit_split_native_toolpaths.py'))
clip=a['clip'];segs=a['allsegs']
def seg_box(p,q,lo,hi):
 def f(t):return sum(max(lo[k]-(p[k]+t*(q[k]-p[k])),0,p[k]+t*(q[k]-p[k])-hi[k])**2 for k in range(3))
 br=[0.,1.]
 for k in range(3):
  if abs(q[k]-p[k])>1e-12:
   br += [t for b in [lo[k],hi[k]] if 0<(t:=(b-p[k])/(q[k]-p[k]))<1]
 br=sorted(br);v=min(map(f,br))
 for ta,tb in zip(br,br[1:]):
  mid=(ta+tb)/2;aa=bb=0
  for k in range(3):
   c=p[k]+mid*(q[k]-p[k]);bound=lo[k] if c<lo[k] else hi[k] if c>hi[k] else None
   if bound is not None:d=q[k]-p[k];aa+=d*d;bb+=d*(p[k]-bound)
  if aa:v=min(v,f(max(ta,min(tb,-bb/aa))))
 return math.sqrt(v)
# Nominal key top working section; account for actual key bead envelope before
# testing surrounding pocket walls. Neither assumes all four walls exist.
lo=[45.2,4,111.72];hi=[47.2,6,112.1];mn=[1e9,1e9];mx=[-1e9,-1e9];n=0
for p,q,r,kind,no in segs['head_roll_bearing_carrier']:
 if 'Support'in kind:continue
 pq=clip(p,q,2,lo[2],hi[2])
 if pq and all(44.9<v[0]<47.5 and 3.7<v[1]<6.3 for v in pq):
  n+=1
  for k in range(2):mn[k]=min(mn[k],*(v[k]-r for v in pq));mx[k]=max(mx[k],*(v[k]+r for v in pq))
assert n
boundlo=mn+[lo[2]];boundhi=mx+[hi[2]];best=None
for p,q,r,kind,no in segs['jaw_support']:
 if 'Support'in kind:continue
 gap=seg_box(p,q,boundlo,boundhi)-r
 if best is None or gap<best['clearanceLowerBoundMm']:best={'clearanceLowerBoundMm':gap,'line':no,'type':kind}
out={'actualKeyEnvelopeXYMm':[mn,mx],'keySegments':n,'sectionWorldZMm':[lo[2],hi[2]],'minimumPocketBeadClearance':best,'passed':best['clearanceLowerBoundMm']>0,'scope':'Actual native conservative sphere bead bounds at working section, all jaw_support model beads tested; physical flow/shrinkage excluded. Not an across-material dimensional certification.'}
(D/'split-key-native-clearance.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
