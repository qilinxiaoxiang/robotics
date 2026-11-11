"""Every number shown on the flying-duck design pages (Chinese and English), read from the project's source files.

build_design.py fills {{key}} in design-template.html (zh) and design-template-en.html (en) from facts(), so the two
languages cannot carry different numbers. Each block names its source; nothing here is typed in by hand except the
labels of where a number comes from.
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

H = Path(__file__).resolve().parent
SIM = H.parents[1]


def J(p):
    return json.loads((H / p).read_text())


def r0(x):
    return f"{x:.0f}"


def r1(x):
    return f"{x:.1f}"


def r2(x):
    return f"{x:.2f}"


def facts() -> dict:
    F: dict[str, str] = {}
    state = json.loads((SIM / "CURRENT-STATE.json").read_text())["facts"]
    parts = state["parts_flight_pack"]["value"]
    F["state_verified"] = state["parts_flight_pack"]["verified_at"]

    # ---------------------------------------------------------------- release and print
    st = J("cad/slices/release-FlightPack-D1/STATUS.json")
    F["release"] = st["version"]
    F["release_checked"] = st["checked"][:10]
    g = J("cad/slices/grams.json")
    F["orange_h2s_time"] = g["plates"]["Orange"]["H2S"]["time"]
    F["orange_h2s_g"] = r0(g["plates"]["Orange"]["H2S"]["grams"])
    F["black_h2s_time"] = g["plates"]["Black"]["H2S"]["time"]
    F["black_h2s_g"] = r0(g["plates"]["Black"]["H2S"]["grams"])
    printed = g["parts"]
    F["printed_g"] = r0(sum(printed.values()))
    for k, v in printed.items():
        F[f"g_{k}"] = r0(v)

    # ---------------------------------------------------------------- mass and centre of mass
    # pack: mass_budget.json v7 case (current fan set), printed parts replaced by the release slicer grams
    case = J("mass_budget.json")["cases"]["v7 CAD, ARESWEI_HDS001 fans 77 g"]
    rows = [dict(p, g=printed.get(p["name"], p["g"])) for p in case]
    pack = sum(p["g"] for p in rows)
    com_pack = [sum(p["g"] * p["pos"][i] for p in rows) / pack for i in range(3)]
    mr = J("sim/out/mass_report.json")
    duck = mr["duck_without_pack"]["mass_g"]
    com_duck = [mr["duck_without_pack"]["com_trunk_mm"][0], mr["duck_without_pack"]["com_trunk_mm"][1],
                mr["duck_without_pack"]["com_trunk_mm"][2] + 120.0]
    tot = duck + pack
    com_tot = [(duck * com_duck[i] + pack * com_pack[i]) / tot for i in range(3)]
    grp = collections.OrderedDict()
    for p in rows:
        n = p["name"]
        k = ("fans" if n.startswith("fan ") else "batteries" if n.startswith("battery") else
             "printed" if n in printed else "stack" if n.startswith(("FC", "ESC")) else "flow" if n.startswith("flow") else
             "leads" if "leads" in n else "hardware")
        grp[k] = grp.get(k, 0) + p["g"]
    F.update(duck_g=r0(duck), pack_g=r0(pack), total_g=r0(tot), total_kg=r2(tot / 1000),
             pack_fans_g=r0(grp["fans"]), pack_batt_g=r0(grp["batteries"]), pack_printed_g=r0(grp["printed"]),
             pack_stack_g=r0(grp["stack"]), pack_flow_g=r1(grp["flow"]), pack_leads_g=r0(grp["leads"]),
             pack_hw_g=r0(grp["hardware"]),
             com_duck_x=r1(com_duck[0]), com_duck_z=r0(com_duck[2]), com_tot_x=r1(com_tot[0]), com_tot_z=r0(com_tot[2]),
             com_shift_x=r1(com_duck[0] - com_tot[0]), com_rise_z=r0(com_tot[2] - com_duck[2]),
             sim_pack_g=r1(mr["pack"]["mass_g"]), sim_total_g=r1(mr["duck_with_pack"]["mass_g"]),
             sim_printed_g=r1(mr["pack"]["by_group_g"]["print"]),
             iner_duck=f'{mr["duck_without_pack"]["inertia_about_com_kgm2"]["xx"]:.4f}',
             iner_pack=f'{mr["duck_with_pack"]["inertia_about_com_kgm2"]["xx"]:.4f}',
             iner_ratio=r1(mr["duck_with_pack"]["inertia_about_com_kgm2"]["xx"] / mr["duck_without_pack"]["inertia_about_com_kgm2"]["xx"]))
    F["mass_gap_g"] = r0(pack - mr["pack"]["mass_g"])

    # ---------------------------------------------------------------- fans, thrust, current, endurance
    w = J("wiring/wiring.json")
    fan = w["fan"]
    F.update(fan_thrust_g=r0(fan["thrust_g"]), fan_V=r1(fan["thrust_V"]), fan_peak_A=r0(fan["peak_A"]),
             fan_mass_g=r0(fan["mass_g"]), fan_kv=r0(fan["kv"]), fan_rotor=r0(fan["rotor_mm"]))
    twr = 4 * fan["thrust_g"] / tot
    F["twr_vendor"] = r2(twr)
    F["hover_per_fan_g"] = r0(tot / 4)
    F["hover_share_pct"] = r0(tot / 4 / fan["thrust_g"] * 100)
    F["twr_two_thirds"] = r2(twr * 2 / 3)
    cur = w["currents"]
    lo, hi = cur["hover_A_total"]
    F.update(hover_A_lo=r0(lo), hover_A_hi=r0(hi), hover_A_fan_lo=r0(cur["hover_A_per_fan"][0]),
             hover_A_fan_hi=r0(cur["hover_A_per_fan"][1]), curr_cap=r0(cur["cap_MOT_BAT_CURR_MAX"]))
    cap_mah = 2 * 1300
    use = 0.8 * cap_mah / 1000
    F.update(batt_mah=r0(cap_mah), batt_wh=r0(cap_mah / 1000 * 14.8), hover_min_lo=r1(use / hi * 60), hover_min_hi=r1(use / lo * 60))

    # flight simulation, full sequence with the leg hand-over (sim/out/fullseq_handover/summary.json)
    fs = J("sim/out/fullseq_handover/summary.json")["summary"]
    def tally(prefix):
        n = sum(fs[k]["n"] for k in fs if k.startswith(prefix + "|"))
        a = sum(fs[k]["airborne_success"] for k in fs if k.startswith(prefix + "|"))
        f = sum(fs[k]["full_success"] for k in fs if k.startswith(prefix + "|"))
        return n, a, f
    for key, pre in (("nom", "ARE_nominal"), ("t90", "ARE_thrust90"), ("t80", "ARE_thrust80")):
        n, a, f = tally(pre)
        F[f"sim_{key}_n"], F[f"sim_{key}_air"], F[f"sim_{key}_full"] = str(n), str(a), str(f)
    # why 80 % failed (sim/README.md "Why 80 % thrust fails here", sim/out/t80_diag/): the stand-in controller assumed vendor
    # thrust. Each batch: thrust fraction delivered, thrust the controller is told (--ctl-thrust-known, absent = vendor), legs
    def batch(d):
        j = J(f"sim/out/t80_diag/{d}/summary.json")
        s, fx = j["summary"], j["fix"]
        opt = lambda n, a: a[a.index(n) + 1] if n in a else None
        case = next(iter(s)).split("|")[0]
        thrust = float(opt("--thrust", fx) or opt("--thrust", j["cases"][case]) or 1.0)
        known = opt("--ctl-thrust-known", fx)
        return dict(thrust=thrust, known=float(known) if known else None, n=sum(v["n"] for v in s.values()),
                    air=sum(v["airborne_success"] for v in s.values()), full=sum(v["full_success"] for v in s.values()),
                    twr=min(v["thrust_to_weight"] for v in s.values()))
    pct = lambda x: r0(100 * x)
    for key, d in (("ho80", "handover_known80"), ("cap", "held_cap0.87"), ("k70", "held_known0.7"), ("k60", "held_known0.6"),
                   ("u85", "held_unknown0.85"), ("u75", "held_unknown0.75")):
        b_ = batch(d)
        F.update({f"t80d_{key}_pct": pct(b_["thrust"]), f"t80d_{key}_n": str(b_["n"]), f"t80d_{key}_air": str(b_["air"]),
                  f"t80d_{key}_full": str(b_["full"]), f"t80d_{key}_twr": r2(b_["twr"])})
        if b_["known"]:
            F[f"t80d_{key}_known"] = r2(b_["known"])
    k80 = [J(str(p.relative_to(H))) for p in sorted(H.glob("sim/out/t80_diag/known80__*__s*.json"))]
    F.update(t80d_k80_n=str(len(k80)), t80d_k80_air=str(sum(x["airborne_success"] for x in k80)),
             t80d_k80_pct=pct(k80[0]["params"]["thrust"]))
    assert all(x["params"]["thrust"] == x["params"]["ctl_thrust_known"] == k80[0]["params"]["thrust"] for x in k80)
    hf = {k: J(f"sim/out/t80_diag/{f}.json")["hover_thrust_frac"] for k, f in
          (("nom", "nominal__hover__s0"), ("t90", "base90__hover__s0"), ("t80", "known80__hover__s0"))}
    F.update(hover_frac_nom=pct(hf["nom"]), hover_frac_t90=pct(hf["t90"]), hover_frac_t80=pct(hf["t80"]))
    F["ap_thst_hover_max"] = "0.6875"   # ArduPilot MOT_THST_HOVER upper limit (parameter list; AP_MotorsMulticopter.h)
    F["sim_robot_g"] = r1(J("sim/out/t80_diag/nominal__hover__s0.json")["mass_g"])
    F["mass_gap_pct"] = r0(100 * (float(F["total_g"]) - float(F["sim_robot_g"])) / float(F["sim_robot_g"]))
    nom = [fs[k] for k in fs if k.startswith("ARE_nominal|")]
    F.update(sim_throttle=r0(max(x["hover_throttle_pct"] for x in nom)), sim_twr=r2(min(x["thrust_to_weight"] for x in nom)),
             sim_hover_A=r0(max(x["hover_current_a"] for x in nom)), sim_flight_s=r0(max(x["flight_s"] for x in nom)),
             sim_mah=r0(max(x["mah_used"] for x in nom)), sim_drift=r2(max(x["takeoff_drift_max_m"] for x in nom)),
             sim_vz=r2(max(-x["touchdown_vz_worst"] for x in nom)), sim_tilt=r0(max(x["max_tilt_deg"] for x in nom)),
             sim_trips=r0(0.8 * cap_mah / max(x["mah_used"] for x in nom)),
             sim_esc_peak=r0(max(x["esc_channel_peak_a"] for x in nom)), sim_pack_peak=r0(max(x["pack_current_peak_a"] for x in nom)))

    # ---------------------------------------------------------------- geometry
    pm = J("pack_meshes.json")
    b = pm["bounds"]
    F.update(width=r0(b["nacelle_outer_L"][1][1] - b["nacelle_outer_R"][0][1]), nac_top=r0(b["nacelle_outer_L"][1][2]),
             nac_bottom=r0(b["nacelle_outer_L"][0][2]), nac_len=r0(b["nacelle_outer_L"][1][0] - b["nacelle_outer_L"][0][0]),
             nac_y_in=r0(b["nacelle_inner_L"][0][1]), nac_y_out=r0(b["nacelle_outer_L"][1][1]),
             cant=r0(pm["cant_deg"]),
             fan_x_front=r0(pm["fans"]["front_L"]["lip"][0]), fan_x_rear=r0(pm["fans"]["rear_L"]["lip"][0]),
             fan_y=r0(pm["fans"]["front_L"]["lip"][1]),
             fan_pitch=r0(pm["fans"]["front_L"]["lip"][0] - pm["fans"]["rear_L"]["lip"][0]),
             lip_top=r0(195.0),
             batt_x0=r0(b["dummy_battery_L"][0][0]), batt_x1=r0(b["dummy_battery_L"][1][0]),
             batt_y0=r1(b["dummy_battery_L"][0][1]), batt_y1=r1(b["dummy_battery_L"][1][1]),
             batt_z0=r0(b["dummy_battery_L"][0][2]), batt_z1=r0(b["dummy_battery_L"][1][2]),
             wing_x0=r0(b["wing_plate"][0][0]), wing_x1=r0(b["wing_plate"][1][0]), wing_y=r0(b["wing_plate"][1][1]),
             wing_ztop=r1(b["wing_plate"][1][2]),
             fc_x0=r0(b["dummy_fc_esc_stack"][0][0]), fc_x1=r0(b["dummy_fc_esc_stack"][1][0]),
             fc_y0=r1(b["dummy_fc_esc_stack"][0][1]), fc_y1=r1(b["dummy_fc_esc_stack"][1][1]),
             fc_z0=r0(b["dummy_fc_esc_stack"][0][2]), fc_z1=r0(b["dummy_fc_esc_stack"][1][2]),
             mtf_x=r0((b["dummy_mtf01"][0][0] + b["dummy_mtf01"][1][0]) / 2), mtf_y=r0((b["dummy_mtf01"][0][1] + b["dummy_mtf01"][1][1]) / 2),
             mtf_z=r0(b["dummy_mtf01"][0][2]))
    con = J("cad/DESIGN-CONTRACT.json")
    for gm in con["geometry"]:
        if gm["part"] == "wing_plate_mid":
            F["mid_zmax"] = r0(gm["bounds"]["z_max"]["lt"] + 120)
        if gm["part"] == "wing_plate_centre":
            F["centre_t"] = r1(gm["bounds"]["x_max"]["lt"] - gm["bounds"]["x_min"]["gt"] - 0.1)

    # ---------------------------------------------------------------- screws
    sc = J("cad/build/screws.json")
    cnt = collections.Counter()
    for s in sc:
        sp = s["spec"]
        key = ("post" if sp.startswith("M2 x 12 (existing") else "clamp" if sp.startswith("M2 x 12 (with") else
               "lug" if s["id"].startswith("lug") else "tray" if s["id"].startswith("tray") else
               "fcb" if s["step"].startswith("FC bracket") else "mtf" if s["step"] == "flow module" else "stack")
        cnt[key] += 1
        F[f"spec_{key}"] = re.match(r"(M\d x \d+)", sp).group(1).replace(" x ", "×")
    for k, v in cnt.items():
        F[f"n_{k}"] = str(v)
    post = next(s for s in sc if s["id"] == "post-0")
    F["post_through"] = r1(post["through_mm"])
    F["post_bite"] = r1(12 - post["through_mm"])

    # ---------------------------------------------------------------- strength (strength/results.json)
    res = J("strength/results.json")
    sbc = res["summary_by_case"]
    def minsf(case, keys=("wing root L", "wing root R", "wing column/arm L", "wing column/arm R")):
        return min(sbc[case][k]["sf"] for k in keys if k in sbc[case])
    F.update(sf_target=r0(res["sf_target"]) if isinstance(res["sf_target"], (int, float)) else "2",
             sf_thrust=r1(minsf("thrust_1.5x_on_ground")), sf_lift_L=r2(sbc["handling_lift_by_nacelle"]["wing root L"]["sf"]),
             sf_lift_R=r2(sbc["handling_lift_by_right_nacelle"]["wing root R"]["sf"]),
             sf_lug_lift=r2(sbc["handling_lift_by_nacelle"]["lug screws"]["sf"]),
             sf_lug_thrust=r2(sbc["thrust_1.5x_on_ground"]["lug screws"]["sf"]),
             sf_post_thrust=r1(sbc["thrust_1.5x_on_ground"]["post screws"]["sf"]),
             sf_land=r2(minsf("vertical_impact_15.6g")), sf_topple=r2(minsf("topple_strike_front_end")))

    # ---------------------------------------------------------------- clearance (cad/checks/check_parts.json)
    cp = J("cad/checks/check_parts.json")["moving"]
    def clear(case):
        best = None
        for part, rowd in cp.items():
            r = rowd.get(case)
            if r and (best is None or r["min_mm"] < best[0]):
                best = (r["min_mm"], part)
        return best
    F["clr_stand_legs"] = r0(clear("stand: legs")[0])
    F["clr_stand_head"] = r0(clear("stand: head")[0])
    F["clr_bend_legs"] = r0(clear("logged real bend poses (1046 rows): legs")[0])
    F["clr_scan"] = r1(clear("head scan poses of pickup.py (yaw to +-1.2 rad, looking down)")[0])
    F["clr_yaw"] = r0(clear("head yaw alone, full +-170 deg, stand pitch")[0])
    F["bend_rows"] = "1046"

    # ---------------------------------------------------------------- walking, bending, head (train/out)
    sbh = J("train/out/style_bend_head.json")
    t = sbh["toe"]
    F.update(toe_pack_L=r0(t["toe_fq2_pack_walk"]["left_stance_toe_out_deg_mean"]),
             toe_pack_R=r0(t["toe_fq2_pack_walk"]["right_stance_toe_out_deg_mean"]),
             toe_ref_L=r0(t["toe_spec_none_walk"]["left_stance_toe_out_deg_mean"]),
             toe_ref_R=r0(t["toe_spec_none_walk"]["right_stance_toe_out_deg_mean"]),
             width_pack=r0(t["toe_fq2_pack_walk"]["step_width_mm"]), width_ref=r0(t["toe_spec_none_walk"]["step_width_mm"]),
             walk_pack_eps=str(t["toe_fq2_pack_walk"]["episodes"]), walk_pack_falls=str(t["toe_fq2_pack_walk"]["falls"]),
             walk_pack_speed=r2(t["toe_fq2_pack_walk"]["speed_median_upright"]),
             bend_pack_eps=str(sbh["bend"]["bend_gp_fq2_pack"]["episodes"]), bend_pack_falls=str(sbh["bend"]["bend_gp_fq2_pack"]["falls"]))
    hd = sbh["head"]
    F["head_falls"] = str(sum(hd[k]["falls"] for k in hd if k.endswith("fq2_pack")))
    F["head_eps"] = str(sum(hd[k]["episodes"] for k in hd if k.endswith("fq2_pack")))

    # bend statics: gravity-only torques along the logged groundpick61 path (train/out/bend_statics.json)
    bs = J("train/out/bend_statics.json")["loads"]
    lim = float(re.search(r"^LIMIT = ([\d.]+)", (H / "train" / "bend_statics.py").read_text(), re.M).group(1))
    for key, case in (("full", "full"), ("none", "none")):
        t_ = {k: v for k, v in bs[case]["traced"]["max_abs_tau"].items() if k.split("_", 1)[1] in ("hip_pitch", "knee", "ankle")}
        jn = max(t_, key=t_.get)
        F[f"bend_tau_{key}"] = r2(t_[jn])
        F[f"bend_joint_{key}"] = jn.split("_", 1)[1]
    F["servo_limit"] = r2(lim)
    F["bend_pct_full"] = r0(float(F["bend_tau_full"]) / lim * 100)

    # flight controller parameters (wiring/wiring.json "parameters")
    for p in next(iter(w["parameters"].values())):
        F["p_" + re.sub(r"\W", "_", p["name"])] = str(p["value"])

    # purchase status codes; build_design.py words them per language
    def code(key):
        s = parts[key]["status"].lower()
        if "roboclub stock" in parts[key].get("seller", "").lower():
            return "roboclub"
        if s.startswith("removed"):
            return "removed"
        if "unticked" in s:
            return "unticked"
        if s.startswith("ordered"):
            return "ordered"
        if s.startswith("carted"):
            return "carted"
        if s.startswith(("in hand", "fitted")):
            return "inhand"
        raise ValueError(f"{key}: unknown status {s[:40]}")
    for key, short in (("edf_fans_areswei_hds001_4650kv", "fans"), ("batteries_cnhl_4s_1300_130c", "batt"),
                       ("fc_esc_micoair743v2_stack", "stack"), ("optical_flow_mtf01", "mtf"), ("compass_m10g_5883", "compass"),
                       ("charger_htrc_b6_v2", "charger"), ("esc_capacitor_1000uf_35v", "cap"), ("battery_straps", "straps"),
                       ("sh1_cable_kit", "shkit"), ("fan_bullets_amass_3p5mm", "bullets"),
                       ("stack_m3_nylon_kit_avrestypt_610", "standoffs"), ("uart_lead_qwiic_kit_minidodca", "uartlead"),
                       ("lug_screws_m3x12_steel", "lugscrews"), ("xt60h_male_pigtails", "xt60")):
        F[f"st_{short}"] = code(key)

    # ---------------------------------------------------------------- money (CURRENT-STATE parts_flight_pack)
    def price(key):
        return [float(x) for x in re.findall(r"\$(\d+\.\d\d)", parts[key]["price"])]
    fans_total = float(re.search(r"order total \$(\d+\.\d\d)", parts["edf_fans_areswei_hds001_4650kv"]["status"]).group(1))
    pyro = float(re.search(r"subtotal \$(\d+\.\d\d)", state["parts_flight_pack"]["source"]).group(1))
    ship = float(re.search(r"Priority Mail \$(\d+\.\d\d)", state["parts_flight_pack"]["source"]).group(1))
    carted = [k for k, v in parts.items() if v["status"].startswith("carted")]
    amz = sum(price(k)[-1] for k in carted)
    F.update(usd_fans=r2(fans_total), usd_pyro=r2(pyro), usd_ship=r2(ship), usd_amazon_carted=r2(amz),
             usd_cap=r2(price("esc_capacitor_1000uf_35v")[0]), n_amazon_carted=str(len(carted)),
             usd_ordered=r0(fans_total + pyro + ship))
    F["fan_arrive"] = re.search(r"arriving \w+ (\d{4}-\d{2}-\d{2})", parts["edf_fans_areswei_hds001_4650kv"]["status"]).group(1)
    F["usd_stack"] = r2(price("fc_esc_micoair743v2_stack")[0])
    F["usd_batt"] = r2(price("batteries_cnhl_4s_1300_130c")[-1])
    F["usd_mtf"] = r2(price("optical_flow_mtf01")[0])
    F["usd_charger"] = r2(price("charger_htrc_b6_v2")[0])

    # ---------------------------------------------------------------- requirements
    req = {r["id"]: r for r in J("REQUIREMENTS.json")["requirements"]}
    F["n_req"] = str(len(req))
    return F


if __name__ == "__main__":
    for k, v in facts().items():
        print(f"{k} = {v}")
