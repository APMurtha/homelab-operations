"""Actual generated task/view/association bodies over an in-memory ORM facade.

No Django/Celery application starts, sockets, Docker, providers or real grants.
Only storage, serialization framing, client fixture data and policy witnesses are
synthetic; discovery and association success execute the hardened source bodies.
"""
import ast,copy,contextlib,json,os,sys,types,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
from test_hardening import BASE,ROOT,prepare,s
sys.path.insert(0,str(ROOT/'tools'))
from dispatcharr_provider.core import provider,Store,Refused,catalogue
from dispatcharr_provider.native import API,Adapter,Ledger,ACCOUNTS,GROUPS
from dispatcharr_provider.synthetic import Synthetic
import tempfile

class Query(list):
    def select_related(self,*args):return self
    def update(self,**values):
        for row in self:row.__dict__.update(values)
        return len(self)

class Engine:
    def __init__(self):
        self.accounts=[];self.groups=[];self.relations=[];self.requests=0
        self.categories=[{'category_id':'1','category_name':'Fixture News'},{'category_id':'2','category_name':'Fixture Other'}]
        self.fetch_error=None;self.release=MagicMock();self.renewer=MagicMock()
        engine=self
        class Missing(Exception):pass
        class Account:
            DoesNotExist=Missing;Types=types.SimpleNamespace(XC='XC');Status=types.SimpleNamespace(ERROR='error',PENDING_SETUP='pending_setup')
            def __init__(self,**kw):
                self.__dict__.update({'id':None,'is_active':True,'status':'idle','last_message':'','custom_properties':{},**kw})
            def save(self):
                if self.id is None:self.id=len(engine.accounts)+10;engine.accounts.append(self)
            def get_user_agent_string(self):return 'synthetic'
        class Accounts:
            def select_related(self,*args):return self
            def get(self,**kw):
                rows=self.filter(**kw)
                if len(rows)!=1:raise Missing()
                return rows[0]
            def filter(self,**kw):return Query(r for r in engine.accounts if all(getattr(r,k,None)==v for k,v in kw.items()))
        Account.objects=Accounts();self.model=Account
        class Group:
            def __init__(self,name):self.name=name
        class Groups:
            def filter(self,**kw):return Query(g for g in engine.groups if g.name in kw['name__in'])
            def bulk_create_provider_groups(self,names):
                rows=[]
                for name in names:
                    g=Group(name);g.id=len(engine.groups)+20;engine.groups.append(g);rows.append(g)
                return rows
        Group.objects=Groups()
        class Relation:
            def __init__(self,**kw):self.__dict__.update(kw)
        class Relations:
            def filter(self,**kw):return Query(r for r in engine.relations if r.m3u_account is kw['m3u_account'] and r.channel_group.name in kw['channel_group__name__in'])
            def bulk_create(self,rows,**kw):engine.relations.extend(rows)
            def bulk_update(self,*args):pass
        Relation.objects=Relations()
        class Client:
            def __init__(self,*args):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def get_live_categories(self):
                s.check();engine.requests+=1
                if engine.fetch_error:raise engine.fetch_error
                return copy.deepcopy(engine.categories)
        env={'M3UAccount':Account,'ChannelGroup':Group,'ChannelGroupM3UAccount':Relation,
             'XCClient':Client,'logger':MagicMock(),'timezone':types.SimpleNamespace(now=lambda:1),
             'ensure_custom_properties_dict':lambda v:v or {},'_db_query_with_retry':lambda fn,**kw:fn(),
             'acquire_task_lock':lambda *a:True,'release_task_lock':self.release,'TaskLockRenewer':lambda *a:self.renewer,
             'group_discovery_allowed':s.group_discovery_allowed,'Denied':s.Denied,
             'send_m3u_update':MagicMock(),'_set_m3u_account_status':lambda *a,**kw:None}
        source=Path(os.environ.get('DISPATCHARR_PINNED_SOURCE','/tmp/dispatcharr-native-hardening-input'))
        self.task_source=prepare.change('apps/m3u/tasks.py',(source/'apps/m3u/tasks.py').read_text())
        tree=ast.parse(self.task_source);nodes=[]
        for name in ['process_groups','refresh_m3u_groups']:
            node=copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name));node.decorator_list=[];nodes.append(node)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'generated-discovery-task','exec'),env)
        self.task=env['refresh_m3u_groups']
        # Execute the pinned real serializer's create body, not fabricated groups.
        data=json.loads((ROOT/'tools/tests/fixtures/native-group-source-evidence.json').read_text())
        fn=ast.parse(__import__('textwrap').dedent(data['fragments']['account_create_serializer']['excerpt'])).body[0]
        serializer=ast.ClassDef(name='Serializer',bases=[],keywords=[],body=[fn],decorator_list=[])
        exec(compile(ast.fix_missing_locations(ast.Module(body=[serializer],type_ignores=[])),'pinned-serializer','exec'),env)
        class Parent:
            def create(self,request,*args,**kw):
                values=copy.deepcopy(request.data);values.pop('metadata_discovery',None)
                row=env['Serializer']().create(values)
                return types.SimpleNamespace(status_code=201,data=engine.serialize(row))
        view_source=prepare.change('apps/m3u/api_views.py',(source/'apps/m3u/api_views.py').read_text())
        fn=copy.deepcopy(next(n for n in ast.walk(ast.parse(view_source)) if isinstance(n,ast.FunctionDef) and n.name=='create'))
        cls=ast.ClassDef(name='View',bases=[ast.Name(id='Parent',ctx=ast.Load())],keywords=[],body=[fn],decorator_list=[])
        env.update(Parent=Parent,job=s.job,discovery_failure=s.discovery_failure,refresh_m3u_groups=self.task,
                   Response=lambda data,status:types.SimpleNamespace(data=data,status_code=status))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),'generated-create-view','exec'),env);self.view=env['View']()
    def serialize(self,a):
        return {**copy.deepcopy(a.__dict__),'channel_groups':[{'channel_group':r.channel_group.id,'custom_properties':r.custom_properties,'enabled':r.enabled} for r in self.relations if r.m3u_account is a]}
    def create(self,body):
        utils=types.ModuleType('core.utils');utils.send_websocket_update=lambda *a:None
        with patch.dict(sys.modules,{'core':types.ModuleType('core'),'core.utils':utils}):return self.view.create(types.SimpleNamespace(FILES={},data=body))

