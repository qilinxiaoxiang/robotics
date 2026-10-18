"""STL print export with mandatory file readback; only remove zero-volume slugs.

STL float32 quantisation can split coincident surface triangles after a rigid
transform. An in-memory mesh check alone therefore cannot accept a print file.
"""
from pathlib import Path
import hashlib
import trimesh

def checked_print_export(path,mesh=None):
    path=Path(path)
    if mesh is not None:mesh.export(path)
    removed=[]
    original=trimesh.load(path,force='mesh')
    original_volume=float(original.volume)
    for attempt in range(3):
        readback=trimesh.load(path,force='mesh')
        pieces=readback.split(only_watertight=False)
        if readback.is_watertight and readback.is_winding_consistent and len(pieces)==1:
            break
        solids=[m for m in pieces if abs(float(m.volume))>1e-6]
        if len(solids)!=1 or not solids[0].is_watertight:
            raise ValueError(f'{path.name}: not exactly one closed positive-volume print solid')
        slugs=[m for m in pieces if m is not solids[0]]
        if not slugs or any(abs(float(m.volume))>1e-6 for m in slugs):
            raise ValueError(f'{path.name}: repair would remove material')
        removed.extend({'triangles':len(m.faces),'volume_mm3':float(m.volume),
                        'area_mm2':float(m.area),'bounds_mm':m.bounds.tolist()} for m in slugs)
        solids[0].export(path)
    else:raise ValueError(f'{path.name}: quantisation did not converge to one closed solid')
    # This result always describes the bytes on disk, not the pre-export mesh.
    final=trimesh.load(path,force='mesh')
    assert final.is_watertight and final.is_winding_consistent
    assert len(final.split(only_watertight=False))==1 and final.volume>0
    assert abs(float(final.volume)-original_volume)<1e-4
    return {'file':path.name,'read_back_from_disk':True,'watertight':bool(final.is_watertight),
            'winding_consistent':bool(final.is_winding_consistent),'connected_components':1,
            'triangles':len(final.faces),'volume_mm3':float(final.volume),
            'bounds_mm':final.bounds.tolist(),'removed_zero_volume_components':removed,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
