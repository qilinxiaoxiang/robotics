from pathlib import Path
import sys,json,subprocess,zipfile,hashlib
D=Path(__file__).resolve().parent;row=next(r for r in json.loads((D/'preparation.json').read_text())['rows']if r['color']==sys.argv[1] and (len(sys.argv)<3 or r['machine']==sys.argv[2]));p=Path(row['project']);out=D/'native'/f"{row['color']}_{row['machine']}";out.mkdir(parents=True,exist_ok=True)
exe='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'if row['machine']=='Bambu'else'/Volumes/OrcaSlicer/OrcaSlicer.app/Contents/MacOS/OrcaSlicer'
cmd=[exe,'--allow-newer-file','--arrange','0','--orient','0','--slice','0']
if row['machine']=='Elegoo':cmd+=['--load-filaments',str(D.parents[2]/'printing-elegoo-20260929/filament.json')]
cmd+=['--export-3mf','sliced.3mf','--outputdir',str(out),str(p)]
(out/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with(out/'cli.log').open('w')as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=170)
assert r.returncode==0,(r.returncode,str(out/'cli.log'))
with zipfile.ZipFile(out/'sliced.3mf')as z:
 gc=[n for n in z.namelist()if n.endswith('.gcode')];assert len(gc)==1;code=z.read(gc[0]);(out/'plate_1.gcode').write_bytes(code)
result={'passed':True,'source':row,'nativeArchive':str(out/'sliced.3mf'),'archiveSha256':hashlib.sha256((out/'sliced.3mf').read_bytes()).hexdigest(),'gcodeSha256':hashlib.sha256(code).hexdigest()};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(row['color'],row['machine'],'OK',flush=True)
