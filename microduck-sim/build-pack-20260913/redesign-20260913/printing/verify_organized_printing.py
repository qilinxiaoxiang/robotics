"""Verify organized copies and native thumbnail exports without operating the GUI."""
from pathlib import Path
import base64, datetime, hashlib, io, json, re, sys, zipfile
import xml.etree.ElementTree as ET
from PIL import Image, ImageStat

O=Path(__file__).resolve().parent
B=O.parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

errors=[]
checks=[]
def check(label, fn):
    try:
        data=fn()
        checks.append({'check':label,'passed':True,'evidence':data})
    except Exception as exc:
        errors.append({'check':label,'error':str(exc)})
        checks.append({'check':label,'passed':False,'error':str(exc)})

def copies():
    m=json.loads((O/'copy-manifest.json').read_text())
    records=m['copy_records']
    assert len(records)==99, f'Expected original99copy records, got{len(records)}'
    for r in records:
        src=Path(r['source']); dst=O/r['copy']
        assert src.is_file() and dst.is_file(),r['copy']
        assert sha(src)==sha(dst)==r['sha256'],f'Changed source or copy: {r["copy"]}'
        assert src.stat().st_size==dst.stat().st_size==r['bytes'],r['copy']
    return {'records':99,'manifest_sha256':sha(O/'copy-manifest.json'),'all_sources_and_copies_match':True}

def stls():
    m=json.loads((O/'copy-manifest.json').read_text())
    original=json.loads((B/'print-manifest.json').read_text())['instances']
    with zipfile.ZipFile(B/'current-print-queue.3mf') as z:
        tree=ET.fromstring(z.read('Metadata/model_settings.config'))
    names={v.get('id'):v.find("metadata[@key='name']").get('value') for v in tree.findall('object')}
    records=[r for r in m['copy_records'] if r['copy'].startswith('01-STL/')]
    assert len(records)==len(original)==89
    assert {r['manifest_instance_index'] for r in records}==set(range(89))
    counts=[]
    for n,plate in enumerate(tree.findall('plate'),1):
        ids={v.find("metadata[@key='object_id']").get('value') for v in plate.findall('model_instance')}
        local=[r for r in records if r['plate']==n]
        assert {r['object_id'] for r in local}==ids
        assert len(list((O/f'01-STL/plate-{n:02d}').glob('*.stl')))==len(ids)
        counts.append(len(ids))
        for r in local:
            source=original[r['manifest_instance_index']]
            assert names[r['object_id']]==Path(source['file']).name
            assert r['source']==source['file'] and r['sha256']==source['sha256']
    assert counts==[10,7,13,13,18,28]==m['plate_counts']
    return {'instances':89,'plate_counts':counts,'queue_sha256':sha(B/'current-print-queue.3mf'),'print_manifest_sha256':sha(B/'print-manifest.json')}

def bambu():
    files=sorted((O/'03-PRINT/Bambu').glob('*.gcode.3mf'))
    assert len(files)==6
    for p in files:
        assert sha(p)==sha(B/'printing-20260926/SD-CARD'/p.name)
    return [{'file':p.name,'sha256':sha(p)} for p in files]

def manual5():
    src=Path('/Users/xiangzheng/Desktop/zhengxia_ECC_0.4_MicroDuck-Centauri-Carbon-sliced_MicroDuck Generic PLA _0.2_51m37s.gcode')
    dst=O/'03-PRINT/Elegoo/MicroDuck_Elegoo_plate_5.gcode'
    assert sha(src)==sha(dst),'Manual plate5 bytes changed'
    return {'desktop_original':str(src),'sha256':sha(src)}

