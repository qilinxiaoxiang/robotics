"""Subtractive-only camera throat overlay; frozen candidate is immutable."""
from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(D/'build_reverse_nut_camera.py');m=json.loads(read(O/'candidate-manifest.json'));files=m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']};cam=load(H/files['camera_board']);housing=cam^box([79.05,-50,100],[95,50,160]);bb=np.array(housing.bounding_box()).reshape(2,3)
# Axis-aligned enclosing box deliberately exceeds the actual housing; 0.55 mm
# radial receiving, limited to hidden rear throat. Does not cut PCB bearing plane.
cut=box([79.05,-5.4913835525512695-.55,125.714599609375-.55],[83.0699966430664+.55,5.308627128601074+.55,136.5146026611328+.55]);rows=[];new={}
for k in ['face_panel','eye_trim']:
 old=load(H/files[k]);q=old-cut;added=max(0,(q-old).volume());protected=box([83.62,-100,0],[200,100,250]);pr=max(0,((old-q)^protected).volume());assert added<1e-9 and pr<1e-9 and len(q.decompose())==1
 path=export(q,k+'_throat055');rows.append({'part':k,'mesh':path,'addedVolumeMm3':added,'removedVolumeMm3':max(0,(old-q).volume()),'removedBoundsMm':list((old-q).bounding_box()),'oldBoundsMm':list(old.bounding_box()),'newBoundsMm':list(q.bounding_box()),'protectedVisibleFrontRemovedMm3':pr,'minimumCameraHousingGapMm':float(housing.min_gap(q,2)),'bodies':len(q.decompose())});new[k]=q
checks=[]
for key in ['camera_fov_clamped','camera_af_clamped']:
 q=load(O/(key+'-world.stl'))
 for fk,f in new.items():
  v,b=n['volume'](q,f);checks.append({'moving':key,'obstacle':fk,'overlapMm3':v,'boundsMm':b})
r={'integrationReady':False,'baseCandidateSha256':n['hashes'][str(O/'candidate-manifest.json')],'engineeringGapTargetMm':.5,'replacementMeshes':{q['part']:q['mesh'] for q in rows},'checks':checks,'parts':rows,'exteriorPreservation':'Subtractive internal aperture relief, no outer overall bounds change; visual perimeter and remaining walls require reported cross section checks','physicalStrengthVerified':False,'sourceHashes':n['hashes']};(O/'camera-throat-subtractive-overlay.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'parts':rows,'checks':checks},indent=2))
