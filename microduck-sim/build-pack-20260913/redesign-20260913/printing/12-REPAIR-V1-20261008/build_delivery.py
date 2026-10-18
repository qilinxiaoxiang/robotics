from pathlib import Path
import json,hashlib,shutil,zipfile,sys
D=Path(__file__).resolve().parent;R=D.parent.parent;H=R/'head-redesign-20261008'
prep=json.loads((D/'preparation.json').read_text())
assert prep['status']!='PRINT_HANDOFF_WITHDRAWN_PENDING_FULL_RIBBON','Full ribbon route and closure must be accepted before a new print handoff'
release=json.loads((D/'release-evidence.json').read_text())
assert release['printGeometryReleased'] is True and release['fullRibbonReviewed'] is True and release['currentClosureClear'] is True
for record in release['evidence']:
    source=Path(record['path'])
    assert hashlib.sha256(source.read_bytes()).hexdigest()==record['sha256'],('Stale release evidence',str(source))
for part in prep['frozenGeometry']:
    source=R/part['source']
    assert hashlib.sha256(source.read_bytes()).hexdigest()==part['sourceSha256'],('Changed print geometry',part['key'])
dest=D/'delivery-V1.3';dest.mkdir(exist_ok=True)
exports={'White':D/'white-yellow-native-review/native-028/White_028.gcode.3mf','Yellow':D/'native-Yellow/Yellow_V1.gcode.3mf','Black':H/'gpio-audio-repair/black-final-export/native-V1-Black-11/Black_V1_11_GUI.gcode','Orange':Path(sys.argv[1]).resolve()}
records=[]
for c in ['Yellow','White','Orange','Black']:
 out=dest/c;out.mkdir(exist_ok=True)
 edit=next((D/'staging-projects').glob('*_'+c+'_*editable.3mf'));shutil.copyfile(edit,out/(c+'_V1.3_editable.3mf'))
 src=exports[c];assert src.exists(),src
 suffix='.gcode.3mf' if c in ['White','Yellow'] else '.gcode'
 target=out/(c+'_V1.3'+suffix);shutil.copyfile(src,target)
 if suffix=='.gcode.3mf':
  with zipfile.ZipFile(src) as z:
   assert z.testzip() is None;assert 'Metadata/plate_1.png' in z.namelist();assert len(z.read('Metadata/plate_1.png'))>1000
   with z.open('Metadata/plate_1.gcode') as f:header=f.read(4096).decode()
 else:
  with src.open() as f:header=''.join(next(f) for _ in range(80))
 records.append({'color':c,'printer':prep['machineByColor'][c],'objects':sum(t['quantity'] for t in prep['frozenGeometry'] if t['color']==c),'sourceExport':str(src),'exportSha256':hashlib.sha256(src.read_bytes()).hexdigest(),'header':header[:600]})
for a in prep['frozenGeometry']:
 src=R/a['source'];assert src.exists();target=dest/a['color']/(a['key']+'_qty'+str(a['quantity'])+'.stl');shutil.copyfile(src,target)
text='''MicroDuck 修订 V1.3 · 2026-10-08

四种颜色共11种、16件。每个颜色目录都有已排盘可编辑3MF、原生打印导出文件、原始源STL。优先打开3MF；STL保留源设计坐标，单独导入需按3MF方向摆放。只使用本版一套文件。

黄色：下头壳×1。Bambu X1 Carbon/0.4mm/Cool Plate/PLA。
白色：前脸×1。Bambu X1 Carbon/0.4mm/Cool Plate/PLA。首层0.28mm已修复原来的点接触，其余层0.2mm。
橙色：弧面头盖×1、扬声器底托×1、压环×1。Elegoo Centauri Carbon/0.4mm/Textured PEI/PLA。扬声器孔已延续，安装孔和侧向螺母入口设局部禁支撑区。
黑色：眼圈×1、相机三螺钉压框×1、原嘴部支架×1、嘴部滑动环×1、颈部1mm小垫圈×4、Pi2mm垫圈×3。Elegoo Centauri Carbon/0.4mm/Textured PEI/PLA。0.1mm层高，保留滑动环0.3mm挡边。

打印导出：Bambu用完整.gcode.3mf；Elegoo用普通.gcode。预览颜色不选择实物料卷；对应装入黄色、白色、橙色、黑色PLA，单色挤出机1。

保留已装好的腿、脚踝、脚掌；保留下颚和上下唇垫。撤回此前拆分下颚、颈部大改和分体轴承承座。
颈部四处M2×6配4个1mm小垫圈；未装电机时清理原薄孔膜。
Pi三处固定各加一个2mm垫圈，用M2.5×8保持原咬合长度；第03点原被动承托留下2mm间隙，这版为三个非共线支点固定，插接排线时从背后托住PCB。
相机压框用3颗M2×4。扬声器底托与压环共用2颗M2.5×8，不能重复数成4颗。嘴部滑环有后挡边保持，宽挡边朝外侧；先套环再放原支架。

相机线已从实物确认：橙色Standard–Mini200mm（SC1892），宽端接Camera Module3，窄端接Zero W；替换摄像头上附带的白色Standard–Standard线。无须再量尺寸。

装线顺序：头盖保持打开，先接摄像头宽端，再接Pi窄端。排线金属触点朝向各自PCB；打开锁扣、平直插牢后锁好。两端加固段保持平直，手托PCB操作。中间余线在Pi侧边与板面外侧空隙松弯收纳；接口旁回弯向板外让开元件，不要精确复制示意曲线。合盖前把线让开功放、螺丝座和壳缝；盖子应自然落位，不能靠拧螺丝压住排线。

数字检查涵盖各盘实际首层、数量、安装孔、支撑、摆放、真实缩略图和导出。完整200mm收纳示例无自相穿插，盖体及Pi加垫圈后的合盖检查通过。接口旁已采用保持全长与两端位置的平缓过渡；实际摆放不要求复制数值曲线。验收范围见随包ASSEMBLY-REVIEW.txt。原下颚采用原仓库弹性装配方式；打印后的配合、自由转动、支撑移除、强度、上电和视觉拾取须在实物上检查。

AI assistance was used to draft.
'''
(dest/'README.txt').write_text(text)
shutil.copyfile(D/'ASSEMBLY-REVIEW.txt',dest/'ASSEMBLY-REVIEW.txt')
manifest={'version':'V1.3','problemIds':['P5','P6'],'partKinds':len(prep['frozenGeometry']),'quantity':sum(p['quantity'] for p in prep['frozenGeometry']),'nativeExports':records,'fullAssemblyAccepted':False,'complete200mmRibbonAccepted':release.get('exactIllustrativeRouteAccepted',False),'flexibleCableAssemblyReviewed':release['fullRibbonReviewed'],'releaseEvidence':release,'physicalFitVerified':False,'files':[]}
for f in dest.rglob('*'):
 if f.is_file() and f.name!='manifest.json':manifest['files'].append({'path':str(f.relative_to(dest)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
(dest/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
archive=D/'MicroDuck-Repair-V1.3-4Colors.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for f in dest.rglob('*'):
  if f.is_file():z.write(f,f.relative_to(dest))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(json.dumps({'archive':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,'partKinds':manifest['partKinds'],'quantity':manifest['quantity']},ensure_ascii=False))
