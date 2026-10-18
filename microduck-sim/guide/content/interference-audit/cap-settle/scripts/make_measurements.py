"""Collect the cap-settle results into ../measurements.json (reads JSON outputs only; no geometry).
Usage: python3 make_measurements.py
"""
import json, hashlib, glob, os
from pathlib import Path

HERE = Path(__file__).resolve().parent; OUT = HERE.parent
ROOT = Path('/Users/xiangzheng/code/robotics/microduck-sim')
USED = [1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 14, 35, 40]
AMP = [4, 12, 14, 35, 40]
NON_AMP = [p for p in USED if p not in AMP]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load(name):
    p = OUT / name
    return json.load(open(p)) if p.exists() else None


m = {'scope': 'MicroDuck head cap settle: female jumper sleeves vs the printed V1.6 and the released V1.7 cap, and the '
              'smallest robust fix (problems P5/P6).',
     'date': '2026-10-10',
     'frame': 'robot frame, mm, x forward, y left, z up; cap-on = populated cap lowered straight down by [0, 0, 40]',
     'criterion': {'rigidMm': 2.0, 'flexibleWireMm': 1.0, 'where': 'along the descent and in the final pose',
                   'method': 'exact triangle-mesh distance (manifold3d min_gap) to exact convex sweeps hull(P, P + [0,0,40])'}}

src = {
    'capV16PrintedWorld': ('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/'
                           'scratchpad/cap-v16-backup/world-head_cap.stl'),
    'capV17World': str(ROOT / 'guide/print/world/head_cap.stl'),
    'candidateWorld': str(ROOT / 'guide/print/candidates/head-cap-idc-seat/head_cap-idc-seat-world.stl'),
    'candidateStlFrame': str(ROOT / 'guide/print/candidates/head-cap-idc-seat/head_cap-idc-seat-stlframe.stl'),
    'candidatePrint': str(ROOT / 'guide/print/candidates/head-cap-idc-seat/head_cap-idc-seat-print.stl'),
    'candidateSupportBlocker': str(ROOT / 'guide/print/candidates/head-cap-idc-seat/pi-positive-y-upper-hole-support-blocker-idc-seat.stl'),
    'guideData': str(ROOT / 'guide/data/guide-data.json'),
    'fullBuildData': str(ROOT / 'guide/data/sources/full-build-data-current.json'),
    'fasteners': str(ROOT / 'guide/content/fasteners.json'),
    'routes': str(ROOT / 'guide/content/routes.json'),
    'steps': str(ROOT / 'guide/content/steps.py'),
    'capSwing': str(ROOT / 'guide/content/interference-audit/cap-swing.json'),
    'approachSearch': str(ROOT / 'guide/content/interference-audit/approach-search.json'),
    'findings': str(ROOT / 'guide/content/interference-audit/findings.json'),
}
m['sources'] = {k: {'path': v, 'sha256': sha(v) if os.path.exists(v) else None} for k, v in src.items()}
m['sources']['capV16PrintedWorld']['note'] = ('byte copy of guide/print/world/head_cap.stl before the V1.7 release '
                                              '(sha 5c22fbf6...); the printed cap')

