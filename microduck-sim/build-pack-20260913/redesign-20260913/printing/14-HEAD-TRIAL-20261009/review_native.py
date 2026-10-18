"""Read the exported machine toolpaths; do not alter source or slices."""
import json, sys
from pathlib import Path

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D.parent / '13-RELEASE-PIPELINE-20261009'))
import release_pipeline as rp

prep = rp.read(D / 'run/preparation.json')
rows = []
for row in prep['rows']:
    result = rp.read(D / 'run/native' / f"{row['color']}_{row['machine']}" / 'result.json')
    archive = rp.bound(result['archive'])
    g, cfg, imgs = rp.native_payload(archive)
    first, footprint = rp.first_layer(g, rp.bound(row['project']), row['machine'])
    assert len(first) == 3
    assert all(p['conservativeGapMm'] > 0 for p in footprint['pairs'])
    rows.append(dict(machine=row['machine'], archive=rp.ref(archive),
                     estimatedSeconds=rp.time_seconds(g, row['machine']),
                     firstLayer=first, footprint=footprint))
receipt = dict(passed=True, preparation=rp.ref(D/'run/preparation.json'), rows=rows,
               scope='Actual sliced contact and all-layer extrusion footprints; functional-hole review separate.')
rp.write(D/'run/first-layer-review.json', receipt)
print(json.dumps(receipt, indent=2))
