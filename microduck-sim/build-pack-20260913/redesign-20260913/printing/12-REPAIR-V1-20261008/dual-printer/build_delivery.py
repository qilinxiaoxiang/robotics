from pathlib import Path
import json,zipfile,hashlib,re,base64,struct,math,shutil
D=Path(__file__).resolve().parent;out=D/'delivery';out.mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):
 with zipfile.ZipFile(p)as z:
  n=next(n for n in z.namelist()if n.endswith('.gcode'));return z.read(n),json.loads(z.read('Metadata/project_settings.config')),{n:z.read(n)for n in z.namelist()if n.endswith('.png')}
def secs(s):return sum(int(n)*{'h':3600,'m':60,'s':1}[u]for n,u in re.findall(r'(\d+)\s*([hms])',s))
prior=json.loads((D/'delivery-index.json').read_text()) if (D/'delivery-index.json').exists() else {}
files=[];checks=[]
for color in ['Yellow','White','Orange','Black']:
 bsrc=D.parent/'delivery-V1.3-Incremental/White/White_V1.3.gcode.3mf'if color=='White'else D/'native'/f'{color}_Bambu/sliced.3mf'
 bg,bc,pngs=read(bsrc);assert 'Metadata/plate_1.png'in pngs
 for machine in ['Bambu','Elegoo']:
  src=bsrc if machine=='Bambu'else D/'native'/f'{color}_Elegoo/sliced.3mf';gc,cfg,imgs=read(src)
  expected=('Bambu Lab X1 Carbon','Cool Plate','GFA00')if machine=='Bambu'else('Elegoo Centauri Carbon','Textured PEI Plate','EPLAB00')
  assert cfg['printer_model']==expected[0]and cfg['curr_bed_type']==expected[1]and cfg['filament_ids']==[expected[2]]
  if color=='White':assert float(cfg['initial_layer_print_height'])==.28
  text=gc.decode();match=re.search(r'total estimated time:\s*([^\r\n]+)',text)if machine=='Bambu'else re.search(r'estimated printing time \(normal mode\)\s*=\s*([^\r\n]+)',text)
  assert match;seconds=secs(match.group(1));minutes=math.ceil(seconds/60);time=(f'{minutes//60}h'if minutes>=60 else'')+f'{minutes%60}m';assert seconds>60 and len(gc)>10000
  label='Bambu-X1C'if machine=='Bambu'else'Elegoo-Centauri-Carbon';name=f'zhengxia_V1.4_{color}_{label}_{time}'+('.gcode.3mf'if machine=='Bambu'else'.gcode');dest=out/name
  if machine=='Bambu':shutil.copyfile(src,dest);previewMode='native archive PNG retained'
  else:
   assert b'thumbnail begin'not in gc
   blocks=[]
   for key in ['Metadata/plate_1.png','Metadata/plate_1_small.png']:
    b=pngs[key];assert b[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',b[16:24]);enc=base64.b64encode(b).decode();blocks.append(f'; thumbnail begin {w}x{h} {len(enc)}\n'+'\n'.join('; '+enc[i:i+78]for i in range(0,len(enc),78))+'\n; thumbnail end\n')
   prefix=('\n'.join(blocks)+'\n').encode();dest.write_bytes(prefix+gc);assert dest.read_bytes()[len(prefix):]==gc;previewMode='unmodified native Bambu PNG of identical plate geometry; native Elegoo command stream unchanged'
  files.append({'color':color,'machine':'Bambu X1 Carbon'if machine=='Bambu'else'Elegoo Centauri Carbon','path':str(dest),'filename':name,'estimatedSeconds':seconds,'estimatedTime':time,'sha256':sha(dest.read_bytes()),'plate':expected[1]})
  checks.append({'color':color,'machine':machine,'nativeSource':str(src),'sourceSha256':sha(src.read_bytes()),'nativeGcodeSha256':sha(gc),'nativeTimeText':match.group(1),'printer':cfg['printer_model'],'bed':cfg['curr_bed_type'],'filament':cfg['filament_settings_id'],'initialLayerMm':cfg['initial_layer_print_height'],'thumbnailProvenance':previewMode,'thumbnailNativeSource':str(bsrc),'thumbnailSha256':sha(pngs['Metadata/plate_1.png']),'gcodeCommandStreamUnchanged':True})
keep={f['filename']for f in files}
for old in prior.get('files',[]):
 p=Path(old['path'])
 if p.parent==out and p.name not in keep and p.exists():
  assert sha(p.read_bytes())==old['sha256'];archive=D/'superseded-delivery';archive.mkdir(exist_ok=True);shutil.move(str(p),str(archive/p.name))
assert len(files)==8 and len(list(out.iterdir()))==8
(D/'delivery-index.json').write_text(json.dumps({'version':'V1.4','status':'NOT_RELEASED','files':files},indent=2)+'\n');(D/'native-delivery-checks.json').write_text(json.dumps({'passed':True,'checks':checks,'firstLayerReviewSeparate':True,'notPhysicalPrinterExecution':True},indent=2)+'\n')
for f in files:print(f['filename'],f['estimatedSeconds'])
