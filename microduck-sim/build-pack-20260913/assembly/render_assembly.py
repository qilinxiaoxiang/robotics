"""Render actual frozen STL/CAD meshes with VTK; draw readable numbered callouts."""
from pathlib import Path
import sys,json,math
import numpy as np,trimesh,vtk
from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent;SIM=HERE.parents[1]
OLD=SIM/'hardware-design-20260912/whole-robot-20260912'
sys.path.insert(0,str(OLD/'assembly'))
from assembly_fk import fk,raw,world_meshes
FONTPATH='/System/Library/Fonts/PingFang.ttc'
if not Path(FONTPATH).exists():FONTPATH='/System/Library/Fonts/STHeiti Medium.ttc'
def font(size):return ImageFont.truetype(FONTPATH,size)
WHITE='#f8fafc';INK='#132b43';MUTED='#50647b'
COLORS={'print':'#e3e9ed','motor':'#245070','battery':'#edb441','camera':'#21987b','board':'#3684bd','amp':'#955a9f','speaker':'#303f4e','new':'#e68d38','imu':'#19a3a4','metal':'#929aa3'}
def rgb(s):return tuple(int(s[i:i+2],16)/255 for i in (1,3,5))
def item(name,mesh,color=COLORS['print'],alpha=1):return {'name':name,'mesh':mesh,'color':color,'alpha':alpha}
def actor(part):
 m=part['mesh'];data=vtk.vtkPolyData();points=vtk.vtkPoints();points.SetData(numpy_to_vtk(np.ascontiguousarray(m.vertices),deep=True));data.SetPoints(points)
 faces=np.column_stack([np.full(len(m.faces),3),m.faces]).astype(np.int64).ravel();cells=vtk.vtkCellArray();cells.SetCells(len(m.faces),numpy_to_vtkIdTypeArray(faces,deep=True));data.SetPolys(cells)
 normals=vtk.vtkPolyDataNormals();normals.SetInputData(data);normals.SetFeatureAngle(35);normals.Update()
 mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort());a=vtk.vtkActor();a.SetMapper(mapper)
 p=a.GetProperty();p.SetColor(*rgb(part['color']));p.SetOpacity(part['alpha']);p.SetAmbient(.3);p.SetDiffuse(.65);p.SetSpecular(.15);p.SetSpecularPower(25)
 return a
def render(parts,path,size=(1600,1400),direction=(1.35,-1.5,.9),focus=None,scale=None):
 ren=vtk.vtkRenderer();ren.SetBackground(*rgb(WHITE));win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetMultiSamples(8);win.AddRenderer(ren);win.SetSize(*size)
 for part in parts:ren.AddActor(actor(part))
 bounds=np.array([p['mesh'].bounds for p in parts]);low=bounds[:,0,:].min(0);high=bounds[:,1,:].max(0);center=(low+high)/2 if focus is None else np.array(focus)
 cam=ren.GetActiveCamera();cam.SetFocalPoint(*center);cam.SetPosition(*(center+np.array(direction)*max(high-low)*3));cam.SetViewUp(0,0,1);cam.ParallelProjectionOn()
 ren.ResetCamera();cam.SetFocalPoint(*center);cam.SetPosition(*(center+np.array(direction)*max(high-low)*3));cam.SetViewUp(0,0,1)
 if scale:cam.SetParallelScale(scale)
 else:cam.SetParallelScale(cam.GetParallelScale()*1.07)
 ren.ResetCameraClippingRange();win.Render()
 cap=vtk.vtkWindowToImageFilter();cap.SetInput(win);cap.Update();png=vtk.vtkPNGWriter();png.SetFileName(str(path));png.SetInputConnection(cap.GetOutputPort());png.Write()
 def project(p):
  ren.SetWorldPoint(*p,1);ren.WorldToDisplay();q=ren.GetDisplayPoint();return (q[0],size[1]-q[1])
 positions={p['name']:project(p['mesh'].centroid) for p in parts};win.Finalize();return positions
def wrap(draw,text,maxwidth,ft):
 lines=[];line=''
 for word in text.split():
  candidate=(line+' '+word).strip()
  if line and draw.textlength(candidate,font=ft)>maxwidth:lines.append(line);line=word
  else:line=candidate
 if line:lines.append(line)
 return lines
