#!/usr/bin/env python3
"""Confirms the study left V1.8 untouched: sha256 of every file listed in guide/print/world/v18-sources.json against
its recorded hash, plus the git status of the protected paths (read-only `git status --porcelain`). Writes
../v18-unchanged.json.
"""
import hashlib
import json
import subprocess

import int_lib as L

GUIDE = L.EXT.parent
WORLD = GUIDE / 'print' / 'world'
PROTECTED = ['microduck-sim/guide/print', 'microduck-sim/guide/content/routes.json', 'microduck-sim/guide/data',
             'microduck-sim/build-pack-20260913']


def main():
    src = json.loads((WORLD / 'v18-sources.json').read_text())['files']
    files = {}
    for f, r in src.items():
        now = hashlib.sha256((WORLD / f).read_bytes()).hexdigest()
        files[f] = {'unchanged': now == r.get('sha256')}
    root = GUIDE.parent.parent
    st = subprocess.run(['git', 'status', '--porcelain', '--', *PROTECTED], cwd=root, capture_output=True, text=True).stdout
    out = {'_method': __doc__.strip(), 'v18FilesUnchanged': all(v['unchanged'] for v in files.values()),
           'files': files, 'gitStatusOfProtectedPaths': st.splitlines()}
    L.jdump(out, L.STUDY / 'v18-unchanged.json')
    print(out['v18FilesUnchanged'], len(files), out['gitStatusOfProtectedPaths'])


if __name__ == '__main__':
    main()
