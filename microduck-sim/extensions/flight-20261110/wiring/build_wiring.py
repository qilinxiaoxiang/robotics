#!/usr/bin/env python3
"""Pin-level wiring of the MicroDuck flight pack: one source for wiring.json, MISSING.md, SOLDERING.md and wiring.html.

Run with the project venv:
    /Users/xiangzheng/code/robotics/microduck-sim/microduck_rl/.venv/bin/python build_wiring.py

Inputs (read only): ../cad/flight_params.py and ../cad/build_pack.py (positions, guide frame, mm: x forward, y left,
z up; stand-world z = guide z + 120), ../mass_budget.json (v6 cases), ../procurement.json, ../../../CURRENT-STATE.json
(A7Z pins in use come from ../../../bringup/a7z/a7z_bench.py, the as-built header map). Board pictures are the makers'
own images saved in sources/ (URLs in SOURCES). The page uses ~/code/wiring-kit (the same drawing route as the A7Z
bring-up pages, bench helpers from bringup/a7z/touch_bench.py), inlined, no network fetch.
"""
from __future__ import annotations

import html
import json
import math
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True          # never write __pycache__ into cad/ or bringup/

HERE = Path(__file__).resolve().parent
FLIGHT = HERE.parent
MS = FLIGHT.parents[1]                  # microduck-sim
sys.path.insert(0, str(FLIGHT / 'cad'))
sys.path.insert(0, str(MS / 'bringup' / 'a7z'))
import flight_params as FP              # noqa: E402
import touch_bench as TB                # noqa: E402
import a7z_bench as AB                  # noqa: E402

from PIL import Image                   # noqa: E402

CHECKED = '2026-11-10'

# ====================================================================== sources
SOURCES = {
    'ap_hwdef': dict(url='https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_HAL_ChibiOS/hwdef/MicoAir743v2/hwdef.dat',
                     local='sources/ardupilot-MicoAir743v2-hwdef-master.dat',
                     quote='SERIAL_ORDER OTG1 USART1 USART2 USART3 UART4 UART5 USART6 UART7 UART8; define HAL_BATT_CURR_SCALE 40.2'),
    'ap_hwdef_463': dict(url='https://github.com/ArduPilot/ardupilot/blob/Copter-4.6.3/libraries/AP_HAL_ChibiOS/hwdef/MicoAir743v2/hwdef.dat',
                         quote='target present in the Copter-4.6.3 release tag (same UART order and battery defines)'),
    'ap_readme': dict(url='https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_HAL_ChibiOS/hwdef/MicoAir743v2/README.md',
                      local='sources/ardupilot-MicoAir743v2-README.md',
                      quote='SERIAL1 -> UART1 (MAVLink2, DMA-enabled) ... SERIAL4 -> UART4 (MAVLink2, DMA-enabled) ... SERIAL7 -> UART7 (RX only, ESC Telemetry)'),
    'ap_ports': dict(url='https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_HAL_ChibiOS/hwdef/MicoAir743v2/MicoAir743v2_Ports_Connection.jpg',
                     local='sources/micoair743v2-ports-ardupilot.jpg',
                     quote='ESC socket labels Curr, RX7, M4, M3, M2, M1, VBAT, GND (silk C R 4 3 2 1 V G); UART4 GND 5V TX4 RX4; UART1 GND 5V TX1 RX1'),
    'mico_fc': dict(url='https://micoair.com/en/docs/flight-controller/micoair743/micoair743v2-flight-controller-manual',
                    quote='Dual 5 V / 3 A and 12 V / 3 A BECs ... Connect flight-controller TX to peripheral RX, and flight-controller RX to peripheral TX ... BATT_CURR_SCALE 40.2 ... do not apply to every ESC'),
    'mico_esc': dict(url='https://micoair.com/en/docs/esc/55a-am32-esc',
                     quote='Maximum continuous current: 55 A x 4 channels ... Current-sensor output: 12.75 mV/A ... NC: no connection required ... VBAT: battery-voltage output'),
    'mico_esc_img': dict(url='https://micoair.com/api/media/file/docs/2026/07/67d3e95c068ba-fd56fc7cb1.png',
                         local='sources/micoair-55a-esc-dimensions.png',
                         quote='SH1.0-8P pin row Curr NC M4 M3 M2 M1 VBAT GND; motor pad groups 1-4 at the corners; + and - battery tabs'),
    'mico_esc_wiring': dict(url='https://micoair.com/api/media/file/docs/2026/07/67d3eb2826e2a-d00354e597.png',
                            local='sources/micoair-55a-esc-wiring.png',
                            quote='maker wiring diagram: straight 8-wire lead Curr-Curr, NC-Rx7, M4-M4, M3-M3, M2-M2, M1-M1, VBAT-VBAT, GND-GND; capacitor across the battery tabs'),
    'mico_esc_am32': dict(url='https://micoair.com/api/media/file/docs/2026/07/67edfc009328d-55af8ec36a.png',
                          quote='AM32 configurator per-ESC checkboxes "Reversed", "3D mode"; Motor KV 2220, Motor poles 14 (defaults)'),
    'mico_mtf': dict(url='https://micoair.com/en/docs/sensors/sensors/mtf-01-sensors',
                     quote='LVTTL (3.3 V) UART, 115200 baud ... Supply voltage: 5 V ... Rx: connect to the FC UART Tx; Tx: connect to the FC UART Rx ... SERIALn_BAUD 115, SERIALn_OPTIONS 1024, SERIALn_PROTOCOL 1, FLOW_TYPE 5, RNGFND1_TYPE 10, RNGFND1_MAX_CM 800, RNGFND1_MIN_CM 1, RNGFND1_ORIENT 25'),
    'mico_mtf_pins': dict(url='https://micoair.com/api/media/file/docs/2026/10/6694fd5a8d782-d7cef158a6-0b3f2a03d3.webp',
                          local='sources/mtf01-pins.png', quote='SH1.0-4P: GND, 5V, Rx, Tx'),
    'mico_mtf_wiring': dict(url='https://micoair.com/api/media/file/docs/2026/10/669a25d2736c0-418cf76b4c-98ef6f222b.webp',
                            local='sources/mtf01-micoair743-wiring.png',
                            quote='MicoAir743: MTF-01 GND/5V/Rx/Tx to UART4 GND/5V/Tx4/Rx4 (straight lead)'),
    'ap_motors': dict(url='https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Motors/AP_MotorsMatrix.cpp',
                      quote='QUAD MOTOR_FRAME_TYPE_X: {45, CCW, 1}, {-135, CCW, 3}, {-45, CW, 4}, {135, CW, 2}  (motor 1..4: angle, spin, test order)'),
    'ap_wiki_motors': dict(url='https://ardupilot.org/copter/docs/connect-escs-and-motors.html',
                           quote='Motor Direction is reversed simply by interchanging two of the three ESC to motor power leads.'),
    'ap_gcs_fs': dict(url='https://ardupilot.org/copter/docs/gcs-failsafe.html',
                      quote='if no GCS is ever connected, the GCS failsafe will remain inactive regardless of parameter settings'),
    'ap_params_463': dict(url='https://github.com/ArduPilot/ardupilot/tree/Copter-4.6.3 (ArduCopter/Parameters.cpp, AP_Arming.cpp, AP_MotorsMulticopter.cpp, AP_BLHeli.cpp, AP_SerialManager.cpp, SRV_Channel.cpp, AP_RangeFinder_Params.cpp, AP_Math/rotations.h)',
                          quote='ARMING_CHECK bitmask 6:RC Channels; FS_THR_ENABLE 0:Disabled; FS_GCS_ENABLE 5:Land; FS_GCS_TIMEOUT range 2-120; MOT_BAT_CURR_MAX range 0-200; MOT_PWM_TYPE 5:DShot300; SERVO_BLH_POLES default 14; SERVOn_FUNCTION 33:Motor1 ... 36:Motor4; SERIALn_OPTIONS bit 10 Don\'t forward mavlink; RNGFND1_MIN_CM/MAX_CM present'),
    'radxa_pins': dict(url='https://docs.radxa.com/cubie/a7z/hardware-use/pin-gpio',
                       local='../../../guide/print/a7z-head/sources/radxa-a7z-pin-gpio.md',
                       quote='pin 16 PJ24 UART4-TX, pin 18 PJ25 UART4-RX, pin 14 GND; UART4 = /dev/ttyAS4; rsetup Overlay -> Manage overlays -> Enable UART4'),
    'radxa_uart4': dict(url='https://github.com/radxa-pkg/radxa-overlays/blob/main/arch/arm64/boot/dts/allwinner/overlays/sun60iw2p1-uart4.dtso',
                        local='sources/radxa-sun60iw2p1-uart4.dtso',
                        quote='title "Enable UART4"; compatible radxa,cubie-a7z; exclusive PJ24, PJ25, uart4; "On Radxa Cubie A7Z, this is pin 16 and pin 18."'),
    'a7z_logic': dict(url='file: microduck-sim/bringup/a7z/README.md (schematic V1.11 read 2026-10-15)',
                      quote='Page 7: ball 1L6 VCC-PJ is wired to VCC33-LCD (SWOUT1 "3.3V with ON/OFF")'),
    'a7z_bench': dict(url='file: microduck-sim/bringup/a7z/a7z_bench.py (A7Z-PINS map, as built)',
                      quote='used pins 1 2 3 4 5 6 7 9 11 12 17 25 29 31 34 35 38 39 40; 8 and 10 debug UART0 (10 carries the optional back-mic flag)'),
    'current_state': dict(url='file: microduck-sim/CURRENT-STATE.json (servo_bus_hosts, a7z_imu_bus, a7z_touch_bus, a7z_audio_capture, power)',
                          quote='A7Z over J12 UART2 /dev/ttyAS2 at 500 kbaud; overlays zz-duck-twi7-engine, zz-duck-twi0-touch, zz-duck-i2s0-din3, sun60iw2p1-i2s0-2ch; no UART4 overlay recorded'),
    'qx_listing': dict(url='https://qwinout.com/products/qx-motor-qf2611-3300-4000kv-4600kv-5000kv-brushless-motor-cw-ccw-3-4s-50mm-12-paddle-edf-ducted-fan-for-fms-rc-plane-helicopter',
                       quote='Configuration: 9N6P ... Weight: 76g ... Max continuous power: 550w ... Max continuous current: 45A; no lead length, gauge or bullet size given'),
    'qx_photo': dict(url='https://cdn.shopify.com/s/files/1/0070/9473/0823/products/QX-MOTOR-QF2611-3300-4000KV-4600KV-5000KV-Brushless-Motor-CW-CCW-3-4S-50mm-12-Paddle.jpg',
                     local='sources/qx-qf2611-leads.jpg',
                     quote='three leads red/black/yellow ending in heat-shrunk gold male bullets; scaled on the 25.8 mm can: lead OD about 1.7 mm, bullet tip about 1-2 mm (inference)'),
    'cnhl': dict(url='https://pyrodrone.com/products/cnhl-black-series-v2-0-1300mah-14-8v-4s-130c-lipo-battery-xt60',
                 quote='Discharge Rate: 130C Continual / 260C Burst ... Output Connector: XT60 ... Balance Connector: JST / XH ... Wire (AWG): 12#'),
    'stack_listing': dict(url='https://pyrodrone.com/products/micoair-743-v2-stack-with-h743-bmi088-bmi270-bluetooth-flight-controller-and-2-6s-55a-am32-4in1-esc-30x30mm',
                          quote='Package Includes: 1 x MicoAir 743 V2 Stack (no cable, capacitor or hardware listed)'),
    'sh_kit': dict(url='https://pyrodrone.com/products/diy-sh-silicone-cable-kit',
                   quote='18x Double crimped cables - 5cm / 10cm / 15cm; 3x each SH1.0 2- to 12-pin connectors'),
    'b6': dict(url='https://www.amazon.com/dp/B0G64JZ7JV',
               quote='LiPo: 1-6 cells ... What You Can Get: One RC Battery Charger; One DC Crocodile Clip; One Connector Splitter; One Adapter; One AC Power Cable ...; images: 2S-6S balance ports, banana splitter with an XT60 plug'),
    'amass_xt60': dict(url='https://datasheet.lcsc.com/datasheet/pdf/266fd4de8ced439ab8f3a91fc5a49212.pdf',
                       quote='XT60: rated 30 A, max 60 A (quoted in ../procurement.json, OCR of the Amass table)'),
    'powerstream': dict(url='https://www.powerstream.com/Wire_Size.htm',
                        quote='AWG 12: 5.20864 ohm/km, chassis 41 A; AWG 14: 8.282, 32 A; AWG 16: 13.17248, 22 A'),
    'esc_lead_practice': dict(url='https://endless-sphere.com/sphere/threads/adding-caps-to-castle-creations-escs.35420/ ; https://flyfreak.net/index.php/topic,15051.0.html',
                              quote='forum practice (not a maker spec): extend motor leads rather than battery leads; if battery leads are long, add low-ESR capacitance at the ESC, 220-440 uF per 10 cm beyond 40 cm'),
    'cad': dict(url='file: microduck-sim/extensions/flight-20261110/cad (commit 0a940d32): flight_params.py, build_pack.py, build/dummy_*-world.stl',
                quote='FC bracket plate x -67..-64 behind the right arm, stack centre (y, z) = (-56, 40), ESC envelope x -83..-77, FC x -96..-88; capacitor y -79..-54 on the right top flange; cross harness x -86.8..-50.4, y -33..37.6, z 4..28'),
    'mass_v6': dict(url='file: microduck-sim/extensions/flight-20261110/mass_budget.json (cases "v6 CAD, fans 80 g" / "113 g") and leg_load.json',
                    quote='v6 pack 927 g (80 g fans) / 1059 g (113 g fans); duck 960.5 g; totals 1887 / 2019 g'),
    'pet_log': dict(url='file: robotics/docs/PET_ROBOT_LOG.md (2026-11-10 entries)',
                    quote='vendor thrust 950 g per fan; the only independent bench tests 440-680 g; Shawn: "不用 默认推力够"'),
    'inventory': dict(url='file: robotics/roboclub/INVENTORY.md',
                      quote='Soldering bench: crimp terminals, ferrules, DuPont housings, JST XH housings + crimps, M2/M2.5/M3 screws, M3x10, M-F jumpers, solder spools; no bullets, heat-shrink, standoffs or silicone wire gauge listed'),
}