class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.engine=Engine();self.p=provider('Synthetic','https://provider.example.invalid','synthetic-user','synthetic-secret',None,1)
        self.approval={'operations':['discover','refresh','epg'],'policy_review_sha256':'a'*64}
        self.valid=True
        def policy(key):
            if not self.valid or key!=self.p['key']:raise s.Denied()
            return self.approval
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(s,'policy',side_effect=policy));self.guard=self.stack.enter_context(patch.object(s,'Readiness'))
    def body(self,**extra):
        return {'name':self.p['name'],'server_url':self.p['server'],'username':self.p['username'],'password':self.p['password'],
                'account_type':'XC','is_active':False,'metadata_discovery':True,'enable_vod':False,
                'auto_enable_new_groups_live':False,'auto_enable_new_groups_vod':False,'auto_enable_new_groups_series':False,
                'custom_properties':{'provider_cli':{'key':self.p['key'],'owner':'dispatcharr-provider/v1/native-v1','registration':'c'*32}},**extra}
    def inactive(self):return self.engine.model.objects.get(id=self.engine.create(self.body(metadata_discovery=False)).data['id'])
    def test_inactive_creation_without_discovery_makes_no_requests(self):
        a=self.inactive();self.assertFalse(a.is_active);self.assertEqual(self.engine.requests,0);self.assertEqual(self.engine.relations,[])
    def test_actual_task_and_process_groups_persist_correct_stable_ids(self):
        result=self.engine.create(self.body());self.assertEqual(result.status_code,201)
        a=self.engine.accounts[0];self.assertFalse(a.is_active);self.assertEqual(self.engine.requests,1)
        relations=[r for r in self.engine.relations if r.m3u_account is a and 'xc_id' in r.custom_properties]
        self.assertEqual({r.custom_properties['xc_id'] for r in relations},{'1','2'})
        self.assertTrue(all(r.enabled is False for r in relations));self.assertTrue(all(r.channel_group in self.engine.groups for r in relations))
        self.assertNotEqual(next(r.channel_group.id for r in relations if r.custom_properties['xc_id']=='1'),1)
        self.assertTrue(s.CURRENT.get() is None)
    def test_ordinary_inactive_group_refresh_keeps_active_requirement(self):
        a=self.inactive();self.assertIsNone(self.engine.task(a.id)[1]);self.assertEqual(self.engine.requests,0)
        with self.assertRaises(s.Denied),s.job('refresh',a,True):pass
    def test_missing_and_expired_authorization_preserve_failed_inactive_account(self):
        for label in ['missing','expired']:
            self.valid=False;result=self.engine.create(self.body(name=label))
            self.assertEqual(result.status_code,403);self.assertEqual(result.data['discovery']['code'],'authorization_refused')
            a=self.engine.accounts[-1];self.assertFalse(a.is_active);self.assertEqual(a.status,'error')
        self.assertEqual(self.engine.requests,0)
    def test_revoked_guard_refuses_before_network(self):
        self.guard.return_value.check.side_effect=ValueError('private-policy-value')
        result=self.engine.create(self.body());self.assertEqual(result.status_code,403)
        self.assertNotIn('private-policy-value',str(result.data));self.assertEqual(self.engine.requests,0)
    def test_discovery_cannot_select_another_account_even_with_same_provider_key(self):
        a=self.inactive();b=self.inactive()
        with s.job('discover',a,True),self.assertRaises(s.Denied):self.engine.task(b.id)
        self.assertEqual(self.engine.relations,[]);self.assertEqual(self.engine.requests,0)
    def test_account_identity_change_is_refused_after_lookup(self):
        a=self.inactive()
        with s.job('discover',a,True):
            a.username='changed'
            with self.assertRaises(s.Denied):self.engine.task(a.id)
        self.engine.release.assert_called();self.assertEqual(self.engine.requests,0)
    def test_task_failure_returns_safe_recoverable_partial_failure(self):
        self.engine.fetch_error=TimeoutError('https://private.invalid/?password=PRIVATE')
        result=self.engine.create(self.body());self.assertEqual(result.status_code,502)
        self.assertEqual(result.data['discovery'],{'state':'failed','code':'discovery_incomplete'})
        self.assertTrue(result.data['account_created']);self.assertNotIn('PRIVATE',str(result.data))
        self.assertFalse(self.engine.accounts[0].is_active);self.assertEqual(self.engine.accounts[0].status,'error')
        self.assertEqual(self.engine.relations,[])
    def test_partial_association_failure_preserves_inactive_state_and_unlocks(self):
        # Failure after actual native group allocation, before relationship insert.
        with patch.object(self.engine.task.__globals__['ChannelGroupM3UAccount'].objects,'bulk_create',side_effect=ValueError('private-values')):
            result=self.engine.create(self.body())
        self.assertEqual(result.status_code,502);self.assertFalse(self.engine.accounts[0].is_active)
        self.assertTrue(self.engine.groups);self.assertEqual(self.engine.relations,[])
        self.engine.renewer.stop.assert_called_once();self.engine.release.assert_called_once()
        self.assertNotIn('private-values',str(result.data))

    def test_simulator_authorized_unauthorized_expired_and_partial_failure(self):
        cat=catalogue({'groups':[{'category_id':'1','category_name':'News'}],'channels':[],'epg_ids':[]})
        for settings,expected in [({},201),({'discovery_authorized':False},403),({'discovery_failure':'discovery_incomplete'},502)]:
            sim=Synthetic(cat,**settings);status,row=sim.exchange('POST',ACCOUNTS,self.body());self.assertEqual(status,expected)
            a=sim.data[ACCOUNTS][0];self.assertFalse(a['is_active'])
            self.assertEqual(bool(a['channel_groups']),expected==201)
            self.assertEqual(sim.exchange('POST','/api/m3u/refresh/'+str(a['id'])+'/',{})[0],400)
        sim=Synthetic(cat);sim.authorization_expires_epoch=0;self.assertEqual(sim.exchange('POST',ACCOUNTS,self.body())[0],403)
    def test_adapter_failure_blocks_duplicate_create_and_preserves_DW(self):
        cat=catalogue({'groups':[{'category_id':'1','category_name':'News'}],'channels':[{'stream_id':101,'category_id':'1','name':'One','epg_channel_id':'one'}],'epg_ids':['one']})
        dw={'id':3,'name':'DW English','channel_number':9001,'streams':[3]}
        with tempfile.TemporaryDirectory() as temp,Store(Path(temp)/'state') as store:
            sim=Synthetic(cat,snapshot={'channels':[dw]},discovery_failure='discovery_incomplete');api=API(sim);ledger=Ledger(store,self.p['key']);adapter=Adapter(api,ledger)
            for _ in range(2):
                with self.assertRaises(Refused):adapter.register(self.p,[cat['channels']['101']],1)
            self.assertEqual(sum(m=='POST' and p==ACCOUNTS for m,p,_ in sim.calls),1)
            self.assertEqual(ledger.value['operations'][0]['state'],'intent');self.assertEqual(sim.data['/api/channels/channels/'],[dw])
            with self.assertRaises(Refused):ledger.reconcile(api)
    def test_no_ambient_or_wrong_operation_can_grant_inactive_access(self):
        a=self.inactive();a.is_active=True
        with s.job('refresh',a,True):self.assertFalse(s.group_discovery_allowed(a.id))
        a.is_active=False
        with self.assertRaises(s.Denied),s.job('discover',a,False):pass
    def test_active_background_call_still_has_no_authorization(self):
        a=self.inactive();a.is_active=True
        self.assertIsNone(self.engine.task(a.id)[1])
        self.assertEqual(self.engine.requests,0);self.assertEqual(self.engine.relations,[])

    def test_retained_image_sources_remain_separate_from_unbuilt_candidate(self):
        retained=json.loads((ROOT/'configs/dispatcharr-iptv/hardened-image-integration/retained-image-contract.json').read_text())
        candidate=json.loads((BASE/'release-contract.json').read_text())
        self.assertIsNone(candidate['aio_image'])
        self.assertEqual(retained['image'],'sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be')
        self.assertEqual({k for k in candidate['source_hashes'] if candidate['source_hashes'][k]!=retained['source_hashes'][k]},
                         {'apps/m3u/api_views.py','apps/m3u/tasks.py','core/provider_security.py'})
        self.assertEqual(candidate['readiness_hashes'],retained['readiness_hashes'])

    def test_safe_exception_classifications_exclude_messages(self):
        self.assertEqual(s.discovery_failure(s.Denied()),('authorization_refused',403))
        self.assertEqual(s.discovery_failure(TimeoutError('secret')),('discovery_timeout',502))
        self.assertEqual(s.discovery_failure(ValueError('secret')),('discovery_invalid_response',502))

if __name__=='__main__':unittest.main()
