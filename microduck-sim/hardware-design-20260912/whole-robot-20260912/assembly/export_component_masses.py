from pathlib import Path
import json,trimesh
O=Path(__file__).parent/'compact-battery';old=trimesh.load(O/'original-power-support-body.stl');new=trimesh.load(O/'power-support-integrated-body.stl');cover=trimesh.load(O/'small-regulator-cover-body.stl');density=.00000124
parts=[]
for name,c,d,m in [('battery',[-37.6,0,-4],[22,34,63],.057),('servo_regulator',[-35.5,0,-48],[43.2,31.8,11],.019),('logic_regulator',[-4,0,17.5],[22.9,9.7,22.9],.0035)]:
 parts.append({'id':name,'body':'trunk_base','position_m':[x*.001 for x in c],'dimensions_m':[x*.001 for x in d],'rotation_wxyz':[1,0,0,0],'mass_kg':m,'accounting':'replacement_after_removal_original_battery_mass' if name=='battery' else 'add'})
for name,mult,mesh in [('integrated_support_add',1,new),('original_support_remove',-1,old),('small_cover_add',1,cover)]:
 parts.append({'id':name,'body':'trunk_base','position_m':(mesh.center_mass*.001).tolist(),'mass_kg':mesh.volume*density*mult,'inertia_about_com_kg_m2':(mesh.moment_inertia*density*1e-6*mult).tolist(),'accounting':'solid PLA 1.24 g/cm3 estimate; signed mass replacement, replace with slicing mass'})
(O/'component-body-masses.json').write_text(json.dumps({'parts':parts,'net_printed_delta_mass_kg':(new.volume-old.volume+cover.volume)*density,'small_cover_mass_kg':cover.volume*density,'warning':'Board envelopes exclude optional screw terminals. Direct soldered flying leads are assumed. Cable/fuse/switch/hardware allowances remain separate; original body inertial must not double-count battery.'},indent=2))
print('net printed delta',round((new.volume-old.volume+cover.volume)*density*1000,3),'g')
