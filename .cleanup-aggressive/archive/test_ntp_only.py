#!/usr/bin/env python3
"""Test just NTP query"""
import socket
import struct
import time

def query_ntp_raw(server_ip, port=123, timeout=5):
    """Query NTP server using raw UDP packets"""
    try:
        print(f"  Sending NTP request to {server_ip}...")
        ntp_packet = bytearray(48)
        ntp_packet[0] = 0x1B
        
        t1 = time.time()
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(ntp_packet, (server_ip, port))
        print(f"  Waiting for response...")
        
        data, _ = sock.recvfrom(1024)
        t4 = time.time()
        sock.close()
        
        print(f"  Received {len(data)} bytes")
        
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
        offset_ms = offset * 1000
        
        return offset_ms
        
    except socket.timeout:
        print(f"  TIMEOUT after {timeout} seconds")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

print("Testing NTP queries...\n")

for server in ['14.38.117.100', '14.38.117.200']:
    print(f"Server: {server}")
    offset = query_ntp_raw(server)
    if offset:
        print(f"  ✓ Offset: {offset:.3f} ms")
    else:
        print(f"  ✗ Failed")
    print()
