import json,sys,tempfile,unittest,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from model import Predictor
from engine import extract_order

class FlowTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.predictor=Predictor()
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.app=create_app(Path(self.tmp.name)/'test.sqlite',self.predictor);self.app.config['TESTING']=True;self.client=self.app.test_client();self.client.get('/api/session')
 def tearDown(self):self.tmp.cleanup()
 def chat(self,text,client=None,rid=None):
  r=(client or self.client).post('/api/chat',json={'message':text,'request_id':rid or str(uuid.uuid4())});self.assertEqual(r.status_code,200,r.data);return r.json
 def order(self,id,client=None):return next(o for o in (client or self.client).get('/api/session').json['orders'] if o['id']==id)
 def test_model_routes_real_questions(self):
  for text,label in [('Where is my order?','track_order'),('Return order 1043','get_refund'),('Cancel order 1041','cancel_order'),('Track refund 1044','track_refund'),('Change shipping address for order 1041','change_shipping_address')]:
   p=self.predictor.predict(text);self.assertTrue(p['accepted']);self.assertEqual(p['intent'],label)
 def test_tracking_followup(self):
  self.assertEqual(self.chat('Where is my order?')['pending']['stage'],'order');r=self.chat('1042');self.assertIn('shipped',r['response']);self.assertIsNone(r['pending'])
 def test_cancellation_confirmation(self):
  r=self.chat('Cancel order 1041');self.assertEqual(r['pending']['stage'],'confirm');self.assertEqual(self.order('1041')['status'],'processing');self.chat('confirm');self.assertEqual(self.order('1041')['status'],'cancelled');self.assertEqual(self.order('1041')['refund_status'],'processing')
 def test_decline_keeps_order(self):
  self.chat('Cancel order 1041');self.chat('no');self.assertEqual(self.order('1041')['status'],'processing')
 def test_shipped_cannot_cancel(self):
  r=self.chat('Cancel order 1042');self.assertIsNone(r['pending']);self.assertEqual(self.order('1042')['status'],'shipped')
 def test_return_three_turns(self):
  r=self.chat('Return order 1043');self.assertEqual(r['pending']['stage'],'reason');r=self.chat('Wrong size');self.assertEqual(r['pending']['stage'],'confirm');self.chat('confirm');o=self.order('1043');self.assertEqual(o['status'],'return_requested');self.assertEqual(o['refund_status'],'awaiting_return');self.assertIn('awaits',self.chat('Track refund 1043')['response'])
 def test_return_window(self):
  r=self.chat('Return order 1045');self.assertIn('outside',r['response']);self.assertIsNone(r['pending']);self.assertEqual(self.order('1045')['status'],'delivered')
 def test_address_confirm(self):
  r=self.chat('Change shipping address for order 1041');self.assertEqual(r['pending']['stage'],'address');self.chat('88 Sample Road, Pune');self.assertNotEqual(self.order('1041')['address'],'88 Sample Road, Pune');self.chat('confirm');self.assertEqual(self.order('1041')['address'],'88 Sample Road, Pune')
 def test_sessions_are_isolated(self):
  other=self.app.test_client();other.get('/api/session');self.chat('Cancel order 1041');self.chat('confirm');self.assertEqual(self.order('1041',other)['status'],'processing')
 def test_retry_is_idempotent(self):
  self.chat('Cancel order 1041');a=self.chat('confirm',rid='retry-confirm');b=self.chat('confirm',rid='retry-confirm');self.assertEqual(a,b);r=self.client.post('/api/chat',json={'message':'different','request_id':'retry-confirm'});self.assertEqual(r.status_code,409)
 def test_invalid_input(self):
  for payload in [{},[],{'message':'','request_id':'x'},{'message':'a'*501,'request_id':'x'}]:self.assertEqual(self.client.post('/api/chat',json=payload).status_code,400)
 def test_unknown_order_and_recovery(self):
  r=self.chat('Track order 9999');self.assertIn('not in',r['response']);r=self.chat('1042');self.assertIn('shipped',r['response'])
 def test_switch_intent_while_waiting_for_order(self):
  self.chat('I want a refund');r=self.chat('Cancel order 1041');self.assertEqual(r['pending']['intent'],'cancel_order');self.assertEqual(r['pending']['stage'],'confirm')
 def test_reset(self):
  self.chat('Cancel order 1041');self.chat('confirm');self.client.post('/api/reset',json={});self.assertEqual(self.order('1041')['status'],'processing')
 def test_invoice_and_static(self):
  r=self.chat('I need an invoice for order 1042');self.assertEqual(r['invoice_url'],'/api/invoice/1042');self.assertIn(b'INR 2499',self.client.get(r['invoice_url']).data)
  for path in ['/','/static/app.js','/static/styles.css','/health']:
   with self.client.get(path) as r:self.assertEqual(r.status_code,200)
 def test_spoken_order_numbers(self):
  self.assertEqual(extract_order('one zero four two'),'1042');self.assertEqual(extract_order('one thousand forty three'),'1043')
 def test_ambiguous_confirmation_no_mutation(self):
  self.chat('Cancel order 1041');self.chat('maybe');self.assertEqual(self.order('1041')['status'],'processing')
if __name__=='__main__':unittest.main(verbosity=2)
