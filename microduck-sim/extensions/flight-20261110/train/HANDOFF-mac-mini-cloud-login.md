# Mac mini: log in to Modal and Kaggle once

Goal: the flight-pack watchers (gate scoring on Modal, Kaggle kernel fetch and push) can run on the always-on Mac
mini instead of the MacBook, so a closed MacBook lid no longer pauses them.

State on 2026-11-19 20:48: the clients are installed on the Mac mini in `~/.venvs/cloud-cli` (modal 1.6.4, kaggle).
No token exists there: `~/.modal.toml` and `~/.kaggle/kaggle.json` are missing, `modal profile list` is empty. Claude
may not create, copy or print tokens, so these two logins are Shawn's (or an agent he hands this file to).

## 1. Modal (workspace zhengxia)

On the Mac mini (Screen Sharing or a terminal at the machine, because the login opens a browser):

    ~/.venvs/cloud-cli/bin/modal token new --profile zhengxia

Approve in the browser with the account that owns the workspace `zhengxia`. The token is written to `~/.modal.toml`
by the command itself.

Check: `~/.venvs/cloud-cli/bin/modal profile list` shows `zhengxia`, and
`~/.venvs/cloud-cli/bin/modal app list` prints a table without an authentication error.

## 2. Kaggle

On https://www.kaggle.com/settings (API section) press "Create New Token"; the browser downloads `kaggle.json`.
On the Mac mini:

    mkdir -p ~/.kaggle && mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json && chmod 600 ~/.kaggle/kaggle.json

Creating a new token can invalidate the old one on the MacBook; if it does, copy the same file to
`~/.kaggle/kaggle.json` on the MacBook as well.

Check: `~/.venvs/cloud-cli/bin/kaggle kernels list --mine | head -3` lists kernels without a 401.

## After both checks pass

Tell the flight-training session "Mac mini login done". It runs the two checks itself, then moves
`train/ts3m_watch.py`, `train/ts3_after_kaggle.sh`, `train/ts3_distill_trigger.py` and `train/ts3_bill_guard.py` to
the Mac mini (detached, parent pid 1, heartbeats under `~/flight-heartbeat/`) and stops the MacBook copies.
