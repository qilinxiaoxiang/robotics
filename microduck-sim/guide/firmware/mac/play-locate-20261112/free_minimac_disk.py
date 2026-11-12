#!/usr/bin/env python3
"""Free space on the Mac mini (2026-11-12, Shawn: "该删就删掉"): delete the bulky outputs of finished sim studies in
~/sims (per-tick logs, frames, videos: any file over 5 MB), keeping every small file (summaries, JSON results,
scripts) so the studies' conclusions stay. Studies dated 2026-11-11 or later are left alone (other sessions may be
using them), and so is everything outside ~/sims. Prints what it deletes and the space freed.

  python3 free_minimac_disk.py           # list only
  python3 free_minimac_disk.py --delete
"""
import os
import sys
from pathlib import Path

ROOT = Path.home() / "sims"
OLD = ["glance-20261101", "seepick-gap-20261027", "pet-runner-20261029", "bvh-refit-20261029",
       "seepick-rehearsal-20261027", "sit-rise-20261029", "face-view-20261029"]
BIG = 5 * 1024 * 1024


def main():
    delete = "--delete" in sys.argv
    total = 0
    for name in OLD:
        d = ROOT / name
        if not d.is_dir():
            continue
        freed = 0
        for p in d.rglob("*"):
            if p.is_file() and not p.is_symlink() and p.stat().st_size > BIG:
                freed += p.stat().st_size
                if delete:
                    p.unlink()
        total += freed
        print(f"{name}: {freed / 1e9:.2f} GB in files over 5 MB")
    print(f"{'deleted' if delete else 'would delete'} {total / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
