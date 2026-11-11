import json
print(json.dumps({'files': sorted(n + '.' + e for n, ex in designs(folder).items() for e in ex),
                  'folders': sorted(x.name for x in folder.dataFolders)}))
