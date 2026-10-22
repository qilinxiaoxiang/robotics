# A7Z flipped, Radxa Heatsink 6530B behind the board: fit check (2026-10-21)

Read-only check on the current guide CAD (`guide/data/guide-data.json` final poses, board frame `guide/print/a7z-head/checks.json`). No part was changed.

- Assumed 6530B envelope: 65 x 30 x 11.5 mm (Radxa page), 13 mm from the component face with the pad, 16 mm with a 3 mm fan inlet gap; it leaves the header strip (d < 6 mm) open, as in Radxa's photo.
- Result (`free.json`, `flip-6530b.png`): with the board flipped in place, 68 % of the heatsink footprint has 13 mm behind it (60 % has 16 mm). The upper part (d 13-30) has 13-50 mm. The lower band d 6-13 along the whole board has 4-10 mm: `jaw_support` (and `motor15`, the jaw servo, at the pin-1 end). Both board ends meet the cap's mounting pads (1.6-2.4 mm), which a flip would redesign anyway.
- Moving the board up does not free the band: the cap roof is 5-8 mm above the board's top edge (median) and near 0 at the ends (`up.py`).
- So the 6530B fits behind a flipped board only if the jaw support and jaw servo drop or move by about 3-9 mm, or the head grows; both change the jaw mechanism or the head shape (jaw geometry change reruns the jaw pose-cap study).

Run: `/tmp/microduck-cad-venv/bin/python -I rear_free.py free`, then `up.py`, `fig.py` in this folder.
