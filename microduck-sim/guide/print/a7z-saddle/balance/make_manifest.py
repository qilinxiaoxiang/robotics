"""Balance manifest for the A7Z roof saddle as built in build/build.json (D-022, 2026-10-22): the as-built manifest with the
head board items removed, the camera as a USB module (estimate), and one saddle module on the torso roof. Positions are
trunk_base-frame metres (the guide world frame). Masses: printed parts from the CAD volumes at 1.24 g/cm3 (PLA), the A7Z
20 g assumed (no published weight), fan 7 g (Adafruit 3368 class), copper 15x15x5 10 g, pad/housings/antenna/screws 8 g.
    ~/.venvs/microduck-dyn/bin/python make_manifest.py   -> manifest-saddle.json (and manifest-today.json copied for the comparison)"""
import json, sys, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent; SLICE = HERE.parents[1] / 'a7z-slice-20261022'
sys.path.insert(0, str(SLICE)); import make_manifests as MM
B = json.loads((HERE.parent / 'build/build.json').read_text())
PLA = 1.24
body_g = B['parts']['saddle_body']['volume_mm3'] / 1000 * PLA; lid_g = B['parts']['saddle_lid']['volume_mm3'] / 1000 * PLA
module_g = body_g + lid_g + MM.A7Z_G + 7.0 + 10.0 + 8.0
m = MM.base()
parts = [p for p in m['parts'] if p['id'] not in MM.HEAD_OUT]
for p in parts:
    if p['id'] == 'add-camera_board':
        p['mass_kg'] = 0.010; p['basis'] = 'estimate'; p['label'] = 'estimate'
        p['source'] = 'USB UVC camera module 32x32 mm (about 5 g board) plus its cable end and a right-angle plug (estimate 10 g)'
# module centre: printed parts about the saddle centre (x -25, z 52), board at z 48, fan at z 68, copper at z 53
parts.append(dict(id='add-a7z-saddle-module', body='trunk_base', mass_kg=module_g / 1000, position_m=[-0.025, 0.0, 0.056],
                  dimensions_m=[0.040, 0.069, 0.032], basis='estimate', label='estimate',
                  source=f'A7Z roof saddle (print/a7z-saddle/build/build.json): body {body_g:.1f} g + lid {lid_g:.1f} g (CAD volume x 1.27), A7Z {MM.A7Z_G:.0f} g assumed, '
                         f'30x30x8 fan 7 g, 15x15x5 copper 10 g, pad/housings/antenna/screws 8 g; {module_g:.0f} g total'))
parts.append(dict(id='add-cable-imu-uart-5v-trunk_base', body='trunk_base', mass_kg=0.004, position_m=[-0.015, 0.0, 0.040],
                  dimensions_m=[0.02, 0.02, 0.02], basis='estimate', label='estimate', source='IMU, J12 UART and 5 V leads end in the saddle (about 4 g over the roof opening)'))
parts.append(dict(id='add-cable-head-bundle-neck', body='neck', mass_kg=0.004, position_m=[-0.002, -0.026, 0.037],
                  dimensions_m=[0.02, 0.02, 0.02], basis='estimate', label='estimate', source='USB camera cable, five amplifier and four XIAO wires down the neck (4 g share)'))
m['parts'] = parts
m['build'] = f'D-022 2026-10-22: A7Z in the roof saddle ({module_g:.0f} g module at x -25, z 56); head without the board, USB camera'
(HERE / 'manifest-saddle.json').write_text(json.dumps(m, indent=1))
shutil.copyfile(SLICE / 'balance/manifest-today.json', HERE / 'manifest-today.json')
print('saddle module g', round(module_g, 1), 'signed mass g', round(sum(p['mass_kg'] for p in parts) * 1000, 1))
