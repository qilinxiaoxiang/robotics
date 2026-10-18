from pathlib import Path
import json,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[2];HD=W/'enclosed-wiring-repair/head-layout';H=W.parent/'head-redesign-20261008';hashes={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):hashes[str(p)]=sha(p);return json.loads(Path(p).read_text())
def load(p):hashes[str(p)]=sha(p);m=trimesh.load_mesh(p);assert m.is_volume;return mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)))
T=np.array(read(HD/'native-fusion-repair-inputs.json')['openrb']['nativeToCurrentWorld']);p=read(HD/'openrb-usbc-native-port.json')['correctedAssumedMouldShoulderMm'];capfile=H/'curved-head/community-curved-head-world.stl';cap=load(capfile).transform(np.linalg.inv(T)[:3]);rows=[]
def test(L):
 b=mf.Manifold.cube([12,L,7]).translate([p[0]-6,p[1],p[2]-3.5]);q=b^cap;assert q.status()==mf.Error.NoError;return max(0,q.volume())
for L in [0.25,.5,1,2,3,4,5,8,12,22]:rows.append({'axialLengthMm':L,'intersectionMm3':test(L)})
lo=0;hi=22
for i in range(18):
 mid=(lo+hi)/2
 if test(mid)>1e-7:hi=mid
 else:lo=mid
pins=read(D/'actual-pin-components.json');inv=read(HD/'audio-relocation/positive-y13-native/current-rigid-inventory.json');targets={}
for k in ['REFERENCE Pi current pi','REFERENCE MicroB photo receiving']:
 q=next(q for q in inv['parts']if q['id']==k);s=load(q['file']).transform(np.array(q['worldTransform'])[:3]);targets[k]=s
pinchecks=[]
for q in pins['records']:
 assert sha(q['file'])==q['sha256'];s=load(q['file'])
 for n,b in targets.items():
  z=s^b;pinchecks.append({'component':q['index'],'fixed':n,'actualIntersectionMm3':max(0,z.volume()),'boundsMm':list(z.bounding_box())if z.volume()>1e-6 else None})
# Original bare shell versus real PCB excludes retired/new mount material.
pcbmeta=read(HD/'actual-openrb-components/micro-contact-proof.json');q=next(q for q in pcbmeta['records']if q['index']==141);pcb=load(q['mesh']);orig=load(capfile);v=(pcb^orig).volume()
r={'status':'ORIGINAL_HEAD_DATUM_INTERFACE_DEFICIENCIES','usbC':{'nativeShoulderMm':p,'nativeAxis':[0,1,0],'receiverCrossSectionMm':[12,7],'axialContactBracketMm':[lo,hi],'samples':rows,'axialMouldLengthMm':22,'strainReliefAdditionalMm':5,'scope':'Measured along fixed original controller axis against original community closed shell. Width12 and axial22+5 from source drawing;7mm thickness and shoulder1.2mm remain receiving assumptions. No right-angle product is selected.'},'actualPinChecks':pinchecks,'actualPinSumsMm3':{n:sum(q['actualIntersectionMm3']for q in pinchecks if q['fixed']==n)for n in targets},'actualPCBOriginalBareShellIntersectionMm3':v,'currentAdditionsCanBeRevised':True,'sourceHashes':hashes|{str(Path(__file__)):sha(__file__)}}
(D/'original-interface-measurements.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'C_axial':r['usbC']['axialContactBracketMm'],'pinSums':r['actualPinSumsMm3'],'pcbBareCap':v,'samples':rows},indent=2))
