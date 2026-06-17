#!/usr/bin/env python
"""
Simple HTTP GET Stress Tool - Hardcoded Configuration
FOR EDUCATIONAL PURPOSES ONLY - Use on your own servers only!
"""

import threading
import time
import random
import sys
import signal
import urllib2
import ssl

# ============================================================
# HARDCODED CONFIGURATION - EDIT THESE
# ============================================================
TARGET_URL = "https://usl.edu.ph"  # CHANGE THIS
THREADS = 20
REQUESTS_PER_THREAD = 100  # 0 = infinite
DELAY_MIN = 0.1
DELAY_MAX = 0.5
TIMEOUT = 10

# ============================================================
# STATISTICS
# ============================================================
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
    print("  Target: %s" % TARGET_URL)
    print("  Threads: %d" % THREADS)
    print("  Requests per thread: %s" % ('Infinite' if REQUESTS_PER_THREAD == 0 else str(REQUESTS_PER_THREAD)))
    print("  Delay: %.1fs - %.1fs" % (DELAY_MIN, DELAY_MAX))
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
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive'
    }
    
    requests_sent = 0
    
    while stats['running']:
        if REQUESTS_PER_THREAD > 0 and requests_sent >= REQUESTS_PER_THREAD:
            break
        
        try:
            req = urllib2.Request(TARGET_URL, headers=headers)
            start_time = time.time()
            response = urllib2.urlopen(req, timeout=TIMEOUT)
            
            with stats_lock:
                stats['total'] += 1
                if response.getcode() in [200, 301, 302]:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
                
                if stats['total'] % 10 == 0:
                    print_status()
            
            requests_sent += 1
            
        except urllib2.URLError as e:
            with stats_lock:
                stats['total'] += 1
                stats['failed'] += 1
                stats['errors'].append(str(e.reason)[:50])
        except Exception as e:
            with stats_lock:
                stats['total'] += 1
                stats['failed'] += 1
                stats['errors'].append(str(e)[:50])
        
        if DELAY_MAX > 0:
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

def print_status():
    """Print current statistics"""
    global stats
    
    if stats['total'] == 0:
        return
    
    elapsed = time.time() - stats['start_time']
    rate = stats['total'] / elapsed if elapsed > 0 else 0
    success_rate = (stats['success'] / float(stats['total']) * 100) if stats['total'] > 0 else 0
    
    sys.stdout.write("\r[%s] Total: %d | Success: %d | Failed: %d | Rate: %.1f/s | Success: %.1f%%" % (
        time.strftime('%H:%M:%S'),
        stats['total'],
        stats['success'],
        stats['failed'],
        rate,
        success_rate
    ))
    sys.stdout.flush()

def main():
    """Main function"""
    global stats
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print_banner()
    
    stats['start_time'] = time.time()
    
    threads = []
    for i in range(THREADS):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        time.sleep(0.05)
    
    print("[*] Started %d threads at %s\n" % (THREADS, time.strftime('%H:%M:%S')))
    
    for t in threads:
        t.join()
    
    # Final statistics
    elapsed = time.time() - stats['start_time']
    rate = stats['total'] / elapsed if elapsed > 0 else 0
    success_rate = (stats['success'] / float(stats['total']) * 100) if stats['total'] > 0 else 0
    
    print("\n\n" + "=" * 60)
    print("  FINAL STATISTICS")
    print("=" * 60)
    print("  Total Requests:  %d" % stats['total'])
    print("  Successful:      %d (%.1f%%)" % (stats['success'], success_rate))
    print("  Failed:          %d (%.1f%%)" % (stats['failed'], 100-success_rate))
    print("  Duration:        %.1fs" % elapsed)
    print("  Average Rate:    %.1f req/s" % rate)
    
    if stats['errors']:
        error_counts = {}
        for err in stats['errors']:
            error_counts[err] = error_counts.get(err, 0) + 1
        print("\n  Errors:")
        for err, count in error_counts.items():
            print("    - %s: %d" % (err, count))
    
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user.")
        sys.exit(0)
