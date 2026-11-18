"""Real Django/PostgreSQL/Redis/Celery integration, only inside network-none test.

Happy provider operations use explicitly labeled loopback transport fixtures.
No real AirVPN grant, host policy, provider, production data or credentials exist.
"""
import contextlib
import hashlib
import http.server
import io
import json
import logging
import os
from pathlib import Path
import pwd
import copy
import importlib
import shutil
import stat
import socket
import ssl
import subprocess
import sys
import threading
import time
import traceback
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs,urlsplit,urlencode
from runtime_diagnostics import Diagnostics,TEST_IDS,safe_stack,safe_exception,load_snapshot

STATE=Path('/test-state')
PROVIDER_USER='synthetic-provider-private-user'
PROVIDER_PASSWORD='synthetic-provider-private-password'
REDIS_PASSWORD='synthetic-isolated-redis-password'
DIAG=None
DIAGNOSTIC_FD=None
ACTUAL_TASKS=0
BOOT={};PROCESSES=[];RESULT={'bootstrap':BOOT,'boundary':'network-none; synthetic loopback authorization only; no real AirVPN attestation'}


def child(command,user=None,log='services.log',diagnostic_fd=None):
    kwargs={}
    if diagnostic_fd is not None:kwargs['pass_fds']=(diagnostic_fd,)
    if user:
        account=pwd.getpwnam(user)
        def identity():os.setgroups([]);os.setgid(account.pw_gid);os.setuid(account.pw_uid)
        kwargs['preexec_fn']=identity
    stream=(STATE/log).open('ab');process=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,**kwargs)
    PROCESSES.append(process);return process


def wait(fn,seconds=30):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if fn():return
        time.sleep(.2)
    raise AssertionError('bounded_fixture_readiness_deadline')


def audit_network(event,args):
    # No socket is opened by the diagnostic writer; denial always exits 86.
    DIAG.audit(event,args)


def completed_task():
    global ACTUAL_TASKS
    ACTUAL_TASKS+=1
    DIAG.complete('task_execution',{'actual_completed_tasks':ACTUAL_TASKS})



def image_permissions_and_authorization():
    expected=json.loads(Path('/fixture/expected-source-hashes.json').read_text())
    modes={}
    for name,wanted in expected.items():
        path=Path('/app')/name;st=path.lstat()
        if hashlib.sha256(path.read_bytes()).hexdigest()!=wanted:raise RuntimeError('image_source_drift')
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o644:raise RuntimeError('image_source_mode_drift')
        modes[name]={'uid':st.st_uid,'gid':st.st_gid,'mode':oct(stat.S_IMODE(st.st_mode))}
        if name.startswith('core/') or name.startswith('apps/epg/') or name.startswith('apps/m3u/'):
            for directory in [path.parent,*path.parent.parents]:
                if str(directory)=='/':break
                d=directory.stat()
                if d.st_uid!=0 or d.st_gid!=0 or stat.S_IMODE(d.st_mode)!=0o755:raise RuntimeError('image_directory_mode_drift')
    BOOT['image_source_modes']=modes
    # Only this ephemeral container's synthetic root publishes assertions.
    sys.path.insert(0,'/fixture/publisher')
    from publish_policy import Publisher
    publisher=Publisher(guard='/guard-status')
    publisher.initialize();publisher.publish(BOOT['provider_key'])
    from core.provider_policy import Reader
    def probe():
        r,w=os.pipe();pid=os.fork()
        if pid==0:
            os.close(r);os.setgroups([]);os.setgid(1000);os.setuid(1000)
            try:
                row=Reader().read(BOOT['provider_key'])
                try:Path('/run/dispatcharr-provider').iterdir().__next__();private=False
                except PermissionError:private=True
                try:Path('/run/dispatcharr-provider-status/prohibited').write_text('x');write=True
                except PermissionError:write=False
                value={'public':True,'private_denied':private,'public_write_denied':not write,'generation':row['authorization_generation']}
            except Exception:value={'public':False}
            os.write(w,json.dumps(value).encode());os.close(w);os._exit(0)
        os.close(w);data=os.read(r,8192);os.close(r);os.waitpid(pid,0);return json.loads(data)
    valid=probe()
    if not valid.get('public') or not valid['private_denied'] or not valid['public_write_denied']:raise RuntimeError('UID1000_authorization_boundary_failure')
    publisher.revoke(BOOT['provider_key']);revoked=probe()
    if revoked.get('public'):raise RuntimeError('revocation_not_observed')
    publisher.publish(BOOT['provider_key']);fresh=probe()
    if fresh['generation']==valid['generation']:raise RuntimeError('generation_not_fresh')
    original=json.loads((Path('/run/dispatcharr-provider-status')/(BOOT['provider_key']+'.json')).read_text())
    negatives=Path('/run/provider-negative-fixtures');negatives.mkdir(mode=0o755)
    for kind in ['expired','wrong_generation','wrong_namespace','malformed','missing']:
        folder=negatives/kind;folder.mkdir(mode=0o755);st=folder.stat();value=copy.deepcopy(original);value.update(anchor_dev=st.st_dev,anchor_ino=st.st_ino)
        if kind=='expired':value['policy']['expires_epoch']=0
        if kind=='wrong_generation':value['guard_generation']='f'*64
        if kind=='wrong_namespace':value['policy']['netns']=[1,2]
        if kind!='missing':
            file=folder/(BOOT['provider_key']+'.json');file.write_text('{' if kind=='malformed' else json.dumps(value));file.chmod(0o644)
    BOOT['public_policy_security']={'actual_UID_GID':1000,'private_traversal_denied':True,'unprivileged_public_write_denied':True,'actual_revocation_observed':True,'fresh_generation':True,'real_AirVPN_grant':False}