def panel(filename,title,subtitle,parts,labels,direction=(1.35,-1.5,.9),focus=None,scale=None):
 path=HERE/'images'/filename;rawpath=path.with_name(path.stem+'-geometry.png');pos=render(parts,rawpath,direction=direction,focus=focus,scale=scale)
 im=Image.new('RGB',(2400,1700),WHITE);im.paste(Image.open(rawpath).convert('RGB'),(15,205));d=ImageDraw.Draw(im)
 d.text((85,42),title,font=font(50),fill=INK);d.text((65,114),subtitle,font=font(25),fill=MUTED)
 d.line((65,176,2335,176),fill='#d7e1ea',width=3);y=225;markers=[]
 for i,(name,title,desc) in enumerate(labels,1):
  col=next((p['color'] for p in parts if p['name']==name),COLORS['new'])
  if sum(a*b for a,b in zip(rgb(col),[.2126,.7152,.0722]))>.55:col=COLORS['motor']
  x0=1675;d.ellipse((x0,y,x0+48,y+48),fill=col);d.text((x0+24,y+23),str(i),font=font(27),anchor='mm',fill='white')
  d.text((x0+70,y+1),title,font=font(28),fill=INK)
  lines=wrap(d,desc,565,font(24))
  for j,line in enumerate(lines):d.text((x0+70,y+52+j*34),line,font=font(24),fill=MUTED)
  y+=max(132,82+len(lines)*34)
  if name in pos:
   x,qy=pos[name];x+=15;qy+=205;px,py=x,qy
   for ax,ay in markers:
    if ((x-ax)**2+(qy-ay)**2)**.5<56:x=ax+58
   markers.append((x,qy));d.line((px,py,x,qy),fill=col,width=3)
   d.ellipse((x-22,qy-22,x+22,qy+22),fill=col,outline='white',width=3);d.text((x,qy),str(i),font=font(26),anchor='mm',fill='white')
 d.text((65,1640),'Source CAD geometry | Dimensions in mm | Numbered parts match the right-hand notes | Digital checks, not physical assembly',font=font(24),fill=MUTED)
 im.save(path);return path

def world_final():
 b,gs=fk();H=OLD/'electrical/head-layout/final';C=OLD/'assembly/compact-battery';I=OLD/'assembly/trunk-imu'
 removed={'np_f970','power_support','top_head_shell','elec_rpi_robot_hat_pcb','speaker','lens','m12_lens_holder'};parts=[]
 for g,m in world_meshes():
  if g['mesh'] in removed or (g['body']=='jaw_soft' and g['mesh']=='seeed_bearing__configuration_default'):continue
  if g['body']=='jaw_soft' and g['mesh']=='motor_support':m=trimesh.load(HERE/'mouth-support/motor-support-coaxial-assembly.stl',force='mesh').apply_transform(b['jaw_soft'])
  name='pi' if g['mesh']=='pcb__raspberry_pi_zero_2_w' else f"{g['body']}:{g['mesh']}:{g['index']}"
  color=COLORS['camera'] if g['mesh']=='pcb__raspberry_pi_zero_2_w' else COLORS['motor'] if g['mesh']=='xl330' else COLORS['metal'] if 'bearing__' in g['mesh'] else '#efbb5f' if g['mesh'] in ['jaw','face_part','noenoeil','foot_left','foot_right','ankle_left','ankle_right'] else COLORS['print']
  p=item(name,m,color);p.update(body=g['body'],source_mesh=g['mesh'],index=g['index']);parts.append(p)
 for p in json.loads((H/'head-mesh-mass-manifest.json').read_text())['pieces']:
  if p['id']=='pi_retained':continue
  m=trimesh.load(HERE/'mouth-clearance/head-cap-mouth-clearance-assembly.stl' if p['id']=='head_cap' else p['mesh_file'],force='mesh').apply_transform(b['jaw_soft'])
  color=COLORS['new'] if p['id'] in ['head_cap','audio_carrier','camera_pitch_foot','camera_cradle'] else COLORS['camera'] if 'camera' in p['id'] else COLORS['board'] if p['id']=='openrb' else COLORS.get(p['id'],COLORS['metal'])
  x=item(p['id'],m,color);x.update(body='jaw_soft',source_mesh=p['id']);parts.append(x)
 for n,c in [('power-support-integrated-body',COLORS['new']),('battery-max-envelope-body',COLORS['battery']),('large_regulator-envelope-body',COLORS['board']),('small_regulator-envelope-body',COLORS['amp']),('small-regulator-cover-body',COLORS['new']),('two-retention-ties-envelope','#313c49')]:
  x=item(n,trimesh.load(C/(n+'.stl'),force='mesh'),c);x.update(body='trunk_base',source_mesh=n);parts.append(x)
 for n,c in [('imu_clamp_holder_body',COLORS['imu']),('imu_rear_cover_body',COLORS['imu']),('imu_28x25x8_envelope_body',COLORS['amp'])]:
  x=item(n,trimesh.load(I/(n+'.stl'),force='mesh'),c);x.update(body='trunk_base',source_mesh=n);parts.append(x)
 S=HERE/'service-mounts'
 for p in sorted(S.glob('*-body.stl'))+sorted(S.glob('*-envelope.stl')):
  color='#138e9b' if 'tie-' in p.name else COLORS['motor'] if 'en-switch' in p.name else COLORS['battery'] if 'fuse-' in p.name and 'envelope' in p.name else COLORS['amp'] if 'alarm-envelope' in p.name else COLORS['new']
  x=item(p.stem,trimesh.load(p,force='mesh'),color);x.update(body='trunk_base',source_mesh=p.stem);parts.append(x)
 return parts
