"""Chapters, steps and legend for the MicroDuck torso, neck, head and wiring guide.

build(ctx) returns (chapters, steps, legend). ctx comes from build_guide_data.py and provides part bounds (ctx.cam),
cable lengths in mm (ctx.L) and part presence (ctx.has). Mechanical step order and screw counts follow the current
CAD operations in full-build-data-current.json (torso-01/02, imu-local-*, neck-01..14, head-current-01..04,
camera-current-01..03, electronics-current-01..03/05, head-close-current-01..03). Power, controller and cabling
steps follow the 7 V servo rail (PROJECT-CONTEXT.json current_build.servo_rail_7v_20261014, power-diagram/README.md,
2026-10-14; set point 7.40 V and Shutdown 52 from current_build.servo_shutdown_52_20261015): a USB-C PD charger at 15 V
into an Adafruit 5991, two ROBOTIS kit XL4015 converters set to 7.40 V (OpenRB
and servos) and 5.00 V (Pi), all three boards in the printed rear converter box behind the rear pack (layout F, approved
2026-10-14, print/back-plate/layout-F/: frame and lid, the frame replacing the pack cover; three tiers: XL4015 #1 (7 V) on
top, #2 (5 V) in the middle, the 5991 in a narrow bottom tier); no soldering on power wires. The power wire cut lengths
come from routes.json powerWiresF (layout F wire paths + 15 mm per screw-terminal end).
"""
from __future__ import annotations

import math

from wiring.openrb import openrb_wiring

LEGS = ['left-leg', 'right-leg']
TORSO = ['torso_base', 'rear_pack', 'ring10_torso', 'ring5_torso']
# The finished legs come apart at the hip so the torso base can sit between each hip-yaw motor and its yaw link
# (leg guide steps 13-20, reversed and rebuilt). Everything below the hip bridge stays together.
HIP_YAW = ['motor10', 'motor5']
HIP_ROLL = ['motor9', 'passive', 'washer9', 'motor4', 'right_passive', 'washer4']
YAW_LINKS = ['yaw', 'right_yaw']
# Thigh, hip bridge and ankle-foot groups per leg (leg guide module keys), for the leg cable steps.
THIGH_R = ['right_thigh', 'motor3', 'motor2', 'right_plate', 'ring2']
THIGH_L = ['thigh', 'motor8', 'motor7', 'plate', 'ring7']
BRIDGE_R = ['right_hip', 'ring3', 'ring4']
BRIDGE_L = ['hip', 'ring8', 'ring9']
ANKLE_R = ['right_lower', 'right_ankle', 'right_smallring', 'motor1', 'washer1', 'right_foot']
ANKLE_L = ['lower', 'ankle', 'smallring', 'motor6', 'washer6', 'foot']
LEG_CABLES = ['dxl-5-4', 'dxl-4-3', 'dxl-3-2', 'dxl-2-1', 'dxl-10-9', 'dxl-9-8', 'dxl-8-7', 'dxl-7-6']
THIGH_CABLES = ['dxl-4-3', 'dxl-3-2', 'dxl-2-1', 'dxl-9-8', 'dxl-8-7', 'dxl-7-6']
HIP_CABLES = ['dxl-5-4', 'dxl-10-9']
CONTROLLER = ['openrb_board']
IMU = ['imu_board', 'imu_sh4_receiving']
# Rear converter box, layout F (print/back-plate/layout-F/layout_f.json, 2026-10-14): the frame replaces the pack cover;
# the 5991 sits in the narrow bottom tier, XL4015 #2 (5 V) in the middle tier and #1 (7 V) in the top tier; the lid
# closes its back.
BOX_FRAME = ['rear_frame']
BOX_BOARDS = ['pd5991', 'xl4015_mid', 'xl4015_top']
BOX_LID = ['rear_lid']
NECK_LOWER = ['motor12', 'motor11', 'neck_link_a', 'neck_link_b', 'idler11', 'idler12', 'idler_cap11', 'idler_cap12']
PITCH_GROUP = ['neck_pitch', 'neck_pitch_ring', 'motor13']
ROLL_GROUP = ['head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b', 'motor14']
SHELLS = ['shell_left', 'shell_right']
JAW = ['jaw_support', 'mouth_sliding_ring', 'jaw_frame', 'motor15']
FACE = ['face_panel', 'eye_trim']
CAMERA = ['camera_board']   # A7Z head (2026-10-15): Radxa Camera 13M 214 on four face bosses; the eye trim has its own two screws

# Radxa Cubie A7Z header (2026-10-15). The 32 mm camera board covers the edge-row plug ends of pins 10 to 34, so the bundle
# uses the inner row: IMU on 1, 3, 5 (TWI7), 9; UART2 on 7 (TX) and 11 (RX); the head 5 V lead on 2 and 6. Pins 8 and 10 are
# the A7Z debug console and stay empty.
GPIO_PINS = (1, 2, 3, 5, 6, 7, 9, 11)   # the eight bundle wires from the torso
AUDIO_PINS = (4, 12, 35, 39, 40)        # amplifier Vin, BCLK, LRC, GND, DIN
TOUCH_PINS = (17, 25, 29, 31)           # touch readout (XIAO ESP32-S3): 3.3 V, GND, I2C SCL (PB2), I2C SDA (PB3); custom overlay


def gpio_key(pin: int) -> str:
    """Guide part key of the plug end on an A7Z header pin."""
    return f'head_pi_gpio_pin_{pin:02d}_receiving'


def a7z(anchor: str, label: str, note: str = '', page: str = 'A7Z-PINS.html') -> dict:
    """Detailed A7Z bench pages (Chinese, photos with markers), served next to this guide."""
    return {'label': label, 'href': f'{page}#{anchor}', 'note': note, 'external': True}
AUDIO = ['speaker_tape', 'speaker', 'speaker_retainer', 'amplifier']   # 2026-10-13: five wires soldered into the amplifier, no header or housings
# 2026-10-15 touch extension (extension-20261015-touch/PLAN.md): five copper-tape pads inside the cap and a XIAO ESP32-S3
# on foam tape on the inner left wall; its nine wires are soldered to its edge pads (approved exception, like the amplifier).
TOUCH_PADS = ['touch_pad_l1', 'touch_pad_r1', 'touch_pad_l2', 'touch_pad_r2', 'touch_pad_m']
TOUCH = TOUCH_PADS + ['touch_xiao_tape', 'touch_xiao']
# V1.9 neck-bundle wire clips, each a 2 mm tab under an existing screw head (print/ext-v19/README.md).
CLIPS = ['clip_torso', 'clip_bracket', 'clip_head', 'clip_cap']

REAR = (-1.0, -0.85, 0.55)
REAR_LOW = (-1.0, -0.55, -0.25)
FRONT = (1.0, 1.1, 0.75)
RIGHT_REAR = (-0.6, -1.2, 0.5)
LEFT_REAR = (-0.6, 1.2, 0.5)
TOP_REAR = (-0.7, 0.4, 1.0)


# Detailed bench pages with product photos, numbered markers and wiring views (Chinese), served next to this guide.
def bringup(anchor: str, label: str, note: str = '') -> dict:
    return {'label': label, 'href': f'BRINGUP.html#{anchor}', 'note': note, 'external': True}


def figure(name: str, caption: str) -> dict:
    """A drawing from guide/content/figures/ embedded as a data URI (the viewer accepts only data: images)."""
    import base64
    from pathlib import Path
    path = Path(__file__).resolve().parent / 'figures' / name
    mime = 'image/png' if name.endswith('.png') else 'image/jpeg'
    return {'src': f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode(), 'caption': caption}


def here(step_id: str, label: str, note: str = '') -> dict:
    return {'label': label, 'href': f'#{step_id}', 'note': note}


def r5(x: float) -> int:
    """Round a cut length up to the next 5 mm."""
    return int(math.ceil(x / 5.0) * 5)


# Power wires in the rear converter box (layout F, 2026-10-14). Each key is a routes.json cable id. The cut comes from
# routes.json powerWiresF.cutMm (build_guide_data puts it in L as 'cut:<id>'): the longer wire of the pair along its
# layout F path + 15 mm per screw-terminal end, rounded up to 5 mm, both wires cut alike; the head 5 V lead adds 45 mm for the
# neck (39 mm worst neck and head pose) and dressing instead of a second terminal end.
PLATE_ROUTES = ('pw-15v', 'pw-15v-link', 'pw-7v', 'pi-lead')
PENDING_ROUTE = 'length pending: route {rid} in the rear converter box'


def plate_cut(L: dict, rid: str) -> str:
    """Cut length text for a box power wire: '<n> mm per wire' once routes.json has the cut, else the pending note."""
    if f'cut:{rid}' in L:
        return f'{L[f"cut:{rid}"]} mm per wire'
    return PENDING_ROUTE.format(rid=rid)


