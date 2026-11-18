"""Read-only pinned AIO acceptance, executed after its generated environment is loaded."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


# Diagnostic projection only. No values from commands, environment or exceptions.
import contextlib
import math
import sys

DIAG_PREFIX = 'DISPATCHARR_BACKEND_DIAG '
STAGES = ('api_sources', 'postgres', 'redis', 'uwsgi', 'celery')
MAX_RECORD = 768


def failure_code(stage, error, metrics):
    known = {
        'pinned_API_source_changed': 'source_hash_mismatch',
        'Redis_not_ready': 'redis_ping_failed',
        'unexpected_worker_count': 'worker_count_exceeded',
        'two_fresh_web_workers_required': 'fresh_workers_missing',
    }
    if type(error) is ValueError and len(error.args) == 1:
        # Equality tests only: never serialize an exception's message/arguments.
        for message, code in known.items():
            if error.args == (message,) and code in FAILURES[stage]: return code
        if stage=='postgres' and error.args == ('database_or_migrations_changed',):
            return 'postgres_command_failed' if metrics.get('returncode') else 'migration_mismatch'
        if stage=='celery' and error.args == ('Celery_not_ready',):
            if metrics.get('returncode'): return 'celery_command_failed'
            if not metrics.get('default_present') and not metrics.get('dvr_present'): return 'celery_roles_missing'
            if not metrics.get('default_present'): return 'celery_default_missing'
            if not metrics.get('dvr_present'): return 'celery_dvr_missing'
            return 'celery_reply_count'
    if type(error).__module__.startswith('redis.'):
        code = {'AuthenticationError':'redis_authentication_failed', 'ConnectionError':'redis_connection_failed',
                'TimeoutError':'redis_timeout'}.get(type(error).__name__)
        if code: return code
    if isinstance(error, subprocess.TimeoutExpired): return 'subprocess_timeout'
    if isinstance(error, FileNotFoundError): return 'file_missing'
    if isinstance(error, PermissionError): return 'file_permission'
    if isinstance(error, json.JSONDecodeError): return 'invalid_manifest'
    if isinstance(error, ImportError): return 'dependency_unavailable'
    return 'unexpected_exception'


class Diagnostics:
    def __init__(self):
        self.started = time.monotonic()
        self.values = {}

    def metrics(self, **values):
        self.values.update(values)

    def emit(self, stage, event, classification, metrics=False):
        elapsed = round(time.monotonic() - self.started, 6)
        if not math.isfinite(elapsed) or elapsed < 0: raise ValueError('diagnostic_clock_invalid')
        record = {'stage':stage, 'event':event, 'elapsed_s':elapsed, 'classification':classification}
        if metrics: record.update(self.values)
        raw = DIAG_PREFIX + json.dumps(record, sort_keys=True, allow_nan=False, separators=(',', ':'))
        if len(raw.encode()) > MAX_RECORD: raise ValueError('diagnostic_record_limit')
        print(raw, file=sys.stderr, flush=True)

    @contextlib.contextmanager
    def stage(self, name):
        self.values = {}
        self.emit(name, 'start', 'checking')
        try:
            yield
        except Exception as error:
            self.emit(name, 'fail', failure_code(name, error, self.values), metrics=True)
            raise
        else:
            self.emit(name, 'pass', 'ready', metrics=True)


# Shared producer/reader schema. Importing this module does not run check().
FAILURES = {
    'api_sources': {'source_hash_mismatch'},
    'postgres': {'postgres_command_failed', 'migration_mismatch'},
    'redis': {'redis_ping_failed','redis_authentication_failed','redis_connection_failed','redis_timeout'},
    'uwsgi': {'worker_count_exceeded','fresh_workers_missing','redis_authentication_failed','redis_connection_failed','redis_timeout'},
    'celery': {'celery_command_failed','celery_roles_missing','celery_default_missing','celery_dvr_missing','celery_reply_count'},
}
COMMON_FAILURES = {'file_missing','file_permission','invalid_manifest','dependency_unavailable','subprocess_timeout','unexpected_exception'}
METRICS = {'api_sources': {'count'}, 'postgres': {'returncode'}, 'redis': set(),
           'uwsgi': {'count'}, 'celery': {'count','returncode','default_present','dvr_present'}}


class InvalidDiagnostics(ValueError): pass


def decode_record(raw):
    def pairs(items):
        value = {}
        for key,item in items:
            if key in value: raise InvalidDiagnostics('duplicate_field')
            value[key] = item
        return value
    def constant(_): raise InvalidDiagnostics('nonfinite_number')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, TypeError, UnicodeError):
        raise InvalidDiagnostics('invalid_JSON') from None
    base = {'stage','event','elapsed_s','classification'}
    if not isinstance(value,dict) or not base <= set(value): raise InvalidDiagnostics('fields')
    stage=value['stage'];event=value['event'];code=value['classification']
    if not isinstance(stage,str) or stage not in STAGES: raise InvalidDiagnostics('stage')
    if not isinstance(event,str) or event not in {'start','pass','fail'}: raise InvalidDiagnostics('event')
    if not isinstance(code,str): raise InvalidDiagnostics('classification')
    if set(value)-base-METRICS[stage]: raise InvalidDiagnostics('fields')
    elapsed=value['elapsed_s']
    if type(elapsed) not in (int,float) or not 0 <= elapsed <= 90 or not math.isfinite(elapsed): raise InvalidDiagnostics('elapsed')
    if 'count' in value and (type(value['count']) is not int or not 0<=value['count']<=65535): raise InvalidDiagnostics('count')
    if 'returncode' in value and (type(value['returncode']) is not int or not -255<=value['returncode']<=255): raise InvalidDiagnostics('returncode')
    for field in ['default_present','dvr_present']:
        if field in value and type(value[field]) is not bool: raise InvalidDiagnostics('role')
    if event=='start':
        if set(value)!=base or code!='checking': raise InvalidDiagnostics('start')
    elif event=='pass':
        if code!='ready' or set(value)!=base|METRICS[stage]: raise InvalidDiagnostics('pass')
        if stage=='api_sources' and value['count']!=14: raise InvalidDiagnostics('source_count')
        if stage=='uwsgi' and value['count']!=2: raise InvalidDiagnostics('worker_count')
        if stage in {'postgres','celery'} and value['returncode']!=0: raise InvalidDiagnostics('returncode')
        if stage=='celery' and (value['count']!=2 or value['default_present'] is not True or value['dvr_present'] is not True): raise InvalidDiagnostics('roles')
    elif code not in FAILURES[stage]|COMMON_FAILURES: raise InvalidDiagnostics('failure')
    if event=='fail':
        if code=='migration_mismatch' and value.get('returncode')!=0:raise InvalidDiagnostics('migration_evidence')
        if code in {'postgres_command_failed','celery_command_failed'} and ('returncode' not in value or value['returncode']==0):raise InvalidDiagnostics('command_evidence')
        if code=='fresh_workers_missing' and ('count' not in value or value['count']==2):raise InvalidDiagnostics('worker_evidence')
        if code=='worker_count_exceeded' and value.get('count',0)<=16:raise InvalidDiagnostics('worker_evidence')
        if code in {'celery_roles_missing','celery_default_missing','celery_dvr_missing','celery_reply_count'}:
            if not METRICS['celery']<=set(value) or value['returncode']!=0:raise InvalidDiagnostics('Celery_evidence')
            expected=('celery_roles_missing' if not value['default_present'] and not value['dvr_present'] else 'celery_default_missing' if not value['default_present'] else 'celery_dvr_missing' if not value['dvr_present'] else 'celery_reply_count')
            if code!=expected or code=='celery_reply_count' and value['count']==2:raise InvalidDiagnostics('Celery_evidence')
    return value


class RecordStream:
    def __init__(self):
        self.records=[];self.index=0;self.open=False;self.terminal=False;self.last_elapsed=0

    def append(self, raw):
        if len(raw)>MAX_RECORD or self.terminal or self.index>=len(STAGES): raise InvalidDiagnostics('record_limit_or_terminal')
        value=decode_record(raw)
        if value['stage']!=STAGES[self.index] or value['elapsed_s']<self.last_elapsed: raise InvalidDiagnostics('sequence')
        event=value['event']
        if not self.open and event!='start' or self.open and event=='start': raise InvalidDiagnostics('sequence')
        self.last_elapsed=value['elapsed_s'];self.records.append(value)
        if event=='start':self.open=True
        elif event=='fail':self.open=False;self.terminal=True
        else:self.open=False;self.index+=1;self.terminal=self.index==len(STAGES)

    @property
    def passed(self):return self.index==len(STAGES) and self.terminal


def check():
    diagnostic = Diagnostics()
    with diagnostic.stage('api_sources'):
        pins = json.loads(Path('/opt/permanent/api-source-pins.json').read_text())
        diagnostic.metrics(count=len(pins['files']))
        for name, expected in pins['files'].items():
            if hashlib.sha256((Path('/app') / name).read_bytes()).hexdigest() != expected:
                raise ValueError('pinned_API_source_changed')
    with diagnostic.stage('postgres'):
        env = os.environ.copy()
        for pg, source in [('PGHOST','POSTGRES_HOST'), ('PGPORT','POSTGRES_PORT'),
                           ('PGDATABASE','POSTGRES_DB'), ('PGUSER','POSTGRES_USER'), ('PGPASSWORD','POSTGRES_PASSWORD')]:
            env[pg] = os.environ.get(source, '')
        env['PGOPTIONS'] = '-c default_transaction_read_only=on -c statement_timeout=10000 -c lock_timeout=3000'
        query = "SELECT count(*)||':'||md5(string_agg(app||'.'||name,',' ORDER BY app,name)) FROM django_migrations"
        p = subprocess.run(['psql','-XAt','--no-password','-v','ON_ERROR_STOP=1','-c',query],
                           env=env, capture_output=True, text=True, timeout=15)
        diagnostic.metrics(returncode=p.returncode)
        if p.returncode or p.stdout.strip() != '184:b00f51e91c5b882cd84d3b2579d074ca':
            raise ValueError('database_or_migrations_changed')
    with diagnostic.stage('redis'):
        import redis
        r = redis.Redis(host=os.environ.get('REDIS_HOST','localhost'), port=int(os.environ.get('REDIS_PORT','6379')),
                        password=os.environ.get('REDIS_PASSWORD') or None, decode_responses=True,
                        socket_connect_timeout=3, socket_timeout=3)
        if not r.ping(): raise ValueError('Redis_not_ready')
    with diagnostic.stage('uwsgi'):
        workers = []
        diagnostic.metrics(count=0)
        for key in r.scan_iter(match='live:worker:*:heartbeat', count=100):
            if len(workers) > 16: raise ValueError('unexpected_worker_count')
            try:
                pid = int(key.rsplit(':',2)[1]); age = time.time() - float(r.get(key))
                if (Path('/proc') / str(pid) / 'comm').read_text().strip() == 'uwsgi' and 0 <= age < 30 and r.ttl(key) > 0:
                    workers.append(pid)
                    diagnostic.metrics(count=len(workers))
            except (OSError, ValueError, TypeError): continue
        if len(workers) != 2: raise ValueError('two_fresh_web_workers_required')
    with diagnostic.stage('celery'):
        p = subprocess.run(['celery','-A','dispatcharr','inspect','ping','--timeout=8'],
                           cwd='/app', capture_output=True, text=True, timeout=40)
        nodes = re.findall(r'->\s+([^:\s]+):\s+OK\s+pong',p.stdout)
        diagnostic.metrics(returncode=p.returncode, count=len(nodes),
                           default_present=any(n.split('@')[0]=='default' for n in nodes),
                           dvr_present=any(n.split('@')[0]=='dvr' for n in nodes))
        if p.returncode or len(nodes) != 2 or {n.split('@')[0] for n in nodes} != {'default','dvr'}:
            raise ValueError('Celery_not_ready')

if __name__ == '__main__':
    try: check()
    except Exception: raise SystemExit('Backend readiness refused; values withheld.')
