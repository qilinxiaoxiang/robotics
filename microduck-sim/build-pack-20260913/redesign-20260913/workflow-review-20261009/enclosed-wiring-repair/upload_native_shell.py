import adsk.core,adsk.fusion,json,time,traceback
from pathlib import Path
P=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair')
a=adsk.core.Application.get();r={'status':'STARTED'}
def save(): (P/'native-shell-upload.json').write_text(json.dumps(r,indent=2)+'\n')
try:
 projects=[p for p in a.data.dataProjects];r['projects']=[{'name':p.name,'id':p.id} for p in projects];save()
 target=next(p for p in projects if p.name=='Default Project');folder=target.rootFolder
 files=[f for f in folder.dataFiles];r['existing']=[{'name':f.name,'id':f.id} for f in files];save()
 match=next((f for f in files if f.name.startswith('top_head_shell')),None)
 if match:r.update(status='EXISTING',dataFileId=match.id)
 else:
  future=folder.uploadFile(str(P/'head-layout/sources/head-source/top_head_shell_头部上壳.SLDPRT'))
  start=time.time()
  while time.time()-start<40 and future.uploadState==adsk.core.UploadStates.UploadProcessing:
   adsk.doEvents();time.sleep(.25)
  r.update(uploadState=str(future.uploadState),elapsed=time.time()-start)
  if future.dataFile:r.update(status='UPLOADED',dataFileId=future.dataFile.id,name=future.dataFile.name)
  else:r['status']='UPLOAD_PENDING_OR_FAILED'
 save()
except Exception:r.update(status='ERROR',error=traceback.format_exc());save()
