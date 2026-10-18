"""Editable head electronics layout. All assembly coordinates: jaw_soft, mm.
Run with /tmp/microduck-cad-venv/bin/python. Does not modify source robot assets.
The cap retains the source head's attachment perimeter and the existing camera datum.
"""
from geometry import *
import json, cadquery as cq
from print_export import checked_print_export
OUT=HERE/'final';OUT.mkdir(exist_ok=True)
R=np.array([[0,0,1],[1,0,0],[0,1,0]])
ORIGIN=np.array([24.5,0,-18])
recs=json.loads((HERE.parent/'sources/openrb-solid-bounds.json').read_text())
def cylinder(c,r,h,axis=0):
    T=np.eye(4)
    if axis==0:T[:3,:3]=np.array([[0,0,1],[0,1,0],[-1,0,0]])
    elif axis==1:T[:3,:3]=np.array([[1,0,0],[0,0,1],[0,-1,0]])
    T[:3,3]=c
    return man(trimesh.creation.cylinder(radius=r,height=h,sections=48,transform=T))
def union(items):return manifold3d.Manifold.batch_boolean(items,manifold3d.OpType.Add)
def export(n,mm):
    m=tri(mm);m.export(OUT/(n+'.stl'));return m
def cqbox(c,d):return cq.Workplane('XY').box(*d).translate(tuple(c)).val()
O=add_pi(obstacles(True))
old=next(m for n,m,mm in obstacles() if n=='top_head_shell')
# Actual component-box proxy: four PCB holes retained; independent solids need not
# be fused exactly, unlike the single watertight collision reservation below.
actual=[];padded=[]
for i,r in enumerate(recs):
    b=np.array(r['bounds_mm']);a=cub(b.mean(0),np.ptp(b,axis=0))
    if i==135:
        for x in [-10.25,10.25]:
            for y in [-30.75,30.75]:a-=cylinder([x,y,.8],1.25,3,2)
    actual.append(a)
    padded.append(cub(b.mean(0),np.ptp(b,axis=0)+1.0))
actual=union(actual).transform(np.c_[R,ORIGIN])
padded=union(padded).transform(np.c_[R,ORIGIN])
components=[('openrb',tri(padded),padded)]
component_specs=[('amp',[25,-27,-26],[12,22,21]),('speaker',[20,28,0],[6,21,31])]
plug_specs=[('openrb_usb_plug',[27.2,0,23.6],[7,12,15]),('pi_usb_data_plug',[35.435,8.9,-56.1],[10,10,6]),('pi_usb_power_plug',[35.435,21.5,-56.1],[10,10,6]),('pi_camera_connector',[15.435,35.49,-56.1],[12,6,6])]
for n,c,d in component_specs+plug_specs:components.append((n,box(c,d),cub(c,d)))
# Squared hollow cowl. 1.2 mm roof/walls; original flange and screw features stay.
# Cut only within the new opening; preserve the original exterior perimeter.
outer=cub([20,0,-15],[44,84,96]) # X -2..42, Z -63..33
inner=cub([15.4,0,-15],[50.8,81.6,93.6]) # Open below: X -10..40.8
cap=man(old)+outer
cap-=inner
# The original face is a separate closing part. Its interference is removed
# from the replacement cowl, leaving the original face itself untouched.
face=next(mm for n,m,mm in O if n=='face_part')
cap-=face
# Camera foot plane / M3 hole centers preserved from the prior verified mount.
camera_z=-37.84501011669636;camera_x=42.66671433493411
platform=cub([(41.9+camera_x)/2,0,camera_z],[camera_x-41.9,36,20])
for y in [-11,11]:
    platform+=cylinder([40.4,y,camera_z],4.8,4.5)
    platform-=cylinder([41,y,camera_z],1.7,10)
cap+=platform
# OpenRB posts terminate exactly at the actual PCB component-side surface.
post_centers=[]
for y in [-10.25,10.25]:
    for z in [-48.75,12.75]:
        post_centers.append([y,z]);cap+=cylinder([(26.1+41)/2,y,z],2.3,41-26.1)
        cap-=cylinder([34,y,z],1.2,21)
# Captive M2 nuts at the outside surface, print-accessible and replaceable.
def hex_hole(c,af,h):
    m=trimesh.creation.cylinder(radius=af/np.sqrt(3),height=h,sections=6)
    T=np.eye(4);T[:3,:3]=np.array([[0,0,1],[0,1,0],[-1,0,0]]);T[:3,3]=c
    return man(m.apply_transform(T))
for y,z in post_centers:cap-=hex_hole([41.2,y,z],4.2,2.0)
# Audio carrier: open pockets hold components with two nylon ties per part.
# Ties pass through slots outside the reserved electronic envelope.
carrier_bits=[];carrier_cq=[]
def cb(c,d):
    carrier_bits.append(cub(c,d));carrier_cq.append(cqbox(c,d))
def tray(x,y,z,iy,iz):
    cb([x,y,z],[1.2,iy+2.4,iz+2.4])
    for sy in [-1,1]:cb([x+1.6,y+sy*(iy/2+.6),z],[3.2,1.2,iz+2.4])
    for sz in [-1,1]:cb([x+1.6,y,z+sz*(iz/2+.6)],[3.2,iy,1.2])
