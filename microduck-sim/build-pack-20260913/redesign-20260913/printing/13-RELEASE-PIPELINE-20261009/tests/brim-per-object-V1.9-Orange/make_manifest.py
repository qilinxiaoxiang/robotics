"""Scratch per-object brim acceptance manifest from the V1.9 Orange release (copied here; release-V1.9 is read-only).

    /tmp/microduck-cad-venv/bin/python make_manifest.py

Same parts, poses, sources (hash-bound at their original paths), profiles and baseline as release-V1.9/manifest-V1.9.json,
with two changes: releaseKind 'fixture' (can never become RELEASED) and no brim keys in processOverrides. Each part's
objectSettings comes from its rows.json row when set there (with objectSettingsReason); otherwise release_pipeline_v2 applies
the R1 default from the part's tip angle. This is the passthrough a release make_manifest.py needs.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRIM_KEYS = ('brim_type', 'brim_width', 'brim_object_gap')

src = json.loads((HERE / 'source-manifest-V1.9.json').read_text())
rows = {r['key']: r for r in json.loads((HERE / 'source-rows-V1.9.json').read_text())}
m = dict(src, version='V1.9-BRIM-PER-OBJECT-TEST', releaseKind='fixture',
         prototypeScope='Pipeline v2 per-object brim acceptance on the V1.9 Orange plate. Not a release.')
m['processOverrides'] = {k: o for k, o in ({k: {a: b for a, b in v.items() if a not in BRIM_KEYS}
                                             for k, v in src.get('processOverrides', {}).items()}).items() if o}
m['processOverrideReason'] = 'No plate-wide brim: the brim is set per part (objectSettings, R1 default from the tip angle).'
parts = []
for p in src['parts']:
    p = dict(p)
    r = rows[p['key']]
    p.update({k: r[k] for k in ('objectSettings', 'objectSettingsReason') if k in r})   # release template passthrough
    parts.append(p)
m['parts'] = parts
(HERE / 'manifest.json').write_text(json.dumps(m, indent=1) + '\n')
print(json.dumps(dict(processOverrides=m['processOverrides'], explicit=[p['key'] for p in parts if 'objectSettings' in p])))
