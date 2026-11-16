#!/usr/bin/env python3
"""UNAPPLIED proposal: wait for Gluetun before starting Dispatcharr AIO.

Version-specific handoff verified against the 0.33.0 image's source revision.
This is a startup guard, not a substitute for Gluetun's runtime firewall.
"""
import os
import hashlib
from pathlib import Path
import signal
import sys
import time
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    deadline = time.monotonic() + 600
    print("Waiting for the dedicated IPTV VPN health check.", flush=True)
    while time.monotonic() < deadline:
        healthy = False
        try:
            if Path('/guard/ready').read_text().strip() != hashlib.sha256(Path('/opt/egress-policy.json').read_bytes()).hexdigest():
                time.sleep(2)
                continue
            with opener.open("http://127.0.0.1:9999/", timeout=3) as response:
                healthy = response.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        if healthy:
            os.execv("/app/docker/entrypoint.sh", ["/app/docker/entrypoint.sh", *sys.argv[1:]])
        time.sleep(2)
    raise SystemExit("VPN did not become healthy; Dispatcharr was not started.")


if __name__ == "__main__":
    main()
