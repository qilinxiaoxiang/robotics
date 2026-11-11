# Open design NAME's schematic and export the whole sheet as a PNG with EAGLE's EXPORT IMAGE.
# Renders off-screen, so it needs no window in front and sees the full sheet. fusion.py checks
# that a new file appeared (EXPORT IMAGE can fail silently).
import os
d = designs(folder).get('@@NAME@@', {}).get('fsch')
if d is None:
    raise RuntimeError('no schematic named %r' % '@@NAME@@')
if os.path.exists('@@OUT@@'):
    os.remove('@@OUT@@')
doc = app.documents.open(d)
doc.activate()
app.executeTextCommand("Electron.run EXPORT IMAGE '%s' %d;" % ('@@OUT@@', int('@@DPI@@')))
if not os.path.exists('@@OUT@@'):
    raise RuntimeError('EXPORT IMAGE wrote nothing')
print(os.path.getsize('@@OUT@@'))
