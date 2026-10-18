#!/usr/bin/env python3
"""Mac mini entrypoint; expose only the guide allowlist on its private Tailscale IP."""
from pathlib import Path
import ipaddress
import socket
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import serve_guide
address = socket.gethostbyname('today.tailfc7c94.ts.net')
if ipaddress.ip_address(address) not in ipaddress.ip_network('100.64.0.0/10'):
    raise RuntimeError('Expected the Mac mini private Tailscale address')
serve_guide.HOST = address
serve_guide.main()
