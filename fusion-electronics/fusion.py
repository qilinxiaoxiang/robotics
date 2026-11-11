"""Fusion data operations through the ClaudeBridge add-in, with failures that really fail.

  fusion.py ls
  fusion.py rename NAME NEW
  fusion.py delete NAME                 # electronics design: .fprj parent first, then .fsch/.fbrd
  fusion.py delete-folder NAME          # subfolder and the electronics designs in it
  fusion.py import FILE.sch [--replace] [--check "CMD {}"]
  fusion.py export NAME OUT.sch         # Fusion's stored copy, for acceptance checks
  fusion.py image NAME OUT.png [DPI]    # full sheet rendered off-screen (EXPORT IMAGE)
  fusion.py run JOB.py                  # any bridge code (app, ui, adsk defined), same guards

Folder: FUSION_PROJECT + FUSION_PATH (non-empty, slash-separated under the project root).

import is accepted only when all of these hold: no Fusion Error window, a NEW .fsch id named
after the file appears, a settle period passes with no Error window, and Fusion's own exported
copy passes sch_lint.py plus the optional --check command (FUSION_CHECK env also works; {} is the
exported file). With --replace the old design is renamed aside first and deleted only after that
acceptance; every failure path restores it and moves a bad new design aside as NAME__failed_*.
Every bridge error (an exception in Fusion, a guard, a dialog) exits non-zero.
"""
import json
import os
import shlex
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
URL = "http://127.0.0.1:8777/"
PALETTES = {"BROWSER", "SHEETS", "TEXT COMMANDS", "COMMENTS", "PLACE COMPONENTS", "INSPECTOR"}
SHOTS = Path(os.environ.get("FUSION_SHOT_DIR", Path(os.environ.get("TMPDIR", "/tmp")) / "fusion-shots"))
ELECTRONICS = ("fprj", "fsch", "fbrd")


class Fail(Exception):
    pass


# ------------------------------------------------------------------ dialogs
def windows():
    """[(name, subrole, size)] of Fusion's windows. Raises if they cannot be read: an empty
    list would make every dialog guard pass blind."""
    script = ('set out to ""\n'
              'tell application "System Events" to tell (first process whose name is "Autodesk Fusion")\n'
              'repeat with w in every window\n'
              'set out to out & (name of w) & "\t" & (subrole of w) & "\t" & ((size of w) as string) & linefeed\n'
              'end repeat\nend tell\nreturn out')
    for attempt in range(4):     # reads fail for a moment while Fusion's main thread is busy
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        rows = [tuple(l.split("\t")) for l in r.stdout.splitlines() if l.strip()]
        if r.returncode == 0 and rows:
            return rows
        time.sleep(1.5)
    if True:
        raise Fail(f"cannot read Fusion windows (osascript rc {r.returncode}: {r.stderr.strip()[:120]}); "
                   "is Fusion running and does this terminal have Automation access to System Events?")


def dialogs():
    return [w for w in windows() if "Autodesk Fusion" not in w[0] and w[0] not in PALETTES]


def shot(tag):
    SHOTS.mkdir(parents=True, exist_ok=True)
    f = SHOTS / f"{tag}-{time.strftime('%H%M%S')}.png"
    subprocess.run(["screencapture", "-x", str(f)])
    subprocess.run(["sips", "-Z", "1400", str(f)], capture_output=True)
    return f


def key(code):
    """Only for dialogs fusion.py itself raised (Upload Options, and the Error report of the
    upload it started). Brings Fusion to the front, so never a generic dialog closer."""
    subprocess.run(["osascript", "-e", 'tell application "System Events" to tell (first process whose name is "Autodesk Fusion")',
                    "-e", "set frontmost to true", "-e", "delay 0.3", "-e", f"key code {code}", "-e", "end tell"])


# ------------------------------------------------------------------ bridge
def job(template, timeout=10, expect_dialog=False, guard=True, **vals):
    vals = {"PROJECT": os.environ.get("FUSION_PROJECT", ""), "PATH": os.environ.get("FUSION_PATH", ""),
            "CREATE": "no", **vals}
    if not vals["PROJECT"] or not vals["PATH"].strip("/"):
        raise Fail("set FUSION_PROJECT and a non-empty FUSION_PATH (refusing to act on a project root)")
    code = (HERE / "folder.py").read_text() + "\n" + (HERE / "jobs" / f"{template}.py").read_text()
    for k, v in vals.items():
        code = code.replace(f"'@@{k}@@'", repr(str(v)))
    if "'@@" in code:
        raise Fail(f"unfilled placeholder in job {template}")
    return bridge(code, timeout, expect_dialog, guard)


