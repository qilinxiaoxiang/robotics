exec(open(__file__.replace('probe_split.py','probe.py')).read().split('for i,m')[0])
keep=S^box([-100,-100,0],[150,-20.1,250]);main=S-box([-100,-100,0],[150,-19.9,250])
lo=keep^box([-100,-100,0],[150,100,118.5146]);hi=keep^box([-100,-100,118.7146],[150,100,250])
for name,m in [('lo',lo),('hi',hi)]:
 print('part',name,m.volume(),len(m.decompose()),m.bounding_box(),flush=True)
 for v in [[0,0,32],[0,0,-32],[0,-32,0],[32,0,0],[-32,0,0],[0,-32,32],[0,-32,-32]]:
  r=samples({name:m},{'main':main,'motor':M,**J},v,step=1);print(name,v,r['peakContactsMm3'],flush=True)
