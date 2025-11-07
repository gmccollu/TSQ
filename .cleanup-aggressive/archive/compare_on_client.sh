#!/bin/bash
# Run complete comparison on the Linux client

cat > /tmp/compare_three.py << 'EOFPYTHON'
#!/usr/bin/env python3
"""
Compare NTP vs TSQ Streams vs TSQ Datagrams
Runs on Linux client
"""
import subprocess
import socket
import struct
import time
import sys
import os

SERVERS = {
    'server1': '14.38.117.100',
    'server2': '14.38.117.200'
}

def query_ntp_raw(server_ip):
    """Query NTP using raw UDP"""
    try:
        ntp_packet = bytearray(48)
        ntp_packet[0] = 0x1B
        
        t1 = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        sock.sendto(ntp_packet, (server_ip, 123))
        data, _ = sock.recvfrom(1024)
        t4 = time.time()
        sock.close()
        
        t2_seconds = struct.unpack('!I', data[32:36])[0]
        t2_fraction = struct.unpack('!I', data[36:40])[0]
        t2 = t2_seconds + (t2_fraction / 2**32)
        
        t3_seconds = struct.unpack('!I', data[40:44])[0]
        t3_fraction = struct.unpack('!I', data[44:48])[0]
        t3 = t3_seconds + (t3_fraction / 2**32)
        
        NTP_EPOCH_OFFSET = 2208988800
        t2 -= NTP_EPOCH_OFFSET
        t3 -= NTP_EPOCH_OFFSET
        
        offset = ((t2 - t1) + (t3 - t4)) / 2
        return offset * 1000
    except Exception as e:
        return None

def query_tsq_streams(server_ip):
    """Query TSQ Streams using Python client"""
    try:
        cmd = f"cd /home/cisco && source ~/tsq-venv/bin/activate && python tsq_client.py {server_ip} --port 443 --insecure --count 3 2>&1"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, executable='/bin/bash')
        
        for line in result.stdout.split('\n'):
            if 'RTT=' in line and 'offset=' in line and server_ip in line:
                rtt = float(line.split('RTT=')[1].split('ms')[0].strip())
                offset = float(line.split('offset=')[1].split('ms')[0].strip())
                return rtt, offset
        return None, None
    except Exception as e:
        return None, None

def query_tsq_datagrams(server_ip):
    """Query TSQ Datagrams using Rust client"""
    try:
        cmd = f"/home/cisco/tsq-client-dg {server_ip} --port 443 --count 3 --insecure 2>&1"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        for line in result.stdout.split('\n'):
            if 'Average' in line and 'RTT=' in line:
                rtt = float(line.split('RTT=')[1].split('ms')[0].strip())
                offset = float(line.split('Offset=')[1].split('ms')[0].strip())
                return rtt, offset
        return None, None
    except Exception as e:
        return None, None

print()
print("="*80)
print(" "*20 + "NTP vs TSQ Streams vs TSQ Datagrams")
print("="*80)
print()

results = []

for name, ip in SERVERS.items():
    print(f"Testing {name} ({ip})...")
    print("-" * 80)
    
    print(f"  Querying NTP...", end='', flush=True)
    ntp_offset = query_ntp_raw(ip)
    if ntp_offset:
        print(f" {ntp_offset:.3f} ms")
    else:
        print(" FAILED")
    
    print(f"  Querying TSQ Streams...", end='', flush=True)
    stream_rtt, stream_offset = query_tsq_streams(ip)
    if stream_rtt:
        print(f" RTT={stream_rtt:.3f} ms, Offset={stream_offset:.3f} ms")
    else:
        print(" FAILED")
    
    print(f"  Querying TSQ Datagrams...", end='', flush=True)
    dg_rtt, dg_offset = query_tsq_datagrams(ip)
    if dg_rtt:
        print(f" RTT={dg_rtt:.3f} ms, Offset={dg_offset:.3f} ms")
    else:
        print(" FAILED")
    
    results.append({
        'server': name,
        'ip': ip,
        'ntp': ntp_offset,
        'stream_rtt': stream_rtt,
        'stream_offset': stream_offset,
        'dg_rtt': dg_rtt,
        'dg_offset': dg_offset
    })
    print()

# Summary
print()
print("="*80)
print(" "*30 + "COMPARISON SUMMARY")
print("="*80)
print()
print(f"{'Server':<15} {'Protocol':<20} {'RTT (ms)':<12} {'Offset (ms)':<15} {'vs NTP':<12}")
print("-" * 80)

for r in results:
    if r['ntp']:
        print(f"{r['server']:<15} {'NTP':<20} {'N/A':<12} {r['ntp']:>12.3f}   {'--':<12}")
    
    if r['stream_rtt'] and r['ntp']:
        diff = r['stream_offset'] - r['ntp']
        print(f"{'':15} {'TSQ Streams':<20} {r['stream_rtt']:>10.3f}   {r['stream_offset']:>12.3f}   {diff:>+10.3f}")
    
    if r['dg_rtt'] and r['ntp']:
        diff = r['dg_offset'] - r['ntp']
        print(f"{'':15} {'TSQ Datagrams':<20} {r['dg_rtt']:>10.3f}   {r['dg_offset']:>12.3f}   {diff:>+10.3f}")
    
    print()

# Performance
print("="*80)
print(" "*25 + "PERFORMANCE COMPARISON")
print("="*80)
print()

stream_rtts = [r['stream_rtt'] for r in results if r['stream_rtt']]
dg_rtts = [r['dg_rtt'] for r in results if r['dg_rtt']]

if stream_rtts and dg_rtts:
    avg_stream = sum(stream_rtts) / len(stream_rtts)
    avg_dg = sum(dg_rtts) / len(dg_rtts)
    
    print(f"Average RTT:")
    print(f"  TSQ Streams:    {avg_stream:.3f} ms")
    print(f"  TSQ Datagrams:  {avg_dg:.3f} ms")
    print(f"  Improvement:    {((avg_stream - avg_dg) / avg_stream * 100):.1f}% faster")
    print()

print(f"Accuracy (vs NTP):")
for r in results:
    if r['ntp'] and r['stream_offset'] and r['dg_offset']:
        stream_diff = abs(r['stream_offset'] - r['ntp'])
        dg_diff = abs(r['dg_offset'] - r['ntp'])
        print(f"  {r['server']}:")
        print(f"    Streams:   {stream_diff:.3f} ms difference")
        print(f"    Datagrams: {dg_diff:.3f} ms difference")

print()
print("="*80)
print()
EOFPYTHON

# Copy script to client and run it
scp /tmp/compare_three.py cisco@172.18.124.206:/tmp/
ssh cisco@172.18.124.206 "python3 /tmp/compare_three.py"
