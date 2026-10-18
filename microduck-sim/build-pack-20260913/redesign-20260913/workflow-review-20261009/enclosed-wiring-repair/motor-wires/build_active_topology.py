"""Build the active motor-bus graph without rewriting historical failed routes."""
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
OLD=D.parents[1]/'roof-wiring-stage/motor-wires'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
legacy=json.loads((OLD/'route-input.json').read_text())
registered=json.loads((D/'two-openrb-ports.json').read_text())
old={r['id']:r for r in legacy['routes']}
branches=[{'id':'head-neck-leg-5-to-1','motorIds':[0,15,14,13,11,12,5,4,3,2,1],'openrbSourceSocket':74}, {'id':'leg-10-to-6','motorIds':[0,10,9,8,7,6],'openrbSourceSocket':110}]
ports={f"motor-{p['motor']}-socket-{p['sourceSocket']}":p for a in legacy['ports'].values() for p in a}
ports.update({f"motor-0-socket-{p['sourceSocket']}":p for p in registered['ports']})
routes=[]
for b in branches:
 b['routeIds']=[]
 for a,z in zip(b['motorIds'],b['motorIds'][1:]):
  rid=f"ttl-{'openrb' if a==0 else f'{a:02d}'}-{z:02d}"
  source=next((r for r in old.values() if r['from']['motor']==a and r['to']['motor']==z),None)
  reverse=False
  if source is None:
   source=next((r for r in old.values() if r['from']['motor']==z and r['to']['motor']==a),None);reverse=source is not None
  if source:
   fr,to=(source['to'],source['from']) if reverse else (source['from'],source['to'])
  else:
   assert (a,z)==(0,10)
   fr=registered['ports'][1];to=next(p for p in legacy['ports']['10'] if p['sourceSocket']==13)
  row={'id':rid,'branchId':b['id'],'fromPort':f"motor-{a}-socket-{fr['sourceSocket']}",'toPort':f"motor-{z}-socket-{to['sourceSocket']}",'legacyRouteId':source['id'] if source else None,'legacyDirection':'reverse' if reverse else 'same' if source else 'new','directionMeaning':'Traversal/assembly order only; TTL sockets have no assigned IN/OUT. Reversal does not swap electrical pin order.','routeAcceptance':'pending','stockNominalLengthMm':180,'stockLengthMeaning':'Nominal cable allocation only; full routed length, retention and joint service must be checked per route.'}
  if rid in ('ttl-04-03','ttl-09-08'):
   row['routeAcceptance']='neutral-static-cleared; retention and joint-service pending'
   row['geometryReceipt']='local-route.json' if a==4 else 'mirror-route.json'
   row['geometryReceiptDirection']='same' if a==4 else 'reverse'
  reassigned={'ttl-04-03':(14,14),'ttl-03-02':(13,14),'ttl-02-01':(13,13),'ttl-09-08':(13,13),'ttl-08-07':(14,13),'ttl-07-06':(14,14)}
  if rid in reassigned:
   sp,tp=reassigned[rid];row.update(fromPort=f'motor-{a}-socket-{sp}',toPort=f'motor-{z}-socket-{tp}',physicalSocketReassignment='Both parallel sockets reviewed together with neighbouring routes; same motor IDs and pin order.',routeAcceptance='neutral receiving geometry clear; physical installation pending',geometryReceipt='shared-port-repair/joint-right.json' if a<6 else 'shared-port-repair/joint-left.json',geometryReceiptDirection='same')
  routes.append(row);b['routeIds'].append(rid)
out={'schemaVersion':1,'status':'ACTIVE_TOPOLOGY_ROUTE_REPAIR_IN_PROGRESS','wholeHarnessAccepted':False,'purpose':'Single active source for subsequent route generation and tutorial navigation; historical route-input remains a frozen failure artifact.','units':'mm','coordinateScope':'Registered original-body neutral world. OpenRB source frame must follow the board rigid transform selected by the head layout; this graph does not accept a new board pose.','branches':branches,'routes':routes,'ports':ports,'removedLegacyRoutes':[{'id':'ttl-01-06','reason':'Cross-ankle jumper unnecessarily tethers independently moving feet. A separate OpenRB socket feeds motor10 and its descending leg chain.','replacement':'ttl-openrb-10'}],'socketIdentity':'OpenRB sourceSocket74/110 are geometric connected-component identifiers, not official silkscreen port numbers.','electricalScope':{'bus':'One TTL DYNAMIXEL bus; unchanged motor IDs','branchDoesNotIncreaseSupplyCapacity':True,'powerTerminationAccepted':False,'note':'This physical branch graph does not authorize bridging isolated VDD supplies or reinterpret model strand colours as pin order.'},'sourceEvidence':[{'url':'https://emanual.robotis.com/docs/en/parts/controller/openrb-150/#dynamixel-ports','verifiedDate':'2026-10-09','supports':'Four dedicated TTL DYNAMIXEL ports; EHR-03 mating housing; pins GND/VDD/DATA. Board port specification is 3000mA, not 3000mA multiplied by socket count.','decision':'Use a second real port to remove the cross-foot jumper; exact routing is a project implementation decision.'}],'sourceHashes':{str(OLD/'route-input.json'):sha(OLD/'route-input.json'),str(D/'two-openrb-ports.json'):sha(D/'two-openrb-ports.json'),str(Path(legacy['portRegistration'])):sha(Path(legacy['portRegistration']))}}
(D/'active-topology.json').write_text(json.dumps(out,indent=2)+'\n')
