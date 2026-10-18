"""Explicit source closure for geometry imported through assembly_fk."""
from pathlib import Path
import hashlib
import xml.etree.ElementTree as ET
O = Path(__file__).resolve().parent
S = O.parents[2]
W = S / 'hardware-design-20260912/whole-robot-20260912'

def hashes(paths):
    return {str(Path(p).resolve()): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}

def assembly_sources():
    robot = S / 'microduck_rl/src/mjlab_microduck/robot/microduck'
    xml = robot / 'robot_allcollisions.xml'
    # raw(name) resolves visual geometry through these native assets.
    names = {g.get('mesh') for g in ET.parse(xml).iter('geom') if g.get('class') == 'visual' and g.get('mesh')}
    return [Path(__file__), xml, W/'assembly/assembly_fk.py',
            *[robot/'assets'/(name+'.stl') for name in sorted(names)]]
