from pathlib import Path
import os,json,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n)
read=n['read'];load=n['loadfile'];read(Path(__file__));m=json.loads(read(D/'local-candidate-manifest.json'));paths=m['replacementMeshes']|{a['key']:a['mesh'] for a in m['additionalParts']};paths['amplifier']='gpio-audio-repair/amp16z2-placement-world.stl'
f=D/'sc1892-roof-fold-receiving-world.stl';fit=json.loads(read(D/'roof-fold-ribbon-fit.json'));assert fit.get('meshSha256')==__import__('hashlib').sha256(read(f)).hexdigest(), 'No current exact-endpoint ribbon mesh';c=load(f);assert c.status()==n['mf'].Error.NoError and c.volume()>1800;assert n['trimesh'].load(f,force='mesh').is_watertight;key=sys.argv[1]
if key=='native_head_cap':
 o=n['source']('head_cap')
elif key in paths:
 f=D.parent/paths[key];read(f);o=load(f)
else:o=n['source'](key)
raw,rawbb=n['volume'](c,o);slot=None
if key=='zero_w_components':
 T=n['np'].array(m['piWorldTransform']);slot=n['mf'].Manifold.cube([.6,4.4,11.5],True).translate([65.8,32.4886208-2.2,131.0496]).transform(T[:3])
if key=='camera_board':slot=n['mf'].Manifold.cube([.6,5,16],True).translate([76.03,9.3706236-2.5,131.1145958])
v,bb=n['volume'](c,o-slot if slot is not None else o);out=D/('roof-fold-pair-'+key+'.json');out.write_text(json.dumps({'accepted':False,'part':'full16mm200mmFFC','obstacle':key,'volumeMm3':v,'rawVolumeMm3':raw,'exactMatingSlotApplied':slot is not None,'intersectionBoundsMm':bb,'sourceHashes':n['hashes']},indent=2)+'\n');print(key,v,bb,flush=True)
