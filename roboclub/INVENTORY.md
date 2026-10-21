# RoboClub parts inventory (partial)

Source: 10 photos Shawn took of the RoboClub electronics shelves on 2026-10-20 (`inventory-photos/IMG_7048.jpg` to `IMG_7057.jpg`). Entries are drawer labels as read from the photos, not counted contents; a label can be stale and a drawer can be empty. `?` marks a label that was hard to read. Open the drawer before relying on it.

To request club parts, see the Discord `#i-want-this` channel.

## Cabinet A: small black 20-drawer, modules (IMG_7048)
- Row 1: (unlabelled, acrylic pieces), DC Motor Drivers, USB-C connectors, potentiometers 25k/47k/50k? + ceramic disc caps (handwritten), SD Card Breakouts
- Row 2: RS232 adapters, FTDI USB, Speakers & Transducers, Trinkey (Adafruit), Logic Level Shifters
- Row 3: (unlabelled), LED Drivers, (unlabelled), two drawers covered with velcro (unlabelled)
- Row 4: (unlabelled, wire), Color Sensors / Light Sensors, Active Buzzer, Noods (flexible LED filament)
- On top: servo leads, plastic boxes of loose modules

## Cabinet B: small black 20-drawer, wireless and sensors (IMG_7049)
- Row 1: Misc Stepper Drivers, Pogo Pins, RFID Readers & Tags, 915 MHz LoRa, 900 MHz + LoRa
- Row 2: Current Sensors, (open slot, bags), Bluetooth, XBee, 433 MHz
- Row 3: Relays, (unlabelled, ultrasonic sensor parts), UFL/SMA Adapters, XBees, ISM Antennas
- Row 4: Solid-State Relays, IMU/Accelerometer, NRF24L01 2.4 GHz, XBee Adapters, 915 MHz TRX
- On shelf: RTC module (DS3231-style, blue), ultrasonic sensor HC-SR04

## Cabinet C: 24-drawer, power and microcontroller boards (IMG_7050)
- Row 1: Bucks, Boosts & Buck-Boosts; (unlabelled, potentiometers?); SWD Debug Probe; Power MOSFETs
- Row 2: (bubble wrap, unlabelled); LEDs; 5A Boost; Screens
- Row 3: Diodes; Battery; 3A Buck; 5V/5A Buck
- Row 4: Bluetooth; (unlabelled, modules); Buck-Boosts; Line Sensors
- Row 5: Crystals; Fuses; Fuses; Seeeduino XIAO
- Seeeduino XIAO drawer contents (opened 2026-10-20, IMG_7059): 1 XIAO ESP32-S3 (loose, no bag), 2 XIAO nRF52840 Sense (sealed, 102010469), 3 XIAO SAMD21 (sealed, 102010328), 2 XIAO RP2040 (in round cans), 1 more round can (closed, not identified).
- Row 6: ESP8266; ESP32; Arduino Nano / Arduino Pro; Raspberry Pi Pico (RP2040)

## Cabinet D: 60-drawer, LEDs, transistors, passives (IMG_7051)
- LEDs: white (several drawers), blue, red, red right-angle, green, green right-angle, yellow T1-3/4, orange, orange high-power, RGB, 10-segment LED DIP green, bargraph LED DIP, WS2812B addressable RGB, red square/rectangle, IR emitter 940 nm (LTE-302), RGB LED (common?)
- Diodes: mystery diodes, 1N4002 100 V 1 A
- BJTs: 2N3906 PNP, 2N4403 PNP, TIP29A NPN, TIP31C NPN, TIP142 NPN Darlington, TIP125 PNP Darlington, TIP107 PNP Darlington, 2N4401, PNP (generic), 2N2222A
- FETs: 2N5457 JFET, 2N7000, 2SK2231 N-MOSFET, ZVP2106A P-MOSFET, ZVN3306A N-MOSFET, P-MOSFET 230 mA 45 V (BS250?), IRF9540 P-MOSFET
- Pots: 1K trimpots, 10K pots, 20K, larger pots (measure), knobs
- Electrolytic caps: 0.1 µF, 1 µF, 10 µF, 100 µF, 1000 µF, 3300 µF
- Resistors: 120 Ω, 300 Ω, 4.7K, 6.8K, 10K?, 62K

## Cabinet E: 60-drawer, digital ICs, sensors, analog ICs (IMG_7052)
- Digital: 74AHCT125, SN74HC14N Schmitt inverter, MC14021B 8-bit shift reg, MC14021, LR4098 dual monostable, MAX232 RS232-to-TTL, CD4007, CD4066 quad bilateral switch, 74HC595, CD4013 dual D flip-flop, 74ALS27x, 74ALS273 8x D flip-flop, 74FCT827 10-bit buffer, NE555P timer, LM3914/3916 LED bar driver + STP08DP05, LM331 V-to-F, LM2907 F-to-V, LM567 tone decoder
- Converters and interface: 8-bit SPI/parallel DACs (MCP4801/TLC7524), MAX1110 8-bit ADC, 4-channel I2C ADC, 6N139 optoisolator, CD4053 8-channel analog mux, piezo transducers
- Sensors: breadboard pushbuttons, 8-position DIP switch, thermometer, microphones, IR reflective LED/phototransistor, IR detector (two drawers), PDV-P8103 photoresistor, photoresistors, digital Hall sensors, (Digi-Key bag), LM35DZ temp sensor, analog joystick, rotary encoders, analog/linear Hall, misc atmospheric sensors, carbon monoxide gas sensor, emitter/sensor PCB mount
- Resonators: 4, 6, 10, 20, 24 MHz
- Analog: LM386 audio amp, MCP602 op-amp, LM301 op-amp, LM2903 dual comparator, LF411 (and LM215?), OPA2??/TL071 op-amp, LM108A, LM675T, LM741, LM1458, LM358
- On top: red box of LEDs/headers, clear box

