from pathlib import Path
f=Path(__file__).parent/'check_spacer2_outreturn.py'
exec(compile(f.read_text().split('keys=sorted(')[0],str(f),'exec'))
r={'accepted':False,'localization':[],'self':[],'expectedSelfPairs':0,'completedSelfPairs':0}
for key in ['face_panel','head_cap']:
 ob=load(H/files[key]); rows=[]
 for a in np.arange(5,L-4.4,2):
  b=min(a+2,L-4.4);s=build(a,b);v,bb=n['volume'](s,ob)
  if v>1e-6:rows.append({'s':[a,b],'volume':v,'bounds':bb})
  del s
 r['localization'].append({'key':key,'rows':rows});del ob;gc.collect()
 (O/'spacer2-outreturn-localization.json').write_text(json.dumps(r,indent=2)+'\n')
# narrow segments compared nonadjacently, bounding boxes first.
chunks=[]
for a in np.arange(0,L,2):
 s=build(a,min(a+2,L));chunks.append((a,s,np.array(s.bounding_box()).reshape(2,3)))
for i,(a,s,bb) in enumerate(chunks):
 for j in range(i+2,len(chunks)):
  b,z,zb=chunks[j];r['expectedSelfPairs']+=1
  if np.all(bb[1]>=zb[0]) and np.all(zb[1]>=bb[0]):
   v,bounds=n['volume'](s,z)
   if v>1e-6:r['self'].append({'s1':a,'s2':b,'volume':v,'bounds':bounds})
  r['completedSelfPairs']+=1
 (O/'spacer2-outreturn-localization.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
