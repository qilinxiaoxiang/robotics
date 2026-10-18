#!/usr/bin/env python3
"""Serve the existing guide, explicit prototype and source snapshots on loopback only."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit
import argparse
import json
import socket
import gzip
import hashlib
import threading

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
CONNECTION_TIMEOUT = 3.0
TRANSFER_TIMEOUT = 60.0
_REPRESENTATIONS = {}
_CACHE_LOCK = threading.Lock()
ALLOWLIST = {
    "/": "MICRODUCK-BUILD.html",
    "/MICRODUCK-BUILD.html": "MICRODUCK-BUILD.html",
    "/BATTERY-WIRING.html": "BATTERY-WIRING.html",
    "/PARTS-SHEET.html": "PARTS-SHEET.html",
    "/zhengxia_MicroDuck_V1.6_8-files.zip": "zhengxia_MicroDuck_V1.6_8-files.zip",
    "/PARTS-SHEET-V1.7.html": "PARTS-SHEET-V1.7.html",
    "/zhengxia_MicroDuck_V1.7_4-files.zip": "zhengxia_MicroDuck_V1.7_4-files.zip",
    "/PARTS-SHEET-V1.8.html": "PARTS-SHEET-V1.8.html",
    "/zhengxia_MicroDuck_V1.8_8-files.zip": "zhengxia_MicroDuck_V1.8_8-files.zip",
    "/LEFT-LEG.html": "LEFT-LEG.html",
    "/HEAD-EYE-REVIEW.html": "HEAD-EYE-REVIEW.html",
    "/DESIGN-REVIEW.html": "DESIGN-REVIEW.html",
    "/REPRINT-PLAN.html": "REPRINT-PLAN.html",
    "/REPRINT-PARTS.zip": "REPRINT-PARTS.zip",
    "/ANKLE-REDESIGN.html": "ANKLE-REDESIGN.html",
    "/ANKLE-REDESIGN.zip": "ANKLE-REDESIGN.zip",
    "/BRINGUP.html": "BRINGUP.html",
    "/A7Z-PINS.html": "A7Z-PINS.html",
    "/A7Z-ANTENNA.html": "A7Z-ANTENNA.html",
    "/A7Z-WIRES.html": "A7Z-WIRES.html",
    "/POWER-12V.html": "POWER-12V.html",
    "/EXTENSION-REVIEW.html": "EXTENSION-REVIEW.html",
    "/HEAD-3D.html": "HEAD-3D.html",
    "/PARTS-SHEET-V1.9.html": "PARTS-SHEET-V1.9.html",
    "/zhengxia_MicroDuck_V1.9_2-files.zip": "zhengxia_MicroDuck_V1.9_2-files.zip",
    "/PARTS-SHEET-V1.10.html": "PARTS-SHEET-V1.10.html",
    "/zhengxia_MicroDuck_V1.10_2-files.zip": "zhengxia_MicroDuck_V1.10_2-files.zip",
    "/PARTS-SHEET-V1.11.html": "PARTS-SHEET-V1.11.html",
    "/zhengxia_MicroDuck_V1.11_2-files.zip": "zhengxia_MicroDuck_V1.11_2-files.zip",
    "/PARTS-SHEET-V1.12.html": "PARTS-SHEET-V1.12.html",
    "/zhengxia_MicroDuck_V1.12_2-files.zip": "zhengxia_MicroDuck_V1.12_2-files.zip",
    "/PARTS-SHEET-V1.13.html": "PARTS-SHEET-V1.13.html",
    "/zhengxia_MicroDuck_V1.13_4-files.zip": "zhengxia_MicroDuck_V1.13_4-files.zip",
    "/PARTS-SHEET-V1.14.html": "PARTS-SHEET-V1.14.html",
    "/zhengxia_MicroDuck_V1.14_4-files.zip": "zhengxia_MicroDuck_V1.14_4-files.zip",
    "/PARTS-SHEET-V1.15.html": "PARTS-SHEET-V1.15.html",
    "/zhengxia_MicroDuck_V1.15_4-files.zip": "zhengxia_MicroDuck_V1.15_4-files.zip",
    "/PARTS-SHEET-V1.16.html": "PARTS-SHEET-V1.16.html",
    "/zhengxia_MicroDuck_V1.16_4-files.zip": "zhengxia_MicroDuck_V1.16_4-files.zip",
    "/PARTS-SHEET-V1.17.html": "PARTS-SHEET-V1.17.html",
    "/zhengxia_MicroDuck_V1.17_4-files.zip": "zhengxia_MicroDuck_V1.17_4-files.zip",
    "/PARTS-SHEET-V1.18.html": "PARTS-SHEET-V1.18.html",
    "/zhengxia_MicroDuck_V1.18_2-files.zip": "zhengxia_MicroDuck_V1.18_2-files.zip",
    "/PARTS-SHEET-V1.19.html": "PARTS-SHEET-V1.19.html",
    "/zhengxia_MicroDuck_V1.19_2-files.zip": "zhengxia_MicroDuck_V1.19_2-files.zip",
    "/sources/print-colors.json": "sources/print-colors.json",
    "/sources/motor-fasteners.json": "sources/motor-fasteners.json",
}


class GuideHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def setup(self):
        # Browser preconnects and unfinished headers must not monopolize a worker.
        self.request.settimeout(CONNECTION_TIMEOUT)
        super().setup()

    def _serve(self, head_only=False):
        try:
            route = unquote(urlsplit(self.path).path, errors="strict")
        except (ValueError, UnicodeError):
            self.send_error(404)
            return
        relative = ALLOWLIST.get(route)
        if relative is None:
            self.send_error(404)
            return
        path = ROOT / relative
        # The allowlist is literal, and symlink changes cannot escape this folder.
        try:
            if not path.resolve(strict=True).is_relative_to(ROOT):
                self.send_error(404)
                return
            stream = path.open("rb")
        except (OSError, ValueError):
            self.send_error(404)
            return
        with stream:
            # A short header timeout protects against abandoned preconnects;
            # a valid large response needs its own idle-write timeout.
            self.request.settimeout(TRANSFER_TIMEOUT)
            import os
            stat = os.fstat(stream.fileno())
            accept = self.headers.get("Accept-Encoding", "")
            wants_gzip = False
            for token in accept.split(","):
                fields = [part.strip() for part in token.split(";")]
                if fields[0].lower() != "gzip":
                    continue
                try:
                    quality = next((float(part[2:]) for part in fields[1:] if part.startswith("q=")), 1.0)
                    wants_gzip = quality > 0
                except ValueError:
                    pass
            compress = wants_gzip and relative.endswith((".html", ".json"))
            key = (str(path), stat.st_mtime_ns, stat.st_size, compress)
            with _CACHE_LOCK:
                cached = _REPRESENTATIONS.get(key)
                if cached is None:
                    data = stream.read()
                    if compress:
                        data = gzip.compress(data, compresslevel=6, mtime=0)
                    cached = (data, '"' + hashlib.sha256(data).hexdigest() + '"')
                    # Keep only current versions; allowlist bounds total memory.
                    for old in list(_REPRESENTATIONS):
                        if old[0] == str(path) and old[3] == compress:
                            del _REPRESENTATIONS[old]
                    _REPRESENTATIONS[key] = cached
            data, etag = cached
            unchanged = self.headers.get("If-None-Match") == etag
            self.send_response(304 if unchanged else 200)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Vary", "Accept-Encoding")
            if not unchanged:
                self.send_header("Content-Type", "text/html; charset=utf-8" if relative.endswith(".html") else "application/zip" if relative.endswith(".zip") else "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                if compress:
                    self.send_header("Content-Encoding", "gzip")
            self.end_headers()
            if not head_only and not unchanged:
                try:
                    for offset in range(0, len(data), 65536):
                        self.wfile.write(data[offset:offset+65536])
                except (BrokenPipeError, ConnectionResetError, socket.timeout):
                    self.close_connection = True

    def do_GET(self):
        self._serve()

    def do_HEAD(self):
        self._serve(head_only=True)


class GuideServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 64


def create_server(port=8766):
    return GuideServer((HOST, port), GuideHandler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    with create_server(args.port) as server:
        print(json.dumps({"status": "listening", "url": f"http://{HOST}:{server.server_port}/LEFT-LEG.html", "root": str(ROOT), "allowlist": list(ALLOWLIST), "connection_timeout_s": CONNECTION_TIMEOUT}), flush=True)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
