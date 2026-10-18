exec(open(__file__.replace('probe_cheek.py','probe.py')).read().split('for i,m')[0])
print('SHELL',H.bounding_box(),flush=True)
for label,selector,approach in [('swept',(sweep),[0,-48,0]),('leftblock',box([15,-100,85],[53,1,120]),[0,-48,0]),('lowerblock',box([15,-100,85],[53,1,120]),[0,0,-40])]:
 cheek=H^selector;main=H-selector
 print('PART',label,cheek.volume(),len(cheek.decompose()),len(main.decompose()),flush=True)
 fixed={**J,'motor15':M,'shell':main}
 for v in [[0,-48,0],[0,0,-40],[48,0,0],[0,-40,-40]]:
  print(label,v,samples({'cheek':cheek},fixed,v,step=1)['peakContactsMm3'],flush=True)
