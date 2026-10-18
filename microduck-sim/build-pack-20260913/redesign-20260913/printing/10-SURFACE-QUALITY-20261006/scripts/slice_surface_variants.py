from pathlib import Path
import json,subprocess,sys,argparse
D=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--printer',choices=['Elegoo','Bambu'],default='Elegoo');ap.add_argument('--group');args=ap.parse_args();q=json.loads((D/'projects/project-preparation.json').read_text())
 for v in q['variants']:
  if v['printer']!=args.printer or (args.group and v['group']!=args.group):continue
  if v['group'] in ['WHITE','old-black-plate5']:continue
  out=D/'intermediate'/v['printer']/v['group']/'pass0';out.mkdir(parents=True,exist_ok=True);helper=D/'slicing/guarded_orca_slice.py' if v['printer']=='Elegoo' else D/'scripts/guarded_bambu_slice.py';cmd=[sys.executable,str(helper),'--project',v['project'],'--outputdir',str(out),'--export',f'MicroDuck_{v["printer"]}_{v["group"]}_SURFACE_CLI.3mf']
  with (out/'helper.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=240)
  print(v['printer'],v['group'],r.returncode,flush=True);assert r.returncode==0,(cmd,r.returncode)
if __name__=='__main__':main()
