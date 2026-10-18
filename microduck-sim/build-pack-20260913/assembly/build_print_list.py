from pathlib import Path
import json,collections,shutil,hashlib,trimesh
H=Path(__file__).resolve().parent
rows=json.loads((H/'community-print-inventory.json').read_text())['objects'];groups=collections.defaultdict(list)
for r in rows:groups[r['source_name']].append(r)
names={'3.obj':'Lower head shell','4.obj':'Moving jaw frame','5.obj':'Superseded cap','7.obj':'Left shell','8.obj':'Right shell','a.obj':'Superseded power support','b.obj':'Hip bracket','d.obj':'Neck link A','e.obj':'Neck link B','f.obj':'Thigh reinforcing plate A','g.obj':'Thigh reinforcing plate B','h.obj':'Superseded head motor support','i.obj':'Original PCB retaining strip','j.obj':'Neck U bracket','k.obj':'Lower-leg link A','l.obj':'Lower-leg link B','m.obj':'Torso base','n.obj':'Hip yaw/roll link A','o.obj':'Hip yaw/roll link B','p.obj':'Fixed upper lip pad','q.obj':'Moving lower lip pad','111.obj':'Community foot A, combined mesh','222.obj':'Community foot B, combined mesh','333.obj':'Eye outer ring','dfvdfb.obj':'Passive roll support','ersgtbgertgestrg.obj':'22 mm printed sliding ring','idle_horn.stl':'Printed passive idler','idle_cap.stl':'Printed idler cap','rgbn.obj':'14.6 mm printed ankle ring','grbrgn.obj':'Community right ankle','thngthm.obj':'Community left ankle','dfbdfbbbbb1.obj':'Head yaw/roll link','fgb.obj':'Right thigh','gbgb.obj':'Left thigh','ghmghmghmghm.obj':'Face panel and Pi mount'}
def sliced(name):
 d=json.loads((H/name/'slice-verification.json').read_text())['result']['sliced_plates'];g=sum(sum(f['total_used_g'] for f in x['filaments']) for x in d);sec=round(sum(x['total_predication'] for x in d));return len(d),g,f'{sec//3600} h {sec%3600//60:02d} min {sec%60:02d} s'
