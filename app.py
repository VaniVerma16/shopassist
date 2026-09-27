"""Flask API + static frontend. Session-isolated SQLite demo state."""
import json,os,secrets,sqlite3,time,uuid
from pathlib import Path
from flask import Flask,request,jsonify,session,send_from_directory,Response
from engine import fresh_state,handle
from model import Predictor,ROOT

def create_app(db_path=None,predictor=None):
    app=Flask(__name__,static_folder='static',static_url_path='/static')
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_hex(32),MAX_CONTENT_LENGTH=8192,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','0')=='1')
    database=str(db_path or os.getenv('DATABASE_PATH','/tmp/shopassist.sqlite3'))
    Path(database).parent.mkdir(parents=True,exist_ok=True)
    def connect():
        con=sqlite3.connect(database,timeout=15);con.execute('PRAGMA journal_mode=WAL');return con
    with connect() as con:
        con.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, state TEXT NOT NULL, updated REAL NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS messages (sid TEXT, rid TEXT, body TEXT, result TEXT, created REAL, PRIMARY KEY(sid,rid))')
        con.execute('DELETE FROM sessions WHERE updated < ?',(time.time()-86400,))
        con.execute('DELETE FROM messages WHERE created < ?',(time.time()-86400,))
    classifier=predictor or Predictor()
    def load(con):
        con.execute('DELETE FROM sessions WHERE updated < ?', (time.time()-86400,))
        con.execute('DELETE FROM messages WHERE created < ?', (time.time()-86400,))
        sid=session.get('sid')
        if not sid:sid=uuid.uuid4().hex;session['sid']=sid
        row=con.execute('SELECT state,updated FROM sessions WHERE id=?',(sid,)).fetchone()
        state=json.loads(row[0]) if row and row[1]>time.time()-86400 else fresh_state()
        return sid,state
    def save(con,sid,state):con.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)',(sid,json.dumps(state),time.time()))
    @app.after_request
    def headers(res):
        res.headers['X-Content-Type-Options']='nosniff';res.headers['Referrer-Policy']='same-origin'
        if request.path.startswith('/api/'):res.headers['Cache-Control']='no-store'
        return res
    @app.errorhandler(413)
    def too_large(e):return jsonify(error='Request too large.'),413
    @app.get('/')
    def index():return send_from_directory(app.static_folder,'index.html')
    @app.get('/health')
    def health():return jsonify(status='ok',model='BiLSTM',intents=len(classifier.labels))
    @app.get('/api/session')
    def current():
        with connect() as con:
            con.execute('BEGIN IMMEDIATE');sid,state=load(con);save(con,sid,state)
        return jsonify(orders=state['orders'],pending=state['pending'],model={'architecture':'Embedding 64 → BiLSTM 64×2 → Dense 64 → 27 intents','threshold':classifier.meta['threshold']})
    @app.post('/api/chat')
    def chat():
        body=request.get_json(silent=True)
        if not isinstance(body,dict):return jsonify(error='Send a JSON object.'),400
        text=body.get('message');rid=body.get('request_id')
        if not isinstance(text,str) or not text.strip() or len(text)>500:return jsonify(error='Enter a message of 1–500 characters.'),400
        if not isinstance(rid,str) or len(rid)>80 or not rid:return jsonify(error='A request ID is required.'),400
        with connect() as con:
            con.execute('BEGIN IMMEDIATE');sid,state=load(con)
            prev=con.execute('SELECT body,result FROM messages WHERE sid=? AND rid=?',(sid,rid)).fetchone()
            if prev:
                if prev[0]!=text:return jsonify(error='Request ID already used for a different message.'),409
                return jsonify(json.loads(prev[1]))
            count=con.execute('SELECT count(*) FROM messages WHERE sid=? AND created>?',(sid,time.time()-60)).fetchone()[0]
            if count>=40:return jsonify(error='Please wait a minute before sending more messages.'),429
            start=time.perf_counter();result=handle(text.strip(),state,classifier.predict);result['processing_ms']=round((time.perf_counter()-start)*1000,1)
            save(con,sid,state)
            con.execute('INSERT INTO messages VALUES(?,?,?,?,?)',(sid,rid,text,json.dumps(result),time.time()))
            con.execute('DELETE FROM messages WHERE sid=? AND rid NOT IN (SELECT rid FROM messages WHERE sid=? ORDER BY created DESC LIMIT 100)',(sid,sid))
        return jsonify(result)
    @app.post('/api/reset')
    def reset():
        with connect() as con:
            con.execute('BEGIN IMMEDIATE');sid,state=load(con);state=fresh_state();save(con,sid,state);con.execute('DELETE FROM messages WHERE sid=?',(sid,))
        return jsonify(orders=state['orders'],pending=None)
    @app.get('/api/invoice/<order_id>')
    def invoice(order_id):
        with connect() as con:sid,state=load(con)
        order=next((o for o in state['orders'] if o['id']==order_id),None)
        if not order:return jsonify(error='Order not found.'),404
        text=f"SHOPASSIST - RECEIPT\nNot a tax invoice. No real transaction.\n\nInvoice: INV-{order_id}\nOrder: {order_id}\nDate: {order['ordered_on']}\nItem: {order['item']}\nQuantity: {order['quantity']}\nTotal: INR {order['total']}\nStatus: {order['status']}\n"
        return Response(text,mimetype='text/plain',headers={'Content-Disposition':f'attachment; filename=invoice-{order_id}.txt'})
    return app

if __name__=='__main__':
    create_app().run(host='0.0.0.0',port=int(os.getenv('PORT','7860')),debug=False)
