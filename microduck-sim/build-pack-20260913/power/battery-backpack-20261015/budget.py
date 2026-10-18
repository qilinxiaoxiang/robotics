"""Battery current and runtime for the MicroDuck 2S battery backpack.

Reads loads.json (servo-rail bus current per scenario from the 7.4 V simulation, 5 V branch loads from the A7Z
research) and writes budget.json: battery current and runtime per scenario for each candidate pack.

Model:
  servo branch   = simulated bus current at 7.4 V, taken straight from the battery (no converter)
  5 V branch     = P_5V / eta_buck at the battery (DFR1202, eta from loads.json)
  battery energy = capacity_mAh * 7.4 V * usable fraction (stop at 3.5 V/cell under load, cells aged)
Runtime is a continuous-operation figure for one scenario; real sessions mix scenarios.
"""
import json
import pathlib

HERE = pathlib.Path(__file__).parent
loads = json.loads((HERE / "loads.json").read_text())

V_NOM = 7.4
eta = loads["buck_efficiency"]
usable = loads["usable_energy_fraction"]
packs = loads["packs"]

rows = []
for sc in loads["scenarios"]:
    servo_a = sc["servo_bus_a"]
    p5 = sc["five_volt_w"]
    batt_w = servo_a * V_NOM + p5 / eta
    batt_a = batt_w / V_NOM
    row = {"scenario": sc["name"], "servo_bus_a": servo_a, "five_volt_w": p5,
           "battery_w": round(batt_w, 2), "battery_a": round(batt_a, 2), "runtime_min": {}}
    for p in packs:
        wh = p["mah"] / 1000 * V_NOM * usable
        row["runtime_min"][p["name"]] = round(wh / batt_w * 60, 1)
    rows.append(row)

peak = loads["peak"]
peak_a = peak["servo_bus_a"] + peak["five_volt_w"] / eta / V_NOM
out = {"inputs": "loads.json", "v_nominal": V_NOM, "buck_efficiency": eta, "usable_energy_fraction": usable,
       "scenarios": rows,
       "peak_battery_a": round(peak_a, 2),
       "peak_c_rate": {p["name"]: round(peak_a / (p["mah"] / 1000), 1) for p in packs}}
(HERE / "budget.json").write_text(json.dumps(out, indent=1) + "\n")
for r in rows:
    print(f"{r['scenario']:<22} servo {r['servo_bus_a']:5.2f} A  5V {r['five_volt_w']:4.1f} W  "
          f"battery {r['battery_a']:5.2f} A  " + "  ".join(f"{k} {v:5.1f} min" for k, v in r["runtime_min"].items()))
print(f"peak battery current {peak_a:.2f} A; C-rate " + ", ".join(f"{k} {v}C" for k, v in out["peak_c_rate"].items()))
