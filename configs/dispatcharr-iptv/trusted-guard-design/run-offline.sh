#!/bin/sh
# Design model only. Temporary tmpfs/binds, no production or firewall operations.
set -eu
review=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
unshare --user --map-auto --map-root-user --mount --net --fork sh -eu -c '
  TRUSTED_GUARD_DESIGN_NS=1 python3 -B "$1/test_model.py" -v
' sh "$review"
