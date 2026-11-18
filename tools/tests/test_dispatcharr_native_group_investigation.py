"""Source-backed offline counterexample; no sockets, Django, Celery or Docker.

Exact approved view/task excerpts run with in-memory storage and lock/job stubs.
The task excerpt stops before category processing: an active control only proves
it passes the early query, not that a full active discovery would be authorized.
"""
import ast
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import textwrap
import types
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'configs/dispatcharr-iptv/hardened-image-integration'))
from dispatcharr_provider.core import Store, Refused, provider, catalogue
from dispatcharr_provider.native import API, Adapter, Ledger, ACCOUNTS, GROUPS, CHANNELS, SOURCES
from dispatcharr_provider.synthetic import Synthetic
import runtime_test as runtime

EVIDENCE=json.loads((Path(__file__).parent/'fixtures/native-group-source-evidence.json').read_text())
FRAGMENTS=EVIDENCE['fragments']
SELECTED={'id':'101','group':'1','name':'Fixture One','epg_id':'fixture.one','format_hint':'ts'}
CATALOGUE=catalogue({'groups':[{'category_id':'1','category_name':'Fixture News'}, {'category_id':'2','category_name':'Fixture Other'}],
                     'channels':[{'stream_id':101,'category_id':'1','name':'Fixture One','epg_channel_id':'fixture.one'}], 'epg_ids':['fixture.one']})
DW={'id':3,'name':'DW English','streams':[3],'channel_number':9001,'tvg_id':'dw','uuid':'synthetic-dw'}


class SourcePath(Synthetic):
    """Replace the simulator's optimistic account creation with exact source flow."""
    def __init__(self):
        super().__init__(copy.deepcopy(CATALOGUE),snapshot={'channels':[DW]})
        self.queries=[];self.job_calls=[];self.group_results=[]
        self.renewer=Mock();self.release=Mock()
        transport=self
        class Missing(Exception):pass
        class Manager:
            def select_related(self,*args):return self
            def get(self,**filters):
                transport.queries.append(copy.deepcopy(filters))
                row=next((r for r in transport.data[ACCOUNTS] if all(r.get(k)==v for k,v in filters.items())),None)
                if row is None:raise Missing()
                return types.SimpleNamespace(**copy.deepcopy(row))
        model=types.SimpleNamespace(DoesNotExist=Missing,objects=Manager(),Types=types.SimpleNamespace(XC='XC'))
        scope={'M3UAccount':model,'acquire_task_lock':lambda *a:True,'TaskLockRenewer':lambda *a:self.renewer,'release_task_lock':self.release}
        exec(compile(FRAGMENTS['group_task_prefix']['excerpt'],'approved-task-prefix.py','exec'),scope)
        self.group_prefix=scope['refresh_m3u_groups']
        def refresh(account_id):
            value=self.group_prefix(account_id);self.group_results.append(value);return value
        @contextlib.contextmanager
        def job(kind,resource,requested):
            # Synthetic context only, never a real guard or provider authorization.
            self.job_calls.append((kind,resource.id,resource.is_active,requested));yield
        class Base:
            def create(self,request,*args,**kwargs):
                row=transport.allocate(ACCOUNTS,request.data)
                # Serializer-owned preferences are synthetic storage scaffolding.
                row['custom_properties']={**row['custom_properties'],**{k:row[k] for k in ['enable_vod','auto_enable_new_groups_live','auto_enable_new_groups_vod','auto_enable_new_groups_series']}}
                row.update(channel_groups=[],profiles=[],updated_at=None)
                return types.SimpleNamespace(status_code=201,data=copy.deepcopy(row))
        scope={'Base':Base,'M3UAccount':model,'job':job,'refresh_m3u_groups':refresh}
        code='class M3UAccountViewSet(Base):\n'+textwrap.indent(textwrap.dedent(FRAGMENTS['account_create_view']['excerpt']),'    ')
        exec(compile(code,'approved-create-view.py','exec'),scope)
        self.view=scope['M3UAccountViewSet']()

    def exchange(self,method,path,body=None):
        if method=='POST' and path==ACCOUNTS:
            self.calls.append((method,path,copy.deepcopy(body)))
            utils=types.ModuleType('core.utils');utils.send_websocket_update=lambda *a:None
            with patch.dict(sys.modules,{'core':types.ModuleType('core'),'core.utils':utils}):
                response=self.view.create(types.SimpleNamespace(FILES={},data=copy.deepcopy(body)))
            return response.status_code,response.data
        return super().exchange(method,path,body)


