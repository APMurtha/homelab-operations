"""Read-only pinned AIO acceptance, executed after its generated environment is loaded."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


def check():
    pins = json.loads(Path('/opt/permanent/api-source-pins.json').read_text())
    for name, expected in pins['files'].items():
        if hashlib.sha256((Path('/app') / name).read_bytes()).hexdigest() != expected:
            raise ValueError('pinned_API_source_changed')
    env = os.environ.copy()
    for pg, source in [('PGHOST','POSTGRES_HOST'), ('PGPORT','POSTGRES_PORT'),
                       ('PGDATABASE','POSTGRES_DB'), ('PGUSER','POSTGRES_USER'), ('PGPASSWORD','POSTGRES_PASSWORD')]:
        env[pg] = os.environ.get(source, '')
    env['PGOPTIONS'] = '-c default_transaction_read_only=on -c statement_timeout=10000 -c lock_timeout=3000'
    query = "SELECT count(*)||':'||md5(string_agg(app||'.'||name,',' ORDER BY app,name)) FROM django_migrations"
    p = subprocess.run(['psql','-XAt','--no-password','-v','ON_ERROR_STOP=1','-c',query],
                       env=env, capture_output=True, text=True, timeout=15)
    if p.returncode or p.stdout.strip() != '184:b00f51e91c5b882cd84d3b2579d074ca':
        raise ValueError('database_or_migrations_changed')
    import redis
    r = redis.Redis(host=os.environ.get('REDIS_HOST','localhost'), port=int(os.environ.get('REDIS_PORT','6379')),
                    password=os.environ.get('REDIS_PASSWORD') or None, decode_responses=True,
                    socket_connect_timeout=3, socket_timeout=3)
    if not r.ping(): raise ValueError('Redis_not_ready')
    workers = []
    for key in r.scan_iter(match='live:worker:*:heartbeat', count=100):
        if len(workers) > 16: raise ValueError('unexpected_worker_count')
        try:
            pid = int(key.rsplit(':',2)[1]); age = time.time() - float(r.get(key))
            if (Path('/proc') / str(pid) / 'comm').read_text().strip() == 'uwsgi' and 0 <= age < 30 and r.ttl(key) > 0:
                workers.append(pid)
        except (OSError, ValueError, TypeError): continue
    if len(workers) != 2: raise ValueError('two_fresh_web_workers_required')
    p = subprocess.run(['celery','-A','dispatcharr','inspect','ping','--timeout=8'],
                       cwd='/app', capture_output=True, text=True, timeout=40)
    nodes = re.findall(r'->\s+([^:\s]+):\s+OK\s+pong',p.stdout)
    if p.returncode or len(nodes) != 2 or {n.split('@')[0] for n in nodes} != {'default','dvr'}:
        raise ValueError('Celery_not_ready')


if __name__ == '__main__':
    try: check()
    except Exception: raise SystemExit('Backend readiness refused; values withheld.')
