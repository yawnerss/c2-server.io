#!/usr/bin/env python
"""
Interactive HTTP GET Stress Tool
Pure GET requests with customizable threads
FOR EDUCATIONAL PURPOSES ONLY - Use on your own servers only!
"""

import threading
import time
import random
import sys
import signal
import urllib2
import ssl
import urlparse

# ============================================================
# GLOBAL STATISTICS
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

def get_input(prompt, default=None, input_type=str, min_val=None, max_val=None):
    """Get user input with validation"""
    while True:
        if default is not None:
            full_prompt = "%s [%s]: " % (prompt, str(default))
        else:
            full_prompt = prompt + ": "
        
        try:
            user_input = raw_input(full_prompt).strip()
            if not user_input and default is not None:
                return default
            
            if input_type == int:
                value = int(user_input)
                if min_val is not None and value < min_val:
                    print("  Value must be >= %d" % min_val)
                    continue
                if max_val is not None and value > max_val:
                    print("  Value must be <= %d" % max_val)
                    continue
                return value
            elif input_type == float:
                value = float(user_input)
                if min_val is not None and value < min_val:
                    print("  Value must be >= %.1f" % min_val)
                    continue
                return value
            else:
                return user_input
        except ValueError:
            print("  Invalid input. Please try again.")

def print_banner():
    """Display banner"""
    print("=" * 60)
    print("  INTERACTIVE HTTP STRESS TOOL")
    print("  Pure GET Requests | Customizable Threads")
    print("=" * 60)

def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    global stats
    stats['running'] = False
    print("\n\n[!] Stopping... Please wait.\n")

def worker(thread_id, target_url, requests_per_thread, delay_min, delay_max, timeout):
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
        if requests_per_thread > 0 and requests_sent >= requests_per_thread:
            break
        
        try:
            req = urllib2.Request(target_url, headers=headers)
            start_time = time.time()
            response = urllib2.urlopen(req, timeout=timeout)
            elapsed = (time.time() - start_time) * 1000
            
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
        
        if delay_max > 0:
            time.sleep(random.uniform(delay_min, delay_max))

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

def show_final_stats():
    """Show final statistics"""
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

def main():
    """Main function"""
    global stats
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print_banner()
    print("\n[!] For educational purposes only. Use on your own servers.\n")
    
    # Get user input
    print("Enter configuration parameters:")
    print("-" * 40)
    
    target_url = get_input("Target URL (e.g., http://example.com)", "http://example.com")
    
    # Validate URL
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'http://' + target_url
    
    threads = get_input("Number of threads", 10, int, min_val=1, max_val=1000)
    requests_per_thread = get_input("Requests per thread (0 = unlimited)", 100, int, min_val=0)
    delay_min = get_input("Minimum delay between requests (seconds)", 0.1, float, min_val=0)
    delay_max = get_input("Maximum delay between requests (seconds)", 0.5, float, min_val=0)
    timeout = get_input("Request timeout (seconds)", 10, int, min_val=1)
    
    # Confirm
    print("\n" + "=" * 60)
    print("  CONFIGURATION SUMMARY")
    print("=" * 60)
    print("  Target URL:          %s" % target_url)
    print("  Threads:             %d" % threads)
    print("  Requests per thread: %s" % ('Unlimited' if requests_per_thread == 0 else str(requests_per_thread)))
    print("  Min Delay:           %.1fs" % delay_min)
    print("  Max Delay:           %.1fs" % delay_max)
    print("  Timeout:             %ds" % timeout)
    print("=" * 60)
    
    confirm = get_input("\nStart the attack? (y/n)", "y")
    if confirm.lower() not in ['y', 'yes']:
        print("Aborted.")
        return
    
    # Start stats
    stats['start_time'] = time.time()
    
    # Create and start threads
    threads_list = []
    for i in range(threads):
        t = threading.Thread(target=worker, args=(i, target_url, requests_per_thread, delay_min, delay_max, timeout))
        threads_list.append(t)
        t.start()
        time.sleep(0.05)
    
    print("\n[*] Started %d threads at %s" % (threads, time.strftime('%H:%M:%S')))
    print("[*] Press Ctrl+C to stop\n")
    
    # Wait for threads to complete
    for t in threads_list:
        t.join()
    
    # Show final stats
    show_final_stats()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user.")
        sys.exit(0)
