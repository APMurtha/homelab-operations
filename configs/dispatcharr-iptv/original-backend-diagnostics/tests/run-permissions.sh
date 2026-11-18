#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
unshare --user --map-auto --map-root-user --net --fork sh -eu -c '
  export BACKEND_DIAGNOSTIC_PERMISSION_FIXTURE=1
  exec python3 -B "$1/permission_fixture.py"
' fixture "$here"
