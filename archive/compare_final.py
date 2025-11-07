#!/usr/bin/env python3
"""
Final working comparison: NTP vs TSQ Streams vs TSQ Datagrams
Uses correct IP addresses for each protocol
"""
import subprocess
import asyncio
import sys
import os
import struct
import time
import socket
import paramiko

sys.path.insert(0, '/Users/garrettmccollum/Desktop/TSQ')
from aioquic.asyncio.client import connect
from aioquic.quic.configuration import QuicConfiguration

# Server mappings
SERVERS = {
    'server1': {
        'external_ip': '172.18.124.203',  # For NTP from Mac
        'internal_ip': '14.38.117.100',   # For TSQ (routable from client)
    },
    'server2': {
        'external_ip': '172.18.124.204',
        'internal_ip': '14.38.117.200',
    }
}

CLIENT = '172.18.124.206'
USER = 'cisco'
PASSWORD = 'cisco123'

def query_ntp_raw(server_ip, port=123, timeout=5):
    """Query NTP server using raw UDP packets"""
    try:
        ntp_packet = bytearray(48)
        ntp_packet[0] = 0x1B
        
        t1 = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(ntp_packet, (server_ip, port))
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
        return offset * 1000  # Convert to ms
        
    except Exception as e:
        print(f"    NTP error: {e}")
        return None

async def query_tsq_streams(server_ip):
    """Query TSQ Streams server"""
    try:
        cfg = QuicConfiguration(is_client=True, alpn_protocols=["tsq/1"])
        cfg.verify_mode = False
        
        async with connect(server_ip, 443, configuration=cfg) as client:
            nonce = os.urandom(16)
            request = struct.pack("!BB", 1, 16) + nonce
            
            reader, writer = await client.create_stream()
            writer.write(request)
            t1 = time.time_ns()
            await writer.drain()
            
            response_data = await asyncio.wait_for(reader.read(100), timeout=3.0)
            t4 = time.time_ns()
            
            if len(response_data) == 0:
                return None, None
            
            offset = 0
            t2_ntp = None
            t3_ntp = None
            
            while offset < len(response_data):
                if offset + 2 > len(response_data):
                    break
                tlv_type = response_data[offset]
                tlv_len = response_data[offset + 1]
                tlv_val = response_data[offset + 2:offset + 2 + tlv_len]
                
                if tlv_type == 2:
                    t2_ntp = tlv_val
                elif tlv_type == 3:
                    t3_ntp = tlv_val
                
                offset += 2 + tlv_len
            
            if not t2_ntp or not t3_ntp:
                return None, None
            
            NTP_EPOCH_OFFSET = 2208988800
            ntp_seconds, ntp_fraction = struct.unpack("!II", t2_ntp)
            t2 = (ntp_seconds - NTP_EPOCH_OFFSET) * 1_000_000_000 + int((ntp_fraction * 1_000_000_000) / 2**32)
            
            ntp_seconds, ntp_fraction = struct.unpack("!II", t3_ntp)
            t3 = (ntp_seconds - NTP_EPOCH_OFFSET) * 1_000_000_000 + int((ntp_fraction * 1_000_000_000) / 2**32)
            
            rtt_ns = (t4 - t1) - (t3 - t2)
            offset_ns = ((t2 - t1) + (t3 - t4)) // 2
            
            writer.close()
            return rtt_ns / 1e6, offset_ns / 1e6
            
    except Exception as e:
        print(f"    TSQ Streams error: {e}")
        return None, None

def query_tsq_datagrams(server_ip):
    """Query TSQ Datagrams via SSH to client"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=CLIENT, username=USER, password=PASSWORD, timeout=10)
        
        cmd = f"/home/cisco/tsq-client-dg {server_ip} --port 443 --count 3 --insecure 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        output = stdout.read().decode()
        ssh.close()
        
        for line in output.split('\n'):
            if 'Average' in line and 'RTT=' in line:
                rtt_str = line.split('RTT=')[1].split('ms')[0].strip()
                offset_str = line.split('Offset=')[1].split('ms')[0].strip()
                return float(rtt_str), float(offset_str)
        
        return None, None
        
    except Exception as e:
        print(f"    TSQ Datagrams error: {e}")
        return None, None

async def main():
    print()
    print("="*80)
    print(" "*20 + "NTP vs TSQ Streams vs TSQ Datagrams")
    print("="*80)
    print()
    
    results = []
    
    for name, ips in SERVERS.items():
        print(f"Testing {name}...")
        print("-" * 80)
        
        # Query NTP (use external IP from Mac)
        print(f"  Querying NTP ({ips['external_ip']})...", end='', flush=True)
        ntp_offset = query_ntp_raw(ips['external_ip'])
        if ntp_offset:
            print(f" {ntp_offset:.3f} ms")
        else:
            print(" FAILED")
        
        # Query TSQ Streams (use internal IP)
        print(f"  Querying TSQ Streams ({ips['internal_ip']})...", end='', flush=True)
        stream_rtt, stream_offset = await query_tsq_streams(ips['internal_ip'])
        if stream_rtt:
            print(f" RTT={stream_rtt:.3f} ms, Offset={stream_offset:.3f} ms")
        else:
            print(" FAILED")
        
        # Query TSQ Datagrams (use internal IP)
        print(f"  Querying TSQ Datagrams ({ips['internal_ip']})...", end='', flush=True)
        dg_rtt, dg_offset = query_tsq_datagrams(ips['internal_ip'])
        if dg_rtt:
            print(f" RTT={dg_rtt:.3f} ms, Offset={dg_offset:.3f} ms")
        else:
            print(" FAILED")
        
        results.append({
            'server': name,
            'external_ip': ips['external_ip'],
            'internal_ip': ips['internal_ip'],
            'ntp': ntp_offset,
            'stream_rtt': stream_rtt,
            'stream_offset': stream_offset,
            'dg_rtt': dg_rtt,
            'dg_offset': dg_offset
        })
        
        print()
    
    # Print comparison table
    print()
    print("="*80)
    print(" "*30 + "COMPARISON SUMMARY")
    print("="*80)
    print()
    print(f"{'Server':<15} {'Protocol':<20} {'RTT (ms)':<12} {'Offset (ms)':<15} {'vs NTP':<12}")
    print("-" * 80)
    
    for r in results:
        server_label = f"{r['server']}"
        
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
    
    stream_rtts = [r['stream_rtt'] for r in results if r['stream_rtt']]
    dg_rtts = [r['dg_rtt'] for r in results if r['dg_rtt']]
    
    if stream_rtts and dg_rtts:
        avg_stream_rtt = sum(stream_rtts) / len(stream_rtts)
        avg_dg_rtt = sum(dg_rtts) / len(dg_rtts)
        
        print(f"Average RTT:")
        print(f"  TSQ Streams:    {avg_stream_rtt:.3f} ms")
        print(f"  TSQ Datagrams:  {avg_dg_rtt:.3f} ms")
        improvement = ((avg_stream_rtt - avg_dg_rtt) / avg_stream_rtt * 100)
        print(f"  Improvement:    {improvement:.1f}% faster")
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

if __name__ == "__main__":
    asyncio.run(main())
