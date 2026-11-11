import adsk.core, adsk.fusion, threading, json, traceback, io, contextlib, queue, uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

app = adsk.core.Application.get()
EVENT_ID = 'ClaudeBridgeRun'
handlers, pending = [], {}
server = None

class RunHandler(adsk.core.CustomEventHandler):
    def notify(self, args):
        job = pending.get(args.additionalInfo)
        if not job: return
        out = io.StringIO(); g = {'adsk': adsk, 'app': app, 'ui': app.userInterface}
        try:
            with contextlib.redirect_stdout(out):
                exec(job['code'], g)
            job['result'] = {'ok': True, 'out': out.getvalue(), 'result': repr(g.get('result'))}
        except Exception:
            job['result'] = {'ok': False, 'out': out.getvalue(), 'error': traceback.format_exc()}
        job['done'].set()

class Http(BaseHTTPRequestHandler):
    def do_POST(self):
        code = self.rfile.read(int(self.headers['Content-Length'])).decode()
        jid = str(uuid.uuid4()); job = {'code': code, 'done': threading.Event()}
        pending[jid] = job
        app.fireCustomEvent(EVENT_ID, jid)
        job['done'].wait(600)
        res = job.get('result', {'ok': False, 'error': 'timeout'}); pending.pop(jid, None)
        body = json.dumps(res).encode()
        self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

def run(context):
    global server
    ev = app.registerCustomEvent(EVENT_ID); h = RunHandler(); ev.add(h); handlers.append(h)
    server = HTTPServer(('127.0.0.1', 8777), Http)
    threading.Thread(target=server.serve_forever, daemon=True).start()

def stop(context):
    if server: server.shutdown()
    app.unregisterCustomEvent(EVENT_ID)
