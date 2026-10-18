exec(open(__file__.replace('probe_anchor.py','probe.py')).read().split('for i,m')[0])
K=S^box([-100,-100,0],[150,-20.1,250]);slot=box([20.8,-42,90],[31.4,-34,118.6146]);upper=K-slot;p=np.array([26.1,0,118.6146]);jj=[sum([s.translate(-p).rotate([0,a,0]).translate(p) for s in J.values()],mf.Manifold()) for a in np.linspace(0,-90,19)]
for x in [8,12,16,19,33,36,40,44]:
 for y in [-38,-35,-32,-29,-26]:
  pillar=mf.Manifold.cylinder(15,2.6,2.6,circular_segments=32).translate([x,y,115.6]);connect=(pillar^upper).volume()
  if connect<5:continue
  worst=max((pillar^s).volume() for s in jj)
  if worst<.001:print('ANCHOR',x,y,'connect',connect,'jaw',worst,flush=True)
