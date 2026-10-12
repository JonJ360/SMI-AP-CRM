import unittest
from unittest.mock import patch,Mock
from ap_refresh import Backend
class BackendRenewal(unittest.TestCase):
 def test_one_401_reauthorizes_and_retries_exact_query(self):
  b=Backend.__new__(Backend);b._token='test-only-old'
  def renew(self):self._token='test-only-new'
  with patch('requests.post',side_effect=[Mock(status_code=401),Mock(status_code=201,json=lambda:[{'ok':True}])]) as post,patch.object(Backend,'__init__',renew):
   self.assertEqual(b.query('select 1'),[{'ok':True}]);self.assertEqual(post.call_count,2)
   self.assertEqual(post.call_args_list[0].kwargs['json'],post.call_args_list[1].kwargs['json'])
   self.assertNotEqual(post.call_args_list[0].kwargs['headers'],post.call_args_list[1].kwargs['headers'])
 def test_permanent_denial_is_bounded(self):
  b=Backend.__new__(Backend);b._token='test-only'
  for status,count in [(401,2),(413,1)]:
   with patch('requests.post',return_value=Mock(status_code=status)) as post,patch.object(Backend,'__init__',lambda self:None):
    with self.assertRaises(RuntimeError):b.query('select 1')
    self.assertEqual(post.call_count,count)