def bootstrap():
    if not STATE.is_dir() or os.getuid()!=0:raise RuntimeError('owned_test_tmpfs_required')
    interfaces={p.name for p in Path('/sys/class/net').iterdir()}
    if interfaces!={'lo'} or any(line.split()[1]=='00000000' for line in Path('/proc/net/route').read_text().splitlines()[1:]):raise RuntimeError('uncertain_network_isolation')
    if Path('/var/run/docker.sock').exists() or Path('/run/dispatcharr-guard').exists():raise RuntimeError('forbidden_host_resource')
    BOOT['isolation']={'interfaces':sorted(interfaces),'external_default_route':False,'docker_socket':False}
    os.environ.clear();os.environ.update({'PATH':'/dispatcharrpy/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':str(STATE),'LANG':'C.UTF-8','DJANGO_SETTINGS_MODULE':'dispatcharr.settings','DJANGO_SECRET_KEY':'synthetic-integration-key-not-a-production-secret-000000000000000','DISPATCHARR_DEBUG':'False','DISPATCHARR_ENV':'aio','DISPATCHARR_LOG_LEVEL':'warning','POSTGRES_HOST':'127.0.0.1','POSTGRES_PORT':'5432','POSTGRES_DB':'native_integration','POSTGRES_USER':'dispatch','POSTGRES_PASSWORD':'','REDIS_HOST':'127.0.0.1','REDIS_PORT':'6379','REDIS_PASSWORD':REDIS_PASSWORD,'PYTHONDONTWRITEBYTECODE':'1'})
    os.chdir('/app');sys.path.insert(0,'/app');sys.path.insert(0,'/fixture/client')
    for path in ['/data/logs','/data/media','/data/plugins','/data/pgdata','/data/pgsocket']:
        Path(path).mkdir(parents=True,exist_ok=True)
    account=pwd.getpwnam('dispatch')
    for path in ['/data/pgdata','/data/pgsocket']:
        os.chown(path,account.pw_uid,account.pw_gid);os.chmod(path,0o700)
    pgdir=sorted(Path('/usr/lib/postgresql').glob('*/bin'),key=lambda p:int(p.parent.name))[-1]
    DIAG.begin('postgresql')
    init=child([str(pgdir/'initdb'),'-D','/data/pgdata','--auth-local=trust','--auth-host=trust','--username=dispatch','--encoding=UTF8','--no-locale'],user='dispatch')
    if init.wait(timeout=45):raise RuntimeError('isolated_initdb_failed')
    child([str(pgdir/'postgres'),'-D','/data/pgdata','-k','/data/pgsocket','-h','127.0.0.1','-p','5432','-c','shared_buffers=32MB','-c','max_connections=30'],user='dispatch')
    wait(lambda:subprocess.run([str(pgdir/'pg_isready'),'-h','127.0.0.1','-p','5432'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0)
    subprocess.run([str(pgdir/'createdb'),'-h','127.0.0.1','-U','dispatch','native_integration'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    DIAG.complete('postgresql',{'postgres_major':int(pgdir.parent.name)})
    DIAG.begin('redis')
    config=STATE/'redis.conf';config.write_text('bind 127.0.0.1\nport 6379\nsave ""\nappendonly no\nrequirepass '+REDIS_PASSWORD+'\n');config.chmod(0o600)
    child(['redis-server',str(config)])
    import redis
    r=redis.Redis(host='127.0.0.1',port=6379,password=REDIS_PASSWORD,socket_timeout=2)
    def redis_ready():
        try:return r.ping()
        except redis.RedisError:return False
    wait(redis_ready)
    DIAG.complete('redis',{'redis_ping':True})
    BOOT['postgres_version']=pgdir.parent.name;BOOT['redis_ping']=True
    for path in ['/data','/data/logs','/data/media','/data/plugins']:
        os.chown(path,1000,1000)
    appdir=STATE/'app';appdir.mkdir(mode=0o700);os.chown(appdir,1000,1000)
    os.chmod(STATE,0o755)
    # Root-private, explicitly synthetic and unusable as a production grant.
    root=Path('/run/dispatcharr-provider');root.mkdir(mode=0o700)
    public=Path('/guard-status')
    ns=Path('/proc/self/ns/net').stat();boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    guard={'schema':1,'boot_id':boot,'generation':'b'*64,'policy_sha256':'a'*64}
    for name,value in [('guard.json',guard),('grant.json',{**guard,'netns_dev':ns.st_dev,'netns_ino':ns.st_ino})]:
        path=public/name;path.write_text(json.dumps(value));path.chmod(0o644)
    server='https://provider.example.invalid'
    key=hashlib.sha256(json.dumps([server,PROVIDER_USER],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    permit={'schema':1,'server_contract':'dispatcharr-native-airvpn-v1','provider_key':key,'network_owner':'AirVPN','purpose':'IPTV_METADATA_ONLY','review_reference':'SYNTHETIC_ONLY_NO_AIRVPN_NO_PRODUCTION_GRANT','boot_id':boot,'netns':[ns.st_dev,ns.st_ino],'host_netns':[1,1],'expires_epoch':time.time()+600,'vpn_interface':'tun0','policy_review_sha256':'a'*64,'operations':['discover','refresh','epg'],'epg_url_sha256':hashlib.sha256(json.dumps(server+'/xmltv.php?'+urlencode({'username':PROVIDER_USER,'password':PROVIDER_PASSWORD}),sort_keys=True,separators=(',',':')).encode()).hexdigest(),'endpoints':[{'host':'provider.example.invalid','path':'/player_api.php','ipv4':['93.184.216.34']}]}
    permit['endpoints'].append({'host':'provider.example.invalid','path':'/xmltv.php','ipv4':['93.184.216.34']})
    path=root/(key+'.json');path.write_text(json.dumps(permit));path.chmod(0o600)
    BOOT['provider_key']=key
    image_permissions_and_authorization()


def application_bootstrap():
    if os.geteuid()!=1000 or os.getegid()!=1000:raise RuntimeError('deployed_application_uid_not_reproduced')
    os.chdir('/app');sys.path.insert(0,'/app');sys.path.insert(0,'/fixture/client')
    DIAG.begin('django_setup')
    from django.conf import settings
    settings.MEDIA_ROOT=Path('/data/media')
    sys.addaudithook(audit_network)
    import django
    django.setup();BOOT['django_version']=django.get_version()
    DIAG.complete('django_setup',{'django_version':django.get_version()})
    from django.core.management import call_command
    DIAG.begin('migrations')
    call_command('migrate',interactive=False,verbosity=0)
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*),md5(string_agg(app||'.'||name,',' ORDER BY app,name)) FROM django_migrations")
        count,fingerprint=cursor.fetchone()
    BOOT['migrations']={'count':count,'fingerprint':fingerprint}
    DIAG.complete('migrations',{'migration_count':count,'migration_fingerprint':fingerprint})
    BOOT['python']=sys.version.split()[0]


class Provider(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        query=parse_qs(urlsplit(self.path).query);path=urlsplit(self.path).path
        self.server.events.append({'path':path,'action':query.get('action',[None])[0]})
        if path=='/xmltv.php':
            from datetime import datetime,timezone,timedelta
            now=datetime.now(timezone.utc);start=(now-timedelta(hours=1)).strftime('%Y%m%d%H%M%S +0000');end=(now+timedelta(hours=2)).strftime('%Y%m%d%H%M%S +0000')
            body=('<tv><channel id="fixture.one"><display-name>Fixture One</display-name></channel><programme channel="fixture.one" start="'+start+'" stop="'+end+'"><title>Clearly synthetic programme</title></programme></tv>').encode()
        elif query.get('username')!=[PROVIDER_USER] or query.get('password')!=[PROVIDER_PASSWORD]:
            self.send_response(401);self.send_header('Content-Length','0');self.end_headers();return
        elif query.get('action')==['get_live_categories']:
            body=json.dumps([{'category_id':'1','category_name':'Fixture News'},{'category_id':'2','category_name':'Fixture Other'}]).encode()
        elif query.get('action')==['get_live_streams']:
            body=json.dumps([{'stream_id':101,'category_id':'1','name':'Fixture One','epg_channel_id':'fixture.one','stream_icon':'http://127.0.0.1/unapproved','num':101},{'stream_id':102,'category_id':'1','name':'Unselected One','epg_channel_id':'fixture.two','num':102},{'stream_id':201,'category_id':'2','name':'Unselected group','epg_channel_id':'fixture.other','num':201}]).encode()
        else:body=json.dumps({'user_info':{'auth':1,'status':'Active','username':PROVIDER_USER}}).encode()
        self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)


class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        DIAG.begin('application_setup')
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient
        from apps.channels.models import Channel,Stream,ChannelGroup
        from core.models import StreamProfile
        from dispatcharr_provider.core import provider,Store
        from dispatcharr_provider.native import API,Adapter,Ledger
        import core.provider_security as security
        from dispatcharr.celery import app
        from celery.contrib.testing.worker import start_worker
        cls.stack=contextlib.ExitStack();cls.addClassCleanup(cls.stack.close)
        cls.security=security
        cls.admin=get_user_model().objects.create_superuser(username='integration-admin',email='fixture@example.invalid',password='synthetic-admin-password')
        if hasattr(cls.admin,'user_level'):
            cls.admin.user_level=10;cls.admin.save(update_fields=['user_level'])
        cls.client=APIClient();token=cls.client.post('/api/accounts/token/',{'username':'integration-admin','password':'synthetic-admin-password'},format='json')
        if token.status_code!=200:raise RuntimeError('actual_admin_token_route_failed')
        cls.client.credentials(HTTP_AUTHORIZATION='Bearer '+token.json()['access']);cls.client.raise_request_exception=False
        profiles=[p for p in StreamProfile.objects.filter(locked=True,is_active=True) if p.command=='ffmpeg' and '-c copy' in p.parameters and '-f mpegts' in p.parameters]
        if not profiles:profiles=[StreamProfile.objects.create(name='Synthetic locked streamcopy fixture',command='ffmpeg',parameters='-i {streamUrl} -c copy -f mpegts pipe:1',locked=True,is_active=True)]
        if len(profiles)!=1:raise RuntimeError('synthetic_profile_fixture_ambiguous')
        cls.profile=profiles[0]
        group=ChannelGroup.objects.create(name='Fixture DW Group')
        for index in range(2):Channel.objects.create(name='Synthetic baseline '+str(index),channel_number=9100+index,channel_group=group,hidden_from_output=True)
        stream=Stream.objects.create(name='DW English',url='http://127.0.0.1:9199/fixture-relay-opaque',tvg_id='fixture.dw',channel_group=group)
        channel=Channel.objects.create(name='DW English',channel_number=9001,channel_group=group,tvg_id='fixture.dw',stream_profile=cls.profile,hidden_from_output=True)
        channel.streams.add(stream)
        cls.dw_id=channel.pk;cls.dw_before=cls.client.get('/api/channels/channels/'+str(channel.pk)+'/').json()
        cls.p=provider('Synthetic Native Provider','https://provider.example.invalid',PROVIDER_USER,PROVIDER_PASSWORD,None,1)
        cls.cert=STATE/'fixture.crt';cls.key=STATE/'fixture.key'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(cls.key),'-out',str(cls.cert),'-days','1','-subj','/CN=provider.example.invalid','-addext','subjectAltName=DNS:provider.example.invalid'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        os.environ['SSL_CERT_FILE']=str(cls.cert)
        cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',443),Provider);cls.server.events=[]
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(cls.cert,cls.key);cls.server.socket=ctx.wrap_socket(cls.server.socket,server_side=True)
        thread=threading.Thread(target=cls.server.serve_forever,daemon=True);thread.start();cls.addClassCleanup(cls.server.server_close);cls.addClassCleanup(cls.server.shutdown)
        class Exchange:
            simulation=True
            def exchange(self,method,path,body=None):
                response=cls.client.generic(method,path,data=json.dumps(body) if body is not None else '',content_type='application/json')
                try: data=response.json()
                except ValueError:data={}
                return response.status_code,data
        cls.store=cls.stack.enter_context(Store(STATE/'native-state'));cls.ledger=Ledger(cls.store,cls.p['key'])
        cls.api=API(Exchange());cls.adapter=Adapter(cls.api,cls.ledger,polls=30)
        @app.task(name='synthetic.runtime.queue_probe')
        def queue_probe(value):return {'value':value,'uid':os.geteuid()}
        # Actual Celery consumer + Redis broker, not eager/mocked task execution.
        app.conf.task_always_eager=False
        DIAG.begin('celery_startup')
        cls.worker=cls.stack.enter_context(start_worker(app,pool='solo',concurrency=1,perform_ping_check=False,queues=['celery','default','dvr'],loglevel='WARNING'))
        if app.conf.task_always_eager:raise RuntimeError('real_worker_required')
        DIAG.complete('celery_startup',{'worker_started':True,'eager_disabled':True})
        DIAG.begin('task_registration')
        required={'apps.m3u.tasks.refresh_single_m3u_account','apps.epg.tasks.refresh_epg_data','synthetic.runtime.queue_probe'}
        if not required<=set(app.tasks):raise RuntimeError('required_tasks_not_registered')
        DIAG.complete('task_registration',{'required_tasks_registered':True,'registered_tasks':len(app.tasks)})
        cls.capture=io.StringIO();cls.handler=logging.StreamHandler(cls.capture)
        for name in ['', 'apps','celery','core.tasks','core.utils']:
            logger=logging.getLogger(name);logger.addHandler(cls.handler);cls.addClassCleanup(logger.removeHandler,cls.handler)
        RESULT['runtime']={'actual_APIClient_JWT':True,'actual_Celery_worker':'solo thread with actual Redis broker','database':'isolated PostgreSQL','provider_endpoint':'loopback TLS only','security_positive_override':'test-only VPN-context/route/DNS fixtures and approved-IP dial redirection to loopback; actual TLS/destination/public reader; image bytes unchanged'}

    def test_01_unmodified_contract_refuses_missing_AirVPN_policy(self):
        response=self.client.get('/api/core/provider-security/',{'provider_key':self.p['key'],'epg_url_sha256':'a'*64})
        self.assertEqual(response.status_code,403);self.assertEqual(self.server.events,[])

    def test_02_default_inactive_account_creation_has_no_provider_requests(self):
        from apps.m3u.models import M3UAccount
        from django_celery_beat.models import PeriodicTask
        body={'name':'Silent Fixture','account_type':'XC','server_url':'https://silent.example.invalid','username':'silent-fixture','password':'synthetic-silent-password','is_active':False,'enable_vod':False,'auto_enable_new_groups_live':False,'auto_enable_new_groups_vod':False,'auto_enable_new_groups_series':False,'max_streams':1,'refresh_interval':24}
        response=self.client.post('/api/m3u/accounts/',body,format='json');self.assertEqual(response.status_code,201)
        pk=response.json()['id'];self.assertTrue(M3UAccount.objects.filter(pk=pk).exists());self.assertEqual(self.server.events,[])
        self.assertFalse(PeriodicTask.objects.filter(name='m3u_account-refresh-'+str(pk),enabled=True).exists())
        self.__class__.silent_id=pk

    def test_03_real_Celery_default_and_profile_tasks_make_no_provider_requests(self):
        from apps.m3u.tasks import refresh_single_m3u_account,refresh_account_profiles
        before=len(self.server.events)
        result=refresh_single_m3u_account.delay(self.silent_id);result.get(timeout=20,propagate=False)
        self.assertEqual(result.state,'FAILURE');completed_task()
        profile=refresh_account_profiles.delay(self.silent_id).get(timeout=20)
        self.assertEqual(profile,'automatic_native_profile_refresh_disabled');self.assertEqual(len(self.server.events),before);completed_task()

    def test_04_public_authorization_and_private_policy_permissions(self):
        self.assertEqual(os.geteuid(),1000)
        with self.assertRaises(PermissionError):(Path('/run/dispatcharr-provider')/(self.p['key']+'.json')).read_bytes()
        value=self.security.policy(self.p['key'])
        self.assertEqual(value['provider_key'],self.p['key']);self.assertEqual(value['review_reference'],'trusted_public_projection')
        self.assertNotIn('SYNTHETIC_ONLY',json.dumps(value))
        from core.provider_policy import Reader
        for kind in ['expired','wrong_generation','wrong_namespace','malformed','missing']:
            with self.assertRaises(Exception):Reader('/run/provider-negative-fixtures/'+kind,'/guard-status').read(self.p['key'])
        RESULT['authorization_reader']={'real_image_UID1000':True,'private_denied':True,'public_approved_projection':True,'negative_states_rejected':5,'real_AirVPN_grant':False}

    def test_05_explicit_discovery_failure_has_known_commit_and_no_blind_retry(self):
        from dispatcharr_provider.core import Refused
        from dispatcharr_provider.native import ACCOUNTS
        from dispatcharr_provider.core import provider
        p=provider('Unapproved synthetic discovery','https://unapproved.example.invalid','unapproved','synthetic-unapproved',None,1)
        from dispatcharr_provider.native import Ledger
        ledger=Ledger(self.store,p['key'])
        body={'name':p['name'],'account_type':'XC','server_url':p['server'],'username':p['username'],'password':p['password'],'is_active':False,'metadata_discovery':True,'enable_vod':False,'auto_enable_new_groups_live':False,'auto_enable_new_groups_vod':False,'auto_enable_new_groups_series':False,'max_streams':1,'refresh_interval':24,'custom_properties':{'provider_cli':{'owner':'dispatcharr-provider/v1/native-v1','key':p['key'],'registration':'c'*32}}}
        ledger.begin(p,[])
        with self.assertRaises(Refused):ledger.mutate(self.api,'POST',ACCOUNTS,body,{'name':p['name']},ACCOUNTS,statuses=(201,))
        rows=[r for r in self.api.rows(ACCOUNTS) if r.get('custom_properties',{}).get('provider_cli',{}).get('registration')=='c'*32]
        self.assertEqual(len(rows),1)
        self.assertEqual(ledger.value['operations'][-1]['state'],'intent')
        with self.assertRaises(Refused):ledger.reconcile(self.api)
        self.assertEqual(self.server.events,[])
        RESULT['uncertain_mutation']={'write_attempts':1,'HTTP_failure_after_create':True,'owned_record_confirmed_by_API':rows[0]['id'],'intent_preserved':True,'automatic_retry':False}

    def test_06_actual_native_discovery_import_and_XMLTV_mapping(self):
        from core import provider_transport as transport
        from apps.epg.models import EPGData,ProgramData
        from apps.channels.models import Stream,Channel
        original_socket=socket.socket
        class LoopbackFixtureSocket(original_socket):
            def connect_ex(self,address):
                if address==('93.184.216.34',443):address=('127.0.0.1',443)
                return super().connect_ex(address)
        def resolve(host):
            if host!='provider.example.invalid':raise RuntimeError('unapproved_synthetic_DNS_name')
            return {'93.184.216.34'}
        with patch.object(transport.MetadataHTTPS,'context_checks'),patch.object(transport.MetadataHTTPS,'vpn_route'),patch.object(transport,'resolve',side_effect=resolve),patch.object(self.security.socket,'socket',LoopbackFixtureSocket):
            summary=self.adapter.register(self.p,[{'id':'101','group':'1','name':'Fixture One','epg_id':'fixture.one','format_hint':'ts'}],self.profile.pk)
        resources=self.ledger.value['resources'];channels=resources['channels'];self.assertEqual(len(channels),1)
        native=Stream.objects.get(pk=channels[0]['stream_id']);self.assertEqual(native.stream_id,101)
        guide=EPGData.objects.get(pk=channels[0]['expected']['epg_data_id']);self.assertEqual(guide.tvg_id,'fixture.one')
        self.assertTrue(ProgramData.objects.filter(epg=guide).exists())
        self.assertEqual(self.ledger.value['phase'],'registered_inactive')
        account=self.ledger.value['resources']['account']['id']
        self.assertEqual(Channel.objects.filter(streams__m3u_account_id=account).distinct().count(),1)
        self.assertTrue(self.server.events)
        self.assertTrue(all(e['path'] in ['/player_api.php','/xmltv.php'] for e in self.server.events))
        DIAG.complete('xtream_xmltv',{'selected_channels':len(channels),'programmes':ProgramData.objects.filter(epg=guide).count()})
        RESULT['native_workflow']={'actual_supported_API':True,'actual_Xtream_discovery':True,'actual_selected_channels':1,'unselected_not_imported':True,'actual_XMLTV_import_and_programmes':True,'phase':self.ledger.value['phase'],'provider_HTTP_requests':len(self.server.events),'real_AirVPN_grant':False}

    def test_07_existing_local_custom_DW_shape_is_unchanged(self):
        current=self.client.get('/api/channels/channels/'+str(self.dw_id)+'/').json();self.assertEqual(current,self.dw_before)
        self.assertEqual(float(current['channel_number']),9001.0)

    def test_08_inactive_and_remote_EPG_jobs_remain_denied(self):
        from apps.epg.tasks import refresh_epg_data
        from apps.epg.models import EPGSource
        source=EPGSource.objects.create(name='Denied Remote Guide',source_type='xmltv',url='https://provider.example.invalid/xmltv.php',is_active=True,custom_properties={'provider_cli':{'owner':'dispatcharr-provider/v1/native-v1','key':self.p['key'],'registration':'d'*32}})
        before=len(self.server.events)
        result=refresh_epg_data.delay(source.pk,operator_requested=True);result.get(timeout=20,propagate=False)
        self.assertEqual(result.state,'FAILURE');self.assertEqual(len(self.server.events),before);completed_task()

    def test_08b_actual_worker_consumes_default_and_DVR_queues(self):
        from dispatcharr.celery import app
        for queue in ['celery','dvr']:
            result=app.send_task('synthetic.runtime.queue_probe',args=[queue],queue=queue).get(timeout=20)
            self.assertEqual(result,{'value':queue,'uid':1000});completed_task()
        RESULT['Celery_queues']=['celery','dvr']

    def test_08c_actual_uWSGI_readiness_without_media(self):
        import redis
        executable=shutil.which('uwsgi')
        self.assertTrue(executable)
        config=STATE/'uwsgi-fixture.ini'
        config.write_text('[uwsgi]\nchdir=/app\nmodule=dispatcharr.wsgi:application\nvirtualenv=/dispatcharrpy\nmaster=true\nworkers=2\nlazy-apps=true\nhttp=127.0.0.1:5656\nsocket='+str(STATE/'uwsgi.sock')+'\nvacuum=true\ndie-on-term=true\ngevent=400\ngevent-early-monkey-patch=true\nimport=dispatcharr.gevent_patch\n')
        process=child([executable,'--ini',str(config)],log='uwsgi.log')
        r=redis.Redis(host='127.0.0.1',port=6379,password=REDIS_PASSWORD,socket_timeout=2)
        def heartbeats():
            rows=[]
            for key in r.scan_iter(match='live:worker:*:heartbeat',count=100):
                try:
                    pid=int(key.rsplit(b':',2)[1]);age=time.time()-float(r.get(key))
                    if Path('/proc/'+str(pid)+'/comm').read_text().strip()=='uwsgi' and 0<=age<30 and r.ttl(key)>0:rows.append(pid)
                except (OSError,ValueError,TypeError):pass
            return len(set(rows))==2
        try:
            wait(heartbeats,30)
            import urllib.request
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:5656/',timeout=5) as response:self.assertEqual(response.status,200)
            DIAG.complete('uwsgi',{'actual_workers':2,'HTTP_status':200})
            RESULT['uWSGI']={'actual_workers':2,'fresh_Redis_heartbeats':True,'HTTP_health':200,'stock_application_module':True,'fixture_ini_without_attached_daemons':True}
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)

    def test_09_credentials_never_appear_in_captured_runtime_logs(self):
        logs=self.capture.getvalue()
        self.assertNotIn(PROVIDER_PASSWORD,logs);self.assertNotIn(PROVIDER_USER,logs)
        RESULT['redaction']={'provider_password_absent':True,'provider_username_absent':True}
        # A refused monitored socket event exits immediately; reaching this
        # assertion is not a measurement of unaudited networking operations.
        RESULT['socket_audit_refusals_in_successful_process']=0



def test_identifier(test):
    value=type(test).__name__+'.'+getattr(test,'_testMethodName','')
    return value if value in TEST_IDS else 'unassigned'


def phase_for(test):
    name=getattr(test,'_testMethodName','')
    if name.startswith('test_06_'):return 'xtream_xmltv'
    if name.startswith(('test_03_','test_08b_')):return 'task_execution'
    if name.startswith('test_08c_'):return 'uwsgi'
    return 'native_api'


class EvidenceResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.passed=set()
        self.native_tests={name for name in TEST_IDS if not name.startswith(('Integration.test_03_','Integration.test_06_','Integration.test_08b_','Integration.test_08c_'))}
    def getDescription(self,test):return test_identifier(test)
    def startTest(self,test):
        DIAG.context(phase_for(test),test_identifier(test));DIAG.record('test_started')
        super().startTest(test)
    def addSuccess(self,test):
        DIAG.context(phase_for(test),test_identifier(test));DIAG.record('test_passed');self.passed.add(test_identifier(test))
        if self.native_tests<=self.passed:DIAG.complete('native_api',{'completed_tests':len(self.native_tests)})
        super().addSuccess(test)
    def addFailure(self,test,err):
        DIAG.context(phase_for(test),test_identifier(test));DIAG.record('test_failed',reason='test_failure',stack=safe_stack(err[2]),error=err[1])
        super().addFailure(test,err)
    def addError(self,test,err):
        DIAG.context(phase_for(test),test_identifier(test));DIAG.record('test_failed',reason='test_error',stack=safe_stack(err[2]),error=err[1])
        super().addError(test,err)
    def addSkip(self,test,reason):super().addSkip(test,'skip_details_withheld')
    def _exc_info_to_string(self,err,test):
        return json.dumps({'error_class':safe_exception(err[1]),'stack':safe_stack(err[2])})


def app_main():
    global STATE,DIAG
    STATE=Path('/test-state/app')
    fd=int(os.environ['DISPATCHARR_TEST_DIAGNOSTIC_FD'])
    DIAG=Diagnostics(STATE/'diagnostics','application',emit_fd=fd,tests=TEST_IDS)
    try:
        application_bootstrap()
        runner=unittest.TextTestRunner(stream=(STATE/'unittest.log').open('w'),verbosity=2,failfast=True,descriptions=False,resultclass=EvidenceResult)
        result=runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(Integration))
        successful=result.wasSuccessful() and not result.skipped
        RESULT.update(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),tests_success=successful,application_uid=os.geteuid(),application_gid=os.getegid())
        if successful:DIAG.complete('application_suite',{'success':True,'tests_run':result.testsRun,'failures':0,'errors':0,'skips':0})
    except Exception as error:
        DIAG.exception(error,tb=error.__traceback__);RESULT.update(tests_success=False,bootstrap_error=safe_exception(error))
    RESULT['success']=RESULT.get('tests_success',False) and RESULT.get('deployment_compatible',True)
    RESULT['diagnostics']=load_snapshot(STATE/'diagnostics',os.geteuid())
    (STATE/'result.json').write_text(json.dumps(RESULT))
    return 0 if RESULT.get('tests_success') else 1



def final_acceptance_ready(value):
    required={'django_setup','migrations','celery_startup','task_registration',
        'task_execution','native_api','xtream_xmltv','uwsgi','application_suite'}
    completed=value.get('application_diagnostics',{}).get('completed',{})
    return (value.get('success') is True and value.get('tests_success') is True
        and value.get('application_exit_code')==0
        and all(completed.get('application:'+phase,{}).get('kind')=='checkpoint' for phase in required))


def main():
    global DIAG,DIAGNOSTIC_FD
    DIAGNOSTIC_FD=os.dup(1)  # A write-only evidence channel to Docker stdout.
    DIAG=Diagnostics(STATE/'supervisor-diagnostics','supervisor',emit_fd=DIAGNOSTIC_FD)
    try:
        bootstrap()
        DIAG.begin('application_setup')
        os.environ.update(USER='dispatch',LOGNAME='dispatch',HOME='/test-state/app',DISPATCHARR_TEST_DIAGNOSTIC_FD=str(DIAGNOSTIC_FD))
        app=child([sys.executable,'-B',__file__,'--app'],user='dispatch',log='application.log',diagnostic_fd=DIAGNOSTIC_FD)
        app.wait(timeout=180);RESULT['application_exit_code']=app.returncode
        # tmpfs evidence survives the child even when it calls os._exit().
        try:RESULT['application_diagnostics']=load_snapshot(STATE/'app/diagnostics',1000)
        except Exception:RESULT['application_diagnostics']={'last_checkpoint':None,'last_failure':None,'evidence_status':'missing_or_invalid'}
        result_path=STATE/'app/result.json'
        if result_path.exists():
            result=json.loads(result_path.read_text());result['services_bootstrap']=BOOT;RESULT.update(result)
        else:
            RESULT.update(success=False,bootstrap_error='application_result_missing')
            DIAG.record('incomplete',reason='application_process_abnormal')
    except Exception as error:
        DIAG.exception(error,reason='supervisor_exception',tb=error.__traceback__)
        RESULT.update(success=False,bootstrap_error=safe_exception(error))
    finally:
        for process in reversed(PROCESSES):
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        try:RESULT['memory_peak_bytes']=int(Path('/sys/fs/cgroup/memory.peak').read_text())
        except (OSError,ValueError):pass
        if final_acceptance_ready(RESULT):
            DIAG.complete('final_acceptance',{'success':True,'tests_run':RESULT.get('tests_run',0),'failures':0,'errors':0,'skips':0})
        else:RESULT['success']=False
        RESULT['supervisor_diagnostics']=load_snapshot(STATE/'supervisor-diagnostics',os.geteuid())
        print(json.dumps(RESULT))
        os.close(DIAGNOSTIC_FD)
    return 0 if RESULT.get('success') else 1

if __name__=='__main__':raise SystemExit(app_main() if '--app' in sys.argv else main())
