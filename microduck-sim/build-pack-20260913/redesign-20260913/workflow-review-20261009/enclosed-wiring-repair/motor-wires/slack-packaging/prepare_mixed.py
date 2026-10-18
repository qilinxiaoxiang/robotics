from pathlib import Path
import json,hashlib,copy
D=Path(__file__).resolve().parent
k=json.loads((D/'knee100-right.json').read_text());f=json.loads((D/'surface-folds-right.json').read_text());assert k['currentStaticClear']and f['currentStaticClear'];rows=k['rows']+[r for r in f['rows']if r['routeId']=='ttl-02-01'];out={'rows':rows,'currentStaticClear':True,'status':'Mixed candidate; full delta gate pending','sourceHashes':{str(D/n):hashlib.sha256((D/n).read_bytes()).hexdigest()for n in ['knee100-right.json','surface-folds-right.json']}};(D/'mixed-right.json').write_text(json.dumps(out,indent=2))
