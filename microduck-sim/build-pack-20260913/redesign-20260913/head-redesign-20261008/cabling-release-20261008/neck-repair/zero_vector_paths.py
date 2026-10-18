import xml.etree.ElementTree as E,re,math
from pathlib import Path
P=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/cabling-release-20261008/neck-repair')
root=E.parse(P/'zero-w-official-mechanical.svg').getroot()
num=r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?'
paths=[]
for idx,el in enumerate(root):
 ts=re.findall('[MLCZ]|'+num,el.get('d',''));matrix=list(map(float,re.findall(num,el.get('transform',''))));a,b,c,d,e,f=matrix if matrix else [1,0,0,1,0,0]
 def tr(p):return[a*p[0]+c*p[1]+e,b*p[0]+d*p[1]+f]
 seg=[];i=0;pt=None;start=None
 while i<len(ts):
  cmd=ts[i];i+=1
  if cmd in ['M','L']:
   q=list(map(float,ts[i:i+2]));i+=2
   if cmd=='L':seg.append((tr(pt),tr(q)))
   else:start=q
   pt=q
  elif cmd=='C':
   vals=list(map(float,ts[i:i+6]));i+=6;q1,q2,q3=vals[:2],vals[2:4],vals[4:];old=pt
   for j in range(1,65):
    t=j/64;q=[(1-t)**3*pt[k]+3*(1-t)**2*t*q1[k]+3*(1-t)*t*t*q2[k]+t**3*q3[k] for k in [0,1]];seg.append((tr(old),tr(q)));old=q
   pt=q3
  elif cmd=='Z':seg.append((tr(pt),tr(start)));pt=start
  else:raise ValueError(cmd)
 if seg:paths.append({'id':idx,'segments':seg,'width':float(el.get('stroke-width',0)),'bbox':[min(p[k] for s in seg for p in s) for k in [0,1]]+[max(p[k] for s in seg for p in s) for k in [0,1]]})
def dist(p,a,b):
 v=[b[k]-a[k] for k in [0,1]];den=sum(x*x for x in v);t=max(0,min(1,sum((p[k]-a[k])*v[k] for k in [0,1])/den)) if den else 0
 return math.dist(p,[a[k]+t*v[k] for k in [0,1]])
if __name__=='__main__':
 for center in [[438*842/1600,499*842/1600],[885*842/1600,499*842/1600],[438*842/1600,676*842/1600],[885*842/1600,676*842/1600]]:
  print('CENTER',center)
  rows=sorted((min(dist(center,*s) for s in p['segments']),p['id'],p['bbox'],len(p['segments'])) for p in paths)
  for row in rows[:25]:print(row)
