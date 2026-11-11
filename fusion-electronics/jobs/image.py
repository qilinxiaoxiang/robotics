# Open design NAME's schematic and export the whole sheet as a PNG with EAGLE's EXPORT IMAGE.
# Renders off-screen, so it needs no window in front and sees the full sheet (a screenshot only
# shows what the window shows, and the Claude window can cover half of it).
d = designs(folder).get('@@NAME@@', {}).get('fsch')
if d is None:
    raise RuntimeError('no schematic named %r' % '@@NAME@@')
doc = app.documents.open(d)
doc.activate()
app.executeTextCommand("Electron.run EXPORT IMAGE '%s' %s;" % ('@@OUT@@', '@@DPI@@'))
import os
print(os.path.getsize('@@OUT@@'))
