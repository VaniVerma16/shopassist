"""Original, training-only conversational supplements. Bitext remains attributed separately."""
import json,random
from pathlib import Path
SEEDS={
'cancel_order':'cancel my order|stop my purchase|I do not want this order anymore|please cancel this purchase|can you cancel it|cancel order|cancel the headphones I bought|I ordered by mistake cancel it|do not ship my order|I want to cancel my purchase',
'change_order':'change the items in my order|I want a different size in my order|edit my order quantity|replace one item in my purchase|can I modify my order|change my purchase|I ordered the wrong color|add another item to my order|remove an item from my order|I want to change the product I ordered',
'change_shipping_address':'change my delivery address|send my order to another address|update shipping address|change shipping address for order|I entered the wrong delivery address|ship it to a different place|edit the address on my order|my order has the wrong address|can I change where my order is delivered|change the delivery location',
'check_cancellation_fee':'is there a cancellation fee|does cancelling cost money|how much does it cost to cancel|will I be charged for cancelling|can I cancel for free|what is the cancellation charge|is cancellation free|are there fees to cancel my order',
'check_invoice':'my invoice is incorrect|check the amount on my invoice|there is an error in my bill|explain a charge on my invoice|the invoice total is wrong|can you check my receipt|why is my bill wrong|invoice details are incorrect',
'get_invoice':'I need an invoice|download my receipt|send me the invoice for my order|show invoice for order|give me a receipt|where can I get my invoice|I need a copy of my bill|I need an invoice for order|download invoice|show me my receipt',
'check_payment_methods':'what payment methods do you accept|can I pay with UPI|do you accept cards|how can I pay|which cards are accepted|can I pay cash|payment options|what ways can I pay',
'check_refund_policy':'what is your return policy|how many days do I have to return something|what are the refund rules|is there a return window|which items are eligible for refunds|explain the return policy|what is the refund policy|are returns allowed',
'complaint':'I want to make a complaint|I am unhappy with your service|your support has been terrible|file a complaint|I want to complain about my experience|I have a problem with your service|this shopping experience was awful|I need to report bad service',
'contact_customer_service':'how do I contact customer support|give me the support email|what is your customer service number|contact customer service|how can I reach support|where is customer support|I need customer service contact details|help me contact your support team',
'contact_human_agent':'I want to speak to a person|connect me to a human|can I talk to an agent|transfer me to a real person|I need a human agent|let me talk to someone|is a person available|I do not want to talk to a bot',
'create_account':'how do I sign up|create a new account|I want to register|open an account|help me create my profile|make a shopping account|where can I sign up|I need a new account',
'delete_account':'delete my account|close my account|remove my profile|I want to leave and delete my account|erase my account|how do I close my profile|permanently delete my profile|I no longer want an account',
'delivery_options':'what delivery options do you have|do you offer express delivery|which shipping methods are available|can you deliver internationally|is same day shipping available|where do you deliver|what shipping options can I choose|which delivery services do you offer',
'delivery_period':'how long does delivery take|what is your usual shipping time|how many days is standard delivery|when do you usually deliver|how fast is shipping|delivery time for new orders|what is the standard delivery period|how long does shipping normally take',
'edit_account':'change my account details|edit my profile|update my name|change the email on my account|I need to update my account|modify my profile information|edit my personal details|my account details need updating',
'get_refund':'I want to return my order|return order|I want a refund|request a return|the item arrived damaged|I received the wrong item|my shoes are the wrong size|I want my money back|return my headphones|the product is broken|start a return for my order|I want to send this item back|I need a refund for order|my parcel arrived damaged|return this purchase|I want to return order',
'newsletter_subscription':'subscribe to your newsletter|stop newsletter emails|unsubscribe from marketing|sign me up for updates|turn off promotional emails|join the mailing list|I want your newsletter|remove me from your email list',
'payment_issue':'my payment failed|I was charged twice|my card was declined|money was deducted but payment failed|I cannot complete payment|checkout payment is stuck|I have a payment problem|UPI payment did not go through',
'place_order':'I want to buy something|how do I place an order|buy new headphones|help me order a product|I want to purchase a backpack|how do I check out|place a new order|I want to shop',
'recover_password':'I forgot my password|reset my password|I cannot remember my login password|help me recover my password|how do I reset my login|forgot password|I need a password reset|change a forgotten password',
'registration_problems':'I cannot sign up|registration failed|account creation is not working|I get an error while registering|the signup form is broken|I am unable to register|why does signup fail|new account registration keeps failing',
'review':'I want to review a product|leave a rating|how can I write a review|rate my purchase|I want to give five stars|submit a product review|where can I leave feedback on the item|write a product rating',
'set_up_shipping_address':'add an address to my account|set my default address|save a new shipping address|how do I add an address|set up my delivery address|add my first address|save an address for future orders|create a saved shipping address',
'switch_account':'switch to a different account|log in with another account|change which account I am using|switch profile|use my other account|how do I switch accounts|I want to use another profile|log out and switch accounts',
 'track_order':'where is my order|where is my package|track my order|has my order shipped|what is the status of my order|where is order|when will my order arrive|track order|my package has not arrived|show my order status|where is my delivery|track my purchase|has my parcel arrived|when is my package coming|find my order|what happened to my order',
 'track_refund':'where is my refund|my refund has not arrived|track my refund|check refund status|when will I get my money back|has my refund been processed|track refund|what is the status of my refund|refund is still pending|my money has not been refunded'}
if __name__=='__main__':
 root=Path(__file__).parent;rows=[]
 order_intents={'cancel_order','change_order','change_shipping_address','get_invoice','check_invoice','get_refund','track_order','track_refund'}
 for intent,seeds in SEEDS.items():
  for n,text in enumerate(seeds.split('|')):
   for prefix in ['','please ','hello ','can you help me ']:
    for suffix in ['', ' please', ' thanks']:
     rows.append({'text':prefix+text+suffix,'intent':intent,'source':'authored_training_supplement','seed':intent+str(n)})
    if intent in order_intents:
     for suffix in [' 1042',' for order 1043',' my order number is 1041']:
      rows.append({'text':prefix+text+suffix,'intent':intent,'source':'authored_training_supplement','seed':intent+str(n)})
 (root/'supplement.jsonl').write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
 print('Supplement training examples:',len(rows))
