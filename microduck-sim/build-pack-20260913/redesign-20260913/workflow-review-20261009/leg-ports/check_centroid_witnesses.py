from pathlib import Path
import cadquery as cq,json
D=Path(__file__).resolve().parent;s=cq.importers.importStep(str(D.parents[1]/'fastener-audit/sources/X330_3d.stp')).val();rows=[]
for si in [13,14]:
 for fi in [4,40]:
  f=s.Solids()[si].Faces()[fi];c=f.Center();v=cq.Vertex.makeVertex(*c.toTuple());rows.append({'solid':si,'face':fi,'centroidDistanceToItsOwnTrimmedFaceMm':f.distance(v)})
(D/'centroid-witness-diagnostic.json').write_text(json.dumps({'rows':rows,'scope':'A centroid of a trimmed/concave CAD face need not lie on its surface; only source surface witnesses are suitable for registration.'},indent=2));print(json.dumps(rows,indent=2))
