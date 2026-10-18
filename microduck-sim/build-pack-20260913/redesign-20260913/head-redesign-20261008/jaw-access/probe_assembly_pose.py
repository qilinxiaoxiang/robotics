exec(open(__file__.replace('probe_assembly_pose.py','probe.py')).read().split('for i,m')[0])
K=S^box([-100,-100,0],[150,-20.1,250]);main=S-box([-100,-100,0],[150,-19.9,250]);slot=box([20.8,-42,90],[31.4,-34,118.6146]);upper=K-slot;lower=K^slot
cheek=H^box([15,-100,85],[53,1,120]);hs=H-cheek
pivot=np.array([26.1,0,118.6146])
def posed(s,a):return s.translate(-pivot).rotate([0,a,0]).translate(pivot)

for a in [-60,-70,-80,-90]:
 jj={k:posed(s,a) for k,s in J.items()};print('ANGLE',a,flush=True)
 for name,m,v in [('cheek',cheek,[0,0,-40]),('whole_shell',H,[0,0,-40])]:
  print(name,v,samples({name:m},{'main':main,'motor':M,**jj},v,step=.5)['peakContactsMm3'],flush=True)
