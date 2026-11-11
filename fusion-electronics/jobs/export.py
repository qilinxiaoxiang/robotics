# Export Fusion's stored copy of design NAME's schematic as EAGLE .sch to OUT (acceptance input).
import os
d = designs(folder).get('@@NAME@@', {}).get('fsch')
if d is None:
    raise RuntimeError('no schematic named %r' % '@@NAME@@')
if os.path.exists('@@OUT@@'):
    os.remove('@@OUT@@')
doc = app.documents.open(d)
m = doc.schematic.exportManager
if not m.execute(m.createEagleSchExportOptions('@@OUT@@')):
    raise RuntimeError('export failed')
print('@@OUT@@')
