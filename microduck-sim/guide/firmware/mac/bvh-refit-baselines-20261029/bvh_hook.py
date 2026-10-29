"""BVH-refit baseline study (2026-10-29): run any as-built sim harness unchanged, with or without the body-BVH refit
applied inside evaluate_delay.load (the proposed loader change), and count every body's floor contacts.

  BVH_REFIT=0|1  BVH_OUT=<file.jsonl>  ~/.venvs/microduck-dyn/bin/python bvh_run.py <harness.py> [its args]

bvh_run.py calls install() before the harness is imported. install() adds a meta-path hook: when evaluate_delay is
imported, its load() is wrapped so that after the original load (compile + add_signed_inertias) the refit runs when
BVH_REFIT=1. With BVH_REFIT=0 the refit is only computed on a copy, to report which bodies it would change. Physics is
untouched by the accounting: mujoco.mj_step is wrapped to read d.contact after each step.

Per run (one JSON line appended to BVH_OUT at exit):
  refit          whether the refit was applied
  changed        bodies whose root box the refit changes: {body: {"old": [c, h], "new": [c, h], "outside_mm": d}},
                 outside_mm = how far the body's colliding geometry reaches outside the stale box (0 = still covered)
  floor          per body: steps with a floor contact, first contact time, deepest contact distance (mm)
  missed         per body: 20 ms samples in which a colliding geom of the body was more than 1 mm below the floor with
                 no floor contact of that body (the stale-volume symptom), first time, deepest point (mm)
"""
import atexit
import importlib.abc
import importlib.machinery
import json
import os
import sys

import numpy as np

REFIT = os.environ.get("BVH_REFIT", "0") == "1"
OUT = os.environ.get("BVH_OUT")
SAMPLE_EVERY = 8            # steps between below-floor checks (2.5 ms steps -> 20 ms)
MISS_DEPTH = 1e-3           # m below the floor without a contact that counts as a missed contact
_RUNS = []                  # one accounting object per loaded model
MACBOOK_REPO = "/Users/xiangzheng/code/robotics/"
TRACE = os.environ.get("BVH_TRACE")  # file: every 20 ms sample (lowest point per body, bodies touching the floor)


def refit_body_bvh(m, write=True):
    """brain_sim_check.refit_body_bvh (2026-10-29), verbatim apart from `write` (False: report only) and the
    outside_mm field."""
    import mujoco
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    changed = {}
    for b in range(1, m.nbody):
        adr, num = m.body_bvhadr[b], m.body_bvhnum[b]
        if adr < 0 or num <= 0:
            continue
        R, p = d.ximat[b].reshape(3, 3), d.xipos[b]
        pts = []
        for g in range(m.ngeom):
            if m.geom_bodyid[g] != b or not (m.geom_contype[g] or m.geom_conaffinity[g]):
                continue
            Rg, cg, a = d.geom_xmat[g].reshape(3, 3), d.geom_xpos[g], m.geom_aabb[g]
            for sx in (-1, 1):
                for sy in (-1, 1):
                    for sz in (-1, 1):
                        pts.append(R.T @ (cg + Rg @ (a[:3] + np.array([sx, sy, sz]) * a[3:]) - p))
        if not pts:
            continue
        pts = np.array(pts)
        lo, hi = pts.min(0), pts.max(0)
        box = np.r_[(lo + hi) / 2, (hi - lo) / 2 + 1e-4]
        old = m.bvh_aabb[adr].copy()
        if np.any(np.abs(old[:3] - box[:3]) > old[3:] + 1e-6) or np.any(np.abs(old[:3] - box[:3]) + box[3:] > old[3:] + 1e-4):
            outside = np.maximum(np.abs(pts - old[:3]) - old[3:], 0).max()
            changed[m.body(b).name] = dict(old=old.round(4).tolist(), new=box.round(4).tolist(),
                                           outside_mm=round(float(outside) * 1000, 1))
        if write:
            for k in range(adr, adr + num):
                m.bvh_aabb[k] = box
    return changed


