# One source-driven finite local reroute: cross the FFC below its stored band,
# then rise beyond its negative-Y edge. No printed geometry is changed.
import build_wires as b
import json
D=b.D;m=json.loads((D/'manifest.json').read_text());data=json.loads((D/'routes.json').read_text())
for pin in [12,20,35,40]:
 key='i2s_pin_'+str(pin);r=next(x for x in data['routes'] if x['key']==key);src=next(x for x in b.i2sd['routes'] if x['pin']==pin);pts=r['centerlineMm'];cut=22;first=pts[:cut+1]
 wp=[p[:] for p in src['waypointsAfterFirstBendMm']];wp[0]=pts[cut]
 if pin==12:
  wp[2][2]=120.5;wp[3][2]=120.5
 elif pin==20:
  wp[1][0]=49;wp[1][2]=120.5;wp[2][0]=49;wp[2][2]=120.5;wp[3][2]=120.5
 elif pin==35:
  wp[1][2]=120.5;wp[2][2]=120.5;wp[3][2]=120.5;wp[4][2]=120.5
 else:
  wp[2][2]=120.5;wp[3][2]=120.5;wp[4][1]=-34;wp[4][2]=120.5;wp[5][1]=-34
 # Remove consecutive coincident vertices before exact fillets.
 clean=[wp[0]]
 for p in wp[1:]:
  if b.norm(b.sub(p,clean[-1]))>1e-5:clean.append(p)
 print('repair pin',pin,flush=True);tail=b.round_polyline(clean,1.2);new=first+tail[1:];f=D/(key+'-world.stl');b.tube(f,new,.75)
 p=next(x for x in m['parts'] if x['key']==key);p['sha256']=b.sha(f);p['expectedFinalBoundsMm']=b.bounds(f);p['validationStatus']='Finite FFC-avoidance candidate: crossings lowered to Z120.5, endpoints unchanged. R1.2 is a modeling exploration, not a manufacturer bend specification; checks in head-internal-check.json.'
 r['centerlineMm']=new;r['repairWaypointsMm']=clean;r['candidatePolylineLengthMm']=sum(b.norm(b.sub(new[i],new[i-1])) for i in range(1,len(new)));r['validationStatus']=p['validationStatus']
(D/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');(D/'routes.json').write_text(json.dumps(data,indent=2)+'\n');print('LOCAL I2S REPAIR GENERATED',b.sha(D/'manifest.json'))
