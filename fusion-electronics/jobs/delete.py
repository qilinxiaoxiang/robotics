# Delete design NAME in the folder, or the subfolder NAME when KIND == 'folder'.
# Fusion refuses to delete a child file (.fsch/.fbrd) while its parent electronics design
# (.fprj) exists: DataFile.deleteMe raises "InternalValidationError : res". So: close any open
# document of the design, delete the .fprj first, then the remaining files, then re-list.
import json


def close_docs(files):
    ids = {f.id for f in files}
    for doc in list(app.documents):
        try:
            if doc.dataFile and doc.dataFile.id in ids:
                doc.close(False)
        except Exception:
            pass


def delete_design(f, name):
    d = designs(f).get(name, {})
    if not d:
        return 'absent'
    close_docs(d.values())
    order = sorted(d, key=lambda e: 0 if e == 'fprj' else 1)
    for e in order:
        cur = designs(f).get(name, {}).get(e)   # deleting the parent can remove children
        if cur is not None:
            cur.deleteMe()
    left = designs(f).get(name)
    if left:
        raise RuntimeError('still present after delete: %s' % sorted(left))
    return 'deleted'


if '@@KIND@@' == 'folder':
    sub = folder.dataFolders.itemByName('@@NAME@@')
    if sub is None:
        print(json.dumps({'@@NAME@@': 'absent'}))
    else:
        done = {n: delete_design(sub, n) for n in list(designs(sub))}
        if sub.dataFolders.count:
            raise RuntimeError('folder has subfolders; delete them first: %s' % [x.name for x in sub.dataFolders])
        sub.deleteMe()
        print(json.dumps({'@@NAME@@': 'folder deleted', 'designs': done,
                          'still_listed': folder.dataFolders.itemByName('@@NAME@@') is not None}))
else:
    print(json.dumps({'@@NAME@@': delete_design(folder, '@@NAME@@')}))
