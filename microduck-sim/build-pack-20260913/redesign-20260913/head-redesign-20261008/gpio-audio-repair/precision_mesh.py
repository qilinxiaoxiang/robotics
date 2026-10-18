"""Keep CAD-created near-coplanar vertices in double precision through STL text.
No geometry libraries are imported here; caller supplies guarded CAD runtime.
No face deletion, hole filling, coordinate welding, or material offsets.
"""
def load(c,path):
 m=c.tm.load(path,file_type='stl',force='mesh')
 s=c.mf.Manifold(c.mf.Mesh64(c.np.asarray(m.vertices,c.np.float64),c.np.asarray(m.faces,c.np.uint64)))
 if s.status()!=c.mf.Error.NoError:raise ValueError('Invalid manifold: '+str(path))
 return s

def export(c,s,path):
 q=s.to_mesh64();m=c.tm.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True)
 if not m.is_watertight:raise ValueError('Non-watertight double precision output: '+str(path))
 with path.open('w') as f:
  f.write('solid precise_cad\n')
  for normal,triangle in zip(m.face_normals,m.triangles):
   f.write(' facet normal '+' '.join(repr(float(x)) for x in normal)+'\n  outer loop\n')
   for v in triangle:f.write('   vertex '+' '.join(repr(float(x)) for x in v)+'\n')
   f.write('  endloop\n endfacet\n')
  f.write('endsolid precise_cad\n')
 read=c.tm.load(path,file_type='stl',force='mesh')
 if not read.is_watertight:raise ValueError('STL round trip is not watertight: '+str(path))
 return {'format':'ASCII STL round-trip float64 text','triangles':len(read.faces),'watertight':True,'windingConsistent':bool(read.is_winding_consistent)}
