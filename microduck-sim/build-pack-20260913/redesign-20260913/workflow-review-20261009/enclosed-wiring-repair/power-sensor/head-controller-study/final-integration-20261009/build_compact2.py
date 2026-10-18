from pathlib import Path
import json,numpy as np,trimesh,hashlib
F=Path(__file__).resolve().parent;r=json.loads((F/'original-inset-pi4-package.json').read_text());T=np.array(r['boardNativeToWorld']);removed=[];keep=[]
for q in r['parts']:
 if q['key'] in ['C22 receiving','C5 relief'] or 'C22' in q['key'] or 'C5' in q['key'] or q['group']=='pi_interface_conditional':removed.append(q);continue
 if q['group']=='pi':q['worldTransform'][2][3]-=1.5;q['worldTransform'][1][3]-=4
 if q['group']=='speaker':
  S=np.eye(4);S[:3,:3]=[[0,-1,0],[1,0,0],[0,0,1]];S[:3,3]=np.array([20.,-19.,134.])-S[:3,:3]@np.array([-3.,12.,132.]);q['worldTransform']=(S@q['worldTransform']).tolist()
 keep.append(q)
r['parts']=keep;r['piCurrentWorldDelta'][2][3]-=1.5;r['piCurrentWorldDelta'][1][3]-=4
P=np.array(r['piCurrentWorldDelta']);n=P[:3,:3]@[-1.,0,0];w=P[:3,:3]@[0.,1,0];v=P[:3,:3]@[0.,0,1];mouth=(P@np.array([44.,-9.9113773,133.6,1]))[:3]
def box(key,size,M,group):
 m=trimesh.creation.box(size);m.apply_transform(M);p=F/(key+'.stl');m.export(p);r['parts'].append({'key':key,'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'worldTransform':np.eye(4).tolist(),'group':group,'geometryKind':'declared-receiving-envelope'});return m.bounds.tolist()
M=np.eye(4);M[:3,:3]=np.column_stack([w,v,n]);M[:3,3]=mouth-v*6.65+n*7.3
micro=box('compact2-micro-PCB-receiving',[17,13.3,3.6],M,'micro_receiver')
# Manufacturer photo-based whole PCB receiver: 17.5 wide,14 from port toward -normal,5 deep.
# Does not claim vendor tolerance or exact mate. Standard C metal interface is inside source socket and separate datum.
C=np.eye(4);C[:3,3]=[.015,34.1+2.5,3.23-7];C[:3,:3]=[[1,0,0],[0,0,1],[0,-1,0]]
cb=box('compact2-typeC-PCB-receiving',[17.5,14,5],T@C,'c_receiver')
r['removedConditionalReferences']=[{'key':q['key'],'reason':'Existing straight/historical receiver remains negative reference; not silently accepted with new connector.'}for q in removed];r['connectorProposal']={'supplier':'https://fpv-solution.com/product/usb-ends/','micro':'Micro USB 1 or 2 OTG, outward orientation to Pi backside','typeC':'USB type C 90 degree sink','ribbon':'100 mm same supplier FFC, free span to be checked','status':'Proposed purchase only; no order; dimensions receiving assumptions, physical keyed mating/USB enumeration required','microDimensionsSource':'Adafruit4104 published PCB17x13.3x3.6; analogous FPV kit photo, not identical SKU tolerance','cDimensionsSource':'supplier DSC_0150 photo scaled against USB C metal width8.4mm; rounded 17.5x14x5 receiving; not dimensioned manufacturer CAD','bounds':{'micro':micro,'c':cb}}
r['stage']='Complete rigid package with proposed low profile direct USB interfaces. Pi moves down1.5mm and negativeY4mm to address measured connector roof contact; speaker rotated to negative cheek and inset6mm to free downward C exit. Diagnostic until full inventory/assembly passes.'
(F/'compact2-package.json').write_text(json.dumps(r,indent=2)+'\n');s=(F/'check_package.py').read_text().replace("src=F/'joint-package.json'","src=F/'compact2-package.json'").replace("'joint-check-'","'compact2-check-'");(F/'check_low_profile.py').write_text(s);print(json.dumps({'removed':[q['key']for q in removed],'receivers':r['connectorProposal']['bounds']}))
