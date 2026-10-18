"""Separate plastic strip from pins; never fill the inter-pin air as plastic."""
from pathlib import Path
import os,json,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(Path(__file__));O=D/'fixed-pose-local-bend'
pose=json.loads(read(D/'positive-x225-pose.json'));T=np.array(pose['worldTransform']);ob=load(D/'positive-x225/head_bottom_x225_receiver-world.stl');old=load(D/'positive-x225/zero_w_gpio_male_receiving-world.stl')
r={'integrationReady':False,'accepted':False,'purpose':'Refine only false filled40pin male prism. Retain old full52x7 plastic footprint for2.54mm base; forty individual pins0.64nominal and0.8engineering upper receiver,notuserbrandmeasurement.','sourceDimensionBoundary':'2.54pitch fromZeroW mechanicaldrawing;0.64square standardheader metal used as parent-requested nominal model;0.8 is deliberate widened sensitivity. Base52x7 is unchanged conservativefootprint. Total8.5mm projection retained.','cases':[],'sourceHashes':n['hashes']}
for d in [2.,3.]:
 delta=-T[:3,0]*d
 for side in [.64,.8]:
  pieces=[mf.Manifold.cube([2.54,52,7],True).translate([67.31-1.27,-.011,119.5496]).transform(T[:3]).translate(delta)];rows=[]
  for pin in range(1,41):
   yy=-24.141+2.54*((pin-1)//2);zz=118.2796+(2.54 if pin%2==0 else 0);piece=mf.Manifold.cube([8.5-2.54,side,side],True).translate([67.31-(8.5+2.54)/2,yy,zz]).transform(T[:3]).translate(delta);pieces.append(piece)
  for i,p in enumerate(pieces):
   v,b=n['volume'](p,ob);rows.append({'part':'plastic_base' if i==0 else f'pin{i}','overlapMm3':v,'boundsMm':b,'gapCapped2Mm':float(p.min_gap(ob,2))})
  agg=mf.Manifold.batch_boolean(pieces,mf.OpType.Add);v,b=n['volume'](old.translate(delta),ob);outside=agg-old.translate(delta);row={'spacerMm':d,'pinWidthMm':side,'expectedParts':41,'completedParts':len(rows),'oldFilledPrismOverlapMm3':v,'oldOverlapBoundsMm':b,'refinedChecks':rows,'newOutsideOriginalEnvelopeMm3':max(0,float(outside.volume())),'meshExported':False};r['cases'].append(row);print(d,side,'old',v,'new',sum(p['overlapMm3'] for p in rows),'mingap',min(p['gapCapped2Mm'] for p in rows),flush=True);del pieces,agg;gc.collect()
(O/'spacer-discrete-male.json').write_text(json.dumps(r,indent=2)+'\n')