def bridge(code, timeout=10, expect_dialog=False, guard=True):
    d = dialogs() if guard else []
    if d:
        raise Fail(f"Fusion already shows dialog(s) {d}; screenshot {shot('dialog')}")
    try:
        with urllib.request.urlopen(urllib.request.Request(URL, data=code.encode()), timeout=timeout) as r:
            res = json.loads(r.read())
    except (TimeoutError, urllib.error.URLError) as e:
        raise Fail(f"bridge call failed or exceeded {timeout} s ({e}); screenshot {shot('stuck')}")
    if not res.get("ok"):
        raise Fail("Fusion raised: " + (res.get("error") or "")[-600:])
    if not expect_dialog:
        time.sleep(3)          # Fusion raises assert dialogs a few seconds after the call returns
        d = dialogs()
        if d:
            raise Fail(f"Fusion opened dialog(s) {d} during the call; screenshot {shot('dialog')}")
    return res.get("out", "").strip()


def listing(create=False, guard=True):
    """guard=False only inside cmd_import's wait loop, which handles its own dialogs."""
    out = job("ls", CREATE="yes" if create else "no", guard=guard, expect_dialog=not guard)
    return json.loads(out.splitlines()[-1])


def files_named(name):
    return listing()["files"].get(name, {})


# ------------------------------------------------------------------ commands
def cmd_rename(name, new):
    job("rename", NAME=name, NEW=new)
    lst = listing()["files"]
    if name in lst or new not in lst:
        raise Fail(f"rename {name} -> {new} not reflected in the folder listing")


def cmd_delete(name, kind="design"):
    out = job("delete", timeout=60, NAME=name, KIND=kind)
    lst = listing()
    if (kind == "design" and any(e in ELECTRONICS for e in lst["files"].get(name, {}))) or \
            (kind == "folder" and name in lst["folders"]):
        raise Fail(f"{name} still listed after delete")
    return out


def cmd_export(name, out):
    out = str(Path(out).resolve())
    job("export", timeout=60, NAME=name, OUT=out)
    if not Path(out).exists():
        raise Fail(f"export produced no file {out}")
    return out


def cmd_image(name, out, dpi="150"):
    if not str(dpi).isdigit():
        raise Fail("DPI must be an integer")
    out = str(Path(out).resolve())
    if "'" in out or ";" in out:
        raise Fail("image path may not contain a quote or ';' (it goes into an EAGLE command)")
    t0 = time.time()
    job("image", timeout=60, NAME=name, OUT=out, DPI=dpi)
    if not Path(out).exists() or Path(out).stat().st_mtime < t0 - 1:
        raise Fail(f"EXPORT IMAGE wrote no new file at {out}")
    return out


def accept(sch_path, check):
    """sch_lint plus the project check on Fusion's exported copy."""
    sys.path.insert(0, str(HERE))
    from sch_lint import lint
    fails, _ = lint(sch_path)
    if fails:
        raise Fail("Fusion's stored copy fails sch_lint:\n  " + "\n  ".join(fails[:10]))
    if check:
        r = subprocess.run(check.replace("{}", shlex.quote(sch_path)), shell=True, capture_output=True, text=True)
        if r.returncode:
            raise Fail(f"project check failed on Fusion's stored copy:\n{(r.stdout + r.stderr)[-1500:]}")


