"""Write one reviewed Elegoo machine file before full packaging, using the same thumbnail rule as release_pipeline.package
(Bambu native preview of the identical layout prepended; Elegoo command stream byte-identical)."""
import sys, io, base64, json, math; sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009')
import release_pipeline as r
from pathlib import Path
from PIL import Image
R = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/release-V1.6')
color = sys.argv[1]
rev = r.read(R / f'review/{color}_Elegoo-review.json'); assert rev['passed']
res = r.read(R / f'run/native/{color}_Elegoo/result.json'); g, cfg, imgs = r.native_payload(r.bound(res['archive'])); assert r.digest(g) == res['gcodeSha256'] == rev['gcodeSha256']
assert b'thumbnail begin' not in g and 'Metadata/plate_1.png' not in imgs
prep = r.read(R / 'run/preparation.json'); rows = {(x['color'], x['machine']): x for x in prep['rows']}; assert rows[(color, 'Bambu')]['placements'] == rows[(color, 'Elegoo')]['placements']
pr = r.read(R / f'run/native/{color}_Bambu/result.json'); _, _, bimgs = r.native_payload(r.bound(pr['archive'])); png = bimgs['Metadata/plate_1.png']; im = Image.open(io.BytesIO(png)).convert('RGB')
enc = base64.b64encode(png).decode(); prefix = f'; thumbnail begin {im.width}x{im.height} {len(enc)}\n' + '\n'.join('; ' + enc[i:i + 78] for i in range(0, len(enc), 78)) + '\n; thumbnail end\n\n'
payload = prefix.encode() + g; assert payload.endswith(g)
secs = r.time_seconds(g, 'Elegoo'); minutes = math.ceil(secs / 60); label = (f'{minutes // 60}h' if minutes >= 60 else '') + f'{minutes % 60}m'
dest = R / f'zhengxia_V1.6_{color}_Elegoo-Centauri-Carbon_{label}.gcode'; dest.write_bytes(payload)
print(json.dumps(dict(path=str(dest), sha256=r.sha(dest), estimatedSeconds=secs, label=label, grams=rev['filamentGrams'], thumbnailFromBambuArchive=pr['archive']['path'])))
