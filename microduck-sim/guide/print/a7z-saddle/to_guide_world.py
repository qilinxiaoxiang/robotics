"""Copy the A7Z saddle (D-022) into guide/print/world for build_guide_data.py and the print gate.
Run after build_saddle.py. The printed body and lid keep their names; the bought parts in the saddle pose get the sd_ prefix
(the head-pose a7z_*.stl, antenna*.stl, camera_board.stl and camera_ribbon.stl stay in print/world for the record: the
guide no longer registers them, see build_guide_data.py).
    /tmp/microduck-cad-venv/bin/python to_guide_world.py"""
import hashlib, json, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent; B = HERE / 'build'
WORLD = HERE.parents[0] / 'world'
BOUGHT = ['a7z_pcb', 'soc_a733', 'ram', 'pmic_area', 'wifi_module_fcu760k', 'usb_c_otg_dp', 'usb_c_power', 'micro_hdmi', 'fan_connector',
          'ipex_socket', 'microsd_socket', 'microsd_card', 'csi_connector', 'pcie_fpc', 'uboot_button', 'underside_smd',
          'heatsink', 'thermal_pad', 'fan', 'dupont_housings', 'antenna', 'usb_c_plug']
COPY = {'saddle_body.stl': B / 'saddle_body-world.stl', 'saddle_lid.stl': B / 'saddle_lid-world.stl'}
COPY.update({f'sd_{n}.stl': B / f'{n}-world.stl' for n in BOUGHT})
out = {}
for name, src in COPY.items():
    shutil.copyfile(src, WORLD / name)
    out[name] = str(src)
sha = {n: hashlib.sha256((WORLD / n).read_bytes()).hexdigest() for n in out}
(HERE / 'guide-world.json').write_text(json.dumps({'world': str(WORLD), 'sources': out, 'sha256': sha,
                                                   'buildJson': hashlib.sha256((B / 'build.json').read_bytes()).hexdigest()}, indent=1) + '\n')
print(WORLD, len(out), 'files', {n: s[:12] for n, s in sha.items() if not n.startswith('sd_')})
