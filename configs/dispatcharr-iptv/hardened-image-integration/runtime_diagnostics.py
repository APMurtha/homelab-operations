"""Bounded test-only audit/checkpoint records. Never a network policy service.

No arguments, source lines, locals, URLs, environment or destination values are
serialized. Classification and permission are separate: legitimate-looking local
bytes/abstract addresses still fail the reviewed legacy allowlist.
"""
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import stat
import sys
import threading
import time

PHASES=frozenset({'bootstrap','postgresql','redis','django_setup','migrations',
    'application_setup','application_suite','celery_startup','task_registration','task_execution',
    'native_api','xtream_xmltv','uwsgi','final_acceptance'})
ROLES=frozenset({'supervisor','application'})
KINDS=frozenset({'phase_started','checkpoint','test_started','test_passed',
    'test_failed','refusal','exception','incomplete'})
MAX_RECORD=4000
MAX_STATE=65536
MAX_RECORDS=128
TAG='dispatcharr_test_diagnostic'
TEST_IDS=frozenset(['Integration.test_01_unmodified_contract_refuses_missing_AirVPN_policy', 'Integration.test_02_default_inactive_account_creation_has_no_provider_requests', 'Integration.test_03_real_Celery_default_and_profile_tasks_make_no_provider_requests', 'Integration.test_04_public_authorization_and_private_policy_permissions', 'Integration.test_05_explicit_discovery_failure_has_known_commit_and_no_blind_retry', 'Integration.test_06_actual_native_discovery_import_and_XMLTV_mapping', 'Integration.test_07_existing_local_custom_DW_shape_is_unchanged', 'Integration.test_08_inactive_and_remote_EPG_jobs_remain_denied', 'Integration.test_08b_actual_worker_consumes_default_and_DVR_queues', 'Integration.test_08c_actual_uWSGI_readiness_without_media', 'Integration.test_09_credentials_never_appear_in_captured_runtime_logs'])
DETAIL_TYPES={'postgres_major':int,'redis_ping':bool,'django_version':str,
    'migration_count':int,'migration_fingerprint':str,'worker_started':bool,
    'eager_disabled':bool,'required_tasks_registered':bool,'registered_tasks':int,
    'actual_completed_tasks':int,'completed_tests':int,'tests_run':int,
    'failures':int,'errors':int,'skips':int,'selected_channels':int,
    'programmes':int,'HTTP_status':int,'actual_workers':int,'success':bool}


REASONS=frozenset({'malformed_or_unsupported_socket_address','local_IPC_representation_not_in_legacy_allowlist',
    'loopback_representation_not_in_legacy_allowlist','private_network_destination_denied',
    'public_network_destination_denied','unknown_destination_denied','application_exception',
    'test_failure','test_error','application_process_abnormal','supervisor_exception'})
NETWORK_VALUES={'operation':{'connect','getaddrinfo'},'family':{v.name for v in socket.AddressFamily}|{'UNKNOWN'},
    'destination_class':{'unix_ipc','loopback','private','public','unknown'},
    'address_form':{'bytes','text','tuple','unknown','kernel_ipc','pathname_text','pathname_bytes','abstract_text','abstract_bytes','hostname_text','hostname_bytes'},
    'local_service':{'unspecified','postgresql_fixture','redis_fixture','HTTPS_fixture','HTTP_fixture','other_loopback'}}


def safe_network(value):
    if not isinstance(value,dict):return {}
    out={k:value[k] for k,allowed in NETWORK_VALUES.items() if isinstance(value.get(k),str) and value[k] in allowed}
    out.update({k:value[k] for k in ['valid_shape','legacy_allowed'] if type(value.get(k)) is bool})
    return out


def stack_fields(value):
    out=[]
    for frame in (value if isinstance(value,list) else [])[:8]:
        if not isinstance(frame,dict):continue
        name=frame.get('file','');function=frame.get('function','');line=frame.get('line',0)
        good=isinstance(name,str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}\.py',name)
        out.append({'file':name if good else '<redacted-file>',
            'function':function if good and isinstance(function,str) and re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,63}',function) else '<redacted-function>',
            'line':line if type(line) is int and 0<line<10000000 else 0})
    return out


def safe_details(values):
    out={}
    for name,kind in DETAIL_TYPES.items():
        value=values.get(name)
        if type(value) is not kind:continue
        if kind is int and not 0<=value<=1000000:continue
        if name=='django_version' and not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}(?:(?:a|b|rc)[0-9]+)?',value):continue
        if name=='migration_fingerprint' and not re.fullmatch('[a-f0-9]{32}',value):continue
        out[name]=value
    return out


