"""Package review files and exact candidate solids; never creates a printer job."""
from pathlib import Path
import json,hashlib,zipfile
P=Path(__file__).resolve().parent;G=P.parent/'leg-guide-20261006'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    # Curated contents: native CAD, bed-oriented meshes, review and evidence.
    files=[P/n for n in ['README.md','DESIGN-NOTES.md','ANKLE-REDESIGN.html','preview-data.json','review-bundle.json','print-review.json','print-review.md','cad-export.json','geometry-evidence.json','check_candidate_geometry.py','generate_candidate.py','export_step.py','finalize_manifest.py','prepare_print_stl.py','verify_redesign.py']]
    files+=sorted((P/'CAD').glob('*.step'))+sorted((P/'CAD').glob('*.stp'))
    files+=sorted((P/'STL').glob('*.stl'))+sorted((P/'PRINT-STL').glob('*.stl'))
    files+=sorted((P/'evidence').glob('*.json'))+sorted((P/'evidence').glob('*.md'))
    files+=sorted(P.glob('mechanical-*.json'))+sorted(P.glob('mechanical-*.md'))+sorted(P.glob('*verification*.json'))
    assert len(list((P/'PRINT-STL').glob('*.stl')))==6, 'six bed-oriented prototype meshes required'
    assert all(f.exists() for f in files)
    files=sorted(set(files));target=G/'ANKLE-REDESIGN.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for f in files:z.write(f,str(f.relative_to(P)))
    manifest={'zipSha256':sha(target),'files':{str(f.relative_to(P)):sha(f) for f in files},'scope':'Prototype model and review; no sliced job, physical fit or strength acceptance.'}
    (P/'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('ANKLE_REDESIGN_PACKAGE_PASS',len(files),target.stat().st_size)
if __name__=='__main__':main()
