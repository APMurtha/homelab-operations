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

STATE=Path('/test-state')
PROVIDER_USER='synthetic-provider-private-user'
PROVIDER_PASSWORD='synthetic-provider-private-password'
REDIS_PASSWORD='synthetic-isolated-redis-password'
BOOT={};PROCESSES=[];RESULT={'bootstrap':BOOT,'boundary':'network-none; synthetic loopback authorization only; no real AirVPN attestation'}


def child(command,user=None,log='services.log'):
    kwargs={}
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
    init=child([str(pgdir/'initdb'),'-D','/data/pgdata','--auth-local=trust','--auth-host=trust','--username=dispatch','--encoding=UTF8','--no-locale'],user='dispatch')
    if init.wait(timeout=45):raise RuntimeError('isolated_initdb_failed')
    child([str(pgdir/'postgres'),'-D','/data/pgdata','-k','/data/pgsocket','-h','127.0.0.1','-p','5432','-c','shared_buffers=32MB','-c','max_connections=30'],user='dispatch')
    wait(lambda:subprocess.run([str(pgdir/'pg_isready'),'-h','127.0.0.1','-p','5432'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0)
    subprocess.run([str(pgdir/'createdb'),'-h','127.0.0.1','-U','dispatch','native_integration'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    config=STATE/'redis.conf';config.write_text('bind 127.0.0.1\nport 6379\nsave ""\nappendonly no\nrequirepass '+REDIS_PASSWORD+'\n');config.chmod(0o600)
    child(['redis-server',str(config)])
    import redis
    r=redis.Redis(host='127.0.0.1',port=6379,password=REDIS_PASSWORD,socket_timeout=2)
    def redis_ready():
        try:return r.ping()
        except redis.RedisError:return False
    wait(redis_ready)
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
    path=root/(key+'.json');path.write_text(json.dumps(permit));path.chmod(0o600)


def application_bootstrap():
    if os.geteuid()!=1000 or os.getegid()!=1000:raise RuntimeError('deployed_application_uid_not_reproduced')
    os.chdir('/app');sys.path.insert(0,'/app');sys.path.insert(0,'/fixture/client')
    from django.conf import settings
    settings.MEDIA_ROOT=Path('/data/media')
    import django
    django.setup();BOOT['django_version']=django.get_version()
    from django.core.management import call_command
    call_command('migrate',interactive=False,verbosity=0)
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*),md5(string_agg(app||'.'||name,',' ORDER BY app,name)) FROM django_migrations")
        count,fingerprint=cursor.fetchone()
    BOOT['migrations']={'count':count,'fingerprint':fingerprint}
    BOOT['python']=sys.version.split()[0]


class Provider(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        query=parse_qs(urlsplit(self.path).query);path=urlsplit(self.path).path
        self.server.events.append({'path':path,'action':query.get('action',[None])[0]})
        if path=='/xmltv.php':
            body=b'<tv><channel id="fixture.one"><display-name>Fixture One</display-name><icon src="http://127.0.0.1/unapproved"/></channel><programme channel="fixture.one" start="20261118000000 +0000" stop="20261119000000 +0000"><title>Real synthetic fixture programme</title></programme></tv>'
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
        cls.profile=next(p for p in StreamProfile.objects.filter(locked=True,is_active=True) if p.command=='ffmpeg' and '-c copy' in p.parameters and '-f mpegts' in p.parameters)
        group=ChannelGroup.objects.create(name='Fixture DW Group')
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
        # Actual Celery consumer + Redis broker, not eager/mocked task execution.
        app.conf.task_always_eager=False
        cls.worker=cls.stack.enter_context(start_worker(app,pool='solo',concurrency=1,perform_ping_check=False,queues=['celery','default','dvr'],loglevel='WARNING'))
        cls.capture=io.StringIO();cls.handler=logging.StreamHandler(cls.capture)
        for name in ['', 'apps','celery','core.tasks','core.utils']:
            logger=logging.getLogger(name);logger.addHandler(cls.handler);cls.addClassCleanup(logger.removeHandler,cls.handler)
        RESULT['runtime']={'actual_APIClient_JWT':True,'actual_Celery_worker':'solo thread with actual Redis broker','database':'isolated PostgreSQL','provider_endpoint':'loopback TLS only','security_positive_override':'test-only MetadataHTTPS context/authorize; image source unchanged'}

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
        self.assertEqual(result.state,'FAILURE')
        profile=refresh_account_profiles.delay(self.silent_id).get(timeout=20)
        self.assertEqual(profile,'automatic_native_profile_refresh_disabled');self.assertEqual(len(self.server.events),before)

    def test_04_root_policy_is_unreadable_at_actual_deployed_uid(self):
        from dispatcharr_provider.core import Refused
        self.assertEqual(os.geteuid(),1000)
        path=Path('/run/dispatcharr-provider')/(self.p['key']+'.json')
        with self.assertRaises(PermissionError):path.read_bytes()
        # Public guard/grant reader works at UID 1000; policy traversal does not.
        reader=self.security.Readiness('/guard-status','a'*64)
        self.assertEqual(reader.check(),'b'*64)
        before=len(self.server.events)
        with self.assertRaises(Refused):
            self.adapter.register(self.p,[{'id':'101','group':'1','name':'Fixture One','epg_id':'fixture.one','format_hint':'ts'}],self.profile.pk)
        self.assertIsNone(self.ledger.value);self.assertEqual(len(self.server.events),before)
        RESULT['blockers']=['UID_1000_CANNOT_READ_ROOT_0700_0600_PROVIDER_POLICY']
        RESULT['deployment_compatible']=False
        RESULT['native_remote_workflow']='BLOCKED before mutation by actual server contract gate'

    def test_05_explicit_discovery_failure_has_known_commit_and_no_blind_retry(self):
        from dispatcharr_provider.core import Refused
        from dispatcharr_provider.native import ACCOUNTS
        body={'name':self.p['name'],'account_type':'XC','server_url':self.p['server'],'username':self.p['username'],'password':self.p['password'],'is_active':False,'metadata_discovery':True,'enable_vod':False,'auto_enable_new_groups_live':False,'auto_enable_new_groups_vod':False,'auto_enable_new_groups_series':False,'max_streams':1,'refresh_interval':24,'custom_properties':{'provider_cli':{'owner':'dispatcharr-provider/v1/native-v1','key':self.p['key'],'registration':'c'*32}}}
        self.ledger.begin(self.p,[])
        with self.assertRaises(Refused):self.ledger.mutate(self.api,'POST',ACCOUNTS,body,{'name':self.p['name']},ACCOUNTS,statuses=(201,))
        rows=[r for r in self.api.rows(ACCOUNTS) if r.get('custom_properties',{}).get('provider_cli',{}).get('registration')=='c'*32]
        self.assertEqual(len(rows),1)
        self.assertEqual(self.ledger.value['operations'][-1]['state'],'intent')
        with self.assertRaises(Refused):self.ledger.reconcile(self.api)
        self.assertEqual(self.server.events,[])
        RESULT['uncertain_mutation']={'write_attempts':1,'HTTP_failure_after_create':True,'owned_record_confirmed_by_API':rows[0]['id'],'intent_preserved':True,'automatic_retry':False}

    def test_06_real_group_selection_channel_import_and_local_XMLTV_mapping(self):
        from apps.m3u.models import M3UAccount
        from apps.channels.models import Stream,ChannelGroup,ChannelGroupM3UAccount
        from apps.epg.models import EPGSource,EPGData,ProgramData
        from django_celery_beat.models import PeriodicTask
        from datetime import datetime,timezone,timedelta
        # Discovery is blocked. Seed only synthetic native metadata through ORM;
        # the following group/channel/EPG operations use actual supported APIs.
        account=M3UAccount.objects.create(name='Seeded Native Metadata Fixture',account_type='XC',server_url='https://seeded.example.invalid',username='seeded',password='synthetic-seeded-password',is_active=True,custom_properties={'enable_vod':False,'auto_enable_new_groups_live':False,'auto_enable_new_groups_vod':False,'auto_enable_new_groups_series':False})
        group=ChannelGroup.objects.create(name='Seeded Fixture Group')
        ChannelGroupM3UAccount.objects.create(m3u_account=account,channel_group=group,enabled=False,auto_channel_sync=False,custom_properties={'xc_id':'1'})
        stream=Stream.objects.create(name='Seeded Fixture Channel',url='https://seeded.example.invalid/live/fixture/fixture/101.ts',m3u_account=account,channel_group=group,stream_id=101,tvg_id='fixture.one')
        response=self.client.patch('/api/m3u/accounts/'+str(account.pk)+'/group-settings/',{'group_settings':[{'channel_group':group.pk,'enabled':True,'auto_channel_sync':False,'custom_properties':{'xc_id':'1'}}]},format='json');self.assertEqual(response.status_code,200)
        response=self.client.get('/api/m3u/accounts/'+str(account.pk)+'/');rels=response.json()['channel_groups'];self.assertTrue(next(r for r in rels if r['channel_group']==group.pk)['enabled'])
        now=datetime.now(timezone.utc);start=(now-timedelta(hours=1)).strftime('%Y%m%d%H%M%S +0000');end=(now+timedelta(hours=2)).strftime('%Y%m%d%H%M%S +0000')
        path=Path('/data/media/fixture.xml');path.write_text('<tv><channel id="fixture.one"><display-name>Clearly Synthetic Guide</display-name></channel><programme channel="fixture.one" start="'+start+'" stop="'+end+'"><title>Clearly Synthetic Programme</title></programme></tv>')
        response=self.client.post('/api/epg/sources/',{'name':'Local Synthetic XMLTV','source_type':'xmltv','url':'','file_path':str(path),'is_active':False,'refresh_interval':0},format='json');self.assertEqual(response.status_code,201);pk=response.json()['id']
        self.assertEqual(self.client.patch('/api/epg/sources/'+str(pk)+'/',{'is_active':True},format='json').status_code,200)
        self.assertEqual(self.client.post('/api/epg/import/',{'id':pk,'force':False},format='json').status_code,202)
        def parsed():
            row=EPGSource.objects.get(pk=pk)
            if row.status=='error':raise AssertionError('local_XMLTV_import_error')
            return row.status=='success' and EPGData.objects.filter(epg_source_id=pk,tvg_id='fixture.one').exists()
        wait(parsed,30)
        guide=EPGData.objects.get(epg_source_id=pk,tvg_id='fixture.one')
        response=self.client.post('/api/channels/channels/',{'name':'Seeded Fixture Channel','streams':[stream.pk],'channel_group_id':group.pk,'tvg_id':'fixture.one','epg_data_id':guide.pk,'stream_profile_id':self.profile.pk,'hidden_from_output':True,'channel_profile_ids':[]},format='json');self.assertEqual(response.status_code,201)
        channel=response.json();self.assertEqual(channel['streams'],[stream.pk]);self.assertEqual(channel['epg_data_id'],guide.pk)
        self.assertEqual(self.client.post('/api/epg/import/',{'id':pk,'force':False},format='json').status_code,202)
        wait(lambda:ProgramData.objects.filter(epg=guide).exists(),30)
        self.assertFalse(PeriodicTask.objects.filter(name='m3u_account-refresh-'+str(account.pk),enabled=True).exists())
        RESULT['API_components']={'metadata_fixture_seeded_by_ORM':True,'native_network_discovery':False,'group_selection_API':True,'selective_channel_API':True,'local_XMLTV_import_real_worker':True,'EPG_native_ID_mapping':True,'programme_count':ProgramData.objects.filter(epg=guide).count(),'provider_HTTP_requests':len(self.server.events)}

    def test_07_existing_local_custom_DW_shape_is_unchanged(self):
        current=self.client.get('/api/channels/channels/'+str(self.dw_id)+'/').json();self.assertEqual(current,self.dw_before)
        self.assertEqual(float(current['channel_number']),9001.0)

    def test_08_inactive_and_remote_EPG_jobs_remain_denied(self):
        from apps.epg.tasks import refresh_epg_data
        from apps.epg.models import EPGSource
        source=EPGSource.objects.create(name='Denied Remote Guide',source_type='xmltv',url='https://provider.example.invalid/xmltv.php',is_active=True,custom_properties={'provider_cli':{'owner':'dispatcharr-provider/v1/native-v1','key':self.p['key'],'registration':'d'*32}})
        before=len(self.server.events)
        result=refresh_epg_data.delay(source.pk,operator_requested=True);result.get(timeout=20,propagate=False)
        self.assertEqual(result.state,'FAILURE');self.assertEqual(len(self.server.events),before)

    def test_09_credentials_never_appear_in_captured_runtime_logs(self):
        logs=self.capture.getvalue()
        self.assertNotIn(PROVIDER_PASSWORD,logs);self.assertNotIn(PROVIDER_USER,logs)
        RESULT['redaction']={'provider_password_absent':True,'provider_username_absent':True}


def app_main():
    global STATE
    STATE=Path('/test-state/app')
    try:
        application_bootstrap()
        runner=unittest.TextTestRunner(stream=(STATE/'unittest.log').open('w'),verbosity=2,failfast=True)
        result=runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(Integration))
        RESULT.update(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),tests_success=result.wasSuccessful(),application_uid=os.geteuid(),application_gid=os.getegid())
        if result.failures or result.errors:
            RESULT['failure_detail']=(result.failures+result.errors)[0][1][-6000:]
    except Exception as error:RESULT.update(tests_success=False,bootstrap_error=type(error).__name__,failure_detail=traceback.format_exc()[-6000:])
    for secret in [PROVIDER_USER,PROVIDER_PASSWORD,REDIS_PASSWORD]:
        if 'failure_detail' in RESULT:RESULT['failure_detail']=RESULT['failure_detail'].replace(secret,'[synthetic-secret-redacted]')
    RESULT['success']=RESULT.get('tests_success',False) and RESULT.get('deployment_compatible',True)
    (STATE/'result.json').write_text(json.dumps(RESULT))
    return 0 if RESULT.get('tests_success') else 1


def main():
    try:
        bootstrap()
        os.environ.update(USER='dispatch',LOGNAME='dispatch',HOME='/test-state/app')
        app=child([sys.executable,'-B',__file__,'--app'],user='dispatch',log='application.log')
        app.wait(timeout=180)
        result_path=STATE/'app/result.json'
        if result_path.exists():
            result=json.loads(result_path.read_text());result['services_bootstrap']=BOOT;RESULT.update(result)
        else:RESULT.update(success=False,bootstrap_error='application_result_missing',failure_detail=(STATE/'application.log').read_text()[-4000:])
    except Exception as error:RESULT.update(success=False,bootstrap_error=type(error).__name__,failure_detail=traceback.format_exc()[-4000:])
    finally:
        for process in reversed(PROCESSES):
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        try:RESULT['memory_peak_bytes']=int(Path('/sys/fs/cgroup/memory.peak').read_text())
        except (OSError,ValueError):pass
        print(json.dumps(RESULT))
    return 0 if RESULT.get('tests_success') else 1

if __name__=='__main__':raise SystemExit(app_main() if '--app' in sys.argv else main())
