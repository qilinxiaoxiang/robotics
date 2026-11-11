# Rename every file of design NAME (both .fprj and .fsch/.fbrd) to NEW.
d = designs(folder).get('@@NAME@@', {})
if not d:
    raise RuntimeError('no design named %r' % '@@NAME@@')
if '@@NEW@@' in designs(folder):
    raise RuntimeError('a design named %r already exists' % '@@NEW@@')
for f in d.values():
    f.name = '@@NEW@@'
print(sorted(designs(folder)))