class NativeGroupInvestigation(unittest.TestCase):
    def body(self,**overrides):
        return {'name':'Synthetic','account_type':'XC','is_active':False,'metadata_discovery':True,
                'custom_properties':{},'enable_vod':False,'auto_enable_new_groups_live':False,
                'auto_enable_new_groups_vod':False,'auto_enable_new_groups_series':False,**overrides}

    def test_excerpt_provenance_matches_approved_contracts(self):
        release=json.loads((ROOT/'configs/dispatcharr-iptv/hardened-image-integration/retained-image-contract.json').read_text())
        api=json.loads((ROOT/'tools/dispatcharr_provider/api-contract.json').read_text())
        for entry in FRAGMENTS.values():
            self.assertEqual(hashlib.sha256(entry['excerpt'].encode()).hexdigest(),entry['excerpt_sha256'])
            pins=api['source_files'] if entry['path'].endswith('serializers.py') else release['source_hashes']
            self.assertEqual(entry['source_sha256'],pins[entry['path']])

    def test_fixture_category_and_selected_group_are_identical_without_HTTP(self):
        handler=object.__new__(runtime.Provider)
        handler.path='/player_api.php?'+urlencode({'username':runtime.PROVIDER_USER,'password':runtime.PROVIDER_PASSWORD,'action':'get_live_categories'})
        handler.server=types.SimpleNamespace(events=[]);handler.wfile=io.BytesIO()
        handler.send_response=Mock();handler.send_header=Mock();handler.end_headers=Mock()
        handler.do_GET();groups=json.loads(handler.wfile.getvalue())
        self.assertEqual([g['category_id'] for g in groups],['1','2'])
        self.assertEqual(groups[0]['category_id'],SELECTED['group'])
        tree=ast.parse((ROOT/'configs/dispatcharr-iptv/hardened-image-integration/runtime_test.py').read_text())
        fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='test_06_actual_native_discovery_import_and_XMLTV_mapping')
        call=next(n for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='register')
        self.assertEqual(ast.literal_eval(call.args[1]),[SELECTED])

    def test_exact_task_prefix_rejects_inactive_before_category_processing(self):
        backend=SourcePath();backend.data[ACCOUNTS]=[{'id':7,'is_active':False}]
        value=backend.group_prefix(7)
        self.assertEqual(value,('M3UAccount with ID=7 not found or inactive.',None))
        self.assertEqual(backend.queries,[{'id':7,'is_active':True}])
        backend.renewer.start.assert_called_once();backend.renewer.stop.assert_called_once()
        backend.release.assert_called_once_with('refresh_m3u_account_groups',7)
        self.assertEqual(backend.data[GROUPS],[])

    def test_active_control_only_passes_the_early_query(self):
        backend=SourcePath();backend.data[ACCOUNTS]=[{'id':7,'is_active':True}]
        self.assertIsNone(backend.group_prefix(7)) # End of excerpt, not full discovery.
        backend.renewer.stop.assert_not_called()
        self.assertEqual(backend.data[GROUPS],[])

    def test_exact_create_view_ignores_inactive_discovery_return(self):
        backend=SourcePath();status,row=backend.exchange('POST',ACCOUNTS,self.body())
        self.assertEqual(status,201);self.assertFalse(row['is_active'])
        self.assertEqual(backend.group_results,[(f"M3UAccount with ID={row['id']} not found or inactive.",None)])
        self.assertEqual(row['channel_groups'],[])
        self.assertEqual(backend.job_calls,[('discover',row['id'],False,True)])
        self.assertEqual(backend.data[GROUPS],[])

    def test_metadata_optout_never_enters_discovery(self):
        backend=SourcePath();status,row=backend.exchange('POST',ACCOUNTS,self.body(metadata_discovery=False))
        self.assertEqual(status,201);self.assertEqual(backend.job_calls,[]);self.assertEqual(backend.group_results,[])

    def test_authorized_simulator_matches_corrected_inactive_contract(self):
        optimistic=Synthetic(copy.deepcopy(CATALOGUE))
        status,row=optimistic.exchange('POST',ACCOUNTS,self.body())
        self.assertFalse(row['is_active']);self.assertEqual(status,201)
        self.assertEqual([r['custom_properties']['xc_id'] for r in row['channel_groups']],['1','2'])

    def test_real_adapter_refuses_source_backed_path_and_preserves_ownership(self):
        with tempfile.TemporaryDirectory() as temp,Store(Path(temp)/'private') as store:
            backend=SourcePath();api=API(backend)
            p=provider('Synthetic','https://provider.example.invalid','synthetic-user','synthetic-secret',None,1)
            ledger=Ledger(store,p['key']);adapter=Adapter(api,ledger,pause=lambda _:None,polls=3)
            with self.assertRaisesRegex(Refused,'^native_selected_group_missing$'):
                adapter.register(p,[SELECTED],1)
            writes=[(m,path) for m,path,_ in backend.calls if m!='GET']
            self.assertEqual(writes,[('POST',ACCOUNTS)])
            account_id=backend.data[ACCOUNTS][0]['id']
            self.assertTrue(any(m=='GET' and path==ACCOUNTS+str(account_id)+'/' for m,path,_ in backend.calls))
            self.assertEqual(ledger.value['operations'][0]['state'],'verified')
            self.assertEqual(ledger.value['resources']['account']['id'],account_id)
            self.assertEqual(ledger.value['phase'],'registering')
            self.assertEqual(backend.data[CHANNELS],[DW]);self.assertEqual(backend.data[SOURCES],[])
            self.assertEqual(backend.data[GROUPS],[])

if __name__=='__main__':unittest.main()
