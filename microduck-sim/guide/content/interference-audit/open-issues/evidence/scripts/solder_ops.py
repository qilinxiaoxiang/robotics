import json
H='helper'; 
def op(n, step, line, joint, end, cls, alt, cat, note=''):
    return {'op': n, 'step': step, 'stepsPyLine': line, 'joint': joint, 'end': end, 'currentClass': cls,
            'solderFreeAlternative': alt, 'alternativeSource': cat, 'note': note}
ops = []
ops += [op(1,'uart-wires',263,'J12 pad 3 (SERIAL_RX) to wire TX','OpenRB','signal','None that fits. Serial3 on header sockets D13/D14 plus M-F jumper and a one-line firmware change, but measured headroom is 4.4 mm (D13) and 9.3 mm (D14) against about 14 mm for a jumper housing.','helper','Helper solders the cut end of a F-F jumper half so the Pi end is a ready-made sleeve; extend with a M-F jumper.'),
        op(2,'uart-wires',263,'J12 pad 4 (SERIAL_TX) to wire RX','OpenRB','signal','As op 1.','helper')]
ops += [op(3,'pd-tether',280,'5 A fuse lead to 5991 + output','off-robot 20 V','5 A','Clamp the fuse lead in the 5991 screw terminal ("No soldering required!", Adafruit 5991 page).','shawn-parts'),
        op(4,'pd-tether',280,'far fuse lead to red 18 AWG tether','off-robot 20 V','5 A','WAGO 221-412 lever connector in the receiver box.','roboclub-stock'),
        op(5,'pd-tether',282,'XT30 female + cup to red 18 AWG','off-robot 20 V','5 A','Pre-wired XT30 female pigtail joined with WAGO 221-412.','purchase','Otherwise helper.'),
        op(6,'pd-tether',282,'XT30 female - cup to black 18 AWG','off-robot 20 V','5 A','As op 5.','purchase')]
for n,j,c in ((7,'DFR1202 VIN pad to red 18 AWG','20 V 5 A'),(8,'DFR1202 GND pad to black 18 AWG','20 V return'),(9,'DFR1202 5V pad to red 16 AWG','10 A'),(10,'DFR1202 GND pad to black 16 AWG','10 A return')):
    ops.append(op(n,'dfr-leads',297 if n<9 else 298,j,'torso','%s'%c,'None: castellated edge pads only (DFRobot product 2907).','helper'))
ops += [op(11,'dfr-leads',299,'10 A fuse to 25 mm red stub','torso','10 A','WAGO 221-412 (20 A UL); fit in the bay unchecked.','roboclub-stock','Helper if it does not fit.'),
        op(12,'dfr-leads',299,'10 A fuse to red 16 AWG run','torso','10 A','As op 11.','roboclub-stock')]
ops += [op(13,'junction',315,'J+ node (6 conductors)','torso','10 A','WAGO blocks, two per node; modelled J box is 8 x 12 x 6 mm, smaller than one 221-412 (13.1 x 18.6 x 8.3 mm).','helper','Fit trial only.')]
for n,j in ((14,'R feed 3 A fuse to 20 AWG red'),(15,'L feed 3 A fuse to 20 AWG red'),(16,'N feed 3 A fuse to 20 AWG red'),(17,'Pi lead 3 A fuse to 22 AWG red')):
    ops.append(op(n,'junction',315,j,'torso','3 A','WAGO 221-412 per fuse; fit unchecked.','helper','Op 17 is on the Pi-bound wire but at the torso end.'))
ops.append(op(18,'junction',316,'J- node (6 conductors)','torso','10 A return','As op 13.','helper'))
for k,(n,j) in enumerate(((19,'link R VDD'),(20,'link R GND'),(21,'link L VDD'),(22,'link L GND'),(23,'link N VDD'),(24,'link N GND'))):
    ops.append(op(n,'splices',332,j,'torso','3 A','WAGO 221-412 only if X3P conductors are 24 AWG or larger (gauge not published), or insulated butt splices with a ratcheting crimper.','helper','Polarity-critical: reversed feed destroys XL330s.'))
