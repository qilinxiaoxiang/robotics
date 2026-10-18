"""Source-sized terminal receiver, complete speaker prewire, and finite tolerance tests."""
from scene import *
# SourceSTEP excludes terminal. Keep old10.4mm height and8mm depth conservative,
# enlarge width to8.3mm (Adafruit-linked4UCON2-position body7.8+0.5 tolerance).
T0=np.eye(4);T0[:3,3]=[24.1100006104,-33.797000885,132.0149994]
Tr=trimesh.transformations.rotation_matrix(np.pi/2,[0,0,1],[33,-24,138]);Tr[1,3]+=.8
T=Tr@T0
terminal=mf.Manifold.cube([8.3,8,10.4],True).translate([8.79,15.594,6.77]).transform(T[:3])
amp=obs['amplifier']+terminal;obs['amplifier']=amp
tri(amp).export(D/'amplifier-terminal-receiving-world.stl')
# Exact EagleX1 pin axes. Front hole height2.2mm aboveterminalbase is scaled
# from manufacturerdrawing, so sweep±0.5 as receiving allowance.
mouth_z=132.0149994+1.57+2.2
r=json.loads(read(C/'audio-route-candidate.json'))
newpaths=[];solids=[];allrows=[]
for i,x in enumerate([-7.77,1.77]):
 best=None
 # Retain the original rearward route; adjust only terminalapproachheight.
 for dropx in [16,17,18,19,20]:
  end=np.array([23.203,-21.5-i*3.5,mouth_z]);rear=-12.+i*2.5;y=-4.5-i*1.5
  wp=np.array([[x,.94,132.35],[x,.94,134.85],[x,y,134.85],[rear,y,134.85],[rear,-18-i*1.5,135.5-i*1.8],[dropx,end[1],mouth_z],end],float)
  try:pts,L=rounded(wp,2.)
  except ValueError:continue
  s=tube(pts,.75);hh={}
  for k,o in obs.items():
   if k.startswith('speaker_wire_'):continue
   if k=='speaker':o-=mf.Manifold.cube([3.4,3.4,2.6],True).translate(wp[0])
   if k=='amplifier':o-=mf.Manifold.cube([2,2.2,2.6],True).translate(end)
   if(v:=hits(s,o))>1e-5:hh[k]=v
  allrows.append({'wire':i,'dropX':dropx,'hits':hh})
  if not hh:best=(wp,pts,L,s,end);break
 if best is None:continue
 wp,pts,L,s,end=best;solids.append(s);newpaths.append({'id':i,'pointsMm':pts.tolist(),'waypointsMm':wp.tolist(),'lengthMm':L,'diameterMm':1.5,'minimumRadiusMm':2,'terminalWireHeightAboveBodyBottomMm':2.2,'sourceDrawingHeightToleranceReceivingMm':.5})
 tri(s).export(D/f'speaker-wire-{i}-world.stl')
report={'problemIds':['P5','P6'],'sourceHashes':hashes,'paths':newpaths,'candidateRows':allrows,'terminalLocalToWorld':T.tolist(),'ampOtherHits':{k:v for k,v in intersections(amp,['amplifier','speaker_wire_0','speaker_wire_1','curved_cap_hardware']).items() if v>2e-5},'wirePairOverlapMm3':hits(*solids) if len(solids)==2 else None,'physicalVerified':False,'integrationReady':False}
(D/'audio-design.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['paths','sourceHashes']},indent=2))
