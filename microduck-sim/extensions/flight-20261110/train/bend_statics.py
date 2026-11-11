"""Can the duck bend to the floor with the flight pack inside the servo limit? Static torques over the bend (BEND-PLAN.md).

1. Trace: one no-pack groundpick61 episode in the probe (brain_sim_check, as train/style_probe.sh bend runs it)
   records the 14 joint angles every 0.04 s from the bend start to the hand-back.
2. Statics: each traced pose is put on the as-built model of each load (full pack, batteries out, no pack), feet flat
   on the floor (static_gap.feet_flat_rot). Gravity torque on every leg pitch joint = the moment, about that joint's
   axis, of the weight of everything above the cut through both legs at that joint (the trunk side), split equally
   between the two legs (symmetric pose); the neck and head pitch joints carry their own subtrees. Quasi-static:
   no acceleration, no contact with the floor except the soles.
3. Search: hip pitch, knee, ankle, neck pitch and head pitch on a grid inside the joint ranges, legs mirrored from the
   traced bend pose; a pose qualifies when the mouth tip is within 3 cm of the floor and the whole-robot centre of
   mass is over the sole contact patch with 5 mm margin. Reported: the qualifying pose with the lowest hip pitch
   torque, and the lowest worst-leg-joint torque, per load.

Run on the Mac mini (mini.sh run): $PY train/bend_statics.py --out train/out/bend_statics.json
"""
import argparse
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flight_eval as fe  # noqa: E402

LIMIT = 0.538
TARGET = 0.50
MOUTH_MAX_Z = 0.03
COM_MARGIN = 0.005
LOADS = {"full": "flightpack-load100.json", "nobatt": "flightpack-nobatt.json", "none": "flightpack-load000.json"}
PITCH = ("hip_pitch", "knee", "ankle")


def trace(models, manifest):
    """joint angles over one no-pack groundpick61 episode (gp at 2 s, phase 0.33, hold 4 s, rise, hand-back)"""
    rec = dict(rows=[], names=None, last=-1.0)

    def hook(m, d, t):
        if rec["names"] is None:
            rec["names"] = [m.actuator(i).name for i in range(m.nu)]
            rec["adr"] = [m.jnt_qposadr[m.actuator(i).trnid[0]] for i in range(m.nu)]
        if t >= 1.8 and t - rec["last"] >= 0.04 - 1e-9:
            rec["last"] = t
            rec["rows"].append([round(t, 3)] + [float(d.qpos[a]) for a in rec["adr"]])

    fe.FRAME_HOOK = hook
    extra = "--walk-at 1 --walk-s 0 --gp-at 2 --gp-phase 0.33 --gp-hold-s 4".split()
    r = fe.episode((str(models), str(manifest), "stand", 0, 0.0, 8.0, False, extra))
    fe.FRAME_HOOK = None
    return rec, r


def load_model(manifest):
    sys.path.insert(0, str(fe.RL / "cmu/mac"))
    import brain_sim_check as b
    c0 = b.cfg(0.09, model="asbuilt", kp=200, voltage=7.6)
    c0["mass_manifest"] = str(Path(manifest).resolve())
    m, d, c, names, bam = b.ev.load(c0)
    return b, m, d, names


