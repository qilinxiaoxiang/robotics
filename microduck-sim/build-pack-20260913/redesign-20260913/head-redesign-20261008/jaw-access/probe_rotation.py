exec(open(__file__.replace('probe_rotation.py','probe.py')).read().split('for i,m')[0])
p=np.array([26.1,0,118.6146])
for a in np.linspace(0,-90,19):
 hits={}
 for k,s in J.items():
  ss=s.translate(-p).rotate([0,a,0]).translate(p)
  for q,f in {'S':S,'H':H,'M':M}.items():
   vol=float((ss^f).volume())
   if vol>.001:hits[k+'-'+q]=vol
 print(a,hits,flush=True)