full=sliced('printing-full');current_stats=sliced('printing')
s=f'''# Print files and Bambu projects

This robot uses **15 total actuators, including one jaw actuator**. The print queue contains **64 retained source instances + 11 current parts + 14 additional idler/cap instances = 89 instances**. This is a print-stock count, not a claim that 89 parts are installed.

The source project contains 8 printed idlers and 6 caps. The full queue adds 6 idlers and 8 caps, giving **14 of each** as a maximum-one-pair-per-non-jaw-motor inventory allowance. The CAD identifies ten motor-coaxial large support-ring stations, but merges both motor-side flanges into the motor mesh. It does not establish the exact installed idler/cap count. Keep unused copies as explicit spares and record each installed pair on the first-article sheet.

Bambu Studio 2.7.1.62 predicts **{full[1]:.2f} g / {full[2]} across {full[0]} plates** for the complete queue. The eleven changed/new parts alone predict **{current_stats[1]:.2f} g / {current_stats[2]} across {current_stats[0]} plates**. These are slicer predictions, not completed prints.

- [Complete 89-instance project](printing-full/MicroDuck-complete-89-instances-X1C-CoolPlate.3mf)
- [Eleven current parts](printing/MicroDuck-current-11-parts-X1C-CoolPlate.3mf)
- [Source catalog 1](images/07-print-catalog-1.png), [catalog 2](images/07-print-catalog-2.png), [catalog 3](images/07-print-catalog-3.png)

Both projects embed **X1 Carbon, 0.4 mm nozzle, PLA, Cool Plate, 0.2 mm layers, four walls, 30% gyroid, automatic tree supports**. Match the real machine, nozzle and plate before printing. P1S/P1P/A1, another X1 plate, and A1 mini require correct profiles and fresh arrangement/slicing. Every individual part fits inside a 180 mm cube; this does not validate an A1 mini toolpath or support layout. RoboClub machine availability is not established by these files.

The community project used P1S, Textured PEI, PLA, two walls and 15% infill. The stronger current profile changes weight. Reweigh the assembled robot before claiming the old dynamic simulation applies.

## Eleven current parts: one of each

'''
descs=[('Integrated power support','Replaces a.obj / ID12. Retain the supplied orientation. Four 2 mm regulator spacers are integral; do not purchase separate spacers. Clear pocket and overhang supports.'),('Small-regulator cover','Flat face down. Keep original scale and thickness.'),('Jaw-clearance head cap','Replaces the former cap and source 5.obj / ID6. Use the registered orientation; clear cavity and hanging-post supports.'),('Audio carrier','Large plane down; clear short overhangs.'),('Camera tilt foot','Foot down; clear the side-ear holes.'),('Camera cradle','Retain the supplied rear-plane-down orientation; remove all lens-hole supports.'),('Torso IMU clamp','Retain the supplied side-down orientation; clean the jaws and vents.'),('IMU rear cover','Large plane down; deburr holes.'),('Eleven-fuse carrier','Base down. Clear the 6.5 mm-high lower tier through both open ends with a fine tool.'),('Voltage-alarm and EN-switch carrier','Rear mounting plane down. Clear header window, tie slots, switch saddle and terminal opening.'),('Coaxial jaw motor support','Replaces h.obj / ID24. Integral fixed sliding bushing, 10.4 mm bore centered on the jaw axis; no separate mouth bearing. Retain the source-derived orientation and clear the bore without enlarging it blindly.')]
manifest=[];release=H/'print-parts/current';release.mkdir(exist_ok=True)
current=json.loads((H/'printing/slice-verification.json').read_text())['parts'];assert len(current)==len(descs)==11
for i,(r,(title,desc)) in enumerate(zip(current,descs),1):
 p=Path(r['path']);target=release/p.name;shutil.copy2(p,target);m=trimesh.load(p,force='mesh');dim=' x '.join(f'{x:.1f}' for x in m.extents)
 s+=f'{i}. **{title} / PLA x 1** — {dim} mm. {desc}\n\n   [{p.name}](print-parts/current/{p.name})\n\n'
 manifest.append({'name':title,'quantity':1,'file':str(target.relative_to(H)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'material':'PLA','extent_mm':m.extents.tolist(),'count_basis':'current installation design','orientation':'Provided STL and sliced 3MF; do not auto-orient blindly'})
s+='''## Retained source parts

Dimensions use exported print orientation. Each link is the first instance; the complete 3MF includes repeated instances. All retained parts use PLA and the source orientation. This route uses the community printed sliding supports; do not also purchase the official metal-bearing route.

The source calls p/q soft pads but assigns PLA. A later TPU pad experiment must change only those pads and validate attachment and clearance. Do not change the load-bearing jaw frame or complete combined foot to TPU without a separate design check. PLA foot traction has not been physically measured.

'''
for name,rs in groups.items():
 r=rs[0];dims=' x '.join(f'{v:.1f}' for v in r['print_extent_mm']);ids=', '.join(str(x['id']) for x in rs)
 if r['id'] in [6,12,24]:s+=f'- **Do not print source {name} / ID{r["id"]}.** Replaced by a current file above.\n\n';continue
 extra=14-len(rs) if name in ['idle_horn.stl','idle_cap.stl'] else 0
 s+=f'- **{names.get(name,name)} / {name}: source quantity {len(rs)}'+(f', plus {extra} inventory copies' if extra else '')+f' / PLA.** {dims} mm; source IDs {ids}. Retain orientation and generated supports. [STL](print-parts/community-{r["id"]}.stl)\n\n'
 for x in rs+[r]*extra:manifest.append({'name':names.get(name,name),'source_name':name,'source_id':x['id'],'quantity':1,'file':f'print-parts/community-{x["id"]}.stl','sha256':hashlib.sha256(Path(x['print_file']).read_bytes()).hexdigest(),'material':'PLA','extent_mm':x['print_extent_mm'],'orientation':'Retained source rotation; centered and grounded','count_basis':'source inventory / explicit allowance; installed count not inferred'})
s+='''## Fixed hardware quantities for the added electronics and mounts

- M2 x 5 machine screws: 2, IMU clamp.
- M2 x 8 machine screws: 8, camera 4 and rear IMU/alarm assembly 4.
- M2 x 12 machine screws: 4, small-regulator cover.
- M2 x 18 machine screws: 4, OpenRB.
- M2 x 20 machine screws: 4, large regulator and fuse carrier; replace the old M2 x 8.
- M2 x 25 machine screws: 2, audio carrier.
- M2 nuts: 14: camera 4, OpenRB 4, audio 2, large regulator 4.
- M2.5 x 6 tapping screws: 4, Pi to face panel, no nuts; head envelope at most diameter 4.5 x 1.8 mm.
- M3 x 10 screws: 2, camera foot. M3 x 20: 1, tilt hinge.
- M3 nuts: 3. M3 washers: 4, each 0.5 mm thick.

Head M2 pan-head envelopes were checked at diameter 4 x 1.72 mm. Keep long electronics screws away from servo-case holes.

Battery retention: two Panduit PLT3S-C ties, 292 x 4.8 x 1.3 mm; trim tails and keep locks rearward. Fuse carrier: four PLT2M-C ties, 203 x 2.5 x 1.1 mm, in 2.8 x 1.6 mm slots. The lower tier is lowered 0.5 mm to leave 1.5 mm between the upper tray and lower fuse envelopes.

Short PLT.6SM-C ties, 71 x 1.8 x 0.8 mm: audio four loops of two joined ties (8), alarm two loops of three joined ties (6), EN switch one tie (1), total 15 short ties. The audio/alarm slots require the narrower width. Joined locks are physical first-article clearance checks, not verified flexible geometry. Do not substitute the 2.5 mm fuse tie through the narrow audio/alarm slots.

Battery padding needs no adhesive for retention; use closed-cell material with finished thickness at most 1 mm. If using double-coated 3M4492W, retain its battery-facing liner and measure the finished stack.

## Servo fasteners and inventory limits

Fifteen XL330 packages provide **90 M2 x 6 TAP and 150 M2 x 8 TAP** screws. The numerical inventory covers four output screws per motor (60) and up to eight case screws per motor (120). These are inventory ceilings, not a per-hole screw-length approval. Use **M2 x 6 TAP through a 3 mm output frame**: ROBOTIS warns that M2 x 8 in that location reaches the case and can damage the motor.

Each separately installed passive idler/cap uses **one M2.6 x 6 TAP center screw**, which is absent from the single-motor package. Do not substitute M2.5 or M2.6 machine screws. Source matching screws from RoboClub first; no screw-kit purchase is selected. The former two-pack FPX330-H101 option is a reference for sixteen factory screws only. If club stock lacks the required thread, length and head geometry, record that exact gap before changing the sourcing decision. Do not buy extra HNX active-output horns: this design uses the integrated XL330 output.

[ROBOTIS integrated output and idler assembly](https://emanual.robotis.com/assets/images/dxl/x/x330/xl330_assembly_integrated.png) and [output screw-length warning](https://emanual.robotis.com/assets/images/dxl/x/x330/x330_horn_screw.png), checked 2026-09-13.
'''
(H/'PRINT-LIST.md').write_text(s);(H/'print-manifest.json').write_text(json.dumps({'instances':manifest,'count':len(manifest),'current_parts':11,'retained_source_instances':64,'extra_inventory_instances':14,'source':'frozen local sources, no upstream fetch'},indent=2));assert len(manifest)==89;print('print manifest',len(manifest))
