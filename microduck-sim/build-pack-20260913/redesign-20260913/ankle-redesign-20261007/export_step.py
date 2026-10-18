from pathlib import Path
import json,hashlib,trimesh,numpy as np,cadquery as cq
R=Path(__file__).resolve().parent;rows=[]
for side in ['left','right']:
 for name in ['base','cheek','sleeve']:
  stl=R/'STL'/f'{side}-{name}-world.stl';m=trimesh.load(stl,force='mesh',process=True);assert m.is_watertight
  original=m.copy();m.vertices=np.round(m.vertices,5);m.merge_vertices(digits_vertex=5);m.update_faces(m.nondegenerate_faces());m.remove_unreferenced_vertices();assert m.is_watertight,(side,name,'Quantized mesh not closed');faces=[]
  for tri in m.triangles:
   if np.linalg.norm(np.cross(tri[1]-tri[0],tri[2]-tri[0]))<1e-10:continue
   faces.append(cq.Face.makeFromWires(cq.Wire.makePolygon([cq.Vector(*v) for v in tri],close=True)))
  solid=cq.Solid.makeSolid(cq.Shell.makeShell(faces));assert solid.isValid(),(side,name,'Invalid sewn source-derived BREP');assert abs(solid.Volume()-m.volume)<max(.03,abs(m.volume)*1e-5),(solid.Volume(),m.volume)
  dest=R/'CAD'/f'{side}-{name}.step';cq.exporters.export(solid,str(dest));rows.append(dict(side=side,part=name,stl=str(stl),cad=str(dest),cadKind='Source-derived faceted BREP; exported STL remains unchanged. STEP vertices welded to0.00001mm to resolve OCCT tiny-edge sewing; original geometry is tessellated, not invented analytic surfaces.',stepVertexQuantizationMm=.00001,sourceStlSha256=hashlib.sha256(stl.read_bytes()).hexdigest(),stepSha256=hashlib.sha256(dest.read_bytes()).hexdigest(),valid=True,stlVolumeMm3=float(original.volume),stepInputWeldedMeshVolumeMm3=float(m.volume),stepVolumeMm3=solid.Volume(),volumeDeltaToOriginalStlMm3=solid.Volume()-float(original.volume),stepVertexGridMaxDisplacementMm=8.660254037844386e-6,faces=len(faces)));print('STEP_VALID',side,name,len(faces),flush=True)
(R/'cad-export.json').write_text(json.dumps({'passed':True,'exports':rows},indent=2)+'\n')
