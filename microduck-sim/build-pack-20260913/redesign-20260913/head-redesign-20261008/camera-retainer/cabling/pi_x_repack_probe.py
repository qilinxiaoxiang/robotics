"""Finite Pi translations, entireboard andcurrenthead obstacles; no mountingrelease."""
from pathlib import Path
import json,hashlib,sys,inspect,numpy as np
D=Path(__file__).resolve().parent
import s_bend_lead_search as s
c=s.c
baseobs=c.obs.copy();basepi=c.pi.copy();baseslots=c.slots.copy();moving=['pi','zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails']
# Add current canonicaljaw/drive details (allworldmeshes indata); count atmost
# onceperkey. Thesearethe actualnewjaw/currentassembledhead, notoldproxy.
keys=[]
for k,p in c.P.items():
 if p.get('moduleId') in ['jaw','head','neck'] and k not in c.obs and k not in moving and k not in ['camera_board','face_panel','head_cap','openrb','speaker','amplifier']:
  try:baseobs[k]=c.dec(k);keys.append(k)
  except (KeyError,ValueError):pass
# Applyactualcurrentjawreplacementfragment, andalso originalupwardcamera
# forwholeboardplacement. Cablepathremainsseparate90degreecandidate.
J=c.H/'jaw-access';jf=json.loads((J/'viewer-fragment.json').read_text());addedFiles=[]
for key,rel in jf['replacementMeshes'].items():
 p=c.H/rel;baseobs[key]=c.man(c.trimesh.load_mesh(p));addedFiles.append(p)
for a in jf['additionalParts']:
 p=c.H/a['mesh'];baseobs[a['key']]=c.man(c.trimesh.load_mesh(p));addedFiles.append(p)
originalCamera={}
for key,filename in [('camera','camera-shifted-reference-world.stl'),('face','face-with-camera-anchors-world.stl'),('retainer','camera-retainer-world.stl'),('six_camera_screws','camera-all-six-screw-envelopes-world.stl')]:
 p=D.parent/filename;originalCamera[key]=c.man(c.trimesh.load_mesh(p));addedFiles.append(p)
# Exactrootintegrationconfigurationisthe finalauthorityforcurrentplacements.
configPath=c.H/'viewer-candidate.json';config=json.loads(configPath.read_text());assert not config['transforms']
scene={k:c.dec(k) for k in c.P if k not in config['removedParts']}
for key,rel in config['replacementMeshes'].items():
 p=c.H/rel;scene[key]=c.man(c.trimesh.load_mesh(p));addedFiles.append(p)
for a in config['additionalParts']:
 p=c.H/a['mesh'];scene[a['key']]=c.man(c.trimesh.load_mesh(p));addedFiles.append(p)
# Keep individualreceivedboardenvelopes forattributable collisionvolumes.
for k in moving[1:]:scene[k]=baseobs[k]
moving+=['zero_w_populated_receiving','pi_usb_receiving']
rename={'head_cap':'curved_cap','camera_board':'camera','face_panel':'face','camera_retainer':'retainer','camera_mount_screws':'six_camera_screws'}
scene={rename.get(k,k):v for k,v in scene.items()}
originalCamera={k:scene[k] for k in ['camera','face','retainer','six_camera_screws']}
baseobs=scene.copy()
# Onlythecablecandidateusesitsown90degreecameramechanics; boardplacement
# reportsusethepublishedoriginalupwardcameraabove.
for k in originalCamera:baseobs[k]=c.obs[k]
addedFiles.append(configPath)
code=inspect.getsource(c.make).replace('def make(', 'def make_reception(').replace('(arc-5)/8','(arc-30)/2.25');exec(code,c.__dict__)
rows=[]
for dx in [0,-1,-2,-3]:
 c.pi=basepi+[dx,0,0];c.obs=baseobs.copy();c.slots=baseslots.copy();c.slots['zero_w_components']=baseslots['zero_w_components'].translate([dx,0,0])
 for k in moving:c.obs[k]=baseobs[k].translate([dx,0,0])
 hit={}
 boardObstacles=baseobs|originalCamera
 for k in moving:
  for f,o in boardObstacles.items():
   if f in moving:continue
   q=c.obs[k]^o;v=max(0,q.volume())
   if v>1e-5:hit[k+'--'+f]={'volumeMm3':v,'boundsMm':list(q.bounding_box())}
 # Do notletduplicatedoldface/oldcameraorlegacycapdenythiscandidate; keyslist
 # isreportedforexplicitreview. Primaryboardcollisionverdictcomesfromknown
 # replacedobstacles inbaseobs andcanonicaljawparts.
 rr=[]
 for left in [53.5,52.5,51.5,50.5]:
  s.front=34.9;lead=1.5;top=c.pi[1]+3+lead+.3+.5
  try:r=c.make_reception(left=left,top=top,width=11.5,thick=.3,lead=lead)
  except AssertionError:rr.append({'leftXmm':left,'status':'R3_FILLET_TANGENTS_OVERLAP'});continue
  rr.append(r[-1])
 row={'translationXmm':dx,'boardCollisions':hit,'routes':rr};rows.append(row);print(json.dumps(row),flush=True)
report={'date':'2026-10-08','status':'FINITE_PLACEMENT_AND_ROUTING_ONLY','assemblyAcceptance':False,'movesWholeBoard':moving,'extraCanonicalHeadKeys':keys,'rows':rows,'mounting':'MovingPiwithdrawsitfromoldfaceposts; mountingholes/postsandretentionnotredesigned.Notassemblyready evenifplacementwereclear.','sourceConfirmedWidthMm':11.5,'receivingAssumptions':{'standardEndWidthMm':16,'standardEndReceivingLengthMm':30,'transitionLengthMm':2.25,'thicknessMm':.3,'minimumBendRadiusMm':3,'outsidePiStraightMm':1.5},'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*c.files.values(),*addedFiles,J/'viewer-fragment.json',c.G/'full-build-data.json',D/'pi_x_repack_probe.py',D/'sc1892-official-spec.json']}}
(D/'pi-x-repack-report.json').write_text(json.dumps(report,indent=2)+'\n')
