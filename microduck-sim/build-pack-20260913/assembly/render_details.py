from render_assembly import *
from scipy.spatial.transform import Rotation
P=world_final()
# Left-leg component layers in actual component geometry.
left=select(P,lambda p:p['body'] in ['yaw2roll','hip_l','upper_leg_left','leg','ankle_left'])
for p in left:
 if p['body']=='yaw2roll':p['mesh'].apply_translation([0,0,40])
 elif p['body']=='hip_l':p['mesh'].apply_translation([0,0,20])
 elif p['body']=='leg':p['mesh'].apply_translation([0,0,-25])
 elif p['body']=='ankle_left':p['mesh'].apply_translation([0,0,-55])
labels=[]
for key,title,desc in [('yaw2roll','Hip yaw/roll link','n/o.obj link the horizontal torso motor to the roll motor. Align axes before fastening.'),('hip_l','Hip bracket','Two b.obj brackets. Attach the moving link to the output and the adjacent stationary link to the motor case.'),('upper_leg_left','Thigh and two motors','gbgb.obj and reinforcing plate g.obj. ID 8 is hip pitch; ID 7 is knee pitch.'),('leg','Lower-leg links','k/l.obj. Align the support/idler axes and confirm free rotation after tightening.'),('ankle_left','Ankle and foot','Retain the matched community ankle/foot pair. Fit the foot after checking each joint.')]:
 p=next(x for x in left if x['body']==key and x['source_mesh']!='xl330');labels.append((p['name'],title,desc))
panel('09-leg-detail.png','09  Assemble one leg','Actual left-leg parts, separated vertically. Mirror the sequence for the right leg.',left,labels,direction=(1.5,-1.2,.4))
# Conditional jaw animation endpoints rendered as real geometry, with cap section transparent.
head=[]
for g in fk()[1]:
 if g['body']=='jaw_soft' and g['mesh'] in ['xl330','motor_support','jaw','jaw_soft','soft_mouth_top']:
  if g['mesh']=='xl330' and g['index']!=2:continue
  m=trimesh.load(HERE/'mouth-support/motor-support-coaxial-assembly.stl',force='mesh') if g['mesh']=='motor_support' else raw(g['mesh']).apply_transform(g['local'])
  head.append(item(g['mesh'],m,COLORS['motor'] if g['mesh']=='xl330' else COLORS['battery'] if g['mesh'] in ['jaw','jaw_soft'] else COLORS['print']))
cap=trimesh.load(HERE/'mouth-clearance/head-cap-mouth-clearance-assembly.stl',force='mesh');head.append(item('head-cap-trimmed',cap,COLORS['new'],.22))
im=Image.new('RGB',(2400,1600),WHITE);d=ImageDraw.Draw(im);d.text((65,42),'10  Jaw actuator: the fifteenth motor',font=font(50),fill=INK);d.text((65,116),'The yellow jaw and lower pad rotate. The gray upper pad remains fixed. The new support contains the sliding seat.',font=font(27),fill=MUTED)
pivot=np.array([3.0,0,-18])
for i,deg in enumerate([0,30]):
 parts=select(head,lambda p:True);R=Rotation.from_euler('y',deg,degrees=True).as_matrix();T=np.eye(4);T[:3,:3]=R;T[:3,3]=pivot-R@pivot
 for p in parts:
  if p['name'] in ['jaw','jaw_soft']:p['mesh'].apply_transform(T)
 out=HERE/'images'/f'mouth-{deg}.png';render(parts,out,size=(1130,1000),direction=(-1.5,-1.2,-.55));im.paste(Image.open(out),(65+i*1160,215));d.text((170+i*1160,1230),f'Checked pose: {deg}°',font=font(37),fill=INK)
d.text((65,1360),'61 poses from 0 to 30 degrees are clear at 0.5-degree intervals about the measured X3.0 / Z-18 axis.',font=font(27),fill=MUTED)
d.text((65,1418),'The new integral seat removes the source overlap. Physical fit, shaft calibration, grip force and software actuation remain separate checks.',font=font(24),fill=MUTED);im.save(HERE/'images/10-mouth-detail.png')
# Lower fuses slide axially through open ends; show partly inserted bundle to expose channels.
S=HERE/'service-mounts';parts=[item('fuse-bank',trimesh.load(S/'fuse-bank-body.stl'),COLORS['new'])]
for i,p in enumerate(sorted(S.glob('fuse-[0-9][0-9]-envelope.stl'))):
 m=trimesh.load(p);m.apply_translation([-22 if i>=6 else 14,0,0]);parts.append(item(p.stem,m,COLORS['battery']))
