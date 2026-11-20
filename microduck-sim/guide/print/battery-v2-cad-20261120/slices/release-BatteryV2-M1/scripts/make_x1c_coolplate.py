"""X1C file of BatteryV2-M1 for the Cool Plate, the plate Shawn last named for the club X1C (2026-11-12: "我打的那个是cool
plate 换一下"). Copied from extensions/flight-20261110/cad/slices/release-FlightPack-D1/scripts/make_x1c_coolplate.py; this
plate keeps the Orange filament colour the release names (the flight copy recoloured to black for RoboClub's stock).

The release pipeline slices the X1C for the Textured PEI Plate (release_pipeline_v2.MACHINES['Bambu']['bed']). This takes the
pipeline's prepared X1C project of one colour (run/<Colour>_Bambu_editable.3mf: same meshes, process, supports), changes only
the plate type (project curr_bed_type and the plate's bed_type metadata) to "Cool Plate", slices it with the pipeline's Bambu
command and checks the G-code header (printer, plate, cool-plate temperatures) and the preview thumbnail.

    /tmp/microduck-cad-venv/bin/python scripts/make_x1c_coolplate.py <release dir> <Colour>      (under run_bounded_cad.py)
writes <release>/run-x1c-cool/<Colour>/ (editable, sliced.3mf, cli.log, result.json) and
<release>/delivery-x1c-cool/zhengxia_<version>_<Colour>_Bambu-X1C-CoolPlate_<eta>.gcode.3mf
"""
import json, re, shutil, subprocess, sys, zipfile
from pathlib import Path

SIM = Path(__file__).resolve().parents[6]
PIPE = SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'
sys.path.insert(0, str(PIPE))
import release_pipeline_v2 as rp  # noqa: E402

BED = 'Cool Plate'


LABEL = {'Orange': 'Backpack-Orange'}


def main(release, color):
    REL = Path(release).resolve(); VER = REL.name.split('-', 1)[1]
    src = REL / 'run' / f'{color}_Bambu_editable.3mf'
    with zipfile.ZipFile(src) as z: files = {n: z.read(n) for n in z.namelist()}
    cfg = json.loads(files['Metadata/project_settings.config'])
    assert cfg['printer_model'] == 'Bambu Lab X1 Carbon', cfg['printer_model']
    cfg['curr_bed_type'] = BED
    name = LABEL[color]
    cfg['filename_format'] = f'zhengxia_{VER}_{name}_Bambu-X1C-CoolPlate.gcode'
    st = files['Metadata/model_settings.config'].decode()
    st, n = re.subn(r'(<metadata key="bed_type" value=")[^"]*(")', rf'\g<1>{BED}\g<2>', st)
    assert n >= 1, 'no plate bed_type in model_settings.config'
    files['Metadata/project_settings.config'] = json.dumps(cfg, indent=2).encode()
    files['Metadata/model_settings.config'] = st.encode()
    out = REL / 'run-x1c-cool' / color; out.mkdir(parents=True, exist_ok=True)
    ed = out / f'{color}_X1C_CoolPlate_editable.3mf'
    with zipfile.ZipFile(ed, 'w', zipfile.ZIP_DEFLATED) as z:
        for k, b in files.items(): z.writestr(k, b)
    cmd = [rp.MACHINES['Bambu']['exe'], '--allow-newer-file', '--arrange', '0', '--orient', '0', '--slice', '0', '--min-save',
           '--export-3mf', 'sliced.3mf', '--outputdir', str(out), str(ed)]
    with (out / 'cli.log').open('w') as f: r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, timeout=300)
    assert r.returncode == 0, f'native failure {r.returncode}: {out / "cli.log"}'
    arc = out / 'sliced.3mf'; rp.check_bambu_archive(arc)
    g, scfg, imgs = rp.native_payload(arc)
    assert scfg['curr_bed_type'] == BED and scfg['printer_model'] == 'Bambu Lab X1 Carbon', (scfg['curr_bed_type'], scfg['printer_model'])
    assert re.search(rb'; curr_bed_type = Cool Plate\n', g), 'G-code header is not for the Cool Plate'
    temps = {int(v) for v in scfg['cool_plate_temp']} | {int(v) for v in scfg['cool_plate_temp_initial_layer']}
    assert temps and max(temps) <= 45, ('cool plate temperature', temps)
    thumbs = sorted(n for n in imgs if re.search(r'Metadata/plate_\d+\.png$', n)); assert thumbs and len(imgs[thumbs[0]]) > 2000, 'no preview thumbnail'
    errs = [l for l in (out / 'cli.log').read_text().splitlines() if '[error]' in l]
    assert all('ZFiller: encounter idx from clip' in l for l in errs), errs
    secs = rp.time_seconds(g, 'Bambu'); eta = f'{secs // 3600}h{secs % 3600 // 60:02d}m'
    dest = REL / 'delivery-x1c-cool' / f'zhengxia_{VER}_{name}_Bambu-X1C-CoolPlate_{eta}.gcode.3mf'; dest.parent.mkdir(exist_ok=True)
    for old in list(dest.parent.glob(f'zhengxia_{VER}_{name}_Bambu-X1C-CoolPlate_*.gcode.3mf')) + list(dest.parent.glob(f'zhengxia_{VER}_{color}_Bambu-X1C-CoolPlate_*.gcode.3mf')): old.unlink()
    shutil.copyfile(arc, dest); (dest.parent / f'{name}_X1C_CoolPlate_plate.png').write_bytes(imgs[thumbs[0]])
    fil = re.search(rb'total filament weight \[g\] : ([\d.]+)', g)
    res = dict(passed=True, color=color, bed=BED, coolPlateTempC=sorted(temps), estimatedTime=eta,
               filamentGrams=float(fil.group(1)) if fil else None, source=rp.ref(src), archive=rp.ref(arc), delivered=rp.ref(dest), command=cmd)
    rp.write(out / 'result.json', res); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
