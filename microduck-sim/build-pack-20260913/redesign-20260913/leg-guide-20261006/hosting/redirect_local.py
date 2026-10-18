#!/usr/bin/env python3
"""Keep existing MacBook guide bookmarks working after migration to Mac mini."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from serve_guide import ALLOWLIST
class Redirect(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(3)
        super().setup()
    def do_GET(self):
        route = unquote(urlsplit(self.path).path)
        if route not in ALLOWLIST:
            self.send_error(404)
            return
        self.send_response(307)
        self.send_header('Location', 'http://today.tailfc7c94.ts.net:8766' + route)
        self.send_header('Content-Length', '0')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
    do_HEAD = do_GET
ThreadingHTTPServer(('127.0.0.1', 8766), Redirect).serve_forever()
