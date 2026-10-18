"""Verify the unchanged six-plate source and native SD exports; never edit them."""
from pathlib import Path
import collections
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
import numpy as np

P = Path(__file__).resolve().parent
SOURCE = P.parent / 'current-print-queue.3mf'
FULL = P / 'MicroDuck-current-89-six-plates-sliced.3mf'
NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
PROD = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
EXPECTED = {
    'printer_model': 'Bambu Lab X1 Carbon', 'nozzle_diameter': ['0.4'],
    'curr_bed_type': 'Cool Plate', 'filament_type': ['PLA'],
    'layer_height': '0.2', 'wall_loops': '4', 'sparse_infill_density': '30%',
    'sparse_infill_pattern': 'gyroid', 'enable_support': '1',
    'support_type': 'tree(auto)', 'print_sequence': 'by layer',
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def geometry(file):
    z = zipfile.ZipFile(file)
    assert z.testzip() is None
    cache = {}
    def root(n):
        if n not in cache:
            cache[n] = ET.fromstring(z.read(n))
        return cache[n]
    def transform(s):
        a = np.eye(4)
        if s:
            a[:3, :] = np.array([float(v) for v in s.split()]).reshape(4, 3).T
        return a
    def points(n, oid):
        o = next(x for x in root(n).findall('m:resources/m:object', NS) if x.get('id') == oid)
        v = o.find('m:mesh/m:vertices', NS)
        if v is not None:
            return np.array([[float(x.get(k)) for k in 'xyz'] for x in v])
        result = []
        for c in o.findall('m:components/m:component', NS):
            a = points(c.get(PROD + 'path', n).lstrip('/'), c.get('objectid'))
            t = transform(c.get('transform'))
            result.append(a @ t[:3, :3].T + t[:3, 3])
        return np.vstack(result)
    settings = root('Metadata/model_settings.config')
    names = {o.get('id'): o.find("metadata[@key='name']").get('value') for o in settings.findall('object')}
    by_id = {}
    for b in root('3D/3dmodel.model').findall('m:build/m:item', NS):
        a = points('3D/3dmodel.model', b.get('objectid'))
        t = transform(b.get('transform'))
        by_id[b.get('objectid')] = a @ t[:3, :3].T + t[:3, 3]
    rows = {}
    for pl in settings.findall('plate'):
        n = int(pl.find("metadata[@key='plater_id']").get('value'))
        for inst in pl.findall('model_instance'):
            oid = inst.find("metadata[@key='object_id']").get('value')
            a = by_id[oid]
            key = (n, names[oid], tuple(np.round(a.mean(0), 3)))
            assert key not in rows
            rows[key] = a
    return rows

def main():
    repair = json.loads((P.parent / 'fastener-audit/repaired-cap-3mf-update-verification.json').read_text())
    assert repair['passed'] and repair['unchanged_other_instances'] == 88
    assert repair['target_sha256'] == sha(SOURCE.read_bytes())
    assert repair['stl_sha256'] == sha((P.parent / 'head-cap-usb-service-print.stl').read_bytes())
    assert repair['new_world_vertex_max_abs_error_mm'] < 0.00001
    run = json.loads((P / 'run-command.json').read_text())
    assert sha(SOURCE.read_bytes()) == run['source_sha256']
    src, dst = geometry(SOURCE), geometry(FULL)
    assert src.keys() == dst.keys() and len(src) == 89
    delta = 0.0
    for key, a in src.items():
        b = dst[key]
        assert a.shape == b.shape
        delta = max(delta, float(np.max(np.abs(a - b))))
    assert delta < 0.0001
    counts = [sum(k[0] == n for k in src) for n in range(1, 7)]
    assert counts == [10, 7, 13, 13, 18, 28]
    full_result = json.loads((P / 'result.json').read_text())
    assert full_result['return_code'] == 0 and len(full_result['sliced_plates']) == 6
    assert all(not x['warning_message'] for x in full_result['sliced_plates'])
    native = json.loads((P / 'native-export-results.json').read_text())
    assert len(native) == 6 and all(x['exit_code'] == x['return_code'] == 0 for x in native)
    records = []
    for n in range(1, 7):
        name = f'zhengxia_microduck_plate_{n}.gcode.3mf'
        f = P / 'SD-CARD' / name
        d = P / 'native-exports' / f'plate-{n}'
        assert f.read_bytes() == (d / name).read_bytes()
        command = json.loads((d / 'command.json').read_text())
        assert command[command.index('--arrange') + 1] == '0'
        assert command[command.index('--orient') + 1] == '0'
        assert command[command.index('--slice') + 1] == str(n)
        assert '--min-save' in command and command[-1] == str(SOURCE)
        result = json.loads((d / 'result.json').read_text())
        assert result['return_code'] == 0 and len(result['sliced_plates']) == 1
        plate_result = result['sliced_plates'][0]
        assert plate_result['id'] == n and not plate_result['warning_message']
        expected_names = collections.Counter(k[1] for k in src if k[0] == n)
        assert collections.Counter(x['name'] for x in plate_result['objects']) == expected_names
        z = zipfile.ZipFile(f)
        assert z.testzip() is None
        gn = f'Metadata/plate_{n}.gcode'
        assert [x for x in z.namelist() if x.endswith('.gcode')] == [gn]
        gcode = z.read(gn)
        assert gcode == (d / f'plate_{n}.gcode').read_bytes()
        assert hashlib.md5(gcode).hexdigest().upper() == z.read(gn + '.md5').decode().strip().upper()
        settings = json.loads(z.read('Metadata/project_settings.config'))
        for k, v in EXPECTED.items():
            assert settings[k] == v, (n, k, settings[k])
        text = gcode.decode()
        for k, v in {'printer_model': 'Bambu Lab X1 Carbon', 'curr_bed_type': 'Cool Plate',
                     'filament_type': 'PLA', 'layer_height': '0.2', 'wall_loops': '4',
                     'sparse_infill_density': '30%', 'support_type': 'tree(auto)'}.items():
            assert re.search(r'^; ' + re.escape(k) + ' = ' + re.escape(v) + r'\s*$', text, re.M), (n, k)
        info = ET.fromstring(z.read('Metadata/slice_info.config')).findall('plate')
        assert len(info) == 1
        md = {m.get('key'): m.get('value') for m in info[0].findall('metadata')}
        assert int(md['index']) == n and md['outside'] == 'false' and md['nozzle_diameters'] == '0.4'
        assert collections.Counter(x.get('name') for x in info[0].findall('object')) == expected_names
        assert z.getinfo(f'Metadata/plate_{n}.png').file_size > 0
        records.append({'plate': n, 'file': str(f), 'sha256': sha(f.read_bytes()),
                        'objects': counts[n - 1], 'seconds': int(md['prediction']), 'grams': float(md['weight'])})
    report = {'slice_success': True, 'instances': 89, 'plates': 6, 'placement_preserved': True,
              'maximum_world_vertex_delta_mm': delta, 'sd_files': len(records),
              'profile_verified': True, 'native_export_verified': True, 'profile': EXPECTED,
              'source_sha256': sha(SOURCE.read_bytes()), 'records': records,
              'total_seconds': sum(x['seconds'] for x in records), 'total_grams': sum(x['grams'] for x in records),
              'physical_print_started': False}
    (P / 'handoff-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('PRINT_ACCEPTANCE repaired head cap, 89 instances, six preserved plates, six native SD exports and stored profiles verified')

if __name__ == '__main__':
    main()
