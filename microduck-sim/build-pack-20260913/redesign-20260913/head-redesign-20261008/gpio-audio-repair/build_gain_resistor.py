"""Actual received axial100k dimensional receiving body, insulated bent leads."""
import json,math
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
from prepare_speaker_rewire import rounded
from check_speaker_rewire import tube
D=Path(__file__).resolve().parent;O=D/'speaker-rewire';c.guarded_import();cx=61.;cy=-19.39;cz=139.1
# Circumscribed outer insulation receiving envelope, rather than naked ceramic.
body=c.mf.Manifold.cylinder(6.8,1.6/math.cos(math.pi/32),circular_segments=32).rotate([-90,0,0]).translate([cx,cy-3.4,cz]);rows=[]
for key,sign,yend in [('GAIN',-1,-23.19999939),('VIN',1,-15.57999939)]:
 start=[cx,cy+sign*3.4,cz];yy=cy+sign*7.4;wp=[start,[cx,yy,cz],[56.257000885,yy,cz],[56.257000885,yend,cz],[56.257000885,yend,135.5849994]];pts,segs,L=rounded(wp,1,step=.1);lead=tube(pts,.6);f=O/f'gain-resistor-{key.lower()}-insulated-lead-world.stl';pm.export(c,lead,f);rows.append({'net':key,'waypointsMm':wp,'centerlineMm':pts,'minimumRadiusMm':1,'leadMetalDiameterMm':.6,'insulatedDiameterReceivingMm':1.2,'lengthMm':L,'meshSha256':c.sha(f)})
f=O/'gain-resistor-insulated-body-world.stl';pm.export(c,body,f)
r={'integrationReady':False,'bodyReceivingMm':[6.8,3.2],'sourceMetalBodyMaximumMm':[6.8,2.6],'insulationDimensions':'Receiving allowances, not confirmed heatshrink inventory.','centerWorldMm':[cx,cy,cz],'axisWorld':[0,1,0],'leads':rows,'inputHashes':c.fingerprint([Path(__file__),D/'gain-resistor-source-dimensions.json',D/'prepare_speaker_rewire.py',D/'check_speaker_rewire.py']),'bodySha256':c.sha(f),'pending':['Exact current scene and I2S mutual check','VIN power-wire branch splice and restraint','Terminal/pad solder shoulder acceptance','Insertion and closed-cap articulation'],'netContract':'GAIN100k→VIN preserved; geometry does not authorize placing two conductors into VIN through-hole. Branch splice remains separately designed.'};c.atomic_json(O/'gain-resistor-candidate.json',r);print(json.dumps({'lengths':[x['lengthMm'] for x in rows],'integrationReady':False}))
