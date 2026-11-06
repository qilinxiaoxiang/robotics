#!/usr/bin/env python3
"""Copy a pinned guide-kit version into a consumer repository, and check that copy.

    python3 ~/code/robotics/guide-kit/scripts/sync_guide_kit.py sync  --dest <consumer>/vendor/guide-kit [--ref <commit>]
    python3 <consumer>/vendor/guide-kit/check_guide_kit.py [--kit ~/code/robotics]       # in the consumer's build/CI

`sync` writes the kit files exactly as committed at --ref (default HEAD of ~/code/robotics; uncommitted kit edits
are never shipped), replaces whatever was in --dest, and writes KIT-MANIFEST.json (kit commit and each file's
sha256) plus check_guide_kit.py. The vendored copy is read-only by contract: a consumer change goes into the kit,
is committed there, and is synced again.

`check` (check_guide_kit.py, standard library only, no kit checkout needed) fails when a vendored file differs from
its manifest hash, a manifest file is missing, or an extra file sits in the vendor directory. With --kit <repo> it
also fails when the manifest commit's files differ from that repository's copy at the same commit (a hand-edited
manifest), and reports how many commits the pin is behind.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
REPO = KIT.parent
PREFIX = 'guide-kit/'
SHIP = ('build_guide.py', 'README.md', 'requirements-audit.txt', 'viewer/', 'three/', 'audit/')
MANIFEST = 'KIT-MANIFEST.json'
CHECKER = 'check_guide_kit.py'


def git(*args: str, binary=False):
    out = subprocess.run(['git', '-C', str(REPO), *args], capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode().strip()


def shipped_files(ref: str) -> list[str]:
    names = git('ls-tree', '-r', '--name-only', ref, '--', PREFIX).splitlines()
    rel = [n[len(PREFIX):] for n in names]
    return sorted(r for r in rel if any(r == s or (s.endswith('/') and r.startswith(s)) for s in SHIP) and '__pycache__' not in r)


def sync(dest: Path, ref: str) -> int:
    commit = git('rev-parse', ref)
    files = shipped_files(commit)
    if not files:
        raise SystemExit(f'no guide-kit files at {commit}')
    dest = dest.resolve()
    if dest == KIT or KIT in dest.parents:
        raise SystemExit('dest must be outside the kit')
    if dest.exists():
        shutil.rmtree(dest)
    hashes = {}
    for r in files:
        data = git('show', f'{commit}:{PREFIX}{r}', binary=True)
        p = dest / r
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        hashes[r] = hashlib.sha256(data).hexdigest()
    checker = Path(__file__).read_bytes()
    (dest / CHECKER).write_bytes(checker)
    manifest = {'kit': 'robotics/guide-kit', 'commit': commit, 'files': hashes,
                'checker_sha256': hashlib.sha256(checker).hexdigest(),
                'rule': 'read-only copy; change the kit, commit it, then rerun sync'}
    (dest / MANIFEST).write_text(json.dumps(manifest, indent=1) + '\n')
    print(json.dumps({'dest': str(dest), 'commit': commit, 'files': len(hashes)}))
    return 0


def check(dest: Path, kit_repo: Path | None) -> int:
    m = json.loads((dest / MANIFEST).read_text())
    problems = []
    for r, h in m['files'].items():
        p = dest / r
        if not p.is_file():
            problems.append(f'missing {r}')
        elif hashlib.sha256(p.read_bytes()).hexdigest() != h:
            problems.append(f'edited {r} (differs from guide-kit {m["commit"][:12]}; change the kit and resync)')
    allowed = set(m['files']) | {MANIFEST, CHECKER}
    for p in dest.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            r = p.relative_to(dest).as_posix()
            if r not in allowed:
                problems.append(f'extra {r} (not in the kit)')
    if hashlib.sha256((dest / CHECKER).read_bytes()).hexdigest() != m.get('checker_sha256'):
        problems.append(f'edited {CHECKER}')
    behind = None
    if kit_repo:
        g = lambda *a, b=False: subprocess.run(['git', '-C', str(kit_repo), *a], capture_output=True, check=True).stdout
        for r, h in m['files'].items():
            if hashlib.sha256(g('show', f'{m["commit"]}:{PREFIX}{r}', b=True)).hexdigest() != h:
                problems.append(f'manifest hash for {r} does not match guide-kit at {m["commit"][:12]}')
        behind = int(g('rev-list', '--count', f'{m["commit"]}..HEAD', '--', PREFIX).decode().strip() or 0)
    print(json.dumps({'dest': str(dest), 'commit': m['commit'], 'files': len(m['files']), 'problems': problems,
                      'kitCommitsAhead': behind}))
    return 1 if problems else 0


def main(argv=None) -> int:
    here = Path(__file__).resolve().parent
    if (here / MANIFEST).exists() and here.name != 'scripts':
        # running as the vendored check_guide_kit.py
        ap = argparse.ArgumentParser(description='check a vendored guide-kit copy against its manifest')
        ap.add_argument('--kit', type=Path, help='robotics checkout to compare the pinned commit against')
        a = ap.parse_args(argv)
        return check(here, a.kit)
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('sync'); s.add_argument('--dest', required=True, type=Path); s.add_argument('--ref', default='HEAD')
    c = sub.add_parser('check'); c.add_argument('--dest', required=True, type=Path); c.add_argument('--kit', type=Path, default=REPO)
    a = ap.parse_args(argv)
    return sync(a.dest, a.ref) if a.cmd == 'sync' else check(a.dest, a.kit)


if __name__ == '__main__':
    sys.exit(main())
