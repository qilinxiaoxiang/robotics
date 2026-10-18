#!/bin/bash
# Rebuild the study with each grille / front-gap variant and record its acoustic estimate (acoustics-<tag>.json).
# Ends by rebuilding the recommended variant (AUDIO_FRONT_GAP / AUDIO_GRILLE_D / AUDIO_GRILLE_PITCH defaults).
set -e
PY=/tmp/microduck-cad-venv/bin/python
cd "$(dirname "$0")"
for cfg in "1.0 1.8 2.7 gap1-d1.8" "2.0 1.8 2.7 gap2-d1.8" "20 1.8 2.7 nofill-d1.8" "1.0 1.7 2.6 gap1-d1.7" "1.0 2.0 2.9 gap1-d2.0"; do
  set -- $cfg
  AUDIO_FRONT_GAP=$1 AUDIO_GRILLE_D=$2 AUDIO_GRILLE_PITCH=$3 $PY build_study.py > /dev/null 2>&1
  AUDIO_FRONT_GAP=$1 AUDIO_GRILLE_D=$2 AUDIO_GRILLE_PITCH=$3 AUDIO_VARIANT_TAG=$4 $PY acoustics.py > /dev/null 2>&1
  $PY -c "
import json; d=json.load(open('../acoustics-$4.json')); m=d['measured']; i=d['inference']
print('$4', 'V', m['frontChamberVolumeMm3'], 't', m['roofThicknessAlongHoleAxisMm'], 'N', m['grilleHoles'], 'S', m['grilleOpenAreaMm2'], 'fH', i['helmholtzFrontResonanceHz'])"
done
# recommended variant (defaults) last, so study-solids/ and study-build.json hold it
$PY build_study.py > /dev/null 2>&1
$PY acoustics.py > /dev/null 2>&1
