from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'screen_double_dogleg.py').read_text().split('for La0,L20,R30 in ')[0])
r=json.loads((D/'double-dogleg-screen.json').read_text());rows=[]
for idx in [1,2,5]:
 x=np.array(r['rows'][idx]['parameters']);p,t,w,L,b,pr=family(x);solid=construct(4.4,200,.35,x,16);hits=[]
 for k,v in obstacles.items():
  q=solid^v
  if q.volume()>1e-6:hits.append({'obstacle':k,'volume':q.volume(),'bounds':q.bounding_box()})
 rows.append({'index':idx,'hits':hits})
(D/'candidate-intersection-bounds.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
