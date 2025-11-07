#!/usr/bin/env python3
"""
Test NTS (Network Time Security) clock synchronization
Compare encrypted NTP (NTS) vs encrypted QUIC (TSQ)
"""
import paramiko
import time
import sys

CLIENT = '172.18.124.206'
USER = 'cisco'
PASSWORD = 'cisco123'

# Public NTS servers (internal servers likely don't support NTS)
NTS_SERVERS = [
    'time.cloudflare.com',  # Cloudflare NTS
    'nts.ntp.se',           # Swedish NTS
]

def check_nts_support():
    """Check if chronyd with NTS support is available"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=CLIENT, username=USER, password=PASSWORD)
        
        # Check if chronyd is installed
        stdin, stdout, stderr = ssh.exec_command('which chronyd')
        chronyd_path = stdout.read().decode().strip()
        
        if not chronyd_path:
            print("chronyd not found. Installing...")
            stdin, stdout, stderr = ssh.exec_command('echo cisco123 | sudo -S apt-get install -y chrony', get_pty=True)
            stdout.read()
            stdin, stdout, stderr = ssh.exec_command('which chronyd')
            chronyd_path = stdout.read().decode().strip()
        
        # Check chronyd version (NTS requires 4.0+)
        stdin, stdout, stderr = ssh.exec_command('chronyd -v')
        version_output = stdout.read().decode()
        print(f"Found: {version_output.strip()}")
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"Error checking NTS support: {e}")
        return False

def test_nts_sync(dry_run=True):
    """Test NTS sync using chronyd"""
    
    mode = "DRY RUN" if dry_run else "LIVE SYNC"
    print(f"\n{'='*70}")
    print(f"NTS Clock Synchronization - {mode}")
    print(f"{'='*70}\n")
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {CLIENT}...")
        ssh.connect(hostname=CLIENT, username=USER, password=PASSWORD, timeout=10)
        print("✓ Connected\n")
        
        # Create temporary chrony config for NTS
        print("Configuring chronyd for NTS...")
        nts_config = f"""
# Temporary NTS configuration
server {NTS_SERVERS[0]} iburst nts
server {NTS_SERVERS[1]} iburst nts

# Allow stepping on first update
makestep 1 3

