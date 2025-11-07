#!/usr/bin/env python3
"""
Compare NTP vs TSQ measurements to the same servers
"""
import subprocess
import asyncio
import sys
import os
import struct
import time
import socket

# Import TSQ client functions
sys.path.insert(0, '/Users/garrettmccollum/Desktop/TSQ')
from tsq_client import one_probe, tlv_pack, parse_tlvs, ntp_to_ns, compute_metrics

from aioquic.asyncio.client import connect
from aioquic.quic.configuration import QuicConfiguration

SERVERS = {
    '14.38.117.100': 'server1',
    '14.38.117.200': 'server2'
}

def query_ntp_raw(server_ip, port=123, timeout=5):
    """Query NTP server using raw UDP packets"""
    try:
        # NTP packet format (48 bytes)
        # LI (2 bits) = 0, VN (3 bits) = 3, Mode (3 bits) = 3 (client)
        # First byte: 00 011 011 = 0x1B
        ntp_packet = bytearray(48)
        ntp_packet[0] = 0x1B  # LI=0, VN=3, Mode=3
        
        # Record client transmit time (T1)
        t1 = time.time()
        
        # Send NTP request
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(ntp_packet, (server_ip, port))
        
        # Receive response
        data, _ = sock.recvfrom(1024)
        t4 = time.time()  # Record client receive time (T4)
        sock.close()
        
        # Parse NTP response
        # Receive timestamp is at bytes 32-39 (T3 - server transmit)
        # Originate timestamp is at bytes 24-31 (T1 echo)
        # Reference timestamp is at bytes 16-23
        
        # Extract T2 (server receive) - bytes 32-39
        t2_seconds = struct.unpack('!I', data[32:36])[0]
        t2_fraction = struct.unpack('!I', data[36:40])[0]
        t2 = t2_seconds + (t2_fraction / 2**32)
        
        # Extract T3 (server transmit) - bytes 40-47
        t3_seconds = struct.unpack('!I', data[40:44])[0]
        t3_fraction = struct.unpack('!I', data[44:48])[0]
        t3 = t3_seconds + (t3_fraction / 2**32)
        
        # Convert from NTP epoch (1900) to Unix epoch (1970)
        NTP_EPOCH_OFFSET = 2208988800
        t2 -= NTP_EPOCH_OFFSET
        t3 -= NTP_EPOCH_OFFSET
        
        # Calculate offset using NTP algorithm
        # offset = ((T2 - T1) + (T3 - T4)) / 2
        offset = ((t2 - t1) + (t3 - t4)) / 2
        offset_ms = offset * 1000
        
        return offset_ms
        
    except Exception as e:
        print(f"  Raw NTP query failed: {e}")
        return None

