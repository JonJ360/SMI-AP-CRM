import unittest, tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ap

class Accounting(unittest.TestCase):
 def test_due_date_aging_boundaries_and_credit_signs(self):
  self.assertEqual([ap.aging(d,'2026-10-12') for d in ['2026-10-13','2026-10-12','2026-10-11','2026-09-12','2026-09-11','2026-08-13','2026-08-12','2026-07-14','2026-07-13',None]],['Current','Current','1–30','1–30','31–60','31–60','61–90','61–90','91+','Unknown'])
  self.assertEqual([ap.signed_cents(t,'123.45') for t in range(1,7)],[12345,12345,12345,-12345,-12345,-12345])
  with self.assertRaises(ValueError): ap.signed_cents(99,'1')
  with self.assertRaises(ValueError): ap.signed_cents(1,'-1')
  with self.assertRaises(ValueError): ap.signed_cents(1,'1.001')

class Workflow(unittest.TestCase):
 def test_changed_source_invalidates_selection_preserves_notes(self):
  with tempfile.TemporaryDirectory() as d:
   row=dict(id='SMI:1:A',company='SMI',vendor_id='V',vendor='Fixture',document='A',due='2026-10-01',cents=100,gp_hold=False,doctype=1)
   db=Path(d)/'state.db';s=ap.Store(db,[row]);s.update(row['id'],{'selected':True,'note':'Keep me'})
   changed=ap.Store(db,[{**row,'cents':200}]).view('SMI','2026-10-12')
   self.assertEqual(changed['selected_cents'],0)
   refreshed=ap.Store(db,[{**row,'cents':200}]);refreshed.update(row['id'],{'note':'Edited note'})
   self.assertEqual(refreshed.view('SMI','2026-10-12')['selected_cents'],0)
   self.assertEqual(changed['rows'][0]['note'],'Keep me')

 def test_persistence_scoping_holds_and_selection(self):
  with tempfile.TemporaryDirectory() as d:
   rows=[dict(id='SMI:1:A',company='SMI',vendor_id='V1',vendor='Test vendor',document='A',due='2026-10-01',cents=12345,gp_hold=False,doctype=1),dict(id='SFAB:1:A',company='SFAB',vendor_id='V1',vendor='Test vendor',document='A',due='2026-11-01',cents=600,gp_hold=True,doctype=1),dict(id='SMI:5:C',company='SMI',vendor_id='V1',vendor='Test vendor',document='C',due=None,cents=-500,gp_hold=False,doctype=5)]
   db=Path(d)/'workflow.db'; s=ap.Store(db,rows)
   s.update('SMI:1:A',{'selected':True,'note':'Review invoice','hold':False})
   self.assertEqual(ap.Store(db,rows).view('SMI','2026-10-12')['selected_cents'],12345)
   self.assertEqual(s.view('SFAB','2026-10-12')['selected_cents'],0)
   self.assertEqual(s.view('SMI','2026-10-12')['net_cents'],11845)
   for key in ['SFAB:1:A','SMI:5:C']:
    with self.assertRaises(ValueError): s.update(key,{'selected':True})
   s.update('SMI:1:A',{'hold':True})
   self.assertEqual(s.view('SMI','2026-10-12')['selected_cents'],0)
   self.assertEqual(s.view('SMI','2026-10-12')['rows'][0]['note'],'Review invoice')
   with self.assertRaises(ValueError): s.update('UNKNOWN',{'note':'x'})
   with self.assertRaises(ValueError): s.update('SMI:1:A',{'hold':'false'})
   with self.assertRaises(ValueError): s.view('RSS','2026-10-12')
   self.assertEqual(len(ap.Store(db,rows).audit()),2)

if __name__=='__main__':unittest.main()