def native_archive():
    provenance=json.loads((O/'native-gui-export-manifest.json').read_text())
    archive=O/'02-PROJECTS/Elegoo/MicroDuck-Elegoo-GUI-all-plates.gcode.3mf'
    assert sha(archive)==provenance['archive_sha256']
    assert sorted(r['plate'] for r in provenance['files'])==list(range(1,7))
    with zipfile.ZipFile(archive) as z:
        for r in provenance['files']:
            target=O/f"03-PRINT/Elegoo/MicroDuck_Elegoo_plate_{r['plate']}.gcode"
            assert str(target)==r['destination'] and str(archive)==r['archive']
            assert target.read_bytes()==z.read(r['archive_member'])
            assert sha(target)==r['sha256']
    return {'archive_sha256':sha(archive),'six_native_members_byte_identical':True,'provenance_sha256':sha(O/'native-gui-export-manifest.json')}

def thumbnail(n):
    p=O/f'03-PRINT/Elegoo/MicroDuck_Elegoo_plate_{n}.gcode'
    assert p.is_file(),f'Native GUI export still missing: {p.name}'
    txt=p.read_text()
    hits=list(re.finditer(r'^; thumbnail begin 144x144 (\d+)\s*\n(.*?)^; thumbnail end\s*$',txt,re.M|re.S))
    assert len(hits)==1,'Expected exactly one native144x144 thumbnail'
    hit=hits[0]
    lines=hit.group(2).splitlines()
    assert all(line.startswith('; ') for line in lines),'Malformed thumbnail comment block'
    encoded=''.join(line[2:].strip() for line in lines)
    assert len(encoded)==int(hit.group(1)),'Declared base64 length mismatch'
    raw=base64.b64decode(encoded,validate=True)
    assert raw.startswith(b'\x89PNG\r\n\x1a\n'),'Thumbnail not PNG'
    im=Image.open(io.BytesIO(raw));im.verify()
    im=Image.open(io.BytesIO(raw));im.load()
    assert im.size==(144,144),im.size
    rgba=im.convert('RGBA');alpha=rgba.getchannel('A')
    assert alpha.getbbox(),'Completely transparent image'
    background=Image.new('RGBA',rgba.size,'white');background.alpha_composite(rgba)
    stats=ImageStat.Stat(background.convert('RGB'))
    assert max(stats.var)>1,'Blank or uniform thumbnail'
    assert re.search(r'^G[01]\s.*[XY].*E',txt,re.M),'Missing extrusion toolpath'
    return {'file':str(p.relative_to(O)),'sha256':sha(p),'bytes':p.stat().st_size,'thumbnail_png_sha256':hashlib.sha256(raw).hexdigest(),'thumbnail_size':[144,144],'thumbnail_base64_length':len(encoded),'pixel_variance':stats.var,'nonblank':True}

check('original99copies',copies)
check('all89STLs_and_plate_mapping',stls)
check('six_Bambu_exports_preserved',bambu)
check('manual_Desktop_plate5_exact_bytes',manual5)
check('six_exports_match_native_GUI_archive',native_archive)
for n in range(1,7):check(f'Elegoo_plate_{n}_native_thumbnail',lambda n=n:thumbnail(n))
passed=not errors
if passed:
    p=O/'README.md';t=p.read_text()
    t=t.replace('Plate 5 is the verified manual GUI export. The other five exports are still being completed; this folder is not yet a complete Elegoo handoff.','All six native exports contain decoded, nonblank 144 × 144 PNG thumbnails. Plate 5 remains byte-identical to the verified manual Desktop export. This confirms export completeness and embedded thumbnails; it does not claim a physical printer test.')
    p.write_text(t)
result={'status':'ORGANIZED_PRINTING_ACCEPTANCE_PASS' if passed else 'ORGANIZED_PRINTING_ACCEPTANCE_PENDING','passed':passed,'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verifier_sha256':sha(Path(__file__)),'scope':'File copies, source preservation, plate assignment and valid nonblank embedded thumbnails. No claim of hardware/firmware rejection or physical printing.','checks':checks,'errors':errors}
(O/'organized-printing-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'passed':passed,'errors':errors},indent=2))
sys.exit(0 if passed else 1)
