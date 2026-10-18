import os,sys,json,hashlib
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
D=Path(__file__).resolve().parent;R=D.parents[3];H=R/'head-redesign-20261008';source=H/'curved-head/openrb-curved-layout-world.stl';m=tm.load(source,force='mesh');v=m.vertices;f=m.faces
rr=f.ravel();cc=f[:,[1,2,0]].ravel();g=coo_matrix((np.ones(len(rr),np.int8),(rr,cc)),shape=(len(v),len(v))).tocsr();count,l=connected_components(g,directed=False);q=m.submesh([np.flatnonzero(l[f[:,0]]==65)],append=True);q.export(D/'j4-world.stl')
A=np.eye(4);A[:3,:3]=[[0,0,1],[1,0,0],[0,1,0]];A[:3,3]=[24.5,0,-18]
B=np.array([[0,0,-1,8.1],[0,1,0,0],[1,0,0,115.6146],[0,0,0,1.]])
C=np.array(json.loads((H/'curved-head/curved-layout.json').read_text())['transformsFromGuideWorld']['openrb']);T=C@B@A
q.apply_transform(np.linalg.inv(T));q.export(D/'j4-native.stl')
fig,axs=plt.subplots(1,3,figsize=(12,5))
for ax,idx,label in zip(axs,[(0,2),(0,1),(1,2)],['Front: X/Z, looking +Y','Top: X/Y','Side: Y/Z']):
 ax.add_collection(PolyCollection(q.triangles[:,:,idx],facecolors='lightgray',edgecolors='black',linewidths=.15));ax.autoscale();ax.set_aspect('equal');ax.set_title(label)
fig.savefig(D/'j4-orthographic.png',dpi=180)
print(json.dumps({'nativeBounds':q.bounds.tolist(),'T':T.tolist(),'triangles':len(q.faces)}))
(D/'extraction.json').write_text(json.dumps({'nativeBounds':q.bounds.tolist(),'nativeToWorld':T.tolist(),'source':str(source),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'componentIndex':65,'triangles':len(q.faces)},indent=2))
