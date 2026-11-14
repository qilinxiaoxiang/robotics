"""Keep /Applications/OrcaSlicer.app on the newest stable OrcaSlicer release.

    python3 update_orca.py            # update if a newer stable release exists
    python3 update_orca.py --check    # only report

Shawn 2026-11-14: "以后每次你看到有更新，就帮我更新一下". Slicing scripts call this before they slice
(native_slice.ensure_latest_orca). Source: the GitHub releases of OrcaSlicer/OrcaSlicer, newest non-prerelease,
non-draft tag with a Mac universal DMG. The new app must pass codesign --deep --strict and Gatekeeper (notarized
Developer ID) with the same team ID as the installed app, or nothing is replaced. A running OrcaSlicer is asked to
quit normally; if it stays open (unsaved project dialog), the update stops and says so. The old app goes to the Trash.
Each run appends one line to ~/Library/Logs/update_orca.jsonl.
"""
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

APP = Path('/Applications/OrcaSlicer.app')
API = 'https://api.github.com/repos/OrcaSlicer/OrcaSlicer/releases?per_page=10'
LOG = Path.home() / 'Library/Logs/update_orca.jsonl'


def vtuple(s):
    return tuple(int(x) for x in re.findall(r'\d+', s)[:3])


def installed():
    if not APP.exists():
        return None
    out = subprocess.run(['defaults', 'read', str(APP / 'Contents/Info.plist'), 'CFBundleShortVersionString'],
                         capture_output=True, text=True)
    return out.stdout.strip() or None


def team(app):
    out = subprocess.run(['codesign', '-dv', str(app)], capture_output=True, text=True).stderr
    m = re.search(r'TeamIdentifier=(\w+)', out)
    return m.group(1) if m else None


def latest():
    with urllib.request.urlopen(urllib.request.Request(API, headers={'User-Agent': 'print-kit'}), timeout=15) as r:
        rels = json.load(r)
    for rel in rels:
        if rel['draft'] or rel['prerelease'] or not re.fullmatch(r'v\d+\.\d+\.\d+', rel['tag_name']):
            continue
        dmg = [a for a in rel['assets'] if re.fullmatch(r'OrcaSlicer_Mac_universal_V[\d.]+\.dmg', a['name'])]
        if dmg:
            return rel['tag_name'].lstrip('v'), dmg[0]['browser_download_url'], dmg[0]['size']
    raise RuntimeError('no stable release with a Mac DMG')


def log(**row):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'), **row}) + '\n')


def update(check_only=False):
    have = installed()
    want, url, size = latest()
    if have and vtuple(have) >= vtuple(want):
        log(result='current', installed=have, latest=want)
        return f'OrcaSlicer {have} is current'
    if check_only:
        return f'OrcaSlicer {have} installed, {want} available'
    old_team = team(APP) if APP.exists() else None
    with tempfile.TemporaryDirectory() as tmp:
        dmg = Path(tmp) / Path(url).name
        urllib.request.urlretrieve(url, dmg)
        assert dmg.stat().st_size == size, 'download size differs from the release asset'
        mnt = Path(tmp) / 'mnt'
        subprocess.run(['hdiutil', 'attach', '-nobrowse', '-readonly', '-mountpoint', str(mnt), str(dmg)],
                       check=True, capture_output=True)
        try:
            new = mnt / 'OrcaSlicer.app'
            subprocess.run(['codesign', '--verify', '--deep', '--strict', str(new)], check=True, capture_output=True)
            gk = subprocess.run(['spctl', '-a', '-vv', '-t', 'exec', str(new)], capture_output=True, text=True).stderr
            assert 'accepted' in gk and 'Notarized Developer ID' in gk, gk
            assert old_team is None or team(new) == old_team, f'team {team(new)} differs from installed {old_team}'
            if subprocess.run(['pgrep', '-f', 'OrcaSlicer.app/Contents/MacOS/OrcaSlicer'], capture_output=True).returncode == 0:
                subprocess.run(['osascript', '-e', 'tell application "OrcaSlicer" to quit'], capture_output=True)
                for _ in range(30):
                    if subprocess.run(['pgrep', '-f', 'OrcaSlicer.app/Contents/MacOS/OrcaSlicer'], capture_output=True).returncode:
                        break
                    time.sleep(1)
                else:
                    log(result='blocked', installed=have, latest=want, reason='OrcaSlicer did not quit')
                    raise RuntimeError(f'OrcaSlicer {want} is ready but the open OrcaSlicer did not quit (unsaved project?)')
            if APP.exists():
                subprocess.run(['osascript', '-e', f'tell application "Finder" to delete POSIX file "{APP}"'],
                               check=True, capture_output=True)
            subprocess.run(['ditto', str(new), str(APP)], check=True)
        finally:
            subprocess.run(['hdiutil', 'detach', '-quiet', str(mnt)])
    now = installed()
    assert now and vtuple(now) == vtuple(want), f'installed {now}, expected {want}'
    log(result='updated', previous=have, installed=now)
    return f'OrcaSlicer updated {have} -> {now}'


def notify(text):
    subprocess.run(['osascript', '-e', f'display notification {json.dumps(text)} with title "OrcaSlicer update"'],
                   capture_output=True)


if __name__ == '__main__':
    # --notify: the launchd job (com.xiangzheng.update-orca, every 6 h and at login) shows the result as a macOS
    # notification when something changed or failed; a quiet "current" check shows nothing.
    try:
        msg = update('--check' in sys.argv)
    except Exception as e:
        log(result='error', error=f'{type(e).__name__}: {e}')
        if '--notify' in sys.argv:
            notify(f'Update failed: {e}')
        raise
    if '--notify' in sys.argv and 'updated' in msg:
        notify(msg)
    print(msg)
