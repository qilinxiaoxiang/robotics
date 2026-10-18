from pathlib import Path
f=Path(__file__).parent/'check_spacer2_prefix_current.py';exec(compile(f.read_text().split("solid=load(O/")[0],str(f),'exec'));read(f);read(Path(__file__))
import manifold3d as mf
occfile=H/'cabling-release-20261008/neck-repair/pi-local-components/local-occupancy.json';occ=json.loads(read(occfile))
for p,sha in occ['sourceHashes'].items():assert hashlib.sha256(read(Path(p))).hexdigest()==sha
solid=load(O/'spacer2-tilted-complete-ribbon-outside-world.stl');old=load(H/files['zero_w_components']).translate(delta)
T=np.array(json.loads(read(O/'pi-spacer2-pose.json'))['worldTransform']);B=np.array([[0,0,-1,8.1],[0,1,0,0],[1,0,0,115.6146],[0,0,0,1]],float)
# drawing XY height -> source board local -> world
C=np.array([[0,1,0,.435],[1,0,0,-32.511],[0,0,1,-59.21],[0,0,0,1]],float);M=T@B@C
xy=np.array(occ['localReplacementWindowOfficialXYMm']);window=mf.Manifold.cube([*(xy[1]-xy[0]),10]).translate([*xy[0],-1]).transform(M[:3])
remaining=old-window;rows=[];pieces=[]
for row in occ['rows']:
 cs=mf.CrossSection([row['footprintOfficialXYMm']]).offset(row['xyExpansionMm'],mf.JoinType.Round)
 prism=cs.extrude(row['heightAbovePcbMm']).transform(M[:3])^window
 v=n['volume'](solid,prism)[0];gap=float(solid.min_gap(prism,2));rows.append({'key':row['key'],'overlapMm3':v,'gapCapped2Mm':gap,'heightMm':row['heightAbovePcbMm'],'heightBasis':row['heightBasis']});pieces.append(prism)
refined=remaining
for piece in pieces:refined=refined+piece
v=n['volume'](solid,refined)[0]
# local handling diagnostic only: lift material s179..191 by .9 mm normal to PCB.
# Not a valid whole route or accepted deformation; quantifies adjacent available air.
inter=solid^window;lift=inter.translate((-T[:3,0]*.9).tolist());liftrows=[]
for row,piece in zip(occ['rows'],pieces):liftrows.append({'key':row['key'],'liftedLocalizedMaterialOverlapMm3':n['volume'](lift,piece)[0],'gapCapped2Mm':float(lift.min_gap(piece,2))})
handling=[]
for key in sorted((set(n['P'])|set(files))-removed-{'zero_w_components','openrb'}):
 ob=load(H/files[key]) if key in files else n['source'](key)
 if key in shiftKeys:ob=ob.translate(delta)
 handling.append({'key':key,'overlapMm3':n['volume'](lift,ob)[0],'gapCapped2Mm':float(lift.min_gap(ob,2))})
 del ob
r={'staticClear':v<1e-6,'fullRouteAccepted':False,'originalBoxOverlapMm3':n['volume'](solid,old)[0],'refinedOverlapMm3':v,'outsideWindowOverlapMm3':n['volume'](solid,remaining)[0],'expectedFootprints':len(rows),'completedFootprints':len(rows),'rows':rows,'manualAdjustmentDiagnostic':{'normalToPcbLiftMm':.9,'worldVector':(-T[:3,0]*.9).tolist(),'scope':'Only previously intersecting material, not length-preserving complete ribbon; identifies adjacent handling space, cannot certify adjusted full route','rows':liftrows,'rigidObstacleChecks':handling,'notChecked':'OpenRB and transitions to stationary rest of cable; local air-space only'},'sourceHashes':n['hashes']}
(O/'frozen-local-occupancy-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['staticClear','originalBoxOverlapMm3','refinedOverlapMm3','outsideWindowOverlapMm3']}));print([(x['key'],x['overlapMm3']) for x in rows if x['overlapMm3']>1e-6])
