exec(open(__file__.replace('probe_inside.py','probe.py')).read().split('for i,m')[0])
K=S^box([-100,-100,0],[150,-20.1,250]);sm=S-box([-100,-100,0],[150,-19.9,250]);hc=H^box([15,-100,85],[53,1,120]);hm=H-hc
for name,m,f,v in [('keeper',K,{'motor':M,**J},[0,32,0]),('supportmain',sm,{'motor':M,**J,'keeper':K},[0,0,32]),('cheek',hc,{'motor':M,**J,'S':S},[0,48,0]),('shellmain',hm,{'motor':M,**J,'S':S,'cheek':hc},[0,0,-40])]:
 print(name,v,samples({name:m},f,v,step=.5)['peakContactsMm3'],flush=True)
