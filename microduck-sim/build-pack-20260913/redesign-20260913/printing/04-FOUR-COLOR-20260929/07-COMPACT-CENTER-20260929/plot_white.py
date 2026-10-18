from pathlib import Path
import json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
D=Path(__file__).resolve().parent;C=D.parent
src=C/'05-BAMBU-WHITE-YELLOW/audit_bambu_spacing.py';ns={'__file__':str(src),'__name__':'audit_plot'};exec(src.read_text().replace('return result','return result,hulls,shapes'),ns)
paths=[C/'06-CENTERED-20260929/Bambu/WHITE/MicroDuck_Bambu_WHITE_CENTERED.gcode.3mf',D/'Bambu/WHITE/MicroDuck_Bambu_WHITE_COMPACT.gcode.3mf'];fig,axes=plt.subplots(1,2,figsize=(11,5.6));reports=[]
for ax,p,title in zip(axes,paths,['Before: centered long strip','After: compact two-dimensional cluster']):
 r,hulls,shapes=ns['audit_archive'](p,3);reports.append(r)
 colors=['#2673b8','#dc8636','#35a273']
 for (key,shape),color in zip(shapes.items(),colors):
  ax.add_collection(LineCollection([list(g.coords) for g in shape.geoms],colors=color,linewidths=.12,alpha=.12,rasterized=True))
  boundary=hulls[key].buffer(r['conservative_bead_radius_including_arc_error_mm']);x,y=boundary.exterior.xy;ax.plot(x,y,color=color,lw=1)
 b=[min(o['extrusion_bounds_mm'][i] for o in r['objects']) if i<2 else max(o['extrusion_bounds_mm'][i] for o in r['objects']) for i in range(4)]
 ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,linestyle='--',edgecolor='#333333'));ax.add_patch(Rectangle((0,0),18,28,color='#dd5555',alpha=.2));ax.plot(128,128,'+',color='#333333')
 ax.set(xlim=(0,256),ylim=(0,256),aspect='equal',xlabel='X (mm)',ylabel='Y (mm)',title=f'{title}\n{b[2]-b[0]:.1f} × {b[3]-b[1]:.1f} mm; minimum edge {r["minimum_bed_margin_mm"]:.1f} mm');ax.grid(alpha=.18)
fig.suptitle('Bambu WHITE: actual model and support extrusion paths, same scale\nNo rotations or mesh changes; startup purge paths excluded');fig.tight_layout();fig.savefig(D/'WHITE-before-after.png',dpi=180,bbox_inches='tight')
(D/'bambu-native-audit.json').write_text(json.dumps({'WHITE_before':reports[0],'WHITE_after':reports[1],'yellow_after':ns['audit_archive'](D/'Bambu/yellow/MicroDuck_Bambu_yellow_COMPACT.gcode.3mf',4)[0]},indent=2)+'\n')
print([(r['passed'],r['minimum_interobject_gap_lower_bound_mm'],r['minimum_bed_margin_mm']) for r in reports])
