#!/usr/bin/env python3
"""Bounded concurrency, timeout, content and allowlist regression."""
from pathlib import Path
import hashlib
import gzip
import http.client
import json
import socket
import threading
import time
import serve_guide


def paused_large_download(base, pause_s, expect_complete):
    """Force TCP backpressure, pause past header timeout, then drain promptly."""
    expected = (serve_guide.ROOT / "LEFT-LEG.html").read_bytes()
    assert len(expected) > 8 * 1024 * 1024, "fixture must exceed socket buffers"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # Set before connect so negotiation cannot silently use a large window.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 32768)
        sock.settimeout(20)
        sock.connect(base)
        sock.sendall(b"GET /LEFT-LEG.html HTTP/1.0\r\nHost: localhost\r\nAccept-Encoding: identity\r\n\r\n")
        headers = bytearray()
        while not headers.endswith(b"\r\n\r\n"):
            byte = sock.recv(1)
            assert byte, "response closed before headers"
            headers += byte
            assert len(headers) < 65536
        assert bytes(headers).startswith(b"HTTP/1.0 200 "), bytes(headers)
        fields = dict(line.split(b":", 1) for line in bytes(headers).split(b"\r\n")[1:] if b":" in line)
        advertised = int(fields[b"Content-Length"].strip())
        assert advertised == len(expected)
        started = time.monotonic()
        time.sleep(pause_s)
        actual_pause = time.monotonic() - started
        # Large reads after the pause avoid making the test a bandwidth benchmark.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        received = 0
        digest = hashlib.sha256()
        drain_start = time.monotonic()
        while True:
            chunk = sock.recv(1024 * 1024)
            if not chunk:
                break
            received += len(chunk)
            digest.update(chunk)
        complete = received == advertised and digest.hexdigest() == hashlib.sha256(expected).hexdigest()
        assert complete == expect_complete, {"expected_complete": expect_complete, "received": received, "advertised": advertised}
        return {"passed": True, "pause_s": actual_pause, "header_timeout_s": serve_guide.CONNECTION_TIMEOUT,
                "advertised_bytes": advertised, "received_bytes": received, "exact_body": complete,
                "drain_s": time.monotonic() - drain_start}


def legacy_body_timeout_negative_control():
    """Reproduce old 3-second transfer timeout in an isolated local server."""
    current_timeout = serve_guide.TRANSFER_TIMEOUT
    server = None
    worker = None
    try:
        serve_guide.TRANSFER_TIMEOUT = serve_guide.CONNECTION_TIMEOUT
        server = serve_guide.create_server(0)
        worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .05}, daemon=True)
        worker.start()
        result = paused_large_download((serve_guide.HOST, server.server_port), serve_guide.CONNECTION_TIMEOUT + 1, False)
        result["check"] = "legacy_header_timeout_reused_for_body_truncates_large_download"
        return result
    finally:
        if server:
            server.shutdown()
            server.server_close()
            worker.join(1)
        serve_guide.TRANSFER_TIMEOUT = current_timeout


