"""Offline regression for the three-to-four-service diagnostic scope mistake."""
import copy
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import diagnostic_inventory as inventory
from contracts import Refusal


def baseline():
    return {'containers': [dict(name='/'+name, id=name+'-ID', image='sha256:fixture',
             started='fixture', running=True, health='healthy', restart='no',
             restart_count=0, host_config_sha256='fixture')
             for name in ('rivendell-iptv-vpn', 'dispatcharr', 'rivendell-iptv-gateway',
                          'jellyfin', 'relay', 'dispatcharr-extra', 'rivendell-iptv-relay-extra')],
            'network_ids': ['fixture-network'], 'docker_process': 'fixture-process',
            'dedicated_network': 'fixture-network'}


class Inventory(unittest.TestCase):
    def test_excludes_exactly_four_dedicated_names(self):
        self.assertEqual(inventory.DEDICATED, {'rivendell-iptv-vpn', 'dispatcharr',
                         'rivendell-iptv-relay', 'rivendell-iptv-gateway'})
        before=baseline();after=copy.deepcopy(before)
        after['containers'].append({'name':'/rivendell-iptv-relay'})
        for c in after['containers']:
            if c['name'].removeprefix('/') in inventory.DEDICATED:
                c['id']='new';c['running']=False
        inventory.compare(before,after)
        self.assertEqual(set(inventory.unrelated(after)),
                         {'jellyfin','relay','dispatcharr-extra','rivendell-iptv-relay-extra'})
    def test_unrelated_fields_all_remain_strict(self):
        for field in inventory.FIELDS:
            before=baseline();after=copy.deepcopy(before)
            after['containers'][3][field]='changed'
            with self.subTest(field=field),self.assertRaises(Refusal):inventory.compare(before,after)
    def test_new_or_missing_unrelated_containers_refused(self):
        before=baseline()
        for records in (before['containers'][:-1],before['containers']+[dict(before['containers'][3],name='/new')]):
            after=dict(before,containers=records)
            with self.assertRaises(Refusal):inventory.compare(before,after)
    def test_duplicate_and_invalid_names_refused(self):
        for name in ('/jellyfin','jellyfin','/rivendell-iptv-vpn','//jellyfin','/'):
            s=baseline();s['containers'].append(dict(s['containers'][3],name=name))
            with self.subTest(name=name),self.assertRaises(Refusal):inventory.compare(s,s)
    def test_incomplete_unrelated_record_refused(self):
        for field in inventory.FIELDS:
            s=baseline();del s['containers'][3][field]
            with self.assertRaises(KeyError):inventory.compare(s,s)
    def test_Docker_and_network_identity_changes_refused(self):
        for field in ('network_ids','docker_process','dedicated_network'):
            before=baseline();after=copy.deepcopy(before);after[field]='changed'
            with self.subTest(field=field),self.assertRaises(Refusal):inventory.compare(before,after)
    def test_snapshot_record_order_is_irrelevant(self):
        before=baseline();after=copy.deepcopy(before);after['containers'].reverse()
        inventory.compare(before,after)

if __name__ == '__main__':unittest.main()
