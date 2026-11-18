#!/bin/sh
# No Docker or production access. Only a fresh unrouted user/network namespace.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 -B -m unittest discover -s "$base" -p test_runtime_diagnostics.py -v
unshare --user --map-root-user --net --fork sh -eu -c '
  ip link set lo up
  DISPATCHARR_AUDIT_FIXTURE=1 python3 -B "$1/audit_local_fixture.py"
' fixture "$base"