class Statics:
    def __init__(self, b, m, d, names):
        import mujoco
        self.mj, self.b, self.m, self.d, self.names = mujoco, b, m, d, names
        self.jid = {n: m.actuator(n).trnid[0] for n in names}
        self.body_of = {n: m.jnt_bodyid[self.jid[n]] for n in names}
        par = m.body_parentid
        self.sub = {}
        for n in names:  # bodies in the subtree of each joint's body
            root = self.body_of[n]
            self.sub[n] = {i for i in range(m.nbody) if self._is_desc(i, root, par)}
        self.mouth = m.site("mouth_tip").id
        self.g = 9.81
        self.carried = {}  # joint -> (body index array, share)
        for n in names:
            if any(p in n for p in PITCH) and n.startswith(("left_", "right_")):
                other = n.replace("left_", "right_") if n.startswith("left_") else n.replace("right_", "left_")
                below = self.sub[n] | self.sub[other]
                self.carried[n] = (np.array([i for i in range(1, m.nbody) if i not in below]), 0.5)
            elif "neck" in n or "head" in n:
                self.carried[n] = (np.array(sorted(self.sub[n])), 1.0)
        # left/right mirror: +1 when the two joints' axes point the same way in the stand pose, -1 when opposite
        import walk_brain  # noqa: F401  (on the path through brain_sim_check)
        self.place({k: float(b.BRAIN_STAND[k]) for k in names})
        self.mirror = {}
        for n in names:
            if n.startswith("left_"):
                r = n.replace("left_", "right_")
                self.mirror[n] = 1.0 if float(d.xaxis[self.jid[n]] @ d.xaxis[self.jid[r]]) > 0 else -1.0

    @staticmethod
    def _is_desc(i, root, par):
        while i > 0:
            if i == root:
                return True
            i = par[i]
        return root == 0

    def _sole_cache(self):
        """per foot geom, in its own frame (constant): the sole normal (static_gap.sole_normal) and the vertices within
        1 mm of the sole plane, so placing a pose needs no SVD over the whole foot mesh"""
        m, d = self.m, self.d
        self.b.setup(m, d, self.names, {k: float(self.b.BRAIN_STAND[k]) for k in self.names})
        self.feet = []
        for g in ("left_foot_collision", "right_foot_collision"):
            gid = m.geom(g).id
            mid = m.geom_dataid[gid]
            v = m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]].astype(float)
            R = d.geom_xmat[gid].reshape(3, 3)
            n_world = self.b.sole_normal(m, d, g) if hasattr(self.b, "sole_normal") else None
            if n_world is None:
                import static_gap
                n_world = static_gap.sole_normal(m, d, g)
            n_loc = R.T @ n_world
            h = v @ n_loc
            sole = v[h > h.max() - 1.0]
            self.feet.append((gid, n_loc, sole))

    def place(self, pose):
        """static_gap's placement (mean sole normal straight down, lowest sole point on the floor), from the cache"""
        m, d, mj = self.m, self.d, self.mj
        if not hasattr(self, "feet"):
            self._sole_cache()
        self.b.setup(m, d, self.names, pose)
        n = sum(d.geom_xmat[gid].reshape(3, 3) @ nl for gid, nl, _ in self.feet)
        n /= np.linalg.norm(n)
        t = np.array([0, 0, -1.0])
        ax = np.cross(n, t)
        s = np.linalg.norm(ax)
        cth = float(n @ t)
        if s < 1e-9:
            Rt = np.eye(3)
        else:
            ax /= s
            K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
            Rt = np.eye(3) + math.sin(math.atan2(s, cth)) * K + (1 - cth) * K @ K
        q = np.zeros(4)
        mj.mju_mat2Quat(q, Rt.ravel())
        self.b.setup(m, d, self.names, pose, q)
        pts = self._soles()
        d.qpos[2] -= pts[:, 2].min()
        mj.mj_forward(m, d)
        return self._soles()

    def penetration(self, depth=0.002):
        """the first contact deeper than `depth` that is not a sole on the floor, as (geom1, geom2, dist), else None.
        Also any collision-enabled geom whose centre is below the floor (the model may not collide every part)."""
        m, d = self.m, self.d
        if not hasattr(self, "_soles_ids"):
            self._soles_ids = {gid for gid, _, _ in self.feet}
            self._floor = {i for i in range(m.ngeom) if m.geom_bodyid[i] == 0}
            self._coll = [i for i in range(m.ngeom) if m.geom_bodyid[i] != 0 and i not in self._soles_ids
                          and (m.geom_contype[i] or m.geom_conaffinity[i])]
        for k in range(d.ncon):
            c = d.contact[k]
            g1, g2 = int(c.geom1), int(c.geom2)
            if c.dist > -depth:
                continue
            if (g1 in self._floor and g2 in self._soles_ids) or (g2 in self._floor and g1 in self._soles_ids):
                continue
            return (m.geom(g1).name, m.geom(g2).name, float(c.dist))
        for i in self._coll:
            if d.geom_xpos[i, 2] < 0.0:
                return (m.geom(i).name, "floor (centre below)", float(d.geom_xpos[i, 2]))
        return None

    def _soles(self):
        d = self.d
        return np.vstack([sole @ d.geom_xmat[gid].reshape(3, 3).T + d.geom_xpos[gid] for gid, _, sole in self.feet])

    def torques(self):
        """gravity torque (N m) per joint for the current placed pose; legs: both-leg cut, half each"""
        m, d = self.m, self.d
        # leg load split by the lever rule: the share of the weight each foot carries, from where the whole-robot
        # centre of mass lies between the two soles (0.5 when symmetric; a one-battery pack moves it sideways)
        fl, fr = d.geom_xpos[m.geom("left_foot_collision").id], d.geom_xpos[m.geom("right_foot_collision").id]
        v = (fl - fr)[:2]
        s_left = float(np.clip(((d.subtree_com[0][:2] - fr[:2]) @ v) / (v @ v), 0.0, 1.0))
        out = {}
        for n, (idx, share) in self.carried.items():
            j = self.jid[n]
            w = np.zeros((len(idx), 3))
            w[:, 2] = -m.body_mass[idx] * self.g
            tau = float(np.sum(np.cross(d.xipos[idx] - d.xanchor[j], w) @ d.xaxis[j]))
            if share < 1.0:  # both-leg cut: total moment split by the foot load shares
                share = s_left if n.startswith("left_") else 1.0 - s_left
            out[n] = round(share * tau, 4)  # the servo holds this moment (sign: about the joint axis)
        self.s_left = s_left
        return out

    def state(self, pose, need_tau=True, gate=False):
        pts = self.place(pose)
        d = self.d
        com = d.subtree_com[0]
        touch = pts[pts[:, 2] < 1.5e-3]
        x0, x1 = touch[:, 0].min(), touch[:, 0].max()
        y0, y1 = touch[:, 1].min(), touch[:, 1].max()
        margin = min(com[0] - x0, x1 - com[0], com[1] - y0, y1 - com[1])
        mz = float(d.site_xpos[self.mouth, 2])
        if gate and (mz > MOUTH_MAX_Z or mz < 0.0 or margin < COM_MARGIN):
            return None
        Rt = d.xmat[self.m.body("trunk_base").id].reshape(3, 3)
        pitch = float(math.degrees(math.atan2(-Rt[2, 0], Rt[0, 0])))
        if gate:
            # a forward bend (D-027): trunk nose-down 0-75 deg, nothing but the soles in the floor, no part through
            # another (contacts from mj_forward deeper than 2 mm, foot-floor contacts excepted)
            if not (0.0 <= pitch <= 75.0):
                return None
            if self.penetration() is not None:
                return None
        return dict(mouth_z=mz, com_margin=float(margin), trunk_pitch_deg=pitch,
                    trunk_z=float(d.xpos[self.m.body("trunk_base").id, 2]), tau=self.torques() if need_tau else None)


