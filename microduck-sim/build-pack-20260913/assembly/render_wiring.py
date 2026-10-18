from pathlib import Path
import html
H=Path(__file__).resolve().parent;O=H/'images'
def doc(w,h,title,sub):return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto-start-reverse"><path d="M0 0L8 4L0 8" fill="context-stroke"/></marker></defs><rect width="100%" height="100%" fill="#f8fafc"/><g font-family="PingFang SC,Arial,sans-serif"><text x="65" y="75" font-size="40" fill="#132b43">{title}</text><text x="65" y="126" font-size="23" fill="#50647b">{sub}</text>']
def line(s,pts,c='#de654c',width=4):
 marker='' if c=='#d99825' else ' marker-end="url(#arr)"'
 s.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{c}" stroke-width="{width}"{marker}/>')
def txt(s,x,y,t,size=23,c='#132b43'):s.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{c}">{html.escape(t)}</text>')
def box(s,x,y,w,h,title,sub='',col='#e7eff5'):
 s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{col}" stroke="#c0ceda"/>');txt(s,x+20,y+34,title,25)
 if sub:txt(s,x+20,y+68,sub,19,'#50647b')
s=doc(1800,1610,'Wiring A · Eight fused groups, 15 independent servo feeds','Electrical diagram: red = positive, black = common ground. Follow WIRING.md; flexible cable routes are not validated.')
box(s,60,190,330,90,'2S battery / EC2','Main disconnect: EC2','#fff0cb');line(s,[(390,220),(500,220)]);box(s,500,180,290,85,'F0 · 10A','Near battery positive entry','#ffe3d7')
line(s,[(790,220),(850,220),(850,360),(410,360),(410,400)]);box(s,70,400,680,95,'D42V110F5 · Servo 5V','VIN in; VOUT to servos only. Never join the two VOUT rails.')
line(s,[(850,220),(850,430),(970,430)]);box(s,970,395,250,85,'F9 · 3A','Logic regulator VIN','#ffe3d7');line(s,[(1220,438),(1280,438)]);box(s,1280,395,360,85,'S13V30F5 · Logic 5V','Pi / OpenRB / audio')
line(s,[(1640,438),(1690,438),(1690,542),(1240,542)]);box(s,970,508,270,85,'Pi PWR IN','20AWG≤200mm')
line(s,[(1690,542),(1690,655),(1510,655)]);box(s,1190,617,320,85,'F10 · 0.5A → Amp','Protects the audio branch','#eee3f2')
line(s,[(650,495),(650,545)],'#3389b7');box(s,455,545,460,115,'Servo switch: ENA / GND','Center to ENA; one outer pin to GND.','#e0edf5');txt(s,475,642,'Leave ENB, PFM and PG open.',19)
line(s,[(410,495),(410,1432)]);txt(s,70,730,'Servo 5V positive star',27)
groups=[('F1','1 Right ankle','2 Right knee'),('F2','3 Right hip pitch','4 Right hip roll'),('F3','5 Right hip yaw','10 Left hip yaw'),('F4','6 Left ankle','7 Left knee'),('F5','8 Left hip pitch','9 Left hip roll'),('F6','11 Head pitch','12 Neck pitch'),('F7','13 Head yaw','14 Head roll'),('F8','15 Jaw','')]
for i,(f,a,b) in enumerate(groups):
 y=780+i*83;box(s,465,y,230,60,f+' · 3A',col='#ffe3d7');line(s,[(410,y+30),(465,y+30)]);line(s,[(695,y+30),(840,y+30)]);txt(s,717,y+23,'20AWG',18)
 box(s,850,y,330,60,'ID '+a,col='#e0edf5')
 if b:line(s,[(825,y+30),(825,y+67),(1220,y+67),(1220,y+30),(1260,y+30)]);box(s,1260,y,330,60,'ID '+b,col='#e0edf5')
 txt(s,70,y+34,'Power group '+str(i+1),21,'#50647b')
line(s,[(60,235),(25,235),(25,1540),(1650,1540)],'#303f4e');txt(s,280,1525,'Common ground: both regulators, OpenRB, each Y split and each servo Pin1 return here.',25)
txt(s,580,1490,'Fused Y split: one power pair per servo. No VDD/GND between servos.',23)
s.append('</g></svg>');(O/'wiring-power.svg').write_text(''.join(s))
s=doc(1800,1500,'Wiring B · DATA bus and Pi pin assignments','Pin numbers are logical assignments, not connector viewing directions. Verify manufacturer pinout and continuity.')
box(s,65,200,470,110,'Pi 3 / Pi Zero (gen 1)','Zero baseline; board unverified','#e3f0e9');line(s,[(535,245),(730,245)],'#3389b7');box(s,730,200,360,110,'OpenRB-150','USB-C powers board logic only','#e0edf5')
txt(s,570,220,'USB data cable',21,'#3389b7');txt(s,1130,228,'DXL: Pin1 → common ground',23);txt(s,1130,266,'Pin2 VDD → remove terminal; insulate',23,'#b74b34');txt(s,1130,304,'Pin3 DATA → shared bus below',23)
line(s,[(910,310),(910,370),(125,370),(125,440)],'#d99825')
order=[15,14,13,11,12,10,5,4,3,2,1,6,7,8,9]
for i,id in enumerate(order):
 row=i//5;col=i%5;x=65+col*338;y=440+row*145;box(s,x,y,235,80,'ID '+str(id),'Pin3 DATA','#fff0cb')
 if col<4:line(s,[(x+235,y+40),(x+338,y+40)],'#d99825')
 elif i<14:line(s,[(x+235,y+40),(x+275,y+40),(x+275,y+110),(40,y+110),(40,y+185),(65,y+185)],'#d99825')
txt(s,65,880,'One DATA wire: commands and replies alternate; servos respond by ID, without forwarding.',24)
txt(s,65,923,'Each input also gets its own Pin1 GND and Pin2 5V. The next-servo output retains Pin3 only.',26)
txt(s,65,968,'Order is a routing candidate, not a requirement. Power groups remain as in A; do not daisy-chain servo power.',22,'#50647b')
box(s,65,1010,790,310,'Pi → MAX98357A amplifier / I²S audio',col='#eee3f2')
for i,t in enumerate(['Physical12 / GPIO18 → BCLK','Physical35 / GPIO19 → LRC','Physical40 / GPIO21 → DIN','VIN → logic 5V after F10; GND → logic ground','OUT+/OUT− → speaker; neither output is ground']):txt(s,90,1088+i*43,t,24)
box(s,915,1010,815,310,'Pi → BNO085 orientation sensor / I²C',col='#dff1f0')
for i,t in enumerate(['Physical1 / 3.3V → VIN','Physical6 / GND → GND','Physical3 / GPIO2 → SDA','Physical5 / GPIO3 → SCL','STEMMA QT cable; 3Vo is not VIN']):txt(s,940,1088+i*43,t,24)
txt(s,65,1390,'Zero reference CSI: 22-pin ↔ 15-to-22 cable ↔ camera. Confirm selected Pi connector first.',26)
txt(s,65,1440,'The alarm uses the battery balance port; it is separate from the I²S duck-call speaker.',25,'#50647b')
s.append('</g></svg>');(O/'wiring-signals.svg').write_text(''.join(s))
