from check_routes import *
rows=[]
for y in [29,32,35]:
 for x in [10,13]:
  pts=[[54.5,y,131.5],[x,y,131.5],[x,y,90]];s=tube(pts,1.5);hh=check(s);rows.append({'x':x,'y':y,'points':pts,'hits':hh})
print(json.dumps(rows,indent=2));(D/'head-neck-exit-probe.json').write_text(json.dumps({'rows':rows,'sourceHashes':hashes},indent=2)+'\n')
