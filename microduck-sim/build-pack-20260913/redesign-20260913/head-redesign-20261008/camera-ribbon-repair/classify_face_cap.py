from pathlib import Path
import os,json,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n)
np=n['np'];mf=n['mf'];read=n['read'];load=n['loadfile'];mesh=n['mesh'];read(Path(__file__))
def precise(p):
 read(p);m=n['trimesh'].load(p,force='mesh');assert m.is_watertight;s=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
cap=precise(H/'gpio-audio-repair/cap-amp16z2/cap-current-audio-usb-world.stl');old=precise(H/'face-eye-camera-clearance-world.stl');current=precise(D/'face-pi-camera-three-mount-world.stl');contact=cap^current
v=lambda s:max(0,float(s.volume()))
report={'accepted':False,'sourceFaceContactMm3':v(cap^old),'currentContactMm3':v(contact),'addedFaceContactMm3':v(contact-old),'retainedFaceContactMm3':v(contact^old),'contactBoundsMm':list(contact.bounding_box()),'sourceHashes':n['hashes']}
mesh(contact-old).export(D/'face-cap-added-contact-diagnostic-world.stl')
(D/'face-cap-contact-classification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
