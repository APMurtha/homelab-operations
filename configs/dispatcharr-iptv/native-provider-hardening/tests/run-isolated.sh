#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
unshare --user --map-root-user --net sh -eu -c '
  ip link set lo up
  export NATIVE_ISOLATED_TEST=1
  exec python3 -B "$1/network_fixture.py"
' native-isolated "$base"
