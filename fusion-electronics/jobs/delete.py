# Delete electronics design NAME in the folder, or the subfolder NAME when KIND == 'folder'.
# Fusion refuses to delete a child file (.fsch/.fbrd) while its parent electronics design (.fprj)
# exists: DataFile.deleteMe raises "InternalValidationError : res". So: close any open document of
# the design, delete the .fprj first, then the children, then re-list. Only electronics files are
# touched; other files that share the name (.f3d, .pdf) stay.
import json
ELECTRONICS = ('fprj', 'fsch', 'fbrd')


def close_docs(files):
    ids = {f.id for f in files}
    for doc in list(app.documents):
        try:
            if doc.dataFile and doc.dataFile.id in ids:
                doc.close(False)
        except Exception:
            pass


def delete_design(f, name):
    d = {e: x for e, x in designs(f).get(name, {}).items() if e in ELECTRONICS}
    if not d:
        return 'absent'
    close_docs(d.values())
    for e in ELECTRONICS:                       # fprj first
        cur = designs(f).get(name, {}).get(e)   # deleting the parent can remove children
        if cur is not None:
            cur.deleteMe()
    left = [e for e in designs(f).get(name, {}) if e in ELECTRONICS]
    if left:
        raise RuntimeError('still present after delete: %s.%s' % (name, left))
    return 'deleted'


if '@@KIND@@' == 'folder':
    sub = folder.dataFolders.itemByName('@@NAME@@')
    if sub is None:
        print(json.dumps({'@@NAME@@': 'absent'}))
    else:
        if sub.dataFolders.count:
            raise RuntimeError('folder has subfolders; delete them first: %s' % [x.name for x in sub.dataFolders])
        other = [n + '.' + e for n, ex in designs(sub).items() for e in ex if e not in ELECTRONICS]
        if other:
            raise RuntimeError('folder holds non-electronics files; not deleting: %s' % other)
        done = {n: delete_design(sub, n) for n in list(designs(sub))}
        sub.deleteMe()
        if folder.dataFolders.itemByName('@@NAME@@') is not None:
            raise RuntimeError('folder still listed after delete')
        print(json.dumps({'@@NAME@@': 'folder deleted', 'designs': done}))
else:
    print(json.dumps({'@@NAME@@': delete_design(folder, '@@NAME@@')}))