def mirror_pose(base, vals, stand, mirror):
    """left-leg joints to vals, the right leg to the same change from the stand pose about its own axis (mirror sign)"""
    p = dict(base)
    for k, v in vals.items():
        p[k] = v
        if k.startswith("left_"):
            r = k.replace("left_", "right_")
            p[r] = stand[r] + mirror[k] * (v - stand[k])
    return p


BATT_PARTS = ("battery-L", "battery-R", "strap-L", "strap-R")


def variant_manifests(M, out_dir, moves):
    """hardware variants from the full-pack manifest (trunk_base frame, +x forward, +z up): batteries (with their
    straps) moved by (dx forward, dz down) mm, and one battery (the left one kept, the right battery and strap removed)"""
    base = json.loads((M / LOADS["full"]).read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    res = {}
    for dx, dz in moves:
        h = dict(base)
        h["parts"] = [dict(p, position_m=[p["position_m"][0] + dx / 1000, p["position_m"][1], p["position_m"][2] - dz / 1000])
                      if p["id"] in BATT_PARTS else p for p in base["parts"]]
        h["build"] = f"bend_statics variant: full pack, batteries moved {dx} mm forward and {dz} mm down"
        f = out_dir / f"batt_fwd{dx}_down{dz}.json"
        f.write_text(json.dumps(h))
        res[f"batt_fwd{dx}_down{dz}"] = f
    h = dict(base)
    h["parts"] = [p for p in base["parts"] if p["id"] not in ("battery-R", "strap-R")]
    h["build"] = "bend_statics variant: full pack with one battery (left tray), right battery and strap removed"
    f = out_dir / "one_battery_left.json"
    f.write_text(json.dumps(h))
    res["one_battery_left"] = f
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=str(HERE / "ckpt/bend_spec"))
    ap.add_argument("--manifests", default=str(HERE / "manifests"))
    ap.add_argument("--grid", type=int, default=9)
    ap.add_argument("--moves", default="20:0,40:0,60:0,0:15,0:30,40:15,60:30",
                    help="battery moves dx:dz (mm forward:down) for the hardware variants")
    ap.add_argument("--loads", default="", help="comma list of load names to run (default all); results merge into --out")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    M = Path(a.manifests)
    moves = [tuple(int(v) for v in s.split(":")) for s in a.moves.split(",") if s]
    loads = {k: M / v for k, v in LOADS.items()}
    loads.update(variant_manifests(M, HERE / "logs/bend_variants", moves))
    if a.loads:
        loads = {k: v for k, v in loads.items() if k in a.loads.split(",")}
    import time
    t0 = time.time()
    cache = HERE / "logs/bend_trace.json"  # one probe episode, shared by the split jobs
    if cache.exists():
        tr = json.loads(cache.read_text())
    else:
        rec, r = trace(a.models, M / LOADS["none"])
        tr = dict(names=rec["names"], rows=rec["rows"], fell_at=r["fell_at"], max_tilt=r["max_tilt"],
                  groundpick=(r.get("probe") or {}).get("groundpick") or {})
        cache.write_text(json.dumps(tr))
    print(f"[statics] trace {len(tr['rows'])} poses, {time.time() - t0:.0f} s", flush=True)
    names, rows = tr["names"], np.array(tr["rows"])
    out = Path(a.out)
    res = json.loads(out.read_text()) if out.exists() else {}
    res["trace"] = dict(episode=dict(fell_at=tr["fell_at"], max_tilt=tr["max_tilt"]), groundpick=tr["groundpick"],
                        n_poses=len(rows), dt_s=0.04)
    res.setdefault("loads", {})
    for ld, f in loads.items():
        b, m, d, mnames = load_model(f)
        f = Path(f).name
        st = Statics(b, m, d, mnames)
        stand = {n: float(b.BRAIN_STAND[n]) for n in mnames}
        seq = []
        for row in rows:
            pose = dict(zip(names, row[1:]))
            s = st.state(pose)
            seq.append(dict(t=float(row[0]), mouth_z=round(s["mouth_z"], 4), com_margin_mm=round(1000 * s["com_margin"], 1),
                            trunk_pitch_deg=round(s["trunk_pitch_deg"], 1), tau=s["tau"], penetration=st.penetration()))
        stat = lambda key: max(abs(x["tau"][key]) for x in seq)
        lo = min(seq, key=lambda x: x["mouth_z"])
        st.place(dict(stand))
        st.penetration()
        n_coll = len(st._coll)
        entry = dict(manifest=f, total_kg=round(float(m.body_subtreemass[0]), 4), mirror=st.mirror,
                     collision_geoms_checked=n_coll,
                     traced_poses_flagged_by_the_filter=sum(x["penetration"] is not None for x in seq),
                     stand=st.state(dict(stand)),
                     traced=dict(max_abs_tau={n: round(stat(n), 3) for n in seq[0]["tau"]},
                                 at_lowest_mouth=lo, sequence=seq[::5]))
        # search: legs mirrored, hip pitch / knee / ankle / neck pitch / head pitch over their joint ranges
        rng = {}
        for n in ("left_hip_pitch", "left_knee", "left_ankle", "neck_pitch", "head_pitch"):
            jr = m.jnt_range[st.jid[n]]
            rng[n] = np.linspace(jr[0], jr[1], a.grid)
        best_hip, best_all, n_ok = None, None, 0
        bend_like = []  # D-027: a forward bend at the hips (trunk nose-down >= 20 deg, hips flexed as groundpick61's)
        base = {n: stand[n] for n in mnames}
        # second, finer set around the traced lowest pose (+-0.5 rad, 7 values per joint, inside the joint range)
        pm = tr["groundpick"].get("pose_at_min") or {}
        fine = {n: np.clip(np.linspace(pm.get(n, stand[n]) - 0.5, pm.get(n, stand[n]) + 0.5, 7),
                           m.jnt_range[st.jid[n]][0], m.jnt_range[st.jid[n]][1]) for n in rng}
        combos = itertools.chain(itertools.product(*rng.values()), itertools.product(*fine.values()))
        for vals in combos:
            pose = mirror_pose(base, dict(zip(rng, vals)), stand, st.mirror)
            s = st.state(pose, gate=True)
            if s is None:
                continue
            n_ok += 1
            hip = max(abs(s["tau"]["left_hip_pitch"]), abs(s["tau"]["right_hip_pitch"]))
            worst = max(abs(s["tau"][k]) for k in s["tau"] if k.startswith(("left_", "right_")))  # leg pitch joints
            cand = dict(pose={k: round(float(v), 3) for k, v in zip(rng, vals)}, mouth_z=round(s["mouth_z"], 4),
                        com_margin_mm=round(1000 * s["com_margin"], 1), trunk_pitch_deg=round(s["trunk_pitch_deg"], 1),
                        trunk_z=round(s["trunk_z"], 4), tau=s["tau"], hip_pitch_nm=round(hip, 4), worst_nm=round(worst, 4),
                        left_foot_share=round(st.s_left, 3))
            if best_hip is None or hip < best_hip["hip_pitch_nm"]:
                best_hip = cand
            if best_all is None or worst < best_all["worst_nm"]:
                best_all = cand
            if s["trunk_pitch_deg"] >= 20.0 and np.sign(cand["pose"]["left_hip_pitch"] - stand["left_hip_pitch"]) == \
                    np.sign(pm.get("left_hip_pitch", -1.0) - stand["left_hip_pitch"]):
                bend_like.append(cand)
        bend_like.sort(key=lambda c: c["worst_nm"])
        entry["search_bend_like"] = dict(
            n=len(bend_like), lowest_worst_joint=bend_like[0] if bend_like else None,
            lowest_hip=min(bend_like, key=lambda c: c["hip_pitch_nm"]) if bend_like else None,
            n_all_legs_under_target=sum(c["worst_nm"] <= TARGET for c in bend_like),
            n_hip_under_target=sum(c["hip_pitch_nm"] <= TARGET for c in bend_like), best5=bend_like[:5])
        entry["search"] = dict(grid=a.grid, ranges={k: [round(float(v[0]), 3), round(float(v[-1]), 3)] for k, v in rng.items()},
                               qualifying=n_ok, lowest_hip=best_hip, lowest_worst_joint=best_all,
                               feasible_under_target=bool(best_all and best_all["worst_nm"] <= TARGET),
                               hip_under_target=bool(best_hip and best_hip["hip_pitch_nm"] <= TARGET))
        res["loads"][ld] = entry
        print(f"[statics] {ld}: traced max |tau| hip {entry['traced']['max_abs_tau'].get('left_hip_pitch')} "
              f"knee {entry['traced']['max_abs_tau'].get('left_knee')}; search ok {n_ok}, lowest hip "
              f"{best_hip and best_hip['hip_pitch_nm']}, lowest worst {best_all and best_all['worst_nm']}; bend-like "
              f"{len(bend_like)}, lowest worst {bend_like[0]['worst_nm'] if bend_like else None}; "
              f"{time.time() - t0:.0f} s", flush=True)
        out.write_text(json.dumps(res, indent=1))  # after every load: a timeout keeps the finished ones


if __name__ == "__main__":
    main()
