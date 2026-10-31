"""V1.39 plate (copied from V1.33) for the club's Bambu Lab H2S (Shawn 2026-10-24: "现在有一台新的Bambu H2S ... 就把黄色部分给它出一个切片文件").

The release pipeline knows the X1C and the Centauri Carbon (256 mm beds). This script takes the pipeline's prepared X1C project
of one colour (run/<Colour>_Bambu_editable.3mf: the same meshes, support blockers and per-object settings) and retargets it:
- the project config: every key of the X1C system presets (machine, process, filament) is replaced by the H2S system preset
  value, or dropped when the H2S presets lack it, as dual-printer/prepare.py retargeted donors in V1.4; then the process keys
  the release donor changed from its system preset (different_settings_to_system[0]: walls, infill, shells, tree supports, brim)
  are set again to the donor values. Machine "Bambu Lab H2S 0.4 nozzle", process "0.20mm Standard @BBL H2S", filament
  "Generic PLA @BBL H2S" (220 C nozzle, 55 C textured plate, 12 mm3/s: inside Overture SUPER PLA+'s 190-230 C and 25-60 C),
  bed "Textured PEI Plate" (the H2S default plate);
- the plate: every build item moves by the bed-centre difference, (170, 160) - (128, 128), so the plate stays centred.
It slices with the pipeline's Bambu command (--min-save, so Bambu Studio opens the file on Preview) and the pipeline's archive
check, then checks the H2S config, the bed bounds and the preview thumbnail.

    /tmp/microduck-cad-venv/bin/python scripts/make_h2s.py run/preparation.json Yellow     (under run_bounded_cad.py)
writes run-h2s/<Colour>/ (editable project, sliced.3mf, cli.log, result.json) and
delivery-h2s/zhengxia_V1.39_<Colour>_Bambu-H2S_<eta>.gcode.3mf"""
import hashlib, json, re, shutil, subprocess, sys, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np

REL = Path(__file__).resolve().parents[1]; SIM = REL.parents[2]
PIPE = SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'
sys.path.insert(0, str(PIPE))
import release_pipeline_v2 as rp  # noqa: E402

BBL = Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL')
X1C = ('Bambu Lab X1 Carbon 0.4 nozzle', '0.20mm Standard @BBL X1C', 'Bambu PLA Basic @BBL X1C')
H2S = ('Bambu Lab H2S 0.4 nozzle', '0.20mm Standard @BBL H2S', 'Generic PLA @BBL H2S')
BED = 'Textured PEI Plate'; BED_XY = (340.0, 320.0); MARGIN = 18.0
PROC_KEYS = ('wall_loops', 'sparse_infill_density', 'sparse_infill_pattern', 'top_shell_layers', 'bottom_shell_layers', 'enable_support',
             'support_type', 'support_on_build_plate_only', 'support_threshold_angle', 'support_style', 'brim_type', 'brim_width')   # V1.33 run-h2s result
META = {'name', 'type', 'from', 'inherits', 'include', 'instantiation', 'version', 'setting_id', 'filament_colour', 'description'}


def resolve(name, domain):
    x = json.loads((BBL / domain / f'{name}.json').read_text()); o = {}
    if x.get('inherits'): o.update(resolve(x['inherits'], domain))
    for n in x.get('include', []): o.update(resolve(n, domain))
    o.update(x); return o


def presets(names):
    return [resolve(n, d) for n, d in zip(names, ('machine', 'process', 'filament'))]


def retarget(cfg):
    old, new = presets(X1C), presets(H2S)
    keys = (set().union(*old) | set().union(*new)) - META
    tgt = {}
    for d in new: tgt.update({k: v for k, v in d.items() if k not in META})
    out = dict(cfg)
    for k in keys:
        if k in tgt: out[k] = tgt[k]
        else: out.pop(k, None)
    if 'different_settings_to_system' in cfg:
        proc_delta = [k for k in cfg['different_settings_to_system'][0].split(';') if k]
    else:   # V1.39: the Orange donor project carries no delta list (its process derives from an Elegoo CC preset), so only
            # the design keys V1.33 carried over (walls, infill, shells, supports, brim) are taken, never its speeds
        proc_delta = [k for k in PROC_KEYS if k in cfg]
    for k in proc_delta: out[k] = cfg[k]
    out.update(printer_settings_id=H2S[0], print_settings_id='MicroDuck ' + H2S[1], filament_settings_id=[H2S[2]], inherits_group=[H2S[1], H2S[2], H2S[0]],
               different_settings_to_system=[';'.join(proc_delta), '', ''], curr_bed_type=BED, filament_colour=cfg['filament_colour'],
               filament_ids=[new[2]['filament_id']], print_compatible_printers=new[1]['compatible_printers'])
    out.pop('compatible_printers', None)       # a project carries the process list as print_compatible_printers (the CLI checks it)
    return rp.bambu_self_index(out), proc_delta


def check_h2s(cfg):
    assert cfg['printer_model'] == 'Bambu Lab H2S' and cfg['curr_bed_type'] == BED, (cfg['printer_model'], cfg['curr_bed_type'])
    assert cfg['printable_area'] == ['0x0', '340x0', '340x320', '0x320'] and cfg['nozzle_diameter'] == ['0.4'] and cfg['filament_type'] == ['PLA']
    t = {int(v) for v in cfg['nozzle_temperature']} | {int(v) for v in cfg['nozzle_temperature_initial_layer']}
    b = {int(v) for v in cfg['textured_plate_temp']} | {int(v) for v in cfg['textured_plate_temp_initial_layer']}
    assert t <= set(range(190, 231)) and b <= set(range(25, 61)), ('outside Overture SUPER PLA+ ranges', t, b)


