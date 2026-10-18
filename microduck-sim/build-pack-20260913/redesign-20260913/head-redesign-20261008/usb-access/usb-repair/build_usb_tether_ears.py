"""Small exterior tether eyes; a strain restraint, not an unverified rigid USB jig."""
from pathlib import Path
import hashlib,json,os,sys,types
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent.parent
sys.path.insert(0,str(H/'gpio-audio-repair'))
from precision_mesh import load,export
c=types.SimpleNamespace(np=np,tm=tm,mf=mf)
source=H/'gpio-audio-repair/speaker-rewire/cap-audio-speaker-restraint-print-candidate-world.stl'
out=D/'usb-tether-ears';out.mkdir(exist_ok=True)
cap=load(c,source);mesh=tm.load(source,force='mesh');tri=mesh.triangles
def heights(x,y):
    a=tri[:,0,:2];u=tri[:,1,:2]-a;v=tri[:,2,:2]-a;p=np.array([x,y])-a
    den=u[:,0]*v[:,1]-u[:,1]*v[:,0];valid=np.abs(den)>1e-10
    aa=np.zeros(len(tri));bb=aa.copy()
    aa[valid]=(p[valid,0]*v[valid,1]-p[valid,1]*v[valid,0])/den[valid]
    bb[valid]=(u[valid,0]*p[valid,1]-u[valid,1]*p[valid,0])/den[valid]
    hit=valid&(aa>=-1e-9)&(bb>=-1e-9)&(aa+bb<=1+1e-9)
    z=tri[hit,0,2]+aa[hit]*(tri[hit,1,2]-tri[hit,0,2])+bb[hit]*(tri[hit,2,2]-tri[hit,0,2])
    return np.unique(np.round(z,7))
if '--roof-grid' in sys.argv:
 print(json.dumps({'bounds':mesh.bounds.tolist(),'roofGrid':{str((x,y)):heights(x,y).tolist() for x in range(-15,81,5) for y in (-21,-18,-15,15,18,21)}}));sys.exit(0)
ears=[];rows=[]
for x in (0.,35.):
 for y in (-18.,18.):
    rays=[heights(x+dx,y+dy) for dx in np.linspace(-3,3,7) for dy in np.linspace(-3,3,7)]
    assert all(len(z)>=2 for z in rays),('Eye footprint outside curved roof',x,y,mesh.bounds.tolist(),[z.tolist() for z in rays if len(z)<2])
    outer=np.array([z[-1] for z in rays]);inner=np.array([z[-2] for z in rays])
    floor=float(max(outer.min()-.8,inner.max()+.3));top=float(outer.max()+4.4)
    assert floor>inner.max()+.2,('Eye would enter internal cavity',x,y,floor,inner.max())
    body=mf.Manifold.cube([6,6,top-floor],True).translate([x,y,(floor+top)/2])
    hole=mf.Manifold.cube([3.3,6.4,1.8],True).translate([x,y,float(outer.max()+2.2)])
    ear=body-hole;contact=float((ear^cap).volume());assert contact>5
    ears.append(ear);rows.append({'centerXY':[x,y],'footZ':floor,'topZ':top,'roofZRange':[float(outer.min()),float(outer.max())],'roofContactMm3':contact,'interiorVerticalClearanceLowerBoundMm':float(floor-inner.max())})
new=cap
for ear in ears:new=new+ear
assert new.status()==mf.Error.NoError and len(new.decompose())==1
path=out/'cap-usb-tether-eyes-candidate-world.stl';evidence=export(c,new,path)
added=new-cap;export(c,added,out/'tether-added-volume-world.stl')
report={'status':'CANDIDATE_REQUIRES_ENTRY_AND_ASSEMBLY_CHECK','purpose':'Four small exterior eyes for adjustable removable straps; prevents loose USB harness pulling directly on Pi socket. Does not claim to rigidly locate the floating USB-A pair.',
 'strapReceivingSpec':{'maximumWidthMm':2.5,'maximumThicknessMm':1.0,'slotMm':[3.3,1.8],'stockVerified':False},'eyes':rows,'addedVolumeMm3':float(added.volume()),'removedOriginalVolumeMm3':max(0,float((cap-new).volume())),'oneBody':True,'export':evidence,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,path,Path(__file__)]},'physicalFitVerified':False,'integrationReady':False}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'eyes':rows,'addedVolumeMm3':report['addedVolumeMm3']}))