def select(parts,predicate):return [dict(p,mesh=p['mesh'].copy()) for p in parts if predicate(p)]
def shift(parts,v):
 for p in parts:p['mesh'].apply_translation(v)
 return parts

def main():
 parts=world_final()
 # Whole robot, matching source dimensions and orientation.
 panel('01-overall.png','01  Whole-robot component locations','The robot faces right. Component colors match the detail views.',parts,[
 ('camera_module3_wide','Monocular camera','Camera Module 3 Wide on the new cap, with a printed foot and tilt cradle.'),
 ('head_cap','Head electronics','OpenRB, amplifier and speaker sit inside the new cap. Pi keeps its original face-panel mount.'),
 ('power-support-integrated-body','Integrated power mount','Replaces source a.obj and retains the battery plus both regulators.'),
 ('imu_clamp_holder_body','Body orientation sensor','BNO085 is mounted rigidly to the torso, so it measures torso orientation.'),
 ('upper_leg_left:xl330:1','15 total, including one jaw actuator','Five per leg, four in the head/neck, one in the jaw. See the ID map.')],direction=(-1.3,-1.5,.65))
 # Spatial disassembly by existing rigid-body groups.
 explode=[]
 for p in parts:
  q=dict(p,mesh=p['mesh'].copy());body=p['body']
  if body=='jaw_soft':v=[0,0,125]
  elif body in ['neck','neck_pitch','yaw_roll_motion']:v=[0,0,50]
  elif body in ['yaw2roll','hip_l','upper_leg_left','leg','ankle_left']:v=[0,68,-15]
  elif body in ['bearing_roll','hip_l_2','upper_leg_right','leg_2','ankle_right']:v=[0,-68,-15]
  else:v=[0,0,0]
  q['mesh'].apply_translation(v);explode.append(q)
 panel('02-exploded.png','02  Assemble the modules','Exploded offsets show the sequence; the assembled view shows final locations.',explode,[
 ('power-support-integrated-body','Build the power module first','Install the small regulator in the central pocket before adjacent hip motors.'),
 ('upper_leg_left:xl330:1','Left leg','Assemble ID 10 to 6. Set each ID and center the shaft before fastening the output frame.'),
 ('upper_leg_right:xl330:0','Right leg','Assemble ID 5 to 1 using the mirrored parts.'),
 ('neck:xl330:1','Neck','Install IDs 12, 11, 13 and 14, then the jaw motor inside the head.'),
 ('head_cap','Head electronics and camera','Connect the camera ribbon, USB and audio wiring before closing the cap.')],direction=(1.5,-1.8,.7))
 head=select(parts,lambda p:p['body']=='jaw_soft' and p['source_mesh'] not in ['head_cap','face_part','jaw','bottom_head_shell','noenoeil','head_fasteners'])
 panel('03-head-internal.png','03  Wire the head before closing it','Cap, face and lower shell are hidden to expose the internal installation.',head,[
 ('openrb','OpenRB-150','Supplier STEP geometry; four M2 x 18 screws and M2 nuts attach it to the cap posts.'),
 ('pi','Pi Zero envelope; board unconfirmed','Pi 3 or first-generation Zero options. These four M2.5 x 6 seats model the Zero envelope only; Pi 3 mounting and power are unverified.'),
 ('amp','MAX98357A amplifier','Purple installation envelope. Retain with the cradle, insulation pad and narrow ties.'),
 ('speaker','8-ohm / 1 W speaker','Dark installation envelope. Secure the rim and keep ties clear of the diaphragm.'),
 ('audio_carrier','Audio carrier','Two M2 x 25 screws and M2 nuts. Fit the amplifier and speaker to this carrier first.'),
 ('camera_module3_wide','Camera and cradle','Route the ribbon through the cap slot. Use M3 x 10 screws for the mounting foot.')],direction=(1.2,-1.4,1.1))
 power=select(parts,lambda p:p['source_mesh'] in ['power-support-integrated-body','battery-max-envelope-body','large_regulator-envelope-body','small_regulator-envelope-body','small-regulator-cover-body','two-retention-ties-envelope','imu_clamp_holder_body','imu_rear_cover_body','imu_28x25x8_envelope_body'])
 panel('04-power-installed.png','04  Battery, regulators and torso IMU','Actual printed geometry; rectangular electronics show dimensioned installation envelopes.',power,[
 ('battery-max-envelope-body','Maximum battery envelope','22 x 34 x 63 mm. Unplug EC2, then release or replace the two ties to remove the battery.'),
 ('two-retention-ties-envelope','Two battery ties','4.8 mm wide, at least 200 mm long; locks face rearward. Stops and ties carry the load.'),
 ('large_regulator-envelope-body','Servo 5 V regulator','D42V110F5 below the battery; four M2 x 20 screws share the fuse-carrier mounting holes.'),
 ('small_regulator-envelope-body','Logic 5 V regulator','S13V30F5 between the hip motors. Solder its leads before fitting the cover.'),
 ('imu_clamp_holder_body','Removable IMU clamp','Two M2 x 5 clamp screws; four M2 x 8 screws retain the rear cover and alarm carrier.')],direction=(-1.5,-1.3,.75))
 exp=select(power,lambda p:True)
 moves={'battery-max-envelope-body':[-65,0,0],'two-retention-ties-envelope':[-65,0,0],'large_regulator-envelope-body':[0,0,-38],'small-regulator-cover-body':[35,0,0],'imu_clamp_holder_body':[-25,0,43],'imu_rear_cover_body':[-45,0,43],'imu_28x25x8_envelope_body':[-35,0,43]}
 for p in exp:p['mesh'].apply_translation(moves.get(p['name'],[0,0,0]))
 panel('05-power-exploded.png','05  Power-module assembly order','Exploded positions show the order. Disconnect the battery before assembly or removal.',exp,[
 ('small_regulator-envelope-body','1  Small regulator','Solder and insulate flying leads before insertion. Optional screw terminals do not fit this pocket.'),
 ('small-regulator-cover-body','2  Small-regulator cover','Four M2 x 12 screws into plastic pilot holes. Tighten by hand without splitting the posts.'),
 ('large_regulator-envelope-body','3  Large regulator','Connect input/output leads and align the four integral spacers. Preserve the air gap.'),
 ('battery-max-envelope-body','4  Battery and ties','Insert from the rear. Pad the wrap and let the printed stops carry structural loads.'),
 ('imu_clamp_holder_body','5  IMU clamp','Clamp onto the printed corner rails and route sensor leads through the vent.')],direction=(-1.5,-1.5,.8))
 service=select(parts,lambda p:p['source_mesh'] in ['power-support-integrated-body','large_regulator-envelope-body','imu_clamp_holder_body','imu_rear_cover_body'] or p['name'].startswith('fuse-') or p['name'].startswith('voltage-alarm') or p['name'].startswith('en-switch'))
 panel('08-service-mounts.png','08  Removable fuse and alarm carriers','Actual carrier geometry. Yellow boxes reserve 24 x 5 x 5 mm per insulated fuse assembly.',service,[
 ('fuse-bank-body','Eleven-fuse carrier','Six upper and five lower positions; 42.6 mm wide. Uses the four regulator holes.'),
 ('large_regulator-envelope-body','Shared mounting holes','Four M2 x 20 replace the former M2 x 8 screws; nuts stay the same. Load the lower tier first.'),
 ('voltage-alarm-carrier-body','Voltage-alarm carrier','Fits outside the IMU cover. Four M2 x 8 replace the former M2 x 6 screws.'),
 ('voltage-alarm-envelope','38 x 25 x 11 mm alarm','Two narrow ties secure the frame. Face the header toward the side opening; reserve 12 mm for the plug plus 10 mm for bending.'),
 ('en-switch-body-envelope','Servo-enable switch','Fits the saddle above the alarm. One narrow tie retains the metal rim; keep the slider free. See Figure 13.')],direction=(-1.7,-1.5,-.15))
 # 15 numbered motor identities, isolated from outer shells.
 motor_ids={('trunk_base',4):10,('trunk_base',9):5,('yaw2roll',1):9,('upper_leg_left',1):7,('upper_leg_left',4):8,('leg',2):6,('neck',1):12,('neck',2):11,('yaw_roll_motion',1):13,('jaw_soft',2):15,('jaw_soft',7):14,('bearing_roll',1):4,('upper_leg_right',0):2,('upper_leg_right',4):3,('leg_2',0):1}
 motorparts=select(parts,lambda p:p['source_mesh']=='xl330')
 for p in motorparts:p['name']='ID '+str(motor_ids[(p['body'],p['index'])])
 rawpath=HERE/'images/06-servo-map-geometry.png';pos=render(motorparts,rawpath,size=(1550,1410),direction=(1.25,-2,.45))
 im=Image.new('RGB',(2400,1700),WHITE);im.paste(Image.open(rawpath),(20,230));d=ImageDraw.Draw(im);d.text((65,80),'06  15 total, including one jaw actuator',font=font(50),fill=INK);d.text((65,158),'Shells and links are hidden. Numbers are device IDs; left/right follow the robot.',font=font(26),fill=MUTED)
 placed=[]
 for name,(x,y) in sorted(pos.items(),key=lambda kv:kv[1][1]):
  x+=20;y+=230
  px,py=x,y
  for ax,ay in placed:
   if ((x-ax)**2+(y-ay)**2)**.5<61:y=ay+61
  placed.append((x,y));d.line((px,py,x,y),fill=COLORS['motor'],width=3)
  d.ellipse((x-25,y-25,x+25,y+25),fill=COLORS['motor'],outline='white',width=3);d.text((x,y),name[3:],font=font(26),fill='white',anchor='mm')
 y=250
 for title,txt in [('Right leg：ID 1–5','1 ankle / 2 knee / 3 hip pitch\n4 hip roll / 5 hip yaw'),('Left leg：ID 6–10','6 ankle / 7 knee / 8 hip pitch\n9 hip roll / 10 hip yaw'),('Neck/head: IDs 11-14','11 head pitch / 12 neck pitch\n13 head yaw / 14 head roll'),('Jaw: ID 15','Mount and sliding seat are present.\nThe walking policy does not drive it.\nCalibrate its limits separately.')]:
  d.text((1660,y),title,font=font(35),fill=INK);y+=65
  for line in txt.split('\n'):d.text((1660,y),line,font=font(29),fill=MUTED);y+=46
  y+=55
 d.text((65,1637),'Set IDs and center shafts individually before fastening output frames. Model zero, encoder center and standing posture need separate calibration.',font=font(25),fill=MUTED);im.save(HERE/'images/06-servo-map.png')
 # Reference print catalog uses actual extracted build orientation; repeated objects grouped by name.
 rows=json.loads((HERE/'community-print-inventory.json').read_text())['objects'];groups={}
 for row in rows:groups.setdefault(row['source_name'],[]).append(row)
 groups=list(groups.values())
 for page,start in enumerate(range(0,len(groups),12),1):
  im=Image.new('RGB',(2400,1800),WHITE);d=ImageDraw.Draw(im);d.text((65,40),f'Source print catalog {page} / {math.ceil(len(groups)/12)}',font=font(50),fill=INK);d.text((65,112),'Original 3MF object IDs are retained. Multiplicities are source-project quantities and may include spares.',font=font(25),fill=MUTED)
  for j,gr in enumerate(groups[start:start+12]):
   row=gr[0];x=55+(j%4)*585;y=185+(j//4)*520
   p=Path(row['print_file']);m=trimesh.load(p,force='mesh');rp=HERE/'images'/f'part-{row["id"]}.png';render([item(str(row['id']),m,COLORS['new'])],rp,size=(520,350),direction=(1.2,-1.4,.9))
   im.paste(Image.open(rp),(x,y));d.text((x+10,y+355),f'ID {row["id"]} · {row["source_name"]} ×{len(gr)}',font=font(25),fill=INK)
   dims=' × '.join(f'{v:.1f}' for v in row['print_extent_mm']);d.text((x+10,y+400),dims+' mm',font=font(23),fill=MUTED)
   if row['id'] in [6,12,24]:d.text((x+10,y+442),'Replaced: print the current file',font=font(24),fill='#b45528')
  im.save(HERE/'images'/f'07-print-catalog-{page}.png')
 print('Rendered assembly and complete source catalog',flush=True)
if __name__=='__main__':main()