def family(value):
    if type(value) is not int:
        try:value=int(value) if isinstance(value,socket.AddressFamily) else None
        except Exception:value=None
    allowed={int(v):v.name for v in socket.AddressFamily}
    return allowed.get(value,'UNKNOWN')


def address_info(event,args):
    """Never return raw address text, paths, ports, hostnames or their hashes."""
    result={'operation':'connect' if event=='socket.connect' else 'getaddrinfo',
        'family':'UNKNOWN','destination_class':'unknown','address_form':'unknown',
        'local_service':'unspecified','valid_shape':False,'legacy_allowed':False}
    try:
        if not isinstance(args,tuple):return result
        if event=='socket.connect':
            sock,address=args[0],args[1];f=family(getattr(sock,'family',None))
        elif event=='socket.getaddrinfo':
            address=args[0];f=family(args[2]) if len(args)>2 else 'AF_UNSPEC'
        else:return result
        result['family']=f
        if event=='socket.connect' and f=='AF_NETLINK':
            result['address_form']='kernel_ipc';return result
        host=address[0] if isinstance(address,tuple) and address else address
        result['address_form']='bytes' if isinstance(host,bytes) else 'text' if isinstance(host,str) else 'tuple' if isinstance(address,tuple) else 'unknown'
        text=host.decode('ascii') if isinstance(host,bytes) else host if isinstance(host,str) else None
        if text is None or len(text)>2048:return result
        if event=='socket.connect' and f=='AF_UNIX':
            if not isinstance(address,(str,bytes)) or not text:return result
            result.update(destination_class='unix_ipc',valid_shape=True,
                address_form=('abstract_' if text.startswith('\0') else 'pathname_')+result['address_form'])
        elif event=='socket.connect' and f=='AF_NETLINK':
            result['address_form']='kernel_ipc';return result
        else:
            if event=='socket.connect' and (f not in {'AF_INET','AF_INET6'} or not isinstance(address,tuple)
                    or len(address) not in ({2} if f=='AF_INET' else {2,4})
                    or type(address[1]) is not int or not 0<=address[1]<=65535):return result
            result['valid_shape']=True
            try:
                ip=ipaddress.ip_address(text)
                if ip.is_loopback or (isinstance(ip,ipaddress.IPv6Address) and ip.ipv4_mapped and ip.ipv4_mapped.is_loopback):result['destination_class']='loopback'
                elif ip.is_unspecified or ip.is_multicast or ip.is_reserved:result['destination_class']='unknown'
                elif ip.is_private or ip.is_link_local:result['destination_class']='private'
                elif ip.is_global:result['destination_class']='public'
            except ValueError:
                if text=='localhost':result['destination_class']='loopback'
                else:result['address_form']='hostname_'+result['address_form']
        port=address[1] if event=='socket.connect' and isinstance(address,tuple) else args[1] if event=='socket.getaddrinfo' and len(args)>1 else None
        if result['destination_class']=='loopback':
            result['local_service']={5432:'postgresql_fixture',6379:'redis_fixture',443:'HTTPS_fixture',5656:'HTTP_fixture'}.get(port,'other_loopback') if type(port) is int else 'other_loopback'
        # Preserve the literal legacy allowlist; no new local representations
        # are authorized merely because classification identifies them as local.
        result['legacy_allowed']=bool(result['valid_shape'] and isinstance(host,str)
            and ((event=='socket.connect' and f=='AF_UNIX' and host.startswith('/'))
                 or (f!='AF_UNIX' and host in ('127.0.0.1','::1','localhost'))))
    except Exception:
        result['valid_shape']=False;result['legacy_allowed']=False
    return result


def refusal_reason(info):
    if not info['valid_shape']:return 'malformed_or_unsupported_socket_address'
    if info['destination_class']=='unix_ipc':return 'local_IPC_representation_not_in_legacy_allowlist'
    if info['destination_class']=='loopback':return 'loopback_representation_not_in_legacy_allowlist'
    if info['destination_class']=='private':return 'private_network_destination_denied'
    if info['destination_class']=='public':return 'public_network_destination_denied'
    return 'unknown_destination_denied'


