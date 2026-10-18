"""Read back the delivered PDF, its source bindings and completed visual review.
Run with a Python providing pypdf (Codex bundled Python); does not rebuild artifacts.
"""
from pathlib import Path
import hashlib
import json
import sys
from pypdf import PdfReader
from verify_assembly_handoff import inspect_assembly

P=Path(__file__).resolve().parent
O=P/'output/pdf'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def inspect():
    errors=inspect_assembly()
    def require(ok,message):
        if not ok: errors.append(message)
    try:
        pdf=O/'MicroDuck_Assembly_Manual.pdf'
        report=json.loads((O/'manual-verification.json').read_text())
        visual=json.loads((O/'manual-visual-verification.json').read_text())
        require(report.get('passed') is True,'Manual content verification failed')
        require(visual.get('passed') is True,'Manual visual verification failed')
        require(sha(pdf)==report['pdf_sha256']==visual['pdf_sha256'],'PDF differs from content or visual acceptance')
        required={'ASSEMBLY-STEPS.md','ASSEMBLY-WIRING.md','assembly-fasteners.json','design-contract.json','print-manifest.json','build_assembly_pdf.py','PROJECT-CONTEXT.json'}
        require(required <= {Path(x).name for x in report['sources']},'Missing required manual source binding')
        for name,digest in report['sources'].items():
            source=Path(name)
            require(source.is_file() and sha(source)==digest,'Manual source changed: '+name)
        reader=PdfReader(pdf)
        require(not reader.is_encrypted,'Manual is encrypted')
        require(len(reader.pages)==report['pages']==visual['rendered_pages']==35,'Manual page count differs from inspected 35-page delivery')
        text='\n'.join(page.extract_text() or '' for page in reader.pages)
        ledger=json.loads((P/'assembly-fasteners.json').read_text())
        rows=ledger['connections']
        require(len(rows)==report['connection_groups']==129,'Connection count mismatch')
        require(sum(bool(r.get('servo_ids')) for r in rows)==report['joint_positions']==118,'Joint count mismatch')
        for row in rows:require(row['id'] in text,'PDF omits connection '+row['id'])
        for sid in range(1,16):require(f'Motor {sid:02d} -' in text,'Missing motor card '+str(sid))
        for term in ['Printed-parts checklist','Installed hardware checklist','Pi physical-pin and fuse checklist','W1. Make and inspect the unpowered harness','W2. First power and records','C1-C3','S1-S4','MacBook Pro','sensor capture','400 mm']:
            require(term.lower() in text.lower(),'PDF omits required instruction: '+term)
        require(report.get('physical_tests')==0,'Manual falsely claims physical tests')
        require('MicroDuck_Assembly_Manual.pdf' in (P/'ASSEMBLY.html').read_text(),'HTML handoff omits printable manual')
        # Native rendered-page evidence retained beside the source. Every delivered
        # page has a decoded raster, and the visual certificate binds this PDF.
        from PIL import Image
        for n in range(1,len(reader.pages)+1):
            image=P/f'tmp/pdfs/accepted-{n:02d}.png'
            with Image.open(image) as im:
                im.verify()
            require(image.stat().st_size>1000,'Empty render for page '+str(n))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        errors.append('Incomplete printable manual: '+str(exc))
    return errors

if __name__=='__main__':
    errors=inspect()
    result={'passed':not errors,'errors':errors,'pdf':str(O/'MicroDuck_Assembly_Manual.pdf'),'physical_tests':0}
    print(json.dumps(result,indent=2))
    if errors:sys.exit(1)
    print('PRINTABLE_MANUAL_ACCEPTANCE_PASS')
