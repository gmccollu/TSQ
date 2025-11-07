#!/usr/bin/env python3
"""
Validate NTP vs TSQ accuracy by comparing against public NTP servers
"""
import socket
import struct
import time
import statistics

PUBLIC_NTP_SERVERS = [
    'time.google.com',
    'time.cloudflare.com',
    'pool.ntp.org',
    'time.nist.gov'
]

def query_ntp_server(server, timeout=5):
    """Query an NTP server and return offset in milliseconds"""
    try:
        # Create NTP request packet
        ntp_packet = bytearray(48)
        ntp_packet[0] = 0x1B  # LI=0, VN=3, Mode=3
        
        # Record client transmit time
        t1 = time.time()
        
        # Send request
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(ntp_packet, (server, 123))
        
        # Receive response
        data, _ = sock.recvfrom(1024)
        t4 = time.time()
        sock.close()
        
        # Parse timestamps from response
        # T2 (server receive) at bytes 32-39
        t2_seconds = struct.unpack('!I', data[32:36])[0]
        t2_fraction = struct.unpack('!I', data[36:40])[0]
        t2 = t2_seconds + (t2_fraction / 2**32)
        
        # T3 (server transmit) at bytes 40-47
        t3_seconds = struct.unpack('!I', data[40:44])[0]
        t3_fraction = struct.unpack('!I', data[44:48])[0]
        t3 = t3_seconds + (t3_fraction / 2**32)
        
        # Convert from NTP epoch to Unix epoch
        NTP_EPOCH_OFFSET = 2208988800
        t2 -= NTP_EPOCH_OFFSET
        t3 -= NTP_EPOCH_OFFSET
        
        # Calculate offset: ((T2 - T1) + (T3 - T4)) / 2
        offset = ((t2 - t1) + (t3 - t4)) / 2
        offset_ms = offset * 1000
        
        # Calculate RTT
        rtt = (t4 - t1) - (t3 - t2)
        rtt_ms = rtt * 1000
        
        return offset_ms, rtt_ms
        
    except Exception as e:
        print(f"  Error querying {server}: {e}")
        return None, None

def main():
    print("="*70)
    print("ACCURACY VALIDATION: Comparing against Public NTP Servers")
    print("="*70)
    print("\nQuerying public NTP servers to establish ground truth...")
    print()
    
    public_offsets = []
    
    for server in PUBLIC_NTP_SERVERS:
        print(f"Querying {server}...")
        offset, rtt = query_ntp_server(server)
        if offset is not None:
            print(f"  Offset: {offset:8.3f} ms  (RTT: {rtt:6.2f} ms)")
            public_offsets.append(offset)
        else:
            print(f"  Failed")
    
    if len(public_offsets) < 2:
        print("\n✗ Not enough public NTP servers responded")
        return
    
    # Calculate statistics
    avg_offset = statistics.mean(public_offsets)
    median_offset = statistics.median(public_offsets)
    stdev = statistics.stdev(public_offsets) if len(public_offsets) > 1 else 0
    
    print("\n" + "="*70)
    print("PUBLIC NTP CONSENSUS (Ground Truth)")
    print("="*70)
    print(f"Average offset:  {avg_offset:8.3f} ms")
    print(f"Median offset:   {median_offset:8.3f} ms")
    print(f"Std deviation:   {stdev:8.3f} ms")
    print(f"Samples:         {len(public_offsets)}")
    
    # Compare with your measurements
    print("\n" + "="*70)
    print("COMPARISON WITH YOUR SERVERS")
    print("="*70)
    
    # These are the values from your last test
    ntp_server1 = 1287.608
    ntp_server2 = 1261.322
    tsq_server1 = 787.437
    tsq_server2 = 761.260
    
    avg_ntp = (ntp_server1 + ntp_server2) / 2
    avg_tsq = (tsq_server1 + tsq_server2) / 2
    
    print(f"\nYour NTP measurement (avg):  {avg_ntp:8.3f} ms")
    print(f"Your TSQ measurement (avg):  {avg_tsq:8.3f} ms")
    print(f"Public NTP consensus:        {median_offset:8.3f} ms")
    
    # Calculate errors
    ntp_error = abs(avg_ntp - median_offset)
    tsq_error = abs(avg_tsq - median_offset)
    
    print("\n" + "="*70)
    print("ACCURACY ANALYSIS")
    print("="*70)
    print(f"NTP error from ground truth: {ntp_error:8.3f} ms")
    print(f"TSQ error from ground truth: {tsq_error:8.3f} ms")
    
    if tsq_error < ntp_error:
        print(f"\n✓ TSQ is MORE ACCURATE by {ntp_error - tsq_error:.3f} ms")
        print(f"  TSQ offset is closer to public NTP consensus")
    elif ntp_error < tsq_error:
        print(f"\n✓ NTP is MORE ACCURATE by {tsq_error - ntp_error:.3f} ms")
        print(f"  NTP offset is closer to public NTP consensus")
    else:
        print(f"\n= Both are equally accurate")
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    
    # Determine which is better
    if tsq_error < ntp_error:
        print("TSQ appears to be measuring more accurately.")
        print("\nPossible reasons:")
        print("- QUIC's connection-oriented nature provides better timing")
        print("- TLS handshake in QUIC may provide more stable RTT measurement")
        print("- Your NTP servers may have additional latency in NTP processing")
    elif ntp_error < tsq_error:
        print("NTP appears to be measuring more accurately.")
        print("\nPossible reasons:")
        print("- NTP is optimized specifically for time synchronization")
        print("- Lighter protocol overhead than QUIC")
        print("- Your TSQ implementation may have additional processing delay")
    
    print(f"\nNote: The ~500ms systematic difference suggests there may be")
    print(f"a constant offset in one of the implementations or server clocks.")

if __name__ == "__main__":
    main()
