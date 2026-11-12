"""Single source of truth for the MicroDuck head USB board (contract: ../DESIGN-CONTRACT.json).

One USB cable from the A7Z enters at J_UP. A CH334F hub splits it into the camera (J_CAM) and an RP2040.
The RP2040 is the USB sound card: it clocks three INMP441 microphones and a MAX98357A amp over I2S, and reads the
touch XIAO over I2C (the XIAO stays an I2C slave at 0x2A) to forward it over the same USB cable.

Pin numbers and circuit values come from (read 2026-11-12, quotes in ../HANDOFF.md):
  RP2040   Raspberry Pi "Hardware design with RP2040" minimal design + datasheet Table 615
  CH334F   WCH CH334/335 datasheet V3.0 Table 1-3 and section 6; Adafruit CH334F breakout schematic
  MAX98357A  datasheet 19-6779 Rev 7 pin description, Tables 5, 6, 8; Adafruit 3006 schematic (SD_MODE 1M to VDD, GAIN open)
  INMP441  datasheet DS-INMP441-00 Rev 1.1 (64 SCK per frame, 100k pull-down on a shared SD line)
From memory, to be checked against the part datasheet before layout: AP2112K-3.3 pinout, W25Q16JV USON-8 pinout.

Open items carried on the sheet as OPEN_* values:
  X1 load: the reference design is tuned for a 10 pF crystal (ABM8-272-T3); the JLCPCB basic 12 MHz 3225 is 20 pF.
"""

TITLE = "MicroDuck head USB board: hub + USB sound card + amp, one USB cable across the neck (draft 1, 2026-11-12)"

KINDS, GROUPS, PREFIX = {}, {}, {"R": "R", "C": "C", "FB": "FB", "XTAL": "X", "TP": "TP"}


def part(group, ref, kind, value, pins):
    """pins: [(number or None, name, side L/R, net or None)]"""
    shape = [(n, nm, s) for n, nm, s, _ in pins]
    if KINDS.setdefault(kind, shape) != shape:
        raise SystemExit(f"{ref}: kind {kind} defined twice with different pins")
    key = lambda n, nm: f"{n}_{nm}" if n is not None else nm
    GROUPS.setdefault(group, []).append((ref, kind, value, {key(n, nm): net for n, nm, _, net in pins}))


def two(group, ref, kind, value, a, b):
    part(group, ref, kind, value, [(None, "1", "L", a), (None, "2", "R", b)])


def tp(group, ref, net):
    part(group, ref, "TP", "pad", [(None, "1", "L", net)])


def conn(group, ref, value, nets, names=None):
    n = len(nets)
    PREFIX[f"CONN{n}"] = "J"
    part(group, ref, f"CONN{n}", value, [(i + 1, "P", "L", net) for i, net in enumerate(nets)])


# ---------------------------------------------------------------- power
part("POWER", "U4", "AP2112K-3.3", "AP2112K-3.3 C51118", [
    (1, "VIN", "L", "VBUS"), (3, "EN", "L", "VBUS"), (2, "GND", "L", "GND"),
    (5, "VOUT", "R", "+3V3"), (4, "NC", "R", None)])
two("POWER", "C1", "C", "10uF", "VBUS", "GND")
two("POWER", "C2", "C", "10uF", "+3V3", "GND")
two("POWER", "C3", "C", "10uF", "+3V3", "GND")

# ---------------------------------------------------------------- USB hub
part("USB_HUB", "U1", "CH334F", "CH334F C5187527", [
    (19, "V5", "L", "VBUS"), (20, "VDD33", "L", "HUB_3V3"), (0, "EP_GND", "L", "GND"),
    (4, "XI", "L", "HUB_XI"), (3, "XO", "L", "HUB_XO"),
    (16, "RESET#", "L", None), (18, "PSELF", "L", None), (1, "OVCUR#", "L", None), (24, "PWREN#", "L", None),
    (2, "NC", "L", None), (17, "NC2", "L", None),
    (15, "DPU", "R", "UP_DP"), (14, "DMU", "R", "UP_DM"),
    (12, "DP1", "R", "MCU_DP"), (11, "DM1", "R", "MCU_DM"),
    (10, "DP2", "R", "CAM_DP"), (9, "DM2", "R", "CAM_DM"),
    (8, "DP3", "R", None), (7, "DM3", "R", None), (6, "DP4", "R", None), (5, "DM4", "R", None),
    (22, "LED1", "R", None), (23, "LED2", "R", None), (13, "LED3", "R", None), (21, "LED4", "R", None)])
two("USB_HUB", "X2", "XTAL", "12MHz 3225 (no load caps)", "HUB_XI", "HUB_XO")
two("USB_HUB", "C4", "C", "1uF", "VBUS", "GND")
two("USB_HUB", "C5", "C", "10uF", "HUB_3V3", "GND")
two("USB_HUB", "C6", "C", "100nF", "HUB_3V3", "GND")

