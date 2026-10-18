"""Integral roof saddle, open-bottom insertion and one narrow-tie channel."""
import json,gc
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
D=Path(__file__).resolve().parent;H=D.parent;O=D/'speaker-rewire';c.guarded_import();nativefile=H/'curved-head/community-curved-head-world.stl';native=pm.load(c,nativefile)
x=34.8;y=-23.25;z=137.7849994;patch=native^c.mf.Manifold.cube([5.2,7.1,60],True).translate([x,y,140]);fill=patch
for step in range(1,26):fill=(fill+patch.translate([0,0,-step])).as_original();gc.collect()
post=fill^c.mf.Manifold.cube([5.2,7.1,35]).translate([x-2.6,y-3.55,z-1.0])
for yy in [-21.5,-25]:
 bore=c.mf.Manifold.cylinder(5.4,1.,circular_segments=48).rotate([0,90,0]).translate([x-2.7,yy,z]);opening=c.mf.Manifold.cube([5.4,1.8,4]).translate([x-2.7,yy-.9,z-4]);post=post-bore-opening
slot=c.mf.Manifold.cube([2.8,8,1.2],True).translate([x,y,z+2.7]);post=post-slot
out=O/'speaker-pair-roof-saddle-world.stl';rt=pm.export(c,post,out)
r={'integrationReady':False,'dimensionsMm':{'outerX':5.2,'outerY':7.1,'wireBoreDiameter':2,'wireReceivingDiameter':1.5,'openBottomGap':1.8,'tieSlotWidth':2.8,'tieSlotThickness':1.2,'minimumXWeb':1.2},'mounting':'Integral addition under native roof; saddle open toward-Z so the prewired pair is placed without threading terminations. One2.5mm narrow tie, stock not confirmed, would secure both wires through upperY slot; no tie acceptance or physical grip claimed yet.','inputHashes':c.fingerprint([Path(__file__),nativefile,D/'speaker-rewire-amp16z2p0-proposal.json']),'meshSha256':c.sha(out),'mesh':rt,'pending':['exact static','tie geometry','12-pose regression/full domain','prewired insertion and tool access','physical printed retention strength']};c.atomic_json(O/'speaker-restraint-proposal.json',r);print(json.dumps({'mesh':str(out),'watertight':rt['watertight'],'bounds':list(post.bounding_box())}))
