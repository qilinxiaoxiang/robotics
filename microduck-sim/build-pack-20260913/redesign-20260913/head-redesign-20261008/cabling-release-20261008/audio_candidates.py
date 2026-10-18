from check_routes import *
rows=[]
for end in [-1,1]:
 for side in [-13.,-11.,-9.]:
  for z in [134.5,135.5,136.5]:
   pair=[]
   for i,x in enumerate([-7.77,1.77]):
    p=np.array([x,12+end*11.06,132.35]);y=12+end*15.5
    pts=[p,p+[0,0,2.5],[x,y,134.85],[side,y,134.85],[side,-18,z],[23,-18,z],[31.15+i*3.5,-13.3,138.5]]
    ss=tube(pts,.6);hh=check(ss,['speaker','amplifier']);pair.append(hh)
   rows.append({'padEnd':end,'rearX':side,'z':z,'hits':pair})
print(json.dumps(rows,indent=2));(D/'audio-bounded-candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