ops += [op(25,'converter-plug',454,'XT30 male + cup to red 18 AWG','torso','20 V 5 A','Pre-wired XT30 male pigtail (15 cm) whose leads the helper solders at ops 7 and 8; saves 2 joints.','purchase'),
        op(26,'converter-plug',454,'XT30 male - cup to black 18 AWG','torso','20 V return','As op 25.','purchase')]
for k,c in enumerate(['red','black','blue','yellow']):
    ops.append(op(27+k,'imu-board',533,'4397 JST-side splice, %s'%c,'mid-cable','signal','Do not cut the 4397; plug M-F extension jumpers into its female sockets.','roboclub-stock'))
for k,c in enumerate(['red','black','blue','yellow']):
    ops.append(op(31+k,'imu-board',533,'4397 socket-side splice, %s'%c,'mid-cable','signal','As ops 27 to 30.','roboclub-stock'))
ops += [op(35,'speaker',753,'speaker + tab','head bench','<0.5 A','Adafruit 4227 speaker with PicoBlade lead; thicker than the 4.2 mm envelope.','purchase','Easy helper joint otherwise.'),
        op(36,'speaker',753,'speaker - tab','head bench','<0.5 A','As op 35.','purchase')]
ops += [op(37,'amp',767,'100 kOhm resistor into GAIN','amplifier','signal','None with the 3006 ("Some soldering is required to attach the header"). Pimoroni Audio Amp SHIM is solder-free but drops the gain resistor and fuse; fit unchecked.','helper'),
        op(38,'amp',767,'100 kOhm resistor into VIN','amplifier','signal','As op 37.','helper')]
for k,w in enumerate(['VIN 24 AWG','GND 24 AWG','BCLK 26 AWG','LRC 26 AWG','DIN 26 AWG']):
    ops.append(op(39+k,'amp',768,'%s wire to amplifier pad'%w,'amplifier','0.5 A' if k<2 else 'signal','Helper solders the supplied 7-pin header; F-F jumpers then run to the Pi with no wire joint.','roboclub-stock','The header itself is helper work.'))
ops += [op(44,'amp',768,'0.5 A fuse, first in-line joint','head','0.5 A','WAGO 222-412 (28 to 12 AWG) on the VIN jumper; bulky in the head.','roboclub-stock','Helper otherwise; it is mid-wire, not at the Pi end.'),
        op(45,'amp',768,'0.5 A fuse, second in-line joint','head','0.5 A','As op 44.','roboclub-stock')]
pins=[(46,1,'IMU red','4397 socket plus M-F extension.'),(47,3,'IMU blue','4397 socket plus M-F extension.'),(48,5,'IMU yellow','4397 socket plus M-F extension.'),(49,9,'IMU black','4397 socket plus M-F extension.'),
      (50,2,'PI red 5 V','22 AWG into the head, lever connector, one cut 26 AWG jumper end (OI-04).'),(51,6,'PI black','As pin 2.'),
      (52,4,'amp VIN','F-F jumper from the helper-soldered amplifier header.'),(53,14,'amp GND','As pin 4.'),(54,12,'BCLK','As pin 4.'),(55,35,'LRC','As pin 4.'),(56,40,'DIN','As pin 4.'),
      (57,8,'UART TX','M-F extension from the jumper half soldered at J12.'),(58,10,'UART RX','As pin 8.')]
for n,p,w,a in pins:
    ops.append(op(n,'gpio',794,'Pin %d, %s'%(p,w),'Pi','3 A branch' if p in (2,6) else ('0.5 A' if p in (4,14) else 'signal'),a,'roboclub-stock','Pi end: must be solder-free (binding constraint).'))
assert [o['op'] for o in ops]==list(range(1,59)), [o['op'] for o in ops]
json.dump(ops, open('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/open-issues/solder-ops.json','w'), indent=1)
from collections import Counter
print(len(ops), Counter(o['alternativeSource'] for o in ops), sum(o['end']=='Pi' for o in ops))