panel('11-fuse-loading.png','11  Load the fuse carrier','Yellow boxes are insulated fuse-assembly envelopes, not printed parts. They are pulled out axially for this view.',parts,[
 ('fuse-bank','Remove internal supports','The lower tier is 6.5 mm high. Clear supports through the open ends and remove wire-snagging burrs.'),
 ('fuse-07-envelope','Load the lower five first','Solder and insulate first, then slide each assembly in from an open end.'),
 ('fuse-01-envelope','Then load the upper six','Each envelope is 24 x 5 x 5 mm; channel width is 5.4 mm. Measure the insulated assemblies first.'),
 ('fuse-bank','Tie the insulated lead sections','Thread the 2.5 mm fuse ties through the end slots. Retain insulated leads, keep off fuse bodies, and preserve labels.')],direction=(-1.3,-1.6,1.0))

# Supplier-dimension recognition model; not a picture of a received component.
T=np.eye(4);T[:3,:3]=[[0,0,1],[0,1,0],[-1,0,0]]
fuse=trimesh.creation.cylinder(radius=3.18/2,height=7.11,sections=64,transform=T)
lead=trimesh.creation.cylinder(radius=.32,height=26,sections=24,transform=T)
fusepic=HERE/'images/fuse-recognition.png';render([item('lead',lead,'#a5afb9'),item('fuse',fuse,'#2c9b76')],fusepic,size=(650,240),direction=(.5,-1.4,1.0))
im=Image.open(HERE/'images/11-fuse-loading.png').convert('RGB');im.paste(Image.open(fusepic),(1640,1190));d=ImageDraw.Draw(im);d.text((1665,1140),'Identify the axial fuse and leads',font=font(29),fill=INK);d.text((1665,1460),'Body: 7.11 mm long, up to 3.18 mm diameter',font=font(23),fill=MUTED);d.text((1665,1500),'Supplier dimensions; lead length and color are illustrative',font=font(23),fill=MUTED);im.save(HERE/'images/11-fuse-loading.png')
# All four tie loops; transparent body exposes the slots instead of hiding the route.
parts=[item('carrier',trimesh.load(S/'fuse-bank-body.stl'),COLORS['new'],.3)]
for i in range(1,5):parts.append(item('tie'+str(i),trimesh.load(S/f'fuse-tie-{i}-envelope.stl'),'#138e9b'))
panel('12-fuse-ties.png','12  Route the four fuse-retaining ties','Underside view. The transparent carrier exposes four paths for PLT2M-C ties, 2.5 mm wide and 1.1 mm thick.',parts,[
 ('tie3','First lower tie','Thread through the bottom slots before loading fuses. Tie around insulated leads, clear of the fuse body.'),
 ('tie4','Second lower tie','Parallel to the first tie, retaining the other end. Keep the lock outside the open end.'),
 ('tie1','First upper tie','Wrap the leads of the upper six. Upper and lower tie paths are offset.'),
 ('tie2','Second upper tie','Tighten gently after checking for sharp edges. Verify the actual tie-lock clearance separately.')],direction=(-1.3,-1.6,-1.0))

# Switch saddle, lead clearance and an edge strap, actual new bracket geometry.
parts=[item('alarm-holder',trimesh.load(S/'voltage-alarm-carrier-body.stl'),COLORS['new'],.38),item('alarm',trimesh.load(S/'voltage-alarm-envelope.stl'),COLORS['amp'],.25)]
for n,c in [('en-switch-body-envelope',COLORS['metal']),('en-switch-actuator-envelope',COLORS['motor']),('en-switch-terminal-envelope','#d09e48'),('en-switch-tie-envelope','#138e9b')]:parts.append(item(n,trimesh.load(S/(n+'.stl')),c,.4 if 'terminal' in n else 1))
panel('13-en-switch.png','13  Mount the servo-enable switch','The saddle projects above the alarm carrier. Transparency reveals the tie slots and terminal opening.',parts,[
 ('en-switch-body-envelope','Solder the two EN leads first','Pololu 1408 body: 8.5 x 3.7 x 3.5 mm. Use the center and one outer terminal; see the wiring page.'),
 ('en-switch-terminal-envelope','Route terminals through the base','Insulated terminals must fit 2.4 x 6.8 x 11.5 mm. Measure and trim; supplier pin length is not specified.'),
 ('en-switch-tie-envelope','One narrow tie on the metal rim','Thread the saddle slots and retain the outer metal edge. Keep clear of the slider and soldered terminals.'),
 ('en-switch-actuator-envelope','Check both slider positions','Dark blue shows the full actuator envelope. The secured switch must move freely to both positions.'),
 ('alarm-holder','This disables only servo power','Pi and the alarm remain powered. Unplug EC2 and then the alarm balance lead for complete shutdown.')],direction=(-1.6,-1.2,1.3))
