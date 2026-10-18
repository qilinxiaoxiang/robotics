from pathlib import Path
exec(Path(__file__).with_name('local_route.py').read_text().split('rows=[];solids=[]')[0])
output=[]
for name in ['local-route.json','mirror-route.json']:
 a=json.loads((D/name).read_text());rows=[]
 for r in a['strands']:
  wire=solid(trimesh.load_mesh(r['file'],process=True))
  for entry in r['checked']:
   ob=json.loads((OLD/'obstacles'/f"{entry['key']}.json").read_text());m=trimesh.load_mesh(ob['file'],process=True);m.apply_translation(ob.get('importTranslationMm',[0,0,0]));gap=wire.min_gap(solid(m),2.)
   rows.append({'wire':r['id'],'obstacle':entry['key'],'gapMmCappedAt2':gap})
 output.append({'route':a['route'],'sourceSha256':sha(D/name),'rows':rows,'minimumGapMm':min(x['gapMmCappedAt2']for x in rows)})
 print(a['route'],sorted(rows,key=lambda x:x['gapMmCappedAt2'])[:5],flush=True)
(D/'route-gap-readback.json').write_text(json.dumps(output,indent=2))