# ====================================================================== geometry (guide frame, mm)
BP_TEXT = (FLIGHT / 'cad' / 'build_pack.py').read_text()


def bp_const(name):
    m = re.search(rf'^{name}\s*=\s*(.+?)\s*(#.*)?$', BP_TEXT, re.M)
    if not m:
        raise SystemExit(f'build_pack.py: {name} not found')
    return eval(m.group(1), {'WING': FP.WING})   # constants only (numbers, tuples, WING lookups)


FCB_T = bp_const('FCB_T')
FCB_X = (FP.WING['arm_x_rear'] - FCB_T, FP.WING['arm_x_rear'])
FC_CENTRE = bp_const('FC_CENTRE')
FC_BOSS = bp_const('FC_BOSS')
CAP_Y0 = bp_const('CAP_Y0')
MTF_C = bp_const('MTF_C')
SHELF_Z = bp_const('SHELF_Z')
X0 = FCB_X[0] - FC_BOSS                       # -71: standoff tips
ESC_X = X0 - 9.0                              # -80: ESC board mid-plane (envelope x0-12 .. x0-6)
FC_X = X0 - 25.0                              # -96: FC top face (envelope x0-25 .. x0-17), connectors face rear
YC, ZC = FC_CENTRE
HS, HR = FP.WING['harness_side'], FP.WING['harness_rear']
LW, FW = FP.WING['lead_window'], FP.WING['fan_window']
CAP_C = (-57.0, CAP_Y0, FP.WING['arm_z'][1] + FP.CAP['d'] / 2)
SLACK = 1.15
FAN_LEAD = FP.FAN['lead_len']                 # 70 mm, coordinator estimate from photos (not published)

# ESC pad and tab offsets on the maker drawing (component side, tabs down), mm from the 30.5 pattern centre:
# 10.4 px/mm on micoair-55a-esc-dimensions.png, pattern centre at (370, 445.5) px.
ESC_PX, ESC_C = 10.4, (370.0, 445.5)
ESC_PADS_PX = {  # pad group: (x px, [y px of pads a (nearest the battery tabs), b, c])
    1: (157, [582, 537, 490]), 2: (157, [400, 352, 305]), 3: (577, [582, 537, 490]), 4: (577, [400, 352, 305])}
ESC_TABS_PX = {'+': (322, 660), '-': (417, 660)}
# On the robot the stack stands in the y-z plane behind the right arm, component side facing rear (-x), battery tabs UP
# toward the capacitor on the flange. Seen from behind (right of the picture = robot right, -y), the drawing is turned
# half a turn; that maps drawing (u right, v down) to world y = YC + u, z = ZC + v.


def esc_world(px):
    u, v = (px[0] - ESC_C[0]) / ESC_PX, (px[1] - ESC_C[1]) / ESC_PX
    return (ESC_X, YC + u, ZC + v)


def pad_world(group, k=0):
    x, ys = ESC_PADS_PX[group]
    return esc_world((x, ys[k]))


def fan_exit(which, side):
    """Where the three leads leave the motor front ring, on the inboard side (FAN lead_t, motor radius inboard)."""
    x, y, z = FP.fan_point(which, sum(FP.FAN['lead_t']) / 2, side)
    return (x, y - side * FP.FAN['motor_od'] / 2, z)


