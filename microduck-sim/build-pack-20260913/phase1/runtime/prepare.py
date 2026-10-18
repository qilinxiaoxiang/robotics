# SPDX-License-Identifier: MIT
"""Create a self-contained bundle from frozen local community + 61D sources."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
# Canonical shared jaw/head-pitch limits; copied into every bundle, never edited here.
LIMITS = HERE.parents[2]/'guide'/'firmware'/'pi'

def build(community, overlay, destination):
    community, overlay, destination = map(lambda p: Path(p).resolve(), (community, overlay, destination))
    if destination.exists():
        raise RuntimeError('Destination already exists; preserve it and choose a new empty path')
    lock = json.loads((overlay/'source-lock.json').read_text())
    for source, expected in lock['source_files_sha256'].items():
        relative = source.split('/microduck/src/', 1)[1]
        if hashlib.sha256((community/'src'/relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Frozen source mismatch: '+relative)
    destination.mkdir(parents=True)
    for name in ('phase1.py', 'assign_id.py', 'core.py', 'policy.py', 'imu_mount.py', 'imu_calibrate.py', 'torso_imu.py', 'compensation.py', 'runtime_compensation.py', 'mac_control.py', 'requirements.txt', 'LICENSE', 'README.md', 'calibration.template.json'):
        shutil.copy2(HERE/name, destination/name)
    for name in ('jaw_limits.py', 'jaw_limits.json', 'jaw_pose_caps.json'):
        shutil.copy2(LIMITS/name, destination/name)
    src = destination/'community/src'
    src.mkdir(parents=True)
    # Real community modules; no unused simulator, old robot meshes, daemon or placo dependency.
    for relative in ('constants.py','robot_controller.py','observer.py','controller.py','imu_reader.py',
                     'input/input_source.py','input/__init__.py','moves/move.py','moves/__init__.py','moves/walk.py'):
        (src/relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(community/'src'/relative, src/relative)
    spec = importlib.util.spec_from_file_location('overlay_installer', overlay/'install.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.install(destination/'community')
    shutil.copy2(community.parent/'LICENSE', destination/'COMMUNITY-LICENSE')
    shutil.copy2(overlay/'LICENSE', destination/'OVERLAY-LICENSE')
    manifest = {'community_commit': lock['community_commit'], 'policy_commit': lock['official_policy_commit'],
                'models':lock['models_sha256'], 'files':{}}
    for p in sorted(destination.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            manifest['files'][str(p.relative_to(destination))] = hashlib.sha256(p.read_bytes()).hexdigest()
    (destination/'bundle-lock.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--community',required=True);p.add_argument('--overlay',required=True)
    p.add_argument('--destination',required=True);a=p.parse_args();m=build(a.community,a.overlay,a.destination)
    print(json.dumps({'files':len(m['files']), 'destination':a.destination, 'hardware_opened':False}))
