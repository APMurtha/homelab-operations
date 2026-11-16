#!/bin/sh
# Run inside the pinned, already-running AIO as UID/GID 1000:1000.
# Execute only an approved check; do not dump the generated environment or keys.
set +x
set -eu
if [ "$#" -ne 1 ]; then
  echo 'Choose environment, migrations or workers.' >&2
  exit 2
fi
if [ ! -r /etc/profile.d/dispatcharr.sh ]; then
  echo 'Image-generated application environment is unavailable.' >&2
  exit 1
fi
. /etc/profile.d/dispatcharr.sh
if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
  echo 'Application Django secret is unavailable; no check executed.' >&2
  exit 1
fi
export PYTHONDONTWRITEBYTECODE=1
cd /app
case "$1" in
  environment)
    exec python -c 'import json,os; names=("DJANGO_SECRET_KEY","POSTGRES_DB","POSTGRES_USER","POSTGRES_HOST","POSTGRES_PORT"); result={name+"_loaded":bool(os.environ.get(name)) for name in names}; print(json.dumps(result)); raise SystemExit(0 if all(result.values()) else 1)'
    ;;
  migrations)
    exec python manage.py migrate --check --noinput
    ;;
  workers)
    exec python - <<'PYWORKERS'
import re
import subprocess
import sys
try:
    result = subprocess.run(
        ['celery', '-A', 'dispatcharr', 'inspect', 'ping', '--timeout=8'],
        capture_output=True, text=True, timeout=80,
    )
except subprocess.TimeoutExpired:
    print('Worker readiness command timed out.', file=sys.stderr)
    raise SystemExit(1)
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
nodes = re.findall(r'->\s+([^:\s]+):\s+OK\s+pong', result.stdout)
expected = {'default', 'dvr'}
healthy = result.returncode == 0 and len(nodes) == 2 and {n.split('@', 1)[0] for n in nodes} == expected
if not healthy:
    print('Both expected default and DVR workers must respond.', file=sys.stderr)
raise SystemExit(0 if healthy else 1)
PYWORKERS
    ;;
  *)
    echo 'Unsupported application check.' >&2
    exit 2
    ;;
esac