def polyline(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def up10(v):
    return int(math.ceil(v / 10.0) * 10)


FAN_POS = {  # name: (which, side, ArduPilot motor, spin from above, ESC pad group, ArduPilot output)
    'FR': ('front', -1, 1, 'CCW', 1, 1),
    'RR': ('rear', -1, 4, 'CW', 2, 2),
    'FL': ('front', +1, 3, 'CW', 3, 3),
    'RL': ('rear', +1, 2, 'CCW', 4, 4),
}
fan_win_mid = lambda side: (FW['y'][0] + FW['y'][1]) / 2 * side
HZ = (HS['z'][0] + HS['z'][1]) / 2           # 21: harness_side mid height
HRZ = (HR['z'][0] + HR['z'][1]) / 2          # 10: harness_rear mid height
HSY = (HS['y'][0] + HS['y'][1]) / 2          # 35.1
HRX = (HR['x'][0] + HR['x'][1]) / 2          # -83.7


def fan_route(name):
    which, side, _, _, grp, _ = FAN_POS[name]
    e = fan_exit(which, side)
    pad = pad_world(grp, 1)
    if side < 0 and which == 'front':      # along the tray top, through the right fan window, into the bay
        pts = [e, (e[0], fan_win_mid(-1), e[2]), (FP.WING['x_front'], fan_win_mid(-1), sum(FW['z']) / 2),
               (FP.WING['x_back'] - 5, fan_win_mid(-1), sum(FW['z']) / 2), pad]
    elif side < 0:                          # rear right: straight into the bay behind the web
        pts = [e, (e[0] - 5, e[1] + 10, e[2]), pad]
    else:                                   # left fans: to the harness outboard of the backpack, across behind the cap
        start = [e]
        if which == 'front':
            start += [(e[0], fan_win_mid(+1), e[2]), (FP.WING['x_front'], fan_win_mid(+1), sum(FW['z']) / 2),
                      (FP.WING['x_back'] - 2, fan_win_mid(+1), sum(FW['z']) / 2)]
        pts = start + [(HS['x'][1], HSY, HZ), (HRX, HSY, HRZ), (HRX, HR['y'][0], HRZ), (pad[0], pad[1], HRZ), pad]
    route = polyline(pts) * SLACK
    return route, pts


def battery_route(side):
    """XT60 mated pair just behind the lead window in the bay; pigtail from there to the ESC battery tab."""
    mate = (FP.WING['x_back'] - 8.0, side * sum(LW['y']) / 2, sum(LW['z']) / 2)
    tab = esc_world(ESC_TABS_PX['+'])
    if side < 0:
        pts = [mate, (mate[0] - 10, mate[1], tab[2]), tab]
    else:
        pts = [mate, (HS['x'][1], HSY, HZ), (HRX, HSY, HRZ), (HRX, HR['y'][0], HRZ), (tab[0], tab[1], HRZ), tab]
    return polyline(pts) * SLACK, pts


def a7z_route():
    """A7Z header (saddle front edge, pin 16 area) to FC UART1 (top edge of the FC). Not modelled in CAD: the lead
    follows the A7Z 5 V lead down the saddle floor opening into the torso and back to the backpack gap, then across
    to the FC; 1.25 slack because the path is not routed in CAD."""
    pin = (-15.0, 8.0, 50.0)
    fc = (FC_X, YC + 1.3, ZC + 13.3)
    pts = [pin, (-15.0, 8.0, 30.0), (-50.0, 20.0, 20.0), (-60.0, 30.0, 10.0), (-86.0, 0.0, 10.0), (-90.0, -40.0, 30.0), fc]
    return polyline(pts) * 1.25, pts


# ====================================================================== currents
def currents():
    mb = json.loads((FLIGHT / 'mass_budget.json').read_text())
    ll = json.loads((FLIGHT / 'leg_load.json').read_text())
    duck = ll['duck']['mass_g']
    pack80 = sum(p['g'] for p in mb['cases']['v6 CAD, fans 80 g'])
    pack113 = sum(p['g'] for p in mb['cases']['v6 CAD, fans 113 g'])
    m_nom, m_hi = duck + pack80, duck + pack113
    v_pack = 14.8
    p_max, t_vendor, i_fan_max = 550.0, 950.0, 45.0     # listing: 550 W, 45 A max continuous; vendor thrust 950 g
    t_bench = t_vendor * 2 / 3                           # PET log: independent tests 440-680 g; two thirds of vendor
    eta = 0.5                                            # figure of merit x motor/ESC efficiency (inference)
    area = math.pi / 4 * ((FP.FAN['bore'] / 1000) ** 2 - (FP.FAN['motor_od'] / 1000) ** 2)

    def per_fan(m, method):
        t = m / 4
        if method == 'vendor':
            return p_max * (t / t_vendor) ** 1.5 / v_pack
        if method == 'bench':
            return p_max * (t / t_bench) ** 1.5 / v_pack
        tn = t / 1000 * 9.81
        return tn ** 1.5 / math.sqrt(2 * 1.2 * area) / eta / v_pack

    rows = {meth: (per_fan(m_nom, meth), per_fan(m_hi, meth)) for meth in ('vendor', 'bench', 'momentum')}
    lo = min(v[0] for v in rows.values())
    hi = max(v[1] for v in rows.values())
    # Share between the packs: the left pigtail is longer (both conductors), pack IR assumed 12 mOhm (inference).
    r_pack = 0.012
    lr, _ = battery_route(+1)
    rr, _ = battery_route(-1)
    r12 = 5.20864e-3
    rl, rrt = r_pack + 2 * up10(lr) / 1000 * r12, r_pack + 2 * up10(rr) / 1000 * r12
    share_r = rl / (rl + rrt)
    cap_total = 110.0
    return dict(
        duck_g=duck, pack_g_80=pack80, pack_g_113=pack113, total_g_nominal=m_nom, total_g_heavy=m_hi,
        hover_thrust_per_fan_g=[round(m_nom / 4), round(m_hi / 4)],
        methods={k: [round(a, 1), round(b, 1)] for k, (a, b) in rows.items()},
        method_notes={'vendor': 'P = 550 W x (T / 950 g)^1.5 (vendor max thrust and power, momentum-theory scaling)',
                      'bench': 'same with max thrust 2/3 of vendor (independent tests of similar 50 mm fans)',
                      'momentum': f'ideal annulus power / {eta} (bore {FP.FAN["bore"]} mm, hub {FP.FAN["motor_od"]} mm)'},
        hover_A_per_fan=[round(lo, 1), round(hi, 1)], hover_A_total=[round(4 * lo), round(4 * hi)],
        peak_A_per_fan=i_fan_max, peak_A_total_uncapped=4 * i_fan_max,
        pack_share_right=round(share_r, 3),
        hover_A_right_pack=[round(4 * lo * share_r, 1), round(4 * hi * share_r, 1)],
        cap_MOT_BAT_CURR_MAX=cap_total, peak_A_right_pack_capped=round(cap_total * share_r, 1),
        peak_A_right_pack_uncapped=round(4 * i_fan_max * share_r, 1),
        assumptions='pack voltage 14.8 V nominal; pack internal resistance 12 mOhm (inference, not published); pigtail lengths from battery_route()',
    )


CUR = currents()

# ====================================================================== lengths
FAN_LEN = {}
for nm in FAN_POS:
    route, pts = fan_route(nm)
    ext = max(40, up10(route - FAN_LEAD + 10))   # 10 mm for the bullet overlap; at least 40 mm so the plug sits free
    FAN_LEN[nm] = dict(route_mm=round(route), ext_mm=ext, pts=[[round(c, 1) for c in p] for p in pts])
BAT_LEN = {}
for side, nm in ((+1, 'L'), (-1, 'R')):
    r, pts = battery_route(side)
    BAT_LEN[nm] = dict(route_mm=round(r), pigtail_mm=up10(r), pts=[[round(c, 1) for c in p] for p in pts])
A7Z_LEN, A7Z_PTS = a7z_route()
CAP_LEN = up10(math.dist(CAP_C[:1] + (CAP_C[1] + FP.CAP['h'],) + CAP_C[2:], esc_world(ESC_TABS_PX['+'])) * SLACK)
CAD_CLAIMS = {'FL': 250, 'RL': 200, 'FR': 80, 'RR': 50, 'bat_L': 220, 'bat_R': 100}

# ====================================================================== boards and pins (with sources)
BOARDS = {
    'fc': dict(name='MicoAir743v2 flight controller (top board of the stack)', where='stack behind the right arm, top face toward the rear, ESC socket at the bottom edge',
               connectors={
                   'ESC': dict(type='JST-SH 1.0 mm 8-pin socket (board), plug lead needed', pins=['Curr', 'RX7', 'M4', 'M3', 'M2', 'M1', 'VBAT', 'GND'], sources=['ap_ports', 'mico_esc_wiring']),
                   'UART4': dict(type='JST-SH 1.0 mm 4-pin socket', pins=['GND', '5V', 'TX4', 'RX4'], sources=['ap_ports', 'mico_mtf_wiring']),
                   'UART1': dict(type='JST-SH 1.0 mm 4-pin socket', pins=['GND', '5V', 'TX1', 'RX1'], sources=['ap_ports', 'ap_readme']),
                   'USB': dict(type='USB Type-C', pins=['USB'], sources=['ap_ports'])}),
    'esc': dict(name='MicoAir 55A AM32 4in1 ESC (bottom board of the stack)', where='stack behind the right arm, component side toward the rear, battery tabs UP',
                connectors={
                    'FC': dict(type='JST-SH 1.0 mm 8-pin socket', pins=['Curr', 'NC', 'M4', 'M3', 'M2', 'M1', 'VBAT', 'GND'], sources=['mico_esc_img', 'mico_esc']),
                    'BAT': dict(type='two gold battery tabs with a solder notch', pins=['+', '-'], sources=['mico_esc_img']),
                    'M1': dict(type='three solder pads', pins=['a', 'b', 'c'], sources=['mico_esc_img']),
                    'M2': dict(type='three solder pads', pins=['a', 'b', 'c'], sources=['mico_esc_img']),
                    'M3': dict(type='three solder pads', pins=['a', 'b', 'c'], sources=['mico_esc_img']),
                    'M4': dict(type='three solder pads', pins=['a', 'b', 'c'], sources=['mico_esc_img'])}),
    'mtf': dict(name='MicoAir MTF-01 optical flow + rangefinder', where='shelf under the stack, lens down',
                connectors={'J1': dict(type='JST-SH 1.0 mm 4-pin socket', pins=['GND', '5V', 'Rx', 'Tx'], sources=['mico_mtf_pins', 'mico_mtf'])}),
    'a7z': dict(name='Radxa Cubie A7Z (duck computer, roof saddle)', where='40-pin header at the saddle front edge, pin 1 at the robot-left end',
                connectors={'J11': dict(type='2.54 mm 40-pin male header', pins=['14 GND', '16 PJ24 UART4-TX', '18 PJ25 UART4-RX'], sources=['radxa_pins', 'radxa_uart4', 'a7z_bench'])}),
    'batt_L': dict(name='CNHL 4S 1300 mAh 130C, left tray', where='left battery tray, leads out the rear end through the left lead window',
                   connectors={'XT60': dict(type='XT60 on the pack lead (female, inference from the listing photo), 12 AWG', pins=['+', '-'], sources=['cnhl']),
                               'BAL': dict(type='JST-XH 5-pin balance lead', pins=['GND', 'C1', 'C2', 'C3', 'C4'], sources=['cnhl'])}),
    'batt_R': dict(name='CNHL 4S 1300 mAh 130C, right tray', where='right battery tray, leads out the rear end through the right lead window',
                   connectors={'XT60': dict(type='XT60 on the pack lead (female, inference), 12 AWG', pins=['+', '-'], sources=['cnhl']),
                               'BAL': dict(type='JST-XH 5-pin balance lead', pins=['GND', 'C1', 'C2', 'C3', 'C4'], sources=['cnhl'])}),
    'cap': dict(name='Rubycon 1000 uF 35 V low-ESR, 12.5 x 20 mm radial', where='lying on the right arm top flange (zip-tie slots), leads toward the ESC tabs',
                connectors={'LEADS': dict(type='radial legs: long leg +, stripe side -', pins=['+', '-'], sources=['mico_esc_wiring'])}),
}
for nm, (which, side, mot, spin, grp, out) in FAN_POS.items():
    BOARDS[f'fan_{nm}'] = dict(
        name=f'QX-Motor QF2611 4000KV 50 mm EDF, {"front" if which == "front" else "rear"} {"left" if side > 0 else "right"} ({spin} unit)',
        where=f'{"left" if side > 0 else "right"} nacelle, {which}', connectors={'LEADS': dict(
            type='three factory leads (red, black, yellow) with male bullets; size not published (photo scale suggests 2.0 mm)',
            pins=['red', 'black', 'yellow'], sources=['qx_photo', 'qx_listing'])})

# ====================================================================== netlist
NET = []


def end(board, conn, pin, signal, ctype, gender, joint):
    return dict(board=board, connector=conn, pin=pin, signal=signal, connector_type=ctype, gender=gender, joint=joint)


def add(id_, group, frm, to, wire, sources, verified, note='', zh=''):
    NET.append(dict(id=id_, group=group, **{'from': frm}, to=to, wire=wire, sources=sources, verified=verified,
                    verified_date=CHECKED, note=note, zh=zh))


# --- power: packs, XT60, pigtails, capacitor
for nm, side in (('R', -1), ('L', +1)):
    b = f'batt_{nm}'
    for pol, col in (('+', 'red'), ('-', 'black')):
        sig = 'VBAT+' if pol == '+' else 'VBAT-'
        add(f'xt60_{nm}{"p" if pol == "+" else "n"}', 'power',
            end(b, 'XT60', pol, sig, 'XT60 (on the pack lead)', 'female (inference)', 'plugged'),
            end(f'pigtail_{nm}', 'XT60', pol, sig, 'XT60', 'male', 'plugged'),
            dict(gauge_awg=12, colour='pack lead', length_mm=None, length_basis='mated connector, no wire', source='pack lead: in the battery box; male XT60: RoboClub stock (Shawn 2026-11-10 "XT60和线")'),
            ['cnhl', 'amass_xt60'], False, 'pack connector gender read from a listing photo only',
            f'{"左" if side > 0 else "右"}电池 XT60（母，电池自带）插尾线 XT60（公）{"+" if pol == "+" else "−"}')
        add(f'pig_{nm}{"p" if pol == "+" else "n"}', 'power',
            end(f'pigtail_{nm}', 'XT60', pol, sig, 'XT60 solder cup', 'male', 'soldered'),
            end('esc', 'BAT', pol, sig, 'battery tab', 'n/a', 'soldered'),
            dict(gauge_awg=12, colour=col, length_mm=BAT_LEN[nm]['pigtail_mm'],
                 length_basis=f'route {BAT_LEN[nm]["route_mm"]} mm incl. x{SLACK} slack ({"cross harness behind the backpack cap" if side > 0 else "bay behind the right arm web"}); CAD claim {CAD_CLAIMS["bat_" + nm]} mm',
                 source='12 AWG silicone: RoboClub stock (Shawn 2026-11-10 "XT60和线"; gauge in stock not confirmed)'),
            ['mico_esc_img', 'powerstream', 'cad'], True,
            'both pigtails land on the same ESC tab (parallel packs); twist the pair' + ('; runs in the cross harness' if side > 0 else ''),
            f'{"左" if side > 0 else "右"}尾线{"红 +" if pol == "+" else "黑 −"}：XT60 公头焊杯 → ESC {"+" if pol == "+" else "−"} 片')
for pol, col in (('+', 'red'), ('-', 'black')):
    add(f'cap_{"p" if pol == "+" else "n"}', 'power',
        end('cap', 'LEADS', pol, 'VBAT+' if pol == '+' else 'VBAT-', 'radial leg', 'n/a', 'soldered'),
        end('esc', 'BAT', pol, 'VBAT+' if pol == '+' else 'VBAT-', 'battery tab', 'n/a', 'soldered'),
        dict(gauge_awg=16, colour=col, length_mm=CAP_LEN,
             length_basis=f'capacitor lead end (y {CAP_C[1] + FP.CAP["h"]:.0f}) to the + tab, x{SLACK}; leg plus a 16 AWG extension if the leg is shorter',
             source='capacitor: Amazon cart; extension: RoboClub wire'),
        ['mico_esc_wiring', 'cad'], True, 'polarity: long leg and the side without the stripe go to +',
        f'电容{"长脚 +" if pol == "+" else "白条一侧 −"} → ESC {"+" if pol == "+" else "−"} 片')

# --- fans: ESC pads -> 16 AWG extension -> female bullet <- fan male bullet
PH = [('a', 'red', 'red'), ('b', 'yellow', 'yellow'), ('c', 'black', 'black')]
ZHC = {'red': '红', 'yellow': '黄', 'black': '黑'}
ZHF = {'FR': '右前', 'RR': '右后', 'FL': '左前', 'RL': '左后'}
for nm, (which, side, mot, spin, grp, out) in FAN_POS.items():
    for pad, lead, col in PH:
        add(f'fan_{nm}_{pad}', 'fans',
            end('esc', f'M{grp}', pad, f'motor {grp} phase {pad.upper()}', 'solder pad', 'n/a', 'soldered'),
            end(f'fan_{nm}', 'LEADS', lead, f'phase ({lead} lead)', 'bullet', 'female on the extension mates the fan male', 'plugged'),
            dict(gauge_awg=16, colour=col, length_mm=FAN_LEN[nm]['ext_mm'],
                 length_basis=f'route {FAN_LEN[nm]["route_mm"]} mm (x{SLACK}) minus the {FAN_LEAD:.0f} mm fan lead plus 10 mm; CAD claim {CAD_CLAIMS[nm]} mm',
                 source='16 AWG silicone: RoboClub stock (Shawn "XT60和线"); female bullets: NOT in stock or cart (MISSING.md)'),
            ['mico_esc_img', 'qx_photo', 'powerstream', 'cad'], False,
            'phase order is arbitrary; direction is set after the motor test (swap two leads at the bullets or AM32 Reversed)',
            f'电调 {grp}{pad} 焊盘 → {ZHC[col]}色 16 AWG 延长线 → 母子弹头，插{ZHF[nm]}风扇{ZHC[lead]}线')

# --- ESC <-> FC 8-pin
for i, (e, f) in enumerate(zip(BOARDS['esc']['connectors']['FC']['pins'], BOARDS['fc']['connectors']['ESC']['pins'])):
    add(f'escfc_{i + 1}', 'signal',
        end('esc', 'FC', i + 1, e, 'JST-SH 8-pin', 'plug on the lead', 'plugged'),
        end('fc', 'ESC', i + 1, f, 'JST-SH 8-pin', 'plug on the lead', 'plugged'),
        dict(gauge_awg=28, colour='kit lead (any colour)', length_mm=50, length_basis='ESC socket (bottom edge, x -83) to FC socket (bottom edge, x -96), round the board edge',
             source='lead from the stack box if included (not listed); else SH kit 5 cm double-crimped leads + 2 x 8-pin housings (Pyrodrone cart)'),
        ['mico_esc_img', 'ap_ports', 'mico_esc_wiring', 'stack_listing', 'sh_kit'], True,
        'straight lead: housing position n to position n' + ('; ESC NC lands on FC RX7 (no ESC telemetry; harmless)' if e == 'NC' else ''),
        f'8 针排线第 {i + 1} 位：ESC {e} ↔ 飞控 {f}')

# --- FC UART4 <-> MTF-01
for i, (f, m) in enumerate(zip(['GND', '5V', 'TX4', 'RX4'], ['GND', '5V', 'Rx', 'Tx'])):
    add(f'mtf_{i + 1}', 'signal',
        end('fc', 'UART4', i + 1, f, 'JST-SH 4-pin', 'plug on the lead', 'plugged'),
        end('mtf', 'J1', i + 1, m, 'JST-SH 4-pin', 'plug on the lead', 'plugged'),
        dict(gauge_awg=28, colour='kit lead', length_mm=100, length_basis='FC UART4 (outboard edge, about y -69, z 40) down to the MTF-01 on the shelf (z 13.5), about 50 mm direct',
             source='MTF-01 box lead if included (not stated); else SH kit 10 cm leads + 2 x 4-pin housings (cart)'),
        ['ap_ports', 'mico_mtf_pins', 'mico_mtf_wiring'], True, 'straight lead; the TX/RX cross is in the pin names', f'4 针线第 {i + 1} 位：飞控 UART4 {f} ↔ 光流 {m}')

# --- FC UART1 <-> A7Z UART4 (MAVLink)
A7Z_LINK = [('GND', '14 GND', 'p14', 'ground', 'black'), ('TX1', '18 PJ25 UART4-RX', 'p18', 'FC TX -> A7Z RX', 'yellow'),
            ('RX1', '16 PJ24 UART4-TX', 'p16', 'A7Z TX -> FC RX', 'green')]
for f, a, pid, sig, col in A7Z_LINK:
    pos = ['GND', '5V', 'TX1', 'RX1'].index(f) + 1
    add(f'mav_{f.lower()}', 'signal',
        end('fc', 'UART1', pos, f, 'JST-SH 4-pin', 'plug on the lead', 'plugged'),
        end('a7z', 'J11', int(a.split()[0]), a, '2.54 mm Dupont', 'female housing on the lead', 'plugged'),
        dict(gauge_awg=28, colour=col, length_mm=300, length_basis=f'estimate {A7Z_LEN:.0f} mm (x1.25, route not modelled in CAD: along the A7Z 5 V lead through the saddle floor and torso to the backpack gap, then across to the FC)',
             source='SH1.0 4-pin to Dupont female cable, 30 cm: NOT in a cart (MISSING.md); extra length: RoboClub M-F jumper'),
        ['ap_ports', 'radxa_pins', 'radxa_uart4', 'a7z_logic'], True, 'UART1 position 2 (5 V) stays empty: no 5 V joins the duck',
        f'飞控 UART1 {f} ↔ A7Z {a.split()[0]} 号针（{sig}）')

OPEN_PINS = [
    dict(where='fc UART1 position 2 (5V)', why='5 V rails of the two supplies must never be joined; pull the contact out of the housing or cut that wire at the housing and shrink it'),
    dict(where='a7z pins 2 and 4 (5V)', why='unchanged duck supply; nothing from the flight pack touches them'),
    dict(where='batt_L / batt_R balance leads (JST-XH 5-pin)', why='used only on the charger; tucked under the strap in flight'),
    dict(where='fc 12V pads, VTX/camera sockets, GPS socket, UART5, UART6, I2C', why='not used (no receiver, no GPS, no compass, no camera)'),
    dict(where='esc NC (8-pin position 2) -> fc RX7', why='connected by the straight lead, carries nothing (the ESC has no serial telemetry)'),
]

# ====================================================================== checks
C = CUR
CHECKS = [
    dict(id='esc_fc_cable', title='FC ESC socket vs ESC socket vs the lead', status='pass',
         evidence=('ESC socket positions 1-8: Curr, NC, M4, M3, M2, M1, VBAT, GND (maker drawing). FC socket positions 1-8: Curr, RX7, M4, M3, M2, M1, VBAT, GND '
                   '(ArduPilot port diagram, silk "C R 4 3 2 1 V G"). Maker wiring diagram draws a straight lead. On the robot both boards face rear with the sockets '
                   'on the same (bottom) edge and in the same left-right order, so a straight lead (position n to n) is correct.'),
         sources=['mico_esc_img', 'ap_ports', 'mico_esc_wiring'],
         open='Whether the stack box contains the 8-pin lead is not stated (listing: "1 x MicoAir 743 V2 Stack"); the SH kit in the cart makes one either way.'),
    dict(id='motor_map', title='ArduPilot Quad-X numbering, spin, ESC pad sets', status='pass',
         evidence=('AP_MotorsMatrix QUAD X: motor 1 at +45 deg (front right) CCW, motor 2 at -135 (rear left) CCW, motor 3 at -45 (front left) CW, motor 4 at +135 (rear right) CW. '
                   'ESC stood behind the right arm with tabs up puts pad sets 1 and 2 on the outboard (right) edge and 3 and 4 on the inboard edge, so outputs are remapped: '
                   'SERVO1_FUNCTION 33 (pad 1 -> FR, motor 1), SERVO2_FUNCTION 36 (pad 2 -> RR, motor 4), SERVO3_FUNCTION 35 (pad 3 -> FL, motor 3), SERVO4_FUNCTION 34 (pad 4 -> RL, motor 2). '
                   'CW units go front-left and rear-right, CCW units front-right and rear-left (spin seen from above = from the inlet, since the inlets face up). '
                   'Direction: an EDF rotor is handed, so each unit must turn its own way to blow down; set it by swapping two leads at the bullets (ArduPilot wiki) or the AM32 "Reversed" box (MicoAir AM32 page).'),
         sources=['ap_motors', 'ap_wiki_motors', 'mico_esc_am32', 'ap_params_463'],
         open=('Which way QX means by "CW" (from the inlet or the exhaust) is not published: confirm at the first motor test (air must leave downward; the unit\'s rotation seen '
               'from above must match the map). If both CW units turn out CCW seen from above, swap the fans left-right between nacelles (no part changes). '
               'Pad 1 = connector M1 is the silkscreen convention; Mission Planner motor test confirms output-to-pad before any fan is mounted.')),
    dict(id='mtf01', title='MTF-01 pinout, voltage, UART, ArduPilot parameters', status='pass',
         evidence=('MTF-01 SH1.0-4P: GND, 5V, Rx, Tx; supply 5 V, about 100 mA; LVTTL 3.3 V UART 115200. FC UART4 socket GND, 5V, TX4, RX4 (5 V from the FC 5 V/3 A BEC). '
                   'MicoAir draws exactly this pairing for the MicoAir743 (straight lead). ArduPilot: SERIAL4_PROTOCOL 1, SERIAL4_BAUD 115, SERIAL4_OPTIONS 1024, FLOW_TYPE 5, '
                   'RNGFND1_TYPE 10, RNGFND1_MIN_CM 1, RNGFND1_MAX_CM 800, RNGFND1_ORIENT 25 (maker guide; MIN_CM/MAX_CM still exist in Copter 4.6.3).'),
         sources=['mico_mtf', 'mico_mtf_pins', 'mico_mtf_wiring', 'ap_params_463'],
         open='FLOW_ORIENT_YAW depends on how CAD turns the module on the shelf (ArduPilot default: heading points from the lenses toward the chip side, maker image).'),
    dict(id='a7z_link', title='A7Z to FC MAVLink link', status='pass',
         evidence=('Free A7Z pins: 14 (GND), 16 (PJ24, UART4-TX), 18 (PJ25, UART4-RX); not in the as-built 19-wire map (used: 1 2 3 4 5 6 7 9 11 12 17 25 29 31 34 35 38 39 40). '
                   'UART2 (pins 7/11) carries the servo bus and is not touched; UART3 is on the IMU pins 3/5; UART0 (8/10) is the debug console. Radxa\'s stock overlay '
                   'sun60iw2p1-uart4 ("Enable UART4", compatible radxa,cubie-a7z, "pin 16 and pin 18") gives /dev/ttyAS4. Levels: PJ bank VCC-PJ = VCC33-LCD 3.3 V (schematic V1.11); '
                   'STM32H743 UART at 3.3 V; no level shifter needed. FC: SERIAL1 (UART1), default MAVLink2.'),
         sources=['radxa_pins', 'radxa_uart4', 'a7z_logic', 'a7z_bench', 'ap_readme', 'current_state'],
         open=('A spare UART has never been enabled on this A7Z: CURRENT-STATE lists only the TWI7, TWI0, I2S0 overlays and UART2; no session enabled uart4 '
               '(transcript search "ttyAS4": documentation mentions only). The A7Z was offline on 2026-11-10 (ssh timeout), so /dev/ttyAS* was not read. '
               'Physical access to pins 14/16/18 in the saddle (edge row) not seen on the robot. 921600 baud on the A7Z UART is untested (115200 fallback).')),
    dict(id='power_path', title='Two packs in parallel into the ESC tabs; currents vs ratings', status='unknown',
         evidence=(f'Mass used: v6 CAD {C["total_g_nominal"]:.0f} g all-up with 80 g fans ({C["total_g_heavy"]:.0f} g with 113 g fans); hover thrust {C["hover_thrust_per_fan_g"][0]}-{C["hover_thrust_per_fan_g"][1]} g per fan. '
                   f'Hover current per fan {C["hover_A_per_fan"][0]}-{C["hover_A_per_fan"][1]} A (three methods: {C["methods"]}), total {C["hover_A_total"][0]}-{C["hover_A_total"][1]} A. '
                   f'Peak per fan {C["peak_A_per_fan"]:.0f} A (listing max continuous), {C["peak_A_total_uncapped"]:.0f} A total uncapped. Right pack share {C["pack_share_right"]:.0%} (shorter pigtail). '
                   f'Per pack: hover {C["hover_A_right_pack"][0]}-{C["hover_A_right_pack"][1]} A, peak {C["peak_A_right_pack_uncapped"]} A uncapped, {C["peak_A_right_pack_capped"]} A with MOT_BAT_CURR_MAX {C["cap_MOT_BAT_CURR_MAX"]:.0f}. '
                   'Ratings: ESC 55 A per channel vs fan 45 A max: pass. Pack 130C x 1.3 Ah = 169 A claimed: pass. XT60 (Amass) rated 30 A, max 60 A: hover may exceed the 30 A rating '
                   'on the worst case; peaks stay at or under 60 A only with the MOT_BAT_CURR_MAX cap. 12 AWG chassis 41 A: hover at most at that rating, flights 1-1.5 min. '
                   '16 AWG chassis 22 A vs per-fan hover rms (0.82 x DC in six-step) and 45 A bursts: see motor_leads. Harness: one male XT60 pigtail per pack, both soldered to the same ESC tab pair; no Y-splice.'),
         sources=['mass_v6', 'pet_log', 'qx_listing', 'cnhl', 'amass_xt60', 'powerstream', 'mico_esc'],
         open=('The hover current spans 2x between methods (13 vs 26 A per fan) and decides the outcome. Low case (about 52 A total): each XT60 carries about 28 A, inside its 30 A rating, '
               'and the 110 A cap leaves 2x control headroom. High case (about 106 A total): each XT60 carries about 57 A continuous, at its 60 A maximum, and the 110 A cap leaves almost '
               'no headroom, so the cap would have to rise and the XT60s would run above rating; the fix then is soldering the pack leads straight to the pigtails or XT90 connectors '
               '(no change to what is ordered: the packs and wire stay the same). Decided by the first tethered hover: read BATT current (after BATT_AMP_PERVLT 78.43) and feel the XT60 '
               'bodies after 60 s. A flight-envelope limit, not a wiring blocker.')),
    dict(id='capacitor', title='Capacitor place, polarity, lead length', status='pass',
         evidence=(f'Across the ESC battery tabs, as the maker diagram shows; 35 V on a 16.8 V pack. CAD places it lying on the right arm top flange, lead end about {CAP_LEN} mm '
                   'from the + tab: each leg reaches the tab with a short 16 AWG extension if the leg is shorter, soldered on the tab together with the two pigtails. '
                   'Long leg / side without the stripe to +. Left battery loop is long (about 0.3 m with the pack lead); forum practice adds 220-440 uF per 10 cm beyond 40 cm: '
                   '1000 uF low-ESR at the tabs covers it, and the right pack (short lead) sits in parallel.'),
         sources=['mico_esc_wiring', 'cad', 'esc_lead_practice'],
         open='Rubycon leg length not published; if the legs reach the tabs directly, no extension and two fewer joints. Moving the capacitor so its legs touch the tabs is a CAD option.'),
    dict(id='grounds', title='Ground and supply separation between duck and flight pack', status='pass',
         evidence=('Joined: exactly one conductor, FC UART1 position 1 (GND) to A7Z pin 14 (GND), plus the two UART signal lines. Open: FC UART1 position 2 (5V); A7Z 5 V pins 2/4 untouched; '
                   'no other conductor between the systems (printed frame, no metal path). No loop in flight: the only return path between the two negatives is that one 28 AWG wire, '
                   'and no load current has a reason to flow in it. Back-feed: no 5 V or VBAT crosses. The one weak case: with the A7Z off and the FC powered, FC TX1 idles at 3.3 V '
                   'into PJ25 of an unpowered SoC (through its protection diode, a few mA). Rule: duck on before the flight packs, flight packs off first (or unplug the 3-pin lead).'),
         sources=['ap_ports', 'radxa_pins', 'a7z_logic'],
         open='If the FC USB and an A7Z USB cable go to the same Mac at the same time, the Mac ground joins them a second time: harmless at bench currents, do not hover like that.'),
    dict(id='motor_leads', title='Motor lead length and extensions', status='pass',
         evidence=('Fan leads about 70 mm (not published; photo estimate). Routed lengths from the CAD geometry (x1.15): '
                   + ', '.join(f'{k} {v["route_mm"]} mm -> extension {v["ext_mm"]} mm' for k, v in FAN_LEN.items())
                   + f' (CAD agent claimed FL 250, RL 200, FR 80, RR 50). Every fan needs an extension: 16 AWG silicone, female bullet at the fan end, soldered to the ESC pad. '
                   'Factory leads look about 1.7 mm OD (about 18 AWG, inference), so 16 AWG does not bottleneck them. 16 AWG over 0.29 m at 45 A: 13.2 mOhm/m, two phases '
                   'conduct, drop about 0.34 V (2.3 %); rms per phase about 37 A, above the 22 A chassis figure, so full throttle is a burst of seconds; hover rms 10-20 A is within it. '
                   'Long motor leads with short battery leads is the ESC-friendly split; here the left side has both, unavoidable with one ESC on the right.'),
         sources=['qx_photo', 'cad', 'powerstream', 'esc_lead_practice'],
         open='Bullet size: the listing does not say; photo scale points to 2.0 mm, not the 3.5 mm the CAD agent assumed. Measure on arrival; MISSING.md buys both sizes so either fits.'),
    dict(id='charger', title='HTRC B6 V2 charges the 4S packs', status='pass',
         evidence=('Listing: "LiPo: 1-6 cells", 80 W 6 A; images show 2S to 6S JST-XH balance ports (4S port labelled), 4 mm banana outputs and a "Connector Splitter" lead with an XT60 plug; '
                   'box: charger, crocodile clip lead, connector splitter, 15 V 6 A adapter, AC cable. 4S at 1C (1.3 A) is 22 W, far under 80 W. Charge the packs one at a time, never through the flight harness.'),
         sources=['b6'],
         open='Gender of the splitter XT60 not visible (charge leads are normally male, matching the female pack plug).'),
    dict(id='arming', title='Arm and stop without an RC receiver', status='pass',
         evidence=('No extra hardware. Parameters (Copter 4.6.3 sources): FS_THR_ENABLE 0 (no RC throttle failsafe); ARMING_CHECK with bit 6 "RC Channels" cleared (1047998 = all individual checks except RC); '
                   'arm, mode changes and take-off from the A7Z over MAVLink (MAV_CMD_COMPONENT_ARM_DISARM, GUIDED, MAV_CMD_NAV_TAKEOFF); stop = disarm, force with param2 21196; '
                   'FS_GCS_ENABLE 5 (Land), FS_GCS_TIMEOUT 2 (minimum); the A7Z is the GCS (heartbeats at sysid 255 = SYSID_MYGCS default) and must land on its own if the web page '
                   'stops (the FC only sees the A7Z). GCS failsafe only arms after a GCS has been seen, which arming from the A7Z guarantees. The board has no safety switch.'),
         sources=['ap_params_463', 'ap_gcs_fs', 'ap_hwdef'],
         open='Bench test before the first hover: kill the web page -> A7Z lands; kill the A7Z link -> FC lands after 2 s.'),
    dict(id='current_sensor', title='Battery current scale (found while checking)', status='fail',
         evidence='ArduPilot default BATT_AMP_PERVLT 40.2 belongs to another ESC; this ESC outputs 12.75 mV/A, so the value is 1000 / 12.75 = 78.43 A/V. Until set, current, mAh and MOT_BAT_CURR_MAX read about half the truth.',
         sources=['mico_esc', 'ap_hwdef', 'mico_fc'], open='Set BATT_AMP_PERVLT 78.43 at setup; check against a clamp meter or the charger\'s mAh refill.'),
    dict(id='am32_poles', title='AM32 motor poles and KV (found while checking)', status='fail',
         evidence='QF2611 is 9N6P (6 magnet poles); AM32 default is 14 poles, KV 2220 (MicoAir). Set Motor poles 6 and KV 4000 in AM32 on all four ESCs, and SERVO_BLH_POLES 6 in ArduPilot for bidirectional DShot RPM.',
         sources=['qx_listing', 'mico_esc_am32', 'mico_esc', 'ap_params_463'], open='Set through ArduPilot BLHeli passthrough (SERVO_BLH_AUTO 1) and the AM32 configurator.'),
]

PARAMS = {
    'ArduPilot Copter 4.6.x (MicoAir743v2)': [
        ('FRAME_CLASS', 1, 'Quad'), ('FRAME_TYPE', 1, 'X'),
        ('SERVO1_FUNCTION', 33, 'ESC pad set 1 -> motor 1 (front right, CCW)'),
        ('SERVO2_FUNCTION', 36, 'ESC pad set 2 -> motor 4 (rear right, CW)'),
        ('SERVO3_FUNCTION', 35, 'ESC pad set 3 -> motor 3 (front left, CW)'),
        ('SERVO4_FUNCTION', 34, 'ESC pad set 4 -> motor 2 (rear left, CCW)'),
        ('MOT_PWM_TYPE', 5, 'DShot300 (MicoAir recommends DShot300)'),
        ('SERVO_BLH_AUTO', 1, 'AM32 passthrough over the FC USB'), ('SERVO_BLH_BDMASK', 15, 'bidirectional DShot on outputs 1-4'),
        ('SERVO_BLH_POLES', 6, 'QF2611 9N6P'),
        ('BATT_MONITOR', 4, 'analog voltage and current'), ('BATT_VOLT_MULT', 21.12, 'hwdef default'),
        ('BATT_AMP_PERVLT', 78.43, '1000 / 12.75 mV/A (MicoAir 55A ESC)'), ('BATT_CAPACITY', 2600, 'two 1300 mAh in parallel'),
        ('MOT_BAT_CURR_MAX', 110, 'keeps the right XT60 at or under 60 A'),
        ('SERIAL1_PROTOCOL', 2, 'MAVLink2 to the A7Z'), ('SERIAL1_BAUD', 921, '921600; 115 if the A7Z UART refuses it'),
        ('SERIAL4_PROTOCOL', 1, 'MTF-01 (maker guide)'), ('SERIAL4_BAUD', 115, ''), ('SERIAL4_OPTIONS', 1024, "don't forward MAVLink"),
        ('FLOW_TYPE', 5, 'MAVLink flow'), ('RNGFND1_TYPE', 10, 'MAVLink rangefinder'), ('RNGFND1_MIN_CM', 1, ''), ('RNGFND1_MAX_CM', 800, ''), ('RNGFND1_ORIENT', 25, 'down'),
        ('FS_THR_ENABLE', 0, 'no RC'), ('ARMING_CHECK', 1047998, 'all checks except RC Channels (bit 6)'),
        ('FS_GCS_ENABLE', 5, 'Land when A7Z heartbeats stop'), ('FS_GCS_TIMEOUT', 2, 'seconds (minimum)'),
        ('AHRS_ORIENTATION', 'board stands vertical, arrow down', 'pick from the list at setup and confirm on the HUD (derivation suggests 29 Roll180Pitch90; inference)'),
    ],
    'AM32 (each of the 4 ESCs)': [('Motor poles', 6, 'default 14'), ('Motor KV', 4000, 'default 2220'), ('Reversed', 'per motor test', 'only if a fan blows the wrong way and the leads are not swapped')],
    'A7Z (Radxa OS)': [('overlay', 'Enable UART4 (sun60iw2p1-uart4) in rsetup -> Overlay -> Manage overlays', 'pins 16/18 -> /dev/ttyAS4; reboot'),
                       ('serial', '/dev/ttyAS4 at 921600 8N1, MAVLink2', 'the duck runtime acts as GCS, sysid 255')],
}

# ====================================================================== missing items and soldering
MISSING = [
    dict(item='Female bullet connectors for the fan extensions', qty='12 (plus spares)', why='fan leads end in male bullets; the extensions need the mating female so a fan can be unplugged from its nacelle',
         spec='gold bullets, sold as male/female pairs, in BOTH 2.0 mm and 3.5 mm (fan size not published; photo suggests 2.0 mm, CAD agent assumed 3.5 mm); solder-cup type, 16 AWG entry',
         source='not in any cart, not in roboclub/INVENTORY.md, not named by Shawn. Hobby shops (Pyrodrone, Amazon "2mm 3.5mm bullet connector set")'),
    dict(item='Heat-shrink tubing', qty='about 1 m mixed', why='insulates 12 bullet joints, the XT60 cups and the capacitor legs',
         spec='3 mm and 4 mm (bullets, 16 AWG), 6 mm (12 AWG at the XT60), 2:1, polyolefin',
         source='not in INVENTORY.md and not named by Shawn on 2026-11-10 (sourcing-policy.json lists heat-shrink as RoboClub supply from 2026-09-13; bin stock not asserted)'),
    dict(item='SH1.0 4-pin to 2.54 mm Dupont female cable, 30 cm', qty='1', why='FC UART1 (JST-SH) to A7Z pins 14/16/18 (Dupont); the SH kit leads are SH on both ends and at most 15 cm',
         spec='JST-SH 1.0 mm 4-pin housing one end, four single 2.54 mm female Dupont housings the other end, 28 AWG, 300 mm; the 5 V wire is pulled out or cut at the SH end',
         source='Amazon/AliExpress listings for "JST SH 1.0 4 pin to Dupont female"; no-buy alternative: one 15 cm SH kit lead per wire with a Dupont crimp at the free end, only if RoboClub has a Dupont crimper (not listed)'),
    dict(item='M3 nylon standoffs and nuts for the stack', qty='4 M3 x 6 male-female (plate to ESC, CAD screws.json) + 4 M3 male-female ESC-to-FC spacers + 4 M3 nylon nuts',
         why='the stack box lists only "1 x MicoAir 743 V2 Stack"; CAD lists only the four plate standoffs; INVENTORY has M3 screws, no standoffs',
         spec='nylon (no metal near the FC), M3; ESC-to-FC spacer length set by CAD (the envelope implies about 8 mm board to board, inference); nuts M3 nylon',
         source='M3 nylon standoff assortment kit (Amazon); RoboClub stock reported as not holding them (coordinator 2026-11-10)'),
    dict(item='12 AWG and 16 AWG silicone wire, red and black (16 AWG also yellow)', qty=f'12 AWG: about {BAT_LEN["L"]["pigtail_mm"] + BAT_LEN["R"]["pigtail_mm"]} mm each colour; 16 AWG: about {sum(v["ext_mm"] for v in FAN_LEN.values())} mm each of three colours',
         why='pigtails and fan extensions', spec='silicone-insulated, fine-strand',
         source='RoboClub stock by Shawn\'s word ("XT60和线"); only listed here so the gauges are checked at the club before the order: 12 AWG and 16 AWG specifically were not named'),
    dict(item='USB-C data cable for FC setup', qty='1', why='flash firmware, set parameters, AM32 passthrough',
         spec='USB-C to the FC; the Mac end as the Mac needs', source='probably the cable already used for the OpenRB or A7Z (not verified to be a data cable); buy only if none is at hand'),
]
NOT_MISSING = ['FC-ESC 8-pin lead (SH kit in the Pyrodrone cart)', 'MTF-01 lead (SH kit)', 'XT60 male connectors (RoboClub, Shawn)', 'bulk capacitor (Amazon cart)',
               'battery straps (cart)', 'charger leads (in the B6 V2 box: splitter with XT60, balance ports on the charger)', 'solder, flux (RoboClub supply)', 'zip ties (RoboClub supply)',
               'M2 x 4 for the MTF-01, M2 x 8 / x 10 for the brackets (MicoAir screw stock: even M2 lengths 4-10)', 'receiver, GPS, compass (not used: deleted or replaced by the A7Z link)']

SOLDER = [
    dict(joint='ESC + tab: right pigtail red, left pigtail red, capacitor + leg', count=1, conductors=3, why_not_plug='the ESC has bare battery tabs only; a plug here would be one more XT60 in series carrying both packs (120 A peak), worse than solder'),
    dict(joint='ESC - tab: right pigtail black, left pigtail black, capacitor - leg', count=1, conductors=3, why_not_plug='same as the + tab'),
    dict(joint='XT60 male solder cups on the two pigtails (+ and -)', count=4, conductors=4, why_not_plug='XT60 contacts are solder-cup parts; there is no crimp XT60 in the parts list'),
    dict(joint='Fan extensions onto the ESC motor pads (4 fans x 3)', count=12, conductors=12, why_not_plug='the ESC has solder pads only; no connector option on this board'),
    dict(joint='Female bullets onto the fan-side end of each extension', count=12, conductors=12, why_not_plug='bullets are solder-cup parts; this joint is what makes the fan end a plug'),
    dict(joint='Capacitor leg extensions (only if the legs do not reach the tabs)', count='0 or 2', conductors=2, why_not_plug='a capacitor must be soldered at the tabs to work; moving it in CAD so the legs reach removes these two'),
]

# ====================================================================== wiring.json
def wiring_json():
    return dict(
        schema='flight-pack wiring v1', date=CHECKED, frame='guide frame, mm (x forward, y left, z up); stand-world z = guide z + 120',
        status=dict(complete_at_pin_level=True, orderable=True,
                    blocks_order=[],
                    buy_with_order=[m['item'] for m in MISSING[:4]],
                    note='Every pin, wire and joint is defined. Four small items are not in any cart (MISSING.md). Open facts are confirmed on arrival and do not change what to buy.'),
        sources={k: dict(v, checked=CHECKED) for k, v in SOURCES.items()},
        boards=BOARDS, netlist=NET, open_pins=OPEN_PINS, checks=CHECKS, currents=CUR,
        lengths=dict(fans=FAN_LEN, batteries=BAT_LEN, a7z_link_mm=round(A7Z_LEN), a7z_link_pts=[[round(c, 1) for c in p] for p in A7Z_PTS],
                     capacitor_lead_mm=CAP_LEN, fan_lead_assumed_mm=FAN_LEAD, cad_agent_claims=CAD_CLAIMS,
                     esc_pads_world={f'M{g}': [round(c, 1) for c in pad_world(g, 1)] for g in (1, 2, 3, 4)},
                     esc_tabs_world={k: [round(c, 1) for c in esc_world(v)] for k, v in ESC_TABS_PX.items()}),
        parameters={k: [dict(name=a, value=b, why=c) for a, b, c in v] for k, v in PARAMS.items()},
        missing=MISSING, checked_not_missing=NOT_MISSING, soldering=SOLDER,
        notes_for_cad=['ESC orientation chosen here: component side to the rear, battery tabs up (toward the capacitor). Pad sets 1/2 outboard, 3/4 inboard; FC turned the same way (ESC socket at the bottom edge).',
                       'FC SH sockets: UART4 on the outboard edge, UART1 on the top edge, ESC on the bottom edge (CAD keep-out box sits only on the outboard edge).',
                       'A7Z-to-FC lead (300 mm, 3 wires) is not routed in CAD; it should follow the A7Z 5 V lead.',
                       'Capacitor legs would reach the tabs directly if the capacitor lay about 20 mm further toward the stack.',
                       'screws.json lists only the four M3 x 6 plate standoffs: ESC-to-FC spacers and M3 nuts are missing there.'],
    )


# ====================================================================== markdown files
def missing_md():
    out = ['# Flight pack: items not in any cart', '',
           f'Generated by build_wiring.py from the same data as wiring.json ({CHECKED}). Nothing here has been added to a cart.', '']
    for m in MISSING:
        out += [f'## {m["item"]}', '', f'- Quantity: {m["qty"]}', f'- Why: {m["why"]}', f'- Spec: {m["spec"]}', f'- Where from: {m["source"]}', '']
    out += ['## Checked and not missing', ''] + [f'- {x}' for x in NOT_MISSING] + ['']
    return '\n'.join(out)


def solder_md():
    total = sum(s['count'] for s in SOLDER if isinstance(s['count'], int))
    out = ['# Flight pack: solder joints', '', f'Generated by build_wiring.py ({CHECKED}). {total} joints, plus 2 if the capacitor legs need extending. Everything else plugs.', '']
    for s in SOLDER:
        out += [f'- **{s["joint"]}** ({s["count"]} joint(s), {s["conductors"]} conductors). Why not a plug: {s["why_not_plug"]}']
    out += ['', 'Plugged, no solder: XT60 pack-to-pigtail (2), 12 fan bullets, FC-ESC 8-pin, FC-MTF-01 4-pin, FC-A7Z 3-wire lead, balance leads (charger only).', '']
    return '\n'.join(out)


# ====================================================================== page (wiring-kit benches)
SRC = HERE / 'sources'
RED, BLK, YEL, BLU, GRN, ORG, PUR, WHT, GRY, TEAL = '#d7263d', '#1d1d1f', '#c99a00', '#1f6fd1', '#1f9d55', '#ef6c00', '#7b5ea7', '#ffffff', '#8a8f98', '#00897b'


def photo_module(mid, title, subtitle, short, im, w_mm, pins):
    h_mm = w_mm * im.height / im.width
    return {'id': mid, 'title': title, 'subtitle': subtitle, 'short': short,
            'drawing': {'kind': 'svg', 'svg': TB.photo_svg(im, w_mm, h_mm)}, 'width': round(w_mm, 2), 'height': round(h_mm, 2), 'pins': pins}


def pin(pid, label, name, role, x, y, volt=None, multi=False, note=''):
    p = {'id': pid, 'label': label, 'name': name, 'role': role, 'x': round(x, 2), 'y': round(y, 2)}
    if volt is not None:
        p['voltage'] = volt
    if multi:
        p['multi'] = True
    if note:
        p['note'] = note
    return p


def esc_module():
    im = Image.open(SRC / 'micoair-55a-esc-dimensions.png').convert('RGB')
    box = (140, 255, 600, 690)
    im = im.crop(box)
    f = lambda px: ((px[0] - box[0]) / ESC_PX, (px[1] - box[1]) / ESC_PX)
    pins = []
    for g, (x, ys) in ESC_PADS_PX.items():
        for k, pad in enumerate('abc'):
            px, py = f((x, ys[k]))
            pins.append(pin(f'M{g}{pad}', f'{g}{pad}', f'电机 {g} 焊盘 {pad}', 'signal', px, py, 16.8))
    for t, (x, y) in ESC_TABS_PX.items():
        px, py = f((x, y))
        pins.append(pin('BATP' if t == '+' else 'BATN', t, '电池 +（16.8 V）' if t == '+' else '电池 −', 'power' if t == '+' else 'ground', px, py,
                        16.8 if t == '+' else None, multi=True, note='三根线焊在同一片：右尾线、左尾线、电容'))
    names = BOARDS['esc']['connectors']['FC']['pins']
    for k, nm in enumerate(names):
        x = (368.5 - box[0]) / ESC_PX + (k - 3.5) * 1.0
        role = 'power' if nm == 'VBAT' else 'ground' if nm == 'GND' else 'signal'
        pins.append(pin(f'S{k + 1}', str(k + 1), f'8 针第 {k + 1} 位：{nm}', role, x, (300 - box[1]) / ESC_PX,
                        16.8 if nm == 'VBAT' else None if nm in ('GND', 'NC') else 3.3,
                        note='NC：直通线里有这一根，但电调这一位内部不接，什么都不传' if nm == 'NC' else ''))
    return photo_module('esc', 'MicoAir 55A AM32 四合一电调', '堆叠下层；装在右臂后面时电池片朝上（本图已按从机器人后面看的方向转好）', '电调', im, im.width / ESC_PX, pins)


def fc_module():
    im = Image.open(SRC / 'micoair743v2-ports-ardupilot.jpg').convert('RGB')
    box = (377, 350, 877, 847)
    im = im.crop(box)
    k_ = 13.77
    pins = []
    for k, nm in enumerate(BOARDS['fc']['connectors']['ESC']['pins']):
        role = 'power' if nm == 'VBAT' else 'ground' if nm == 'GND' else 'signal'
        pins.append(pin(f'E{k + 1}', str(k + 1), f'ESC 座第 {k + 1} 位：{nm}', role, (702.5 - box[0]) / k_ + (k - 3.5), (415 - box[1]) / k_,
                        16.8 if nm == 'VBAT' else None if nm == 'GND' else 3.3))
    for k, nm in enumerate(['GND', '5V', 'TX4', 'RX4']):
        role = 'ground' if nm == 'GND' else 'power' if nm == '5V' else 'signal'
        pins.append(pin(f'U4_{k + 1}', nm, f'UART4 第 {k + 1} 位：{nm}', role, (445 - box[0]) / k_, (600 - box[1]) / k_ + (k - 1.5),
                        None if nm == 'GND' else 5 if nm == '5V' else 3.3))
    for k, nm in enumerate(['GND', '5V', 'TX1', 'RX1']):
        role = 'ground' if nm == 'GND' else 'power' if nm == '5V' else 'signal'
        pins.append(pin(f'U1_{k + 1}', nm, f'UART1 第 {k + 1} 位：{nm}', role, (645 - box[0]) / k_ + (k - 1.5), (780 - box[1]) / k_,
                        None if nm == 'GND' else 5 if nm == '5V' else 3.3,
                        note='这一位空着：不接 A7Z' if nm == '5V' else ''))
    return photo_module('fc', 'MicoAir743v2 飞控', '堆叠上层；本图已按从机器人后面看的方向转好（ESC 座在下沿）', '飞控', im, im.width / k_, pins)


def mtf_module():
    im = Image.open(SRC / 'mtf01-pins.png').convert('RGB')
    box = (215, 30, 580, 245)
    im = im.crop(box)
    k_ = 12.46
    pins = [pin(f'J{k + 1}', nm, f'第 {k + 1} 位：{nm}', 'ground' if nm == 'GND' else 'power' if nm == '5V' else 'signal',
                (x - box[0]) / k_, (200 - box[1]) / k_, None if nm == 'GND' else 5 if nm == '5V' else 3.3)
            for k, (nm, x) in enumerate(zip(['GND', '5V', 'Rx', 'Tx'], [341, 354, 366, 379]))]
    return photo_module('mtf', 'MicoAir MTF-01 光流 + 测距', '飞控下方的小架子上，镜头朝下（本图看的是背面插座）', '光流', im, im.width / k_, pins)


def a7z_module():
    m = AB.a7z()
    keep = {'p14', 'p16', 'p18'}
    for p in m['pins']:
        if p['id'] == 'p16':
            p['name'] = 'PJ24 · UART4-TX（新用）'
        if p['id'] == 'p18':
            p['name'] = 'PJ25 · UART4-RX（新用）'
        if p['id'] == 'p14':
            p['name'] = 'GND（新用）'
    m['subtitle'] = '背包座里的 A7Z，从上往下看；只用 14、16、18 三根针，其余针照旧'
    return m


def outline(mid, title, subtitle, short, w, h, color, pins, blocks=()):
    return {'id': mid, 'title': title, 'subtitle': subtitle, 'short': short,
            'drawing': {'kind': 'outline', 'color': color, 'radius': 2.0, 'blocks': list(blocks)}, 'width': w, 'height': h, 'pins': pins}


def battery_module(nm):
    side = '左' if nm == 'L' else '右'
    return outline(f'bat{nm}', f'{side}电池 CNHL 4S 1300', f'{side}电池托盘上；引线从后端出来，经{side}臂的引线窗进到后面', f'{side}电池', 37.0, 16.5, '#3a3f47',
                   [pin('P', '+', 'XT60 + （电池自带母头，插尾线公头）', 'power', 37.0, 5.5, 16.8), pin('N', '−', 'XT60 − ', 'ground', 37.0, 11.0)],
                   [{'x': 3, 'y': 3, 'w': 28, 'h': 10.5, 'label': '4S 1300', 'color': '#5c6470'}])


def cap_module():
    return outline('cap', '1000 µF 35 V 电容', '躺在右臂顶上的小槽里，用扎带固定', '电容', 8.0, 12.0, '#24324a',
                   [pin('P', '+', '长脚 +', 'power', 2.5, 12.0, 16.8), pin('N', '−', '白条一侧 −', 'ground', 5.5, 12.0)],
                   [{'x': 0.8, 'y': 0.8, 'w': 1.6, 'h': 10.4, 'color': '#cfd8dc'}])


def fan_module(nm):
    which, side, mot, spin, grp, out = FAN_POS[nm]
    zh = {'FR': '右前', 'RR': '右后', 'FL': '左前', 'RL': '左后'}[nm]
    x_pins = 22.0 if side < 0 else 0.0
    pins = [pin(lead, ZHC[lead], f'{zh}风扇{ZHC[lead]}线（公子弹头）', 'signal', x_pins, 6.0 + 5.0 * i, 16.8) for i, lead in enumerate(['red', 'yellow', 'black'])]
    return outline(f'fan{nm}', f'{zh}涵道风扇（{spin}）', f'ArduPilot 电机 {mot}，从上看{"逆时针" if spin == "CCW" else "顺时针"}；接电调 {grp} 号焊盘', f'{zh}风扇', 22.0, 22.0, '#2b2b2b',
                   pins, [{'x': 4, 'y': 4, 'w': 14, 'h': 14, 'label': f'M{mot}', 'color': '#b8860b'}])


TEXT = TB.TEXT


def bench_power():
    e = esc_module()
    return {'modules': [battery_module('L'), battery_module('R'), cap_module(), e],
            'placements': [{'module': 'esc', 'rotation': 180, 'x': 60, 'y': 30}, {'module': 'batL', 'x': 0, 'y': 0},
                           {'module': 'batR', 'x': 125, 'y': 0, 'rotation': 180}, {'module': 'cap', 'x': 92, 'y': 6}],
            'groups': [{'id': 'pos', 'label': '正极（红）', 'color': RED}, {'id': 'neg', 'label': '负极（黑）', 'color': BLK}],
            'wires': [
                {'id': 'pig_Rp', 'from': 'batR.P', 'to': 'esc.BATP', 'color': RED, 'group': 'pos', 'label': f'右尾线红 12 AWG {BAT_LEN["R"]["pigtail_mm"]} mm：XT60 公头 + → 电调 + 片（焊）'},
                {'id': 'pig_Rn', 'from': 'batR.N', 'to': 'esc.BATN', 'color': BLK, 'group': 'neg', 'label': f'右尾线黑 12 AWG {BAT_LEN["R"]["pigtail_mm"]} mm：XT60 公头 − → 电调 − 片（焊）'},
                {'id': 'pig_Lp', 'from': 'batL.P', 'to': 'esc.BATP', 'color': RED, 'group': 'pos', 'label': f'左尾线红 12 AWG {BAT_LEN["L"]["pigtail_mm"]} mm（走背包后面的横线束）：XT60 公头 + → 电调 + 片（焊）'},
                {'id': 'pig_Ln', 'from': 'batL.N', 'to': 'esc.BATN', 'color': BLK, 'group': 'neg', 'label': f'左尾线黑 12 AWG {BAT_LEN["L"]["pigtail_mm"]} mm：XT60 公头 − → 电调 − 片（焊）'},
                {'id': 'cap_p', 'from': 'cap.P', 'to': 'esc.BATP', 'color': RED, 'group': 'pos', 'label': '电容长脚 + → 电调 + 片（焊）'},
                {'id': 'cap_n', 'from': 'cap.N', 'to': 'esc.BATN', 'color': BLK, 'group': 'neg', 'label': '电容白条一侧 − → 电调 − 片（焊）'},
            ]}


def bench_fans():
    e = esc_module()
    mods = [e] + [fan_module(n) for n in ('FL', 'RL', 'FR', 'RR')]
    pl = [{'module': 'esc', 'rotation': 180, 'x': 55, 'y': 18},
          {'module': 'fanFL', 'x': 0, 'y': 0}, {'module': 'fanRL', 'x': 0, 'y': 52},
          {'module': 'fanFR', 'x': 133, 'y': 0}, {'module': 'fanRR', 'x': 133, 'y': 52}]
    colours = {'red': RED, 'yellow': YEL, 'black': BLK}
    wires = []
    for nm in ('FR', 'RR', 'FL', 'RL'):
        grp = FAN_POS[nm][4]
        zh = {'FR': '右前', 'RR': '右后', 'FL': '左前', 'RL': '左后'}[nm]
        for pad, lead, _ in PH:
            wires.append({'id': f'f{nm}{pad}', 'from': f'esc.M{grp}{pad}', 'to': f'fan{nm}.{lead}', 'color': colours[lead], 'group': nm,
                          'label': f'{zh}：电调 {grp}{pad} 焊盘 → {ZHC[lead]}色 16 AWG {FAN_LEN[nm]["ext_mm"]} mm → 母子弹头插风扇{ZHC[lead]}线'})
    groups = [{'id': n, 'label': {'FR': '右前风扇', 'RR': '右后风扇', 'FL': '左前风扇', 'RL': '左后风扇'}[n], 'color': c}
              for n, c in (('FR', ORG), ('RR', PUR), ('FL', BLU), ('RL', TEAL))]
    return {'modules': mods, 'placements': pl, 'groups': groups, 'wires': wires}


def bench_signal():
    e, f, m, a = esc_module(), fc_module(), mtf_module(), a7z_module()
    cols8 = [PUR, GRY, BLU, BLU, BLU, BLU, RED, BLK]
    wires = []
    for k, nm in enumerate(BOARDS['esc']['connectors']['FC']['pins']):
        wires.append({'id': f'ef{k + 1}', 'from': f'esc.S{k + 1}', 'to': f'fc.E{k + 1}', 'color': cols8[k], 'group': 'escfc',
                      'label': f'8 针直通线第 {k + 1} 位：电调 {nm} ↔ 飞控 {BOARDS["fc"]["connectors"]["ESC"]["pins"][k]}'})
    for k, (fn, mn, c) in enumerate(zip(['GND', '5V', 'TX4', 'RX4'], ['GND', '5V', 'Rx', 'Tx'], [BLK, RED, YEL, GRN])):
        wires.append({'id': f'mt{k + 1}', 'from': f'fc.U4_{k + 1}', 'to': f'mtf.J{k + 1}', 'color': c, 'group': 'mtf',
                      'label': f'4 针直通线第 {k + 1} 位：飞控 UART4 {fn} ↔ 光流 {mn}'})
    for fn, an, pid, sig, col in A7Z_LINK:
        pos = ['GND', '5V', 'TX1', 'RX1'].index(fn) + 1
        wires.append({'id': f'mv{fn}', 'from': f'fc.U1_{pos}', 'to': f'a7z.{pid}', 'color': {'black': BLK, 'yellow': YEL, 'green': GRN}[col], 'group': 'mav',
                      'label': f'飞控 UART1 {fn} → A7Z {an.split()[0]} 号针（{ {"GND": "地", "TX1": "飞控发、A7Z 收", "RX1": "A7Z 发、飞控收"}[fn] }），30 cm SH 转杜邦线'})
    return {'modules': [e, f, m, a],
            'placements': [{'module': 'esc', 'rotation': 180, 'x': 0, 'y': 52}, {'module': 'fc', 'rotation': 180, 'x': 2, 'y': 0},
                           {'module': 'mtf', 'x': 0, 'y': 108}, {'module': 'a7z', 'x': 80, 'y': 0}],
            'groups': [{'id': 'escfc', 'label': '电调 ↔ 飞控', 'color': BLU}, {'id': 'mtf', 'label': '光流', 'color': YEL},
                       {'id': 'mav', 'label': 'A7Z 链路', 'color': GRN}],
            'wires': wires}


CSS = """
:root{--bg:#f7f8fa;--card:#fff;--ink:#16181d;--mute:#5b6270;--line:#e2e5ea;--ok:#1f9d55;--bad:#c62828;--unk:#b26a00;--acc:#1f6fd1}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#f7f8fa;--card:#fff;--ink:#16181d}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
main{max-width:980px;margin:0 auto;padding:16px}
h1{font-size:26px;line-height:1.3;margin:8px 0 4px}h2{font-size:21px;margin:32px 0 10px;padding-top:8px;border-top:1px solid var(--line)}h3{font-size:17px;margin:18px 0 6px}
p,li{overflow-wrap:anywhere}code{font-size:14px;background:#eef1f5;border-radius:4px;padding:1px 4px;overflow-wrap:anywhere}
.lead{font-size:18px}.mute{color:var(--mute);font-size:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:10px 0}
.verdict{border-left:6px solid var(--ok)}
.pill{display:inline-block;border-radius:999px;padding:1px 10px;font-size:13px;font-weight:600;margin-right:6px;vertical-align:1px}
.pass{background:#e3f4ea;color:var(--ok)}.fail{background:#fde8e8;color:var(--bad)}.unknown{background:#fff3df;color:var(--unk)}
.solder{background:#fde8e8;color:var(--bad)}.plug{background:#e7f0fd;color:var(--acc)}
.wires{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}
.wire{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;display:flex;gap:10px;align-items:flex-start}
.wire input{width:22px;height:22px;margin-top:3px;flex:none;font-size:16px}
.sw{display:inline-block;width:28px;height:8px;border-radius:4px;border:1px solid #9aa0a6;vertical-align:2px;margin-right:6px}
.wire b{font-weight:600}.wire .meta{color:var(--mute);font-size:14px}
.wkhost{margin:8px 0 4px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:6px}
nav.toc{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}nav.toc a{font-size:15px;text-decoration:none;color:var(--acc);background:#e7f0fd;border-radius:8px;padding:4px 10px}
ul.tight li{margin:4px 0}.src{font-size:14px;color:var(--mute)}.src a{color:var(--acc)}
.kv{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:15px}.kv span{white-space:nowrap}
"""


def esc_(s):
    return html.escape(str(s))


def bench_html(host, bench):
    data = json.dumps(bench, ensure_ascii=False).replace('</', '<\\/')
    return (f'<div class="wkhost" id="{host}"></div><script>WiringKit.render(document.getElementById("{host}"),{data},'
            f'{{text:{TEXT},pinLabel:(pin,m)=>m.id==="a7z"?pin.label+" 号":pin.label}});</script>')


def wire_cards(group_ids):
    out = []
    for w in NET:
        if w['group'] not in group_ids:
            continue
        f, t, wr = w['from'], w['to'], w['wire']
        joints = [('焊' if f['joint'] == 'soldered' else '插'), ('焊' if t['joint'] == 'soldered' else '插')]
        cls = lambda j: 'solder' if j == '焊' else 'plug'
        col = {'red': RED, 'black': BLK, 'yellow': YEL, 'green': GRN}.get(wr['colour'], '#c9ced6')
        length = f'{wr["length_mm"]} mm' if wr['length_mm'] else '对插，无导线'
        gauge = f'{wr["gauge_awg"]} AWG' if wr['gauge_awg'] else ''
        out.append(f'<label class="wire"><input type="checkbox" aria-label="{esc_(w["id"])} 完成"><div><b><span class="sw" style="background:{col}"></span>{esc_(w["zh"])}</b>'
                   f'<div class="meta">{esc_(gauge)} · {esc_(length)} · 一头<span class="pill {cls(joints[0])}">{joints[0]}</span>另一头<span class="pill {cls(joints[1])}">{joints[1]}</span></div>'
                   f'<div class="meta">{esc_(f["board"])}.{esc_(f["connector"])}.{esc_(f["pin"])} → {esc_(t["board"])}.{esc_(t["connector"])}.{esc_(t["pin"])} · 编号 {esc_(w["id"])}</div></div></label>')
    return '<div class="wires">' + ''.join(out) + '</div>'


ZH_STATUS = {'pass': '通过', 'fail': '要改设置', 'unknown': '待实测'}
ZH_CHECK = {
    'esc_fc_cable': ('电调和飞控之间的 8 针线', '两块板的插座顺序完全相同（Curr、NC/RX7、M4、M3、M2、M1、VBAT、GND），厂家接线图画的就是直通线。装上后两块板都朝后、插座都在下沿，所以直通线就对。盒里有没有这根线没写，购物车里的 SH 线套件能做一根。'),
    'motor_map': ('四个风扇的编号、转向和焊盘', 'ArduPilot 四轴 X：1 号右前逆时针，2 号左后逆时针，3 号左前顺时针，4 号右后顺时针（从上看）。电调电池片朝上装时，1、2 号焊盘在外侧（右），3、4 号在内侧，所以在参数里重新对应：1 号焊盘接右前，2 号接右后，3 号接左前，4 号接左后。顺时针的两个风扇放左前和右后。QX 没写“顺时针”是从哪面看的，第一次电机测试时看风往下吹、从上看转向对，不对就把左右风扇对调（零件不改）。'),
    'mtf01': ('光流模块', '4 针：GND、5V、Rx、Tx，5 V 供电，3.3 V 串口 115200。接飞控 UART4（GND、5V、TX4、RX4），厂家给 MicoAir743 画的就是这根直通线。参数照厂家 ArduPilot 指南。'),
    'a7z_link': ('A7Z 和飞控的 MAVLink 线', 'A7Z 的 14（地）、16（UART4 发）、18（UART4 收）三根针现在都空着；舵机用的 UART2（7、11）不动。Radxa 自带“Enable UART4”覆盖，指名 A7Z 的 16、18 号针，设备是 /dev/ttyAS4。两边都是 3.3 V。这块 A7Z 以前从没开过备用串口；今天 A7Z 不在线，没能读设备列表。'),
    'power_path': ('电池并联和电流', f'按 v6 总重 {C["total_g_nominal"]:.0f} 克（重风扇 {C["total_g_heavy"]:.0f} 克）算，悬停每个风扇 {C["hover_A_per_fan"][0]}～{C["hover_A_per_fan"][1]} A，合计 {C["hover_A_total"][0]}～{C["hover_A_total"][1]} A；满油门每个 45 A。右电池尾线短，分到 {C["pack_share_right"]:.0%}。电调 55 A、电池 130C 都够。XT60 额定 30 A、最大 60 A。估算低的一头（合计约 52 A），每个 XT60 约 28 A，在额定内，限流 110 A 还留一倍余量；高的一头（合计约 106 A），每个 XT60 持续约 57 A，贴着最大值，限流 110 A 几乎没有控制余量，那时改成电池线直接焊尾线或换 XT90，要买的东西不变。实际落在哪一边，看第一次拴绳悬停读到的电流。'),
    'capacitor': ('电容', f'跨在电调电池片上，长脚接 +。CAD 里它躺在右臂顶上，脚尖离 + 片约 {CAP_LEN} mm：脚不够长就各接一段 16 AWG 短线，和两根尾线一起焊在片上。左电池引线较长，1000 µF 低内阻电容放在片上就够。'),
    'grounds': ('两套电源只共一根地线', '只连三根：飞控 UART1 的地 ↔ A7Z 14 号针，加两根信号线。飞控 UART1 的 5V 位空着，A7Z 的 5 V 针不碰。没有第二条地线回路，没有 5 V 或电池电压过去。顺序：先开鸭子，再插飞行电池；先拔飞行电池，再关鸭子。'),
    'motor_leads': ('风扇引线长度', '风扇自带线约 70 mm（未公布），四个都要接延长线：' + '，'.join(f'{ {"FR": "右前", "RR": "右后", "FL": "左前", "RL": "左后"}[k]} {v["ext_mm"]} mm' for k, v in FAN_LEN.items()) + '。16 AWG 在悬停电流下够用，满油门只能是几秒的冲刺。子弹头尺寸没公布，照片比例看像 2.0 mm（CAD 那边假设的是 3.5 mm），两种都买。'),
    'charger': ('充电器', 'HTRC B6 V2 支持 1～6 节锂电，机身上有 2S～6S 平衡口，盒里的多头转接线带 XT60。4S 1300 按 1C 充只要 22 W。两块电池分开充，不要通过飞行线束一起充。'),
    'arming': ('没有遥控器怎么解锁和停机', '不需要加任何硬件。关掉遥控相关的检查和油门失控保护，由 A7Z 用 MAVLink 解锁、切模式、起飞、强制上锁；A7Z 心跳停 2 秒，飞控自己降落。网页断了，A7Z 要自己让它降落。'),
    'current_sensor': ('电流读数要改设置', 'ArduPilot 默认的电流系数 40.2 是别的电调的；这个电调是 12.75 mV/A，要设 78.43。不改的话，电流和限流都只读到一半左右。'),
    'am32_poles': ('电调里的电机极数要改', 'QF2611 是 6 极，AM32 默认 14 极、KV 2220。四个电调都改成 6 极、KV 4000，ArduPilot 里 SERVO_BLH_POLES 也设 6。'),
}


def page():
    js = (TB.WK / 'wiring-kit.js').read_text().replace('</script', '<\\/script')
    css_wk = (TB.WK / 'wiring-kit.css').read_text()
    n_solder = sum(s['count'] for s in SOLDER if isinstance(s['count'], int))
    checks = []
    for c in CHECKS:
        t, body = ZH_CHECK[c['id']]
        checks.append(f'<div class="card"><h3><span class="pill {c["status"]}">{ZH_STATUS[c["status"]]}</span>{esc_(t)}</h3><p>{esc_(body)}</p>'
                      f'<p class="src">来源：{"、".join(esc_(s) for s in c["sources"])}（见页尾）</p></div>')
    miss = ''.join(f'<div class="card"><h3>{esc_(z)}</h3><p>{esc_(d)}</p></div>' for z, d in [
        ('母子弹头 12 个（2.0 mm 和 3.5 mm 各买一套）', '风扇线头是公子弹头，延长线要配母头，风扇才能拔下来。尺寸没公布，到货后用卡尺量，用对的那套。'),
        ('热缩管约 1 米', '3 mm、4 mm（子弹头和 16 AWG）、6 mm（XT60 上的 12 AWG）。俱乐部清单里没有，今天你也没提。'),
        ('SH1.0 4 针转杜邦母头线，30 cm，1 根', '飞控 UART1 是 SH 插座，A7Z 是 2.54 mm 排针；套件里的线两头都是 SH，最长 15 cm。'),
        ('M3 尼龙铜柱和螺母', '堆叠盒里只写“1 个 743 V2 堆叠”。要 4 个 M3×6 公母柱（CAD 已有）、4 个电调到飞控的 M3 公母柱（长度由 CAD 定）、4 个 M3 尼龙螺母。'),
        ('要在俱乐部确认的线规', '12 AWG 和 16 AWG 硅胶线你说俱乐部有，但没说线规；下单前看一眼有没有这两种。USB-C 数据线用现有的就行。')])
    solder = ''.join(f'<li><b>{esc_(z)}</b>：{esc_(d)}</li>' for z, d in [
        ('电调 + 片（1 处，3 根线）', '右尾线红、左尾线红、电容长脚。电调只有裸片，没有插座可选。'),
        ('电调 − 片（1 处，3 根线）', '右尾线黑、左尾线黑、电容另一脚。'),
        ('两根尾线上的 XT60 公头（4 处）', 'XT60 是焊杯式，没有压接款。'),
        ('四个风扇延长线焊到电调焊盘（12 处）', '电调电机输出只有焊盘。'),
        ('延长线另一头焊母子弹头（12 处）', '子弹头是焊杯式；焊了这一头，风扇那头才能插拔。'),
        ('电容脚加长（0 或 2 处）', '只在电容脚够不到电池片时需要；CAD 把电容挪近 20 mm 就省掉。')])
    params = ''.join(f'<h3>{esc_(k)}</h3><ul class="tight">' + ''.join(f'<li><code>{esc_(a)} = {esc_(b)}</code> <span class="mute">{esc_(c)}</span></li>' for a, b, c in v) + '</ul>'
                     for k, v in PARAMS.items())
    srcs = ''.join(f'<li><b>{esc_(k)}</b>：<a href="{esc_(v["url"].split(" ")[0])}">{esc_(v["url"])}</a>，{CHECKED} 查。“{esc_(v["quote"])}”</li>' for k, v in SOURCES.items())
    body = f"""
<main>
<h1>飞行背包接线</h1>
<p class="lead">四个 50 mm 涵道风扇、两块 4S 电池并联、MicoAir 743 V2 飞控加四合一电调、MTF-01 光流，飞控通过一根三芯线和鸭子的 A7Z 说话。每根线两头的针脚、线规、长度、焊还是插，都在下面。</p>
<div class="card verdict"><b>结论：</b>到针脚为止已经完整，可以下单。下单时另外买 4 样小东西（子弹头、热缩管、SH 转杜邦线、M3 尼龙柱和螺母），见“缺的东西”。
有两项设置必须改（电流系数、电调极数），一项待第一次拴绳悬停实测（悬停电流和 XT60 额定的关系）。共 {n_solder} 个焊点，其余全是插接。</div>
<nav class="toc"><a href="#power">电源</a><a href="#fans">风扇</a><a href="#signal">信号</a><a href="#list">逐根清单</a><a href="#solder">焊点</a><a href="#missing">缺的东西</a><a href="#checks">检查</a><a href="#params">参数</a><a href="#src">来源</a></nav>
<p class="mute">所有板子都按“站在机器人后面往前看”画：图的左边是鸭子的左边。点一块板子只亮它的线；“逐根接线”一根一根走。</p>

<h2 id="power">一、电源：两块电池并联到电调</h2>
<p>每块电池自带 XT60 母头，插一根 12 AWG 尾线（XT60 公头）。两根尾线的红线都焊在电调 + 片上，黑线都焊在 − 片上，电容也焊在同一对片上。没有分线器。插电池前确认两块都是充满的（每节电压差 0.05 V 以内），不然插上的一瞬间会互相大电流充电。</p>
{bench_html('b-power', bench_power())}
<h2 id="fans">二、风扇：电调焊盘 → 延长线 → 子弹头</h2>
<p>每个风扇三根线，任意顺序接三块焊盘，转向等电机测试后再调（对调两根子弹头，或在 AM32 里勾 Reversed）。左边两个风扇的延长线走背包外侧、从背包盖后面横过来。</p>
{bench_html('b-fans', bench_fans())}
<h2 id="signal">三、信号：电调、飞控、光流、A7Z</h2>
<p>电调和飞控之间一根 8 针直通线；飞控 UART4 到光流一根 4 针直通线；飞控 UART1 到 A7Z 三根线（地、两根串口线），UART1 的 5V 那一位空着。</p>
{bench_html('b-signal', bench_signal())}

<h2 id="list">四、逐根清单（做完一根勾一根）</h2>
<h3>电源</h3>{wire_cards({'power'})}
<h3>风扇</h3>{wire_cards({'fans'})}
<h3>信号</h3>{wire_cards({'signal'})}
<div class="card"><b>空着不接的：</b>飞控 UART1 第 2 位（5V，把这根线从插头里拔出或齐根剪掉包好）；A7Z 2、4 号 5 V 针（不动）；两块电池的平衡头（只给充电器用，飞行时压在绑带下）；飞控的 12V、图传、GPS、UART5、UART6、I2C（不用）。</div>

<h2 id="solder">五、焊点（共 {n_solder} 个，外加电容可能的 2 个）</h2>
<ul class="tight">{solder}</ul>
<p class="mute">插接、不用焊：两对 XT60、12 个风扇子弹头、电调–飞控 8 针、飞控–光流 4 针、飞控–A7Z 线、平衡头。</p>

<h2 id="missing">六、缺的东西（不在任何购物车里）</h2>
{miss}

<h2 id="checks">七、检查结果</h2>
{''.join(checks)}

<h2 id="params">八、要设的参数</h2>
{params}

<h2 id="src">九、来源</h2>
<ul class="tight src">{srcs}</ul>
<p class="mute">本页由 <code>extensions/flight-20261110/wiring/build_wiring.py</code> 从 <code>wiring.json</code> 的同一份数据生成；接线图用 wiring-kit 画。</p>
</main>"""
    return (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>飞行背包接线</title><style>{CSS}</style><style>{css_wk}</style><script>{js}</script></head><body>{body}</body></html>')


def main():
    data = wiring_json()
    (HERE / 'wiring.json').write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n')
    (HERE / 'MISSING.md').write_text(missing_md())
    (HERE / 'SOLDERING.md').write_text(solder_md())
    (HERE / 'wiring.html').write_text(page())
    print(json.dumps(dict(fans={k: (v['route_mm'], v['ext_mm']) for k, v in FAN_LEN.items()},
                          batteries={k: (v['route_mm'], v['pigtail_mm']) for k, v in BAT_LEN.items()},
                          a7z_mm=round(A7Z_LEN), cap_mm=CAP_LEN, currents={k: CUR[k] for k in ('total_g_nominal', 'total_g_heavy', 'methods', 'hover_A_per_fan', 'hover_A_total', 'pack_share_right', 'hover_A_right_pack', 'peak_A_right_pack_capped', 'peak_A_right_pack_uncapped')},
                          netlist=len(NET), html_kb=round((HERE / 'wiring.html').stat().st_size / 1024)), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
