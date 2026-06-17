#!/usr/bin/env python3
"""
Simple HTTP GET Stress Tool
Pure GET requests with customizable threads
FOR EDUCATIONAL PURPOSES ONLY - Use on your own servers only!
"""

import threading
import time
import random
import requests
from datetime import datetime
import sys
import signal

# ============================================================
# CONFIGURATION
# ============================================================
TARGET_URL = "https://usl.edu.ph"
THREADS = 20
REQUESTS_PER_THREAD = 100  # 0 = infinite
DELAY_MIN = 0.1  # Minimum delay between requests (seconds)
DELAY_MAX = 0.5  # Maximum delay between requests (seconds)
TIMEOUT = 10

# Statistics
stats = {
    'total': 0,
    'success': 0,
    'failed': 0,
    'errors': [],
    'start_time': None,
    'running': True
}
stats_lock = threading.Lock()

# ============================================================
# FUNCTIONS
# ============================================================

def print_banner():
    """Display banner"""
    print("=" * 60)
    print("  SIMPLE HTTP STRESS TOOL")
    print("  Pure GET Requests | Customizable Threads")
    print("=" * 60)
    print(f"  Target: {TARGET_URL}")
    print(f"  Threads: {THREADS}")
    print(f"  Requests per thread: {'Infinite' if REQUESTS_PER_THREAD == 0 else REQUESTS_PER_THREAD}")
    print(f"  Delay: {DELAY_MIN}s - {DELAY_MAX}s")
    print("=" * 60)
    print("\n[!] Press Ctrl+C to stop\n")

def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    global stats
    stats['running'] = False
    print("\n\n[!] Stopping... Please wait.\n")

def worker(thread_id):
    """Worker thread function"""
    global stats
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    })
    
    requests_sent = 0
    
    while stats['running']:
        # Check if we've reached the limit
        if REQUESTS_PER_THREAD > 0 and requests_sent >= REQUESTS_PER_THREAD:
            break
        
        try:
            start_time = time.time()
            response = session.get(TARGET_URL, timeout=TIMEOUT)
            elapsed = (time.time() - start_time) * 1000  # ms
            
            with stats_lock:
                stats['total'] += 1
                if response.status_code in [200, 301, 302]:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
                
                # Print status every 10 requests
                if stats['total'] % 10 == 0:
                    print_status()
            
            requests_sent += 1
            
        except requests.exceptions.Timeout:
            with stats_lock:
                stats['total'] += 1
                stats['failed'] += 1
                stats['errors'].append('Timeout')
        except requests.exceptions.ConnectionError:
            with stats_lock:
                stats['total'] += 1
                stats['failed'] += 1
                stats['errors'].append('Connection Error')
        except Exception as e:
            with stats_lock:
                stats['total'] += 1
                stats['failed'] += 1
                stats['errors'].append(str(e)[:50])
        
        # Random delay
        if DELAY_MAX > 0:
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    
    if stats['running']:
        print(f"\n[Thread {thread_id}] Completed {requests_sent} requests")

def print_status():
    """Print current statistics"""
    global stats
    
    if stats['total'] == 0:
        return
    
    elapsed = time.time() - stats['start_time']
    rate = stats['total'] / elapsed if elapsed > 0 else 0
    success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    print(f"\r[{datetime.now().strftime('%H:%M:%S')}] "
          f"Total: {stats['total']} | "
          f"Success: {stats['success']} | "
          f"Failed: {stats['failed']} | "
          f"Rate: {rate:.1f}/s | "
          f"Success: {success_rate:.1f}%", end='')

def main():
    """Main function"""
    global stats
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print_banner()
    
    # Start stats
    stats['start_time'] = time.time()
    
    # Create and start threads
    threads = []
    for i in range(THREADS):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        time.sleep(0.05)  # Small delay to prevent startup spike
    
    print(f"[*] Started {THREADS} threads at {datetime.now().strftime('%H:%M:%S')}\n")
    
    # Wait for threads to complete
    for t in threads:
        t.join()
    
    # Final statistics
    elapsed = time.time() - stats['start_time']
    rate = stats['total'] / elapsed if elapsed > 0 else 0
    success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    print("\n\n" + "=" * 60)
    print("  FINAL STATISTICS")
    print("=" * 60)
    print(f"  Total Requests:  {stats['total']}")
    print(f"  Successful:      {stats['success']} ({success_rate:.1f}%)")
    print(f"  Failed:          {stats['failed']} ({100-success_rate:.1f}%)")
    print(f"  Duration:        {elapsed:.1f}s")
    print(f"  Average Rate:    {rate:.1f} req/s")
    
    # Show errors
    if stats['errors']:
        error_counts = {}
        for err in stats['errors']:
            error_counts[err] = error_counts.get(err, 0) + 1
        print("\n  Errors:")
        for err, count in error_counts.items():
            print(f"    - {err}: {count}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
