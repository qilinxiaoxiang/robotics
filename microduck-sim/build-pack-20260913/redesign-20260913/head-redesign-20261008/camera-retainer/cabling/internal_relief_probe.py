"""Finite candidate: retain originalcap exterior; test minimum1.2mmremaining skin.
Onlythisdirectorywritesoutputs. NominaldimensionsnotestablishedbyPCNarestated.
"""
from pathlib import Path
import json,hashlib,sys,inspect
import numpy as np,trimesh,manifold3d as mf
import s_bend_lead_search as s
c=s.c;D=Path(__file__).resolve().parent
# Source-confirmed11.5mmbody/16mmstandardend. Oversizeendlength30mm plus
# 2.25mmtransition is receivingenvelope; PCN36pictureisnotdimensioneddrawing.
code=inspect.getsource(c.make).replace('def make(', 'def make_reception(').replace('(arc-5)/8','(arc-30)/2.25')
exec(code,c.__dict__);make=c.make_reception
s.front=34.9
lead=float(sys.argv[1]) if len(sys.argv)>1 else 1.5
tag='' if len(sys.argv)==1 else '-lead'+str(lead).replace('.','p')
top=c.pi[1]+3+lead+.3+.5
nominal=make(top=top,width=11.5,thick=.3,lead=lead)
# 0.3mmextraeachsideofbodyandstandardtip. These aredesignclearancemargins,
# not manufacturer tolerances. Samecenterline/length asnominal.
code=code.replace('def make_reception(', 'def make_clearance(').replace('16-(16-width)','16.6-(16.6-width)').replace('11.5-(11.5-width)','12.1-(12.1-width)')
exec(code,c.__dict__)
clearance=c.make_clearance(top=top,width=12.1,thick=.9,lead=lead)
cap=c.obs['curved_cap'];cavity=clearance[0];removed=cap^cavity;candidate=cap-cavity
mesh=c.tri(cap);cm=c.tri(cavity)
# Sampleoutervisibilityalong+Yatlocalizedcutcrosssections. Lastcrossingis
# actualexternalhull. BecauseallpocketpointsareinsidepositiveYsideofhead,
# outerY minuspocketY isadirectskin-thicknessUPPERbound: if<1.2, true
# shortestwallthickness iscertainly<1.2. Thiscanreject, nevercertifybyitself.
lo,hi=cm.bounds
xs=np.arange(max(lo[0],50),min(hi[0],76)+1e-8,.15);zs=np.arange(max(lo[2],125),min(hi[2],138)+1e-8,.15)
xx,zz=np.meshgrid(xs,zs);orig=np.c_[xx.ravel(),np.full(xx.size,60.),zz.ravel()];directions=np.tile([0.,-1.,0.],(len(orig),1))
loc,idx,face=mesh.ray.intersects_location(orig,directions,multiple_hits=True)
outer={}
for p,i in zip(loc,idx):outer[int(i)]=max(outer.get(int(i),-1e6),float(p[1]))
cloc,cidx,cface=cm.ray.intersects_location(orig,directions,multiple_hits=True)
pocket={}
for p,i in zip(cloc,cidx):pocket[int(i)]=max(pocket.get(int(i),-1e6),float(p[1]))
rows=[]
for i,y in pocket.items():
 if i not in outer:continue
 rows.append({'Xmm':float(orig[i,0]),'Zmm':float(orig[i,2]),'externalSurfaceYmm':outer[i],'clearanceCavityYmm':y,'remainingYskinUpperBoundMm':outer[i]-y})
rows.sort(key=lambda r:r['remainingYskinUpperBoundMm']);fail=[r for r in rows if r['remainingYskinUpperBoundMm']<1.2]
# Onlygivecandidateasnegative diagnostic ifskinconstraintfails.
c.tri(removed).export(D/('internal-relief-removed-diagnostic'+tag+'-world.stl'))
c.tri(candidate).export(D/('internal-relief-cap-NOT-RELEASED'+tag+'-world.stl'))
report={'date':'2026-10-08','status':'REJECTED_INSUFFICIENT_REMAINING_SKIN' if fail else 'REQUIRES_SHORTEST_NORMAL_SKIN_AND_CLOSURE_TEST','released':False,'canonicalCapUnchanged':True,'minimumSkinRequirementMm':1.2,'additionalClearanceEachSideMm':.3,'officialBodyWidthMm':11.5,'standardEndWidthMm':16,'unknownDimensionsKeptExplicit':{'bodyThicknessAssumptionMm':.3,'minimumBendRadiusAssumptionMm':3,'standardEndReceivingLengthMm':30,'transitionReceivingLengthMm':2.25,'outsidePiStraightAssumptionMm':lead},'nominalRoute':nominal[-1],'cavityIntersections':clearance[-1]['intersectionsMm3'],'removedCapVolumeMm3':float(removed.volume()),'skinMethod':'Raygridsampled0.15mm inXandZ; +Yvisibilityidentifiesouterhull. Ydistanceisupperboundonshortestskin, soanysample<1.2 decisivelyrejects. Thisisnotapassingthicknesscertificate.','gridStepMm':.15,'sampleCount':len(rows),'minimumRemainingSkinUpperBoundMm':rows[0]['remainingYskinUpperBoundMm'] if rows else None,'violatingSampleCount':len(fail),'worst20Witnesses':rows[:20],'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'internal_relief_probe.py',D/'sc1892-official-spec.json',*c.files.values(),c.G/'full-build-data.json']}}
(D/('internal-relief-report'+tag+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','removedCapVolumeMm3','minimumRemainingSkinUpperBoundMm','violatingSampleCount','worst20Witnesses']},indent=2))
