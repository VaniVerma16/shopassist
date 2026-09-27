"""Supplementary author-written probes; not an independent real-user benchmark."""
import json,time,statistics
from model import Predictor,ROOT,tokenize
CASES={
 'track_order':['Could you tell me where my parcel has got to?','Has order 1042 left the warehouse yet?','I am waiting for my purchase to turn up','Any update on the package I ordered?'],
 'cancel_order':['Please stop order 1041 from being sent','I changed my mind and do not need my purchase','Can you undo the order I just placed?','Please cancel the backpack purchase'],
 'get_refund':['These sneakers do not fit and I need to send them back','The wrong item was in the box and I would like a refund','Please arrange a return for my purchase','I would like to send order 1043 back for a refund'],
 'track_refund':['Can you tell me if the refund has gone through?','I sent it back but still have not got my money','Has the money for my return been sent yet?','Please give me an update on my refund'],
 'change_shipping_address':['I moved house and need to update the delivery location','Could you redirect my unshipped order to another address?','The shipping address on 1041 needs changing','Please update where order 1041 will be delivered'],
 'get_invoice':['Could I have a copy of the receipt for 1042?','Please provide the invoice for my last purchase','I need my order receipt for my records','Let me download the invoice for this purchase'],
 'check_refund_policy':['How long is the window for returning an item?','What conditions apply if I want a refund?','Explain which purchases qualify for returns','What are the rules for sending products back?'],
 'check_payment_methods':['Is UPI one of your payment options?','Which forms of payment can I use at checkout?','Can I use a debit card to pay?','Do you take credit cards?'],
 'payment_issue':['My bank charged me but checkout said failed','I have been billed twice for one purchase','Payment did not complete even though money left my account','The card payment keeps getting rejected'],
 'contact_human_agent':['Could a real person take over this chat?','Please put me through to a support representative','I need to speak with someone rather than the bot','May I talk to a human support agent?']}
OOD=['What is the capital of India?','Write a poem about the moon','Explain binary search trees','Book a flight to Mumbai','What will the weather be tomorrow?','Who won the football match?','Translate hello to French','Recommend a film for tonight','How do I cook pasta?','My wifi is disconnected','Can you help with my homework?','Calculate the square root of 625','Tell me a joke','What does photosynthesis mean?','Which laptop should I buy?','Order pizza for me','What are the latest stock prices?','Give me medical advice','Find a nearby hospital','Turn on the bedroom lights']
if __name__=='__main__':
 p=Predictor();trainkeys={' '.join(tokenize(json.loads(l)['text'])) for l in (ROOT/'data/train.jsonl').read_text().splitlines()};results=[];times=[]
 for label,texts in CASES.items():
  for text in texts:
   assert ' '.join(tokenize(text)) not in trainkeys,text
   t=time.perf_counter();r=p.predict(text);times.append((time.perf_counter()-t)*1000);results.append({'text':text,'expected':label,**r})
 out=[{'text':text,**p.predict(text)} for text in OOD]
 m={'count':len(results),'accuracy':sum(r['intent']==r['expected'] for r in results)/len(results),'coverage':sum(r['accepted'] for r in results)/len(results),'accepted_correct':sum(r['accepted'] and r['intent']==r['expected'] for r in results),'ood_count':len(out),'ood_rejected':sum(not r['accepted'] for r in out),'median_inference_ms':statistics.median(times),'results':results,'ood_results':out}
 (ROOT/'reports/challenge_results.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k not in ['results','ood_results']},indent=2))
 print('Errors:',[(r['text'],r['expected'],r['intent']) for r in results if r['intent']!=r['expected']])
