"""Three evidence-driven head anchor alternatives, stdlib only."""
from pathlib import Path
import json,math,hashlib,itertools
from prepare_single_candidate import moved,add,sub,mul,norm,dot
from single_circle_candidate import arc,line
import finite_anchor_screen as family
D=Path(__file__).resolve().parent;H=D.parent.parent
CASES=[{'id':'up-r16-6','A':[-47.,23.2,147.],'TA':[0,0,1.],'outletStart':[-31,23.2,125],'fixedOutletLengthMm':16*math.pi/2+6}, {'id':'rear-straight-28','A':[-59.,32.,125.],'TA':[-1.,0,0],'outletStart':[-31,32,125],'fixedOutletLengthMm':28}, {'id':'rear-side-straight-24','A':[-55.,38.,125.],'TA':[-1.,0,0],'outletStart':[-31,38,125],'fixedOutletLengthMm':24}]
B=[0.,-25.,47.];U=[-2**-.5,-2**-.5,0.];BODIES={'trunk_base':0,'neck':1,'neck_pitch':2,'yaw_roll_motion':3,'jaw_soft':4};ORDER=['neck_pitch','head_pitch','head_yaw','head_roll']
CASES += [{'id':'down-r16-side40','A':[-47.,40.,103.],'TA':[0,0,-1.],'outletStart':[-31,40,125],'fixedOutletLengthMm':16*math.pi/2+6},{'id':'down-r16-side-minus40','A':[-47.,-40.,103.],'TA':[0,0,-1.],'outletStart':[-31,-40,125],'fixedOutletLengthMm':16*math.pi/2+6}]
def main():
 plan=json.loads((D/'short-domain/plan.json').read_text());domain=json.loads((H/'usb-access/usb-repair/rigid-domain.json').read_text());clear=plan['nativeClearPoseIndices'];reports=[]
 for c in CASES:
  family.A=c['A'];family.TA=c['TA'];raw=[family.terms(r['jointDegrees'],B,U) for r in domain['samples']];target=5*math.ceil(max(raw[i][-1] for i in clear)/5);potential=[]
  for i in clear:
   q=domain['samples'][i]['jointDegrees'];center=moved(c['A'],q)
   for item in plan['obstacles']:
    qq={k:q.get(k,0) for k in ORDER[:BODIES[item['body']]]};corners=[moved(p,qq) for p in itertools.product(*zip(*item['neutralActualVertexBounds']))];lo=list(map(min,zip(*corners)));hi=list(map(max,zip(*corners)))
    if not any(center[k]+3.54<lo[k] or center[k]-3.54>hi[k] for k in range(3)):potential.append({'pose':i,'part':item['key'],'center':center})
  p=family.path({},B,U,target);p.pop('points');reports.append({**c,'B':B,'bowAxis':U,'targetNativeClearMm':target,'fixedAndFlexibleBeforeFanoutsMm':target+c['fixedOutletLengthMm'],'minCoreRadiusNativeClearMm':min(raw[i][-2] for i in clear),'minCoreRadiusAll229Mm':min(t[-2] for t in raw),'neutral':p,'anchorAABBPotentialPairs':potential,'scope':'AABB candidates only, not a sphere-to-solid collision claim. Full outlet, path, solids, self and angular-domain checks are still required.'})
 out={'accepted':False,'CADExecuted':False,'reason':'At head_pitch−65°, prior downward anchor itself enters source torso shell; free-loop shape cannot correct an endpoint collision.','cases':reports,'sourceHashes':{str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),D/'short-domain/plan.json',H/'usb-access/usb-repair/rigid-domain.json',D/'finite_anchor_screen.py']}}
 (D/'head-anchor-v2-screen.json').write_text(json.dumps(out,indent=2)+'\n')
 for c in reports:print(json.dumps({k:v for k,v in c.items() if k not in ['anchorAABBPotentialPairs','scope']}|{'potentialAnchorPairs':len(c['anchorAABBPotentialPairs']),'potentialParts':sorted({r['part'] for r in c['anchorAABBPotentialPairs']})}))
if __name__=='__main__':main()
