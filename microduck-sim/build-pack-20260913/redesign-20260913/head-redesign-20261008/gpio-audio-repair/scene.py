"""Read-only scene assembly shared by the independent GPIO/audio repair checks."""
from pathlib import Path
import sys,json,hashlib,ast
D=Path(__file__).resolve().parent;H=D.parent;C=H/'cabling-release-20261008'
sys.path.insert(0,str(C))
from check_routes import np,trimesh,mf,man,tri,load,hits,tube,read,data,config,obs,meshes,hashes
hashes[str(Path(__file__).relative_to(H.parent))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
for node in ast.parse((H/'usb-access/full-harness/build_harness.py').read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['arc','rounded']:exec(compile(ast.Module(body=[node],type_ignores=[]),'<source circular arcs>','exec'))
# Replace the old aggregate receiver with independent conservative board bodies.
obs.pop('zero_w_populated_receiving',None)
for k in ['zero_w_components','zero_w_gpio_solder_tails']:
 obs[k]=man(load(H/'curved-head'/(k+'-world.stl')))
for k,f in [('head_cap','cap-neck-slot-closure-candidate-world.stl'),('amplifier','amplifier-audio-rotation-candidate-world.stl'),('curved_cap_hardware','hardware-audio-rotation-candidate-world.stl'),('speaker_keeper','speaker-keeper-wire-relief-candidate-world.stl')]:
 obs[k]=man(load(C/f))
for i in [0,1]:obs[f'speaker_wire_{i}']=man(load(C/f'speaker-wire-{i}-candidate-world.stl'))
PIN_NETS={1:('imu-vin',.8),2:('pi-5v-2',1.8),3:('imu-sda',.8),4:('pi-5v-4',1.8),5:('imu-scl',.8),6:('pi-gnd-6',1.8),9:('imu-gnd',.8),12:('audio-12',1.5),14:('pi-gnd-14',1.8),20:('audio-20',1.5),35:('audio-35',1.5),40:('audio-40',1.5)}
PCB_FACE_X=67.31

def port(pin,depth=18):return np.array([PCB_FACE_X-depth,-24.141+2.54*((pin-1)//2),118.2796+(2.54 if pin%2==0 else 0)])
def housing(depth=18):return mf.Manifold.cube([depth,52,7],True).translate([PCB_FACE_X-depth/2,-.011,119.5496])
def intersections(s,skip=()):return {k:v for k,o in obs.items() if k not in skip and (v:=hits(s,o))>1e-5}

def discrete_header(depth=18):
 # Full male40pin8.5mm receiver plus onlythe12populatedfemale bodies.
 pieces=[housing(8.5)]
 for pin in PIN_NETS:
  p=port(pin,depth);pieces.append(mf.Manifold.cube([depth-2.54,2.54,2.54],True).translate([PCB_FACE_X-(depth+2.54)/2,p[1],p[2]]))
 return mf.Manifold.batch_boolean(pieces,mf.OpType.Add)