def main(prep_path, color):
    prep = rp.read(prep_path); row = next(r for r in prep['rows'] if r['color'] == color and r['machine'] == 'Bambu')
    project = rp.bound(row['project'])
    with zipfile.ZipFile(project) as z: files = {n: z.read(n) for n in z.namelist()}
    cfg, delta = retarget(json.loads(files['Metadata/project_settings.config']))
    cfg['filename_format'] = f'zhengxia_{prep["version"] if "version" in prep else "V1.39"}_{color}_Bambu-H2S.gcode'
    check_h2s(cfg)
    shift = np.array([BED_XY[0] / 2 - 128, BED_XY[1] / 2 - 128, 0])
    model = ET.fromstring(files['3D/3dmodel.model'])
    for it in model.iter(rp.Q + 'item'):
        v = np.array(it.get('transform').split(), float); v[9:12] += shift; it.set('transform', ' '.join(format(x, '.15g') for x in v))
    bounds = np.array(row['modelBounds']) + shift
    assert bounds[:, 0, :2].min() >= MARGIN and bounds[:, 1, 0].max() <= BED_XY[0] - MARGIN and bounds[:, 1, 1].max() <= BED_XY[1] - MARGIN, 'off the H2S bed'
    centre = (bounds[:, 0, :2].min(0) + bounds[:, 1, :2].max(0)) / 2 - np.array(BED_XY) / 2
    assert np.all(np.abs(centre) <= rp.PLATE_CENTRE_TOL_MM), centre
    st = ET.fromstring(files['Metadata/model_settings.config'])
    for md in st.iter('metadata'):
        if md.get('key') == 'bed_type': md.set('value', BED)
    files.update({'3D/3dmodel.model': ET.tostring(model, encoding='utf-8', xml_declaration=True),
                  'Metadata/model_settings.config': ET.tostring(st, encoding='utf-8', xml_declaration=True),
                  'Metadata/project_settings.config': json.dumps(cfg, indent=2).encode()})
    out = REL / 'run-h2s' / color; out.mkdir(parents=True, exist_ok=True)
    ed = out / f'{color}_H2S_editable.3mf'
    with zipfile.ZipFile(ed, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, b in files.items(): z.writestr(n, b)
    cmd = [rp.MACHINES['Bambu']['exe'], '--allow-newer-file', '--arrange', '0', '--orient', '0', '--slice', '0', '--min-save',
           '--export-3mf', 'sliced.3mf', '--outputdir', str(out), str(ed)]
    with (out / 'cli.log').open('w') as f: r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, timeout=300)
    assert r.returncode == 0, f'native failure {r.returncode}: {out / "cli.log"}'
    arc = out / 'sliced.3mf'; rp.check_bambu_archive(arc)
    g, scfg, imgs = rp.native_payload(arc); check_h2s(scfg)
    assert b'G1 ' in g and re.search(rb'printer_model = Bambu Lab H2S', g), 'G-code header is not for the H2S'
    body = g[g.index(b'; MACHINE_START_GCODE_END'):g.index(b'; MACHINE_END_GCODE_START')]   # the start G-code purges at Y -0.5 by design
    xy = np.array([(float(a), float(b)) for a, b in re.findall(rb'G1 [^\n;]*X([-\d.]+) Y([-\d.]+)[^\n;]*E[\d.]', body)])
    errs = [l for l in (out / 'cli.log').read_text().splitlines() if '[error]' in l]
    # Bambu's H2S end G-code returns the filament to the AMS with "M620 S65535 / T65535 / M621 S65535"; the CLI's G-code
    # processor logs that T as invalid. "ZFiller: encounter idx from clip" comes from the multithreaded clipper and appears on
    # some runs of the same project only (2026-10-24: two slices of one project differed in one loop start at z 5.6 and nothing
    # else). Any other error line stops the delivery.
    assert all('Invalid T command (T65535)' in l or 'ZFiller: encounter idx from clip' in l for l in errs), errs
    lo, hi = xy.min(0), xy.max(0); assert lo.min() >= 0 and hi[0] <= BED_XY[0] and hi[1] <= BED_XY[1], (lo, hi)
    thumbs = sorted(n for n in imgs if re.search(r'Metadata/plate_\d+\.png$', n)); assert thumbs and len(imgs[thumbs[0]]) > 2000, 'no preview thumbnail'
    secs = rp.time_seconds(g, 'Bambu'); eta = f'{secs // 3600}h{secs % 3600 // 60:02d}m'
    dest = REL / 'delivery-h2s' / f'zhengxia_V1.39_{color}_Bambu-H2S_{eta}.gcode.3mf'; dest.parent.mkdir(exist_ok=True)
    for old in dest.parent.glob(f'zhengxia_V1.39_{color}_Bambu-H2S_*.gcode.3mf'): old.unlink()
    shutil.copyfile(arc, dest); (dest.parent / f'{color}_H2S_plate.png').write_bytes(imgs[thumbs[0]])
    fil = re.search(rb'total filament weight \[g\] : ([\d.]+)', g) or re.search(rb'filament used \[g\] = ([\d.]+)', g)
    res = dict(passed=True, color=color, machine=H2S[0], process=H2S[1], filament=H2S[2], bed=BED, processKeysFromRelease=delta,
               shiftMm=shift[:2].tolist(), extrusionXYBoundsMm=[lo.round(2).tolist(), hi.round(2).tolist()], estimatedTime=eta,
               filamentGrams=float(fil.group(1)) if fil else None, cliErrorLines=errs, source=rp.ref(project), archive=rp.ref(arc), delivered=rp.ref(dest), command=cmd)
    rp.write(out / 'result.json', res); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
