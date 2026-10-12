import unittest,json
class PackedTransport(unittest.TestCase):
 def test_dictionary_roundtrip_and_query_safety(self):
  from ap_refresh import pack_records,unpack_records,publish_expression
  rows=[{'a':"O'Brien",'b':1},{'a':'"\\weird\n','b':2}]
  packed=pack_records(rows)
  self.assertEqual(unpack_records(packed),rows)
  self.assertEqual(unpack_records(pack_records([])),[])
  with self.assertRaises(ValueError):pack_records([{'a':1},{'b':2}])
  from tests.test_history_validation import fixture
  source={'companies':{'SMI':{'check_runs':fixture()},'SFAB':{'check_runs':fixture('SFAB')}}}
  expr=publish_expression(source)
  self.assertIn('jsonb_object_agg',expr)
  self.assertNotIn('create table',expr.lower())
