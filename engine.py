"""Deterministic dialogue state and fictional store policy; no real commerce actions."""
import copy,re
from datetime import date,timedelta

POLICY='Store policy: cancel before dispatch at no charge; request returns within 14 days of delivery. Refunds take 5–7 business days after approval. These policies apply only to this fictional store.'
ORDER_INTENTS={'track_order','cancel_order','get_refund','track_refund','change_shipping_address','get_invoice','check_invoice','change_order'}
YES={'yes','yes please','confirm','confirm it','yes confirm','go ahead','do it','proceed','okay','ok'}
NO={'no','no thanks','no thank you','never mind','nevermind','stop','do not','dont','do not cancel','dont cancel','cancel this request','keep my order'}
DIGITS={'zero':'0','oh':'0','one':'1','two':'2','three':'3','four':'4','five':'5','six':'6','seven':'7','eight':'8','nine':'9'}

def fresh_state():
    today=date.today()
    def order(i,item,total,status,days,**extras):
        return {'id':i,'item':item,'quantity':1,'total':total,'currency':'INR','status':status,'ordered_on':(today-timedelta(days=days)).isoformat(),'address':'12 Market Street, Bengaluru','refund_status':'none','refund_amount':0,**extras}
    return {'orders':[
      order('1041','Everyday backpack',1899,'processing',1),
      order('1042','Wireless headphones',2499,'shipped',2,estimated_delivery=(today+timedelta(days=3)).isoformat(),carrier='ShopAssist Express',tracking='SA1042'),
      order('1043','Everyday sneakers',3299,'delivered',7,delivered_on=(today-timedelta(days=3)).isoformat()),
      order('1044','Cotton overshirt',1599,'returned',12,delivered_on=(today-timedelta(days=8)).isoformat(),refund_status='processing',refund_amount=1599),
      order('1045','Travel mug',799,'delivered',45,delivered_on=(today-timedelta(days=40)).isoformat())], 'pending':None,'last_order':None}

def extract_order(text):
    match=re.search(r'(?<!\d)(?:sa[- ]?)?(\d{4})(?!\d)',text.lower())
    if match:return match[1]
    words=re.findall(r'[a-z]+',text.lower()); digits=''.join(DIGITS[w] for w in words if w in DIGITS)
    if len(digits)==4:return digits
    # Common recognition of 1042 as "one thousand forty two".
    m=re.search(r'one thousand(?: and)? (?:and )?forty(?:[ -](one|two|three|four|five))?',text.lower())
    if m:return '104'+DIGITS.get(m[1],'0')
    return None

def normalized(text):return re.sub(r'[^a-z ]','',text.lower()).strip()

def reply(text,state,model=None,**extra):
    return {'response':text,'orders':copy.deepcopy(state['orders']),'pending':copy.deepcopy(state['pending']),'prediction':model,'suggestions':extra.pop('suggestions',[]),**extra}

