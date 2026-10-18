"""Dry run of release_pipeline.package for V1.10 without writing delivery/, the SD ZIP or any receipt the package step
owns. It replays the same bindings and checks (result/command/project binding, native first layer and bed footprint,
ETA filename label, Centauri Carbon preview insertion and firmware-rule replay, native-review receipt binding) and
writes run/native-delivery-precheck.json. Optionally writes the would-be Elegoo payload for an independent line check.

    /tmp/microduck-cad-venv/bin/python scripts/precheck_delivery.py run [--elegoo-payload OUT.gcode]
"""
import argparse, io, json, math, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009')
import release_pipeline as r  # noqa: E402


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('run'); ap.add_argument('--elegoo-payload', type=Path); a = ap.parse_args()
    from PIL import Image, ImageStat
    p = (Path(a.run) / 'preparation.json').resolve(); prep = r.read(p); manifest = r.bound(prep['manifest'])
    m, check = r.source_receipt(manifest); assert check['parts'] == prep['parts']; r.bound(prep['pipeline'])
    assert not (p.parent / 'delivery').exists(), 'delivery/ already exists; package would refuse'
    rows = []
    for row in prep['rows']:
        color, machine = row['color'], row['machine']; project = r.bound(row['project'])
        resultp = p.parent / 'native' / f'{color}_{machine}' / 'result.json'; result = r.read(resultp)
        assert result['passed'] and result['preparation'] == r.ref(p) and result['project'] == r.ref(project)
        command = r.read(r.bound(result['command'])); assert command['preparation'] == r.ref(p) and command['project'] == r.ref(project)
        for extra in command['extraProfiles']: r.bound(extra)
        source = r.bound(result['archive']); g, cfg, imgs = r.native_payload(source); assert r.digest(g) == result['gcodeSha256']; r.check_profile(cfg, machine)
        first, foot = r.first_layer(g, project, machine)
        assert len(first) == sum(x['quantity'] for x in prep['parts'] if x['color'] == color), 'Slicer lost or added model objects'
        seconds = r.time_seconds(g, machine); minutes = math.ceil(seconds / 60); label = (f'{minutes // 60}h' if minutes >= 60 else '') + f'{minutes % 60}m'
        name = f'zhengxia_{m["version"]}_{color}_{r.MACHINES[machine]["slug"]}_{label}' + ('.gcode.3mf' if machine == 'Bambu' else '.gcode')
        preview_source = source
        if machine == 'Elegoo' and 'Metadata/plate_1.png' not in imgs:
            peer = next(x for x in prep['rows'] if x['color'] == color and x['machine'] == 'Bambu'); assert peer['placements'] == row['placements']
            pr = r.read(p.parent / 'native' / f'{color}_Bambu/result.json'); assert pr['preparation'] == r.ref(p)
            preview_source = r.bound(pr['archive']); _, _, imgs = r.native_payload(preview_source)
        png = imgs['Metadata/plate_1.png']; im = Image.open(io.BytesIO(png)).convert('RGB')
        assert min(im.size) >= 100 and max(ImageStat.Stat(im).stddev) > 2, 'Blank thumbnail'
        entry = dict(color=color, machine=machine, filename=name, estimatedSeconds=seconds, estimatedTime=label,
                     nativeArchive=r.ref(source), nativeCommandStreamSha256=r.digest(g), nativeFirstLayer=first, nativeFootprint=foot,
                     thumbnailSource=r.ref(preview_source), thumbnailSha256=r.digest(png))
        if machine == 'Elegoo':
            payload = g if b'thumbnail begin' in g else r.cc_preview(g, png); cc = r.check_cc_preview(payload, g)
            lines = payload.split(b'\n')
            header_end = next(i for i, l in enumerate(lines, 1) if l.startswith(b'; HEADER_BLOCK_END'))
            block_start = next(i for i, l in enumerate(lines, 1) if l.startswith(b'; THUMBNAIL_BLOCK_START'))
            block_end = next(i for i, l in enumerate(lines, 1) if l.startswith(b'; THUMBNAIL_BLOCK_END'))
            first_cmd = next(i for i, l in enumerate(lines, 1) if l[:1] in (b'G', b'M', b'g', b'm'))
            assert cc['slicerLine'] <= r.CC_SLICER_LINES and header_end < block_start < cc['previewLine'] < block_end < first_cmd
            entry['centauriCarbonPreview'] = dict(cc, slicerLineText=lines[cc['slicerLine'] - 1].decode(errors='replace'),
                                                  headerBlockEndLine=header_end, thumbnailBlockStartLine=block_start,
                                                  thumbnailBlockEndLine=block_end, firstGMCommandLine=first_cmd,
                                                  firstGMCommandText=lines[first_cmd - 1].decode(errors='replace')[:60],
                                                  payloadSha256=r.digest(payload), payloadBytes=len(payload))
            if a.elegoo_payload: a.elegoo_payload.write_bytes(payload)
        rows.append(entry)
    rv_path = p.parent / 'native-review.json'; rv = r.read(rv_path)
    assert rv['passed'] and rv['preparationSha256'] == r.sha(p)
    assert rv['nativeArchives'] == {str(r.bound(r.read(p.parent / 'native' / f'{x["color"]}_{x["machine"]}/result.json')['archive'])):
                                    r.sha(r.bound(r.read(p.parent / 'native' / f'{x["color"]}_{x["machine"]}/result.json')['archive'])) for x in prep['rows']}
    out = dict(passed=True, status='PRE_PACKAGE_DRY_RUN', preparation=r.ref(p), manifest=r.ref(manifest), nativeReview=r.ref(rv_path),
               statusPackageWouldWrite='RELEASED', checks=rows,
               claimBoundary=('Replays release_pipeline.package checks; writes no delivery file, ZIP, delivery-index, incremental-audit, '
                              'native-delivery-checks or package-receipt. The package step itself writes native-delivery-checks.json.'))
    r.write(p.parent / 'native-delivery-precheck.json', out)
    print(json.dumps([dict(machine=x['machine'], filename=x['filename'], seconds=x['estimatedSeconds'], cc=x.get('centauriCarbonPreview', {}).get('slicerLine'),
                           firstLayer={f['name']: round(f['model_area_mm2'], 2) for f in x['nativeFirstLayer']}) for x in rows], indent=1))
    for x in rows:
        if 'centauriCarbonPreview' in x: print(json.dumps({k: v for k, v in x['centauriCarbonPreview'].items()}, indent=1))


if __name__ == '__main__':
    main()
