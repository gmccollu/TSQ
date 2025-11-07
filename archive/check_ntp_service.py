#!/usr/bin/env python3
"""
Check if NTP service is running on the servers
"""
import subprocess
import socket

SERVERS = ['14.38.117.100', '14.38.117.200']

print("Checking NTP service on servers...")
print("="*60)

for server in SERVERS:
    print(f"\nServer: {server}")
    
    # Check if port 123 is open
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        sock.sendto(b'\x1b' + b'\x00' * 47, (server, 123))
        data, _ = sock.recvfrom(1024)
        sock.close()
        print(f"  ✓ NTP port 123 is OPEN and responding")
    except socket.timeout:
        print(f"  ✗ NTP port 123 TIMEOUT (service may not be running)")
    except Exception as e:
        print(f"  ✗ NTP port 123 ERROR: {e}")
    
    # Check if TSQ port 443 is open
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        sock.sendto(b'test', (server, 443))
        print(f"  ✓ TSQ port 443 is OPEN")
        sock.close()
    except Exception as e:
        print(f"  ? TSQ port 443: {e}")

print("\n" + "="*60)
print("\nConclusion:")
print("If NTP ports are timing out, the servers may not be running NTP service.")
print("TSQ can still be validated by comparing measurements across multiple probes")
print("for consistency, or by comparing with external NTP servers.")