class Accounting:
    def __init__(self, m, changed):
        import mujoco
        self.m = m
        self.changed = changed
        planes = [g for g in range(m.ngeom) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE]
        self.floor = planes[0] if planes else -1
        self.floor_body = int(m.geom_bodyid[self.floor]) if planes else -1
        self.steps = 0
        self.floor_steps = {}
        self.first = {}
        self.min_dist = {}
        self.missed = {}
        self.missed_first = {}
        self.missed_depth = {}
        self.lowest = {}
        self.pairs = {}
        self.trace = []
        # colliding geometry per body as local points (mesh hull vertices, box corners, sphere/capsule handled by rbound)
        self.geoms = {}
        for g in range(m.ngeom):
            b = int(m.geom_bodyid[g])
            if b == self.floor_body or not (m.geom_contype[g] or m.geom_conaffinity[g]):
                continue
            t = m.geom_type[g]
            if t == mujoco.mjtGeom.mjGEOM_MESH:
                mid = m.geom_dataid[g]
                pts = m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]].copy()
                pad = 0.0
            elif t == mujoco.mjtGeom.mjGEOM_BOX:
                s = m.geom_size[g]
                pts = np.array([[x, y, z] for x in (-s[0], s[0]) for y in (-s[1], s[1]) for z in (-s[2], s[2])])
                pad = 0.0
            elif t == mujoco.mjtGeom.mjGEOM_SPHERE:
                pts, pad = np.zeros((1, 3)), float(m.geom_size[g][0])
            elif t == mujoco.mjtGeom.mjGEOM_CAPSULE:
                h = m.geom_size[g][1]
                pts, pad = np.array([[0, 0, -h], [0, 0, h]]), float(m.geom_size[g][0])
            else:  # cylinder / ellipsoid: bounding sphere, conservative (can only overstate a miss, reported as such)
                pts, pad = np.zeros((1, 3)), float(m.geom_rbound[g])
            self.geoms.setdefault(b, []).append((g, pts, pad))

    def after_step(self, d):
        self.steps += 1
        n = d.ncon
        touching = set()
        if n and self.floor >= 0:
            g1 = d.contact.geom1[:n]
            g2 = d.contact.geom2[:n]
            dist = d.contact.dist[:n]
            sel = (g1 == self.floor) | (g2 == self.floor)
            if (~sel).any():  # contacts between two non-floor bodies (self-collision, objects)
                for a, b in set(zip(self.m.geom_bodyid[g1[~sel]].tolist(), self.m.geom_bodyid[g2[~sel]].tolist())):
                    key = tuple(sorted((a, b)))
                    self.pairs[key] = self.pairs.get(key, 0) + 1
            if sel.any():
                other = np.where(g1 == self.floor, g2, g1)[sel]
                bodies = self.m.geom_bodyid[other]
                for b, dd in zip(bodies.tolist(), dist[sel].tolist()):
                    touching.add(b)
                    self.min_dist[b] = min(self.min_dist.get(b, 1.0), dd)
                for b in touching:
                    self.floor_steps[b] = self.floor_steps.get(b, 0) + 1
                    self.first.setdefault(b, round(float(d.time), 3))
        if self.steps % SAMPLE_EVERY == 0 and self.floor >= 0:
            fz = float(d.geom_xpos[self.floor][2])
            sample = dict(t=round(float(d.time), 3), touch=sorted(self.m.body(b).name for b in touching))
            if TRACE:
                self.trace.append(sample)
            for b, items in self.geoms.items():
                lo = 1e9
                for g, pts, pad in items:
                    R = d.geom_xmat[g].reshape(3, 3)
                    z = (pts @ R[2]).min() + d.geom_xpos[g][2] - pad
                    lo = min(lo, z)
                lo -= fz
                if TRACE:
                    sample.setdefault("low_mm", {})[self.m.body(b).name] = round(lo * 1000, 1)
                self.lowest[b] = min(self.lowest.get(b, 1e9), lo)
                if lo < -MISS_DEPTH and b not in touching:
                    self.missed[b] = self.missed.get(b, 0) + 1
                    self.missed_first.setdefault(b, round(float(d.time), 3))
                    self.missed_depth[b] = min(self.missed_depth.get(b, 0.0), lo)

    def report(self):
        name = lambda b: self.m.body(b).name  # noqa: E731
        return dict(
            changed=self.changed, steps=self.steps,
            floor={name(b): dict(steps=s, first_s=self.first[b], min_dist_mm=round(self.min_dist[b] * 1000, 2))
                   for b, s in sorted(self.floor_steps.items())},
            missed={name(b): dict(samples=s, first_s=self.missed_first[b], deepest_mm=round(self.missed_depth[b] * 1000, 1))
                    for b, s in sorted(self.missed.items())},
            pairs={f"{name(a)}|{name(b)}": s for (a, b), s in sorted(self.pairs.items())},
            lowest_mm={name(b): round(v * 1000, 1) for b, v in sorted(self.lowest.items())})


def _wrap_module(mod):
    import mujoco
    orig_load = mod.load

    def load(config):
        # asbuilt.config.json names its mass manifest by an absolute MacBook path; on the Mac mini snapshot the same file
        # sits under this snapshot's repository root (path only, the content is the same file)
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 5))
        for k, v in list(config.items()):
            if isinstance(v, str) and v.startswith(MACBOOK_REPO) and not os.path.exists(v):
                config[k] = os.path.join(root, v[len(MACBOOK_REPO):])
        out = orig_load(config)
        m = out[0]
        changed = refit_body_bvh(m, write=REFIT)
        _RUNS.append(Accounting(m, changed))
        return out

    load.__wrapped__ = orig_load
    mod.load = load
    if not getattr(mujoco.mj_step, "_bvh_hook", False):
        orig_step = mujoco.mj_step

        def mj_step(m, d, *a, **k):
            orig_step(m, d, *a, **k)
            for acc in _RUNS:
                if acc.m is m:
                    acc.after_step(d)
                    break

        mj_step._bvh_hook = True
        mujoco.mj_step = mj_step


class _Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name != "evaluate_delay":
            return None
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None or spec.loader is None:
            return spec
        exec_orig = spec.loader.exec_module

        def exec_module(module):
            exec_orig(module)
            _wrap_module(module)

        spec.loader.exec_module = exec_module
        return spec


def _write():
    if OUT:
        row = dict(argv=sys.argv, refit=REFIT, models=[a.report() for a in _RUNS])
        with open(OUT, "a") as f:
            f.write(json.dumps(row) + "\n")
    if TRACE and _RUNS:
        with open(TRACE, "w") as f:
            for s in _RUNS[0].trace:
                f.write(json.dumps(s) + "\n")


def install():
    sys.meta_path.insert(0, _Finder())
    atexit.register(_write)