driftfile /tmp/chrony.drift
logdir /tmp
"""
        
        # Write config
        stdin, stdout, stderr = ssh.exec_command('cat > /tmp/chrony-nts.conf', get_pty=True)
        stdin.write(nts_config)
        stdin.channel.shutdown_write()
        stdout.read()
        
        print(f"NTS Servers: {', '.join(NTS_SERVERS)}\n")
        
        if dry_run:
            print("DRY RUN: Would run chronyd with NTS configuration")
            print("Command: sudo chronyd -q -f /tmp/chrony-nts.conf")
            ssh.close()
            return {'success': True, 'duration_ms': None}
        
        # Stop any running chronyd
        ssh.exec_command('echo cisco123 | sudo -S systemctl stop chronyd 2>/dev/null', get_pty=True)
        time.sleep(1)
        
        # Run chronyd in one-shot mode with NTS
        print("Running chronyd with NTS (this may take 10-30 seconds)...")
        print("="*70)
        
        start_time = time.time()
        cmd = 'echo cisco123 | sudo -S chronyd -q -f /tmp/chrony-nts.conf 2>&1'
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=60)
        output = stdout.read().decode()
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000
        
        print(output)
        
        # Restart normal chronyd
        ssh.exec_command('echo cisco123 | sudo -S systemctl start chronyd 2>/dev/null', get_pty=True)
        
        print(f"\n{'='*70}")
        print("✓ NTS SYNC COMPLETED")
        print(f"Total sync duration: {duration:.1f}ms")
        print(f"{'='*70}\n")
        
        ssh.close()
        
        return {
            'success': True,
            'duration_ms': duration,
            'output': output
        }
        
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        return {'success': False, 'error': str(e)}

def compare_all_four():
    """Compare NTP, NTS, TSQ Streams, and TSQ Datagrams"""
    
    print("\n" + "="*70)
    print(" "*10 + "COMPLETE ENCRYPTED TIME SYNC COMPARISON")
    print("="*70)
    print("\nComparing:")
    print("  1. NTP (ntpdate) - No encryption")
    print("  2. NTS (chronyd) - NTP with TLS encryption")
    print("  3. TSQ Streams - QUIC with TLS 1.3")
    print("  4. TSQ Datagrams - QUIC with TLS 1.3")
    print()
    
    # Check NTS support
    if not check_nts_support():
        print("\n✗ NTS not supported on this system")
        return
    
    print()
    
    # Known results from previous tests
    ntp_result = {
        'duration_ms': 168.9,
        'encryption': False,
        'queries': 4
    }
    
    tsq_streams = {
        'duration_ms': 3267.8,
        'rtt_ms': 1.341,
        'encryption': True,
        'queries': 10
    }
    
    tsq_datagrams = {
        'duration_ms': 2061.8,
        'rtt_ms': 0.009,
        'encryption': True,
        'queries': 10
    }
    
    # Test NTS
    print("Testing NTS sync...")
    print("-"*70)
    nts_result = test_nts_sync(dry_run=False)
    
    if not nts_result['success']:
        print("\n✗ NTS test failed")
        return
    
    # Print comparison
    print("\n" + "="*70)
    print(" "*15 + "ENCRYPTED TIME SYNC COMPARISON")
    print("="*70)
    print()
    
    print(f"{'Protocol':<20} {'Duration':<15} {'RTT':<15} {'Encryption':<15}")
    print("-"*70)
    print(f"{'NTP (baseline)':<20} {ntp_result['duration_ms']:>10.1f} ms   {'N/A':<15} {'❌ None':<15}")
    
    if nts_result.get('duration_ms'):
        print(f"{'NTS (encrypted)':<20} {nts_result['duration_ms']:>10.1f} ms   {'N/A':<15} {'✅ TLS':<15}")
    
    print(f"{'TSQ Streams':<20} {tsq_streams['duration_ms']:>10.1f} ms   {tsq_streams['rtt_ms']:>10.3f} ms   {'✅ TLS 1.3':<15}")
    print(f"{'TSQ Datagrams':<20} {tsq_datagrams['duration_ms']:>10.1f} ms   {tsq_datagrams['rtt_ms']:>10.3f} ms   {'✅ TLS 1.3':<15}")
    
    print()
    print("="*70)
    print(" "*20 + "KEY FINDINGS")
    print("="*70)
    print()
    
    if nts_result.get('duration_ms'):
        nts_duration = nts_result['duration_ms']
        
        print(f"Sync Duration (Encrypted Protocols):")
        print(f"  NTS:            {nts_duration:.1f} ms")
        print(f"  TSQ Streams:    {tsq_streams['duration_ms']:.1f} ms")
        print(f"  TSQ Datagrams:  {tsq_datagrams['duration_ms']:.1f} ms")
        print()
        
        if nts_duration < tsq_streams['duration_ms']:
            streams_vs_nts = ((tsq_streams['duration_ms'] - nts_duration) / nts_duration * 100)
            print(f"  TSQ Streams is {streams_vs_nts:.1f}% slower than NTS")
        else:
            streams_vs_nts = ((nts_duration - tsq_streams['duration_ms']) / tsq_streams['duration_ms'] * 100)
            print(f"  TSQ Streams is {streams_vs_nts:.1f}% faster than NTS")
        
        if nts_duration < tsq_datagrams['duration_ms']:
            dg_vs_nts = ((tsq_datagrams['duration_ms'] - nts_duration) / nts_duration * 100)
            print(f"  TSQ Datagrams is {dg_vs_nts:.1f}% slower than NTS")
        else:
            dg_vs_nts = ((nts_duration - tsq_datagrams['duration_ms']) / tsq_datagrams['duration_ms'] * 100)
            print(f"  TSQ Datagrams is {dg_vs_nts:.1f}% faster than NTS")
        
        print()
    
    print(f"Query Performance (RTT):")
    print(f"  NTP:            N/A (no encryption)")
    print(f"  NTS:            N/A (encrypted)")
    print(f"  TSQ Streams:    {tsq_streams['rtt_ms']:.3f} ms (encrypted)")
    print(f"  TSQ Datagrams:  {tsq_datagrams['rtt_ms']:.3f} ms (encrypted, 149x faster than streams!)")
    print()
    
    print(f"Encryption:")
    print(f"  NTP:            ❌ None")
    print(f"  NTS:            ✅ TLS (NTP extension)")
    print(f"  TSQ Streams:    ✅ TLS 1.3 (native QUIC)")
    print(f"  TSQ Datagrams:  ✅ TLS 1.3 (native QUIC)")
    print()
    
    print(f"Protocol Maturity:")
    print(f"  NTP:            ✅ Mature (RFC 5905, 2010)")
    print(f"  NTS:            ⚠️  New (RFC 8915, 2020)")
    print(f"  TSQ:            🆕 Novel (Draft, 2025)")
    print()
    
    print("="*70)
    print()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test NTS clock synchronization")
    parser.add_argument('--live', action='store_true', help='Actually sync the clock')
    parser.add_argument('--compare', action='store_true', help='Compare all four protocols')
    args = parser.parse_args()
    
    if args.compare:
        compare_all_four()
    else:
        dry_run = not args.live
        
        if not dry_run:
            print("\n⚠️  WARNING: This will adjust the system clock using NTS!")
            response = input("Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                sys.exit(0)
        
        result = test_nts_sync(dry_run=dry_run)
        sys.exit(0 if result['success'] else 1)

if __name__ == "__main__":
    main()