m['connectorData'] = {
    'accessed': '2026-10-10',
    'singleSleeves': [
        {'part': 'Amphenol FCI Mini-PV 65039-036LF housing', 'lengthMm': '13.85 +-0.13', 'section': '2.39 x 2.54', 'kind': 'drawing',
         'url': 'https://cdn.amphenol-cs.com/media/wysiwyg/files/drawing/65039.pdf', 'matingPinMm': '5.33 to 6.1'},
        {'part': 'Harwin M20-1060100 housing', 'lengthMm': '14.00 +-0.20', 'section': '2.74 x 2.50', 'kind': 'drawing',
         'url': 'https://content.harwin.com/asset/b9496f9a-d89f-420f-aea9-abb4534be02f/DRG-00376-Technical-Drawing-Datasheet-M20-106-pdf.pdf',
         'matingPinMm': '5.50 to 6.30'},
        {'part': 'Pololu 1x1 housing #1900 (generic Dupont)', 'lengthMm': '14.00 +-0.25', 'section': '2.54 x 2.54',
         'kind': 'retailer drawing', 'url': 'https://www.pololu.com/product/1900/pictures'},
        {'part': 'TE Mod IV 925366 (2 positions minimum)', 'lengthMm': '14.2', 'kind': 'drawing'},
        {'part': 'Molex SL 70066 / C-Grid III 90156 / TE MTE 104257 (2 positions minimum)', 'lengthMm': '15.24', 'kind': 'drawing'},
        {'part': 'Molex KK 254 2695 (2 positions minimum, 6.4 mm minimum insertion)', 'lengthMm': '12.7', 'kind': 'drawing'}],
    'realisticSingleSleeveRangeMm': [13.85, 14.25], 'outlierMm': 15.24,
    'wire': {'odRangeMm': [0.89, 1.30], 'sources': ['Alpha Wire 3049 (26 AWG UL1007) 1.30 mm', 'Alpha Wire 3048 (28 AWG) 1.19 mm',
                                                     'Alpha Wire 422807 (28 AWG UL1061) 0.89 mm'],
             'bendGuidance': 'NASA-STD-8739.4A: harness minimum 3 x OD; older NASA workmanship appendix: individual wire '
                             'minimum 2 x OD with 2 x OD straight before the bend; Alpha Wire 10 x OD',
             'modelsUsed': {'tight': 'OD 1.2, inner radius 0.6, bend right at the exit',
                            'nominal': 'OD 1.4, inner radius 1.4, bend right at the exit',
                            'loose': 'OD 1.6, inner radius 2.4, bend right at the exit'},
             'note': 'all three models are tighter than the workmanship guidance (no straight run before the bend), '
                     'so the jumper wire results are optimistic'},
    'idcSockets2x20': [
        {'part': '3M 89140-0101 (centre bump, no strain relief)', 'digikey': 'MKC40A-ND', 'heightMm': '10.5 REF',
         'widthMm': '6.05 body + 1.5 bump on the pin-1 row side', 'lengthMm': 55.4, 'postMinMm': 5.84,
         'url': 'https://multimedia.3m.com/mws/media/22265O/3m-tm-idc-ribbon-cable-socket-891-series-ts0449.pdf'},
        {'part': 'Samtec IDSD-20-D-03.20-G (cable assembly)', 'digikey': '612-IDSD-20-D-03.20-G-ND', 'heightMm': '9.27 REF',
         'widthMm': '5.08, no key', 'lengthMm': 52.3, 'insertionDepthMm': '5.59 to 6.22', 'note': 'non-standard, non-returnable',
         'url': 'https://suddendocs.samtec.com/catalog_english/idsd.pdf'},
        {'part': 'Amphenol FCI 71600-040LF', 'digikey': '609-1744-ND', 'heightMm': '10.6 without strain relief; 14.2 to 16.8 with',
         'widthMm': '6.2 MAX + 1 mm key', 'note': 'the -040LF code was read as including a standard strain relief (not re-checked); 35-week lead time',
         'url': 'https://cdn.amphenol-cs.com/media/wysiwyg/files/drawing/71600.pdf'},
        {'part': 'TE AMP-LATCH Novo 1658622-9', 'digikey': 'AKC40B-ND', 'heightMm': '11.79 +-0.25', 'widthMm': '6.10 housing, 7.49 overall',
         'note': 'too tall for the 2 mm criterion on the candidate seat'},
        {'part': 'Wurth WR-BHD 61204023021', 'digikey': '732-5448-ND', 'heightMm': 'about 16 with its strain relief',
         'note': 'strain relief included, too tall'},
        {'part': 'Adafruit 1988 GPIO ribbon cable (listing only)', 'heightMm': 'not published; generic FC-40 listing 55.6 x 6 x 10.5',
         'url': 'https://www.adafruit.com/product/1988'}],
}

# ---- row numbering finding
ig = load('inspect-geometry.json')
if ig:
    m['rowNumberingFinding'] = {
        'cad': ig['rows'],
        'statement': 'In the CAD and in the guide-data per-pin envelopes, pin 1 sits 2.23 mm from the PCB header edge and '
                     'pin 2 4.77 mm from it, so the odd row runs along the board edge. A real Pi has the even row along '
                     'the edge (pin 1 on the inner row); guide/content/steps.py already says so in step gpio. All per-pin '
                     'results here use the real (physical) rows.'}

# ---- jumper sweeps (V1.6, V1.7), physical numbering
def phys_key(p):
    k = (p + 1) // 2
    return f'col{k:02d}-' + ('low' if p % 2 == 0 else 'high')

for tag, fname in [('V1.6', 'sleeve-sweep-dx0.json'), ('V1.7', 'sleeve-sweep-dx4.6.json')]:
    d = load(fname)
    if not d:
        continue
    pos = list(d['positions'].values())[0]
    rows = {}
    for p in USED:
        r = pos[phys_key(p)]
        nominal = {k: v['Lmax1mm'] for k, v in r['wires'].items()}
        rows[str(p)] = {'LmaxTouch': r['LmaxTouch'], 'Lmax2mm': r['Lmax2mm'], 'sleeveGapCurve': r['sleeveGap'],
                        'wireLmax1mmByModel': nominal}
    m.setdefault('jumperLengthSweeps', {})[tag] = {'source': fname, 'perPhysicalPin': rows}

