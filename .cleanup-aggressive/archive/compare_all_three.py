#!/usr/bin/env python3
"""
Compare NTP vs TSQ Streams vs TSQ Datagrams
"""
import subprocess
import sys
import time
import paramiko

SERVERS = {
    'server1': {'host': '172.18.124.203', 'ip': '14.38.117.100'},
    'server2': {'host': '172.18.124.204', 'ip': '14.38.117.200'}
}
CLIENT = '172.18.124.206'
USER = 'cisco'
PASSWORD = 'cisco123'

def run_ssh_command(host, command, timeout=30):
    """Run command via SSH and return output"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=USER, password=PASSWORD, timeout=10)
        
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        output = stdout.read().decode()
        error = stderr.read().decode()
        ssh.close()
        
        if error and not output:
            print(f"\n    [DEBUG] Error: {error[:200]}")
        
        return output
    except Exception as e:
        print(f"\n    [DEBUG] Exception: {e}")
        return ""

def query_ntp(server_ip):
    """Query NTP offset using chronyc on client"""
    cmd = f"chronyc -h {server_ip} tracking 2>/dev/null | grep 'System time' | awk '{{print $4, $5}}'"
    output = run_ssh_command(CLIENT, cmd)
    
    if not output.strip():
        # Fallback to ntpdate
        cmd = f"sudo ntpdate -q {server_ip} 2>/dev/null | grep offset | tail -1 | awk '{{print $10}}'"
        output = run_ssh_command(CLIENT, cmd)
    
    try:
        parts = output.strip().split()
        if len(parts) == 2:
            value = float(parts[0])
            unit = parts[1]
            if 'seconds' in unit:
                return value * 1000  # Convert to ms
            return value
        else:
            return float(output.strip()) * 1000  # Assume seconds, convert to ms
    except:
        return None

def query_tsq_streams(server_ip):
    """Query TSQ streams version"""
    cmd = f"cd /home/cisco && source ~/tsq-venv/bin/activate && python tsq_client.py {server_ip} --port 443 --insecure --count 3 2>/dev/null | grep Average"
    output = run_ssh_command(CLIENT, cmd)
    
    try:
        # Parse: [TSQ] Average: RTT=2.123 ms, offset=1289.456 ms
        for line in output.split('\n'):
            if 'Average' in line and 'RTT=' in line:
                parts = line.split('RTT=')[1].split('ms')[0].strip()
                rtt = float(parts)
                parts = line.split('offset=')[1].split('ms')[0].strip()
                offset = float(parts)
                return rtt, offset
    except:
        pass
    return None, None

def query_tsq_datagrams(server_ip):
    """Query TSQ datagrams version"""
    cmd = f"/home/cisco/tsq-client-dg {server_ip} --port 443 --count 3 --insecure 2>/dev/null | grep Average"
    output = run_ssh_command(CLIENT, cmd)
    
    try:
        # Parse: [TSQ-Q] Average: RTT=1.234 ms, Offset=1289.456 ms
        for line in output.split('\n'):
            if 'Average' in line and 'RTT=' in line:
                parts = line.split('RTT=')[1].split('ms')[0].strip()
                rtt = float(parts)
                parts = line.split('Offset=')[1].split('ms')[0].strip()
                offset = float(parts)
                return rtt, offset
    except:
        pass
    return None, None

def main():
    print()
    print("="*80)
    print(" "*20 + "NTP vs TSQ Streams vs TSQ Datagrams")
    print("="*80)
    print()
    
    results = {}
    
    for name, info in SERVERS.items():
        print(f"Testing {name} ({info['ip']})...")
        print("-" * 80)
        
        results[name] = {}
        
        # NTP
        print("  Querying NTP...", end='', flush=True)
        ntp_offset = query_ntp(info['ip'])
        results[name]['ntp'] = ntp_offset
        if ntp_offset:
            print(f" {ntp_offset:.3f} ms")
        else:
            print(" FAILED")
        
        # TSQ Streams
        print("  Querying TSQ Streams...", end='', flush=True)
        stream_rtt, stream_offset = query_tsq_streams(info['ip'])
        results[name]['stream_rtt'] = stream_rtt
        results[name]['stream_offset'] = stream_offset
        if stream_rtt:
            print(f" RTT={stream_rtt:.3f} ms, Offset={stream_offset:.3f} ms")
        else:
            print(" FAILED")
        
        # TSQ Datagrams
        print("  Querying TSQ Datagrams...", end='', flush=True)
        dg_rtt, dg_offset = query_tsq_datagrams(info['ip'])
        results[name]['dg_rtt'] = dg_rtt
        results[name]['dg_offset'] = dg_offset
        if dg_rtt:
            print(f" RTT={dg_rtt:.3f} ms, Offset={dg_offset:.3f} ms")
        else:
            print(" FAILED")
        
        print()
    
    # Summary table
    print()
    print("="*80)
    print(" "*30 + "COMPARISON SUMMARY")
    print("="*80)
    print()
    
    # Header
    print(f"{'Server':<15} {'Protocol':<20} {'RTT (ms)':<12} {'Offset (ms)':<15} {'vs NTP':<12}")
    print("-" * 80)
    
    for name, info in SERVERS.items():
        r = results[name]
        server_label = f"{name} ({SERVERS[name]['ip']})"
        
        # NTP
        if r['ntp']:
            print(f"{server_label:<15} {'NTP':<20} {'N/A':<12} {r['ntp']:>12.3f}   {'--':<12}")
        
        # TSQ Streams
        if r['stream_rtt'] and r['ntp']:
            diff = r['stream_offset'] - r['ntp']
            print(f"{'':15} {'TSQ Streams':<20} {r['stream_rtt']:>10.3f}   {r['stream_offset']:>12.3f}   {diff:>+10.3f}")
        
        # TSQ Datagrams
        if r['dg_rtt'] and r['ntp']:
            diff = r['dg_offset'] - r['ntp']
            print(f"{'':15} {'TSQ Datagrams':<20} {r['dg_rtt']:>10.3f}   {r['dg_offset']:>12.3f}   {diff:>+10.3f}")
        
        print()
    
    # Performance comparison
    print("="*80)
    print(" "*25 + "PERFORMANCE COMPARISON")
    print("="*80)
    print()
    
    stream_rtts = [r['stream_rtt'] for r in results.values() if r['stream_rtt']]
    dg_rtts = [r['dg_rtt'] for r in results.values() if r['dg_rtt']]
    
    if stream_rtts and dg_rtts:
        avg_stream_rtt = sum(stream_rtts) / len(stream_rtts)
        avg_dg_rtt = sum(dg_rtts) / len(dg_rtts)
        
        print(f"Average RTT:")
        print(f"  TSQ Streams:    {avg_stream_rtt:.3f} ms")
        print(f"  TSQ Datagrams:  {avg_dg_rtt:.3f} ms")
        print(f"  Improvement:    {((avg_stream_rtt - avg_dg_rtt) / avg_stream_rtt * 100):.1f}% faster")
        print()
    else:
        print("No RTT data available for comparison")
        print()
    
    print(f"Accuracy (vs NTP):")
    for name, r in results.items():
        if r['ntp'] and r['stream_offset'] and r['dg_offset']:
            stream_diff = abs(r['stream_offset'] - r['ntp'])
            dg_diff = abs(r['dg_offset'] - r['ntp'])
            print(f"  {name}:")
            print(f"    Streams:   {stream_diff:.3f} ms difference")
            print(f"    Datagrams: {dg_diff:.3f} ms difference")
    
    print()
    print("="*80)
    print()

if __name__ == "__main__":
    main()