def handle(text,state,predict):
    simple=normalized(text)
    if simple in {'start over','reset conversation','clear conversation'}:
        state['pending']=None;state['last_order']=None
        return reply('Conversation cleared. Your orders are unchanged. What can I help with?',state)
    if simple in {'hi','hello','hey','help','what can you do'}:
        return reply('I can track orders, cancel an unshipped order, request a return, check refunds, update an unshipped order’s address or show an invoice. Try “Where is order 1042?”',state,suggestions=['Track order 1042','Cancel order 1041','Return order 1043','Track refund 1044'])
    if simple in {'thanks','thank you','thank you very much'}:return reply('You’re welcome. Is there another order you need help with?',state)
    pending=state['pending'];order_id=extract_order(text)
    if pending and simple in NO:
        state['pending']=None
        return reply('I stopped that request. No changes were made.',state)
    if pending and pending['stage']=='confirm':
        if simple in YES:
            order=next(o for o in state['orders'] if o['id']==pending['order_id'])
            action=pending['intent'];state['pending']=None
            if action=='cancel_order':
                if order['status']!='processing':return reply('This order can no longer be cancelled because it is not awaiting dispatch.',state)
                order.update(status='cancelled',refund_status='processing',refund_amount=order['total'])
                return reply(f"Order {order['id']} is cancelled. A refund of ₹{order['total']:,} is processing and is expected within 5–7 business days. No real payment was made.",state)
            if action=='get_refund':
                if order['status']!='delivered':return reply('This order is no longer eligible for a new return request.',state)
                order.update(status='return_requested',return_reason=pending['reason'],refund_status='awaiting_return',refund_amount=order['total'])
                return reply(f"Return request RET-{order['id']} has been recorded for order {order['id']}. The refund of ₹{order['total']:,} will be processed after the item is received and approved. No real pickup has been booked.",state)
            if action=='change_shipping_address':
                if order['status']!='processing':return reply('The order has already left processing; its address cannot be changed.',state)
                order['address']=pending['address']
                return reply(f"The delivery address for order {order['id']} is now {order['address']}.",state)
        # Do not interpret ambiguous acknowledgements as permission to mutate.
        if not order_id and len(text.split())<5:return reply('Please say “confirm” to apply this change, or “no” to leave the order unchanged.',state,suggestions=['Confirm','No'])
    if pending and pending['stage']=='order' and order_id and all(w in {'order','number','my','is','it','its','the','id','sa','one','two','three','four','five','six','seven','eight','nine','zero','oh','thousand','forty','and'} for w in simple.split()):
        return begin(pending['intent'],order_id,state,pending.get('prediction'))
    if pending and pending['stage'] in {'reason','address'}:
        # Allow an explicit new support request to interrupt slot filling.
        p=predict(text)
        if p['accepted'] and p['confidence']>.90 and p['intent'] in ORDER_INTENTS and p['intent']!=pending['intent']:
            state['pending']=None;return route(p['intent'],text,state,p)
        if pending['stage']=='reason':
            if len(text.strip())<5:return reply('Briefly describe why you want to return the item, for example “wrong size” or “item damaged”.',state)
            pending.update(stage='confirm',reason=text.strip()[:300])
            return reply(f"Request a return for order {pending['order_id']} because “{pending['reason']}”? Say confirm or no.",state,suggestions=['Confirm','No'])
        if len(text.strip())<10:return reply('Enter a complete fictional delivery address, including a city. Please do not enter a real address in this application.',state)
        pending.update(stage='confirm',address=text.strip()[:200])
        return reply(f"Change order {pending['order_id']} to this address: {pending['address']}? Say confirm or no.",state,suggestions=['Confirm','No'])
    if order_id and simple in {'','order','order number','sa'} and not pending:
        return begin('track_order',order_id,state,None)
    p=predict(text)
    if not p['accepted']:
        return reply('I’m not sure which shopping request you mean. Ask one question at a time about orders, returns, refunds, delivery or payments.',state,p,suggestions=['Track order 1042','Return order 1043','What is the refund policy?'])
    state['pending']=None
    return route(p['intent'],text,state,p)

def route(intent,text,state,p):
    if intent in ORDER_INTENTS:
        order_id=extract_order(text)
        if not order_id and re.search(r'\b(it|that order|this order|same order)\b',text.lower()):order_id=state['last_order']
        if order_id:return begin(intent,order_id,state,p)
        state['pending']={'intent':intent,'stage':'order','prediction':p}
        return reply('What is the four-digit order ID? You can use one of the orders shown beside this conversation.',state,p,suggestions=['1041','1042','1043','1044'])
    answers={
      'check_refund_policy':POLICY,
      'check_cancellation_fee':'There is no cancellation fee for an order that is still processing. Shipped orders cannot be cancelled; eligible delivered items can be returned within 14 days.',
      'delivery_options':'This store uses standard delivery, typically 3–5 business days. To see a specific order’s estimate, ask to track its order ID.',
      'delivery_period':'Standard delivery usually takes 3–5 business days in this fictional store. Ask “Track order 1042” for its recorded delivery estimate.',
      'check_payment_methods':'The fictional store supports cards and UPI. Checkout and real payments are not connected here.',
      'payment_issue':'If a real payment failed, check its status with your bank before trying again. This assistant cannot inspect bank transactions. For a refund, provide an order ID. Never share card details, passwords or OTPs here.',
      'place_order':'This support assistant has preloaded orders, so new purchases and checkout are not available. You can try tracking 1042, cancelling 1041 or returning 1043.',
      'contact_customer_service':'You’re using the support assistant. It can help with the displayed orders; no external support team is connected.',
      'contact_human_agent':'Human-agent handoff is not connected here. I can still help you track an order, check a refund or explain the fictional store policy.',
      'complaint':'I can help with an order issue. For a delivered item you want to return, say “I want a refund for order 1043”. This assistant does not send complaints to a real company.',
      'review':'Thanks for offering feedback. Product reviews are not published or stored here.',
      'create_account':'Each shopper session starts with its own sample orders. Real account registration is not connected.',
      'delete_account':'There is no real account to delete. Use Reset session to clear your session’s changes and restore the sample orders.',
      'edit_account':'This application has no real customer profile. To change a sample order’s address before dispatch, say “Change shipping address for order 1041”.',
      'recover_password':'No login or password is needed here. For a real store, use its official password-recovery page; never share passwords or verification codes here.',
      'registration_problems':'Real registration is not available here. You can use the sample orders immediately without creating an account.',
      'switch_account':'Each browser session has its own sample orders. Use Reset session to start fresh; switching real accounts is not connected.',
      'set_up_shipping_address':'For an order that has not shipped, say “Change shipping address for order 1041”. Use fictional address details only.',
      'newsletter_subscription':'Newsletter subscriptions are not connected. This application will not collect your email or send messages.'}
    return reply(answers.get(intent,'Please ask about an order, return, refund or delivery.'),state,p)

