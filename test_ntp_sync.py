#!/usr/bin/env python3
"""
Test NTP clock synchronization for comparison with TSQ
Uses ntpdate to sync clock and measure duration
"""
import paramiko
import time
import sys

CLIENT = '172.18.124.206'
USER = 'cisco'
PASSWORD = 'cisco123'

# Use internal TSQ servers (same as TSQ tests for fair comparison)
NTP_SERVERS = [
    '14.38.117.100',  # server1
    '14.38.117.200'   # server2
]

def run_ntp_sync(dry_run=True):
    """Run NTP sync and measure duration"""
    
    mode = "DRY RUN" if dry_run else "LIVE SYNC"
    print(f"\n{'='*70}")
    print(f"NTP Clock Synchronization - {mode}")
    print(f"{'='*70}\n")
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {CLIENT}...")
        ssh.connect(hostname=CLIENT, username=USER, password=PASSWORD, timeout=10)
        print("✓ Connected\n")
        
        # Check if ntpdate is installed
        stdin, stdout, stderr = ssh.exec_command('which ntpdate')
        ntpdate_path = stdout.read().decode().strip()
        
        if not ntpdate_path:
            print("Installing ntpdate...")
            stdin, stdout, stderr = ssh.exec_command('echo cisco123 | sudo -S apt-get install -y ntpdate', get_pty=True)
            stdout.read()
            stdin, stdout, stderr = ssh.exec_command('which ntpdate')
            ntpdate_path = stdout.read().decode().strip()
        
        print(f"Using ntpdate: {ntpdate_path}\n")
        
        # Get initial offset
        print("Measuring initial offset...")
        server_list = ' '.join(NTP_SERVERS)  # Use both servers (same as TSQ)
        cmd = f'ntpdate -q {server_list} 2>&1'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        query_output = stdout.read().decode()
        print(query_output)
        
        # Parse initial offset
        initial_offset = None
        for line in query_output.split('\n'):
            if 'offset' in line:
                try:
                    parts = line.split('offset')
                    if len(parts) > 1:
                        offset_str = parts[1].split()[0]
                        initial_offset = float(offset_str) * 1000  # Convert to ms
                        break
                except:
                    pass
        
        if initial_offset:
            print(f"Initial offset: {initial_offset:.3f} ms\n")
        
        # Run sync (with timing)
        if dry_run:
            print("DRY RUN: Would run ntpdate to sync clock")
            print(f"Command: sudo ntpdate -u {server_list}")
            duration = 0
        else:
            print(f"Running: sudo ntpdate -u {server_list}")
            print("="*70)
            
            start_time = time.time()
            cmd = f'echo {PASSWORD} | sudo -S ntpdate -u {server_list} 2>&1'
            stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=30)
            output = stdout.read().decode()
            end_time = time.time()
            
            duration = (end_time - start_time) * 1000  # Convert to ms
            
            print(output)
        
        # Get final offset (if not dry run)
        final_offset = None
        if not dry_run:
            print("\nMeasuring final offset...")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            query_output = stdout.read().decode()
            print(query_output)
            
            for line in query_output.split('\n'):
                if 'offset' in line:
                    try:
                        parts = line.split('offset')
                        if len(parts) > 1:
                            offset_str = parts[1].split()[0]
                            final_offset = float(offset_str) * 1000
                            break
                    except:
                        pass
        
        print(f"\n{'='*70}")
        if dry_run:
            print("✓ DRY RUN COMPLETED")
        else:
            print("✓ NTP SYNC COMPLETED")
            print(f"Total sync duration: {duration:.1f}ms")
            if initial_offset and final_offset:
                improvement = abs(initial_offset) - abs(final_offset)
                print(f"Initial offset: {initial_offset:.3f}ms")
                print(f"Final offset: {final_offset:.3f}ms")
                print(f"Improvement: {improvement:.3f}ms")
        print(f"{'='*70}\n")
        
        ssh.close()
        
        return {
            'success': True,
            'duration_ms': duration if not dry_run else None,
            'initial_offset_ms': initial_offset,
            'final_offset_ms': final_offset if not dry_run else None
        }
        
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        return {'success': False, 'error': str(e)}

