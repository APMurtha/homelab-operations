"""Read-only pinned AIO acceptance, executed after its generated environment is loaded."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


# Diagnostic projection only. No values from commands, environment or exceptions.
import selectors
import types
import ipaddress
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
            return metrics.get('celery_failure', 'celery_unclassified_failure')
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
        if metrics: record.update({k:v for k,v in self.values.items() if k!='celery_failure'})
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
    'celery': {'celery_no_replies','celery_broker_connection_failed','celery_remote_command_failed','celery_usage_or_import_failed','celery_unclassified_failure','celery_roles_missing','celery_default_missing','celery_dvr_missing','celery_reply_count'},
}
COMMON_FAILURES = {'file_missing','file_permission','invalid_manifest','dependency_unavailable','subprocess_timeout','unexpected_exception'}
CELERY_CODES = {'celery_no_replies','celery_broker_connection_failed','celery_remote_command_failed','celery_usage_or_import_failed','celery_unclassified_failure'}
COMMAND_METRICS = {'command_start_s','command_end_s','command_elapsed_s','stdout_bytes','stderr_bytes',
                   'output_complete','reply_output_valid','broker_comparison_known','broker_endpoint_equal',
                   'broker_transport_equal','broker_auth_equal','broker_namespace_equal'}
OUTPUT_LIMIT = 16384

METRICS = {'api_sources' : {'count'}, 'postgres': {'returncode'}, 'redis': set(),
           'uwsgi': {'count'}, 'celery': {'count','returncode','default_present','dvr_present'} | COMMAND_METRICS}


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
    for field in ['default_present','dvr_present','output_complete','reply_output_valid','broker_comparison_known','broker_endpoint_equal','broker_transport_equal','broker_auth_equal','broker_namespace_equal']:
        if field in value and type(value[field]) is not bool: raise InvalidDiagnostics('role')
    if stage=='celery':
        for field in ['command_start_s','command_end_s','command_elapsed_s']:
            if field in value and (type(value[field]) not in (int,float) or not math.isfinite(value[field]) or not 0<=value[field]<=2**40):raise InvalidDiagnostics('command_clock')
        for field in ['stdout_bytes','stderr_bytes']:
            if field in value and (type(value[field]) is not int or not 0<=value[field]<=OUTPUT_LIMIT+1):raise InvalidDiagnostics('command_bytes')
        if {'count','default_present','dvr_present'}<=set(value) and value['count']<int(value['default_present'])+int(value['dvr_present']):raise InvalidDiagnostics('role_count')
        if COMMAND_METRICS<=set(value):
            if value['command_end_s']<value['command_start_s'] or abs(value['command_end_s']-value['command_start_s']-value['command_elapsed_s'])>0.000003 or value['command_elapsed_s']>50:raise InvalidDiagnostics('command_clock')
            if not value['broker_comparison_known'] and any(value[k] for k in ['broker_endpoint_equal','broker_transport_equal','broker_auth_equal','broker_namespace_equal']):raise InvalidDiagnostics('broker_unknown')
            if value['output_complete'] and max(value['stdout_bytes'],value['stderr_bytes'])>OUTPUT_LIMIT:raise InvalidDiagnostics('command_bytes')
    if event=='start':
        if set(value)!=base or code!='checking': raise InvalidDiagnostics('start')
    elif event=='pass':
        if code!='ready' or set(value)!=base|METRICS[stage]: raise InvalidDiagnostics('pass')
        if stage=='api_sources' and value['count']!=14: raise InvalidDiagnostics('source_count')
        if stage=='uwsgi' and value['count']!=2: raise InvalidDiagnostics('worker_count')
        if stage in {'postgres','celery'} and value['returncode']!=0: raise InvalidDiagnostics('returncode')
        if stage=='celery' and (not value['output_complete'] or not value['reply_output_valid'] or value['count']!=2 or value['default_present'] is not True or value['dvr_present'] is not True): raise InvalidDiagnostics('roles')
    elif code not in FAILURES[stage]|COMMON_FAILURES: raise InvalidDiagnostics('failure')
    if event=='fail':
        if code=='migration_mismatch' and value.get('returncode')!=0:raise InvalidDiagnostics('migration_evidence')
        if code in {'postgres_command_failed','celery_command_failed'} and ('returncode' not in value or value['returncode']==0):raise InvalidDiagnostics('command_evidence')
        if code=='fresh_workers_missing' and ('count' not in value or value['count']==2):raise InvalidDiagnostics('worker_evidence')
        if code=='worker_count_exceeded' and value.get('count',0)<=16:raise InvalidDiagnostics('worker_evidence')
        if stage=='celery' and code in CELERY_CODES:
            if not METRICS['celery']<=set(value):raise InvalidDiagnostics('Celery_evidence')
            if code!='celery_unclassified_failure' and (value['stdout_bytes']!=0 or value['stderr_bytes']==0 or value['reply_output_valid'] or not value['output_complete'] or value['count']!=0 or value['returncode'] not in ({2} if code=='celery_usage_or_import_failed' else {69})):raise InvalidDiagnostics('Celery_evidence')
            if value['returncode']==0 and value['count']==2 and value['default_present'] and value['dvr_present'] and value['output_complete'] and value['reply_output_valid']:raise InvalidDiagnostics('Celery_failure_contradiction')
        if stage=='celery' and code in FAILURES['celery']-CELERY_CODES:
            if not METRICS['celery']<=set(value) or value['returncode']!=0 or not value['output_complete'] or not value['reply_output_valid']:raise InvalidDiagnostics('Celery_evidence')
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



def classify_celery(returncode, stdout, stderr, complete=True):
    # Source-reviewed Celery 5.6.3/Click text only. No error text is returned.
    unknown='celery_unclassified_failure'
    if not complete or not isinstance(stdout,str) or not isinstance(stderr,str):return unknown
    try:
        if len(stdout.encode('utf-8'))>OUTPUT_LIMIT or len(stderr.encode('utf-8'))>OUTPUT_LIMIT:return unknown
    except UnicodeError:return unknown
    if stdout or not stderr.endswith('\n') or any(not c.isprintable() and c!='\n' for c in stderr):return unknown
    if returncode==69:
        if stderr=='Error: No nodes replied within time constraint\n':return 'celery_no_replies'
        prefixes={
            'celery_broker_connection_failed':'Error: Could not connect to the message broker. Please make sure your broker (e.g., RabbitMQ or Redis) is running and the connection settings are correct. Reason: ',
            'celery_remote_command_failed':'Error: Unable to run the `inspect ping` command. Reason: ',
        }
        for code,prefix in prefixes.items():
            if stderr.startswith(prefix):
                tail=stderr[len(prefix):-1]
                if tail.strip() and tail==tail.strip() and not any(x in tail.lower() for x in ['[truncated]','<truncated>','...','…','\ufffd']) and '\n' not in tail and '\r' not in tail and not any(x in tail for x in ['Error:','Usage:','Traceback']):return code
    if returncode==2:
        error='Error: \nUnable to load celery application.\nThe module dispatcharr was not found.\n'
        usage="Usage: celery [OPTIONS] COMMAND [ARGS]...\nTry 'celery --help' for help.\n\n"
        if stderr in (error,usage+error):return 'celery_usage_or_import_failed'
    return unknown


def valid_reply_output(stdout, stderr):
    # Fixed human formatter, no unrecognized logs/errors or terminal controls.
    if stderr or any(not c.isprintable() and c!='\n' for c in stdout):return False
    match=re.fullmatch(r'(?P<replies>(?:->\s+[^:\s]+:\s+OK\s+pong\s*)+)(?:(?P<count>[0-9]+) nodes? online\.\s*)?',stdout)
    if not match:return False
    return match['count'] is None or int(match['count'])==len(re.findall(r'->\s+([^:\s]+):\s+OK\s+pong',match['replies']))


def celery_classification(process, nodes, complete):
    if process.returncode==0 and complete and valid_reply_output(process.stdout,process.stderr):
        roles={n.split('@')[0] for n in nodes}
        if 'default' not in roles and 'dvr' not in roles:return 'celery_roles_missing'
        if 'default' not in roles:return 'celery_default_missing'
        if 'dvr' not in roles:return 'celery_dvr_missing'
        if len(nodes)!=2:return 'celery_reply_count'
    return classify_celery(process.returncode,process.stdout,process.stderr,complete)


def compare_brokers(snapshots=None):
    # Only already-resolved, authoritative effective configuration is accepted.
    # No environment inference, Django import, process scan, DNS or broker I/O.
    result={k:False for k in ['broker_comparison_known','broker_endpoint_equal','broker_transport_equal','broker_auth_equal','broker_namespace_equal']}
    def normalize(value):
        required={'transport','host','port','database','username','password','control_exchange','global_keyprefix','fanout_prefix','fanout_patterns','tls'}
        if not isinstance(value,dict) or set(value)!=required:raise ValueError()
        if value['transport'] not in {'redis','rediss'}:raise ValueError()
        if not isinstance(value['host'],str) or not 1<=len(value['host'])<=253 or not re.fullmatch(r'[a-zA-Z0-9.:-]+',value['host']):raise ValueError()
        host=value['host'].lower().rstrip('.')
        try:host=str(ipaddress.ip_address(host))
        except ValueError:pass
        if type(value['port']) is not int or not 1<=value['port']<=65535:raise ValueError()
        if type(value['database']) is not int or not 0<=value['database']<=65535:raise ValueError()
        for field in ['username','password','control_exchange','global_keyprefix']:
            if not isinstance(value[field],str) or len(value[field])>8192:raise ValueError()
        if any(type(value[k]) is not bool for k in ['fanout_prefix','fanout_patterns']):raise ValueError()
        if ':' in host:
            try:ipaddress.ip_address(host)
            except ValueError:raise ValueError()
        tls=value['tls']
        if value['transport']=='redis':
            if tls is not None:raise ValueError()
            tls_identity=None
        else:
            if not isinstance(tls,dict) or set(tls)!={'verify','ca_identity','client_identity'} or tls['verify'] is not True:raise ValueError()
            if any(not isinstance(tls[k],str) or len(tls[k])>8192 for k in ['ca_identity','client_identity']):raise ValueError()
            tls_identity=(True,tls['ca_identity'],tls['client_identity'])
        return {'endpoint':(host,value['port']), 'transport':(value['transport'],tls_identity),
                'auth':(value['username'],value['password']),
                'namespace':(value['database'],value['control_exchange'],value['global_keyprefix'],value['fanout_prefix'],value['fanout_patterns'])}
    try:
        if not isinstance(snapshots,dict) or set(snapshots)!={'inspection','default','dvr'}:return result
        values={k:normalize(v) for k,v in snapshots.items()}
        for field in ['endpoint','transport','auth','namespace']:
            result['broker_'+field+'_equal']=all(values['inspection'][field]==values[k][field] for k in ['default','dvr'])
        result['broker_comparison_known']=True
    except Exception:return {k:False for k in result}
    return result


def celery_capture(args, **kwargs):
    # Preserve the one invocation/40s bound, but cap both child pipes in memory.
    timeout=kwargs['timeout'];started=time.monotonic();buffers=[bytearray(),bytearray()];sizes=[0,0];complete=True
    process=None;selector=selectors.DefaultSelector()
    try:
        process=subprocess.Popen(args,cwd=kwargs['cwd'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for i,pipe in enumerate([process.stdout,process.stderr]):selector.register(pipe,selectors.EVENT_READ,i)
        while selector.get_map():
            remaining=timeout-(time.monotonic()-started)
            if remaining<=0:raise subprocess.TimeoutExpired(args,timeout)
            for key,_ in selector.select(remaining):
                data=os.read(key.fileobj.fileno(),4096);i=key.data
                if not data:selector.unregister(key.fileobj);continue
                sizes[i]=min(OUTPUT_LIMIT+1,sizes[i]+len(data));buffers[i].extend(data[:max(0,OUTPUT_LIMIT-len(buffers[i]))])
                if sizes[i]>OUTPUT_LIMIT:
                    complete=False;process.kill();selector.close();break
            if not complete:break
        code=process.wait(timeout=max(.001,timeout-(time.monotonic()-started)))
        try:out,err=[bytes(b).decode('utf-8','strict') for b in buffers]
        except UnicodeError:out=err='';complete=False
        return types.SimpleNamespace(returncode=code,stdout=out,stderr=err,complete=complete,stdout_bytes=sizes[0],stderr_bytes=sizes[1])
    finally:
        if process is not None:
            if process.poll() is None:process.kill();process.wait(timeout=1)
            for pipe in [process.stdout,process.stderr]:pipe.close()
        selector.close()


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
        command_start=time.monotonic()
        try:
            p = celery_capture(['celery','-A','dispatcharr','inspect','ping','--timeout=8'],
                           cwd='/app', capture_output=True, text=True, timeout=40)
        finally:
            command_end=time.monotonic()
            diagnostic.metrics(command_start_s=round(command_start,6),command_end_s=round(command_end,6),command_elapsed_s=round(command_end-command_start,6),**compare_brokers())
        complete=getattr(p,'complete',True)
        diagnostic.metrics(stdout_bytes=min(OUTPUT_LIMIT+1,getattr(p,'stdout_bytes',len(p.stdout.encode('utf-8')))),stderr_bytes=min(OUTPUT_LIMIT+1,getattr(p,'stderr_bytes',len(p.stderr.encode('utf-8')))),output_complete=complete)
        diagnostic.metrics(reply_output_valid=valid_reply_output(p.stdout,p.stderr))
        nodes = re.findall(r'->\s+([^:\s]+):\s+OK\s+pong',p.stdout)
        diagnostic.metrics(returncode=p.returncode, count=len(nodes),
                           default_present=any(n.split('@')[0]=='default' for n in nodes),
                           dvr_present=any(n.split('@')[0]=='dvr' for n in nodes))
        diagnostic.metrics(celery_failure=celery_classification(p,nodes,complete))
        if not complete or (p.returncode==0 and not valid_reply_output(p.stdout,p.stderr)): raise ValueError('Celery_not_ready')
        if p.returncode or len(nodes) != 2 or {n.split('@')[0] for n in nodes} != {'default','dvr'}:
            raise ValueError('Celery_not_ready')

if __name__ == '__main__':
    try: check()
    except Exception: raise SystemExit('Backend readiness refused; values withheld.')
