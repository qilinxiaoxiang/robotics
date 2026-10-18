from pathlib import Path
import json,numpy as np
p=Path(__file__).resolve().parent
m=json.loads((p/'component-mass-envelope.json').read_text());a=json.loads((p/'existing-model-mass-audit.json').read_text())
assert abs(sum(x['mass_nominal_kg'] for x in m['parts'])-.1132)<1e-12
assert m['mass_delta_from_existing_kg'] is None
for x in m['parts']:
 lo,hi=x['mass_interval_kg'];assert 0<lo<=x['mass_nominal_kg']<=hi
 assert all(v>0 for v in x['envelope_nominal_mm'])
for model in a['models'].values():
 for x in model['parts']:
  assert x['original_component_mass_g'] is None
  assert x['mesh_watertight'] and x['mesh_positive_volume']
  assert np.linalg.eigvalsh(x['parent_inertia_com_kg_m2']).min()>0
  assert np.linalg.eigvalsh(x['uniform_mesh_inertia_per_kg_m2']).min()>0
  assert 0<x['assumption_dependent_removal_upper_bound_g']<=x['parent_lumped_mass_g']
assert a['models']['official_current']['total_explicit_mass_g']<1000
print('inventory and inertia checks passed')
