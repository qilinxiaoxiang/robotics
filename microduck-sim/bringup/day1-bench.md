# Day 1: connect everything on the bench, no soldering, measure

Date: 2026-10-10. Goal: power, Pi, camera, IMU, OpenRB and servos talk to a Mac, each from the bench with plug-in connections only; every board and connector is measured; the Pi fit problem in the printed head is seen with the real parts.

Industry step: subsystem bring-up before integration. Software: Raspberry Pi Imager, ssh, DYNAMIXEL Wizard 2.0, Arduino IDE (only if the Wizard does not see the OpenRB).

## Bench kit

Mac with a USB-C port, microSD card and reader, 5 V USB phone charger with a micro-USB cable, USB-A to USB-C cable (Adafruit 4472, in the order), digital caliper, multimeter, small flat screwdriver for screw terminals, female-to-female and male-to-female jumper wires, a few 10 cm pieces of 22 AWG hookup wire stripped at both ends, the Xiaomi charger with its original cable.

## Block 1: Pi alone

1. Raspberry Pi Imager on the Mac: Raspberry Pi OS Lite (32-bit). The Zero W is ARMv6 and runs only 32-bit. In OS customisation set hostname `microduck`, a user, the 2.4 GHz Wi-Fi (the Zero W has no 5 GHz), and enable ssh.
2. Insert the card. Power the Pi from the phone charger into the micro-USB marked PWR IN (the outer one). Wait 90 s. `ssh <user>@microduck.local`.
3. Check: the ssh prompt appears.

Measurements (mm):
- Header pin height above the black plastic: ____ (CAD 5.96)
- Header plastic height above the board: ____
- Board length x width x thickness: ____ x ____ x ____ (datasheet 65 x 30 x 1.6)
- One female jumper sleeve, total length: ____ (expected 13.9 to 14.3)
- Sleeve cross section: ____ x ____ (expected about 2.5 x 2.5)

## Block 2: camera

1. The ordered cable is SC1892 (Raspberry Pi 5 camera cable, 200 mm). It is the Standard-Mini cable: 22-pin mini end into the Pi Zero's camera connector, 15-pin end into the Camera Module 3 Wide, replacing the cable that ships on the camera. Lift the connector latch, insert with the contacts facing the board's contacts, press the latch down.
2. `rpicam-hello --list-cameras` then `rpicam-jpeg -o test.jpg`; copy to the Mac with `scp` and open it.
3. Check: one camera listed, a sharp picture.

Measurements (mm):
- Camera board: ____ x ____; lens height above the board: ____
- Connector plus bent cable height at the Pi: ____

## Block 3: IMU

1. Cable 4397: JST end into either STEMMA QT socket on the BNO085 board. Female ends onto the Pi: red to pin 1 (3V3), black to pin 9 (GND), blue to pin 3 (SDA), yellow to pin 5 (SCL). Pin 1 is the inner-row pin at the microSD end; pin 2 is the edge-row pin beside it.
2. `sudo raspi-config` > Interface Options > I2C > enable. `sudo apt install -y i2c-tools`. `i2cdetect -y 1`.
3. Check: `4a` (or `4b`) appears in the grid.

Measurements (mm):
- IMU board: ____ x ____; height including the JST plug: ____

## Block 4: OpenRB-150 and servos

1. Install DYNAMIXEL Wizard 2.0 for macOS from ROBOTIS. Connect the OpenRB with the USB-C cable. The board ships with the `usb_to_dynamixel` firmware. If the Wizard does not find the board, install Arduino IDE, add the OpenRB-150 board package, and upload File > Examples > OpenRB-150 > usb_to_dynamixel.
2. Servo power. For one or two servos the USB port is enough (it has a 500 mA fuse). For the whole chain use the Adafruit 5991 as a 5 V bench supply: with nothing plugged in, switch ON only the 5V DIP switch, plug in the Xiaomi charger, measure the `+` and `-` screw terminals: 4.9 to 5.2 V. Unplug the charger. Two pieces of 22 AWG wire from `+` and `-` into the OpenRB terminal block, matching polarity. Move the OpenRB power jumper to `VIN(DXL)`. Measure again at the OpenRB terminal before connecting any servo.
   Do not switch the 5991 to any voltage above 5 V while servos are connected. XL330 servos accept 3.7 to 6 V; the terminal block passes the input voltage straight to them.
3. Wizard: Scan, all baud rates, protocol 2.0. Note which IDs answer and their input voltage.
4. Check: every connected servo appears once with its own ID. If several servos share ID 1, connect them one at a time and record each.

Measurements (mm):
- OpenRB board: ____ x ____; tallest component height: ____
- USB-C plug plus 15 mm of cable, length from the board edge: ____
- Terminal block height above the board: ____

Record:
- Servo IDs found: ____
- Input voltage reported by the servos: ____ V
- 5991 output no load: ____ V; with the chain idle: ____ V

## Block 5: speaker and amplifier

The MAX98357A board (Adafruit 3006) ships with its speaker terminal block soldered and an 8-pin header loose. The header needs five minutes of soldering by a helper, once. Until then: measure only.

After the header is on: Vin to Pi pin 4 (5V), GND to pin 14, BCLK to pin 12, LRC to pin 35, DIN to pin 40. Speaker wires into the green terminal block. In `/boot/firmware/config.txt` add `dtoverlay=hifiberry-dac` and change `dtparam=audio=on` to `off`. Reboot. `speaker-test -c2 -t sine -f 440 -l 1`.

Measurements (mm):
- Amplifier board: ____ x ____; height with header and terminal block: ____
- Speaker: ____ x ____ x ____; wire length: ____

## Block 6: the head fit, with the real parts

1. Put the Pi into the V1.6 head cap seat (the four rail bosses). Push a female jumper end onto pin 2 and another onto pin 5.
2. Hold the camera stack in the head bottom where it mounts. Lower the cap straight down as in assembly. Watch where the sleeves touch.
3. Caliper, with the Pi in the cap and the cap seated on the head bottom without the Pi: header plastic face to the nearest camera clamp screw head: ____ (model: about 12). Lowest pin row to the head bottom floor: ____ (model: 0.6).
4. Write what touched first: ____

## Block 7: look at the power parts that still assume soldering

Hold each one and note what its connection actually is:
- DFR1202 converter: pads only, no terminal. Candidate replacement: a 5 V buck converter with screw terminals (links come on day 2).
- XT30 (FIT0586): solder cups. Candidate: pre-wired XT30 pigtails.
- Axial fuses: wire leads. Candidate: inline fuse holders with screw or lever terminals.
- 5991: screw terminal output, no change needed. ISET trace: leave as shipped today; cut it on day 2 after the 5 V test, then confirm no continuity across the two pads.

## End of day

- What worked: ____
- What did not and why: ____
- Numbers that disagree with the CAD: ____
- Decisions for day 2: ____