tray(17.8,-27,-26,23,22)
tray(15.8,28,0,22,32)
# Rails and small height transitions.
cb([17.8,-39.4,-6],[1.2,1.2,61])
cb([17.8,0,23],[1.2,80,2.4])
cb([16.8,28,20.6],[3.2,3,8])
cb([17.8,-35.5,-26],[1.2,8,2])
carrier=union(carrier_bits)
for y in [-36,36]:
    carrier+=cylinder([17.8,y,23],3.3,1.2)
    carrier-=cylinder([17.8,y,23],1.2,5)
    cap+=cylinder([(18.4+41)/2,y,23],2.3,41-18.4)
    cap-=cylinder([30,y,23],1.2,28)
    cap-=hex_hole([41.2,y,23],4.2,2.0)
# Tie slots are in the pocket floors, near each long-side edge.
for x,y,z,iy,iz in [(17.8,-27,-26,23,22),(15.8,28,0,22,32)]:
    for dy in [-iy/2+.9,iy/2-.9]:
        for dz in [-iz/2+3,iz/2-3]:carrier-=cub([x,y+dy,z+dz],[4,1.2,2.4])
# Camera holes go through the final union. Nut recess opens from below.
for y in [-11,11]:
    cap-=cylinder([41,y,camera_z],1.7,12)
    cap-=hex_hole([39.5,y,camera_z],5.8,2.5)
# Ribbon-cable exit (18 x 2 mm) lies clear of the existing camera foot.
cap-=cub([41.8,25,-50],[8,18,2])
# Plug service apertures allow real cable tails to exit without a submillimetre bend.
cap-=cub([27.2,0,33],[9,14,10])
for yy in [8.9,21.5]:cap-=cub([42,yy,-56.1],[9,11,8])
# Sound exits through the roof over the speaker.
for yy in [22,28,34]:
    for zz in [-10,-5,0,5,10]:cap-=cylinder([42,yy,zz],1.25,7)
# Keep the original moving/fixed parts untouched; cut their occupied volumes out
# of the newly squared skirt. Face screw-hole slugs are disconnected scrap.
for nn,oo,om in O:cap-=om
cc=tri(cap).split();discarded=[float(m.volume) for m in cc if m.volume<20]
cap=man(max(cc,key=lambda m:m.volume))
capmesh=export('head_cap_assembly',cap)
rackmesh=export('audio_carrier_assembly',carrier)
export('openrb_component_reservation_assembly',padded)
export('openrb_actual_box_proxy_assembly',actual)
for n,m,mm in components[1:]:export(n+'_reservation_assembly',mm)
# Print pose: cap outside face down, open cavity up; rack flat floor down.
poses={};print_readback={}
for n,m,flip in [('head_cap',capmesh,True),('audio_carrier',rackmesh,False)]:
    T=np.eye(4);T[:3,:3]=np.array([[0,1,0],[0,0,1],[-1,0,0] if flip else [1,0,0]])
    if np.linalg.det(T[:3,:3])<0:T[0,:3]*=-1
    p=m.copy().apply_transform(T);T[:3,3]=-p.bounds[0];p=m.copy().apply_transform(T)
    print_readback[n]=checked_print_export(OUT/(n+'_print.stl'),p);poses[n]=T.tolist()
parts=[('head_cap',capmesh,cap),('audio_carrier',rackmesh,carrier)]
checks={}
for n,m,mm in parts:
    checks[n]={'watertight':bool(m.is_watertight),'connected_components':len(m.split()),'volume_mm3':float(m.volume),'solid_PETG_upper_g':float(m.volume*.00127),'bounds_mm':m.bounds.tolist(),'fixed_collisions':hits(mm,O),'component_collisions':hits(mm,[('openrb_actual',tri(actual),actual)]+components[1:])}
checks['cap_carrier_intersection_mm3']=float((cap^carrier).volume())
checks['components']={n:{'fixed_collisions':hits(mm,O),'other_new_collisions':hits(mm,components[:i])} for i,(n,m,mm) in enumerate(components)}
checks['discarded_disconnected_cutting_slugs_mm3']=discarded
checks['original_top_volume_mm3']=float(old.volume)
checks['print_transforms_assembly_to_print_mm']=poses
checks['print_file_readback']=print_readback
(OUT/'validation.json').write_text(json.dumps(checks,indent=2)+'\n')
(OUT/'frozen-sha256.json').write_text(json.dumps({r['file']:r['sha256'] for r in print_readback.values()},indent=2)+'\n')
# Editable feature solids as STEP; original curved source shell remains mesh.
# CadQuery compound preserves the individually editable construction blocks.
cq.exporters.export(cq.Compound.makeCompound(carrier_cq),str(OUT/'audio_carrier_construction.step'))
cq.exporters.export(cq.Compound.makeCompound([cqbox([20,0,-15],[44,84,96]),cqbox([15.4,0,-15],[50.8,81.6,93.6])]),str(OUT/'cap_construction.step'))
print(json.dumps(checks,indent=2))
