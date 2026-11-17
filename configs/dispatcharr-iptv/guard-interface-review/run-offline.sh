#!/bin/sh
# Counterexample fixtures only. No Docker, systemd, nft, provider or API calls.
set -eu
review=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
unshare --user --map-auto --map-root-user --mount --net --fork sh -eu -c '
  ip link set lo up
  DISPATCHARR_GUARD_FIXTURE_NS=1 python3 -B "$1/test_feasibility.py" -v
' sh "$review"