jf = load('jumper-final.json')
if jf:
    summ = {}
    for ver, v in jf['versions'].items():
        pins = v['pins']
        def worst(pset, L):
            g = [(pins[str(p)]['sleeve'][str(L)][0], p, pins[str(p)]['sleeve'][str(L)][1]) for p in pset]
            return min(g)
        def worst_wire(pset, L, model):
            g = [(pins[str(p)]['wire'][str(L)][model]['best'][1], p, pins[str(p)]['wire'][str(L)][model]['best'][0],
                  pins[str(p)]['wire'][str(L)][model]['best'][2]) for p in pset]
            return min(g)
        s = {}
        for lab, pset in [('all13', USED), ('withoutAmplifierPins', NON_AMP)]:
            s[lab] = {'sleeveWorst': {L: worst(pset, L) for L in jf['lengths']},
                      'wireWorstBestDirection': {L: {mdl: worst_wire(pset, L, mdl) for mdl in jf['wireModels']} for L in jf['wireLengths']}}
        summ[ver] = s
    m['jumperDeciding'] = {'source': 'jumper-final.json', 'format': '[gapMm, physicalPin, governingPart] (wire: [gap, pin, '
                                                                     'bend, part])', 'summary': summ}

wi = load('sleeve-sweep-dx4.6-no-retainer-screws.json')
if wi:
    pos = list(wi['positions'].values())[0]
    m['whatIfNoRetainerNoScrewsV17'] = {p: {'LmaxTouch': pos[phys_key(p)]['LmaxTouch'], 'Lmax2mm': pos[phys_key(p)]['Lmax2mm'],
                                            'wireLmax1mm': {k: v['Lmax1mm'] for k, v in pos[phys_key(p)]['wires'].items()}}
                                        for p in USED}

for name in ['block-sweep.json', 'idc-study-a.json', 'idc-study-b.json', 'idc-study-chosen.json',
             'idc-study-chosen-fullribbon.json', 'idc-fold.json',
             'candidate-build-dx3.3-dz2.0.json', 'verify-v18-dx3.3-dz2.0.json', 'routes-v18-dx3.3-dz2.0.json',
             'descent-rails.json', 'static-pi.json', 'probe-added.json', 'probe-web.json', 'shell-overlap.json',
             'path-check-dx4.6-L14.0.json', 'path-check-dx0.0-L14.0.json', 'extract-report.json']:
    d = load(name)
    if d is not None:
        if isinstance(d, dict):
            d = {k: v for k, v in d.items() if k not in ('solidProvenance',)}
        m.setdefault('results', {})[name] = d

# +y rail neck (between the lower screw boss and the roof): rectangular-section approximation from the cap sections
rn = load('rail-neck.json')
if rn:
    neck = {}
    for lab in ('V1.6', 'V1.7', 'candidate'):
        secs = rn[lab]['sectionsAreaXminXmax']
        rows = []
        for z, (area, x0, x1) in sorted(secs.items(), key=lambda kv: float(kv[0])):
            if area <= 0 or area > 30:
                continue
            rows.append((float(z), area, x0, x1))
        # neck = the thinnest section above the boss (first z after the boss where the section drops below 10 mm2)
        boss_end = next(z for z, a, x0, x1 in rows if z > 118 and a < 10.0)
        col = [(z, a, x0, x1) for z, a, x0, x1 in rows if boss_end <= z <= boss_end + 9.0]
        zmin, amin, x0, x1 = min(col, key=lambda r: r[1])
        bx = amin / 3.2
        neck[lab] = {'zMm': zmin, 'areaMm2': amin, 'xExtent': [x0, x1], 'thicknessXmm': round(bx, 2), 'widthYmm': 3.2,
                     'sectionModulusAboutXmm3': round(bx * 3.2 ** 2 / 6, 2), 'sectionModulusAboutYmm3': round(3.2 * bx ** 2 / 6, 2)}
    m['plusYRailNeck'] = {'source': 'rail-neck.json', 'note': 'thinnest +y rail section between the lower (E-pi-02) boss '
                          'and the roof; the boss hangs from this column, so it carries the screw-driving torque. Section '
                          'moduli use a 3.2 mm (y) rectangle; about x = torque about the screw axis.', 'perCap': neck}

runs = {}
for f in sorted(glob.glob(str(OUT / 'runs/run-*.json'))):
    r = json.load(open(f))
    runs[Path(f).name] = {k: r.get(k) for k in ('command', 'exitCode', 'stoppedByGuard', 'elapsedSeconds', 'peakSampledTreeRssMiB', 'maxMiB')}
m['runs'] = runs
m['runner'] = ('python3 build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py --max-mib 1536 '
               '--wait-lock-seconds 60 --seconds 900 --report runs/run-<name>.json -- /tmp/microduck-cad-venv/bin/python scripts/<script>')
json.dump(m, open(OUT / 'measurements.json', 'w'), indent=1)
print('wrote', OUT / 'measurements.json', len(json.dumps(m)) // 1024, 'KiB')
