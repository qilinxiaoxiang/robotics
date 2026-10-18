from pathlib import Path
import json,hashlib,zipfile,shutil
D=Path(__file__).resolve().parent
idx=json.loads((D/'dual-printer/delivery-index.json').read_text()); files=idx['files']; assert len(files)==8
assert idx.get('status') == 'RELEASED', idx.get('status')
assert len({(f['color'],f['machine']) for f in files})==8
out=D/'zhengxia_MicroDuck_V1.4_8-files.zip'
for f in files:
 p=Path(f['path']);assert p.is_file() and f['filename'].startswith('zhengxia_')
 assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256']
 assert f['estimatedSeconds']>0
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(f['path'],f['filename'])
with zipfile.ZipFile(out) as z:assert len(z.namelist())==8 and z.testzip() is None
local=Path('/Users/xiangzheng/Downloads')/out.name;shutil.copyfile(out,local)
receipt={'version':'V1.4','archive':str(out),'localDelivery':str(local),'archiveSha256':hashlib.sha256(out.read_bytes()).hexdigest(),'printFileCount':8,'partKinds':11,'quantity':13,'incrementalOnly':True,'replacements':6,'additions':7,'files':files,'userChoice':'Integral 1mm neck seats; four loose neck washers removed.','unchangedFromV1_3':'All geometry except neck bracket; native variants for both printers.','physicalFitVerified':False}
(D/'dual-printer/package-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='files'},ensure_ascii=False))