# ---------------------------------------------------------------- MCU
part("MCU", "U2", "RP2040", "RP2040 C2040", [
    (1, "IOVDD", "L", "+3V3"), (10, "IOVDD", "L", "+3V3"), (22, "IOVDD", "L", "+3V3"), (33, "IOVDD", "L", "+3V3"),
    (42, "IOVDD", "L", "+3V3"), (49, "IOVDD", "L", "+3V3"), (48, "USB_VDD", "L", "+3V3"), (43, "ADC_AVDD", "L", "+3V3"),
    (44, "VREG_VIN", "L", "+3V3"), (45, "VREG_VOUT", "L", "+1V1"), (23, "DVDD", "L", "+1V1"), (50, "DVDD", "L", "+1V1"),
    (57, "GND", "L", "GND"), (19, "TESTEN", "L", "GND"),
    (20, "XIN", "L", "XIN"), (21, "XOUT", "L", "XOUT"),
    (26, "RUN", "L", "RUN"), (24, "SWCLK", "L", "SWCLK"), (25, "SWD", "L", "SWDIO"),
    (47, "USB_DP", "L", "RP_DP"), (46, "USB_DM", "L", "RP_DM"),
    (56, "QSPI_SS", "L", "QSPI_SS"), (52, "QSPI_SCLK", "L", "QSPI_SCLK"), (53, "QSPI_SD0", "L", "QSPI_SD0"),
    (55, "QSPI_SD1", "L", "QSPI_SD1"), (54, "QSPI_SD2", "L", "QSPI_SD2"), (51, "QSPI_SD3", "L", "QSPI_SD3"),
    (2, "GPIO0", "R", "DBG_TX"), (3, "GPIO1", "R", None), (4, "GPIO2", "R", None), (5, "GPIO3", "R", None),
    (6, "GPIO4", "R", "TOUCH_SDA"), (7, "GPIO5", "R", "TOUCH_SCL"),
    (8, "GPIO6", "R", None), (9, "GPIO7", "R", None), (11, "GPIO8", "R", None), (12, "GPIO9", "R", None),
    (13, "GPIO10", "R", "MIC_SCK"), (14, "GPIO11", "R", "MIC_WS"),
    (15, "GPIO12", "R", "MIC_SD_EARS"), (16, "GPIO13", "R", "MIC_SD_BACK"),
    (17, "GPIO14", "R", None), (18, "GPIO15", "R", None), (27, "GPIO16", "R", None), (28, "GPIO17", "R", None),
    (29, "GPIO18", "R", "SPK_BCLK"), (30, "GPIO19", "R", "SPK_LRC"), (31, "GPIO20", "R", "SPK_DIN"),
    (32, "GPIO21", "R", None), (34, "GPIO22", "R", None), (35, "GPIO23", "R", None), (36, "GPIO24", "R", None),
    (37, "GPIO25", "R", "LED"), (38, "GPIO26", "R", None), (39, "GPIO27", "R", None), (40, "GPIO28", "R", None),
    (41, "GPIO29", "R", None)])
two("MCU", "R3", "R", "27R", "RP_DP", "MCU_DP")
two("MCU", "R4", "R", "27R", "RP_DM", "MCU_DM")
two("MCU", "X1", "XTAL", "12MHz OPEN_CL", "XIN", "XTAL_B")
two("MCU", "R5", "R", "1k", "XOUT", "XTAL_B")
two("MCU", "C7", "C", "15pF", "XIN", "GND")
two("MCU", "C8", "C", "15pF", "XTAL_B", "GND")
two("MCU", "R6", "R", "1k", "LED", "LED_A")
two("MCU", "D1", "LED", "0603 LED", "LED_A", "GND")
PREFIX["LED"] = "D"

part("FLASH", "U3", "W25Q16JV", "W25Q16JVUXIQ C2843335", [
    (1, "CS#", "L", "QSPI_SS"), (6, "CLK", "L", "QSPI_SCLK"), (5, "DI_IO0", "L", "QSPI_SD0"), (2, "DO_IO1", "L", "QSPI_SD1"),
    (3, "WP#_IO2", "R", "QSPI_SD2"), (7, "HOLD#_IO3", "R", "QSPI_SD3"), (8, "VCC", "R", "+3V3"), (4, "GND", "R", "GND")])
two("FLASH", "R1", "R", "1k", "QSPI_SS", "BOOT")
two("FLASH", "R2", "R", "10k DNF", "QSPI_SS", "+3V3")
two("FLASH", "C9", "C", "100nF", "+3V3", "GND")
tp("FLASH", "TP1", "BOOT")
tp("FLASH", "TP2", "GND")

