from pathlib import Path
import os,json,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n);np=n['np'];mf=n['mf'];tm=n['trimesh'];read=n['read'];read(Path(__file__));m=json.loads(read(D/'local-candidate-manifest.json'));files=m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']}
def load(p):
 read(p);q=tm.load(p,force='mesh');assert q.is_watertight,str(p);s=mf.Manifold(mf.Mesh64(np.array(q.vertices,np.float64),np.array(q.faces,np.uint64)));assert s.status()==mf.Error.NoError and s.volume()>0;return s
camdelta=[.8,0,0];pidelta=[2,0,0];cam=load(H/files['camera_board']).translate(camdelta);fov=load(D/'camera-fov-roll90-rearseat4-world.stl').translate(camdelta);af=load(D/'camera-rearseat4-af-additional-receiving-world.stl').translate(camdelta)
checks=[];pikeys=['pi','zero_w_components','zero_w_gpio_solder_tails']+[q['key'] for q in json.loads(read(D/'gpio-individual-receiving-manifest.json'))['additionalParts']]
for k in pikeys:
 s=load(H/files[k]).translate(pidelta);v,bb=n['volume'](cam,s);gap=cam.min_gap(s,5);checks.append({'moving':'camera','fixed':k,'overlapMm3':v,'minimumGapCapped5Mm':float(gap),'boundsMm':bb});del s;gc.collect()
for k in ['face_panel','eye_trim','head_cap']:
 s=load(H/files[k]) if k in files else n['source'](k)
 for name,q in [('camera',cam),('FOV',fov),('AF',af)]:
  v,bb=n['volume'](q,s);checks.append({'moving':name,'fixed':k,'overlapMm3':v,'minimumGapCapped5Mm':float(q.min_gap(s,5)),'boundsMm':bb})
 for sid in ['camera-1','camera-2','camera-3','camera-4']:
  q=load(D/(sid+'-roll90-rearseat4-screw-world.stl')).translate(camdelta);v,bb=n['volume'](q,s);checks.append({'moving':sid,'fixed':k,'overlapMm3':v,'minimumGapCapped5Mm':float(q.min_gap(s,5)),'boundsMm':bb})
 del s;gc.collect()
r={'integrationReady':False,'scope':'Flat camera moved forward 0.8mm; classify required internal face screw relief without changing lens YZ or eye profile','cameraDeltaFromRearseatMm':camdelta,'piDeltaFromLoweredMm':pidelta,'cameraCsiMouthMm':[75.63,9.3706236,131.1145958],'checks':checks,'sourceHashes':n['hashes']};(D/'forward-camera-boundary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'failures':[r for r in checks if r['overlapMm3']>1e-5],'sub0p5Clearances':[r for r in checks if r['minimumGapCapped5Mm']<.5]},indent=2))
