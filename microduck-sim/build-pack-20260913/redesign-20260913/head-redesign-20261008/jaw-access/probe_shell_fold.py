exec(open(__file__.replace('probe_shell_fold.py','probe.py')).read().split('for i,m')[0])
parts={'left':H^box([-100,-100,0],[150,-.1,250]),'right':H^box([-100,.1,0],[150,100,250])};p=np.array([0,0,98.5])
for name,s in parts.items():
 peak={}
 for a in np.linspace(0,90,46):
  m=s.translate(-p).rotate([a*(1 if name=='left' else -1),0,0]).translate(p)
  for k,f in {**J,'M':M,'S':S}.items():
   v=(m^f).volume()
   if v>.001:peak[k]=max(peak.get(k,0),v)
 print(name,peak,flush=True)
