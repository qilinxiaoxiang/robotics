"""Per-object filament grams from an Orca/Elegoo G-code (EXCLUDE_OBJECT_START/END blocks, M83 relative E).
    python3 object_grams.py FILE.gcode [...]   -> JSON on stdout
Material outside object blocks (skirt, purge, wipe tower) is reported as 'unassigned'; per-object values are scaled so
that objects + unassigned equal the slicer header total ('; filament used [g]')."""
import json, math, re, sys

def grams(path):
    dens, dia, total = 1.24, 1.75, None
    cur, sums, un = None, {}, 0.0
    with open(path, errors='ignore') as fh:
        for line in fh:
            if line.startswith('; filament_density'):
                dens = float(re.split(r'[:=]', line, maxsplit=1)[1].split(',')[0])
            elif line.startswith('; filament_diameter'):
                dia = float(re.split(r'[:=]', line, maxsplit=1)[1].split(',')[0])
            elif line.startswith('; filament used [g]'):
                total = float(line.split('=')[1])
            elif line.startswith('EXCLUDE_OBJECT_START'):
                cur = re.search(r'NAME=(\S+)', line).group(1); sums.setdefault(cur, 0.0)
            elif line.startswith('EXCLUDE_OBJECT_END'):
                cur = None
            elif line.startswith(('G1', 'G0', 'G2', 'G3')):
                m = re.search(r'\sE(-?[\d.]+)', line.split(';')[0])
                if m:
                    e = float(m.group(1))
                    if cur: sums[cur] += e
                    else: un += e
    k = math.pi * (dia / 2) ** 2 * dens / 1000.0
    raw = {n: v * k for n, v in sums.items()}; unr = un * k
    s = (total / (sum(raw.values()) + unr)) if total else 1.0
    return {'file': path, 'headerGrams': total, 'objects': {n: round(v * s, 2) for n, v in raw.items()},
            'unassignedGrams': round(unr * s, 2), 'scale': round(s, 4)}

print(json.dumps([grams(p) for p in sys.argv[1:]], indent=1))