def safe_stack(tb=None):
    """Walk frame metadata only: never linecache, source text, args or locals."""
    frames=[]
    if tb is not None:
        while tb is not None and len(frames)<128:
            frames.append((tb.tb_frame,tb.tb_lineno));tb=tb.tb_next
    else:
        frame=sys._getframe(1)
        while frame is not None and len(frames)<32:
            frames.append((frame,frame.f_lineno));frame=frame.f_back
        frames.reverse()
    out=[]
    for frame,line in frames[-8:]:
        path=frame.f_code.co_filename
        # Known code roots only. Generated/URL/unknown filenames never escape.
        trusted=path.startswith(('/app/','/fixture/','/dispatcharrpy/','/usr/lib/python','/usr/local/lib/python')) or path.startswith(str(Path(__file__).resolve().parent)+'/')
        try:name=Path(path).name if trusted and Path(path).is_file() else ''
        except (OSError,ValueError):name=''
        name=name if isinstance(name,str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}\.py',name) else '<redacted-file>'
        function=frame.f_code.co_name
        function=function if name!='<redacted-file>' and re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,63}',function) else '<redacted-function>'
        out.append({'file':name,'function':function,'line':line if type(line) is int and 0<line<10000000 else 0})
    return out


def safe_exception(error):
    name=type(error).__name__
    return name if name in {'AssertionError','ValueError','RuntimeError','PermissionError',
        'FileNotFoundError','TimeoutError','OSError','TypeError','ImportError','ModuleNotFoundError'} else 'ApplicationError'


def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


class Diagnostics:
    def __init__(self,directory,role,emit_fd=None,tests=()):
        if role not in ROLES:raise ValueError('diagnostic_role')
        self.directory=Path(directory);self.directory.mkdir(mode=0o700,exist_ok=True)
        st=self.directory.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o700:raise ValueError('diagnostic_directory')
        self.role=role;self.emit_fd=emit_fd;self.tests=frozenset(tests)&TEST_IDS
        self.lock=threading.RLock();self.phase='bootstrap';self.test_id='unassigned'
        self.state={'schema':1,'role':role,'completed':{},'last_checkpoint':None,'last_failure':None,'sequence':0}

    def context(self,phase,test_id='unassigned'):
        with self.lock:
            self.phase=phase if isinstance(phase,str) and phase in PHASES else 'bootstrap'
            self.test_id=test_id if isinstance(test_id,str) and test_id in self.tests else 'unassigned'

    def _persist(self):
        data=encoded(self.state)
        if len(data)>MAX_STATE:raise ValueError('diagnostic_state_limit')
        path=self.directory/'snapshot.json';temporary=self.directory/('.snapshot-'+str(os.getpid())+'-'+str(threading.get_ident()))
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(fd,'wb') as f:os.fchmod(f.fileno(),0o600);f.write(data);f.flush();os.fsync(f.fileno())
            os.replace(temporary,path)
            fd=os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:os.fsync(fd)
            finally:os.close(fd)
        finally:
            try:temporary.unlink()
            except FileNotFoundError:pass

    def record(self,kind,details=None,network=None,reason=None,stack=None,error=None):
        if kind not in KINDS:raise ValueError('diagnostic_kind')
        with self.lock:
            sequence=self.state['sequence']+1
            if sequence>MAX_RECORDS:raise ValueError('diagnostic_record_limit')
            item={TAG:1,'kind':kind,'sequence':sequence,'role':self.role,'pid':os.getpid(),
                'uid':os.geteuid(),'phase':self.phase,'test_id':self.test_id,
                'thread_role':'main' if threading.current_thread() is threading.main_thread() else 'background',
                'details':safe_details(details or {})}
            if network is not None:item['network']=safe_network(network)
            if reason is not None:item['reason']=reason if isinstance(reason,str) and reason in REASONS else 'unclassified_failure'
            if stack is not None:item['stack']=stack_fields(stack)
            if error is not None:item['error_class']=safe_exception(error)
            if len(encoded(item))>MAX_RECORD:raise ValueError('diagnostic_record_size')
            self.state['sequence']=sequence
            if kind=='checkpoint':
                self.state['completed'][self.phase]=item;self.state['last_checkpoint']=item
            if kind in {'refusal','exception','test_failed','incomplete'}:self.state['last_failure']=item
            try:self._persist();item['persistence']='fsynced'
            except Exception:item['persistence']='failed'
            if self.emit_fd is not None:
                data=encoded(item)+b'\n'
                # Single bounded write keeps records separate on inherited pipes.
                try:
                    if os.write(self.emit_fd,data)!=len(data):raise OSError('short_diagnostic_write')
                except OSError:
                    if item['persistence']!='fsynced':raise ValueError('all_diagnostic_sinks_failed') from None
            if item['persistence']!='fsynced' and self.emit_fd is None:raise ValueError('no_diagnostic_sink')
            return item

    def begin(self,phase,test_id='unassigned'):
        with self.lock:
            self.context(phase,test_id);return self.record('phase_started')

    def complete(self,phase,details=None):
        with self.lock:
            self.context(phase,self.test_id);return self.record('checkpoint',details=details)

    def exception(self,error,reason='application_exception',tb=None):
        return self.record('exception',reason=reason,stack=safe_stack(tb),error=error)

    def audit(self,event,args,terminate=os._exit):
        if event not in {'socket.connect','socket.getaddrinfo'}:return
        info=address_info(event,args)
        if info['legacy_allowed']:return
        try:self.record('refusal',network=info,reason=refusal_reason(info),stack=safe_stack())
        except BaseException:
            emergency={TAG:1,'kind':'refusal','sequence':MAX_RECORDS,'role':self.role,
                'pid':os.getpid(),'uid':os.geteuid(),'phase':self.phase,'test_id':self.test_id,
                'thread_role':'unknown','details':{},'network':info,
                'reason':refusal_reason(info),'stack':safe_stack(),'persistence':'failed'}
            try:os.write(self.emit_fd if self.emit_fd is not None else 2,encoded(emergency)+b'\n')
            except OSError:pass
        finally:terminate(86)


