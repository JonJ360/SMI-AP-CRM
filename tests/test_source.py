import unittest, sys
from pathlib import Path
from decimal import Decimal as D
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gp_extract as gp

class SourceContract(unittest.TestCase):
 def test_vendor_control_signs(self):
  rows=[{'vendor_id':'A','cents':1000},{'vendor_id':'A','cents':-250}]
  self.assertEqual(gp.vendor_control(rows,[{'vendorid':'A','balance':D('7.50')}]),{'matched_vendors':1,'difference_cents':0})
  with self.assertRaises(ValueError):gp.vendor_control(rows,[{'vendorid':'A','balance':D('10.00')}])
  with self.assertRaises(ValueError):gp.vendor_control(rows,[{'vendorid':'A','balance':D('7.50')},{'vendorid':'B','balance':D('1')}])

 def test_reconcile_and_normalize(self):
  raw=[dict(vendorid='TEST',vendor='Fixture only',voucher='0001',document='A',DOCTYPE=1,DOCDATE='2026-10-01',DUEDATE='2026-10-10',DOCAMNT=D('12.34'),CURTRXAM=D('10'),HOLD=0,vendor_hold=0,VENDSTTS=1,terms='NET30',description='fixture',currency='Z-US$')]
  control=[dict(DOCTYPE=1,n=1,amount=D('10'))]
  rows=gp.normalize('SMI',raw,control)
  self.assertEqual(rows[0]['cents'],1000)
  self.assertEqual(rows[0]['id'],'SMI:1:0001')
  with self.assertRaises(ValueError):gp.normalize('RSS',raw,control)
  with self.assertRaises(ValueError):gp.normalize('SMI',raw,[dict(DOCTYPE=1,n=1,amount=D('11'))])
  with self.assertRaises(ValueError):gp.normalize('SMI',raw*2,control)
  for q in gp.QUERIES.values():self.assertTrue(q.strip().upper().startswith('SELECT'))
