from pathlib import Path
import subprocess,time,shutil
H=Path(__file__).resolve().parent
exe='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
for i,(source,out,size) in enumerate([('index.html','images/reader-preview.png','1450,1900'),('images/wiring-power.svg','images/wiring-power-preview.png','1800,1610'),('images/wiring-signals.svg','images/wiring-signals-preview.png','1800,1500')]):
 profile=H/f'.preview-{i}';target=H/out
 if target.exists():target.unlink()
 args=[exe,'--headless','--disable-gpu','--no-first-run','--no-default-browser-check',f'--user-data-dir={profile}',f'--window-size={size}','--hide-scrollbars',f'--screenshot={target}',(H/source).as_uri()]
 with (H/f'.preview-{i}.log').open('w') as log:
  p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT)
  start=time.time()
  while not target.exists() and time.time()-start<30:time.sleep(.2)
  time.sleep(.3);p.terminate()
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:p.kill();p.wait()
 assert target.exists(),source
 print('rendered',source,flush=True)
 shutil.rmtree(profile,ignore_errors=True)