def load_snapshot(directory,expected_uid):
    fd=os.open(Path(directory)/'snapshot.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        st=os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=expected_uid or stat.S_IMODE(st.st_mode)!=0o600 or st.st_nlink!=1:raise ValueError('unsafe_diagnostic_snapshot')
        raw=f.read(MAX_STATE+1)
    if len(raw)>MAX_STATE:raise ValueError('diagnostic_snapshot_size')
    value=json.loads(raw)
    # Rebuild from bounded diagnostic records, not arbitrary file content.
    if value.get('schema')!=1 or value.get('role') not in ROLES:raise ValueError('diagnostic_snapshot_schema')
    records=list(value.get('completed',{}).values())+[value.get('last_failure')]
    records=sorted((r for r in records if isinstance(r,dict)),key=lambda r:r.get('sequence',0) if type(r.get('sequence')) is int else 0)
    clean=recover_records('\n'.join(json.dumps(r) for r in records if r))
    return clean


def recover_records(logs):
    """Host recovery from Docker's bounded stdout log even if PID1 is killed."""
    result={'records':[],'last_checkpoint':None,'last_failure':None,'last_refusal':None,'completed':{}}
    for line in logs.splitlines():
        if len(line)>MAX_RECORD+64:continue
        try:value=json.loads(line)
        except ValueError:continue
        if not isinstance(value,dict) or type(value.get(TAG)) is not int or value.get(TAG)!=1:continue
        if any(not isinstance(value.get(k),str) for k in ['role','kind','phase']):continue
        if value['role'] not in ROLES or value['kind'] not in KINDS or value['phase'] not in PHASES:continue
        # The emitted channel is generated by this module. Reconstruct a closed
        # schema so unrelated log JSON cannot smuggle bodies/environment fields.
        safe={k:value[k] for k in [TAG,'kind','role','phase']}
        for k in ['pid','uid','sequence']:
            n=value.get(k);safe[k]=n if type(n) is int and 0<=n<2**32 else 0
        test=value.get('test_id','');safe['test_id']=test if isinstance(test,str) and test in TEST_IDS else 'unassigned'
        safe['details']=safe_details(value.get('details',{}) if isinstance(value.get('details'),dict) else {})
        safe['thread_role']=value.get('thread_role') if isinstance(value.get('thread_role'),str) and value['thread_role'] in {'main','background'} else 'unknown'
        safe['persistence']=value.get('persistence') if isinstance(value.get('persistence'),str) and value['persistence'] in {'fsynced','failed'} else 'not_in_record'
        if value['kind'] in {'refusal','exception','test_failed','incomplete'}:
            # Refusal/exception fields below are all finite whitelisted labels.
            safe['reason']=value.get('reason') if isinstance(value.get('reason'),str) and value['reason'] in REASONS else 'unclassified_failure'
            safe['network']=safe_network(value.get('network'))
            safe['stack']=stack_fields(value.get('stack'))
        result['records'].append(safe)
        if len(result['records'])>MAX_RECORDS:result['records'].pop(0)
        if safe['kind']=='checkpoint':
            result['completed'][safe['role']+':'+safe['phase']]=safe;result['last_checkpoint']=safe
        if safe['kind'] in {'refusal','exception','test_failed','incomplete'}:result['last_failure']=safe
        if safe['kind']=='refusal':result['last_refusal']=safe
    return result
