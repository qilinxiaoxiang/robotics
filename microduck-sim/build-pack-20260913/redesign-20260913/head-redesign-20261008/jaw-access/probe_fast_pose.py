exec(open(__file__.replace('probe_fast_pose.py','probe.py')).read().split('for i,m')[0])
K=S^box([-100,-100,0],[150,-20.1,250]);main=S-box([-100,-100,0],[150,-19.9,250]);slot=box([20.8,-42,90],[31.4,-34,118.6146]);bar=box([15.0,-39.7,113.4],[37.2,-30.9,115.4])-cylinder_y(5.25,-50,-20)
receivers=box([15,-39.7,115.6],[20.7,-30.9,127])+box([31.5,-39.7,115.6],[37.2,-30.9,127]);bridge=box([0,-36,125.8],[45,-27,129.8]);upper=((K-slot)-bar)+receivers+bridge;lower=(K^slot)+bar
for i,c in enumerate(upper.decompose()):print('uppercomponents',i,c.volume(),c.bounding_box(),flush=True)
pivot=np.array([26.1,0,118.6146]);jj={k:s.translate(-pivot).rotate([0,-90,0]).translate(pivot) for k,s in J.items()}
for name,m,v in [('wholekeeper',K,[0,-32,0]),('upper',upper,[0,0,32]),('lower',lower,[0,0,-32])]:print(name,samples({name:m},{'main':main,'motor':M,**jj},v,step=.5)['peakContactsMm3'],flush=True)
for name,m in [('upper',upper),('lower',lower)]:print('FINALZERO',name,samples({name:m},J,[0,0,0])['peakContactsMm3'],flush=True)