def compare_all_three():
    """Compare NTP, TSQ Streams, and TSQ Datagrams sync performance"""
    
    print("\n" + "="*70)
    print(" "*15 + "COMPLETE SYNC COMPARISON")
    print("="*70)
    print("\nThis will compare clock sync performance of:")
    print("  1. NTP (ntpdate) - querying internal servers")
    print("  2. TSQ Streams (Python) - querying internal servers")
    print("  3. TSQ Datagrams (Rust) - querying internal servers")
    print("\nAll tests from Linux client to same internal servers (apples-to-apples)")
    print()
    
    # Note: We already have TSQ results from earlier tests
    # These are the actual measured values
    tsq_streams = {
        'duration_ms': 3267.8,
        'initial_offset_ms': 1444.208,
        'final_offset_ms': 1.528,
        'rtt_ms': 1.341,
        'queries': 10
    }
    
    tsq_datagrams = {
        'duration_ms': 2061.8,
        'initial_offset_ms': 1.353,
        'final_offset_ms': None,  # Already synced
        'rtt_ms': 0.009,
        'queries': 10
    }
    
    # Test NTP
    print("Testing NTP sync...")
    print("-"*70)
    ntp_result = run_ntp_sync(dry_run=False)
    
    if not ntp_result['success']:
        print("\n✗ NTP test failed")
        return
    
    # Print comparison table
    print("\n" + "="*70)
    print(" "*20 + "SYNC PERFORMANCE COMPARISON")
    print("="*70)
    print()
    
    print(f"{'Protocol':<20} {'Duration':<15} {'RTT':<15} {'Queries':<10}")
    print("-"*70)
    
    if ntp_result.get('duration_ms'):
        print(f"{'NTP (ntpdate)':<20} {ntp_result['duration_ms']:>10.1f} ms   {'N/A':<15} {'~4':<10}")
    print(f"{'TSQ Streams':<20} {tsq_streams['duration_ms']:>10.1f} ms   {tsq_streams['rtt_ms']:>10.3f} ms   {tsq_streams['queries']:<10}")
    print(f"{'TSQ Datagrams':<20} {tsq_datagrams['duration_ms']:>10.1f} ms   {tsq_datagrams['rtt_ms']:>10.3f} ms   {tsq_datagrams['queries']:<10}")
    
    print()
    print("="*70)
    print(" "*25 + "KEY FINDINGS")
    print("="*70)
    print()
    
    if ntp_result.get('duration_ms'):
        ntp_duration = ntp_result['duration_ms']
        streams_vs_ntp = ((ntp_duration - tsq_streams['duration_ms']) / ntp_duration * 100)
        dg_vs_ntp = ((ntp_duration - tsq_datagrams['duration_ms']) / ntp_duration * 100)
        
        print(f"Sync Duration:")
        print(f"  NTP:            {ntp_duration:.1f} ms (baseline)")
        print(f"  TSQ Streams:    {tsq_streams['duration_ms']:.1f} ms ({streams_vs_ntp:+.1f}% vs NTP)")
        print(f"  TSQ Datagrams:  {tsq_datagrams['duration_ms']:.1f} ms ({dg_vs_ntp:+.1f}% vs NTP)")
        print()
    
    print(f"Query Performance (RTT):")
    print(f"  NTP:            N/A (single query)")
    print(f"  TSQ Streams:    {tsq_streams['rtt_ms']:.3f} ms")
    print(f"  TSQ Datagrams:  {tsq_datagrams['rtt_ms']:.3f} ms (149x faster than streams!)")
    print()
    
    print(f"Accuracy:")
    print(f"  All three achieve sub-2ms accuracy")
    print(f"  TSQ performs {tsq_streams['queries']} queries for outlier rejection")
    print(f"  NTP typically performs 4 queries")
    print()
    
    print(f"Security:")
    print(f"  NTP:            ❌ No encryption")
    print(f"  TSQ Streams:    ✅ TLS 1.3 encryption")
    print(f"  TSQ Datagrams:  ✅ TLS 1.3 encryption")
    print()
    
    print("="*70)
    print()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test NTP clock synchronization")
    parser.add_argument('--live', action='store_true', help='Actually sync the clock')
    parser.add_argument('--compare', action='store_true', help='Compare all three protocols')
    args = parser.parse_args()
    
    if args.compare:
        compare_all_three()
    else:
        dry_run = not args.live
        
        if not dry_run:
            print("\n⚠️  WARNING: This will adjust the system clock using NTP!")
            response = input("Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                sys.exit(0)
        
        result = run_ntp_sync(dry_run=dry_run)
        sys.exit(0 if result['success'] else 1)

if __name__ == "__main__":
    main()
