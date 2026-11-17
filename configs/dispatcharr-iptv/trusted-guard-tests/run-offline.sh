#!/bin/sh
set -eu
suite=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
unshare --user --map-auto --map-root-user --mount --net --fork sh -eu -c '
 ip link set lo up
 TRUSTED_GUARD_IMPLEMENTATION_NS=1 python3 -B "$1/test_implementation.py" -v
' sh "$suite"