for i, net in enumerate(["+3V3"] * 8 + ["+1V1"] * 2):
    two("MCU_DECOUPLING", f"C{10 + i}", "C", "100nF", net, "GND")
two("MCU_DECOUPLING", "C20", "C", "1uF", "+3V3", "GND")
two("MCU_DECOUPLING", "C21", "C", "1uF", "+1V1", "GND")

for ref, net in (("TP3", "SWCLK"), ("TP4", "SWDIO"), ("TP5", "RUN"), ("TP6", "DBG_TX"), ("TP7", "GND")):
    tp("DEBUG_PADS", ref, net)

# ---------------------------------------------------------------- audio out
part("AMP", "U5", "MAX98357A", "MAX98357AETE+T C910544", [
    (7, "VDD", "L", "VBUS"), (8, "VDD", "L", "VBUS"),
    (16, "BCLK", "L", "SPK_BCLK"), (14, "LRCLK", "L", "SPK_LRC"), (1, "DIN", "L", "SPK_DIN"),
    (4, "SD_MODE", "L", "AMP_SD"), (2, "GAIN_SLOT", "L", None),
    (9, "OUTP", "R", "AMP_P"), (10, "OUTN", "R", "AMP_N"),
    (3, "GND", "R", "GND"), (11, "GND", "R", "GND"), (15, "GND", "R", "GND"), (17, "EP", "R", "GND"),
    (5, "NC", "R", None), (6, "NC", "R", None), (12, "NC", "R", None), (13, "NC", "R", None)])
two("AMP", "R7", "R", "1M", "AMP_SD", "VBUS")
two("AMP", "C22", "C", "10uF", "VBUS", "GND")
two("AMP", "C23", "C", "100nF", "VBUS", "GND")
two("AMP", "C24", "C", "22uF", "VBUS", "GND")
two("AMP", "FB1", "FB", "ferrite 0603", "AMP_P", "SPK_P")
two("AMP", "FB2", "FB", "ferrite 0603", "AMP_N", "SPK_N")
two("AMP", "C25", "C", "220pF", "SPK_P", "GND")
two("AMP", "C26", "C", "220pF", "SPK_N", "GND")
conn("AMP", "J_SPK", "screw terminal 2P: speaker", ["SPK_P", "SPK_N"])

# ---------------------------------------------------------------- microphones and touch
MIC = ["+3V3", "GND", "MIC_SCK", "MIC_WS"]
conn("MICS", "J_EAR_R", "socket 1x5 2.54: right ear", MIC + ["MIC_SD_EARS"])
conn("MICS", "J_EAR_L", "socket 1x5 2.54: left ear", MIC + ["MIC_SD_EARS"])
conn("MICS", "J_BACK", "socket 1x5 2.54: back mic", MIC + ["MIC_SD_BACK"])
conn("MICS", "J_BACK_SD", "pin 1x1 2.54: back SD", ["MIC_SD_BACK"])
two("MICS", "R8", "R", "100k", "MIC_SD_EARS", "GND")
two("MICS", "R9", "R", "100k", "MIC_SD_BACK", "GND")
two("MICS", "C27", "C", "1uF", "+3V3", "GND")

conn("TOUCH", "J_TOUCH", "pins 1x3 2.54: XIAO GND SCL SDA", ["GND", "TOUCH_SCL", "TOUCH_SDA"])
conn("TOUCH", "J_TOUCH_3V3", "socket 1x1 2.54: XIAO 3V3", ["+3V3"])
two("TOUCH", "R10", "R", "2.2k", "TOUCH_SDA", "+3V3")
two("TOUCH", "R11", "R", "2.2k", "TOUCH_SCL", "+3V3")

# ---------------------------------------------------------------- USB connectors
# Same circuit numbering as the U20CAM's own socket, so its factory cable mates with J_UP as it mates with the camera:
# circuit 1 shield (silk G), 2 GND (G), 3 D+ (P), 4 D- (M), 5 5 V (V). Evidence in HANDOFF.md, 2026-11-12 pin order.
USB5 = lambda dp, dm: ["GND", "GND", dp, dm, "VBUS"]
conn("USB_PLUGS", "J_UP", "PicoBlade 5P: to A7Z (1 shield .. 5 5V)", USB5("UP_DP", "UP_DM"))
conn("USB_PLUGS", "J_CAM", "PicoBlade 5P: camera (1 shield .. 5 5V)", USB5("CAM_DP", "CAM_DM"))

ROWS = [["USB_PLUGS", "USB_HUB", "POWER"],
        ["MCU", "FLASH", "DEBUG_PADS"],
        ["MCU_DECOUPLING"],
        ["AMP", "MICS", "TOUCH"]]