def build(ctx):
    L = ctx.L
    pi_parts = [k for k in ctx.parts if k == 'pi' or (k.startswith('head_pi') and 'receiving' not in k)] \
        + ctx.keys('camera_ribbon')
    gpio = [gpio_key(n) for n in GPIO_PINS]
    audio_gpio = [k for k in (gpio_key(n) for n in AUDIO_PINS) if k in ctx.parts]
    antenna = ctx.keys('antenna')
    antenna_lead = ctx.keys('antenna_coax', 'antenna_ipex')
    audio = ctx.keys(*AUDIO)
    clips = ctx.keys(*CLIPS)
    AUDIO_CABLES = ['amp-lrc', 'amp-bclk', 'amp-din', 'amp-gnd', 'amp-vin']
    touch = ctx.keys(*TOUCH)
    touch_gpio = [k for k in (gpio_key(n) for n in TOUCH_PINS) if k in ctx.parts]
    TOUCH_PAD_CABLES = [c for c in ('touch-l1', 'touch-r1', 'touch-l2', 'touch-r2', 'touch-m') if c in L]
    TOUCH_PIN_CABLES = [c for c in ('touch-pin17', 'touch-pin25', 'touch-pin29', 'touch-pin31') if c in L]
    SPK_CABLES = ['spk-plus', 'spk-minus']
    controller = ctx.keys(*CONTROLLER)
    board = ctx.keys('openrb_board')
    pack = ctx.keys('rear_pack')
    box = ctx.keys(*BOX_FRAME, *BOX_BOARDS, *BOX_LID)

    cut = {
        # Power wires in the rear converter box (15 V feed and link, 7 V pair, Pi lead): text, see plate_cut().
        **{rid: plate_cut(L, rid) for rid in PLATE_ROUTES},
        # +60 = 39 mm worst-pose slack of the V1.9 clip route + about 20 mm for the ends and dressing (matches build_cables
        # slack; route-v19-motion.json).
        'imu': r5(L['imu'] + 60),
        'uart': r5(L['uart'] + 60),
    }
    # Amplifier wires: soldered hole to Pi pin plus 15 mm for the bends at both ends (jumper with one sleeve cut off).
    amp_cut = {c: r5(L[c] + 15) for c in AUDIO_CABLES}
    # Touch wires: route plus 15 mm for the bends at both ends.
    touch_cut = {c: r5(L[c] + 15) for c in TOUCH_PAD_CABLES + TOUCH_PIN_CABLES if c in L}

    chapters = [
        {'id': 'start', 'title': '1. Before you begin', 'intro': False,
         'summary': 'What the finished robot looks like, the parts and kit cables you already own, the 21 new prints and the tools.'},
        {'id': 'openrb', 'title': '2. Prepare the OpenRB-150',
         'summary': 'Set servo IDs, flash the UART bridge, set the power jumper, trim the header tails and solder the two UART wires into J12.'},
        {'id': 'harness', 'title': '3. Set the 15 V, 7 V and 5 V supply boards on the bench',
         'summary': 'The Adafruit 5991 asks the USB-C charger for 15 V (only its 15V switch on). Two ROBOTIS XL4015 converters from the OMX-AI kits take that 15 V: #1 is set to 7.40 V (the 7 V rail) for the servos and #2 to 5.00 V for the A7Z, each metered with nothing on its output. No soldering, no fuses anywhere.'},
        {'id': 'legs', 'title': '4. Open the hips and wire the legs',
         'summary': 'Take each hip apart, check the servo cables inside each leg, plug any that are missing (opening the thigh or the ankle only where a socket is blocked), dress them, and plug each hip cable into its hip-roll motor.'},
        {'id': 'torso', 'title': '5. Torso and the rear electronics pack',
         'summary': 'Build the torso on the yaw links with the hip cables through the centre of the base, screw the BNO085 onto the rear pack on the bench, slide the pack in in place of the power support, close the hips and plug the hip cables into the hip-yaw motors; then the OpenRB-150 in the pack, the 7 V pair into its terminal block, the leg links, the IMU plug, and the rear converter box: the frame in place of the pack cover, the 5991 in its bottom tier, the 5 V converter in the middle tier and the 7 V converter on top, every power wire outside the box (the 15 V wires window to window outside the right wall, the 7 V pair and the head 5 V lead up the outside of the left wall, over the box top and down through the notch at its front edge into the pack), and the lid.'},
        {'id': 'neck', 'title': '6. Neck',
         'summary': 'Build the five-motor neck on the bench with its chain cables and the bracket wire clip, then lower it into the open torso, close the shells with the torso wire clip, and screw each shell down into the rear pack.'},
        {'id': 'head', 'title': '7. Head mechanics and camera',
         'summary': 'Seat the jaw in the lower head shell on the bench, fit the shell, the jaw support with ID15, the head wire clip and the jaw screws, then the face with the eye camera.'},
        {'id': 'head-elec', 'title': '8. Head electronics',
         'summary': 'Speaker and the amplifier with its five soldered wires in the cap, the Wi-Fi antenna inside the cap roof, five copper touch pads and the XIAO touch board inside the cap, the Radxa Cubie A7Z on the cap rails with the cap wire clip, and a pin flag on each of the eight torso wires.'},
        {'id': 'bundle', 'title': '9. Neck bundle and cable dressing',
         'summary': 'Run the 8-wire bundle from the torso through the four wire clips into the head, plug it onto the A7Z, and check every joint for snags.'},
        {'id': 'power-up', 'title': '10. First power-up and close',
         'summary': 'Unpowered checks, A7Z configuration, a readback of both converter voltages before the OpenRB and the A7Z are connected to them, 15/15 servo scan and the servo voltage-limit check, sensors, current, then screw the head shut and weigh the robot.'},
        {'id': 'backpack', 'title': '11. Battery backpack',
         'summary': 'Build the 2S battery backpack (switch, DFR1202, battery, cap) and swap it for the rear converter box on the same four cover screws.'},
    ]

    steps = []
    installed: list[str] = list(LEGS)

    def step(sid, chapter, title, *, add=(), show=None, context=None, approach=None, camera=None, prepare=(), instructions=(),
             checks=(), warnings=(), cables=(), bench=False, group=None, pose=None, flex=None, screwNotes=None, wiring=None,
             links=(), images=(), remove=()):
        add = [a for a in add if a in ctx.parts or a in ('left-leg', 'right-leg')]
        remove = [r for r in remove if r in installed]
        for r in remove:   # a swap step takes these off the robot before it adds its own parts
            installed.remove(r)
        s = {'id': sid, 'chapter': chapter, 'title': title,
             'show': list(show) if show is not None else list(installed),
             'add': add,
             'context': list(context) if context is not None else [],
             'prepare': list(prepare), 'instructions': list(instructions), 'checks': list(checks), 'warnings': list(warnings)}
        if approach:
            s['approach'] = {k: v for k, v in approach.items() if k in add}
        if camera:
            s['camera'] = camera
        if cables:
            s['cables'] = list(cables)
        if group:
            s['group'] = group
        if bench:
            s['bench'] = True
        if pose:
            s['pose'] = pose
        if flex:
            s['flex'] = flex
        if screwNotes:
            s['screwNotes'] = dict(screwNotes)
        if wiring:
            s['wiring'] = wiring
        if images:
            s['images'] = list(images)
        if remove:
            s['remove'] = list(remove)
        if links:
            s['links'] = [dict(l) for l in links]
        steps.append(s)
        if not bench:
            for a in add:
                if a not in installed:
                    installed.append(a)

    tap = lambda q, size: {'item': f'{size} self-tapping screw (TAP)', 'qty': q, 'kind': 'fastener'}

    # ------------------------------------------------------------------ 1. Before you begin
    everything = LEGS + TORSO + controller + IMU + box + NECK_LOWER + PITCH_GROUP + ROLL_GROUP + SHELLS + JAW \
        + ['head_bottom'] + FACE + CAMERA + ['head_cap'] + pi_parts + antenna + antenna_lead + gpio + audio + audio_gpio + clips
    all_cables = ['dxl-r5', 'dxl-l10', 'dxl-n12', 'pw-15v', 'pw-15v-link', 'pw-7v', 'pi-lead', 'imu',
                  'uart', 'dxl-12-11', 'dxl-11-13', 'dxl-13-14', 'dxl-14-15'] + LEG_CABLES + AUDIO_CABLES + SPK_CABLES
    step('overview', 'start', 'What you are building',
         show=everything, camera=ctx.cam(LEGS + ['head_cap'], direction=(1.0, 1.2, 0.55), margin=1.0),
         instructions=[
             'The legs are already built. This guide checks and completes their servo cables, adds the torso, neck and head, and wires the whole robot.',
             'Power comes from a USB-C charger at 15 V. The charger (Shawn\'s Xiaomi 67 W offers 5, 9, 15 and 20 V) feeds an Adafruit 5991 board with only its 15V switch on. Two step-down converters from the ROBOTIS OMX-AI kits (XL4015 "DC converter") take that 15 V: #1 is set to 7.40 V for the OpenRB-150 and the servos (the 7 V rail), #2 to 5.00 V for the head computer, a Radxa Cubie A7Z. All three boards sit in a printed box on the back of the robot, the rear converter box, whose front plate also closes the rear pack; only two cables reach the table, the USB-C power cable into the 5991 (out of the left-hand wall of the box, low down, on the robot\'s left) and the OpenRB USB data cable to the Mac (through the pack floor). Nothing on the power path is soldered; to disconnect, unplug the USB-C cable.',
             'Why 7 V: the walking policies used here (Pollen\'s walk and stand policies) were trained with the servo supply between 6.5 and 8.2 V, and Pollen\'s own MicroDuck runs its servos straight from a 7.2 V battery. The set point is 7.40 V, the nominal voltage of the 2S battery the backpack in chapter 11 carries, inside that range. It is above the XL330\'s factory Max Voltage Limit of 7.0 V, so every servo has its Shutdown register (address 63) set to 52 in chapter 10, as on Pollen\'s robot: above 7.0 V the servos raise their input-voltage flag but keep torque; overload, overheating and electrical shock still switch torque off. In simulation with the 7.87° forward lean measured on this robot, the walk stays upright at 6.8, 7.4 and 8.0 V; it drifts back about 8 cm at 6.8 V and forward about 9 cm at 8.0 V. ROBOTIS rates the XL330-M288 at 3.7 to 6.0 V; running it at 7.4 V follows the trained policies and Pollen\'s robot, not the datasheet.',
             'Inside, a printed rear pack hangs on the four hip-yaw case screws behind the hip motors, where the battery and the power support used to be. It holds the OpenRB-150 standing upright; the 7 V pair and the head 5 V lead come into the pack from the rear converter box through the notch at the front edge of the box top and the top edge of its front plate, where the shell top meets the box, and lie on the frame\'s lip; no wire passes through the front plate, which closes the back of the pack. Nothing hangs under the crotch.',
             'The OpenRB-150 passes the 7 V to the three servo chains through its own ports, as on the original MicroDuck. Two jumper wires from converter #2 carry 5 V up the neck to the A7Z. There are no fuses. The BNO085 IMU is screwed to a rib on the front of the pack plate, between the hip motors. The head holds the Radxa Cubie A7Z, the Radxa Camera 13M 214 behind the eye, a Wi-Fi antenna inside the cap roof, and under the cap roof a small speaker with its MAX98357A amplifier.',
             'The A7Z talks to the OpenRB over two UART wires. Eight thin wires leave the pack over the top of its plate, cross to the right (-Y) side of the torso, and run up the neck in four printed wire clips: one on the right torso shell, one on the neck pitch bracket, one inside the head on the jaw support and one on the A7Z. The bundle enters the head through the opening in the floor of the lower shell, beside the neck; the cap has no notch.',
             'Drawn cables are shown in colour. Use the cable list under each step for the exact ends and lengths.',
         ],
         warnings=['No battery is used. Never connect a battery to this robot.',
                   'Keep the USB-C cable out of the 5991, except for the meter checks in chapter 3, until chapter 10 tells you to plug it in.',
                   'Never let 15 V or 7 V reach the A7Z: it takes 5 V only. Each converter is set and metered with nothing on its output before any load goes on it.'],
         cables=all_cables)

    step('parts', 'start', 'Gather the electronics and kit cables',
         show=LEGS, add=['imu_board', 'camera_board', 'pi'] + board, bench=True,
         camera=ctx.cam(['imu_board', 'pi'] + board, direction=FRONT, margin=1.2),
         prepare=[
             {'item': 'XL330-M288-T servos, IDs 11–15 (from the two OMX-AI kits)', 'qty': 5, 'kind': 'electronic', 'note': 'IDs 1–10 are already in the legs.'},
             {'item': 'OpenRB-150 (from an OMX-AI kit)', 'qty': 1, 'kind': 'electronic', 'note': 'Its header tails get trimmed; use a board from the two kits allocated to the duck, not the reserved third kit.'},
             {'item': 'X3P servo cable 180 mm (OMX-AI kit)', 'qty': 5, 'kind': 'cable', 'note': 'Three controller links plus neck links 11→13 and 14→15.'},
             {'item': 'X3P servo cable 100 mm (OMX-AI kit)', 'qty': 2, 'kind': 'cable', 'note': 'Neck links 12→11 and 13→14.'},
             {'item': 'X3P servo cables for the legs: 180 mm and 100 mm (OMX-AI kit)', 'qty': 'up to 6 + 2', 'kind': 'cable',
              'note': 'Each leg uses three 180 mm cables (hip yaw to hip roll, inside the thigh, knee to ankle) and one 100 mm cable (hip roll to hip pitch). You need only the ones chapter 4 finds missing.'},
             {'item': 'USB-A to USB-C cable (OMX-AI kit)', 'qty': 1, 'kind': 'cable', 'note': 'Laptop to OpenRB: flashing, and the wired control link from the Mac.'},
             {'item': 'Adafruit 5991 USB-C PD board (HUSB238, six DIP switches and a 2-pin screw terminal)', 'qty': 1, 'kind': 'electronic',
              'note': 'DigiKey 1528-5991-ND. Set to 15 V; it sits in the narrow bottom tier of the rear converter box on two M2 × 6 in its lower holes; two lid screws go through its upper holes.'},
             {'item': 'ROBOTIS XL4015 DC converter (the OMX-AI kit "DC converter" module, 61.7 × 26.2 mm, two blue trimmers, IN and OUT screw terminals)', 'qty': 2, 'kind': 'electronic',
              'note': 'From two of the three kits; the third stays on the OMX-F arm. #1 is set to 7.40 V (servos), #2 to 5.00 V (A7Z). Each comes with the ROBOTIS harness screwed into its terminals; that harness comes off and stays with its kit (chapter 3). Each mounts with four M2 × 6 screws.'},
             {'item': 'USB-C PD charger that offers 15 V, with a USB-C cable rated 3 A', 'qty': 1, 'kind': 'electronic', 'note': 'Shawn\'s Xiaomi 67 W charger (5, 9, 15 and 20 V). A charger without a 15 V offer does not work: the 5991 then falls back to a lower voltage.'},
             {'item': '22 AWG solid-core wire, red and black (the club\'s Adafruit box)', 'qty': '3 + 3', 'kind': 'cable',
              'note': 'Solid core because all three are short fixed runs in the rear converter box and the pack (the one wire rule: solid for short fixed runs, stranded for anything that moves or trails). Three pairs: the 15 V feed (5991 to XL4015 #2 IN), the 15 V link (#2 IN to #1 IN) and the 7 V pair (#1 OUT to the OpenRB terminal block). Lengths on the wire list.'},
             {'item': 'Jumper wires for the head 5 V lead: a 30 cm male-female and a 30 cm female-female in red, the same in black', 'qty': '2 + 2', 'kind': 'cable',
              'note': 'Each colour is one chain (male-female into female-female, joint taped) from XL4015 #2 OUT through the neck to the A7Z.'},
             {'item': 'Adafruit BNO085 IMU + 4397 STEMMA QT cable', 'qty': 1, 'kind': 'electronic', 'note': 'Received.'},
             {'item': 'Radxa Camera 13M 214 (Sony IMX214) with its 150 mm 31-pin ribbon', 'qty': 1, 'kind': 'electronic', 'note': 'Ordered 2026-10-15 with the A7Z.'},
             {'item': 'Radxa Cubie A7Z with soldered 40-pin header, microSD card, and the AC019 Wi-Fi antenna from its box', 'qty': 1, 'kind': 'electronic',
              'note': 'Ordered 2026-10-15. Same size and hole pattern as a Pi Zero, so it sits on the same cap rails. The Pi Zero W and the Camera Module 3 Wide are no longer used.'},
             {'item': 'Adafruit MAX98357A I2S amplifier breakout (Adafruit 3006) with five wires soldered straight into LRC, BCLK, DIN, GND and Vin; GAIN and SD left empty, no resistor (BRINGUP step 13)', 'qty': 1, 'kind': 'electronic',
              'note': 'The terminal block comes soldered on. No header goes on this board: the five wires are soldered into its holes, so no right-angle header is needed.'},
             {'item': 'Speaker CMS-30204-18SP (Same Sky, 30 x 20 mm oval, 8 ohm, 1 W) with two thin stranded leads about 30 mm long, cut from a Dupont jumper wire, soldered to its bare pads', 'qty': 1, 'kind': 'electronic'},
             {'item': 'Seeed XIAO ESP32-S3 (21 x 17.8 mm), no headers: reads the five copper touch pads and reports to the A7Z over I2C', 'qty': 1, 'kind': 'electronic',
              'note': 'New purchase, USD 7.49 (seeedstudio.com, XIAO ESP32S3). Its nine wires are soldered straight to its edge pads, like the amplifier; no header goes on it, because a header would stand 20 mm and the board would no longer fit inside the cap.'},
             {'item': 'Copper foil tape with conductive adhesive (Adafruit 1128, 6 mm wide, or wider tape on hand)', 'qty': 1, 'kind': 'other',
              'note': 'New purchase, USD 5.95. Five square pads stuck inside the cap; a finger on the outside of the cap is felt through the 1.7 mm PLA wall.'},
             {'item': 'Foam double-sided tape about 1 mm thick: two strips about 40 x 1.5 mm that together run once round the edge of the speaker grille face', 'qty': 1, 'kind': 'other', 'note': 'Takes the place of the 1 mm foam ring: it fills the 0.6 mm gap between the speaker edge and the collar lip ring, pressed by the retainer screws, so the speaker does not rattle, and it closes the edge so sound from the back of the speaker cannot leak round to the front. The metal grille protects the cone but does neither job. A ring cut from 1 mm foam sheet also works.'},
         ],
         instructions=[
             'Lay out everything in the list. Only the touch parts are new purchases: the Seeed XIAO ESP32-S3 and the copper foil tape.',
             'Count the kit servo cables: you need five 180 mm and two 100 mm X3P cables beyond the ones already in the legs, plus up to six 180 mm and two 100 mm more if the legs were built without their cables (chapter 4 checks).',
             'Keep the unused kit parts (OMX frames, the 12 V supplies and the SMPS2DXL boards) aside; this build uses two of the kit DC converters and nothing else of the power parts. The 12 V supply and the SMPS2DXL are not used. The DFRobot DFR1202 converter and the XT30 and MR30 plugs go into the battery backpack in chapter 11.',
         ],
         checks=['All 15 servos are present and their ID stickers or notes are readable.',
                 'You have at least five 180 mm and two 100 mm spare X3P cables.',
                 'You have two XL4015 converters and a charger that lists 15 V on its label.'])

    new_prints = ctx.keys('shell_left', 'shell_right', 'rear_pack', 'rear_frame', 'rear_lid', 'battery_backpack_frame', 'battery_backpack_cap', 'head_cap', 'head_bottom', 'jaw_frame', 'face_panel', 'eye_trim',
                          'jaw_support', 'mouth_sliding_ring', 'neck_pitch', 'neck_pitch_ring',
                          'speaker_retainer', 'clip_torso', 'clip_bracket', 'clip_head', 'clip_cap')
    step('prints', 'start', 'Print the 21 new parts',
         show=[], add=new_prints, context=LEGS + TORSO, bench=True,
         camera=ctx.cam(new_prints, direction=FRONT, margin=1.05),
         prepare=[{'item': 'PLA, 0.4 mm nozzle (Bambu X1C or Elegoo Centauri Carbon)', 'qty': 'see PARTS-SHEET-V1.19.html, PARTS-SHEET-V1.18.html, PARTS-SHEET-V1.17.html, PARTS-SHEET-V1.9.html and PARTS-SHEET-V1.8.html', 'kind': 'other'},
                  {'item': 'V1.19 package: zhengxia_MicroDuck_V1.19 folder (one orange plate: the new rear converter box cap and the new battery backpack cap)', 'qty': 1, 'kind': 'printed',
                   'note': 'V1.19 holds only the two caps. Each now seats its screw heads on a 3.0 mm printed floor: the 1.0 mm floors of the V1.17 box cap tore through when it came off. The new box cap takes the same four M2 × 10 and fits the V1.17 box frame; the new backpack cap takes three M2 × 8 and fits the V1.18 backpack frame. Replace both old caps; the frames stay. The frame is the cover plate with the bench box width, top and step and a box 26.75 mm deep behind it, printed on its open back rim like the box frame; the cap prints on its flat back face. One plate with a Bambu X1C file (folder X1C) and an Elegoo Centauri Carbon file (folder Elegoo), tree support, no brim; PARTS-SHEET-V1.18.html shows both parts.'},
                  {'item': 'V1.17 package: zhengxia_MicroDuck_V1.17 folder (one orange plate: rear converter box frame and cap and the A7Z cap wire clip; one white plate: both torso shells, the A7Z head cap, the A7Z face panel and both thighs)', 'qty': 1, 'kind': 'printed',
                   'note': 'V1.17 is all of V1.16 plus the three head parts for the Radxa Cubie A7Z and its camera: the A7Z head cap (the V1.9 cap with the board rails cut back to a round pad at each screw hole and a slot at each end, for the camera connector and the microSD card), the A7Z face panel (four bosses for the Radxa Camera 13M 214) and the A7Z cap wire clip (a notch over the micro HDMI socket). The eye trim is unchanged. Two plates, each with a Bambu X1C file (folder X1C) and an Elegoo Centauri Carbon file (folder Elegoo), plus one picture per plate; PARTS-SHEET-V1.17.html shows the parts and the parts they replace. Orange plate: the box frame is one piece, the old cover plate at the front (solid, no wire slot; a 9 mm notch in its top edge and in the front edge of the box top wall lets the four wires drop in from the box top) and behind it a box with two wide tiers for the converters and a narrow bottom tier for the 5991; the cap with rounded edges and nothing sticking out pushes straight onto the back of the box and is held by four hidden M2 × 10, each through a column inside the cap: two at the top corners through the 7 V converter\'s upper holes, two low through the 5991\'s upper holes. No tongues, no hook. The frame prints on its open back rim and the cap on its flat back face, with tree support and no brim. White plate (about 4 h): the V2.0 shells screw down into the V1.9 pack and have no cross tunnel; the cap is the V1.9 cap printed white, unchanged, so it closes with the same three ROBOTIS M2.6 × 6. The thighs are the 10/1 thighs in white, a colour change only: fit them only when a leg is apart anyway. Print the cap roof down with its 4 mm outer brim. Either printer works; the X1C prints the strip on top of the head on the smooth Cool Plate, the Centauri on textured PEI. Both iron the support under the crown, but expect a matte band where the crown printed on support: sand it lightly.'},
                  {'item': 'V1.9 package: zhengxia_MicroDuck_V1.9_2-files.zip (one orange plate: rear electronics pack, head cap, speaker retainer and the four wire clips)', 'qty': 1, 'kind': 'printed',
                   'note': 'A Bambu X1C file and an Elegoo Centauri Carbon file; PARTS-SHEET-V1.9.html shows the seven parts and the two V1.8 parts they retire. The V1.9 pack replaces the V1.8 pack (the BNO085 now screws to a rib instead of standing in a slot) and the V1.9 cap replaces the V1.8 cap (speaker collar and amplifier posts, no rear notch). Print the pack upright on its floor, the retainer flat on its speaker-side face and each clip on the flat face of its tab with the screw hole pointing up. Skip the cap and the cap wire clip on this plate: the V1.17 A7Z cap and clip replace them.'},
                  {'item': 'V1.8 package: zhengxia_MicroDuck_V1.8_8-files.zip', 'qty': 1, 'kind': 'printed', 'note': 'Print the White and Yellow plates and, from the Black plate, the eye trim, the 4.9 mm neck pitch ring that replaces the 4 mm ring from the 10/1 batch under the head-yaw servo, and a 1 mm and a 2 mm shim of the same size that you add under it only if it still rattles. The Orange plate (V1.8 cap and pack) is superseded by the V1.9 set. The pack cover on that plate is retired: the rear converter box frame replaces it. A Bambu X1C and an Elegoo Centauri Carbon file per colour; PARTS-SHEET-V1.8.html shows every part and what it replaces.'},
                  {'item': 'V1.6 print package: zhengxia_MicroDuck_V1.6_8-files.zip', 'qty': 1, 'kind': 'printed', 'note': 'Three parts still come from it: jaw support, mouth sliding ring and neck pitch bracket. Its speaker cradle, speaker keeper, IMU holder, IMU rear cover and OpenRB tray are not used in this build. The V1.7 package is not needed at all: its cap is replaced by the V1.8 cap and its tray is retired.'}],
         instructions=[
             'Everything else comes from the 10/1 batch of 89 parts you already printed.',
             'Print the 21 parts: lower head shell and jaw frame (yellow); face panel, head cap and both torso shells (white); rear electronics pack, rear converter box frame and lid, battery backpack frame and cap, speaker retainer and the four wire clips (orange); eye trim, jaw support, mouth sliding ring, neck pitch bracket and neck pitch ring (black).',
             'Print the V1.19 package (one orange plate: the two caps), the V1.18 package without its cap (the battery backpack frame), the V1.17 package (its box cap is replaced by the V1.19 cap) (its orange plate and its white plate), the V1.9 orange set without its cap and cap clip, the White, Yellow and Black plates from the V1.8 package (the Black plate carries the eye trim, the neck pitch ring and its two optional shims; skip its pack cover) and the other three parts from the V1.6 package. The V1.8 ring is 4.9 mm thick; the 4 mm ring from the 10/1 batch left a 0.9 mm gap under the head-yaw servo and did nothing. If you already printed earlier versions of the head parts, reprint them: the A7Z face holds the Radxa camera on four bosses, the V1.8 eye trim has the two pilots its own two screws thread into, the V1.8 lower shell has no window in its roof behind the face and carries the upper lip, the V1.8 jaw frame carries the lower lip so nothing in the beak is glued, and the A7Z cap (the V1.9 cap in white with relieved rails and two end slots) carries the board 1 mm higher than the V1.7 cap, has a collar for the speaker and two posts for the amplifier in its roof, and has no rear notch. The V1.9 rear pack and the rear converter box together replace the integrated power support, the regulator insert, the OpenRB tray, the fuse carrier, the IMU holder and the IMU rear cover; the V1.9 pack differs from the V1.8 pack only on the plate front, where a rib with two pilot holes replaces the IMU slot and shelf.',
             'The lower head shell and the head cap print lying flat, as in the 10/1 batch; do not reuse the older on-edge files. The rear pack prints standing on its floor, upright as it sits in the robot; the box frame stands on its open back rim and the box cap lies on its flat back face. Peel off any brim, including the 4 mm brim round the cap.',
             'Remove all support material, including thin strands in screw holes, before assembly. On the head cap, open the two small pilot holes beside the speaker collar and the pilot hole in the end of each amplifier post; the collar itself is a shallow ring in the roof and prints without support. On the outside of the cap, support is printed across some of the small sound holes above the speaker: after peeling the crown support, push a needle or a 1.5 mm drill through every sound hole. On the eye trim, make sure the two small pilot holes in its rear face are open. On the rear pack, open the four pilot holes in the round board pads, the four pilot holes in the ends of the two back posts, the USB-C slot in the floor, the window in the left (+Y) wall and the two pilot holes in the rib on the front of the plate. On the box frame, take out every support, open the eight pilot holes in the converter bosses, the four in the 5991 bosses, the two slots in the top wall, the small notch at the top edge of the 5991 terminal window and the wire notch at the front edge of the top wall and in the top edge of the front plate, and clear the four converter windows and the 5991 terminal window in the side walls, and the USB-C window low in the left-hand wall. On each wire clip, run a 2 mm drill or a needle through the screw hole in the tab and make sure the slot into the channel is open along its whole length. On each white torso shell, the small hole in the floor of the round counterbore on top prints on its side: check that an M2 screw drops through it, and if it does not, turn a 2 mm drill through it by hand; pick any support out of the seven horn-screw counterbores on the sides so each screw head seats flat.',
             'These screw seats print over support, so clean them to a flat seat: the three cap-screw tabs on the lower head shell and the four screw seats on the jaw support. On the neck pitch bracket, pick the support out of the shallow round recess in the centre of the horn face so the bracket sits flat on the horn; the thin skin above that recess matches the original part and can stay.',
         ],
         checks=['All 21 parts are printed and cleaned.',
                 'The new neck pitch ring is 4.9 mm thick. The four 4 mm rings from the 10/1 batch stay in use at the two hips and on both sides of the head roll; the fifth is now a spare.',
                 'It is the A7Z cap, printed white: its rear rim is closed all round with no notch and no hood. Inside the roof stand the two board rails, cut back so that only a round pad stands round each of their four pilot holes, with a slot through each end of the board space, a shallow ring (the speaker collar) at the back with a small pilot hole on each side of it, and two short round posts in the middle of the roof with a pilot hole in the end of each. Earlier caps have a rear notch, or round posts in other places; the V1.9 cap has exactly these.',
                 'They are the white V2.0 shells: a round counterbore in the top of each shell near the back with a small hole in its floor, a counterbore round each of the seven horn-screw holes on the sides (not round the rear hole of the right shell, where the clip tab sits), and no tunnel at the back of the left shell.',
                 'Each wire clip is a flat 2 mm tab with one screw hole and a square channel beside it with a slot along one side. The four are different: the torso and bracket clips have the channel beside the tab, the head clip has a taller channel with a window in its side, and the cap clip is the smallest.',
                 'It is the A7Z face: its back is a flat plate with four round bosses round the eye, each with a pilot hole in its top, and two plain holes above and below the eye.',
                 'It is the V1.8 eye trim: two small holes open in its rear face, one above and one below the eye bore.',
                 'It is the V1.8 lower shell: its roof just behind the face is closed on the right-hand side (the earlier shell has a window there).',
                 'The rear pack is one piece: a flat plate with a wide T-shaped top and a notch in its top edge, two screw tabs on each side, a vertical rib with two pilot holes on its front face, four round pads with pilot holes on its back, and behind them an open box with a floor, two side walls, a window in the left (+Y) wall and two tall posts at the back corners.',
                 'The box frame, seen from behind: a front plate with four holes near its corners and a thin lip along its top edge; behind it a box 64 mm wide and 79 mm tall that is open at the back. Its upper part is full width and holds the two converters, one above the other; its bottom part is a narrower tier, 31 mm wide, for the 5991. Each side wall of the upper part has two rectangular windows, one at the height of each converter, cut in from the open back edge; the bottom tier has one window in its right wall (the 5991 terminal) and a taller one in its left wall (the USB-C plug). The front plate has no slot. Inside: eight round bosses for the converters and four standoff bosses for the 5991. At the front edge of the top wall, left of the centre, a 9 mm wide notch continues down into the top edge of the front plate: the four power wires drop through it into the pack. The lid is a cap with rounded edges and nothing sticking out, with four round holes in its back: two at the top corners and two low in its narrow bottom part. Each leads into a column inside the cap for one lid screw. The windows for the converter and 5991 terminals are cut in the side walls of the cap.',
                 'The battery backpack frame has the same front plate and four corner holes as the box frame, with a deeper box behind it (26.75 mm): a rectangular hole in a 3 mm panel in the floor of the narrow bottom part (the switch pocket), a flat window low in the front plate, two thin ribs and four small flexible lips behind the front plate, and two screw bosses high on the side walls. Its cap is rounded like the box cap, with three round holes in its back (two high at the sides, one low in the middle) and two thin fences inside.'],
         warnings=['These parts are no longer used: from the 10/1 batch, the upper lip pad (now printed as part of the lower head shell), the jaw frame and the lower lip pad (now printed as one yellow part), the integrated power support, the open regulator insert, the eleven-fuse carrier, the old head cap with USB window, old lower head shell, old face panel with Pi mount, old eye outer ring, old neck U bracket, coaxial jaw motor support, old torso IMU clamp, old IMU rear cover, small-regulator cover, camera tilt foot, camera cradle, audio carrier and the original PCB retaining strip; from the V1.6 package, the camera retainer, the IMU holder, the IMU rear cover, the speaker cradle and the speaker keeper; and the V1.6 or V1.7 OpenRB tray (PARTS-SHEET-V1.8.html shows each one); the V1.8 pack cover, which the rear converter box frame replaces; the orange torso shells and thighs from the 10/1 batch and the orange V1.9 cap, which the V1.17 white plate replaces (keep these as spares); and, with the move to the A7Z, the V1.8 face panel and the V1.9 cap wire clip, which the V1.17 A7Z face and clip replace. Set them aside so they do not get mixed up with the new prints.'])

    step('tools', 'start', 'Tools and consumables', show=LEGS, camera=ctx.cam(LEGS, direction=FRONT, margin=1.2),
         prepare=[
             {'item': 'Temperature-controlled soldering iron, solder, flux', 'qty': 1, 'kind': 'tool'},
             {'item': 'Multimeter with continuity beep', 'qty': 1, 'kind': 'tool'},
             {'item': 'Wire stripper for 18 to 28 AWG, flush cutter, tweezers', 'qty': 1, 'kind': 'tool'},
             {'item': 'Electrical tape', 'qty': 'club stock', 'kind': 'other', 'note': 'Every joint: three turns, 5 mm past the bare copper on each side. Heat shrink is also fine.'},
             {'item': 'Phillips #0 and #1 screwdrivers and a compact right-angle driver', 'qty': 1, 'kind': 'tool',
              'note': 'The right-angle driver reaches the head-roll screws inside the yaw fork. The #0 driver needs a shaft 5 mm or thinner: the two upper OpenRB screws in the rear pack sit 3 mm from the power-jumper block. The upper BNO085 screw needs a shaft 4 mm or thinner.'},
             {'item': '1.6 mm twist drill in a pin vise', 'qty': 1, 'kind': 'tool',
              'note': 'Once per shell, to drill the pilot for the shell-to-pack screw through the hole in the shell roof.'},
             {'item': 'Self-tapping (TAP) screws: M2 × 4, 6, 8 and 10; ROBOTIS M2.6 × 6 and 8 (the OMX kit screws)', 'qty': 97, 'kind': 'fastener',
              'note': 'Each chapter opens with a "Prepare screws and tools" page that counts every size. The 26 hip screws you take out in chapter 4, and any thigh or ankle screws you take out there to plug a missing leg cable, go back in, so they are not in this count.'},
             {'item': 'Two kinds of wire only: 22 AWG solid-core wire in red and black for the power pairs (15 V feed, 15 V link, 7 V pair), and Dupont jumper wires for everything else (the head 5 V lead and every signal wire)', 'qty': 'club stock', 'kind': 'other',
              'note': 'The next page, "Soldering and wire list", gives the colour and length of every wire.'},
             {'item': 'Female-to-female jumper wires (the breadboard kind, a black plug on each end)', 'qty': 14, 'kind': 'other',
              'note': 'Four 300 mm for the UART pair. Four 300 mm in red, black, blue and yellow for the IMU cable. Five for the amplifier: four 100 mm and one 150 or 200 mm for BCLK. One for the speaker leads, only if the speaker has none. The head 5 V lead takes two more 300 mm female-female (red, black) plus two 300 mm male-female, listed on the parts page.'},
             {'item': 'Small flat screwdriver for the screw terminals (5991, both XL4015 and the OpenRB), the XL4015 trimmers and the amplifier terminal', 'qty': 1, 'kind': 'tool'},
             {'item': 'Narrow cable ties (about 70 × 1.8 mm) and polyimide (Kapton) tape', 'qty': 'club stock', 'kind': 'other'},
             {'item': 'Marker pen and masking tape', 'qty': 1, 'kind': 'other', 'note': 'To flag the two converters "#1 7 V" and "#2 5 V" and to mark each one\'s voltage trimmer.'},
             {'item': 'Narrow cable ties for the leg cables, at most 2.5 mm wide', 'qty': '3 per leg', 'kind': 'other',
              'note': 'Per leg one of at least 160 mm, one of at least 270 mm and one of at least 100 mm. Two short ties hooked together count as one long one.'},
             {'item': 'Laptop with Arduino IDE 2 and DYNAMIXEL Wizard 2.0', 'qty': 1, 'kind': 'tool'},
         ],
         instructions=['Work on a clear, non-conductive bench with eye protection for cutting and soldering.',
                       'Label each wire end with a tape flag as you make it.',
                       'Sort the screws into labelled cups by size. Measure the length under the head: M2 × 4, 6 and 8 differ by only 2 mm each, and M2 and M2.6 do not interchange.',
                       'Every screw in this build is self-tapping into plastic or into a servo case. Turn it until the head touches, then stop. Overtightening strips the hole, and a stripped printed hole means a reprint.'])

    # Every wire, in build order, with its gauge, colour and length (Shawn, 2026-10-13: "我们焊接的线也有很多 ... 我们选哪个
    # 线大概多长"). Lengths are the same values the steps below use. The power path is not soldered at all.
    a = amp_cut
    step('wire-list', 'start', 'Soldering and wire list', show=LEGS, camera=ctx.cam(LEGS, direction=FRONT, margin=1.2),
         prepare=[
             {'item': f'15 V feed: 22 AWG solid core, red + black, {cut["pw-15v"]}', 'qty': 2, 'kind': 'cable',
              'note': 'No solder: 6 mm stripped at each end. 5991 screw terminal (one wire per screw) to XL4015 #2 IN+ and IN− (the 5 V converter, middle tier). Chapter 3, step "Set the 5991 to 15 V and the two XL4015 to 7.40 V and 5.00 V". How the cut lengths are worked out: the longer wire of each pair along its path in the box model, plus 15 mm at each screw terminal, rounded up to 5 mm; cut both colours the same.'},
             {'item': f'15 V link: 22 AWG solid core, red + black, {cut["pw-15v-link"]}', 'qty': 2, 'kind': 'cable',
              'note': 'XL4015 #2 IN+ and IN− (under the same screws as the feed, two solid wires per screw) to XL4015 #1 IN+ and IN− (the 7 V converter, top tier). Chapter 3.'},
             {'item': f'7 V pair: 22 AWG solid core, red + black, {cut["pw-7v"]}', 'qty': 2, 'kind': 'cable',
              'note': 'XL4015 #1 OUT+ and OUT− to the OpenRB terminal block J4 (+ red, − black), one wire per screw: from J4 along the frame\'s lip, up through the notch at the front edge of the box top, over the box top and down the outside of the left wall into #1 OUT, plus 15 mm at each terminal. Into J4 in chapter 5, step "Connect the 7 V pair and plug in the three links"; onto the converter in chapter 10 after its readback.'},
             {'item': f'Head 5 V lead (PI): per colour one 300 mm male-female jumper plugged into one 300 mm female-female jumper, joint taped; red and black, {cut["pi-lead"]}', 'qty': 2, 'kind': 'cable',
              'note': 'From XL4015 #2 OUT through the neck to the A7Z; the chain gives 600 mm, cut it to this length (route, 15 mm at the converter terminal and 45 mm for neck movement and dressing). At the converter end cut the male pin off, strip 10 mm, twist the strands and fold them back on themselves so the screw clamps a double thickness. The female end goes on A7Z pin 2 (red) or 6 (black).'},
             {'item': f'UART pair: jumper wire, green + white (any two colours), {cut["uart"]} mm each', 'qty': 2, 'kind': 'cable',
              'note': 'Each made from two 300 mm jumpers soldered end to end. Soldered into the OpenRB holes printed Rx and Tx; the far end keeps a jumper plug for A7Z pins 7 and 11.'},
             {'item': f'IMU extension: jumper wire, red, black, blue and yellow, spliced into the middle of the 4397 cable so it totals {cut["imu"]} mm', 'qty': 4, 'kind': 'cable',
              'note': 'One 300 mm jumper per colour, both plugs cut off. The far end keeps the 4397 cable\'s own sockets for A7Z pins 1, 3, 5 and 9.'},
             {'item': f'Amplifier wires: female-to-female jumpers, one plug cut off, shortened to LRC {a["amp-lrc"]}, BCLK {a["amp-bclk"]}, DIN {a["amp-din"]}, GND {a["amp-gnd"]} and Vin {a["amp-vin"]} mm (plug included)', 'qty': 5, 'kind': 'cable',
              'note': 'Soldered into the amplifier holes; the plugs go on A7Z pins 35, 12, 40, 39 and 4. Use a 150 or 200 mm jumper for BCLK.'},
             *([{'item': 'Touch pad leads: thin stranded wire (a jumper wire with both plugs cut off), ' + ', '.join(f'{c[6:].upper()} {touch_cut[c]}' for c in TOUCH_PAD_CABLES) + ' mm', 'qty': len(TOUCH_PAD_CABLES), 'kind': 'cable',
                'note': 'Each soldered to a corner of its copper pad and to a XIAO touch pad: L1 to D0, R1 to D1, L2 to D2, R2 to D3, M to D8.'},
               {'item': 'XIAO to A7Z: female-to-female jumpers, one plug cut off, shortened to ' + ', '.join(f'pin {c[9:]} {touch_cut[c]}' for c in TOUCH_PIN_CABLES) + ' mm (plug included)', 'qty': len(TOUCH_PIN_CABLES), 'kind': 'cable',
                'note': 'Soldered to the XIAO edge pads 3V3, GND, D5 (SCL) and D4 (SDA); the plugs go on A7Z pins 17, 25, 29 and 31.'}] if TOUCH_PAD_CABLES else []),
             {'item': 'Speaker leads: jumper wire, 30 mm each (only if the speaker came without leads)', 'qty': 2, 'kind': 'cable',
              'note': 'Soldered to the speaker + and −; the other end is screwed into the green terminal on the amplifier.'},
         ],
         instructions=[
             'Cut each wire to the length on this page before you strip it.',
             'Power pairs (15 V feed, 15 V link, 7 V pair): 22 AWG solid-core wire from the club\'s Adafruit box, red for +, black for −. Stripped, it shows one stiff strand that sits flat under a terminal screw. Each wire is clamped at both ends and never bends in use. The one wire rule: solid core for short fixed runs like these, stranded for anything that moves or trails; the only power cable that trails is the USB-C cable.',
             'Bare copper goes straight under each converter and terminal screw: no ferrules, and no tinned ends (nothing on the power path is soldered).',
             'Unmarked wire: look for "22AWG" printed on the insulation. Otherwise, the smallest stripper hole that takes the insulation off without nicking the copper is its gauge.',
             'Head 5 V lead and signal wires (UART, IMU, amplifier, speaker): Dupont jumper wire.',
             'Signal jumper too short: solder a second one on. Cut a plug off each, strip 5 mm, twist, solder, tape. Only the head 5 V lead is lengthened by plugging (male-female into female-female), with that joint taped.',
             'Insulate every joint with electrical tape: three turns, 5 mm past the bare copper on each side. Heat shrink is also fine; slide it on before you solder.',
         ],
         links=[here('uart-wires', 'Guide: Solder the two UART wires into J12'),
                bringup('s11', 'Detailed page: OpenRB J12, solder two wires', 'BRINGUP step 11'),
                here('bench-test', 'Guide: Set the 5991 to 15 V and the two XL4015 to 7.40 V and 5.00 V'),
                here('orb-power', 'Guide: Connect the 7 V pair and plug in the three links'),
                bringup('s12', 'Detailed page: 15 V from USB-C, 7 V for the servos and 5 V for the A7Z', 'BRINGUP step 12'),
                bringup('s13', 'Detailed page: amplifier, five wires', 'BRINGUP step 13'),
                here('imu-plug', 'Guide: Plug the IMU cable (with the four IMU splices)'),
                here('gpio', 'Guide: Put a jumper-wire end on every wire that goes to the A7Z')])

    # ------------------------------------------------------------------ 2. OpenRB
    orb_cam = ctx.cam(board or pack, direction=TOP_REAR, margin=1.4)
    step('servo-ids', 'openrb', 'Check the neck and head servo IDs',
         show=[], add=ctx.keys('motor11', 'motor12', 'motor13', 'motor14', 'motor15') + board, context=[], bench=True,
         camera=ctx.cam(['motor11', 'motor12', 'motor13', 'motor14', 'motor15'], direction=FRONT, margin=1.2),
         prepare=[{'item': 'Kit USB-A to USB-C cable', 'qty': 1, 'kind': 'cable'},
                  {'item': 'X3P cable 180 mm', 'qty': 1, 'kind': 'cable'}],
         instructions=[
             'In Arduino IDE, add the board manager URL https://raw.githubusercontent.com/ROBOTIS-GIT/OpenRB-150/master/package_openrb_index.json, then install "OpenRB-150" and the Dynamixel2Arduino library.',
             'Upload File > Examples > OpenRB-150 > usb_to_dynamixel. Put the power jumper on the pins marked +5V (the "USB or VIN" position in the e-Manual, away from the VIN(DXL) marking) so a single servo runs from USB.',
             'Connect ONE servo at a time to any OpenRB port. In DYNAMIXEL Wizard 2.0, scan and set: ID 11 (head pitch), 12 (neck pitch), 13 (head yaw), 14 (head roll) or 15 (jaw); Protocol 2.0; baud 1 Mbps; Return Delay Time 0.',
             'Write the ID on a piece of tape on each servo case.',
         ],
         checks=['Each of the five servos answers alone at its new ID and 1 Mbps.'],
         warnings=['Never connect two servos with the same ID to one bus. New XL330 servos ship as ID 1 at 57 600 bps.'])

    step('flash', 'openrb', 'Flash the UART bridge',
         show=board, context=[], bench=True, camera=orb_cam,
         prepare=[{'item': 'guide/firmware/openrb_uart_bridge/openrb_uart_bridge.ino', 'qty': 1, 'kind': 'other'}],
         instructions=[
             'Open openrb_uart_bridge.ino in Arduino IDE, select the board "OpenRB-150" and its USB port, and upload.',
             'The bridge copies bytes between the A7Z UART (OpenRB Serial2, the four J12 pads) and the servo bus at 1 Mbps. The orange USER LED blinks when packets pass. While the bridge is loaded the laptop USB only powers the board; to drive the servos from the laptop directly, upload usb_to_dynamixel instead.',
             'To use DYNAMIXEL Wizard again later, re-upload usb_to_dynamixel, then upload the bridge again before running the robot.',
         ],
         checks=['The upload finishes with no error.'])

    step('jumper-tails', 'openrb', 'Set the power jumper and trim the header tails',
         show=board, bench=True, camera=ctx.cam(board or pack, direction=(-0.3, -1.0, -0.6), margin=1.6),
         prepare=[{'item': 'Flush cutter', 'qty': 1, 'kind': 'tool'}, {'item': 'Polyimide tape', 'qty': '30 mm', 'kind': 'other'}],
         instructions=[
             'Move the power jumper to the VIN(DXL) side. The board will run from its terminal block.',
             'Turn the board over. Cut every stacking-header pin tail so nothing sticks out more than 1.5 mm below the board. Hold the tail tips so they do not fly.',
             'File any sharp burr, blow away cut pieces, then cover the cut tails with one layer of polyimide tape.',
         ],
         checks=['A ruler laid across the underside rocks on nothing taller than 1.5 mm.',
                 'No cut pin fragment is stuck between the pins.'],
         warnings=['Trimming is permanent. The pack needs it: the board stands on four 3.8 mm pads, so its back is only 3.8 mm from the pack plate.'])

    step('uart-wires', 'openrb', 'Solder the two UART wires into J12',
         show=board, bench=True, camera=ctx.cam(board or pack, direction=TOP_REAR, margin=1.6),
         wiring=openrb_wiring(cut),
         prepare=[{'item': f'Jumper wire, green and white (any two colours), {cut["uart"]} mm each', 'qty': 2, 'kind': 'cable',
                   'note': 'Make each from two 300 mm female-to-female jumpers of one colour, soldered end to end.'},
                  {'item': 'Electrical tape and masking tape', 'qty': 1, 'kind': 'other'},
                  {'item': 'Soldering iron, solder, wire stripper, flush cutter, multimeter', 'qty': 1, 'kind': 'tool'},
                  {'item': 'Desoldering braid and tweezers', 'qty': 1, 'kind': 'tool',
                   'note': 'Only if a connector is already soldered into the four holes.'}],
         instructions=[
             'Done: two wires soldered into the OpenRB holes printed Rx and Tx. Each ends in a jumper plug with a tape flag, 7 or 11.',
             'Where: hold the OpenRB with the USB-C socket at the top. Just above the 3-pin row with the jumper cap is a row of four small holes, printed Tx Rx V G. Use only Rx and Tx. V and G are unused.',
             'If a connector is already soldered in those holes: snip its plastic body off, heat each pin from the back and pull it out from the front with tweezers. Clear the Rx and Tx holes with the braid.',
             f'Make the green wire: cut one plug off each of two green jumpers, strip 5 mm, twist the two ends together, solder, tape three turns. Measure {cut["uart"]} mm from the remaining plug, cut, strip 3 mm.',
             'Make the white wire the same way.',
             'Push the green wire into the Rx hole from the front (the component side) and the white wire into Tx. Solder on the back and cut off the copper that sticks out.',
             'Flag the plugs: green 7, white 11. Those are their A7Z pins (UART2: pin 7 sends, pin 11 receives).',
         ],
         checks=['Meter on beep: Rx and Tx do not beep to each other or to G.',
                 'Touch the metal inside the green plug and the Rx joint: beep. White plug and the Tx joint: beep.'],
         links=[bringup('s11', 'Detailed page: OpenRB J12, solder two wires', 'BRINGUP step 11: J12 photo with each pad marked, taking off a soldered connector, flashing the bridge (its Pi pin numbers are the old head; on the A7Z the plugs go on 7 and 11)'),
                a7z('uart', 'A7Z wiring page: the UART pair on pins 7 and 11'),
                here('wire-list', 'Soldering and wire list')])

    # ------------------------------------------------------------------ 3. Supply boards on the bench
    # 7 V servo rail (Shawn, 2026-10-14; PROJECT-CONTEXT.json current_build.servo_rail_7v_20261014), set point 7.40 V since
    # 2026-10-15 (current_build.servo_shutdown_52_20261015, robotics DECISIONS.md D-014); 5991 stays at 15 V. The id stays
    # 'bench-test' because bringup/build/guide-benches.ts keys on the chapter-3 step ids. Sources: wiring/openrb.py
    # (5991 DIP mapping and HUSB238 fallback, XL4015 photo); XL4015 limits: XLSEMI XL4015 datasheet summary
    # (radiolocman.com/datasheet/data.html?di=685191: 8-36 V input, 1.25-32 V output, 5 A, 0.3 V minimum dropout) and
    # CC/CV module vendor notes (probots.co.in XL4015 CC/CV module, https://probots.co.in/xl4015-5a-constant-current-voltage-led-driver-lithium-battery-charger.html:
    # one trimmer for voltage, one for the current limit, clockwise raises the limit, 3-4 A without a heatsink;
    # protosupplies.com XL4015 module, https://protosupplies.com/product/xl4015-adjustable-dc-dc-step-down-module/: clockwise raises
    # the voltage, output at most about 1.5 V below the input). Set point 7.40 V (accept
    # 7.35-7.45 V), Shawn 2026-10-15: every servo holds Shutdown 52 (set_shutdown.py, first-power step), so the 7.0 V Max
    # Voltage Limit no longer cuts torque; 7.4 V is the 2S nominal voltage of the battery backpack. 5991 at 15 V with only
    # the 15V slider ON. Exactly one slider (Shawn 2026-10-15: with 5V also ON the board negotiated 5 V, read 5.167 V);
    # 9 V is not allowed: on 9 V the first walk command browned out the whole input within 0.5 s (2026-10-15 ~17:00,
    # /tmp/duck_wired_log_1015b.jsonl: 7.1 V and 5 deg tilt before the cut; 15 V since, #1 still 7.35 V). Trimmer
    # photo: figures/xl4015-trimmers-en.jpg from bringup/parts/photos/xl4015_trimmers_annotated.png (CV = right trimmer
    # next to U1, CC = left trimmer next to the LM358, inferred from the layout; the meter test confirms it).
    step('bench-test', 'harness', 'Set the 5991 to 15 V and the two XL4015 to 7.40 V and 5.00 V', show=LEGS,
         camera=ctx.cam(LEGS, direction=FRONT, margin=1.2), wiring=openrb_wiring(cut),
         prepare=[{'item': 'Adafruit 5991 USB-C PD board', 'qty': 1, 'kind': 'electronic'},
                  {'item': 'ROBOTIS XL4015 DC converter (OMX-AI kit)', 'qty': 2, 'kind': 'electronic'},
                  {'item': 'USB-C PD charger that offers 15 V, with its USB-C cable', 'qty': 1, 'kind': 'electronic', 'note': 'The Xiaomi 67 W charger (5, 9, 15 and 20 V).'},
                  {'item': f'22 AWG solid-core wire, red and black: the 15 V feed ({cut["pw-15v"]}) and the 15 V link ({cut["pw-15v-link"]})', 'qty': '2 + 2', 'kind': 'cable'},
                  {'item': 'Small flat screwdriver, wire stripper, multimeter, marker pen and masking tape', 'qty': 1, 'kind': 'tool'}],
         instructions=[
             'Done: the 5991 has only its 15V switch on and its terminal reads about 15 V; the 15 V feed runs from the 5991 terminal to XL4015 #2 IN and the 15 V link from #2 IN to #1 IN; with nothing connected to either output, #1 reads 7.35 to 7.45 V (set 7.40 V) and #2 reads 4.95 to 5.10 V at its OUT screws. Nothing is soldered.',
             'Keep the USB-C cable out of the 5991 while you set the switch and fit the wires.',
             'The six sliders of the DIP switch are printed 5V, 9V, 12V, 15V, 18V and 20V from the top, with the switch numbers 6 to 1 on the other side. Push only slider 3, printed 15V, to ON (towards the voltage labels). The other five stay OFF: exactly one slider ON. With the 5V slider also ON the board asked for 5 V (measured 5.17 V on 2026-10-15); with all six off it asks the charger for its highest voltage, 20 V on the Xiaomi charger. Do not use the 9V slider: on 2026-10-15 its 9 V offer (about 27 W) browned out the whole robot within half a second of the first walk command: all 15 servos dropped torque, the OpenRB USB reset and the head computer went offline. Walking needs the 15 V offer (45 W). The board reads the switch only when the USB-C cable is plugged in: after changing a slider, unplug and plug in again before you measure.',
             'Leave the ISet jumper closed and the two OFF pads open. With ISet closed the board asks for 15 V at 1.25 A, which the charger\'s 15 V / 3 A offer meets. Cut, it would ask for 3.25 A, more than that offer, and the board would fall back to a lower voltage.',
             'Flag the two converters with tape: "#1 7 V" and "#2 5 V". Each has an IN block and an OUT block of two screws, with IN+ and OUT+ printed beside one screw of each block; on the kit boards it is the lower screw with the trimmers at the bottom and the inductor at the top.',
             'The two spare kit converters come with the ROBOTIS harness screwed into both terminal blocks (a JST EH plug at each end, ferrules under the screws). Loosen the four terminal screws of each converter, pull the harness out and keep it with its kit. Our wires go straight into the terminals as bare solid copper: no ferrules, no tinning.',
             'Strip 6 mm off both ends of the 15 V feed and of the 15 V link. Feed: red from the 5991 terminal + (marker 9) to #2 IN+ (marker 15), black from − (marker 10) to #2 IN− (marker 16). Link: red from #2 IN+ to #1 IN+ (marker 11), black from #2 IN− to #1 IN− (marker 12). At #2 IN each screw clamps two solid wires side by side; at the 5991 and at #1 IN one wire per screw. Each wire goes straight into its terminal; leave the wires straight for now, the box step bends them. Tighten every screw and tug every wire: none moves.',
             'Nothing goes on either OUT block in this step. Lay the converters apart on the bench so no screw touches another.',
             'Plug the USB-C cable into the charger and into the 5991. Meter on DC volts, red probe on the 5991 terminal +, black on −: 14.5 to 15.5 V.',
             'Find the voltage trimmer on #1. Each converter has two blue multi-turn trimmers printed W103. Held with OUT on the left, IN on the right and the trimmers at the bottom (the picture above), the right-hand trimmer, next to the big XL4015 chip (U1), should be the voltage (CV) trimmer and the left-hand one, next to the small 8-pin LM358, the current limit (CC). That is read from the board layout, so check it: meter on #1 OUT+ and OUT−, turn the right-hand trimmer two full turns clockwise and watch the meter. If the reading moves, that trimmer sets the voltage: mark it with a dot of marker. If nothing changes, it is the current-limit trimmer (it does nothing with no load): turn it back two turns and use the other one.',
             'Set #1: turn its voltage trimmer slowly until the meter reads 7.40 V (accept 7.35 to 7.45 V). Clockwise usually raises the voltage; the meter decides. 7.40 V is above the servos\' 7.0 V Max Voltage Limit on purpose: in chapter 10 every servo gets Shutdown 52 before it runs, so above 7.0 V it raises its input-voltage flag and keeps its torque. It is also the nominal voltage of the 2S battery, so the bench and the battery feed the servos alike.',
             'Turn the current-limit trimmer of #1 clockwise until it slips at the end of its travel (up to about 25 turns), so the limit sits at its highest and does not cut the servo current peaks. The meter reading stays put while you do this.',
             'Set #2 the same way: find and mark its voltage trimmer, set 4.95 to 5.10 V, then turn its current-limit trimmer clockwise to the end.',
             'Unplug the USB-C cable, wait until the converter LEDs are dark, plug it in again and read both outputs once more. Write both values on the tape flags.',
             'Unplug the USB-C cable. The three boards go into the rear converter box in chapter 5 with these wires still in place, as one chain: 5991, then #2, then #1. The outputs stay empty until chapter 10.',
         ],
         checks=['5991 terminal: 14.5 to 15.5 V, red positive, read after a fresh plug-in. Only slider 3 (15V) is ON and ISet is not cut.',
                 'XL4015 #1 OUT, nothing connected: 7.35 to 7.45 V, red positive, after a fresh plug-in.',
                 'XL4015 #2 OUT, nothing connected: 4.95 to 5.10 V, red positive, after a fresh plug-in.',
                 'Each converter carries its tape flag with its measured voltage, and its voltage trimmer has a marker dot.',
                 'The two ROBOTIS harnesses are off the converters and packed with their kits.',
                 'Pull each wire: it stays under its screw.'],
         warnings=['Never connect the OpenRB, a servo or the A7Z to an XL4015 output before you have metered that output in this step. An unadjusted converter can put out nearly its full 15 V input.',
                   'A 5991 reading near 5, 9, 12 or 20 V means the switch is wrong (more than one slider ON, or the wrong one), or the charger has no 15 V offer and the 5991 fell back to a lower voltage it is offered: unplug at once, set exactly one slider (15V), and plug in again. 9 V is not enough even though #1 can make 7.40 V from it: the 9 V offer browned out the robot on its first walk command. From 5 V converter #1 cannot make 7.4 V at all.',
                   'The XL4015 has no reverse-polarity protection: + to IN+ and − to IN− every time.'],
         images=[figure('xl4015-trimmers-en.jpg', 'XL4015 kit converter held as it sits in the box: OUT on the left, IN on the right, trimmers at the bottom. The right-hand trimmer, beside the XL4015 chip (U1), should set the voltage; the left-hand one, beside the LM358, the current limit. This is read from the board layout: confirm it with the turn-and-watch meter test before you set #1 to 7.40 V.')],
         links=[bringup('s12', 'Detailed page: 15 V switch, the two XL4015 settings, OpenRB J4 and A7Z pins 2 and 6', 'BRINGUP step 12'),
                here('orb-power', 'Guide: Connect the 7 V pair and plug in the three links'),
                here('first-power', 'Guide: First power: converter readback, bus scan and voltage-limit check'),
                here('wire-list', 'Soldering and wire list')])

    # ------------------------------------------------------------------ 4. Hips open, leg cables
    leg_rest = [k for k in ctx.module_keys('left-leg') + ctx.module_keys('right-leg') if k not in YAW_LINKS + HIP_YAW + HIP_ROLL]
    hips = YAW_LINKS + HIP_YAW + HIP_ROLL
    step('hip-open', 'legs', 'Open both hips so the torso base can go in',
         show=leg_rest + YAW_LINKS, context=HIP_YAW + HIP_ROLL,
         camera=ctx.cam(hips, direction=(0.9, -1.2, 0.5), margin=1.3),
         prepare=[{'item': 'Six small cups, labelled L1, L2, L3, R1, R2, R3', 'qty': 6, 'kind': 'other',
                   'note': 'Every screw you take out here goes back in later in this chapter.'}],
         instructions=[
             'The torso base sits between each hip-yaw motor (ID10 left, ID5 right) and the yaw link under it. On a finished leg the hip-roll motor (ID9, ID4) covers the four screws that hold the yaw link to the motor, so each hip has to come apart first. This undoes steps 13 to 20 of the leg guide. Work on one leg at a time.',
             'If a cable already joins ID5 to ID4 (ID10 to ID9 on the left), unplug it at the hip-yaw end (ID5, ID10) now and let it hang from the hip-roll motor: its route changes in this build. Leave every other leg cable plugged.',
             'Cup 1: remove the four M2 × 6 screws at the front of the hip bridge that hold it to the hip-roll output (ID9 left, ID4 right). Slide the whole yaw-and-roll group 45 mm backwards off the bridge. The thigh, knee, ankle and foot stay together.',
             'Cup 2: on the bench, remove the four M2 × 8 case screws (two through the tall passive support from the front, two through the yaw link from the back) and the M2.6 × 6 rear-centre screw with its 0.5 mm washer. Slide the hip-roll motor and the passive support forwards out of the yaw link.',
             'Cup 3: the four M2 × 6 screws holding the yaw link to the hip-yaw output horn are now in the open cavity. Remove them and lift the hip-yaw motor off the link.',
         ],
         checks=['Each leg is now three pieces: the hip-yaw motor, the empty yaw link and the rest of the leg with the hip-roll motor beside it.',
                 'You have 13 screws and one washer per leg, sorted in three cups.'],
         warnings=['Do not try to slide the torso base in with the hips closed. It cannot pass the motor, and forcing it cracks the base.'])
    installed[:] = list(YAW_LINKS)   # the rest of each leg waits on the bench until leg-join

    # Leg cables. Sockets and routes: the neutral leg routes reviewed on 2026-10-09 (leg_routes.py,
    # build-pack-20260913/.../motor-wires/slack-packaging/INSTALL-SEQUENCE.md). Thigh and ankle plugs can only go in
    # while their servo is out of the thigh or the ankle fork (leg guide operation dependencies); the hip links now
    # drop through the torso base's centre slot because the rear pack fills the pocket of the old coiled route.
    leg_bench = leg_rest + HIP_ROLL
    step('leg-cable-check', 'legs', 'Check the cables already in each leg', show=leg_bench, context=[], bench=True,
         cables=THIGH_CABLES, camera=ctx.cam(THIGH_R + ANKLE_R + ['motor4'], direction=RIGHT_REAR, margin=1.2),
         instructions=[
             'Each leg is one servo chain of four kit cables. Right leg: 5 → 4 (hip yaw to hip roll, 180 mm), 4 → 3 (hip roll to hip pitch, 100 mm), 3 → 2 (hip pitch to knee, inside the thigh, 180 mm) and 2 → 1 (knee to ankle, 180 mm). The left leg is the mirror image: 10 → 9, 9 → 8 (100 mm), 8 → 7 and 7 → 6.',
             'The two sockets on an XL330 are wired in parallel, so electrically either one works. Still use the socket shown for each plug in the drawing and the cable list: that choice keeps neighbouring plugs and wires from crossing in the narrow thigh.',
             'The hip cable (5 → 4, 10 → 9) gets a new route in any case, in the last step of this chapter. Check the other three cables on each leg. Look into the orange thigh: the hip-pitch servo (ID3, ID8) and the knee servo (ID2, ID7) need two plugs each. The ankle servo (ID1, ID6) needs one. The hip-roll servo (ID4, ID9), loose beside the leg now, needs the 100 mm cable to the hip-pitch servo.',
             'Pull each cable gently near its plug: a latched plug does not move. Follow each cable from end to end to be sure it reaches the right servo.',
             'If a leg has all three cables, skip the next four steps for that leg and go on to "Plug the hip cable into the hip-roll motor".',
         ],
         checks=['For each leg you know which of 4 → 3, 3 → 2 and 2 → 1 (9 → 8, 8 → 7, 7 → 6) is missing, at which end.'],
         warnings=['Do not push a plug into a socket inside the closed thigh or behind a fitted lower link. The plug cannot go straight in there, and levering it breaks the socket latch or the print. The next steps open only what blocks the socket.'])

    step('leg-thigh-open', 'legs', 'Open the thigh (only on a leg missing a thigh plug)', show=leg_bench, context=[], bench=True,
         camera=ctx.cam(THIGH_R + BRIDGE_R, direction=RIGHT_REAR, margin=1.3),
         prepare=[{'item': 'Three more small cups per opened leg, labelled T1, T2, T3', 'qty': 3, 'kind': 'other',
                   'note': 'Every screw you take out here goes back in before the end of this chapter.'}],
         instructions=[
             'Do this only on a leg where 4 → 3, 3 → 2 or 2 → 1 is missing at the hip-pitch or knee servo, including an ankle cable whose upper end is missing. It undoes steps 1 to 4, 10 and 18 of the leg guide.',
             'Cup T1: remove the four M2 × 6 screws that hold the hip bridge to the hip-pitch output horn (ID3 right, ID8 left). The hip-roll group came off in the previous step, so they are open now. Lift the hip bridge off together with its two support rings.',
             'Cup T2: remove the four M2 × 6 screws that hold the lower link to the knee output horn (ID2, ID7). Slide the whole ankle-and-foot module sideways off the knee, towards the robot\'s centre line, the way it went on. Keep it in one piece.',
             'Cup T3: remove the two M2.6 × 6 rear-centre screws (no washers) and the four M2 × 8 case screws of the two thigh servos, then lift out the knee support ring.',
             'Slide both thigh servos and the black 1 mm plate out of the orange thigh towards the robot\'s centre line, the way they went in, until both sockets of both servos are free. Cables that are already plugged stay plugged.',
         ],
         checks=['Both thigh servos are out of the thigh and all four of their sockets can be reached.',
                 'Cup T1 holds four M2 × 6, cup T2 four M2 × 6, cup T3 four M2 × 8 and two M2.6 × 6.'])

    step('leg-thigh-plug', 'legs', 'Plug both thigh servos and slide them back', show=leg_bench, context=[], bench=True,
         cables=THIGH_CABLES, camera=ctx.cam(THIGH_R, direction=(-0.4, -1.2, 0.6), margin=1.3),
         prepare=[{'item': 'X3P 100 mm kit cable (only if 4 → 3 or 9 → 8 is missing)', 'qty': 'per leg 1', 'kind': 'cable'},
                  {'item': 'X3P 180 mm kit cable (only for a missing 3 → 2, 2 → 1, 8 → 7 or 7 → 6)', 'qty': 'per leg up to 2', 'kind': 'cable'}],
         instructions=[
             'Right leg: ID3 socket 14 takes the 100 mm cable from ID4 (its other end goes into ID4 socket 14). One 180 mm cable joins ID3 socket 13 to ID2 socket 14. ID2 socket 13 takes the 180 mm ankle cable; its other end goes to ID1 socket 13 later.',
             'Left leg: ID8 socket 13 takes the 100 mm cable from ID9 (other end in ID9 socket 13). One 180 mm cable joins ID8 socket 14 to ID7 socket 13. ID7 socket 14 takes the 180 mm ankle cable for ID6 socket 14.',
             'Push each plug straight in, holding the housing and not the wires, until it clicks.',
             'Lay the wires as drawn before the servos go back. The 100 mm cable turns down out of its plug before it runs sideways, so the passage behind the servos stays free. The 3 → 2 (8 → 7) cable runs behind the rear frame, dips low, turns inboard below the hip-pitch servo, keeps its extra length outside the frame edge and comes back above the knee servo. The ankle cable leaves the knee servo towards the centre of the frame and turns inboard around the lower lip of the thigh.',
             'Slide both servos and the plate back into the thigh with every cable plugged, feeding the loose wires out through the thigh opening as they go. Lay the cables side by side in the narrow rear passage, never on top of each other, and never under the plate, the ring or a screw seat.',
             'Refit the knee support ring, then drive the four M2 × 8 case screws and the two M2.6 × 6 rear centres from cup T3. Stop when each head touches.',
         ],
         checks=['Every plug on the two thigh servos is latched.',
                 'No wire is trapped under the plate, the ring or a screw head, and both servos sit as they did before.'])

    step('leg-ankle-plug', 'legs', 'Plug the ankle servo (only if its plug is missing)', show=leg_bench, context=[], bench=True,
         cables=['dxl-2-1', 'dxl-7-6'], camera=ctx.cam(ANKLE_R, direction=(0.3, -1.2, 0.5), margin=1.4),
         prepare=[{'item': 'One more small cup per opened ankle, labelled A', 'qty': 1, 'kind': 'other'}],
         instructions=[
             'Do this only if the ankle end of 2 → 1 (7 → 6) is missing. It undoes steps 5 to 8 of the leg guide on the ankle-and-foot module. The foot stays on.',
             'If the module is still on the knee, take it off first: remove the four M2 × 6 knee-output screws into a cup labelled T2 and slide it off towards the centre line.',
             'Cup A: remove the four M2 × 4 output screws, the two M2 × 10 case screws and the M2.6 × 8 rear centre with its 0.5 mm washer.',
             'Pull the lower link straight off the ankle. It was pressed on hard; pull evenly, without twisting. If it does not come off with steady hand pressure, stop and do not lever against the sleeve.',
             'Lift ID1 (ID6) about 30 mm up out of the fork and plug the ankle cable into ID1 socket 13 (ID6 socket 14). Lower the servo back into the fork with the cable leading out through the open side.',
             'Press the lower link back on with the wires beside its end, not under it. Then the screws from cup A: the rear centre with its washer, the two case screws and the four output screws.',
         ],
         checks=['The lower link sits exactly as before and the ankle turns freely by hand.',
                 'The cable leaves the ankle beside the link end without being pinched.'])

    step('leg-thigh-close', 'legs', 'Close each leg and tie the leg cables', show=leg_bench, context=[], bench=True,
         cables=THIGH_CABLES, camera=ctx.cam(THIGH_R + ANKLE_R + BRIDGE_R, direction=RIGHT_REAR, margin=1.2),
         prepare=[{'item': 'Narrow cable ties (at most 2.5 mm wide): at least 160 mm, 270 mm and 100 mm long', 'qty': 'one of each per leg', 'kind': 'other'}],
         instructions=[
             'On an opened leg: slide the ankle-and-foot module back onto the knee output and drive the four M2 × 6 from cup T2; then set the hip bridge with its two rings back on the hip-pitch output and drive the four M2 × 6 from cup T1.',
             'Tie the cables on every leg, opened or not. Keep each cable\'s spare length on the thigh. Put the 160 mm tie around the case of the hip-pitch servo to hold the 100 mm cable and the 3 → 2 (8 → 7) cable where they run past it.',
             'Wrap the 270 mm tie around the thigh frame where the ankle cable\'s spare length hangs, and hook the 100 mm tie loosely through it, outside the frame, to gather that spare length.',
             'Never tie a cable to the lower link, the ankle, the foot or the hip bridge: they move against the thigh.',
             'Leave the ties loose. Move the knee and the ankle by hand through their whole range, let each loop find its place, then pull the ties snug without crushing the wires.',
         ],
         checks=['Knee and ankle move end to end without any cable going tight, rubbing an edge or entering a gap that closes.',
                 'All T and A cups are empty.'])

    step('hip-cable-roll', 'legs', 'Plug the hip cable into the hip-roll motor', show=leg_bench, context=[], bench=True,
         cables=HIP_CABLES, camera=ctx.cam(HIP_ROLL + ['washer4'], direction=(-1.0, -0.6, -0.4), margin=1.4),
         prepare=[{'item': 'X3P 180 mm kit cable (only if the leg has no hip cable)', 'qty': 'per leg 1', 'kind': 'cable'}],
         instructions=[
             'Done: one 180 mm cable plugged into each hip-roll servo, its other end free.',
             'The hip-roll servo (ID4, ID9) is loose beside its leg. Plug the cable into the socket on its rear face nearer the robot\'s centre line: ID4 socket 13, ID9 socket 14. A cable already plugged there stays.',
             'Leave the other end free. In the next chapter it goes up through the slot in the middle of the torso base to the hip-yaw servo.',
         ],
         checks=['The plug is latched in the inner rear socket, and the free end is not plugged anywhere.'])

    # ------------------------------------------------------------------ 5. Torso

    step('torso-base', 'torso', 'Stack the yaw links, rings, torso base and hip-yaw motors',
         add=['ring10_torso', 'ring5_torso', 'torso_base'] + HIP_YAW,
         approach={'ring10_torso': [0, 0, 28], 'ring5_torso': [0, 0, 28], 'torso_base': [0, 0, 28], 'motor10': [0, 0, 28], 'motor5': [0, 0, 28]},
         camera=ctx.cam(['torso_base'] + YAW_LINKS + HIP_YAW, direction=FRONT, margin=1.3), cables=HIP_CABLES,
         prepare=[{'item': 'Torso base (10/1 print)', 'qty': 1, 'kind': 'printed'},
                  {'item': '22 mm sliding ring (10/1 print)', 'qty': 2, 'kind': 'printed'}],
         instructions=['Stand the two empty yaw links on the bench, left and right, as they sit under the robot.',
                       'Drop a 22 mm sliding ring onto each link around its horn seat. It is loose until the base sits on it; then the ring is pinched between link and base and carries the leg\'s tipping load instead of the servo shaft.',
                       'Find the 12 × 6 mm slot in the middle of the torso base. Keep each leg next to its yaw link and push the free end of its hip cable up through the slot from below: the right cable through the right (−Y) half, the left one through the left half. The plug fits through. Pull about 100 mm up and lay it forward over the base.',
                       'Lay the black torso base over both rings, with the two hip cables running down through the slot to their legs.',
                       'Set ID10 (left) and ID5 (right) on top of the base, each output horn going down through the base and its ring onto the yaw link. Line up the four horn holes with the link holes.'],
         checks=['The base lies flat on both rings and each motor case sits flat on the base.',
                 'Both hip cables pass through the centre slot and no cable is under a motor or a ring.'])

    step('hip-yaw-fasten', 'torso', 'Fasten each yaw link to its hip-yaw motor',
         camera=ctx.cam(YAW_LINKS + HIP_YAW, direction=(0.6, -0.9, -1.0), margin=1.4),
         prepare=[tap(8, 'M2 × 6')],
         screwNotes={'M2 × 6 TAP': 'Cup 3. Driven up from below through the empty roll-motor cavity.'},
         instructions=['Hold the stack together and turn it over. Keep both legs beside it on the bench so they do not hang on their hip cables.',
                       'Through the empty roll-motor cavity of each link, drive the four M2 × 6 from cup 3 up into the output horn. Eight in total.'],
         checks=['Each link is pulled tight against its ring with no gap.'])

    step('hip-roll-refit', 'torso', 'Put the hip-roll motors back into the yaw links',
         add=HIP_ROLL, approach={k: ([-10, 0, 0] if k.startswith('washer') else [45, 0, 0]) for k in HIP_ROLL},
         camera=ctx.cam(YAW_LINKS + HIP_ROLL, direction=(1.0, -1.0, -0.4), margin=1.3),
         prepare=[tap(8, 'M2 × 8'), tap(4, 'M2 × 6'), tap(2, 'M2.6 × 6'),
                  {'item': '0.5 mm M2.5 metal washer (DIN433) from cup 2', 'qty': 2, 'kind': 'fastener'}],
         screwNotes={'M2 × 8 TAP': 'Cup 2. Two per side through the passive support from the front, two through the yaw link from the back.',
                     'M2 × 6 TAP': 'Two per side, from the front through the small top tab of the passive support into the yaw link.',
                     'M2.6 × 6 TAP': 'Cup 2. Rear centre, with the 0.5 mm washer under the head.'},
         instructions=['Do this before the rear pack goes on: its plate covers the rear screws.',
                       'Lead each hip cable from its plug on the rear of the hip-roll motor inboard and up to the centre slot. Then slide ID9 (left) and ID4 (right) back into their yaw links from the front, then the tall passive supports, as in the leg guide. The cable stays in the gap between the two yaw links, away from the screw holes.',
                       'Per side: two M2 × 8 through the passive support from the front, two M2 × 8 through the yaw link from the back, and the M2.6 × 6 with its washer in the rear centre.',
                       'Then, per side, two M2 × 6 from the front through the two holes in the small tab along the top of the passive support, into the yaw link behind it. The leg guide has no screws here; they tie the top of the support to the link.'],
         checks=['Each hip-roll motor sits square in its link and the passive support is flush.',
                 'No screw head traps a hip cable; each cable still slides a little in the centre slot.'])

    step('imu-board', 'torso', 'Screw the BNO085 onto the pack rib on the bench', add=['imu_board'], show=pack, context=[], bench=True,
         # Bring the board in from the front, 6 mm to the +Y side of the rib, slide it back beside the plate, then press it
         # sideways onto the rib. A straight sideways path from further out starts inside the pack's +Y upper hip-yaw tab.
         approach={'imu_board': [[10, 6, 0], [0, 6, 0]]},
         camera=ctx.cam(IMU + pack, direction=(1.0, 1.0, 0.6), margin=1.5),
         prepare=[{'item': 'Rear electronics pack (V1.9 print, orange)', 'qty': 1, 'kind': 'printed'},
                  {'item': 'BNO085 board', 'qty': 1, 'kind': 'electronic'}, tap(2, 'M2 × 4'),
                  {'item': 'Phillips #0 driver with a shaft 4 mm or thinner', 'qty': 1, 'kind': 'tool', 'note': 'For the upper screw; any driver up to 6 mm reaches the lower one.'}],
         screwNotes={'M2 × 4 TAP': 'Through a rear corner hole of the board into a pilot in the rib on the front of the pack plate: 1.6 mm of board, then 2.1 mm of thread in the rib, with the tip 0.8 mm short of the rib back.'},
         instructions=[
             'Do this with the pack still off the robot. Stand the pack on the bench with its plate facing you and the open box away from you. Find the vertical rib in the middle of the plate front, with its two pilot holes one above the other.',
             'Hold the board on edge with its components facing the robot\'s left (+Y) and the STEMMA QT socket at the top. Bring it in from the front, just to the left (+Y) of the rib, slide it back until its rear edge is beside the plate, then press it sideways onto the rib so its back lies flat on the rib face and the two holes in its rear edge sit over the two pilots; the two front holes stay empty.',
             'Drive one M2 × 4 through the lower rear hole into the rib. Stop when the head touches the board.',
             'Drive the second M2 × 4 through the upper rear hole with the thin-shaft driver: the board edge sits close to the plate there. Stop when the head touches.',
         ],
         checks=['The board lies flat on the rib with no gap, socket up, and does not move when you press its free front edge.',
                 'Its two front holes are empty.'])

    step('pack-in', 'torso', 'Slide in the rear electronics pack', add=pack + ['imu_board'],
         group={'label': 'Rear pack with the BNO085 screwed on', 'approach': [-30, 0, 0]},
         camera=ctx.cam(TORSO + HIP_YAW, direction=REAR, margin=1.3),
         prepare=[{'item': 'Rear electronics pack (V1.9 print, orange) with the BNO085 already screwed to its rib', 'qty': 1, 'kind': 'printed'}],
         instructions=['Turn the stack upright. Hold the pack with its open box towards you and the wide T-shaped top up; the four round board pads face you, and the BNO085 stands on the far side of the plate.',
                       'Slide it in from the rear until its plate sits against the backs of both hip-yaw motor cases and under the base. The two screw tabs on each side land on the motor case holes, exactly where the old power support sat; the box with the pads stays behind the motors, and the BNO085 ends up between the two hip-yaw motors.',
                       'Lay the two free hip-cable ends forward over the hip-yaw motors first, so the plate cannot trap them.',
                       'Nothing goes into the box yet. Do not fit the orange side shells either; they close over the neck motor later.'],
         checks=['The four tab holes line up with the base and the motor cases, and the notch in the top edge of the plate stands above the motor tops, on the centre line.',
                 'The BNO085 stands between the hip-yaw motors, socket up, and touches neither motor.'],
         warnings=['Later, with the robot built, the pack cannot come out past the shells: a pack swap needs both torso shells off first (chapter 6).'])

    step('torso-fasten', 'torso', 'Fasten the hip-yaw motors to the torso',
         camera=ctx.cam(TORSO + HIP_YAW, direction=(1.0, -1.1, -0.5), margin=1.3),
         prepare=[tap(4, 'M2 × 10'), tap(2, 'M2 × 8')],
         screwNotes={'M2 × 10 TAP': 'Per motor: one from below through the pack\'s lower tab and the base, one from above through the pack\'s upper tab.',
                     'M2 × 8 TAP': 'Per motor: one from below through the base only.'},
         instructions=['Per hip-yaw motor (ID10 left, ID5 right), three screws into the motor case:',
                       'From below: one M2 × 10 through the pack\'s lower tab and the base, and one M2 × 8 through the base alone.',
                       'From above: one M2 × 10 through the pack\'s upper tab.',
                       'The two shell-to-motor M2 × 10 screws come later, when the shells close.'],
         checks=['The base no longer moves on the motors and the pack plate is tight against both motor cases.'])

    step('leg-join', 'torso', 'Slide both legs back onto the hip-roll outputs',
         add=leg_rest, group={'label': 'Both legs below the hip-roll motors', 'approach': [45, 0, 0]},
         camera=ctx.cam(LEGS + TORSO, direction=FRONT, margin=1.1),
         prepare=[tap(8, 'M2 × 6')],
         screwNotes={'M2 × 6 TAP': 'Cup 1. Four per side, driven from the front through the hip bridge into the hip-roll horn.'},
         instructions=['Bring each leg to the robot from the front and slide its hip bridge back onto the hip-roll output, with the roll support ring in the bridge. This is the leg guide\'s step 19 in the other direction.',
                       'Drive the four M2 × 6 from cup 1 through the front of each hip bridge into the horn.'],
         checks=['Move each hip joint by hand through its range with torque off: nothing rubs and no servo cable goes tight.',
                 'All three cups are empty.'])

    step('hip-cable-yaw', 'torso', 'Plug the hip cables into ID5 and ID10', cables=HIP_CABLES,
         camera=ctx.cam(HIP_YAW + ['torso_base'], direction=(1.0, -0.35, 0.8), margin=1.3),
         instructions=[
             'Left: plug the free end into ID10 socket 14, the top socket nearer the centre line. The cable comes straight up from the slot along the inner side of ID10; keep it against the motor so the middle stays free for the IMU.',
             'Right: the cable comes up the same way on the right of centre, crosses the top of ID5 near its back edge and turns forward into ID5 socket 14, the outer top socket. Keep the inner socket 13 free: link R goes there later, in front of this cable.',
             'Turn each hip through its whole yaw range by hand. Leave enough slack under the base that the cable never pulls, about 15 to 20 mm.',
             'About 90 mm (right) and 105 mm (left) of each cable is still spare. Fold it into a flat S no more than 10 mm high on the outer half of the hip-yaw motor top, in front of the plugs. Keep it off the front outer corner, where a shell screw goes into the motor later, and away from the centre line, where a shell post comes down.',
         ],
         checks=['Both plugs are latched.',
                 'Each hip yaws end to end without the cable pulling at either plug or rubbing on the yaw link or the base slot.'])

    step('board', 'torso', 'Mount the OpenRB-150 in the pack',
         add=board, approach={'openrb_board': [-25, 0, 0]}, cables=['uart'],
         camera=ctx.cam(controller + pack, direction=REAR_LOW, margin=1.2),
         prepare=[tap(4, 'M2 × 6'), {'item': 'Phillips #0 driver with a shaft 5 mm or thinner', 'qty': 1, 'kind': 'tool'}],
         screwNotes={'M2 × 6 TAP': 'From the component side through a board corner hole into a pad on the pack plate: 1.6 mm of board, then 3.8 mm of pad and 0.6 mm of plate, with 0.8 mm of pilot spare past the tip.'},
         instructions=[
             'The board must already be flashed (chapter 2). In the pack its USB-C socket faces the slot in the pack floor. The OpenRB USB data cable plugs in from below through that slot and trails to the Mac: it is the wired control link and the route for reflashing, so the board stays in place to be flashed again.',
             'Hold the board upright with its components towards you (the rear), the terminal block up and the USB-C socket down. The side port that stays in use is on the window side of the pack, the robot\'s left (+Y), which is on your right as you face the back of the robot.',
             'Slide it straight in from the back, level, with its bottom edge just above the floor and centred between the two side walls (about 0.6 mm to spare on each side), until its four corner holes sit on the four round pads. Only the rear box frame (or, before chapter 5 ends, nothing) has to be off: the board goes in the same way when the torso shells are already on.',
             'Drive the four M2 × 6 from the component side through the corner holes into the pads. Start the two lower ones, then the two upper ones; the upper pair sits 3 mm from the power-jumper block, so use the #0 driver with the thin shaft there. Stop when each head touches the board.',
             'Lead the two UART wires from J12 sideways past the power jumper into the lane on the +Y side of the board centre and up to the top edge of the plate; they leave the pack later with the IMU wires.',
         ],
         checks=['The board stands square on its four pads with no gap at any corner.',
                 'The USB-C socket sits over the slot in the floor, and the two centre servo ports face you low on the board.',
                 'Nothing blocks the floor slot: the data cable plug goes into the socket from below.'],
         warnings=['To take the board out later (a swap), the shells stay on. Unplug the USB data cable first. Take the box lid off (the four M2 × 10 in the holes in its back, then pull it straight back), unscrew both XL4015 (the four M2 × 6 of the middle converter and the two M2 × 4 in the top converter\'s lower holes; its upper holes held two of the lid screws; the 5991\'s upper holes held the other two) and lift them out backwards, each wire lifting out of its side window, and let them hang on their wires; take the four frame screws out and lift the frame off backwards with the 5991 still in it, lifting the four wires out of the notch at the front edge of the box top first. Then unplug links R and L from the centre ports and link N from the side port, loosen the two J4 screws and pull out the 7 V pair, and lead its free ends out of the back of the pack. Remove the four M2 × 6 and slide the board straight out backwards. The UART pair stays soldered to J12 and moves with the board: slide it out only as far as that pair allows without pulling on the pads.'])

    # Power into the pack (2026-10-14, current_build.servo_rail_7v_20261014): the 7 V pair from XL4015 #1 OUT in the rear
    # converter box (layout F) climbs the outside of the box's +y wall, crosses the box top and drops through the notch at
    # the front edge of the box top (y 3.2..12.4) under the shell lip onto the frame\'s lip, then along the lip into the empty
    # channel behind the board, up it and over the board top into J4, one wire per screw (route pw-7v; no passage since
    # 2026-10-14). The head 5 V lead does not start at J4. Lane order from the back: L, R, then the UART
    # wires (routes.json).
    step('orb-power', 'torso', 'Connect the 7 V pair and plug in the three links',
         cables=['pw-7v', 'dxl-r5', 'dxl-l10', 'dxl-n12'], wiring=openrb_wiring(cut),
         camera=ctx.cam(controller + pack, direction=(-1.0, 0.3, 0.5), margin=1.3),
         prepare=[{'item': f'7 V pair: 22 AWG solid core, red + black, {cut["pw-7v"]}, 6 mm stripped at both ends', 'qty': 2, 'kind': 'cable'},
                  {'item': 'Small flat screwdriver, flush cutter, wire stripper', 'qty': 1, 'kind': 'tool'}],
         instructions=[
             'Done: links R and L in the two centre ports, link N in the left side port, and the 7 V pair under the J4 screws (red +, black −), one wire per screw. Its other end lies free over the top of the pack plate; it goes through the notch of the box frame later in this chapter and onto XL4015 #1 in chapter 10.',
             'Plug link R into the lower centre port and link L into the upper centre port, pushing forward from the back until each clicks. Both plugs lie low in the channel behind the board, pointing forward.',
             'Pass the plug of link N out through the window in the left (+Y) wall and plug it into the side port from outside. Lead N up the outside of the wall to the top of the plate.',
             'From each centre port, lead the link back and to the right (−Y) into the open bay at the bottom of the channel: R low along the back, L above it. Their spare length lies there.',
             'Bring each link back across under the lane entrance and up the lane between the board\'s component side and the channel, left (+Y) of the board centre, past the jumper cap. Order from the back: L, then R.',
             'Above the board, R crosses to the right (−Y) and L stays left. Both reach the top of the plate.',
             'The 7 V pair takes the short way: from the terminal block at the top of the board straight back over the top edge of the board into the empty channel behind it, where the DFR1202 used to sit, then up to the top edge of the plate on the left-hand (+Y) side, just left of the centre as you look from behind (red nearer the centre than black). Leave its free ends hanging over the top edge of the plate.',
             'Loosen the two terminal-block screws. Push the red wire under the screw printed + (marker 3) and the black wire under − (marker 4). Tighten and tug each wire: neither moves. Only these two wires go under the J4 screws; the head 5 V lead starts at XL4015 #2 in the rear converter box.',
             'Check the jumper cap: it sits on the two pins beside the VIN(DXL) print, as set in chapter 2. The 7 V rail (7.40 V) then reaches the servo ports.',
             'Tape the free ends of the pair (the converter end) apart from each other. They go up through the notch of the frame in "Fit the rear box frame" and onto XL4015 #1 OUT only in chapter 10, after its voltage is read back.',
         ],
         checks=['Red under +, black under −: one wire under each screw, none loose when tugged.',
                 'All three plugs clicked in. The right (−Y) side port is empty.',
                 'Nothing in the lane presses on the jumper cap.',
                 'The converter end of the pair is taped and not under any screw.'],
         warnings=['The 7 V pair goes to J4 only, never to a servo port or an A7Z pin. With JP1 on VIN(DXL) the OpenRB passes the 7 V straight to the servo ports.'],
         links=[bringup('s12', 'Detailed page: 7 V pair into OpenRB J4, the head 5 V lead on XL4015 #2', 'BRINGUP step 12'),
                here('box-frame', 'Guide: Fit the rear box frame with the four cover screws'),
                here('bench-test', 'Guide: Set the 5991 to 15 V and the two XL4015 to 7.40 V and 5.00 V'),
                here('wire-list', 'Soldering and wire list')])

    step('leg-links', 'torso', 'Plug the leg links into ID5 and ID10',
         cables=['dxl-r5', 'dxl-l10'],
         camera=ctx.cam(['motor5', 'motor10'] + pack, direction=TOP_REAR, margin=1.3),
         instructions=[
             'Links R and L come up the lane to the top of the plate. Pass both through the notch in the top edge of the plate in its upper row: R at the −Y end, then the UART pair, then a gap for the PI lead (it comes up from the rear converter box in "Fit the rear box frame"), then L at the +Y end; link N crosses below them in the middle of the notch.',
             'In front of the plate, lead R down to the top of ID5 and plug it into ID5 socket 13, the free socket facing up, in front of the hip cable. Lead L to ID10 socket 13 the same way.',
             'Leave a gentle loop at each motor so hip yaw can turn without pulling the plug.',
         ],
         checks=['Turn each hip by hand through its full yaw range: no tight wire, no rub on the base.',
                 'Both top sockets of ID5 and of ID10 now hold a plug: the controller link and the hip cable.'])

    step('imu-plug', 'torso', 'Plug the IMU cable', add=['imu_sh4_receiving'],
         approach={'imu_sh4_receiving': [0, 0, 10]}, cables=['imu'],
         camera=ctx.cam(IMU, direction=TOP_REAR, margin=2.2),
         prepare=[{'item': f'4397 cable extended to {cut["imu"]} mm with jumper wire (red, black, blue, yellow)', 'qty': 1, 'kind': 'cable',
                   'note': 'Four 300 mm female-to-female jumpers, one per colour.'},
                  {'item': 'Electrical tape', 'qty': 1, 'kind': 'other'},
                  {'item': 'Soldering iron, solder, wire stripper, flush cutter', 'qty': 1, 'kind': 'tool'}],
         instructions=[f'Done: the 4397 cable is {cut["imu"]} mm long from its small 4-pin plug to its four black sockets, with taped joints in the middle, and the small plug sits in the BNO085.',
                       'Cut the 4397 cable in the middle. Strip 5 mm on all eight cut ends.',
                       'Cut both plugs off each of the four jumpers.',
                       'On the half with the small 4-pin plug, join a jumper to each wire, colour to colour: twist, solder, tape three turns. Put the four joints 10 mm apart along the cable.',
                       f'Lay the cable straight. Hold the half with the sockets beside it so the sockets end {cut["imu"]} mm from the small plug. Cut each jumper 5 mm past the cut end of that half and strip 5 mm.',
                       'Join the socket half the same way, colour to colour, joints 10 mm apart.',
                       'Push the small plug into the socket at the top of the BNO085 from above, holding the plug, not the wires.',
                       'Lead the four wires straight up and back to the top-rear corner, where the UART pair comes over the top of the plate. The head 5 V lead (PI) joins them there later, through the same notch, from the rear converter box.',
                       'The four sockets go on the A7Z later (step "Plug the bundle onto the A7Z"), all on the inner row of the header: red on pin 1 (3.3 V), blue on pin 3 (SDA), yellow on pin 5 (SCL), black on pin 9 (GND). The A7Z reads the IMU on its hardware I2C bus TWI7 (pins 3 and 5). The wiring picture is on the A7Z wiring page.'],
         checks=['The plug is fully in and the cable leaves it upwards without a sharp bend.',
                 'Tug each joint: it holds, and no copper shows.'],
         links=[a7z('imu', 'Wiring picture: IMU to A7Z pins 1, 3, 5 and 9'),
                here('wire-list', 'Soldering and wire list (IMU extension)')])

    # Rear converter box, layout F (approved by Shawn 2026-10-14; print/back-plate/layout-F/layout_f.json and wires_F.json give
    # every coordinate). Frame: the V1.8 cover plate (outline, holes, lip) at x -47..-45, so the four cover screws hold it, and
    # behind it a box x -65.9..-47, |y| <= 32.05, z -36.02..43 with three tiers: XL4015 #1 (7 V) on top (PCB z 15.1..41.3),
    # #2 (5 V) in the middle (PCB z -13.5..12.7), both long axis along y with IN at +y and OUT at -y, components towards the
    # lid; the 5991 on its back face at x -50 in the 31.2 mm wide bottom tier, turned so its terminal faces -y (USB-C window
    # +y x -57.5..-49.0, z -31.16..-17.16; terminal window -y x -65.9..-53.1, z -28.06..-20.06). Four converter windows
    # x -65.9..-53.2 through the side walls (z 23.0..33.4 top, -5.6..4.8 middle), IN at -y and OUT at +y (layout F as
    # mirrored by the CAD agent to the real board's handedness). No passage (the old P1 was deleted 2026-10-14): a notch y 3.2..12.4 at
    # the front edge of the top wall (x -49.8..-47, through z 41.8..43) and in the top edge of the front plate (x -47..-45,
    # down to z 28.5, the lip top) lets the 7 V pair and the head 5 V lead drop from the box top, under the shell lip, onto the
    # frame lip into the pack (lanes y 4.4 7V red, 6.5 7V black, 8.6 Pi red, 10.7 Pi black; back-plate/layout-F-outside-wires-20261014).
    # Every wire leaves its terminal sideways, goes straight out of its window and stays outside the box (centreline bend
    # radius 3): 15 V feed and link window to window outside the -y wall; 7 V and Pi lead up the outside of the +y wall in
    # four columns, over the top edge, across the box top at z 45 and down the notch. Order: frame on the four cover
    # screws while empty (the top board covers the upper two) with the two pairs fed up the notch, 5991, middle board,
    # top board, the two pairs over the box top to their OUT windows, lid. Screw lengths from the ray casts
    # recorded in fasteners.json (C-rear_frame, C-pd5991, C-xl4015, C-rear_lid). Cap retention (2026-10-15, Shawn: screws, no
    # tongues): four hidden M2 x 10, two through the top converter's upper corner holes (C-rear_lid-03/04) and two through
    # the 5991 upper holes (C-rear_lid-01 +y, C-rear_lid-02 -y); the cap pushes straight on.
    loop_text = ('How a wire passes a window: the ends of each board sit against the side walls, so inside the box there is no room to turn a stiff wire from a terminal towards the back. '
                 'Each wire therefore leaves its terminal sideways, goes straight out through the window in the side wall and stays outside the box: it turns there (bend each corner round the shank of a 4 mm drill bit or screwdriver so it stays round, centreline radius 3 mm) '
                 'and runs along the outside of the wall, about 2 mm off it, to its next window or over the top edge of the box. No wire comes back inside: nothing lies between the components and the lid. '
                 'The windows are open at the back edge of the frame, so each wire slides in from behind; the rear part of each window is cut in the side wall of the cap lid, which goes on last.')
    box_cam = ctx.cam(BOX_FRAME + BOX_BOARDS if ctx.has('rear_frame') else pack, direction=(-1.0, -0.3, 0.25), margin=1.25)
    step('box-frame', 'torso', 'Fit the rear box frame with the four cover screws', add=ctx.keys(*BOX_FRAME),
         approach={'rear_frame': [-30, 0, 0]}, cables=['pw-7v', 'pi-lead'],
         camera=ctx.cam(BOX_FRAME + pack, direction=REAR, margin=1.3),
         prepare=[{'item': 'Rear converter box frame (layout F print, orange)', 'qty': 1, 'kind': 'printed'},
                  {'item': f'Head 5 V lead (PI): the red and the black jumper chain from the wire list ({cut["pi-lead"]}), chain joints taped; at the converter end the male pin is cut off and 10 mm stripped, twisted and folded back', 'qty': 2, 'kind': 'cable'},
                  tap(4, 'M2 × 6')],
         screwNotes={'M2 × 6 TAP': 'Forward through a corner hole of the frame plate into the pilot in a pack post: 2 mm of plate, 4 mm of thread, 0.8 mm of pilot spare past the tip. The same four screws as the V1.8 pack cover. The two lower screws sit just outside the narrow bottom tier: use a driver no thicker than 3 mm there.'},
         instructions=[
             'Done: the frame sits on the back of the pack in place of the old pack cover, held by four M2 × 6, and the box behind it is empty. The 7 V pair and the head 5 V lead rise out of the pack through the notch in the top edge of the front plate, up the narrow cavity between the plate and the box, and out through the notch at the front edge of the box top; their taped ends lie on the box top.',
             'If your pack already wears the V1.8 cover, take it off (four M2 × 6) and keep the screws: they hold the frame. The cover is retired.',
             'Lay the head 5 V lead: drop its two female ends into the notch in the top edge of the pack plate, in the upper row between the UART pair and link L, and leave them hanging forward over the torso (they get their flags in chapter 8). Lead the rest back behind the notch, over the top of the board and up to the top edge of the plate, just left (+Y) of the centre and outboard of the 7 V pair (from the centre outward: 7 V red, 7 V black, PI red, PI black).',
             'Look into the pack once more: the lane dressed flat, nothing across the USB-C slot in the floor (the OpenRB data cable goes through it), and the two free pairs, the 7 V pair from J4 and the head 5 V lead, hanging over the top edge of the plate just left (+Y) of the centre with their ends taped.',
             'Hold the frame with its open box towards you and the lip at the top of the plate pointing forward. Find the wire notch: a 9 mm wide cut in the top edge of the front plate just left (+Y) of the centre as you look at the box from behind, and above it the matching notch through the front edge of the box top wall. As the frame comes on, the four wires hanging over the plate top drop into the plate notch, side by side in their order (7 V red nearest the centre, then 7 V black, PI red, PI black). Lead them up through the narrow cavity between the plate and the box and out through the top-wall notch onto the box top; their ends lie there for now.',
             'Slide the frame forward until the plate sits on the ends of both pack posts and the lip lies over the top of the channel. Nothing may be pinched under the lip or the plate.',
             'Drive the four M2 × 6 from the back through the plate corners into the posts now, while the box is empty: the top converter covers the upper two later. The lower two sit just outside the narrow bottom tier. Start all four, then tighten evenly until the heads touch.',
         ],
         checks=['The plate sits flat on the ends of both posts all round.',
                 'The four wires sit side by side in the plate notch and come out of the top-wall notch onto the box top with their ends taped, and each slides a little when pulled: nothing is pinched.',
                 'The head 5 V lead\'s two female ends hang out of the pack notch in front of the plate.'],
         warnings=['The box must be empty when the frame goes on: the top converter sits over its two upper screws.'],
         links=[here('wire-list', 'Soldering and wire list')])

    step('box-5991', 'torso', 'Screw the 5991 into the bottom tier and loop its 15 V wires', add=ctx.keys('pd5991'),
         approach={'pd5991': [-25, 0, 0]}, cables=['pw-15v'], camera=box_cam,
         prepare=[{'item': 'The 5991, XL4015 #2 and XL4015 #1 chained by the 15 V feed and link from chapter 3', 'qty': 1, 'kind': 'electronic'},
                  {'item': '4 mm drill bit or screwdriver shank, to bend the wire loops round', 'qty': 1, 'kind': 'tool'},
                  tap(2, 'M2 × 6')],
         screwNotes={'M2 × 6 TAP': 'From the component side through a 5991 lower corner hole into a frame boss: 1.6 mm of board, 4.4 mm of thread in the boss, 0.3 mm of pilot spare past the tip. Both upper holes stay empty: the two low lid screws go through them.'},
         instructions=[
             'Done: the 5991 lies on its four bosses in the narrow bottom tier, held by two screws in its lower corners, components towards you, its USB-C socket at the tall window in the left-hand (+Y) wall and its screw terminal at the window in the right-hand (−Y) wall. The 15 V feed leaves the terminal through that window and stays outside: it runs under the step where the box widens and up the outside of the right-hand wall to the middle converter\'s IN window. The two converters hang behind the box on their wires until the next step.',
             'Check the DIP switch once more: only slider 3 (15V) is ON. The switch faces the lid, so you can reach it whenever the lid is off.',
             'Hold the 5991 with its components towards you, the USB-C socket to the left and the screw terminal to the right. Slide it in from the open back into the bottom tier and set its back on the four bosses; the socket lines up with the tall window low in the left-hand wall.',
             'Drive two M2 × 6 through its lower corner holes from the component side into the bosses: lower left and lower right. Stop when each head touches the board. Leave both upper holes empty, the left one beside the USB-C socket and the right one beside the screw terminal: the two low lid screws go through them in "Close the box with its cap lid".',
             loop_text,
             'Lead the 15 V feed at the 5991: both wires leave the terminal to the right, straight out through the bottom-tier window. In this position the + screw is the lower one: red leaves below black. Check the ⊕ printed beside the screw.',
             'Outside the wall, turn the pair up: it runs under the step where the box widens, then up the outside of the right-hand wall to the height of the middle converter\'s IN window. It goes in there in the next step. Keep red on the + screw at both ends; the pair crosses over itself once on the way. Nothing lies inside the box over the 5991 or across the DIP switch.',
         ],
         checks=['A USB-C plug pushed in through the left-hand window goes straight into the socket.',
                 'Every wire is still under its terminal screw: tug each one.',
                 'The 5991 sits flat on all four bosses and does not move, and both its upper holes are still empty; the feed outside the right-hand wall stands about 2 mm off the wall and is not kinked.'])

    step('box-xl4015', 'torso', 'Screw in the 5 V converter, then the 7 V converter above it, IN on the right',
         add=ctx.keys('xl4015_mid', 'xl4015_top'),
         approach={'xl4015_mid': [-25, 0, 0], 'xl4015_top': [-25, 0, 0]}, cables=['pw-15v', 'pw-15v-link'], camera=box_cam,
         prepare=[tap(4, 'M2 × 6'), tap(2, 'M2 × 4')],
         screwNotes={'M2 × 6 TAP': 'The four screws of the middle converter. From the component side through a corner hole into a frame boss: 1.55 mm of board, then the thread. Its lower pair goes into 5 mm bosses with a blind pilot; its upper pair goes into 4.2 mm bosses, the tip just showing at the front end. The top converter\'s two upper holes stay empty here: the lid\'s two top screws go through them.',
                     'M2 × 4 TAP': 'The two lower holes of the top converter only. Their bosses are 3.2 mm long because the shell sits just in front of them; an M2 × 4 ends inside the boss, where an M2 × 6 would poke out towards the shell.'},

         instructions=[
             'Done: two converters lie flat in the box, one above the other, components towards you, each with its IN block at the right (−Y) end and its OUT block at the left: #2 (5 V) in the middle tier on four screws, #1 (7 V) in the top tier on its two lower screws, its two upper corner holes still empty for the lid screws. The 15 V feed and link pass straight through the right-hand windows and run up the outside of that wall, and the 7 V pair and the head 5 V lead stand in the narrow cavity between the front plate and the boards, rising from the plate notch to the top-wall notch.',
             'Before each board goes in, read the printing beside its terminal blocks: IN+ and IN− at one end, OUT+ and OUT− at the other. The four holes are symmetric, so a board also fits with OUT on the right; only IN on the right is correct. With IN on the right, the two blue trimmers sit at the bottom edge and the + screw of each block is the lower one. The 3D model has no printing on it, so it cannot show you which end is which.',
             'Middle converter (flag "#2 5 V"): hold it with its components towards you and its IN block to the right. Its IN screws already hold the 15 V feed and the 15 V link. As the board goes in, guide both pairs into the middle window of the right-hand wall: from the IN block they leave to the right, straight out through the window, and turn outside the wall: the feed down to the 5991 window, the link up towards the top converter\'s IN window.',
             'Slide the board in from the open back, set it on its four bosses and drive four M2 × 6 from the component side. Stop when each head touches the board.',
             'The 7 V pair and the head 5 V lead stay where the frame step left them: rising in the cavity in front of the boards and out of the top-wall notch. Neither board may pinch them: the cavity is 2.8 mm deep in front of the top board\'s pin ends.',
             'Top converter (flag "#1 7 V"): hold it the same way, IN block to the right. Its IN screws hold the other end of the 15 V link. Lead the link straight in through the top window of the right-hand wall, then slide the board in from the open back and set it on its four bosses without pinching the four wires rising in front of its pin ends. Drive two M2 × 4 into the two lower holes, from the component side, and leave the two upper holes empty: in the last step of this chapter the lid\'s two top M2 × 10 go through them into the same bosses. Use the short ones here: an M2 × 6 in a lower hole would poke out of its boss towards the shell.',
             'The two blue trimmers of each converter now face the open back. If a voltage needs touching later, do it with the lid off.',
         ],
         checks=['Both IN blocks are at the right end; the flags read #1 on top and #2 in the middle.',
                 'The feed and the link run outside the right-hand wall about 2 mm off it, window to window, are not kinked, and no bare copper shows outside a terminal.',
                 'The 7 V pair and the head 5 V lead slide a little in the notch and the cavity in front of the boards: nothing is pinched.'],
         warnings=['With OUT on the right, the 15 V wires would go to the OUT block and back-feed the converter. Check the printing before you drive the screws.'])

    step('box-out', 'torso', 'Lead the 7 V pair and the head 5 V lead to their converters\' OUT blocks', cables=['pw-7v', 'pi-lead'], camera=box_cam,
         prepare=[{'item': 'Electrical tape', 'qty': 1, 'kind': 'other'},
                  {'item': '4 mm drill bit or screwdriver shank, to bend the wire loops round', 'qty': 1, 'kind': 'tool'}],
         instructions=[
             'Done: the 7 V pair runs from the top-wall notch over the box top, down the outside of the left-hand wall and in through the top window to the OUT block of the top converter (#1); the head 5 V lead the same way into the middle window to the OUT block of the middle converter (#2). Their bare ends are taped and lie at the OUT block, not under any screw until chapter 10.',
             '7 V pair: from the notch at the front edge of the box top lead it back across the top of the box (it lies on the top wall, about 1 mm above it) to the left-hand (+Y) edge, over that edge and straight down the outside of the left-hand wall, red and black side by side, to the top window; in through the window to the OUT block. The pair runs in the rear half of the wall, behind the window\'s front edge.',
             'Head 5 V lead: from the notch, outboard of the 7 V pair, back across the box top, over the left-hand edge and down the outside of the wall in front of the 7 V pair, past the top window, to the middle window; in through it to the OUT block of the middle converter. Keep the two pairs side by side and not crossing; nothing goes inside the box over the components.',
             'Leave each bare end pointing at its OUT screw with the red end beside OUT+ and the black beside OUT−, and tape the two ends of each pair apart from each other. They go under the OUT screws only in chapter 10, after each converter\'s voltage is read back.',
         ],
         checks=['Four wires lie side by side in the notch, none crossing; each pair runs outside the box on its top and left-hand wall and enters only at its OUT window; nothing lies inside the box over the components.',
                 'No bare copper touches a screw, a terminal or the other pair.'],
         warnings=['Never put the head 5 V lead on #1: #1 is the 7.4 V servo rail and the A7Z takes 5 V only. #1 is the top converter.'])

    step('box-lid', 'torso', 'Close the box with its cap lid', add=ctx.keys(*BOX_LID),
         approach={'rear_lid': [-15, 0, 0]},
         camera=ctx.cam(BOX_FRAME + BOX_LID, direction=REAR, margin=1.3),
         prepare=[{'item': 'Rear converter box lid (V1.19 cap print with 3 mm screw floors, orange)', 'qty': 1, 'kind': 'printed'}, tap(4, 'M2 × 10')],
         screwNotes={'M2 × 10 TAP': 'Forward through the four holes in the back of the cap. Each head sits on the floor of a column inside the cap. Each column floor under a head is 3.0 mm thick. The two top screws cross a 1.25 mm gap and the top converter\'s upper corner holes into those frame bosses (1.55 mm of board, about 4.3 mm of thread). The two low ones cross a 1.5 mm gap and the 5991\'s two upper corner holes into those bosses (1.6 mm of board, 3.9 mm of thread). Tighten until the cap sits firmly on the rim and stop: the heads bear on printed floors. Each hole is 4.4 mm wide and about 10 mm deep: use a driver no thicker than 4 mm.'},
         instructions=[
             'Done: the cap lid closes the back of the box with nothing sticking out. Four M2 × 10, hidden inside the cap, hold it: two at the top corners through the top converter\'s upper corner holes into the frame, and two low in the narrow bottom part through the 5991\'s two upper corners into the frame.',
             'Look into the box once more: no wire lies inside the box over the components, the taped OUT ends lie at their OUT blocks, and nothing presses on a trimmer. The cap carries the side windows for the terminals, so each wire passes its window once the cap is on, and the four wires on the box top cross outside the cap.',
             'Inside the cap find its four round columns: two at the top corners and two low in the narrow part. Each lines up with an empty corner hole: the top converter\'s two upper holes and the 5991\'s two upper holes.',
             'Push the cap straight forward onto the box until its edge meets the frame rim all round. Guide each wire into its window in the cap side wall as the cap comes on, and keep the four wires on the box top out of the cap\'s way.',
             'Drop an M2 × 10 into each of the four round holes in the back of the cap and drive it forward. Each passes the floor of its column and a board corner hole and bites into the frame boss behind it. Start all four by a few turns before tightening any; stop when the heads pull the cap firmly against the frame rim. The heads stay hidden inside the cap.',
             'To take the cap off (chapter 10 does this for the voltage readback), remove the four M2 × 10 and pull it straight back. The top converter then hangs on its two lower screws: do not pull on its wires.',
             'Photo to add for this step: the inside of the cap with markers 1 to 4 on the four columns, and the box with markers 5 and 6 on the top converter\'s empty upper holes and 7 and 8 on the 5991\'s empty upper holes.',
         ],
         checks=['The cap edge meets the frame rim all round, all three screw heads sit inside the cap, and the cap does not move when pulled backwards.',
                 'No wire is pinched under the cap edge or in a window.'])

    # ------------------------------------------------------------------ 5. Neck
    bench_neck: list[str] = []

    def neck_bench(sid, title, add, show=None, **kw):
        # On the bench: no torso around it, and a detached subassembly shows only its own parts.
        nonlocal bench_neck
        step(sid, 'neck', title, add=add, show=list(bench_neck) if show is None else list(show), context=[], bench=True, **kw)
        bench_neck = bench_neck + [a for a in add if a not in bench_neck]

    neck_bench('neck-lower', 'Seat the two neck motors', NECK_LOWER,
               approach={'idler11': [0, -28, 0], 'idler12': [0, -28, 0], 'idler_cap11': [0, -28, 0], 'idler_cap12': [0, -28, 0]},
               camera=ctx.cam(NECK_LOWER, direction=(0.8, -1.2, 0.5), margin=1.4),
               prepare=[{'item': 'Servos ID11 and ID12', 'qty': 2, 'kind': 'electronic'},
                        {'item': 'Neck links A and B (10/1 print)', 'qty': 2, 'kind': 'printed'},
                        {'item': 'Rear idler + idler cap (10/1 print)', 'qty': 2, 'kind': 'printed'}],
               instructions=['Seat ID12 (bottom) and ID11 (top) between the two orange neck links.',
                             'Fit the two printed rear idlers and their caps.'])
    neck_bench('neck-lower-fasten', 'Fasten the neck cases and rear centres', [],
               camera=ctx.cam(NECK_LOWER, direction=(0.8, -1.2, 0.5), margin=1.4),
               prepare=[tap(4, 'M2 × 8'), tap(4, 'M2 × 10'), tap(2, 'M2.6 × 6')],
               screwNotes={'M2 × 8 TAP': 'Through neck link B (the −Y side) into the ID11 and ID12 case corners, two per motor.',
                           'M2 × 10 TAP': 'Through neck link A (the +Y side) into the case corners, two per motor.',
                           'M2.6 × 6 TAP': 'ROBOTIS rounded-head screw, no washer, through each idler cap into the motor rear boss.'},
               instructions=['Case corners, four per motor: two M2 × 8 through link B on the −Y side and two M2 × 10 through link A on the +Y side. The thicker link takes the longer screw.',
                             'Rear centres: one M2.6 × 6 through each idler cap and idler into the motor rear boss, no washer.',
                             'Finish both rear centres now. Once the right torso shell is on, it blocks the ID12 rear-centre screw.'])
    neck_bench('neck-cable-12-11', 'Connect ID12 to ID11 (100 mm)', [], cables=['dxl-12-11'],
               camera=ctx.cam(['motor11', 'motor12'], direction=(0.6, -1.3, 0.3), margin=1.6),
               prepare=[{'item': 'X3P 100 mm kit cable', 'qty': 1, 'kind': 'cable'}],
               instructions=['Plug one end into ID12 socket 13 and the other into ID11 socket 14 (both on the −Y face).',
                             'Bow the cable outward behind the links so it bends, not pulls, when the neck pitches.'],
               checks=['Pitch the links by hand both ways: the cable never goes tight.'])
    neck_bench('neck-pitch', 'Prepare the yaw motor on the pitch bracket', PITCH_GROUP, show=[],
               approach={'neck_pitch_ring': [0, 0, 28], 'motor13': [0, 0, 28]},
               camera=ctx.cam(PITCH_GROUP, direction=FRONT, margin=1.6),
               prepare=[{'item': 'Neck pitch bracket with 1 mm seats (new print)', 'qty': 1, 'kind': 'printed'},
                        {'item': '4.9 mm neck pitch ring (V1.8 Black plate; replaces the 4 mm ring from the 10/1 batch)', 'qty': 1, 'kind': 'printed'},
                        {'item': '1 mm and 2 mm neck ring shims (V1.8 Black plate, optional)', 'qty': 2, 'kind': 'printed'},
                        {'item': 'Servo ID13', 'qty': 1, 'kind': 'electronic'}, tap(4, 'M2 × 6')],
               screwNotes={'M2 × 6 TAP': 'Up through the bracket\'s 1 mm integral seats into the ID13 output horn.'},
               instructions=['Drop the 4.9 mm ring over the round boss on top of the bracket. It is the bearing between the bracket and the ID13 case: it carries the head\'s tipping load so the servo shaft does not. The old 4 mm ring left a 0.9 mm gap under the case and did nothing.',
                             'Attach ID13 to the detached black pitch bracket, its output horn going down through the ring. Keep the bracket off ID11 for now: ID11 would block the yaw output screws.',
                             'From the underside of the bracket, drive four M2 × 6 up through the bracket into the ID13 output horn. The 1 mm seats are printed into the new bracket; use no separate washers.'],
               checks=['The ring is pinched between the bracket and the ID13 case: it does not rattle up and down, and ID13 still turns by hand.',
                       'If the ring still rattles, take ID13 off again and slip the 1 mm shim, the 2 mm shim or both over the boss under the ring (same bore and size as the ring, on the round shoulder). Use the thickest stack with which ID13 still turns by hand.'])
    neck_bench('neck-upper-join', 'Join the upper neck to ID11 and connect 11 → 13', PITCH_GROUP, show=NECK_LOWER,
               group={'label': 'Upper neck: pitch bracket and ID13', 'approach': [0, 0, 40]}, cables=['dxl-11-13'],
               camera=ctx.cam(NECK_LOWER + PITCH_GROUP, direction=(0.8, -1.2, 0.4), margin=1.2),
               prepare=[tap(7, 'M2 × 6'), {'item': 'X3P 180 mm kit cable', 'qty': 1, 'kind': 'cable'}],
               screwNotes={'M2 × 6 TAP': 'Through the pitch bracket: four into the ID11 output horn (+Y side), three into the printed rear idler (−Y side). Stop at snug: the horn holes are only 3 mm deep. The fourth idler-side hole, the rear one level with the pitch axis, takes an M2 × 8 through the bracket wire clip in the next step.'},
               instructions=['Plug one end of the 180 mm cable into ID13 socket 14 first, while it is easy to reach.',
                             'Align both ID11 output and idler seats with the pitch bracket. Drive four M2 × 6 through the bracket into the ID11 output horn on the +Y side. Stop at snug: the screw tip just reaches the bottom of the 3 mm horn hole.',
                             'On the −Y side, drive three M2 × 6 into the printed rear idler: the front one and the upper and lower ones. Leave the rear hole, level with the pitch axis, empty: the bracket wire clip goes under that screw in the next step.',
                             'Plug the other end into ID11 socket 13. Lead the cable down the −Y side of the bracket with a loop at the pitch axis.'],
               checks=['Head pitch through its range: no tight cable, no plug lever.',
                       'The rear bracket hole on the −Y side, level with the pitch axis, is still empty.'])
    neck_bench('neck-bracket-clip', 'Fit the bracket wire clip under its screw', ctx.keys('clip_bracket'),
               approach={'clip_bracket': [0, -14, 0]},
               camera=ctx.cam(['clip_bracket', 'neck_pitch', 'motor11'], direction=(0.8, -1.2, 0.3), margin=1.4),
               prepare=[{'item': 'Bracket wire clip (V1.9 print, orange)', 'qty': 1, 'kind': 'printed'}, tap(1, 'M2 × 8')],
               screwNotes={'M2 × 8 TAP': 'Through the clip tab and the pitch bracket into the printed rear idler, on the head-pitch axis. 2 mm longer than the other idler screws because of the 2 mm tab; the thread bite in the idler (2.7 mm) and the tip position are the same.'},
               instructions=['Hold the clip against the −Y face of the pitch bracket with its tab over the empty rear hole and its square channel standing up and down beside the bracket, the slot facing away from the bracket.',
                             'Drive one M2 × 8 through the tab and the bracket into the idler. Stop at snug, as for the other idler screws.',
                             'The clip turns with the bracket, so the bundle that later lies in its channel pitches with the head. Nothing else holds the clip.'],
               checks=['The tab lies flat under the screw head and the clip does not turn by hand.',
                       'The channel slot is open from end to end; a 2.5 mm drill shank drops into it.'],
               warnings=['The clip stands in front of the ID11 rear-centre screw (the M2.6 × 6 through the idler cap). To re-drive that screw later, take the bundle out of the clip first: the clip channel blocks a straight driver.'])

    step('neck-lower-in', 'neck', 'Lower the neck into the open torso',
         add=NECK_LOWER + PITCH_GROUP, group={'label': 'Neck built on the bench in this chapter', 'approach': [0, 0, 60]},
         cables=['dxl-n12'],
         camera=ctx.cam(TORSO + NECK_LOWER, direction=(0.9, -1.2, 0.6), margin=1.2),
         instructions=['Support the neck and lower ID12 onto the open base, both orange shells still off.',
                       'Plug link N into ID12 socket 14 now; the shells will cover this socket.',
                       'Feed the neck motor leads through their exits. No plug may sit behind a shaft seat.'],
         checks=['Both ID12 shaft centres line up with their seats.', 'Link N is latched and has a small loop.'])

    step('shells', 'neck', 'Close the two torso shells, fit the torso wire clip and screw each shell to the pack',
         add=SHELLS + ctx.keys('clip_torso'), approach={'shell_left': [0, 40, 0], 'shell_right': [0, -40, 0], 'clip_torso': [0, -14, 0]},
         camera=ctx.cam(TORSO + SHELLS + ['motor12'], direction=(1.0, -1.1, 0.75), margin=1.2),
         prepare=[{'item': 'Left and right torso shells (V2.0 print, white, from the V1.17 White plate)', 'qty': 2, 'kind': 'printed'},
                  {'item': 'Torso wire clip (V1.9 print, orange)', 'qty': 1, 'kind': 'printed'},
                  tap(7, 'M2 × 4'), tap(2, 'M2 × 6'), tap(1, 'M2 × 8'), tap(2, 'M2 × 10'),
                  {'item': '1.6 mm twist drill in a pin vise, and a strip of tape', 'qty': 1, 'kind': 'tool', 'note': 'For the two pilot holes in the pack shoulder bars.'}],
         screwNotes={'M2 × 4 TAP': 'Three through the right shell into the ID12 rear idler (the front, upper and lower holes) and four through the left shell into the ID12 output horn. Each sits in a 4.4 mm counterbore, so its head ends 0.5 mm below the shell surface; the thread bite is 1.8 mm in the idler and 2.3 mm in the horn.',
                     'M2 × 6 TAP': 'One per shell, straight down through the round counterbore in the shell roof at the back (x −21.5, 20 mm either side of the centre line) into the shoulder bar of the V1.9 rear pack, in a pilot you drill through the shell hole: 4.0 to 4.1 mm of thread in the bar.',
                     'M2 × 8 TAP': 'The rear hole of the right shell, level with the ID12 axis: through the torso wire clip tab and the shell into the ID12 rear idler. This hole has no counterbore because the clip tab sits under the head; the thread bite (1.8 mm) is the same.',
                     'M2 × 10 TAP': 'One per side, down through the shell into the hip-yaw motor case (ID10 left, ID5 right).'},
         instructions=['Bring each shell in from its side over the ID12 output or idler seat and the yaw-case seat. Never force the neck between two fixed shells.',
                       'Right shell first: drive three M2 × 4 into the ID12 rear idler, the front hole, the upper hole and the lower hole. Leave the rear hole, level with the ID12 axis, empty for now. The upper screw must go in before the clip: the clip covers its head.',
                       'Hold the torso wire clip against the outer face of the right shell with its tab over the empty rear hole and its square channel running front to back just above the tab, slot facing outwards. Drive one M2 × 8 through the tab and the shell into the idler. Stop when the head touches the tab.',
                       'Left shell: drive its four M2 × 4 into the ID12 output horn.',
                       'Then one M2 × 10 per side, down through the shell into the hip-yaw motor case. On the right side the idler screws pull the shell in so its hole lines up.',
                       'Link N runs up the outside of the pack\'s +Y wall and the left shell closes over it above the pack. Make sure it lies flat in the gap and is not pinched under the shell\'s lower edge.',
                       'Pack screws, one per shell. Find the round counterbore in the top of each shell near the back, above the pack. Wrap a tape flag round the 1.6 mm drill 7.0 mm from its tip. Put the drill through the hole in the counterbore floor, straight down, and drill into the pack\'s shoulder bar until the flag touches the counterbore floor. Pull the drill out and blow out the chips.',
                       'Drive one M2 × 6 into each drilled hole until its head touches the counterbore floor, then stop. The shell roof stands 0.4 to 0.5 mm above the bar; turning further bends the roof down onto it.',
                       'Bring the PI lead, the IMU lead and the UART pair out at the top-rear corner, behind the shells.',
                       'Where the shell top meets the box, the four power wires (7 V pair and head 5 V lead) lie in the notch of the box front plate, side by side, under the rear lip of the shell roof. As each shell comes down, make sure its lip passes over the wires and does not pinch them against the plate: each wire still slides a little when pulled from the box top.'],
         checks=['Neck pitch moves freely by hand.', 'No wire is trapped in a shell seam.', 'The four power wires in the box notch slide a little under the shell lip: none is pinched.',
                 'Each pack screw head sits in its counterbore, and the two shells no longer spring apart at the back when you squeeze them.',
                 'The horn screw heads sit below the shell surface in their counterbores.',
                 'The torso clip tab lies flat under its screw head and the clip channel is open from end to end.'],
         warnings=['The clip covers the head of the upper idler screw and stands in front of the ID12 rear-centre screw (the M2.6 × 6 through the idler cap). To re-drive either one later, take the bundle out of the clip and the clip off first.',
                   'To re-drive a pack screw on the finished robot, use a driver shorter than 57 mm: the lower head shell is 57.8 mm above each screw head.',
                   'A pack swap on the built robot needs both shells off: the right shell (the clip and its M2 × 8, three M2 × 4, the M2 × 10 and its pack screw), the left shell (four M2 × 4, the M2 × 10 and its pack screw), then the pack comes out backwards. The OpenRB-150 alone does not need this: with only the rear box frame off it slides out backwards past the shells (step \'Mount the OpenRB-150 in the pack\', note).'])

    # ------------------------------------------------------------------ 6. Head mechanics
    # Order: the shell cannot pass a jaw already on the head (interference-audit/whatif.py), so the jaw goes into the
    # loose shell on the bench. The shell floor opening (x 10.1..40.1, y -29..29) rings the neck, and neither the torso
    # below nor the fork with ID14 above passes through it, so the shell can only reach the neck before the fork is on
    # ID13: the fork with ID14 and its rings drops into the shell on the bench, the whole head is lowered onto ID13 and
    # screwed down, then the support and ID15 drop in. steps_audit.py sweeps each approach back to free space.
    # The one-piece jaw enters the shell only with its arms sprung apart, exactly as against the upstream lower shell
    # (scratch study jaw-vs-shells.json): rising from below, the -Y arm must clear the shell walls by 4.6 mm and the
    # +Y arm by 1.7 mm; the centre of the jaw never touches the shell. Pressed with equal thumb force on a loosely held
    # jaw, the arms bend about 4.0 mm (-Y) and 3.0 mm (+Y) and the jaw slides about 1.0 mm towards -Y, so in the shell
    # frame the arms clear by 5.0 and 2.0 mm (open-issues OI-06: layer stress about 12 to 14 MPa, against 15 to 18 MPa
    # when the -Y arm alone is bent 5 mm).
    JAW_SET = ['mouth_sliding_ring', 'jaw_frame']
    SUPPORT = ['jaw_support', 'motor15']

    def jaw_pose(deg, frm=None):
        # The jaw turns about the sliding-ring axis (+Y through x 26.1, z 118.62); a positive angle opens the mouth.
        p = {'parts': JAW_SET, 'pivot': [26.1, 0.0, 118.62], 'axis': [0, 1, 0], 'deg': deg}
        if frm is not None:
            p['from'] = frm
        return p

    step('jaw-support-bench', 'head', 'Seat ID15 in the jaw support and plug its cable', add=SUPPORT, show=[], context=[], bench=True,
         approach={'motor15': [0, 30, 0]},
         camera=ctx.cam(SUPPORT, direction=(0.6, 1.2, 0.8), margin=1.5),
         prepare=[{'item': 'Jaw support (new print)', 'qty': 1, 'kind': 'printed'},
                  {'item': 'Servo ID15', 'qty': 1, 'kind': 'electronic'},
                  {'item': 'X3P 180 mm kit cable', 'qty': 1, 'kind': 'cable'}],
         instructions=['Slide ID15 into the jaw support from the +Y side, output horn outwards. ID15 has no screws of its own: the support and the lower shell clamp it once the support is screwed down.',
                       'Plug one end of the 180 mm cable into ID15 socket 13 now, while the socket is in view. Leave the other end free.'],
         checks=['ID15 sits flat in the support pocket.'])

    step('head-shell', 'head', 'Check the lower head shell', add=['head_bottom'], show=[], context=[], bench=True,
         camera=ctx.cam(['head_bottom'], direction=(0.8, -0.8, 1.0), margin=1.3),
         prepare=[{'item': 'Lower head shell with the upper lip (new print, yellow)', 'qty': 1, 'kind': 'printed'}],
         instructions=['Clean any stringing out of the four screw bosses for the jaw support and the three closure tabs (two at the front corners, one at the rear).',
                       'Find the local cut-out for the ID14 plug. ID14 drops into the shell from above with the fork, so nothing may catch there.',
                       'Break the support away from under the upper lip at the front, and push a 5 mm drill bit by hand through the two holes in the lip under the front closure tabs: the driver passes through them when the head is screwed shut.'])

    step('jaw-bench', 'head', 'Spring the jaw into the lower shell from below', add=JAW_SET, show=['head_bottom'], context=[], bench=True,
         group={'label': 'Jaw frame with the lower lip and the sliding ring', 'approach': [0, 0, -30]},
         pose=jaw_pose(15),
         flex={'parts': ['jaw_frame'], 'riders': {'mouth_sliding_ring': -1}, 'ramp': [22, 30], 'spread': [4.0, 3.0], 'shift': -1.0, 'window': [0.2, 0.975]},
         camera=ctx.cam(['head_bottom'] + JAW_SET, direction=(0.9, -1.0, -0.8), margin=1.3),
         prepare=[{'item': 'Mouth sliding ring (new print)', 'qty': 1, 'kind': 'printed'},
                  {'item': 'Jaw frame with the lower lip (new print, yellow)', 'qty': 1, 'kind': 'printed'}],
         instructions=['Break the low support away from under the two back corners of the lower lip. The top of the lip, which grips, prints without support.',
                       'Push the sliding ring onto the boss on the inside of the −Y jaw arm, wide flange towards the arm.',
                       'Hold the shell in one hand. Hold the jaw with its mouth open about 15° (the lower lip a finger-width below the upper lip) and bring it up into the shell from below. Its two arms pass outside the shell side walls.',
                       'Hold the jaw loosely by its front lip so it can slide sideways. As the arms pass the walls, press both arms outwards at the same time with equal thumb pressure. The −Y arm (with the ring) opens about 4 mm and the +Y arm about 3 mm, and the jaw slides about 1 mm towards −Y by itself. Never hold one arm still while you bend the other one far. The middle of the jaw never touches the shell. When the ring lines up with its seat, let go: both arms spring back and the ring slides into the seat.',
                       'Only now close the mouth. Kept open until the arms are back, the lower lip cannot catch on the upper lip while the jaw is still pushed 1 mm to one side.'],
         checks=['The ring sits in its seat and both arms are straight again.',
                 'Open the jaw about 30° by hand and close it: it turns on the ring without catching.'],
         warnings=['This is the only flex fit in the build, and it is the same on the original MicroDuck shell. It has not yet been tried on these prints. Bending one arm 5 mm on its own loads the printed layers close to their limit; the even two-thumb press keeps a margin.',
                   'A PLA arm can split along a layer line without turning white first. Stop at any click or cracking sound and report it; do not file the jaw or the shell.'])

    step('neck-roll', 'head', 'Prepare the roll motor on the yaw fork', add=ROLL_GROUP, show=[], context=[], bench=True,
         approach={'head_roll_ring_a': [-60, 0, 0], 'head_roll_ring_b': [60, 0, 0], 'motor14': [-60, 0, 0]},
         camera=ctx.cam(ROLL_GROUP, direction=(0.4, -1.2, 0.7), margin=1.5),
         prepare=[{'item': 'Head yaw/roll link (10/1 print)', 'qty': 1, 'kind': 'printed'},
                  {'item': '22 mm ring (10/1 print)', 'qty': 2, 'kind': 'printed'},
                  {'item': 'Servo ID14', 'qty': 1, 'kind': 'electronic'}, tap(4, 'M2 × 6')],
         screwNotes={'M2 × 6 TAP': 'Through the fork arm into the ID14 output horn. Right-angle driver through the empty yaw-motor cavity.'},
         instructions=['Fit ID14 and its two rings to the black fork on the bench. The rings sit loose on the fork bosses: the lower head shell cups their lower half and the jaw support caps their upper half, and from then on they carry the head on both sides of the roll axis.',
                       'Drive four M2 × 6 through the fork arm into the ID14 output horn. A straight driver has only about 23 mm before the far fork arm, so use a compact right-angle driver with its handle out through the empty yaw-motor cavity.'])

    step('head-fork-in', 'head', 'Drop the fork with ID14 into the shell', add=ROLL_GROUP, show=['head_bottom'] + JAW_SET, context=[], bench=True,
         group={'label': 'Roll fork with ID14 and its two rings', 'approach': [0, 0, 40]},
         camera=ctx.cam(['head_bottom'] + ROLL_GROUP, direction=(0.6, -1.0, 1.1), margin=1.3),
         instructions=['Keep the jaw closed. Hold the fork by its top plate, a fingertip on each ring so they stay on their bosses.',
                       'Lower the fork with ID14 straight down into the open top of the shell. The lower half of each ring drops into its cup in the shell and ID14 drops into its pocket at the back.'],
         checks=['Both rings sit in their cups and ID14 sits in its pocket; the ID14 plug lines up with its cut-out.'],
         warnings=['The fork goes into the shell before it goes onto ID13. Once the fork is screwed to ID13, the shell can no longer reach the head: its floor opening rings the neck, with the torso below and the fork above.'])

    step('neck-yaw-case', 'head', 'Set the head on ID13 and connect 13 → 14', add=['head_bottom'] + JAW_SET + ROLL_GROUP,
         group={'label': 'Lower shell with the jaw, the fork and ID14', 'approach': [0, 0, 45]}, cables=['dxl-13-14'],
         camera=ctx.cam(['head_bottom', 'motor13', 'neck_pitch'] + ROLL_GROUP, direction=(1.0, -0.9, 0.5), margin=1.3),
         prepare=[tap(4, 'M2 × 10'), {'item': 'X3P 100 mm kit cable', 'qty': 1, 'kind': 'cable'}],
         screwNotes={'M2 × 10 TAP': 'Down through the fork top plate into the ID13 case corners.'},
         instructions=['Hold the shell level from below with the fork resting in it. Lower the whole head straight down over ID13: ID13 and the neck pass up through the large opening in the shell floor until the fork top plate sits flat on the ID13 case.',
                       'Keep one hand under the shell: nothing fixes the shell to the fork until the jaw support is screwed down in the next step.',
                       'Drive four M2 × 10 down through the fork top plate into the ID13 case corners.',
                       'Plug the 100 mm cable into ID13 socket 13 (top) and ID14 socket 14. Arch it over the top of the yaw case.'],
         checks=['The fork plate sits flat on ID13 and the shell floor touches nothing on the neck.',
                 'Yaw ±60° by hand: the 100 mm cable follows without pulling.'])

    step('head-bottom', 'head', 'Lower the jaw support with ID15 and screw it down', add=SUPPORT,
         group={'label': 'Jaw support with ID15', 'approach': [0, 0, 30]}, cables=['dxl-14-15'],
         camera=ctx.cam(SUPPORT + ['head_bottom'], direction=(0.6, 1.0, 1.2), margin=1.3),
         prepare=[tap(3, 'M2.6 × 6')],
         screwNotes={'M2.6 × 6 TAP': 'Down through the jaw support base plate into a lower-shell boss: the two +Y bosses and the front −Y boss. The rear −Y boss takes an M2.6 × 8 through the head wire clip in the next step. 3.3 mm of thread in the boss. The plate holes are only 0.05 mm wider than the screw, so press the plate down while you drive.'},
         instructions=['Plug the free end of the 180 mm cable into ID14 socket 13 while the top of the head is still open.',
                       'Lower the jaw support with ID15 straight down into the shell. The ID15 horn drops in behind the +Y jaw arm and the support seat drops over the sliding ring on the −Y side.',
                       'Drive three M2.6 × 6 down through the support base plate into the shell bosses: both on the +Y side and the front one on the −Y side. Leave the rear −Y hole empty: the head wire clip goes under that screw in the next step. These screws also clamp ID14 and ID15, which have no screws of their own.',
                       'Tuck the cable slack beside ID15, clear of the jaw arms and the screw bosses.'],
         checks=['ID14 and ID15 no longer move in the shell.', 'The jaw still swings by hand.', 'The rear −Y hole in the support base plate is still empty.'])

    step('head-clip', 'head', 'Fit the head wire clip under the fourth support screw', add=ctx.keys('clip_head'),
         approach={'clip_head': [0, 0, 18]},
         camera=ctx.cam(['clip_head', 'jaw_support', 'head_bottom'], direction=(0.4, -1.3, 1.0), margin=1.3),
         prepare=[{'item': 'Head wire clip (V1.9 print, orange)', 'qty': 1, 'kind': 'printed'}, tap(1, 'M2.6 × 8')],
         screwNotes={'M2.6 × 8 TAP': 'Down through the clip tab and the jaw support base plate into the rear −Y lower-shell boss. 2 mm longer than the other three because of the 2 mm tab; the thread bite (3.3 mm) and the tip position are the same.'},
         instructions=['Hold the clip over the rear −Y corner of the support base plate with its tab over the empty hole. Its square channel stands upright in front of the tab, towards the middle of the head, with the slot facing the −Y wall and the small window near the bottom of the channel facing +Y.',
                       'Lower it straight down onto the base plate and drive one M2.6 × 8 through the tab and the plate into the shell boss. Stop when the head touches the tab.',
                       'Later the bundle comes up through the floor opening beside the neck, crosses the top of the support wall, drops down this channel and leaves it through the window towards the A7Z.'],
         checks=['The tab lies flat under the screw head and the clip does not turn by hand.', 'The jaw still swings by hand and does not touch the clip.'])

    step('jaw', 'head', 'Screw the jaw to the ID15 horn',
         camera=ctx.cam(['jaw_frame', 'motor15'], direction=(0.3, 1.4, 0.4), margin=1.6),
         prepare=[tap(4, 'M2 × 6')],
         screwNotes={'M2 × 6 TAP': 'All four horn holes. The jaw arm is 4.1 mm thick at the front and top holes and 3.6 mm at the bottom and rear, so the front and top screws bite about 1.5 mm into the horn and the other two about 2.1 mm. The neck-pitch horn (ID13) carries the whole head on four screws that bite 1.85 mm.'},
         instructions=['Close the jaw. Turn the ID15 horn by hand until its four holes line up with the four holes in the +Y jaw arm.',
                       'From the +Y side, drive one M2 × 6 into each of the four holes. Start the front and top ones gently: they reach the horn thread later, through the thicker part of the arm.',
                       'Stop the moment each head touches the arm. The front and top screws hold on only about 4 turns of horn thread, and the horn is not replaceable without taking ID15 apart.'],
         checks=['Open and close the jaw by hand: ID15 turns with it with even resistance and nothing catches.',
                 'Hold the jaw arm and rock it against the horn: no play and no click.'])

    step('face', 'head', 'Fit the eye trim into the face panel and screw it from behind', add=FACE, show=[], context=[], bench=True,
         approach={'eye_trim': [50, 0, 0]},
         camera=ctx.cam(FACE, direction=(-1.4, 0.6, 0.4), margin=1.3),
         prepare=[{'item': 'Face panel (A7Z print, white) and eye trim (V1.8 print, black; the trim you already have fits)', 'qty': 1, 'kind': 'printed'}, tap(2, 'M2 × 6')],
         screwNotes={'M2 × 6 TAP': 'From the back of the face through the plain hole above or below the eye into the pilot in the eye trim; 4.7 mm of thread. The camera board covers both heads later.'},
         instructions=['Look at the back of the white face first. It is a flat plate with four round bosses at the corners of a 28 mm square round the eye opening, each with a small pilot hole in its top: the camera board screws onto them. Directly above and below the eye are two plain screw holes through the plate. If the back has four low pads and two short pins instead, it is the V1.8 face for the old camera.',
                       'Press the black eye trim into the eye opening from the front until it is flush. Its two rear pegs and the small key at the top enter their holes in the face. It is a tight push fit. Do not glue it.',
                       'Turn the face over. Drive one M2 × 6 from the back through the hole above the eye into the trim, and one through the hole below it. Stop when each head touches the face: the thread is cut in the black trim, and a stripped pilot means a new trim.'],
         checks=['The trim is flush with the front of the face and does not move when you push it from the front.',
                 'Both screw heads sit flat on the back of the face, inside the square of the four bosses.'])

    step('camera', 'head', 'Screw the camera to the back of the face', add=CAMERA, show=FACE, context=[], bench=True,
         approach={'camera_board': [-15, 0, 0]},
         camera=ctx.cam(CAMERA + FACE, direction=(-1.0, 0.5, 0.3), margin=1.6),
         prepare=[{'item': 'Radxa Camera 13M 214 with its 150 mm ribbon', 'qty': 1, 'kind': 'electronic'}, tap(4, 'M2 × 4')],
         screwNotes={'M2 × 4 TAP': 'From behind the camera, through a corner hole of the camera board into a face boss. Only 2.4 mm of thread: stop the moment the head touches the board.'},
         instructions=['The camera connector is on the lens side of the board, along one edge next to the lens. Open its latch, insert the 31-pin end of the ribbon fully and squarely, and close the latch. Do this while the board is still loose.',
                       'Lay the face front down on the bench with its top edge away from you. Set the camera lens first into the eye, with the connector edge on your left (that is the robot\'s left-hand side, +Y). The board lies on the four bosses and covers the two trim screw heads.',
                       'Drive the four M2 × 4 through the corner holes into the bosses. Turn each until its head just touches the board, then stop.',
                       'Lead the ribbon out of the connector to your left, flat between the board and the face. It leaves the camera on the left; it turns back into the head later.'],
         checks=['The lens is centred in the eye opening and the board sits flat on the four bosses without rocking.',
                 'The ribbon leaves the camera on the robot\'s left (+Y).'],
         warnings=['Hold the ribbon by its stiffened end; never fold it at the stiffener or pull on the lens.',
                   'Turned this way the picture comes out rotated by 90°. The software turns it back (chapter 10); the camera stays as mounted.'])

    step('face-on', 'head', 'Set the face and camera on the head', add=FACE + CAMERA,
         group={'label': 'Face with eye trim and camera', 'approach': [0, 0, 40]},
         camera=ctx.cam(FACE + ['head_bottom', 'jaw_support'], direction=(1.4, 0.6, 0.6), margin=1.2),
         instructions=['Lower the face unit straight down into the front of the lower shell, camera board inwards.',
                       'Lead the ribbon from the left-hand (+Y) side of the camera along the left wall of the head, flat and without a sharp fold. Near the left edge of the face it turns back towards the A7Z. The free end goes to the A7Z in chapter 8.',
                       'The face has no screws: the cap clamps it when the head is closed at the end. Keep the head upright until then.'],
         checks=['The face sits evenly on the shell all round and the ribbon is not trapped under it.'])

    # ------------------------------------------------------------------ 7. Head electronics
    cap = ctx.keys('head_cap')
    step('cap', 'head-elec', 'Prepare the head cap', show=[], add=cap, context=[], bench=True,
         camera=ctx.cam(cap, direction=(-0.6, 0.8, -0.9), margin=1.1),
         instructions=['Work on the cap upside down on the bench. Its two board rails are printed in; add no extra spacers. On this cap the rails touch the board only on a round pad round each screw hole, and each end of the board space has a slot: the left (+Y) slot takes the camera connector and its ribbon, the right (−Y) slot the end of the microSD card.',
                       'Find the three other features inside the roof: at the back, the shallow ring of the speaker collar with one small pilot hole on each side of it; in the middle, the two short amplifier posts with a pilot hole in the end of each. The cap has no rear notch.',
                       'Run a 1.5 mm drill or a needle through the four audio pilots and the four rail pilots so no stringing is left in them.'])

    step('speaker', 'head-elec', 'Seat the speaker in the cap collar with the retainer', show=[], context=cap, add=ctx.keys('speaker_tape', 'speaker', 'speaker_retainer'), bench=True,
         approach={'speaker_tape': [5, 0, -20], 'speaker': [5, 0, -20], 'speaker_retainer': [5, 0, -20]}, cables=SPK_CABLES,
         # Cap ghosted, camera above the roof looking down through it: the grille face with its seven holes and the yellow tape loop
         # face the viewer, which is what the tape step needs; orbit underneath to see the magnet, the pads and the retainer.
         camera=ctx.cam(ctx.keys('speaker', 'speaker_retainer'), direction=(-0.35, 0.35, 1.0), margin=1.6),
         images=[figure('speaker-section-en.png', 'Section across the middle of the speaker seen from the amplifier end: the flat metal grille faces the roof; the foam-tape loop sits on the 0.6 mm lip ring at the speaker edge; the 1.6 mm pocket over the grille stays clear under the sound slots; the round magnet and the two solder pads face the retainer.')],
         prepare=[{'item': 'Speaker with its two leads', 'qty': 1, 'kind': 'electronic'},
                  {'item': 'Foam double-sided tape about 1 mm thick, two strips of about 40 x 1.5 mm', 'qty': 1, 'kind': 'other'},
                  {'item': 'Speaker retainer (V1.9 print, orange)', 'qty': 1, 'kind': 'printed'}, tap(2, 'M2 × 6')],
         screwNotes={'M2 × 6 TAP': 'Up through the retainer frame into a blind 1.7 mm pilot beside the collar, one on each side; 4.1 mm of thread, tip 0.6 mm short of the pilot end.'},
         instructions=['Which way round: one face of the speaker is a flat metal grille with seven round holes (one large in the middle, six small); the other face has the raised round magnet and the two solder pads. The grille faces the cap roof (up into the collar); the magnet and pads face the retainer, with the pads at the end nearest the amplifier posts. The 3D view looks down through the see-through roof at the grille holes and the yellow tape loop; drag to orbit underneath for the magnet, the two pads and the retainer.',
                       'Cut two strips of 1 mm foam double-sided tape, each about 40 x 1.5 mm. Stick the first one on the grille face right along the edge: start at the middle of one short end, follow the curve, run down the long side and round the other curve, and stop at the middle of the other short end. The second strip does the other half, its ends butting the first, so the tape makes one closed loop (the yellow loop in the 3D view). Press it down along the curves as you go; trim any overlap. The loop stays on the outer 1.5 mm, where the collar has a 0.6 mm lip ring, and clears all seven holes by about 0.8 mm; never cover a hole. Peel the top liners.',
                       'Press the speaker, grille first, into the collar at the back of the roof with the two leads pointing forward towards the amplifier posts. The collar is tilted with the roof; let the speaker follow it. The retainer screws press the tape from 1 mm down to 0.6 mm, which is what holds the speaker.',
                       'Set the retainer frame over the back of the speaker so its two screw holes sit over the two pilots beside the collar.',
                       'Drive two M2 × 6 through the retainer into the pilots. Stop when each head touches: the foam tape, not the screws, holds the speaker tight, and no glue is used.'],
         checks=['The metal grille faces the roof and is hidden inside the collar; the round magnet and the two solder pads are visible on the exposed face, the pads at the amplifier end.',
                 'The speaker does not slide in the collar when you push it sideways, and the retainer frame touches its rim all round.',
                 'Both leads come out towards the posts.'],
         links=[bringup('ab-7', 'Detailed page: soldering the two speaker leads', 'BRINGUP step 13, part 5')])

    step('amplifier', 'head-elec', 'Mount the amplifier on its two posts', show=cap + ctx.keys('speaker', 'speaker_retainer'), add=ctx.keys('amplifier'), bench=True,
         approach={'amplifier': [0, 0, -20]}, cables=SPK_CABLES + AUDIO_CABLES,
         camera=ctx.cam(ctx.keys('amplifier') + cap, direction=(0.3, 0.6, -1.0), margin=1.2),
         prepare=[{'item': 'MAX98357A amplifier from BRINGUP step 13: five wires soldered into LRC, BCLK, DIN, GND and Vin, GAIN and SD empty, a flagged jumper plug on the far end of each wire', 'qty': 1, 'kind': 'electronic'}, tap(2, 'M2 × 6'),
                  {'item': 'Small flat screwdriver for the green terminal', 'qty': 1, 'kind': 'tool'}],
         screwNotes={'M2 × 6 TAP': 'Up through a board hole into the blind 1.7 mm pilot in the end of a cap post; 4.15 mm of thread, tip 1.1 mm short of the pilot end.'},
         instructions=['Done: the amplifier is screwed onto the two posts in the cap roof, the speaker leads are in its green terminal, and the five flagged plugs hang out of the cap.',
                       'While the board is loose, screw the speaker leads into the green terminal: + lead under +, − lead under −. Pull each lead: it holds.',
                       'Hold the board components towards the roof, the five wires pointing forward towards the board rails and lying flat where they leave the board.',
                       'Set the two board holes on the two posts. Drive an M2 × 6 up through each hole into its post. Stop when the head touches.',
                       'Lay the speaker leads flat between the speaker and the terminal.',
                       'Lead the five wires forward over the board space and let the plugs hang out of the cap.'],
         checks=['The board sits flat on both posts, and the five wires leave its front edge flat against the roof.',
                 'Each plug has its A7Z flag: 35, 12, 40, 39, 4 (the GND flag from BRINGUP step 13 said 34; rewrite it to 39).',
                 'The speaker leads are held, and the solder joints on the back of the board touch nothing.'],
         warnings=['The Vin wire is 5 V: its flag must say 4, and nothing else goes on pin 4.'],
         links=[bringup('s13', 'Detailed page: amplifier, five wires', 'BRINGUP step 13: which hole is which, soldering the five wires, meter checks and the speaker (its header pins are the old head; the A7Z pins are on the A7Z wiring page)'),
                here('wire-list', 'Soldering and wire list')])

    step('antenna', 'head-elec', 'Stick the Wi-Fi antenna inside the cap roof', show=cap + audio, add=antenna, bench=True,
         approach={'antenna': [0, 0, -15]},
         camera=ctx.cam(antenna + cap, direction=(0.4, 0.3, -1.0), margin=1.1),
         prepare=[{'item': 'AC019 Wi-Fi antenna from the A7Z box: a flat sticker 42 × 12 mm with a 50 mm cable and a small round IPEX plug', 'qty': 1, 'kind': 'electronic'},
                  {'item': 'Isopropyl alcohol and a tissue', 'qty': 1, 'kind': 'other'}],
         instructions=['Done: the antenna lies flat inside the front of the cap roof, across the head, its cable end at the robot\'s left (+Y).',
                       'With the cap upside down, find the smooth dome of the roof in front of the board rails (towards the face). Wipe it with alcohol and let it dry.',
                       'Peel the backing and stick the antenna across that dome, centred left to right, with the cable end towards the left (+Y) end of the cap. Press it down along its whole length so it follows the curve.',
                       'Let the cable and its plug hang out of the left (+Y) end of the cap; the plug goes onto the A7Z after the cap wire clip.'],
         checks=['The antenna lies flat with no lifted corner and does not cover a rail pad or a pilot hole.'],
         warnings=['Never pull on the thin cable or bend it sharply at the plug.'],
         links=[a7z('stick', 'Antenna page: where it goes, photos and the Wi-Fi check', page='A7Z-ANTENNA.html')])

    if touch:
        step('touch', 'head-elec', 'Stick the five copper touch pads and the XIAO inside the cap', show=cap + audio + antenna, add=touch, bench=True,
             approach={**{k: [0, 0, -12] for k in TOUCH_PADS}, 'touch_xiao_tape': [3.7, -10.5, -4.4], 'touch_xiao': [3.7, -10.5, -4.4]},
             cables=TOUCH_PAD_CABLES,
             camera=ctx.cam(touch + cap, direction=(-0.3, -0.5, -1.0), margin=1.1),
             prepare=[{'item': 'Seeed XIAO ESP32-S3 with its nine wires soldered (wire list): five pad leads on D0, D1, D2, D3 and D8, and four jumper wires on 3V3, GND, D5 and D4, each with a flagged plug: 17, 25, 29, 31', 'qty': 1, 'kind': 'electronic'},
                      {'item': 'Copper foil tape with conductive adhesive', 'qty': 1, 'kind': 'other'},
                      {'item': 'Foam double-sided tape about 1 mm thick, one piece 21 x 18 mm', 'qty': 1, 'kind': 'other'},
                      {'item': 'Isopropyl alcohol and a tissue; soldering iron', 'qty': 1, 'kind': 'other'}],
             instructions=['Done: five copper squares inside the cap wall (L1 and L2 on the left, R1 and R2 on the right, M in the middle at the front), the XIAO on foam tape on the inner left wall behind the speaker, a lead from each pad to the XIAO, and four flagged plugs hanging out of the cap.',
                           'Soldering at the XIAO is an approved exception, like the amplifier: a header with plugs stands about 20 mm and would not fit. Solder each wire flat onto the top face of its edge pad (the half-hole on the board edge), so it leaves the board sideways and not upwards.',
                           'With the cap upside down, wipe the inside of the wall at the five places in the 3D view with alcohol and let it dry.',
                           'Cut each pad from the copper tape, about 18 x 18 mm (lay 6 mm strips side by side, each overlapping the last by 1 mm; the conductive adhesive joins them). Press each pad down with a fingernail so it follows the curve with no air under it.',
                           'Stick the foam tape on the flat back of the XIAO (the side without the metal can). Press the XIAO onto the inner left wall where the 3D view shows it, metal can facing into the head, USB-C end towards the back, the D0 to D6 edge up.',
                           'Solder each pad lead to a corner of its pad: tin the copper briefly, lay the stripped wire on it, touch it with the iron for a second or two. Too much heat lifts the tape and can mark the PLA. Pad L1 to D0, R1 to D1, L2 to D2, R2 to D3, M to D8.',
                           'Lay each pad lead flat along the wall to the XIAO and hold it with a small piece of tape. R1, R2 and M cross the roof in front of the speaker collar and behind the amplifier.',
                           'Lead the four A7Z wires (flags 17, 25, 29, 31) forward along the left wall towards the board rails and let the plugs hang out of the cap.'],
             checks=['Each pad lies flat with no lifted corner; no pad touches another pad, a screw, the speaker retainer or the amplifier.',
                     'A meter in continuity mode beeps between each pad and its XIAO pin (L1 D0, R1 D1, L2 D2, R2 D3, M D8) and does not beep between any two pads.',
                     'The XIAO does not move when pushed, and no wire stands up from it more than about 2 mm.'],
             warnings=['Copper is bare on its top face: keep every pad clear of the A7Z, the amplifier and screw heads.'],
             links=[here('wire-list', 'Soldering and wire list')])

    pi_add = pi_parts
    step('pi', 'head-elec', 'Mount the Radxa Cubie A7Z on the cap rails', show=cap + audio + antenna + touch, add=pi_add, bench=True,
         group={'label': 'Radxa Cubie A7Z with soldered 40-pin header', 'approach': [24.6, 0, -4.3]},   # straight down onto the rails, along the board normal
         camera=ctx.cam(['pi'] + cap, direction=(1.0, 0.3, 0.6), margin=1.0),
         prepare=[{'item': 'Radxa Cubie A7Z with 40-pin header and flashed microSD', 'qty': 1, 'kind': 'electronic'}, tap(2, 'M2 × 6'), tap(1, 'M2 × 4')],
         screwNotes={'M2 × 6 TAP': 'Two board corners on the −Y rail: through the corner hole into the rail pad, driven from the header side. The upper +Y corner takes an M2 × 8 through the cap wire clip in the next step.',
                     'M2 × 4 TAP': 'The lower corner on the +Y rail only (the antenna-socket end, next to header pin 1). That rail is trimmed to clear the jaw support, so a longer screw would stick out of its back.'},
         instructions=['Insert the microSD card first (chapter 10 for the OS). On the A7Z the card slot is on the underside at the end away from header pin 1; the card sticks out about 2 mm.',
                       'With the cap beside the head, insert the free end of the camera ribbon into the A7Z camera connector, contacts towards the board, and close the latch. That connector is on the underside of the A7Z at the pin-1 end, at the end edge.',
                       'Hold the five amplifier wires, the four XIAO wires and the antenna cable out of the way and lower the A7Z straight down onto the two rails, header towards the face and down, pin-1 end to the left (+Y). Do not slide it along the rails: the parts under the board would catch on them. The ribbon wraps round the board end into the left slot of the cap; the microSD card goes into the right slot. The board rests on the four round pads.',
                       'Drive the short M2 × 4 into the lower +Y corner first, then M2 × 6 into the two −Y corners. Leave the upper +Y corner empty: the cap wire clip goes under that screw in the next step. The rail pilots are 1.7 mm; M2.5 or M2.6 screws split them.'],
         checks=['Both ribbon latches are closed; the ribbon and the microSD card sit in their end slots without being pinched.',
                 'The antenna is still flat and its cable hangs free.',
                 'No screw tip shows behind the +Y rail.', 'The upper +Y corner hole of the A7Z is still empty.'],
         links=[a7z('mount', 'Antenna page: the A7Z on the rails', page='A7Z-ANTENNA.html')])

    step('pi-clip', 'head-elec', 'Fit the cap wire clip under the fourth A7Z screw', show=cap + audio + antenna + touch + pi_add, add=ctx.keys('clip_cap'), bench=True,
         approach={'clip_cap': [16, 0, -3]},
         camera=ctx.cam(ctx.keys('clip_cap') + ['pi'], direction=(1.0, 0.6, 0.5), margin=1.4),
         prepare=[{'item': 'Cap wire clip (A7Z print, orange: with a notch in its underside for the micro HDMI socket)', 'qty': 1, 'kind': 'printed'}, tap(1, 'M2 × 8')],
         screwNotes={'M2 × 8 TAP': 'Through the clip tab and the upper +Y corner of the A7Z into the cap rail. 2 mm longer than the other rail screws because of the 2 mm tab; the thread bite (4.1 mm) and the tip position are the same.'},
         instructions=['Hold the clip on the A7Z with its tab over the empty upper +Y corner hole and its square channel lying across the top edge of the board, slot facing away from the board. The notch in its underside sits over the micro HDMI socket. The V1.9 clip has no notch and rocks on that socket; do not use it.',
                       'Drive one M2 × 8 through the tab and the board corner into the rail. Stop when the head touches the tab.',
                       'The bundle from the torso is pressed into this channel in chapter 9, where it crosses the top edge of the board on its way down to the header.'],
         checks=['The tab lies flat under the screw head and the clip does not turn by hand.', 'The channel slot is open and clear of the board components and the antenna cable.'])

    step('antenna-plug', 'head-elec', 'Plug the antenna cable onto the A7Z', show=cap + audio + antenna + touch + pi_add + clips[-1:], add=antenna_lead, bench=True,
         group={'label': 'AC019 antenna cable and IPEX plug', 'approach': [6, 0, -1]},   # pressed straight down onto the socket
         camera=ctx.cam(antenna_lead + ['pi'] + clips[-1:], direction=(1.0, 0.5, 0.5), margin=1.6),
         instructions=['Done: the antenna\'s IPEX plug is clicked onto the A7Z antenna socket and its cable runs along the board, forward and up to the antenna, in front of the cap wire clip.',
                       'Find the small round antenna socket on the top side of the A7Z, at the pin-1 end (left, +Y) beside the small fan socket.',
                       'Hold the plug square over it, cable pointing to the right (towards −Y, along the board), and press straight down with a fingertip until it clicks. Do not rock it on.',
                       'Lay the cable flat along the top face of the board for a few millimetres, then forward and up under the roof to the antenna. Keep it in front of the cap wire clip, off the header pins.'],
         checks=['The plug sits flat and does not turn when you touch the cable.', 'The cable does not cross the header pins, the clip channel or the clip screw.'],
         warnings=['Never pull the plug off by its cable; lever it straight up under the plug body.'],
         links=[a7z('plug', 'Antenna page: plugging the IPEX plug', page='A7Z-ANTENNA.html')])

    step('audio-pi', 'head-elec', 'Plug the five amplifier wires onto the A7Z', show=cap + audio + antenna + touch + antenna_lead + pi_add + clips[-1:], add=audio_gpio, bench=True,
         approach={k: [20, 0, 0] for k in audio_gpio}, cables=AUDIO_CABLES,
         camera=ctx.cam(audio_gpio + ['pi'], direction=(1.0, 0.8, 0.4), margin=1.6),
         instructions=['Done: the five amplifier wires sit on the A7Z pins written on their flags: 4, 12, 35, 39 and 40.',
                       'Count pins from the pin-1 end of the header: the end with the antenna socket, opposite the microSD card. The row along the board edge is the even pins; the other row (the inner row) is the odd pins. This is the other end from the one used on the Pi.',
                       'Flag 4 (Vin): edge row, 2nd pin.',
                       'Flag 12 (BCLK): edge row, 6th pin.',
                       'Flag 35 (LRC): inner row, 18th pin (3rd from the far end).',
                       'Flag 39 (GND): inner row, last pin.',
                       'Flag 40 (DIN): edge row, last pin.',
                       'Bend the BCLK wire flat against the end of its plug and lead it up between the plug and the camera position (only about 2 mm there once the face is on), then each wire down the front of the A7Z and over its top edge back to the amplifier, flat on the board. Keep the top edge at the +Y end free for the cap clip.'],
         checks=['Wires on pins 4, 12, 35, 39 and 40 only. Count again from the antenna-socket end.',
                 'Pin 2 (edge row, 1st) is empty, and nothing else is on the edge row between pin 4 and pin 40 except pin 12.'],
         warnings=['Pin 4 is 5 V: the Vin plug on the wrong pin can kill the A7Z.'],
         links=[a7z('audio', 'A7Z wiring page: the five amplifier wires')])

    # The eight ends are shown on their pins so the reader sees where each flag goes; they are plugged at cap-on, so this
    # step has no slide-on animation (the source jumper-end envelopes are two rows tall and would cross the audio ends).
    if touch_gpio:
        step('touch-pi', 'head-elec', 'Plug the four XIAO wires onto the A7Z', show=cap + audio + antenna + touch + antenna_lead + pi_add + clips[-1:] + audio_gpio, add=touch_gpio, bench=True,
             approach={k: [20, 0, 0] for k in touch_gpio}, cables=TOUCH_PIN_CABLES,
             camera=ctx.cam(touch_gpio + ['pi'], direction=(1.0, 0.8, 0.4), margin=1.6),
             instructions=['Done: the four XIAO wires sit on the A7Z inner-row pins written on their flags: 17, 25, 29 and 31.',
                           'Count on the inner row (the odd pins) from the pin-1 end, the end with the antenna socket.',
                           'Flag 17 (3.3 V): inner row, 9th pin.',
                           'Flag 25 (GND): inner row, 13th pin.',
                           'Flag 29 (SCL): inner row, 15th pin.',
                           'Flag 31 (SDA): inner row, 16th pin.',
                           'Bend each wire down right at its plug, as for the amplifier ground on 39, and lead it up the front of the A7Z and over its top edge back along the left wall to the XIAO.'],
             checks=['Wires on 17, 25, 29 and 31, all on the inner row. Pin 17 is 3.3 V: one pin off puts 3.3 V on the wrong line.'],
             warnings=['Never put the 3V3 wire on pin 2 or 4 (5 V): the XIAO 3V3 pin takes 3.3 V only.'])

    step('gpio', 'head-elec', 'Check the plug on every wire that goes to the A7Z and flag it', show=cap + audio + antenna + touch + antenna_lead + pi_add + clips[-1:] + audio_gpio + touch_gpio, add=gpio, bench=True,
         camera=ctx.cam(gpio + ['pi'], direction=(1.0, 0.8, 0.4), margin=1.6),
         prepare=[{'item': 'Masking tape and a fine marker', 'qty': 1, 'kind': 'other', 'note': 'For a pin-number flag on each wire.'},
                  {'item': 'Electrical tape', 'qty': 1, 'kind': 'other', 'note': 'For the joint of each head-lead jumper chain, if it is not taped yet.'}],
         instructions=[
             'Done: the eight wires at the top-rear corner of the torso each end in a black plug with a tape flag giving its A7Z pin. Nothing is soldered in this step.',
             'The eight wires: the PI lead (the head 5 V lead, two jumper chains from XL4015 #2 in the rear converter box), the four IMU wires and the UART pair. The PI lead and the UART pair already end in female plugs, and the IMU wires end in the 4397 cable\'s own sockets.',
             'PI lead: check that the joint of each chain (male plug inside the female plug) is taped so it cannot pull apart in the neck.',
             'Wrap a tape flag round each wire right behind its plug and write the pin: PI red 2, PI black 6, UART green 7, UART white 11, IMU red 1, IMU blue 3, IMU yellow 5, IMU black 9. Flags written for the Pi (8, 10, 7, 13) must be rewritten.',
             'Plug nothing onto the A7Z yet. That happens in chapter 9.',
         ],
         checks=['Eight plugs, eight flags: 1, 2, 3, 5, 6, 7, 9, 11.', 'Tug each IMU joint and each PI chain joint: it holds, and no copper shows.'],
         links=[a7z('pins', 'A7Z wiring page: every pin, with photos'),
                bringup('s12', 'Detailed page: the 5 V lead', 'BRINGUP step 12 (pins 2 and 6 are the same on the A7Z)'),
                here('wire-list', 'Soldering and wire list')])

    # ------------------------------------------------------------------ 8. Bundle
    step('bundle-run', 'bundle', 'Run the 8-wire bundle through the torso, bracket and head clips',
         cables=['pi-lead', 'imu', 'uart'],
         camera=ctx.cam(SHELLS + NECK_LOWER + ['motor13', 'motor14', 'clip_head'], direction=(0.9, -1.2, 0.45), margin=1.15),
         prepare=[{'item': 'Narrow cable ties', 'qty': 2, 'kind': 'other'}, {'item': 'Spiral wrap, 5 mm or smaller outside diameter', 'qty': '300 mm', 'kind': 'other', 'note': 'Each clip channel is 4.8 mm square with a 2.4 mm slot; the eight wires lie two deep, about 3.4 mm across.'}],
         instructions=[
             'Gather the PI pair, the four IMU wires and the two UART wires, all over the notch in the pack plate, at the top-rear corner: eight wires. Wrap them in spiral wrap from the pack notch to the head.',
             'Lead the group forward and to the right (−Y) across the top of the torso, over ID12, to the torso clip on the right shell. Press it into the clip channel through the slot: push the wires in two or three at a time with a fingernail until all eight lie in the channel. Nothing else holds it there.',
             'Run the group straight up the right side of the neck, past ID11, to the bracket clip on the pitch bracket. Press it into that channel the same way. Leave the group slightly slack between the two clips, about 5 mm of bow: the bracket pitches with the head.',
             'From the bracket clip, lead the group up and in through the right (−Y) side of the opening in the floor of the lower head shell, beside the neck, over the top of the jaw-support wall and down into the head clip channel. Press it in through the slot and bring it out of the window at the bottom of the channel, towards the board space.',
             f'From the pack notch to the head clip the group is about {L["bundle_neck"] + 40} mm. Leave the eight jumper ends hanging out of the open top of the head for now.',
             'Tie the group once to the torso at the pack notch so a pull from outside loads the pack plate, not the plugs. Do not tie it to any neck link.',
         ],
         checks=['Pitch, yaw and roll the head by hand through the trained range (yaw about ±80°): the group slides in the head opening, bows between the two clips and never goes tight or rubs a horn.',
                 'The jaw opens 30° by hand without touching the group or the head clip.'])

    step('cap-on', 'bundle', 'Plug the bundle onto the A7Z, press it into the cap clip and lower the cap',
         add=cap + audio + antenna + touch + antenna_lead + pi_add + clips[-1:] + audio_gpio + touch_gpio + gpio,
         group={'label': 'Populated head cap from chapter 8', 'approach': [0, 0, 40]},
         cables=['pi-lead', 'imu', 'uart'] + AUDIO_CABLES + SPK_CABLES + TOUCH_PAD_CABLES + TOUCH_PIN_CABLES,
         camera=ctx.cam(cap + ['motor14'], direction=(-1.0, 0.7, 0.5), margin=1.2),
         instructions=[
             'Done: eight more plugs on the A7Z, the bundle pressed into the cap clip, and the cap resting loose on the head.',
             'Hold the cap upside down above the head, header towards you. With the cap lifted about 40 mm, the eight plugs from the head clip reach the header.',
             'Count pins from the pin-1 end of the header: the end with the antenna socket, opposite the microSD card. The row along the board edge is the even pins; the inner row is the odd pins.',
             'Edge row: flag 2 (PI red) on the 1st pin, flag 6 (PI black) on the 3rd.',
             'Inner row: flag 1 (IMU red) on the 1st pin, flag 3 (IMU blue) on the 2nd, flag 5 (IMU yellow) on the 3rd, flag 7 (UART green) on the 4th, flag 9 (IMU black) on the 5th, flag 11 (UART white) on the 6th.',
             'Push each plug fully down. The amplifier wires are already on 4, 12, 35, 39 and 40, the touch wires on 17, 25, 29 and 31. All other pins stay empty, including 8 and 10 (the A7Z debug console).',
             'Bend the wires on the inner row down where they leave the plugs and lay them towards the left (+Y) end along the bottom of the header: the camera board will stand just in front of the plug ends, and only the space under its bottom edge stays free. Bend the two edge-row wires (2 and 6) up and to the left.',
             'Lead the bundle up the front of the A7Z, over its top edge at the +Y end, and press it into the cap clip channel through the slot.',
             'Behind the A7Z the bundle runs under the five amplifier wires towards the head clip. Lay the amplifier wires flat on top of it.',
             'Fold the extra camera ribbon flat along the left (+Y) wall, between the face and the board end.',
             'Lower the cap slowly onto the head. Watch the bundle between the head clip and the cap clip: it bows, it does not fold.',
         ],
         checks=['Every plug is fully down. Count again from the antenna-socket end: none is one pin off or in the wrong row.',
                 'Over the last 15 mm the cap goes down without any wire catching on the camera board, its ribbon or the amplifier wires.',
                 'Lift the cap 20 mm and let it down again: the bundle slides in the head clip and nothing pulls at the pins.'],
         warnings=['Pins 2 and 4 are 5 V: a plug one pin off can kill the A7Z.',
                   'Leave the cap unscrewed until "Screw the head shut"; the power-up checks need it loose.',
                   'To take the cap off later, lift it about 40 mm and unplug the eight plugs first.'],
         links=[a7z('check', 'A7Z wiring page: final check of all 17 wires')])

    # ------------------------------------------------------------------ 9. Power-up
    full = list(installed)
    step('unpowered', 'power-up', 'Unpowered checks', show=[k for k in full if k not in BOX_LID],
         camera=ctx.cam(LEGS + ['head_cap'], direction=REAR, margin=1.0),
         prepare=[{'item': 'Multimeter', 'qty': 1, 'kind': 'tool'}],
         instructions=['Take the lid off the rear converter box (the four M2 × 10 in the holes in its back, then pull it straight back) and keep it aside with its screws: it stays off until the current check. With the USB-C cable out of the 5991, measure resistance on each of the three supplies. The 7 V pair and the head 5 V lead are not on their converters yet (they go on in "First power"), so each is checked on its own.',
                       '15 V side: 5991 terminal + to −: not a short. It is the same circuit as both converter inputs.',
                       '7 V side: OpenRB terminal block + to −: not a short (the OpenRB input capacitors charge from the meter, then it reads high). Read the same between the two taped converter ends of the 7 V pair; if they read open while J4 does not, a wire is loose under a J4 screw.',
                       '5 V side: A7Z header pin 2 to pin 6: not a short. Pins 7 and 11 are not connected to pin 2 or 4.',
                       'Cross check: the red end of the 7 V pair to A7Z pin 2: no beep, reads high. A beep means the 7 V pair and the head 5 V lead are swapped or touch.',
                       'Turn every joint by hand once more through its full range.',
                       'Leg clearance at the back: on each leg, turn the toes inward a little and swing the foot backwards. The shin passes under the bottom rear edge of the pack. In simulated walking over every adopted policy frame the left shin stays at least 3.7 mm and the right shin 5.0 mm from the pack, the hip bodies at least 4.9 mm, This was simulated for the pack; the rear converter box, the wire loops outside its side windows and the USB-C plug in its left-hand wall have been checked only in the standing pose, so swing each leg backwards and outwards and watch the shin and the plug. Note any rubbing on the pack floor, the box or the plug.',
                       'Two cables leave the robot: the USB-C power cable from the 5991, out of the low window in the left-hand (+Y) wall of the bottom tier of the rear converter box, and the OpenRB USB data cable through the pack floor slot. Lead both straight back to the table; neither may loop round a leg.'],
         checks=['No short on any of the three supplies, and no connection between the 7 V pair and A7Z pin 2.', 'Every cable end is plugged and latched.',
                 'Neither foot touches the pack, the box or the USB-C plug when swung backwards with the toes turned in.'])

    step('pi-config', 'power-up', 'Set up the A7Z software', show=full,
         camera=ctx.cam(['pi', 'head_cap'], direction=(1.0, 0.4, 0.8), margin=1.3),
         instructions=[
             'Flash Radxa\'s official Debian image for the Cubie A7Z to the microSD card (docs.radxa.com, Cubie A7Z, quick start).',
             'On the A7Z run sudo rsetup, go to Overlays, Manage overlays, and switch on four: Enable UART2 (TX pin 7, RX pin 11, the OpenRB link), Enable TWI7 (pins 3 and 5, the IMU), Enable I2S0 (pins 12, 35 and 40, the amplifier) and Enable Radxa Camera 13M 214. Reboot.',
             'Then switch TWI7 to engine mode with the MicroDuck overlay guide/firmware/pi/duck-twi7-engine.dts. In the default drv mode, which Radxa\'s Enable TWI7 overlay sets, the A7Z\'s TWI7 driver locks up right after boot, after the probe i2cdetect sends and whenever the IMU resets, and stays locked until the driver is restarted, so the IMU looks missing although its wires are fine. Copy the file to the A7Z and run: dtc -@ -I dts -O dtb -o /tmp/zz-duck-twi7-engine.dtbo duck-twi7-engine.dts, then sudo install -m 644 /tmp/zz-duck-twi7-engine.dtbo /boot/dtbo/, then sudo u-boot-update. Keep the zz- in the name: overlays load in alphabetical order, and this one must come after Radxa\'s twi7 overlay or that one sets drv mode back. grep fdtoverlays /boot/extlinux/extlinux.conf ends with zz-duck-twi7-engine.dtbo. Reboot. cat /sys/devices/platform/soc@3000000/2517000.twi/twi_mode must say "Current mode is 0: engine". rsetup now lists it as "MicroDuck: TWI7 in engine mode"; leave it on. To undo, delete the file from /boot/dtbo, run sudo u-boot-update and reboot.',
             'The touch board on pins 29 and 31 has no ready-made overlay on the A7Z (Radxa\'s Enable TWI0 is for the CM-A7 only). Its I2C overlay is written and checked during the touch bench test (extension-20261015-touch/PLAN.md); until then the touch wires stay plugged in and unused.',
             'The OpenRB link is then /dev/ttyAS2 and the IMU is on I2C bus 7. The scripts below take the port as --port /dev/ttyAS2; imu_read.py takes the bus as its second argument.',
             'Leave pins 8 and 10 empty: they are the A7Z debug console (115200 baud), the way back in with a USB serial adapter if the network fails.',
             'Copy guide/firmware/pi/scan_bus.py, set_shutdown.py, check_voltage_limit.py, battery.py, current_watch.py and imu_read.py to the A7Z (duck-twi7-engine.dts goes over in the step above) and install the Python packages dynamixel_sdk, adafruit-circuitpython-bno08x and adafruit-extended-bus.',
         ],
         checks=['ls /dev/ttyAS2 shows the port.', 'ls /dev/i2c-7 shows the IMU bus.', 'twi_mode says "Current mode is 0: engine".'],
         links=[a7z('software', 'A7Z wiring page: the overlays and device names')])

    # Converter readback before the loads go on, then Shutdown 52 on every servo (set_shutdown.py: torque off, write,
    # read back; EEPROM) and a power-cycle, then the voltage-limit check (check_voltage_limit.py --rail battery,
    # read-only: 6.4-8.4 V, Shutdown 52 required): XL330 Max Voltage Limit (address 32, factory 70 = 7.0 V), Shutdown (63,
    # factory 53, 52 clears bit 0 Input Voltage Error), Hardware Error Status (70), Present Input Voltage (144), e-Manual
    # https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/ (checked 2026-10-14). Shawn's robot holds 52 on 15/15 since
    # 2026-10-15 (current_build.servo_shutdown_52_20261015).
    step('first-power', 'power-up', 'First power: converter readback, bus scan, Shutdown 52 and voltage-limit check', show=[k for k in full if k not in BOX_LID], cables=['pw-15v', 'pw-15v-link', 'pw-7v', 'pi-lead'],
         camera=ctx.cam(LEGS + ['head_cap'], direction=REAR, margin=1.0),
         prepare=[{'item': 'Multimeter and small flat screwdriver', 'qty': 1, 'kind': 'tool'}],
         instructions=[
             'Lay the robot on its right side with the legs free, so the USB-C plug in the left-hand wall of the box points up and the open back of the rear converter box faces you (the lid is off since the unpowered checks). The 7 V pair and the head 5 V lead are still off their converters, so plugging in now powers only the 5991 and the two XL4015.',
             'Check once more that only the 15V slider of the 5991 is on. Plug the USB-C cable into the charger, then into the 5991.',
             'Readback before any load: meter on XL4015 #1 OUT+ and OUT−: 7.35 to 7.45 V. Meter on XL4015 #2 OUT+ and OUT−: 4.95 to 5.10 V. If either is off, set it again with its marked voltage trimmer (chapter 3) before you go on.',
             'Unplug the USB-C cable. Untape the ends of the 7 V pair at the OUT block of XL4015 #1 (top converter, left-hand end) and screw red under #1 OUT+ and black under #1 OUT−. Untape the two head 5 V lead ends at the OUT block of XL4015 #2 (middle converter, left-hand end; male pin already cut off, 10 mm stripped, strands twisted and folded back) and screw red under #2 OUT+ and black under #2 OUT−. Tug every wire. The U-loops outside the left-hand windows keep their shape.',
             'Plug the USB-C cable in again. The green PWR light on the OpenRB and the green power light on the A7Z come on.',
             'Meter on DC volts: the OpenRB terminal block (red probe on +) reads 7.2 to 7.45 V; A7Z pin 2 to pin 6 (edge row, 1st and 3rd pin from the antenna-socket end) reads 4.9 to 5.1 V.',
             'The servo ports switch on about half a second after the OpenRB starts.',
             'On the A7Z run: python3 scan_bus.py --port /dev/ttyAS2. It pings IDs 1 to 15 at 1 Mbps over the UART link, prints each role and input voltage, and exits 0 only when all 15 answer. On this first power-up a servo still on the factory Shutdown 53 reads 7.3 to 7.4 V, above its 7.0 V Max Voltage Limit, so it has latched its input-voltage error and answers with error 0x80. That is expected here, and nothing moves: torque is off after power-up.',
             'Write Shutdown 52 on every servo: python3 set_shutdown.py --port /dev/ttyAS2. Shutdown (address 63) is stored in the servo and can only be written with torque off. The script reads Torque Enable and Shutdown on all 15 first and writes nothing unless every servo answers with torque off; it then writes 52 to each servo that differs, reads all 15 back and ends with "PASS: 15/15 servos read back 52". Shutdown 52 keeps the overload, overheating and electrical-shock cut-outs and drops only the input-voltage one.',
             'Power-cycle: unplug the USB-C cable, wait until the LEDs are dark, plug it in again. This clears the latched errors and starts every servo with Shutdown 52. Then python3 set_shutdown.py --port /dev/ttyAS2 --check ends with "PASS: every servo holds 52".',
             'Then run: python3 check_voltage_limit.py --port /dev/ttyAS2 --rail battery. It only reads. For every servo it prints Max and Min Voltage Limit, Shutdown, Hardware Error Status and the present supply voltage, and ends with PASS when all 15 have a Max Voltage Limit of 7.0 V and Shutdown 52 and all read 6.4 to 8.4 V. HWerr 0x01 on every servo is expected above 7.0 V: it is the input-voltage flag, and Shutdown 52 keeps torque on. A reading under 7.0 V still passes but prints a warning: re-trim #1 to 7.40 V. Use --rail battery on this 7.4 V rail: the default --rail 7v expects the old 6.80 V set point and fails above 7.0 V. Over the wired link both scripts run on the Mac the same way (~/.venvs/microduck-walk/bin/python guide/firmware/pi/set_shutdown.py, then check_voltage_limit.py --rail battery), with openrb_dual_host on the OpenRB.',
             'Wired control from the Mac (walk_wired.py, default --supply auto) arms its battery guard once the servos read 7.2 V or more, which at 7.40 V it does at start; armed, it accepts the flagged status packets, warns under 7.0 V and stops at 6.6 V. If it prints that the guard is not armed, the rail reads under 7.2 V: re-trim #1 to 7.40 V.',
         ],
         checks=['Before any load: #1 OUT 7.35 to 7.45 V and #2 OUT 4.95 to 5.10 V.',
                 'With the loads on: OpenRB J4 7.2 to 7.45 V and A7Z pin 2 to 6 4.9 to 5.1 V.',
                 'scan_bus.py reports 15/15 and every input voltage is 7.2 V or more.',
                 'set_shutdown.py --check after the power-cycle: PASS, every servo holds 52.',
                 'check_voltage_limit.py --rail battery ends with PASS and exit code 0.'],
         warnings=['If anything smells hot or a LED stays off, unplug the USB-C cable from the 5991 first, then investigate.',
                   'If A7Z pin 2 reads more than 5.25 V, unplug at once: the head 5 V lead is on the wrong converter or #2 is set wrong.',
                   'If set_shutdown.py refuses because a servo has torque on, stop every controller, power-cycle and run it again; if a servo does not answer, fix the bus first. Never run the robot on this rail with a servo still on Shutdown 53: above 7.0 V it switches its torque off.',
                   'If a servo shows a Max Voltage Limit below 7.0 V, set it back to 70 (7.0 V) in DYNAMIXEL Wizard (address 32) and power-cycle; check_voltage_limit.py itself never writes.',
                   'If a servo is missing, check its chain cable and its ID; do not reflash or re-ID while two servos share an ID.'],
         links=[bringup('s12', 'Detailed page: power-up, readback and voltage-limit check', 'BRINGUP step 12'),
                here('bench-test', 'Guide: Set the 5991 to 15 V and the two XL4015 to 7.40 V and 5.00 V')])

    step('sensors', 'power-up', 'Check the IMU, camera, Wi-Fi and speaker', show=full, cables=['imu'] + AUDIO_CABLES,
         camera=ctx.cam(['head_cap', 'rear_pack'], direction=(-1.0, 0.8, 0.6), margin=1.1),
         instructions=['IMU: first check that twi_mode says "Current mode is 0: engine" (step Set up the A7Z software); only then run sudo i2cdetect -y -r 7, which shows 4a. python3 imu_read.py 10 7 prints roll, pitch and yaw twice a second for 10 seconds. If 4a is missing or imu_read.py stops with an I2C error, check twi_mode first: in drv mode the bus locks up although the wires are fine. Run the upstream bno08x_calibrate_ui.py; with the robot upright, projected gravity must be near [0, 0, −1]. If not, fix IMU_MOUNT_QUAT before training.',
                       'Camera: ls /dev/video* lists video0 and video1. Radxa\'s checked 1080p source on the A7Z is: gst-launch-1.0 v4l2src device=/dev/video0 en-awisp=1 en-largemode=0 ! video/x-raw,format=NV12,width=1920,height=1080,framerate=30/1. Take one frame from it through the eye and check it is sharp. The picture comes out turned by 90°: rotate it 90° clockwise in software and confirm on that frame that up is up.',
                       'Wi-Fi: with the cap on, iw dev wlan0 link shows the signal level; write it down with the cap off and on (the antenna page explains the check).',
                       'Speaker: with Enable I2S0 on, aplay -l lists the I2S0 card; play a short voice sample to it. This sound path is new on the A7Z and not yet tested on this board.'],
         checks=['IMU, camera and Wi-Fi work with the head cap still loose. Note the result of the speaker test, pass or fail.'],
         links=[a7z('check', 'Antenna page: Wi-Fi signal check', page='A7Z-ANTENNA.html')])

    step('range', 'power-up', 'Range-of-motion check with torque off', show=full,
         camera=ctx.cam(LEGS + ['head_cap'], direction=FRONT, margin=1.0),
         instructions=['With torque off, move every joint by hand from end to end, one at a time.',
                       'Watch every cable at its plug and at each moving joint. Re-dress any loop that tightens.',
                       'Enable torque on one chain at a time (right leg, left leg, neck) and command small moves first.'],
         checks=['No plug is levered and no cable is stretched at any joint extreme.'])

    # Limits (2026-10-14): OpenRB DXL ports 3 A together (ROBOTIS, unchanged); XL4015 #1: chip rated 5 A (XLSEMI datasheet
    # summary), CC/CV modules 3-4 A continuous without a heatsink (probots.co.in,
    # https://probots.co.in/xl4015-5a-constant-current-voltage-led-driver-lithium-battery-charger.html); USB side 15 V x 3 A = 45 W (charger's
    # 15 V offer). The 5991 requests 15 V at 1.25 A operating current (ISet closed; HUSB238 datasheet RDO determination).
    # 2026-10-15 ~17:00: on the 9 V offer (27 W) the first walk command browned out the whole input within 0.5 s
    # (/tmp/duck_wired_log_1015b.jsonl, 7.1 V and 5 deg tilt before the cut), so 15 V is required for walking.
    step('current', 'power-up', 'Measure the servo current through the OpenRB', show=[k for k in full if k not in BOX_LID], cables=['pw-7v'],
         camera=ctx.cam(controller + pack, direction=REAR, margin=1.3),
         instructions=[
             'All servo power passes through XL4015 #1 and then the OpenRB ports. Three limits apply: the OpenRB ports, which ROBOTIS rates at 3 A for all ports together; converter #1, whose XL4015 chip is rated 5 A and whose module runs 3 to 4 A continuously without a heatsink; and the USB side, where the charger gives at most 3 A at 15 V, 45 W for both converters together. 3 A at 7.4 V is about 22 W at the servos, roughly 25 W at the charger after converter losses, plus a few watts for the A7Z, inside 45 W, so the OpenRB rating is the one to watch. The 9 V offer (27 W) is not enough: on 2026-10-15 it browned out the whole robot within half a second of the first walk command. The old simulated walking numbers (2.05 A mean, 5.4 A for 20 ms) were for a 5 V supply; this step measures the real current on the 7 V rail. Do it before the first walk.',
             'With torque on and the robot standing in its default pose, run on the A7Z: python3 current_watch.py --port /dev/ttyAS2 --seconds 60. It reads every servo\'s own current reading 15 times a second, shows the running total and saves all samples to current.csv. It only reads; it moves nothing.',
             'While it runs, press the torso down gently so both legs bend and push back, then let the robot crouch into its lowest pose and stand up again. These are the hardest moments for the leg servos.',
             'Keep the meter on the OpenRB terminal block while you press and crouch: it stays at 7.0 V or more. A sagging USB supply shows here first.',
             'Watch the three small LEDs on XL4015 #1 (the top converter) through the open back of the box. The red one (R) lights when its current limit is cutting in: then turn its current-limit trimmer further clockwise and repeat.',
             'The walking controller uses the same serial port, so current_watch.py cannot run beside it. For the first walk, add the same Present Current read (address 126) to the controller\'s loop and keep the log.',
             'Unplug the USB-C cable and close the rear converter box: the lid pushed straight on and its four M2 × 10 driven through the holes in its back, as in "Close the box with its cap lid".',
         ],
         checks=['current_watch.py ends with "Under 3000 mA apart from bursts shorter than 1.0 s" and exit code 0.',
                 'The red LED on XL4015 #1 stayed dark, and the OpenRB terminal block read 7.0 V or more throughout.',
                 'Touch the OpenRB terminal block, the 7 V pair and XL4015 #1 after the minute: warm is fine, none is too hot to keep a finger on.'],
         warnings=['If the total stays above 3000 mA for a second or more, a part gets too hot to touch, or the supply drops out (the 5991 green LED or the OpenRB PWR light goes out), unplug the USB-C cable and stop. Do not cut the 5991 ISet jumper: with it cut the 5991 asks for 3.25 A, more than the charger\'s 3 A offer at 15 V, and falls back to a lower voltage. Report the log instead.'])

    step('close', 'power-up', 'Screw the head shut', show=full, pose=jaw_pose(30),
         camera=ctx.cam(['head_bottom', 'jaw_frame', 'face_panel'], direction=(1.0, -0.7, -0.9), margin=1.2),
         prepare=[tap(3, 'M2.6 × 6')],
         screwNotes={'M2.6 × 6 TAP': 'Up through a lower-shell tab into a cap boss: two at the front corners, one at the rear. 2.9 mm of thread in the boss. The 4.5 mm head passes through the 5.2 mm holes in the upper lip.'},
         instructions=['Unplug the USB-C cable from the 5991. Lower the populated cap onto the head without screws and watch every plug and wire as the seam closes. If anything presses, lift the cap and re-dress it.',
                       'The white cap is held to the yellow lower shell by three M2.6 × 6, all driven upwards from under the head: two at the front corners and one at the back, centred behind ID14. Each goes through a tab on the lower shell into a boss inside the cap.',
                       'Front pair: hold the jaw 30–35° open by hand. The upper lip is part of the yellow shell; under each front screw it has a 5.2 mm hole, and the driver goes up through that hole. At rest the lower lip covers the holes; opened this far it clears a straight driver path. The jaw meets the shell at about 40°, so do not force it further.',
                       'Rear screw: there are about 70 mm of clear space straight below the rear tab before the torso shells, too short for a full-length screwdriver. Use the compact right-angle driver, or a stubby one. The bundle runs up the right (−Y) side of the neck in its clips and stays clear of the driver path.',
                       'Drive two M2.6 × 6 up through the front tabs and one up through the rear tab into the cap bosses. Stop when each head touches its tab. They also clamp the face, which has no screws of its own.'],
         checks=['The cap seam is closed all round and no wire is caught in it.',
                 'Lift the head gently by the cap: the cap and the lower shell move as one.'])

    step('weigh', 'power-up', 'Close the mouth and weigh the robot', pose=jaw_pose(0, 30),
         camera=ctx.cam(['head_cap', 'face_panel', 'head_bottom'], direction=FRONT, margin=1.1),
         prepare=[{'item': 'Kitchen scale, 0.1 g', 'qty': 1, 'kind': 'tool'}],
         instructions=['Let the jaw close onto the upper lip.',
                       'Weigh the robot and note where it balances. Without the battery the torso is lighter than the training model; record the new mass for the simulation team before training a new policy.'],
         checks=['The mouth closes without force.', 'Mass and balance point are recorded.'])

    # ------------------------------------------------------------------ 11. Battery backpack (D-010)
    # print/back-plate/battery-backpack-20261015/ (README.md, build_bp.py, bp_checks.json): the swap alternative to the rear
    # converter box on the same four cover screws (guide-data 'alternates'). Frame x -67.05..-45 (cover plate x -47..-45),
    # cap x -74.45..-67.05 (V1.20); Swann 39 switch (REV-31-1387 envelope) rocker down in the narrow-tier floor pocket (panel hole, snap wings); DFR1202 behind
    # the front plate (back 2.2 mm off it, pads at the bottom edge, z 10.5..40.5), on two ribs, four clip lips and a VIN stop;
    # Tattu 2S 650 upright behind the switch; plugs 1 and 2 at the battery sides, balance plug on top at -y; plugs 3 (XT30)
    # and 4 (MR30) out of the front plate window (|y| <= 12, z 4.6..9.4) into the pack channel. Cap: three M2 x 6 from the
    # back (y +-27 z 24, y 0 z -26.5), 5.0 mm of thread each. Upper fixing screws through the empty battery space, lower
    # two under the box floor (bp_checks.json screws).
    if ctx.has('battery_backpack_frame'):
        bp_built = ctx.keys('battery_backpack_frame', 'bp_switch', 'bp_dfr1202')
        bp_cam = ctx.cam(ctx.keys('battery_backpack_frame'), direction=(-1.0, -0.45, -0.35), margin=1.35)
        plan = 'build-pack-20260913/power/battery-backpack-20261015/README.md'
        step('bp-switch', 'backpack', 'Snap the switch into the backpack floor, rocker down',
             add=ctx.keys('battery_backpack_frame', 'bp_switch'), show=[], context=[], bench=True,
             approach={'bp_switch': [0, 0, -30]}, camera=bp_cam,
             # the two snap wings (|y| up to 16.22) fold in to pass the 13.75 mm half-width panel hole and spring out above it
             flex={'parts': ['bp_switch'], 'riders': {}, 'ramp': [13.0, 13.75], 'spread': [-2.6, -2.6], 'window': [0.1, 0.97]},
             prepare=[{'item': 'Battery backpack frame (V1.18 print, orange)', 'qty': 1, 'kind': 'printed'},
                      {'item': 'Swann 39 rocker switch with its soldered switch lead (XT30 male to the battery, XT30 female to the feed lead; BATTERY-WIRING.html)', 'qty': 1, 'kind': 'electronic'}],
             instructions=[
                 'Done: the switch sits in the pocket under the narrow bottom part of the box, rocker down and flush with the floor, its body up through the hole in the 3 mm floor panel and held by its own snap wings. Its two leads lie inside the box.',
                 f'This chapter needs the robot-side plugs of the battery plan ({plan}, section 5): a male XT30 servo inlet on OpenRB J4 and a male MR30 on the A7Z lead, with the bench box outputs ending in the matching female plugs. The bench box chapters above wire it straight to J4 and the A7Z; without those plugs the two boxes cannot be swapped.',
                 'Hold the frame upside down. Feed the two switch leads up through the rectangular hole in the floor panel, then push the switch body up after them until both snap wings click over the panel. Press on the switch body, not on the rocker.',
                 'The rocker now faces down, flush in the pocket: on the robot you press it with a finger from below the backpack. Nothing sticks out of the floor.',
             ],
             checks=['Both snap wings sit over the panel and the switch does not move when its leads are pulled.',
                     'The rocker is flush with the pocket rim and switches with a fingertip.'])
        step('bp-dfr', 'backpack', 'Clip the DFR1202 behind the front plate and lead its plugs out of the window',
             add=ctx.keys('bp_dfr1202'), show=ctx.keys('battery_backpack_frame', 'bp_switch'), context=[], bench=True,
             approach={'bp_dfr1202': [-25, 0, 0]}, camera=bp_cam,
             prepare=[{'item': 'DFRobot DFR1202 5 V converter with its feed, servo and 5 V leads soldered to its pads', 'qty': 1, 'kind': 'electronic',
                       'note': f'Leads as in the battery plan ({plan}, steps 4 to 6): feed lead with a male XT30 (plug 2), servo lead with a female XT30 (plug 3), 5 V lead with a female MR30 (plug 4).'},
                      {'item': '2 mm foam pad for the big inductor', 'qty': 1, 'kind': 'other'}],
             instructions=[
                 'Done: the DFR1202 stands against the inside of the front plate, its pads at the bottom edge, its back on two ribs 2.2 mm off the plate, its two long edges clipped by two pairs of flexible lips and its VIN end on a small stop. The servo lead and the 5 V lead leave through the flat window in the front plate under the board; the feed lead waits for the switch.',
                 'Stick the 2 mm foam pad on the big inductor: it rests against the battery later and keeps the board from rattling.',
                 'Before the board goes in, push the servo lead (XT30 female, plug 3) and the 5 V lead (MR30 female, plug 4) through the window in the front plate from inside, about 4 cm out. Mark the red side of the MR30 with its paint dot facing up.',
                 'Hold the board with its pads down and its components towards you, VIN end on the stop side. Slide it in from the open back of the box, straight forward, until its back meets the two ribs; press its long edges past the lips until they click over. Do not bend the lips further than they need.',
                 'Plug the feed lead (plug 2) into the switch\'s female XT30. Lay plug 2 in the space on the left (+Y) side of the battery space; it stays plugged and exists only so the switch can be replaced.',
             ],
             checks=['The board sits on both ribs and all four lips hold its edges; it does not move when tapped.',
                     'Plugs 3 and 4 stand out of the front plate window and no lead is pinched by the board or a lip.'],
             warnings=['Every pad joint carries the servo current: check each one before the board goes in. A cold joint here warms up while the robot walks (D-010 revisit point).'])

        bench_box = [k for k in box if k in installed]
        bp_robot = [k for k in installed if k not in bench_box]
        step('bp-mount', 'backpack', 'Swap the rear converter box for the battery backpack',
             add=bp_built + ctx.keys('bp_swap_plugs'), remove=bench_box, show=bp_robot,
             group={'label': 'Battery backpack frame with the switch and the DFR1202', 'approach': [-40, 0, 0]},
             camera=ctx.cam(ctx.keys('battery_backpack_frame') + pack, direction=REAR, margin=1.3),
             prepare=[tap(4, 'M2 × 6'), {'item': 'A driver no thicker than 3 mm for the two lower screws', 'qty': 1, 'kind': 'tool'}],
             screwNotes={'M2 × 6 TAP': 'Forward through a corner hole of the backpack front plate into the pilot in a pack post, as on the bench box: 2 mm of plate, 4 mm of thread, 0.8 mm of pilot spare past the tip. The upper two are reached straight through the empty battery space, the lower two from behind under the box floor.'},
             instructions=[
                 'Done: the backpack frame sits on the back of the pack in place of the rear converter box, on the same four M2 × 6. Plug 3 (servo, XT30) and plug 4 (A7Z 5 V, MR30) stand mated in the empty pack channel behind the OpenRB, robot half on top. The battery and the cap are not in yet.',
                 'Shut the A7Z down, then unplug the USB-C cable from the bench box.',
                 'Take the bench box off: remove its cap (four M2 × 10), take the top converter off its two lower M2 × 4 and let it hang back on its wires to reach the two upper cover screws, then remove all four cover screws and pull the box about 4 cm back. Unplug the bench box\'s XT30 and MR30 from the robot\'s servo inlet and A7Z lead. Keep the screws.',
                 'Hold the backpack frame about 4 cm behind the pack. Plug the backpack\'s XT30 female (plug 3) onto the robot\'s servo inlet and its MR30 female (plug 4) onto the A7Z lead. XT30 and MR30 cannot be crossed. Stand both plugs in the pack channel, robot half on top.',
                 'Push the frame straight forward until its plate sits on the ends of both pack posts. Nothing may be pinched under the plate; the two leads fold into the channel.',
                 'Drive the two upper M2 × 6 through the empty battery space and the two lower ones from behind, under the box floor. Start all four, then tighten evenly until the heads touch.',
             ],
             checks=['The plate sits flat on the ends of both posts all round.',
                     'Plugs 3 and 4 are fully mated and stand in the channel; nothing presses on the OpenRB.'],
             warnings=['Swap only with the switch off and the A7Z shut down.',
                       'Never plug the bench box\'s XT30 and the battery into the robot at the same time.'])

        step('bp-battery', 'backpack', 'Slide the battery in upright and connect plug 1',
             add=ctx.keys('bp_battery', 'bp_plugs'), group={'label': 'Battery with plug 1 and its balance plug', 'approach': [-40, 0, 0]},
             camera=bp_cam,
             prepare=[{'item': 'Tattu 2S 650 mAh 75C LiPo with XT30, charged and checked (7.0 to 8.4 V)', 'qty': 1, 'kind': 'electronic'}],
             instructions=[
                 'Done: the battery stands upright behind the switch on the floor panel, leads at the top. Plug 1 (battery to switch, XT30) hangs on the robot\'s right (−Y) side of the battery, between the battery and the side wall, and the balance plug sits on top on the same side.',
                 'Switch off. Plug the battery\'s XT30 female onto the switch\'s male lead (plug 1) outside the box.',
                 'Stand the battery upright, leads up and on the right (−Y) side, and slide it straight forward into the box until it rests on the floor panel against the DFR1202 foam pad. Tuck plug 1 and the balance plug into the space between the battery and the right-hand wall.',
             ],
             checks=['The battery stands centred on the floor panel; no lead is under it.',
                     'Plug 1 is fully mated; plug 2 is still mated on the left side.'],
             warnings=['A LiPo is a fire risk if crushed or shorted: never force the battery in, and never pinch its leads or the balance plug.',
                       f'Before the first battery power, follow the battery plan ({plan}): every servo already holds Shutdown 52 from chapter 10 (confirm with set_shutdown.py --check) and the battery guard runs. A full pack is 8.4 V, above the 7.0 V Max Voltage Limit.'])

        step('bp-cap', 'backpack', 'Close the backpack with its cap',
             add=ctx.keys('battery_backpack_cap'), approach={'battery_backpack_cap': [-15, 0, 0]},
             camera=ctx.cam(ctx.keys('battery_backpack_frame', 'battery_backpack_cap'), direction=REAR, margin=1.3),
             prepare=[{'item': 'Battery backpack cap (V1.19 print, orange)', 'qty': 1, 'kind': 'printed'},
                      {'item': '1 mm foam pad for the inside of the cap, behind the battery', 'qty': 1, 'kind': 'other'},
                      tap(3, 'M2 × 8')],
             screwNotes={'M2 × 8 TAP': 'Forward through the three holes in the back of the cap: each head sits on the 3.0 mm floor of a column inside the cap and the screw takes 5.0 mm of thread in the frame boss. Use a driver no thicker than 4 mm.'},
             instructions=[
                 'Done: the cap closes the back of the backpack, held by three M2 × 8 hidden inside it: two high on the sides, one low in the middle. Its two fences keep the battery centred and its foam pad presses the battery forward.',
                 'Stick the 1 mm foam pad inside the cap between the two fences.',
                 'Push the cap straight forward until its edge meets the frame rim all round, with the battery between the fences and no lead under the edge.',
                 'Drive the three M2 × 8 forward through the holes in the back of the cap. Start all three, then tighten until the heads pull the cap firmly against the rim.',
                 'Switch on from below: press the rocker. Read the A7Z input as in the battery plan before the first boot.',
                 'Charging: switch off, remove the three cap screws, take the cap off, slide the battery back out and unplug plug 1 outside the box. The battery is never charged on the robot.',
             ],
             checks=['The cap edge meets the frame rim all round and the cap does not move when pulled backwards.',
                     'The battery does not rattle when the robot is shaken gently.'])

    legend = [
        {'kind': 'dxl', 'color': '#6a3df0', 'label': 'DYNAMIXEL bus (X3P kit cables)'},
        {'kind': 'power-15v', 'color': '#ef6c00', 'label': '15 V feed and link (5991 → XL4015 #2 → #1)'},
        {'kind': 'power-7v', 'color': '#d32f2f', 'label': '7 V servo pair (XL4015 #1 → OpenRB J4, set to 7.40 V)'},
        {'kind': 'power-5v', 'color': '#ad1457', 'label': 'Head 5 V lead (XL4015 #2 → A7Z pins 2 and 6)'},
        {'kind': 'uart', 'color': '#00897b', 'label': 'UART A7Z ↔ OpenRB'},
        {'kind': 'i2c', 'color': '#1e88e5', 'label': 'IMU I²C'},
        {'kind': 'i2s', 'color': '#8e24aa', 'label': 'Amplifier wires (I²S and 5 V)'},
        {'kind': 'speaker', 'color': '#5d4037', 'label': 'Speaker leads'},
        {'kind': 'touch', 'color': '#c87533', 'label': 'Touch wires (copper pads → XIAO → A7Z I²C and 3.3 V)'},
    ]
    return chapters, steps, legend
