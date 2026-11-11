import json
print(json.dumps({'files': {n: {e: f.id for e, f in ex.items()} for n, ex in designs(folder).items()},
                  'folders': sorted(x.name for x in folder.dataFolders)}, ensure_ascii=False))
