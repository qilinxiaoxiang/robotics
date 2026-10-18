"""Invert the actual slicer's extruder-offset command transform for readback.

OrcaSlicer v2.4.2 GCode.cpp point_to_gcode():
    commandedXY = modelXY + origin - extruder_offset
The inverse adds the configured active nozzle offset. These jobs have one nozzle;
different multi-nozzle offsets would require explicit tool-state parsing, not a guess.
"""
import numpy as np

def offset_from_config(cfg):
    value=cfg.get('extruder_offset',['0x0'])
    value=value if isinstance(value,list) else [value]
    offsets=[np.array([float(n) for n in entry.split('x')],float) for entry in value]
    if not offsets or any(len(v)!=2 for v in offsets):raise ValueError('Invalid extruder_offset configuration')
    if any(not np.allclose(v,offsets[0],atol=1e-12) for v in offsets[1:]):
        raise ValueError('Different nozzle offsets require active-tool-state readback')
    return offsets[0]

def assert_object_absolute_xy(code):
    """The shared parser assumes absolute XY; reject a contrary active-object block."""
    active=False;absolute=True
    for line in code.splitlines():
        if line.startswith('EXCLUDE_OBJECT_START'):active=True
        elif line.startswith('EXCLUDE_OBJECT_END'):active=False
        elif line.split(';',1)[0].strip()=='G91':absolute=False
        elif line.split(';',1)[0].strip()=='G90':absolute=True
        if active and not absolute:raise ValueError('Relative XY in active object requires modal parser support')

def material_frame_paths(paths,cfg,code):
    assert_object_absolute_xy(code);offset=offset_from_config(cfg)
    for layers in paths.values():
        for entries in layers.values():
            for entry in entries:entry['points']=[(x+offset[0],y+offset[1]) for x,y in entry['points']]
    return paths,offset.tolist()
