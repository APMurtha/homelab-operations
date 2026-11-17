#!/bin/sh
# No Docker commands, production credentials or broadcaster requests.
set -eu
candidate=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python3 -B -m unittest discover -s "$candidate/tests" -p test_candidate.py
python3 -B -m unittest discover -s "$candidate/tests" -p test_contract.py
python3 -B -m unittest discover -s "$candidate/tests" -p test_inventory.py
python3 -B -m unittest discover -s "$candidate/tests" -p test_provenance.py
python3 -B -m unittest discover -s "$candidate/../minimal-phase6b3d/tests"
python3 -B -m unittest discover -s "$candidate/../boot-admission-phase6b3k/tests"
python3 -B "$candidate/tests/verify_units.py"
sh "$candidate/../trusted-guard-tests/run-offline.sh"
# Pass the existing SHA-verified binary; this runner never fetches/builds images.
: "${CADDY_TEST_BINARY:?Path to previously verified Caddy executable required}"
export CADDY_TEST_BINARY
unshare --user --map-root-user --net sh -eu -c '
  ip link set lo up
  ip addr add 93.184.216.34/32 dev lo
  PERMANENT_TEST_NS=1 python3 -S -B -m unittest discover -s "$1/tests" -p test_network.py
  DISPATCHARR_GATEWAY_TEST_NS=1 python3 -S -B "$1/tests/test_gateway_native.py"
' sh "$candidate"
