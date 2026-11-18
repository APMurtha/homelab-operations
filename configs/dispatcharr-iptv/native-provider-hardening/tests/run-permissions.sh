#!/bin/sh
# Offline UID1000/tmpfs/bind semantics, no Docker or real network requests.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
unshare --user --map-auto --map-root-user --mount --net --fork sh -eu -c '
  export PROVIDER_PERMISSION_FIXTURE=1
  exec python3 -B "$1/permission_fixture.py" -v
' fixture "$base"
