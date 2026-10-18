#!/usr/bin/env python3
"""Inspect publisher PyPI wheel tags; never install or open robot devices."""
from pathlib import Path
import json, urllib.request, urllib.error, hashlib, datetime
D=Path(__file__).resolve().parent
runtime=D.parents[1]/'phase1/runtime'
rows=[]
for line in (runtime/'requirements.txt').read_text().splitlines():
    if not line or line.startswith('#'):continue
    name,version=line.split('==');url=f'https://pypi.org/pypi/{name}/{version}/json'
    row={'name':name,'version':version,'url':url}
    try:
        raw=urllib.request.urlopen(url,timeout=25).read();data=json.loads(raw)
        files=[x['filename'] for x in data['urls'] if x['packagetype']=='bdist_wheel']
        row.update(metadataSha256=hashlib.sha256(raw).hexdigest(),requiresPython=data['info']['requires_python'],wheelCount=len(files),armv6Wheels=[x for x in files if 'armv6' in x or x.endswith('-none-any.whl')],armv7Wheels=[x for x in files if 'armv7' in x],linuxAarch64Wheels=[x for x in files if 'aarch64' in x and 'linux' in x],macArm64Wheels=[x for x in files if 'macosx' in x and ('arm64' in x or 'universal2' in x)],metadataFetched=True)
    except (urllib.error.URLError,ValueError) as e:
        row.update(metadataFetched=False,error=str(e))
    rows.append(row)
report={'checkedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'requirementsSha256':hashlib.sha256((runtime/'requirements.txt').read_bytes()).hexdigest(),'scope':'Publisher wheel inventory, not an ARM install test. ARMv7 is not compatible with ARMv6. No armv6/universal wheel blocks the old binary-only pip recipe; source builds remain separate unverified work.','rows':rows}
(D/'dependency-wheel-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{'name':r['name'],'fetched':r['metadataFetched'],'armv6OrUniversal':len(r.get('armv6Wheels',[])),'linuxAarch64':len(r.get('linuxAarch64Wheels',[])),'error':r.get('error')} for r in rows],indent=2))