def begin(intent,order_id,state,p):
    order=next((o for o in state['orders'] if o['id']==order_id),None)
    if not order:
        state['pending']={'intent':intent,'stage':'order','prediction':p}
        return reply(f'Order {order_id} is not in this session. Please use one of 1041–1045.',state,p)
    state['last_order']=order_id;state['pending']=None;status=order['status']
    if intent=='track_order':
        extra=f" Estimated delivery: {order['estimated_delivery']}. Carrier: {order['carrier']}." if status=='shipped' else f" Delivered on {order['delivered_on']}." if status=='delivered' else ''
        return reply(f"Order {order_id}: {order['item']} — {status.replace('_',' ')}.{extra}",state,p)
    if intent in {'get_invoice','check_invoice'}:
        return reply(f"Invoice INV-{order_id}: {order['quantity']} × {order['item']}, total ₹{order['total']:,}. Order date: {order['ordered_on']}. This is a sample receipt, not a tax invoice.",state,p,invoice_url=f'/api/invoice/{order_id}')
    if intent=='track_refund':
        descriptions={'none':'No refund has been requested.','processing':f"A refund of ₹{order['refund_amount']:,} is processing. Allow 5–7 business days from approval.",'awaiting_return':f"A return is requested. The refund of ₹{order['refund_amount']:,} awaits receipt and approval of the item."}
        return reply(f"Order {order_id}: "+descriptions.get(order['refund_status'],order['refund_status']),state,p)
    if intent=='change_order':return reply('Item and quantity edits are not supported here. You can cancel order 1041 before dispatch or update its delivery address.',state,p)
    if intent in {'cancel_order','change_shipping_address'}:
        if status!='processing':return reply(f"Order {order_id} is {status.replace('_',' ')}. Only orders that are still processing can be cancelled or have their shipping address changed.",state,p)
        if intent=='cancel_order':
            state['pending']={'intent':intent,'stage':'confirm','order_id':order_id}
            return reply(f"Cancel order {order_id} ({order['item']}, ₹{order['total']:,})? Say confirm to cancel and start its refund, or no to keep it.",state,p,suggestions=['Confirm','No'])
        state['pending']={'intent':intent,'stage':'address','order_id':order_id}
        return reply('What fictional address should I use? Include a street and city. Do not enter your real address.',state,p)
    if intent=='get_refund':
        if status in {'return_requested','returned','cancelled'}:return begin('track_refund',order_id,state,p)
        if status!='delivered':return reply(f'Order {order_id} has not been delivered, so a return cannot be started. If it is still processing, you can ask to cancel it.',state,p)
        if (date.today()-date.fromisoformat(order['delivered_on'])).days>14:return reply(f'Order {order_id} is outside the store’s 14-day return window and is not eligible for a standard return.',state,p)
        state['pending']={'intent':intent,'stage':'reason','order_id':order_id}
        return reply(f'Order {order_id} is eligible for a return. What is the reason—for example, wrong size or an item damaged on arrival?',state,p,suggestions=['Wrong size','Item arrived damaged','Wrong item received'])
    return reply('Please ask about order tracking, cancellation, returns or refunds.',state,p)
