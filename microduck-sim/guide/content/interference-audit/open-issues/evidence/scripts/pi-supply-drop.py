# Pi supply screen v2. Ohms, metres. Per-pole series resistance; loop = plus + minus.
R20 = {'22': 0.05296, '24': 0.08422, '26': 0.1339, '28': 0.2129}   # copper ohm/m at 20 C (ASTM B258 solid)
TC = 0.00393; CCA = 1/0.629
def w(g, L, T, cca=False): return R20[g]*L*(1+TC*(T-20))*(CCA if cca else 1)
JOINT = 0.001; CLAMP = 0.003; R_COMMON = 0.015
parts = {  # name: (contact ohm per mated 2.54 mm contact, wire temp C, cca?, 3A fuse ohm)
 'good':     (0.010, 25, False, 0.031),
 'rated':    (0.020, 40, False, 0.035),
 'degraded': (0.050, 40, True,  0.035),
}
def pole(segs, P, plus):
    c, T, cca, fuse = P
    r = fuse if plus else 0.0
    for s in segs:
        k = s[0]
        if k == 'w22': r += w('22', s[1], T)
        elif k == 'jw': r += w(s[1], s[2], T, cca)
        elif k == 'contact': r += c*s[1]
        elif k == 'joint': r += JOINT*s[1]
        elif k == 'clamp': r += CLAMP*s[1]
        elif k == 'par':  # parallel identical branches: ('par', n, [segs])
            r += pole(s[2], P, False)/s[1]
    return r
V = {
 'V0 current guide (22AWG 475mm + soldered 45mm 26AWG tail, 1 contact)':
     [('w22',0.475),('joint',2),('jw','26',0.045),('contact',1)],
 'A1 all-jumper 3x20cm 26AWG Cu (2 inline + header)':
     [('clamp',1),('jw','26',0.60),('contact',3)],
 'A2 all-jumper 3x20cm 28AWG':
     [('clamp',1),('jw','28',0.60),('contact',3)],
 'A3 all-jumper 5x10cm 28AWG (4 inline + header)':
     [('clamp',1),('jw','28',0.50),('contact',5)],
 'A4 all-jumper 2x30cm 26AWG (1 inline + header)':
     [('clamp',1),('jw','26',0.60),('contact',2)],
 'B1 22AWG 100mm to clamp in torso corner + 2x20cm 26AWG':
     [('w22',0.10),('joint',1),('clamp',1),('jw','26',0.40),('contact',2)],
 'B3 B1 with two parallel jumper chains per pole':
     [('w22',0.10),('joint',1),('clamp',1),('par',2,[('jw','26',0.40),('contact',2)])],
 'D1 22AWG 320mm to clamp at hood + one 17cm 26AWG jumper end':
     [('w22',0.32),('joint',1),('clamp',1),('jw','26',0.17),('contact',1)],
 'D2 D1 doubled (two 17cm jumpers per pole)':
     [('w22',0.32),('joint',1),('clamp',1),('par',2,[('jw','26',0.17),('contact',1)])],
 'C1 22AWG 430mm to clamp inside head + one 10cm 26AWG jumper end':
     [('w22',0.43),('joint',1),('clamp',1),('jw','26',0.10),('contact',1)],
 'C2 C1 doubled (two 10cm jumpers per pole, pins 2+4 / 6+14)':
     [('w22',0.43),('joint',1),('clamp',1),('par',2,[('jw','26',0.10),('contact',1)])],
 'C1-28 same as C1 with 28AWG jumper':
     [('w22',0.43),('joint',1),('clamp',1),('jw','28',0.10),('contact',1)],
}
loads = [  # label, I_pi, I_motor, V_dfr
 ('L1 bench: 0.65A, motors off, DFR 5.00', 0.65, 0.0, 5.00),
 ('L2 realistic run: 0.65A, motors 7A, DFR 5.00', 0.65, 7.0, 5.00),
 ('L3 conservative: 0.95A, motors 7A, DFR 4.95', 0.95, 7.0, 4.95),
 ('L4 old allocation: 1.5A, motors 7A, DFR 4.95', 1.5, 7.0, 4.95),
]
print('loads:', '; '.join(l[0] for l in loads))
for name, segs in V.items():
    print(name)
    for pn, P in parts.items():
        p = pole(segs, P, True); m = pole(segs, P, False); R = p+m
        vs = [vd - R_COMMON*(i+im) - R*i for _, i, im, vd in loads]
        print(f'   {pn:9s} loop {R*1e3:6.1f} mOhm  V@pins2-6: ' + '  '.join(f'{v:.2f}' for v in vs))
# loop budgets for 4.75 V
for lab, i, im, vd in loads:
    print(lab, 'max branch loop for 4.75 V:', round((vd - R_COMMON*(i+im) - 4.75)/i*1e3,1), 'mOhm')
# first-power check: Pi booting ~0.3 A, J at 4.95
for name in ('V0 current guide (22AWG 475mm + soldered 45mm 26AWG tail, 1 contact)',):
    for pn,P in parts.items():
        R = pole(V[name],P,True)+pole(V[name],P,False)
        print('first-power pin2-6 with J=4.95, 0.3A:', pn, round(4.95-0.3*R,3))
# heating
for g in ('26','28'):
    for cca in (False, True):
        print(g, 'CCA' if cca else 'Cu', 'W per m at 0.95A:', round(0.95**2*w(g,1,40,cca),3))
