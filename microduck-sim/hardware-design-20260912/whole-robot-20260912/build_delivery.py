"""Package the frozen current design, final experiments, and reproducible sources."""
from pathlib import Path
import hashlib
import json
import zipfile
import shutil

W = Path(__file__).resolve().parent
A = W.parent
SIM = A.parent

licenses = W / 'licenses'
licenses.mkdir(exist_ok=True)
for src, name in [
    (SIM / 'microduck_rl/LICENSE', 'microduck_rl-LICENSE'),
    (SIM / 'Microduck-build-tutorial/LICENSE', 'community-root-LICENSE'),
    (SIM / 'Microduck-build-tutorial/microduck/LICENSE', 'community-controller-LICENSE'),
    (A / 'reference/microduck/cad/LICENSE', 'original-CAD-LICENSE'),
]:
    shutil.copyfile(src, licenses / name)

lockfile = W / 'runtime-overlay/source-lock.json'
lock = json.loads(lockfile.read_text())
for rel in lock['overlay_files_sha256']:
    lock['overlay_files_sha256'][rel] = hashlib.sha256((lockfile.parent / rel).read_bytes()).hexdigest()
lockfile.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n')

selected = set()
def add_tree(root):
    for p in root.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.name != '.DS_Store' and not p.name.endswith('.log'):
            selected.add(p)

for name in ['assembly', 'electrical', 'runtime-overlay', 'licenses', 'delay-repair-20260912']:
    add_tree(W / name)
for name in ['camera', 'reference', 'roboclub']:
    add_tree(A / name)
selected.add(A / 'audio-power/REPORT.md')
for p in (A / 'slicing').iterdir():
    if p.suffix == '.py' or p.name in ['machine.json', 'filament.json', 'process.json', 'head-process.json']:
        selected.add(p)
for p in W.iterdir():
    if p.is_file() and (p.suffix in ['.py', '.md'] or p.name == 'final-delivery-verification.json'):
        selected.add(p)
for p in (W / 'printing').rglob('*'):
    if p.is_file() and (p.name.startswith('MicroDuck-') or p.suffix == '.stl' or p.suffix == '.json'):
        selected.add(p)
for p in (W / 'dynamics').iterdir():
    if not p.is_file():
        continue
    if (p.suffix in ['.py', '.txt', '.obj', '.mp4', '.png'] or
            p.name.startswith('final-') or 'summary' in p.name or
            p.name in ['source-lock.json', 'full-mass-base.json', 'full-geometry.json']):
        selected.add(p)

manifest = {
    'verified_date': '2026-09-12',
    'scope': 'Current eight printable additions; original 43/45 baseline, repaired 45/45 at unchanged gates, and retained additional failures; no physical robot acceptance.',
    'files_sha256': {str(p.relative_to(A)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(selected)},
}
manifest_path = W / 'delivery-manifest.json'
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
selected.add(manifest_path)
dest = A / 'MicroDuck-whole-assembly-20260912.zip'
entry = ('# 当前整机设计包\n\n'
         '请先读 [装配与验收范围](whole-robot-20260912/README.md)。'
         '两个以 MicroDuck- 开头的 Bambu 工程共含 8 个新增打印件；原鸭子的其他打印件仍来自固定版本的上游仓库。\n\n'
         '当前整机不使用旧版外置背包打印盘。assembly 和 electrical 中其余网格包括原件、空间预留和检查参考，'
         '不要把所有 STL 都送去打印。\n\n'
         'dynamics/ 保留原43/45基线；delay-repair-20260912/ 包含相同门槛下修复后的45/45、额外60ms全部跌倒和停车方向保持限制。'
         '补偿尚未接入机载程序，不能将仿真延迟直接写死为真实延迟。早期探索保留摘要与必要几何检查记录。'
         '复现环境见 [REPRODUCE](whole-robot-20260912/REPRODUCE.md)。'
         '文件校验值见 whole-robot-20260912/delivery-manifest.json。\n')
with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    archive.writestr(A.name + '/README.md', entry)
    for p in sorted(selected):
        archive.write(p, A.name + '/' + str(p.relative_to(A)))
with zipfile.ZipFile(dest) as archive:
    assert archive.testzip() is None
    for rel, digest in manifest['files_sha256'].items():
        assert hashlib.sha256(archive.read(A.name + '/' + rel)).hexdigest() == digest, rel
print(json.dumps({'file': str(dest), 'files': len(selected) + 1, 'bytes': dest.stat().st_size,
                  'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(), 'crc_and_hashes': 'passed'}))
