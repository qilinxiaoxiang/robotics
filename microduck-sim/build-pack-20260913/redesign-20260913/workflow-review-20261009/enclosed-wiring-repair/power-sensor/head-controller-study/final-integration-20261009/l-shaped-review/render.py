from pathlib import Path
import sys,json,hashlib,trimesh,numpy as np
from scipy.spatial import ConvexHull
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
F=Path(__file__).resolve().parent
src=F/(sys.argv[1] if len(sys.argv)>1 else 'layout.json')
r=json.loads(src.read_text());fig,axs=plt.subplots(1,3,figsize=(18,7))
colors={'controller':'#cf6a28','pi':'#19955f','pi_interface_conditional':'#d62376','amp':'#9f5dcc','speaker':'#1976c9','fixed':'#606770','conditional_A_join':'#ab2038'}
views=[(0,1,'Top X/Y'),(0,2,'Side X/Z'),(1,2,'Front Y/Z')]
for q in sorted(r['parts'],key=lambda q:q['group']!='fixed'):
 p=Path(q['file']);assert hashlib.sha256(p.read_bytes()).hexdigest()==q['sha256'];m=trimesh.load_mesh(p);m.apply_transform(q['worldTransform']);v=m.vertices
 for ax,(a,b,title) in zip(axs,views):
  if q['key']=='current_cap':
   # Exact shell mid-plane sections; projected outer hull would obscure the layer heights.
   normal=np.zeros(3);normal[3-a-b]=1;origin=np.zeros(3);origin[3-a-b]=0 if 3-a-b!=2 else 140
   sec=m.section(plane_origin=origin,plane_normal=normal)
   if sec:
    for line in sec.discrete: ax.plot(line[:,a],line[:,b],color='#222',linewidth=.8)
  else:
   xy=v[:,[a,b]];h=ConvexHull(xy);c=colors[q['group']]
   if q['key'].startswith('C22') or 'relief' in q['key'].lower() or q['key'].startswith('EH'):c='#e82b28'
   ax.add_patch(Polygon(xy[h.vertices],facecolor=c,edgecolor=c,alpha=.22 if q['group']=='fixed' else .45,linewidth=.35))
  ax.set_title(title);ax.set_aspect('equal');ax.autoscale_view();ax.grid(alpha=.2);ax.set_xlabel('XYZ'[a]+' mm');ax.set_ylabel('XYZ'[b]+' mm')
fig.suptitle(src.stem+' — diagnostic, NOT a fit approval',fontsize=17)
fig.text(.02,.03,'Orange: complete OpenRB • Green: populated Pi • Magenta: Micro-B receiver • Purple: amplifier • Blue: speaker • Grey: retained mechanics\nBlack: exact shell section (top uses Z140); coloured component projections are convex silhouettes. USB-C hard receiver remains included. No mounts adopted.',fontsize=11)
fig.tight_layout(rect=[0,.09,1,.94]);out=F/(src.stem+'-views.png');fig.savefig(out,dpi=130);fig.savefig(out.with_suffix('.svg'));print(out)