## Cabinet F: 60-drawer, regulators, fuses, diodes, MCUs (IMG_7053)
- Linear regulators: LE33CZ 3.3 V 100 mA, LM1117-3.3 800 mA, MCP1702-5002 5 V 250 mA, LM2931 5 V 100 mA, LM341T-5.0 500 mA, LM1085 3 A adjustable, LM337 negative adj 1.5 A, LM317 1.5 A, LM7808 8 V, 5V regulators, 3.3V regulators
- Switching: LM2574N-5 5 V 0.5 A buck, LM2596 3 A adj buck, HW-045 2 A adj boost, TC7660CPA negative voltage generator, breadboard 5V/3.3V breakout
- Fuses: 250 V 1 A, 250 V 3 A 1/4", 250 V 1.25 A 3AG
- Power resistors (three drawers)
- Diodes: 1N751A 5.1 V Zener, 1N5822 Schottky 40 V 3 A, 1N5400 3 A, 1N4733A 5.1 V Zener, small-signal 100 V 0.2 A, 1N5232B 5.6 V Zener, 3.3 V Zener 500 mW, 3.3 V Zener 1 W, 5.1 V Zener 500 mW, Schottky 45 V 15 A, Schottky 35 V 15 A
- Microcontrollers: PIC16F628-20/P, ATmega? / ATtiny85?, ATtiny861-20PU, PIC16F877, PIC16F73, PIC18F4431, several drawers marked "Microcontroller"
- Lower rows: motor driver section (labels unreadable)

## Cabinet G: 60-drawer, mostly old labels (IMG_7054)
- Readable: LED Mounts, A5984 stepper driver, 250 V 2 A fuse, LMD18200T 3 A motor driver, L297 stepper controller, IR LED T1-3/4, 2N3904?, CAN Bus Transceiver
- Most other drawers have torn or no labels
- On top: box of assorted 5 mm LEDs

## Soldering bench (IMG_7055)
- Drawers: hot-air nozzles + misc; soldering iron tips and handles (Weller ET, T18, Weller NT); flux pens + syringes
- Small boxes: crimp terminals (several), ferrules, DuPont housings, SMD parts?, JST XH housings + crimps, DuPont, JST ZH 1.5 connectors
- Craftsman cabinet: 1/4 W resistors, ceramic capacitors, M2, M2.5, M3 screws, JST XH, M3x10, Q-tips
- Also: breadboards, alligator clips, M-F jumpers, misc surface-mount binder, fume extractor, solder spools, magnetic parts tray

## Cabinet H: red Akro-Mils 44-drawer, connectors (IMG_7056)
- IC sockets: other sockets, 14/16 DIP, 18/28 DIP, 28 DIP wide 0.6", 24 DIP wide 0.6", 32 DIP wide 0.6", 40 DIP, wire-wrap sockets, 24 DIP narrow 0.3", 20? DIP, PCB-mount?
- Terminals: screw terminals up to 12 AWG, small 18-26 AWG screw terminals, 2-pos hoods
- RF and audio: UFL connectors, 3.5 mm audio jack
- Headers: SOT-23 breakouts, 40-pin male?, male 0.1" 90°, round female 0.1", jumpers, square female 0.1", male 0.1" header, Pi header extenders, extra-long headers
- Large drawers: Ethernet connectors, Ethernet connector shells, protoboard, breakouts, **HEATSINKS**, crimpable alligators, weird/special connectors
- HEATSINKS drawer contents (opened 2026-10-20, IMG_7058): aluminium heatsink with 40 mm 4-wire fan (Jetson Nano size), Intel-style stock CPU cooler with copper core and push pins, long black extruded aluminium heatsink bar, large U-shaped aluminium heatsink with mounting nuts, two Cooler Master thermal paste syringes, one brown thermal grease tube, small clear box (contents not checked). No small adhesive heatsink (Pi/Zero size).

## Cabinet I: small blue 13-drawer (IMG_7057)
- 1x battery (two drawers, battery clips/springs), 1x straight headers, 2x straight pins, 1x6 wire header, 1x2 wire header, 1x10 wire header, 1x6 female pin headers, angled headers?, line-sensor holders?, servo mounts, breadboard holders, servo arms
- Beside: box labelled "1x angled headers"

## Reported, location not photographed
- Copper foil tape (Shawn, 2026-10-20).

## Not yet photographed
Other club shelves (tools, motors, filament, bins under the benches) are not in this list.
