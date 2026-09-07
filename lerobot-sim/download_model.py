"""Restore the pinned, Apache-2.0 SO-101 model; verify every file."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent

def main():
    manifest = json.loads((ROOT / "model-manifest.json").read_text())
    for entry in manifest["files"]:
        target = ROOT / "models" / entry["path"]
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == entry["sha256"]:
            continue
        content = urlopen(entry["url"], timeout=60).read()
        if hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise ValueError(f"Model checksum mismatch: {entry['path']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    print(f"SO-101: verified {len(manifest['files'])} files at {manifest['commit']}")

if __name__ == "__main__":
    main()
