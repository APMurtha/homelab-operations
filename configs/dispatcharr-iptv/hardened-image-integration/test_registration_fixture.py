"""Nullable native account metadata must not crash test-only reconciliation."""
import unittest
from runtime_test import registration_matches

class RegistrationFixture(unittest.TestCase):
    def test_reproduce_previous_chained_lookup_failure(self):
        rows=[{'id':1,'custom_properties':None}]
        with self.assertRaises(AttributeError):
            [r for r in rows if r.get('custom_properties',{}).get('provider_cli',{}).get('registration')=='c'*32]
        self.assertEqual(registration_matches(rows,'c'*32),[])

    def test_only_exact_structured_tag_selected(self):
        wanted={'id':3,'custom_properties':{'provider_cli':{'registration':'c'*32}}}
        rows=[{'id':1,'custom_properties':None},{'id':2},wanted,{'id':4,'custom_properties':{'provider_cli':{'registration':'d'*32}}}]
        self.assertEqual(registration_matches(rows,'c'*32),[wanted])

    def test_malformed_or_null_tags_do_not_authorize_any_record(self):
        for props in [None,'opaque',[],{}, {'provider_cli':None},{'provider_cli':[]},{'provider_cli':'opaque'}]:
            self.assertEqual(registration_matches([{'id':1,'custom_properties':props}],'c'*32),[])

    def test_duplicates_remain_visible_to_existing_exact_count_assertion(self):
        rows=[{'id':i,'custom_properties':{'provider_cli':{'registration':'c'*32}}} for i in [3,4]]
        self.assertEqual(len(registration_matches(rows,'c'*32)),2)

if __name__=='__main__':unittest.main()
