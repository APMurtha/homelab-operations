"""New server-contract gate; only synthetic APIs are used."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dispatcharr_provider import core as c
from dispatcharr_provider.native import API,Adapter,Ledger,Store,SECURITY,ACCOUNTS,SOURCES
from dispatcharr_provider.synthetic import Synthetic
from test_dispatcharr_native import RAW,DW


class Hardened(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'state').__enter__();self.addCleanup(self.store.__exit__)
        self.p=c.provider('Synthetic','https://provider.example.invalid','synthetic-user','synthetic-secret',None,1)
        self.cat=c.catalogue(copy.deepcopy(RAW));self.transport=Synthetic(self.cat,snapshot={'channels':[DW]})
        self.api=API(self.transport);self.ledger=Ledger(self.store,self.p['key']);self.adapter=Adapter(self.api,self.ledger,pause=lambda _:None,polls=3)
    def register(self):return self.adapter.register(self.p,[self.cat['channels']['101']],1)
    def alter(self,change):
        original=self.transport.exchange
        def response(method,path,body=None):
            status,value=original(method,path,body)
            if path.startswith(SECURITY):change(value)
            return status,value
        self.transport.exchange=response
    def denied_before_write(self):
        with self.assertRaises(c.Refused):self.register()
        self.assertFalse(self.ledger.path.exists());self.assertFalse(any(m!='GET' for m,_,_ in self.transport.calls))
    def test_absent_contract_endpoint_blocks_before_account_creation(self):
        original=self.transport.exchange
        self.transport.exchange=lambda m,p,b=None:(404,{}) if p.startswith(SECURITY) else original(m,p,b)
        self.denied_before_write()
    def test_wrong_server_source_hash_is_not_accepted(self):
        self.alter(lambda v:v.update(source_hashes={}));self.denied_before_write()
    def test_wrong_network_owner_is_not_accepted(self):
        self.alter(lambda v:v.update(network_owner='WAN'));self.denied_before_write()
    def test_missing_enforcement_feature_is_not_accepted(self):
        self.alter(lambda v:v.update(features=[]));self.denied_before_write()
    def test_stale_approval_is_not_accepted(self):
        self.alter(lambda v:v.update(expires_epoch=0));self.denied_before_write()
    def test_different_guide_URL_approval_is_not_accepted(self):
        self.alter(lambda v:v.update(epg_url_sha256='f'*64));self.denied_before_write()

    def test_wrong_provider_policy_is_not_accepted(self):
        self.alter(lambda v:v.update(provider_key='f'*64));self.denied_before_write()
    def test_media_activation_or_removal_must_remain_disabled(self):
        self.alter(lambda v:v.update(media_activation=True,native_removal=True));self.denied_before_write()
    def test_all_required_explicit_operations_must_be_approved(self):
        self.alter(lambda v:v.update(operations=['discover']));self.denied_before_write()
    def test_guard_generation_must_be_current_assertion(self):
        self.alter(lambda v:v.update(guard_generation='missing'));self.denied_before_write()
    def test_explicit_discovery_and_post_mapping_programme_import_are_journaled(self):
        self.register()
        account=next(o for o in self.ledger.value['operations'] if o['method']=='POST' and o['path']==ACCOUNTS)
        self.assertIs(account['body']['metadata_discovery'],True)
        imports=[o for o in self.ledger.value['operations'] if o['path']=='/api/epg/import/']
        self.assertEqual(len(imports),2);self.assertTrue(all(o['state']=='verified' for o in imports))
        self.assertEqual(self.api.detail(SOURCES,self.ledger.value['resources']['epg_source']['id'])['is_active'],False)
    def test_refresh_rechecks_server_contract_without_mutations(self):
        self.register();before=len(self.transport.calls);self.alter(lambda v:v.update(features=[]))
        with self.assertRaises(c.Refused):self.adapter.refresh()
        self.assertTrue(all(m=='GET' for m,_,_ in self.transport.calls[before:]))

if __name__=='__main__':unittest.main()
