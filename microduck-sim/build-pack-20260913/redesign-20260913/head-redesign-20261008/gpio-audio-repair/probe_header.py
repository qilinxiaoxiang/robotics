from scene import *
rows=[]
for depth in [11,15,18,20]:
 h=housing(depth);rr={'pcbToExitMm':depth,'housingHitsMm3':intersections(h,['pi']),'pinRows':[]}
 for pin,(net,diameter) in PIN_NETS.items():
  p=port(pin,depth);s=tube([p,p+[-5,0,0]],diameter/2)
  rr['pinRows'].append({'physicalPin':pin,'net':net,'diameterMm':diameter,'exitMm':p.tolist(),'straight5mmHitsMm3':intersections(s)})
 rows.append(rr)
tri(housing()).export(D/'gpio18-receiving-world.stl')
out={'problemIds':['P5','P6'],'sourceHashes':hashes,'rows':rows,'dimensionsFile':'connector-dimensions.json','physicalVerified':False}
(D/'header-baseline.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(rows,indent=2))
