"""Round 2 DAgger in the runtime simulation: fine-tune the recurrent student on runtime-simulation episodes labelled
by the privileged teacher (ts2_dagger_modal.py -> out/dagger/r<k>.npz). CPU, Mac mini (never the MacBook).

  <microduck_rl venv python> train/ts2_dagger_train.py --init train/ckpt/s2g_200/model_200.pt --data train/out/dagger/r1.npz \
      --tag s2r1 --epochs 30 --lr 5e-5 --template train/ckpt/s2g_200/walk61.onnx

State handling as distill_worker.py and flight_eval._StatefulSession: an episode starts from an empty state; the state
steps only on called ticks (a skipped tick is simply not in the sequence); it is zeroed before a call that follows five
or more skipped ticks. Truncated backpropagation over --bptt called ticks (100), the state carried detached to the next
segment, so every episode's first segment starts at its empty state. Loss: mean squared action error to the teacher's
label, the first --early-ticks (100) called ticks of an episode weighted x --early-w (3).
Every --save-every epochs: train/ckpt/<tag>_<epoch>/{model_<epoch>.pt, walk61.onnx, stand61.onnx} (ONNX metadata copied
from --template, the checkpoint the fine-tune starts from) and a row in train/out/dagger/<tag>_log.json with the
training and held-back (every 20th episode) error, overall and over the first 100 ticks.
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "microduck_rl/cmu/finetune/flight"))


def load(files, anchor_after=None, anchor_w=None):
    obs, lab, skip, n = [], [], [], []
    for f in files:
        z = np.load(f)
        off, zo, zl, zs, zk = z["offsets"], z["obs"], z["lab"], z["stu"], z["skip"]  # one decompression per array
        for a, b in zip(off[:-1], off[1:]):
            obs.append(zo[a:b].astype(np.float32))
            y = zl[a:b].astype(np.float32)
            if anchor_after is not None and anchor_w is None:  # from this called tick on the target is the collecting student's own action
                y[anchor_after:] = zs[a:b].astype(np.float32)[anchor_after:]
            elif anchor_after is not None:
                # teacher label on every tick plus, from anchor_after on, a second term of weight anchor_w toward the
                # collecting student's action: (a - lab)^2 + w (a - stu)^2 has its minimum at the mixed target below
                # (the factor 1 + w on those ticks is left out, so every tick keeps weight 1)
                y[anchor_after:] = (y[anchor_after:] + anchor_w * zs[a:b].astype(np.float32)[anchor_after:]) / (1.0 + anchor_w)
            lab.append(y)
            skip.append(zk[a:b])
            n.append(b - a)
    N, T = len(n), int(max(n))
    O, L = np.zeros((T, N, 61), np.float32), np.zeros((T, N, 14), np.float32)
    V, Z = np.zeros((T, N), bool), np.zeros((T, N), bool)
    for i in range(N):
        O[:n[i], i], L[:n[i], i], V[:n[i], i] = obs[i], lab[i], True
        Z[:n[i], i] = skip[i] >= 5
    return torch.tensor(O), torch.tensor(L), torch.tensor(V), torch.tensor(Z)


def run(student, O, L, V, Z, idx, a, opt=None):
    """one pass over the episodes idx in minibatches; returns (weighted loss, mse all ticks, mse first early ticks)"""
    T = O.shape[0]
    w_t = torch.ones(T)
    w_t[:a.early_ticks] = a.early_w
    tot = dict(l=0.0, n=0.0, e=0.0, en=0.0, a=0.0, an=0.0)
    for i in range(0, len(idx), a.mb):
        mb = idx[i:i + a.mb]
        s = student.init_state(len(mb))
        t_end = int(V[:, mb].any(dim=1).sum())
        for t0 in range(0, t_end, a.bptt):
            loss, wsum = 0.0, 0.0
            for t in range(t0, min(t0 + a.bptt, t_end)):
                v = V[t, mb]
                s = s * (~Z[t, mb]).view(-1, 1)
                act, s_new = student.step(O[t, mb], s)
                s = torch.where(v.view(-1, 1), s_new, s)
                e = ((act - L[t, mb]) ** 2).mean(dim=1) * v
                loss = loss + w_t[t] * e.sum()
                wsum += float(w_t[t] * v.sum())
                tot["a"] += float(e.sum())
                tot["an"] += float(v.sum())
                if t < a.early_ticks:
                    tot["e"] += float(e.sum())
                    tot["en"] += float(v.sum())
            if wsum == 0:
                break
            tot["l"] += float(loss)
            tot["n"] += wsum
            if opt is not None:
                opt.zero_grad()
                (loss / wsum).backward()
                torch.nn.utils.clip_grad_norm_(student.parameters(), 1.0)
                opt.step()
            s = s.detach()
    return tot["l"] / max(tot["n"], 1), tot["a"] / max(tot["an"], 1), tot["e"] / max(tot["en"], 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", required=True)
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--save-every", type=int, default=10)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--mb", type=int, default=128)
    ap.add_argument("--bptt", type=int, default=100)
    ap.add_argument("--early-ticks", type=int, default=100)
    ap.add_argument("--early-w", type=float, default=3.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--anchor-w", type=float, default=None,
                    help="with --anchor-after: keep the teacher label on every tick and add the student's own action as a "
                         "second term of this weight from that tick on (round 4: 1.0, then halved per round)")
    ap.add_argument("--anchor-after", type=int, default=None,
                    help="from this called tick of an episode on, the target is the collecting student's own action (stored "
                         "as stu) instead of the teacher's: only the start is corrected, the rest is held where it was. Valid "
                         "only for data collected by the checkpoint given as --init (2026-11-19: plain imitation of the "
                         "teacher on all ticks, s2r1_8, cured the creep but walked 0.32 m/s and fell 83 times in the seven cells)")
    ap.add_argument("--max-minutes", type=float, default=50.0)
    a = ap.parse_args()
    import onnx
    import recurrent as rc
    torch.manual_seed(a.seed)
    torch.set_num_threads(8)
    O, L, V, Z = load(a.data, a.anchor_after, a.anchor_w)
    N = O.shape[1]
    val = torch.arange(0, N, 20)
    trn = torch.tensor([i for i in range(N) if i % 20])
    ck = torch.load(a.init, map_location="cpu", weights_only=False)
    student = rc.load_checkpoint(a.init)
    opt = torch.optim.Adam(student.parameters(), lr=a.lr)
    log_p = HERE / f"out/dagger/{a.tag}_log.json"
    rows = []
    student.eval()
    with torch.no_grad():
        v0 = run(student, O, L, V, Z, val, a)
    print(f"[dagger] {N} episodes ({len(trn)} train, {len(val)} held back), {int(V.sum())} called ticks, longest {O.shape[0]}; "
          f"start: held-back mse {v0[1]:.5f}, first {a.early_ticks} ticks {v0[2]:.5f}", flush=True)
    rows.append(dict(epoch=0, val_mse=v0[1], val_mse_early=v0[2]))
    t0 = time.time()
    for ep in range(1, a.epochs + 1):
        student.train()
        # minibatches of episodes of similar length (rounds differ: 20 s, 8 s and 10 s episodes), in random order
        order = trn[torch.randperm(len(trn))]
        order = order[torch.argsort(V[:, order].sum(dim=0) // 150, stable=True)]
        chunks = [order[i:i + a.mb] for i in range(0, len(order), a.mb)]
        order = torch.cat([chunks[i] for i in torch.randperm(len(chunks)).tolist() if len(chunks[i]) == a.mb]
                          + [c for c in chunks if len(c) != a.mb])
        tr = run(student, O, L, V, Z, order, a, opt)
        student.eval()
        with torch.no_grad():
            va = run(student, O, L, V, Z, val, a)
        row = dict(epoch=ep, minutes=round((time.time() - t0) / 60, 2), train_loss=tr[0], train_mse=tr[1], train_mse_early=tr[2],
                   val_mse=va[1], val_mse_early=va[2])
        capped = (time.time() - t0) / 60 >= a.max_minutes
        if ep % a.save_every == 0 or ep == a.epochs or capped:
            d = HERE / f"ckpt/{a.tag}_{ep}"
            d.mkdir(parents=True, exist_ok=True)
            torch.save(dict(student=student.state_dict(), spec=ck["spec"], iter=ep, args=vars(a), init=a.init), d / f"model_{ep}.pt")
            p = str(d / "walk61.onnx")
            rc.export_onnx(student, p)
            m, tpl = onnx.load(p), onnx.load(a.template)
            del m.metadata_props[:]
            m.metadata_props.extend(tpl.metadata_props)
            onnx.save(m, p)
            row["onnx_vs_torch"] = rc.check_onnx(student, p)
            assert row["onnx_vs_torch"] < 1e-3, row
            shutil.copyfile(p, d / "stand61.onnx")
            row["saved"] = d.name
        rows.append(row)
        log_p.write_text(json.dumps(dict(args=vars(a), episodes=N, called_ticks=int(V.sum()), rows=rows), indent=1))
        print("[dagger]", json.dumps(row), flush=True)
        if capped:
            print("[dagger] time cap", flush=True)
            break


if __name__ == "__main__":
    main()
