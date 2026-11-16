#!/bin/sh
# No public network request before the host's scoped firewall is installed.
set -eu
trap 'exit 0' TERM INT
actual=$(sha256sum /opt/egress-policy.json | cut -d ' ' -f 1)
tries=0
while [ "$tries" -lt 300 ]; do
  if [ -r /guard/ready ]; then
    expected=$(cat /guard/ready)
    if [ "$expected" = "$actual" ]; then
      exec /gluetun-entrypoint "$@"
    fi
  fi
  tries=$((tries + 1))
  sleep 2
done
echo 'Host egress guard is not ready; VPN owner was not started.' >&2
exit 1