def verify(port=None):
    owned = serve_guide.create_server(0) if port is None else None
    worker = None
    if owned:
        worker = threading.Thread(target=owned.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        worker.start()
        port = owned.server_port
    base = (serve_guide.HOST, port)
    sockets = []
    checks = []
    try:
        idle = socket.create_connection(base, timeout=1)
        sockets.append(idle)
        incomplete = socket.create_connection(base, timeout=1)
        sockets.append(incomplete)
        incomplete.sendall(b"GET /LEFT-LEG.html HTTP/1.1\r\nHost: localhost\r\n")
        slow_reader = socket.create_connection(base, timeout=1)
        sockets.append(slow_reader)
        slow_reader.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
        slow_reader.sendall(b"GET /LEFT-LEG.html HTTP/1.1\r\nHost: localhost\r\n\r\n")
        # Do not read this large download: its worker must not block other requests.
        time.sleep(0.05)
        for method in ["HEAD", "GET"]:
            started = time.monotonic()
            conn = http.client.HTTPConnection(*base, timeout=2)
            conn.request(method, "/LEFT-LEG.html?regression=1")
            response = conn.getresponse()
            body = response.read()
            elapsed = time.monotonic() - started
            assert response.status == 200, response.status
            assert elapsed < 2, elapsed
            if method == "GET":
                assert hashlib.sha256(body).hexdigest() == hashlib.sha256((serve_guide.ROOT / "LEFT-LEG.html").read_bytes()).hexdigest()
            else:
                assert body == b""
            conn.close()
            checks.append({"check": f"normal_{method}_while_idle_incomplete_and_slow_reader_connections_open", "passed": True, "elapsed_s": elapsed, "received_bytes": len(body)})
        for route in serve_guide.ALLOWLIST:
            conn = http.client.HTTPConnection(*base, timeout=2)
            conn.request("GET", route)
            response = conn.getresponse()
            content = response.read()
            assert response.status == 200, (route, response.status)
            assert content == (serve_guide.ROOT / serve_guide.ALLOWLIST[route]).read_bytes()
            conn.close()
            checks.append({"check": "exact_allowed_file", "route": route, "passed": True})
        for route in ["/README.md", "/viewer.js", "/sources/", "/sources/../README.md", "/%2e%2e/ASSEMBLY.html", "/sources/%2e%2e%2fREADME.md", "/%252e%252e/ASSEMBLY.html", "/etc/passwd"]:
            conn = http.client.HTTPConnection(*base, timeout=2)
            conn.request("GET", route)
            response = conn.getresponse()
            response.read()
            assert response.status == 404, (route, response.status)
            conn.close()
            checks.append({"check": "outside_allowlist_rejected", "route": route, "passed": True})
        for name, sock in [("idle", idle), ("incomplete_headers", incomplete)]:
            started = time.monotonic()
            sock.settimeout(serve_guide.CONNECTION_TIMEOUT + 1)
            assert sock.recv(1) == b"", name
            checks.append({"check": f"{name}_times_out_and_closes", "passed": True, "wait_s": time.monotonic() - started})
        expected = (serve_guide.ROOT / "LEFT-LEG.html").read_bytes()
        for encoding in ["gzip", "gzip;q=0.5", "gzip;q=0"]:
            conn = http.client.HTTPConnection(*base, timeout=20)
            conn.request("GET", "/LEFT-LEG.html", headers={"Accept-Encoding": encoding})
            response = conn.getresponse()
            encoded = response.read()
            assert response.status == 200
            compressed = encoding != "gzip;q=0"
            assert (response.getheader("Content-Encoding") == "gzip") == compressed
            assert (gzip.decompress(encoded) if compressed else encoded) == expected
            assert response.getheader("Vary") == "Accept-Encoding"
            etag = response.getheader("ETag")
            assert etag
            conn.close()
            conditional = http.client.HTTPConnection(*base, timeout=5)
            conditional.request("GET", "/LEFT-LEG.html", headers={"Accept-Encoding": encoding, "If-None-Match": etag})
            cached = conditional.getresponse()
            assert cached.status == 304, cached.status
            assert cached.read() == b""
            assert cached.getheader("ETag") == etag
            conditional.close()
            checks.append({"check": "encoding_exact_body_and_etag_304", "accept_encoding": encoding, "passed": True, "wire_bytes": len(encoded), "decoded_bytes": len(expected)})
        slow = paused_large_download(base, serve_guide.CONNECTION_TIMEOUT + 1, True)
        slow["check"] = "large_body_remains_exact_after_reader_pauses_past_header_timeout"
        checks.append(slow)
        checks.append(legacy_body_timeout_negative_control())
        return {"passed": True, "marker": "GUIDE_SERVER_REGRESSION_PASS", "host": base[0], "port": port, "connection_timeout_s": serve_guide.CONNECTION_TIMEOUT, "transfer_timeout_s": serve_guide.TRANSFER_TIMEOUT, "checks": checks, "script_sha256": hashlib.sha256(Path(serve_guide.__file__).read_bytes()).hexdigest()}
    finally:
        for sock in sockets:
            sock.close()
        if owned:
            owned.shutdown()
            owned.server_close()
            worker.join(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.port)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["marker"], f"{result['host']}:{result['port']}")
