"""Use an existing independent 2 mm Pi spacer; this is not a robot release."""
from pathlib import Path
import json
from release_pipeline import *
source=PRINT/'12-REPAIR-V1-20261008/delivery-V1.3-Incremental/Black/pi_2mm_spacer_qty3.stl'
evidence=PRINT/'12-REPAIR-V1-20261008/incremental-audit/incremental-audit-V1.4.json'
m=load_mesh(source);print(m.bounds.tolist())
manifest=dict(schemaVersion=1,releaseKind='fixture',version='PIPELINE-SMOKE',baselineStock=ref(PRINT/'copy-manifest.json'),profiles=default_profile_refs(),parts=[dict(**ref(source),key='pi_spacer_fixture',color='Black',quantity=1,sourceToPrint=np.eye(4).tolist(),flatContact={'minimumAreaMm2':1},replacesStockIds=[],decision='addition',changeReason='Existing V1.4 independent spacer used only as pipeline fixture; not an additional robot print.',incrementalEvidence=ref(evidence))])
write(HERE/'fixture-manifest.json',manifest)
