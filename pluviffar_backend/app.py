import calendar
import csv
import io
import math
import os
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify, session, send_from_directory, Response
from werkzeug.security import generate_password_hash, check_password_hash

ROOT = Path(__file__).resolve().parent

def create_app(config=None):
    app = Flask(__name__, static_folder=str(ROOT.parent / 'pluviffar_frontend'), static_url_path='/assets')
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_hex(32), DATABASE=os.getenv('DATABASE_PATH', str(ROOT / 'instance' / 'pluviffar.sqlite3')), ADMIN_USER=os.getenv('ADMIN_USER', 'admin'), ADMIN_PASS=os.getenv('ADMIN_PASS'), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict', MAX_CONTENT_LENGTH=16384)
    if config: app.config.update(config)
    tz = ZoneInfo('America/Sao_Paulo')
    dbpath = Path(app.config['DATABASE']); dbpath.parent.mkdir(parents=True, exist_ok=True)
    @contextmanager
    def db():
        conn = sqlite3.connect(dbpath); conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        try:
            with conn:
                yield conn
        finally:
            conn.close()
    with db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS devices(id INTEGER PRIMARY KEY, device_code TEXT UNIQUE NOT NULL, mac_address TEXT NOT NULL, location_name TEXT NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL, mm_per_tick_default REAL NOT NULL, is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS readings(id INTEGER PRIMARY KEY, device_id INTEGER REFERENCES devices(id), timestamp TEXT NOT NULL, ticks INTEGER NOT NULL, mm_per_tick REAL NOT NULL, battery_mv INTEGER, UNIQUE(device_id,timestamp));
CREATE INDEX IF NOT EXISTS reading_time ON readings(device_id,timestamp);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, timestamp TEXT, action TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);''')
        if not c.execute('SELECT 1 FROM devices').fetchone():
            c.execute('INSERT INTO devices(device_code,mac_address,location_name,latitude,longitude,mm_per_tick_default) VALUES(?,?,?,?,?,?)', ('ESP001','84:CC:A8:12:34:56','IFFar – Campus Panambi',float(os.getenv('DEFAULT_LATITUDE','-28.286')),float(os.getenv('DEFAULT_LONGITUDE','-53.501')),0.25))
        if app.config['ADMIN_PASS']:
            password_hash = generate_password_hash(app.config['ADMIN_PASS'])
        else:
            row = c.execute("SELECT value FROM settings WHERE key='admin_hash'").fetchone()
            if row: password_hash = row[0]
            else:
                password = secrets.token_urlsafe(12); password_hash = generate_password_hash(password)
                c.execute("INSERT INTO settings VALUES('admin_hash',?)", (password_hash,))
                print(f'Primeiro acesso local: usuário {app.config["ADMIN_USER"]}, senha {password}', flush=True)
    buckets = defaultdict(deque)
    def limited(key, limit, seconds):
        now=time.monotonic(); q=buckets[key]
        while q and q[0] < now-seconds: q.popleft()
        if len(q)>=limit: return True
        q.append(now); return False
    @app.before_request
    def protect():
        if request.path in ('/api/v1/readings','/admin/login') and request.method=='POST':
            if limited((request.path,request.remote_addr), 10 if request.path=='/admin/login' else 1000,3600): return jsonify(error='Limite de requisições excedido.'),429
        if request.path.startswith('/admin/') and request.method in ('POST','PUT','DELETE') and request.path!='/admin/login':
            if not session.get('authenticated'): return jsonify(error='Faça login.'),401
            if not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),session.get('csrf','!')): return jsonify(error='Sessão inválida. Atualize a página.'),403
    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Cache-Control']='no-store'
        return response
    def admin(fn):
        @wraps(fn)
        def wrapped(*a,**kw):
            if not session.get('authenticated'): return jsonify(error='Faça login.'),401
            return fn(*a,**kw)
        return wrapped
    def body():
        data=request.get_json(silent=True)
        if not isinstance(data,dict): raise ValueError('Envie um objeto JSON.')
        return data
    def number(data,key,low,high,default=None):
        val=data.get(key,default)
        if isinstance(val,bool): raise ValueError(f'{key}: valor inválido.')
        try: val=float(val)
        except (ValueError,TypeError): raise ValueError(f'{key}: informe um número.')
        if not math.isfinite(val) or not low<=val<=high: raise ValueError(f'{key}: fora do intervalo permitido.')
        return val
    @app.errorhandler(ValueError)
    def invalid(e): return jsonify(error=str(e)),422
    @app.errorhandler(sqlite3.IntegrityError)
    def conflict(e): return jsonify(error='Registro já existe ou referência inválida.'),409
    @app.get('/')
    @app.get('/admin')
    def index(): return send_from_directory(app.static_folder,'index.html')
    @app.get('/healthz')
    @app.get('/api/healthz')
    def health(): return jsonify(status='ok')
    @app.post('/admin/login')
    def login():
        d=body()
        if d.get('username')!=app.config['ADMIN_USER'] or not isinstance(d.get('password'),str) or not check_password_hash(password_hash,d['password']): return jsonify(error='Usuário ou senha inválidos.'),401
        session.clear(); session['authenticated']=True; session['csrf']=secrets.token_hex(24)
        return jsonify(csrf=session['csrf'])
    @app.get('/admin/session')
    @admin
    def current(): return jsonify(csrf=session['csrf'])
    @app.post('/admin/logout')
    def logout(): session.clear(); return jsonify(status='ok')
    @app.get('/data/locations')
    def locations():
        with db() as c: rows=c.execute('SELECT id,location_name,latitude,longitude FROM devices WHERE is_active=1 ORDER BY id').fetchall()
        return jsonify([dict(r) for r in rows])
    @app.get('/admin/devices')
    @admin
    def devices():
        with db() as c: rows=c.execute('SELECT * FROM devices ORDER BY id').fetchall()
        return jsonify([dict(r) for r in rows])
    def device_data(d):
        values=[]
        for key in ('device_code','mac_address','location_name'):
            val=d.get(key)
            if not isinstance(val,str) or not val.strip() or len(val)>200: raise ValueError(f'{key}: campo obrigatório (até 200 caracteres).')
            values.append(val.strip())
        if not re.fullmatch(r'[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}',values[1]): raise ValueError('MAC inválido. Use AA:BB:CC:DD:EE:FF.')
        values[1]=values[1].upper()
        values += [number(d,'latitude',-90,90),number(d,'longitude',-180,180),number(d,'mm_per_tick_default',0.000001,100,0.25)]
        return values
    @app.post('/admin/devices')
    @admin
    def add():
        values=device_data(body())
        with db() as c:
            cur=c.execute('INSERT INTO devices(device_code,mac_address,location_name,latitude,longitude,mm_per_tick_default) VALUES(?,?,?,?,?,?)',values)
            c.execute('INSERT INTO audit(timestamp,action) VALUES(?,?)',(datetime.now(timezone.utc).isoformat(),f'Dispositivo {cur.lastrowid} cadastrado'))
        return jsonify(id=cur.lastrowid),201
    @app.put('/admin/devices/<int:ident>')
    @admin
    def edit(ident):
        d=body(); values=device_data(d)
        if d.get('is_active',1) not in (0,1,False,True): raise ValueError('is_active inválido.')
        with db() as c:
            cur=c.execute('UPDATE devices SET device_code=?,mac_address=?,location_name=?,latitude=?,longitude=?,mm_per_tick_default=?,is_active=? WHERE id=?',values+[int(d.get('is_active',1)),ident])
            if not cur.rowcount: return jsonify(error='Dispositivo não encontrado.'),404
            c.execute('INSERT INTO audit(timestamp,action) VALUES(?,?)',(datetime.now(timezone.utc).isoformat(),f'Dispositivo {ident} atualizado'))
        return jsonify(status='ok')
    @app.delete('/admin/devices/<int:ident>')
    @admin
    def deactivate(ident):
        with db() as c:
            cur=c.execute('UPDATE devices SET is_active=0 WHERE id=?',(ident,))
            if not cur.rowcount: return jsonify(error='Dispositivo não encontrado.'),404
            c.execute('INSERT INTO audit(timestamp,action) VALUES(?,?)',(datetime.now(timezone.utc).isoformat(),f'Dispositivo {ident} desativado'))
        return jsonify(status='ok')
    @app.get('/admin/audit')
    @admin
    def audit():
        with db() as c: rows=c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100').fetchall()
        return jsonify([dict(r) for r in rows])
    @app.post('/api/v1/readings')
    def ingest():
        d=body()
        with db() as c:
            device=c.execute('SELECT * FROM devices WHERE device_code=? AND mac_address=? AND is_active=1',(str(d.get('device_code','')),str(d.get('mac_address','')).upper())).fetchone()
            if not device: return jsonify(error='Dispositivo inválido ou inativo.'),401
            ticks=number(d,'ticks',0,10000000)
            if not ticks.is_integer(): raise ValueError('ticks deve ser inteiro.')
            try:
                stamp=datetime.fromisoformat(str(d.get('timestamp','')).replace('Z','+00:00'))
                if stamp.tzinfo is None: raise ValueError()
                stamp=stamp.astimezone(timezone.utc)
            except (ValueError,OverflowError): raise ValueError('timestamp deve ser ISO 8601 com fuso horário.')
            factor=number(d,'mm_per_tick',0.000001,100,device['mm_per_tick_default'])
            battery=None if d.get('battery_mv') is None else number(d,'battery_mv',0,100000)
            old=c.execute('SELECT id,ticks,mm_per_tick,battery_mv FROM readings WHERE device_id=? AND timestamp=?',(device['id'],stamp.isoformat())).fetchone()
            if old:
                if tuple(old)[1:]!=(int(ticks),factor,battery): return jsonify(error='Timestamp já usado com outra leitura.'),409
                return jsonify(status='ok',stored=False,reading_id=old['id'])
            cur=c.execute('INSERT INTO readings(device_id,timestamp,ticks,mm_per_tick,battery_mv) VALUES(?,?,?,?,?)',(device['id'],stamp.isoformat(),int(ticks),factor,battery))
        return jsonify(status='ok',stored=True,reading_id=cur.lastrowid),201
    @app.get('/data/location/<int:ident>/<period>')
    def history(ident,period):
        if period not in ('daily','monthly','yearly'): return jsonify(error='Período inválido.'),404
        try: selected=datetime.strptime(request.args.get('date',datetime.now(tz).strftime('%Y-%m-%d')),'%Y-%m-%d').date()
        except ValueError: raise ValueError('Data inválida. Use AAAA-MM-DD.')
        with db() as c:
            device=c.execute('SELECT id FROM devices WHERE id=? AND is_active=1',(ident,)).fetchone()
            if not device: return jsonify(error='Localidade não encontrada.'),404
            rows=c.execute('SELECT * FROM readings WHERE device_id=? ORDER BY timestamp',(ident,)).fetchall()
        count=24 if period=='daily' else calendar.monthrange(selected.year,selected.month)[1] if period=='monthly' else 12
        totals=[0.0]*count; today_total=0; last=None
        for r in rows:
            stamp=datetime.fromisoformat(r['timestamp']).astimezone(tz); amount=r['ticks']*r['mm_per_tick']; last=r['timestamp']
            if stamp.date()==datetime.now(tz).date(): today_total+=amount
            if stamp.year!=selected.year: continue
            if period!='yearly' and stamp.month!=selected.month: continue
            if period=='daily' and stamp.day!=selected.day: continue
            idx=stamp.hour if period=='daily' else stamp.day-1 if period=='monthly' else stamp.month-1
            totals[idx]+=amount
        labels=[f'{i:02d}:00' if period=='daily' else str(i+1) if period=='monthly' else ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][i] for i in range(count)]
        points=[{'label':label,'mm':round(val,4)} for label,val in zip(labels,totals)]
        if request.args.get('format')=='csv':
            output=io.StringIO(); writer=csv.writer(output); writer.writerow(['periodo','data','intervalo','precipitacao_mm'])
            writer.writerows((period,selected.isoformat(),p['label'],p['mm']) for p in points)
            return Response('\ufeff'+output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename=pluviffar-{ident}-{period}-{selected}.csv'})
        return jsonify(points=points,total=round(sum(totals),4),today=round(today_total,4),last_reading=last,timezone=str(tz))
    return app

if __name__=='__main__':
    create_app().run(host='127.0.0.1',port=int(os.getenv('PORT','5000')),debug=False)
