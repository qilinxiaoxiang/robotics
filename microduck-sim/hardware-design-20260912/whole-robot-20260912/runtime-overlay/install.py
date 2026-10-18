"""Reversible file overlay; does not start a service or access robot hardware."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def install(target):
    target=Path(target).resolve();backup=target/'.runtime-overlay61-backup'
    if backup.exists():raise RuntimeError('Backup exists. Uninstall first; never overwrite the original backup.')
    walk=target/'src/moves/walk.py';const=target/'src/constants.py'
    if not walk.is_file() or not const.is_file():raise RuntimeError('Target must be the community microduck deployment directory containing src/.')
    lock=json.loads((P/'source-lock.json').read_text())
    if sha(walk)!=lock['community_walk_sha256']:raise RuntimeError('Community WalkMove differs from the verified source; review the difference before adapting this overlay.')
    text=const.read_text()
    replacements={'KP_RL':'200','BAM_VIN':'5.0','BAM_VIN_MIN':'4.0','BAM_MAX_CURRENT':'1.47'}
    for key,value in replacements.items():
        text,count=re.subn(r'(?m)^('+key+r'\s*:\s*(?:int|float)\s*=\s*)[^\n#]+',lambda m:m[1]+value+' ',text)
        if count!=1:raise RuntimeError('Expected exactly one '+key+' constant.')
    # Do not alter MOTOR_OFFSET, MOTOR_SIGN, mounting quaternion, neutral pose,
    # KP_DEFAULT, main.py, scheduler, services, or the original walk.onnx.
    payload={'src/moves/walk.py':(P/'src/moves/walk.py').read_bytes(),'src/constants.py':text.encode(),
             'src/agents/walk61.onnx':(P/'models/walk61.onnx').read_bytes(),'src/agents/stand61.onnx':(P/'models/stand61.onnx').read_bytes()}
    backup.mkdir();records={}
    for name,data in payload.items():
        dest=target/name;records[name]={'existed':dest.exists(),'installed_sha256':hashlib.sha256(data).hexdigest()}
        if dest.exists():
            saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,saved)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    (backup/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    return {'status':'installed','target':str(target),'modified_files':list(records),'services_started':False}
def uninstall(target):
    target=Path(target).resolve();backup=target/'.runtime-overlay61-backup'
    records=json.loads((backup/'manifest.json').read_text())
    for name,record in records.items():
        if not (target/name).is_file() or sha(target/name)!=record['installed_sha256']:
            raise RuntimeError('Installed file changed since overlay: '+name+'. Original remains in backup; refusing to erase later edits.')
    for name,record in records.items():
        if record['existed']:shutil.copy2(backup/name,target/name)
        else:(target/name).unlink()
    shutil.rmtree(backup)
    return {'status':'restored','target':str(target),'services_started':False}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['install','uninstall']);ap.add_argument('target',type=Path);a=ap.parse_args()
    print(json.dumps((install if a.mode=='install' else uninstall)(a.target),indent=2))