def cmd_import(sch, replace=False, check=None):
    sch = str(Path(sch).resolve())
    name = Path(sch).stem
    check = check or os.environ.get("FUSION_CHECK")
    stamp = time.strftime("%Y%m%d%H%M%S")
    old = None
    if listing(create=True)["files"].get(name):   # import may target a new folder
        if not replace:
            raise Fail(f"design {name} already exists; pass --replace")
        old = f"{name}__replaced_{stamp}"
        cmd_rename(name, old)
    old_ids = {i for exts in listing()["files"].values() for i in exts.values()}
    # DataFolder.uploadFile blocks Fusion's main thread until its Upload Options dialog is
    # answered, so the upload call runs in a thread while this loop confirms the dialog.
    result = {}

    def run_upload():
        try:
            result["out"] = job("upload", timeout=180, expect_dialog=True, guard=False, FILE=sch, CREATE="yes")
        except Exception as e:     # reported after the thread ends
            result["err"] = e

    th = threading.Thread(target=run_upload, daemon=True)
    started = False
    try:
        if dialogs():
            raise Fail(f"Fusion shows a dialog before the upload; screenshot {shot('dialog')}")
        th.start()
        started = True
        confirmed, deadline = False, time.time() + 60
        while th.is_alive() and time.time() < deadline:
            time.sleep(1)
            d = dialogs()
            if any("Error" in w[0] for w in d):
                raise Fail(f"Fusion reported an import error (screenshot {shot('import-error')})")
            if not confirmed and any(w[0] == "" for w in d):
                time.sleep(1)
                key(36)     # Upload Options: keep "Create Electronics Design" and confirm
                confirmed = True
        th.join(5)
        if th.is_alive():
            raise Fail(f"upload still blocked after 60 s (screenshot {shot('stuck')})")
        if "err" in result:
            raise result["err"]
        print("upload state", result.get("out"))
        settle_until, deadline = None, time.time() + 90
        while time.time() < deadline:
            time.sleep(1)
            d = dialogs()
            if any("Error" in w[0] for w in d):
                raise Fail(f"Fusion reported an import error (screenshot {shot('import-error')})")
            if d:
                continue    # a modal blocks the bridge: wait for it to clear before listing
            fsch = listing(guard=False)["files"].get(name, {}).get("fsch")
            if fsch and fsch not in old_ids:
                settle_until = settle_until or time.time() + 5
                if time.time() >= settle_until:
                    break
        else:
            raise Fail(f"no new {name}.fsch within 90 s")
        exported = cmd_export(name, Path(os.environ.get("TMPDIR", "/tmp")) / f"fusion-accept-{name}-{stamp}.sch")
        accept(exported, check)
    except Exception as e:
        notes = []
        if started:          # free Fusion's main thread from dialogs this upload raised
            for _ in range(3):
                d = dialogs()
                if not d:
                    break
                key(36 if any("Error" in w[0] for w in d) else 53)   # dismiss our Error report / cancel Upload Options
                time.sleep(2)
            th.join(10)
        try:
            if files_named(name):
                cmd_rename(name, f"{name}__failed_{stamp}")
                notes.append(f"failed new design moved aside as {name}__failed_{stamp}")
        except Exception as e2:
            notes.append(f"could not move the failed new design aside: {e2}")
        if old:
            try:
                cmd_rename(old, name)
                notes.append(f"old design restored as {name}")
            except Exception as e3:
                notes.append(f"OLD DESIGN NOT RESTORED: it is still named {old} ({e3})")
        raise Fail(f"{e}\n" + "\n".join(notes))
    if old:
        cmd_delete(old)
    return f"PASS: {name} imported; Fusion's stored copy {exported} passed acceptance"


def main(argv):
    if not argv:
        print(__doc__); return 2
    c, a = argv[0], argv[1:]
    if c == "ls":
        print(json.dumps(listing(), indent=1, ensure_ascii=False))
    elif c == "rename":
        cmd_rename(*a); print("renamed")
    elif c == "delete":
        print(cmd_delete(a[0]))
    elif c == "delete-folder":
        print(cmd_delete(a[0], "folder"))
    elif c == "export":
        print(cmd_export(*a))
    elif c == "image":
        print(cmd_image(*a))
    elif c == "run":
        code = Path(a[0]).read_text()
        import re
        if re.search(r"\bADD\s+[^;'\"@]*[;'\"]", code, re.I):
            raise Fail("ADD without name@library opens a modal picker; use exact names")
        print(bridge(code, int(os.environ.get("FX_TIMEOUT", "10"))))
    elif c == "import":
        check = a[a.index("--check") + 1] if "--check" in a else None
        print(cmd_import(a[0], "--replace" in a, check))
    else:
        print(__doc__); return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Fail as e:
        print("FAIL:", e)
        sys.exit(1)
