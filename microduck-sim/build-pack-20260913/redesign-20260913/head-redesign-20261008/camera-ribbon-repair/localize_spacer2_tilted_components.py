from pathlib import Path
f=Path(__file__).parent/'check_spacer2_tilted_complete.py'
exec(compile(f.read_text().split('keys=sorted(')[0],str(f),'exec'))
r={'accepted':False,'localization':[],'self':[],'expectedSelfPairs':0,'completedSelfPairs':0}
for key in ['zero_w_components']:
 ob=load(H/files[key]).translate(delta); rows=[]
 for a in np.arange(5,L-4.4,2):
  b=min(a+2,L-4.4);s=build(a,b);v,bb=n['volume'](s,ob)
  if v>1e-6:rows.append({'s':[a,b],'volume':v,'bounds':bb})
  del s
 r['localization'].append({'key':key,'rows':rows});del ob;gc.collect()
 (O/'spacer2-tilted-complete-components-localization.json').write_text(json.dumps(r,indent=2)+'\n')