def query_ntp(server_ip):
    """Query NTP server using chronyc, ntpdate, or raw UDP"""
    # Try chronyc first (more common on modern systems)
    try:
        # Use chronyc to query a specific server
        result = subprocess.run(
            ['chronyc', '-c', 'sources'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Parse CSV output: IP,Mode,State,Name,Stratum,Poll,Reach,LastRx,Last sample
        # Last sample format: offset[+/-value] frequency skew
        for line in result.stdout.split('\n'):
            if server_ip in line:
                parts = line.split(',')
                if len(parts) >= 9:
                    # Parse last sample field
                    last_sample = parts[8]
                    # Extract offset value (in seconds)
                    if '[' in last_sample and ']' in last_sample:
                        offset_str = last_sample.split('[')[1].split(']')[0]
                        offset_ms = float(offset_str) * 1000  # Convert to ms
                        return offset_ms
    except FileNotFoundError:
        pass  # chronyc not available, try ntpdate
    except Exception as e:
        print(f"  chronyc failed: {e}")
    
    # Try ntpdate as fallback
    try:
        result = subprocess.run(
            ['ntpdate', '-q', server_ip],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Parse output: "server 14.38.117.100, stratum 3, offset -0.784523, delay 0.03045"
        for line in result.stdout.split('\n'):
            if 'offset' in line and server_ip in line:
                parts = line.split(',')
                for part in parts:
                    if 'offset' in part:
                        offset_str = part.split()[1]
                        offset_ms = float(offset_str) * 1000  # Convert to ms
                        return offset_ms
    except FileNotFoundError:
        pass  # ntpdate not available, use raw NTP
    except Exception as e:
        print(f"  ntpdate failed: {e}")
    
    # Final fallback: raw NTP query
    print(f"  Using raw NTP query...")
    return query_ntp_raw(server_ip)

async def query_tsq(server_ip):
    """Query TSQ server"""
    try:
        cfg = QuicConfiguration(is_client=True, alpn_protocols=["tsq/1"])
        cfg.verify_mode = False
        
        async with connect(server_ip, 443, configuration=cfg) as client:
            # Generate nonce and build request
            nonce = os.urandom(16)
            request = struct.pack("!BB", 1, 16) + nonce  # TLV: Type 1, Length 16
            
            reader, writer = await client.create_stream()
            
            # Send request and record T1 right before drain
            writer.write(request)
            t1 = time.time_ns()
            await writer.drain()
            
            # Read response and record T4 immediately
            response_data = await asyncio.wait_for(reader.read(100), timeout=3.0)
            t4 = time.time_ns()
            
            if len(response_data) == 0:
                return None
            
            # Parse response
            offset = 0
            nonce_echo = None
            t2_ntp = None
            t3_ntp = None
            
            while offset < len(response_data):
                if offset + 2 > len(response_data):
                    break
                tlv_type = response_data[offset]
                tlv_len = response_data[offset + 1]
                tlv_val = response_data[offset + 2:offset + 2 + tlv_len]
                
                if tlv_type == 1:
                    nonce_echo = tlv_val
                elif tlv_type == 2:
                    t2_ntp = tlv_val
                elif tlv_type == 3:
                    t3_ntp = tlv_val
                
                offset += 2 + tlv_len
            
            if not t2_ntp or not t3_ntp:
                return None
            
            # Convert NTP to nanoseconds
            NTP_EPOCH_OFFSET = 2208988800
            ntp_seconds, ntp_fraction = struct.unpack("!II", t2_ntp)
            t2 = (ntp_seconds - NTP_EPOCH_OFFSET) * 1_000_000_000 + int((ntp_fraction * 1_000_000_000) / 2**32)
            
            ntp_seconds, ntp_fraction = struct.unpack("!II", t3_ntp)
            t3 = (ntp_seconds - NTP_EPOCH_OFFSET) * 1_000_000_000 + int((ntp_fraction * 1_000_000_000) / 2**32)
            
            # Calculate offset
            rtt_ns = (t4 - t1) - (t3 - t2)
            offset_ns = ((t2 - t1) + (t3 - t4)) // 2
            
            writer.close()
            
            return offset_ns / 1e6  # Convert to ms
            
    except Exception as e:
        print(f"TSQ query failed: {e}")
        return None

async def main():
    print("="*60)
    print("NTP vs TSQ Comparison")
    print("="*60)
    print()
    
    results = []
    
    for server_ip, server_name in SERVERS.items():
        print(f"Testing {server_name} ({server_ip})...")
        
        # Query NTP
        print(f"  Querying via NTP...")
        ntp_offset = query_ntp(server_ip)
        
        # Query TSQ
        print(f"  Querying via TSQ...")
        tsq_offset = await query_tsq(server_ip)
        
        results.append({
            'server': server_name,
            'ip': server_ip,
            'ntp': ntp_offset,
            'tsq': tsq_offset
        })
        
        print()
    
    # Print comparison table
    print("="*60)
    print("Results Summary")
    print("="*60)
    print()
    print(f"{'Server':<15} {'NTP Offset (ms)':>18} {'TSQ Offset (ms)':>18} {'Difference':>12}")
    print("-"*70)
    
    for r in results:
        if r['ntp'] is not None and r['tsq'] is not None:
            diff = abs(r['ntp'] - r['tsq'])
            print(f"{r['server']:<15} {r['ntp']:>18.3f} {r['tsq']:>18.3f} {diff:>12.3f}")
        else:
            ntp_str = f"{r['ntp']:.3f}" if r['ntp'] is not None else "FAILED"
            tsq_str = f"{r['tsq']:.3f}" if r['tsq'] is not None else "FAILED"
            print(f"{r['server']:<15} {ntp_str:>18} {tsq_str:>18} {'N/A':>12}")
    
    print("-"*70)
    print()
    print("Note: Small differences (<50ms) are expected due to:")
    print("  - Different measurement times")
    print("  - Network jitter")
    print("  - Different protocol overhead (UDP vs QUIC)")

if __name__ == "__main__":
    asyncio.run(main())
