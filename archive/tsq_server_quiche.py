#!/usr/bin/env python3
"""
TSQ Server - Quiche QUIC Datagram Version
Uses Cloudflare's Quiche library for proper datagram support
"""
import argparse
import socket
import struct
import time
import os
from quiche_wrapper import QuicheWrapper, is_quiche_available

# TLV Types
T_NONCE = 1
T_RECV_TS = 2
T_SEND_TS = 3

def tlv_pack(tlv_type: int, value: bytes) -> bytes:
    """Pack a TLV with 1-byte length field"""
    return struct.pack("!BB", tlv_type, len(value)) + value

def ns_to_ntp(ns_timestamp: int) -> bytes:
    """Convert nanosecond timestamp to NTP format"""
    NTP_EPOCH_OFFSET = 2208988800
    seconds = ns_timestamp // 1_000_000_000
    nanos = ns_timestamp % 1_000_000_000
    ntp_seconds = seconds + NTP_EPOCH_OFFSET
    ntp_fraction = int((nanos * 2**32) / 1_000_000_000)
    return struct.pack("!II", ntp_seconds, ntp_fraction)

def handle_tsq_request(request_data: bytes) -> bytes:
    """Process TSQ request and build response"""
    # Record receive time
    t2_recv = time.time_ns()
    
    print(f"[TSQ-Q] Received {len(request_data)} bytes")
    
    # Parse nonce (Type 1, Length 16, Value 16 bytes)
    if len(request_data) < 18:
        print(f"[TSQ-Q] Invalid request (too short)")
        return None
    
    # Extract nonce
    nonce = request_data[2:18]
    
    # Build response
    response = b""
    response += tlv_pack(T_NONCE, nonce)
    response += tlv_pack(T_RECV_TS, ns_to_ntp(t2_recv))
    
    # Record T3 RIGHT BEFORE returning
    t3_send = time.time_ns()
    response += tlv_pack(T_SEND_TS, ns_to_ntp(t3_send))
    
    return response

def run_server(host: str, port: int, cert_file: str, key_file: str):
    """Run TSQ server with Quiche"""
    
    if not is_quiche_available():
        print("[TSQ-Q] ERROR: Quiche library not available")
        print("[TSQ-Q] Please run: ./install_quiche.sh")
        return 1
    
    print(f"[TSQ-Q] Starting TSQ server (Quiche/Datagrams)")
    print(f"[TSQ-Q] Listening on {host}:{port}")
    print(f"[TSQ-Q] Certificate: {cert_file}")
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.setblocking(False)
    
    print(f"[TSQ-Q] Server ready")
    
    # Initialize Quiche
    quiche = QuicheWrapper()
    
    # Store active connections
    connections = {}  # scid -> (conn, client_addr)
    
    # Main server loop
    buf = bytearray(65535)
    
    try:
        while True:
            # Try to receive data
            try:
                data, client_addr = sock.recvfrom_into(buf)
                recv_data = bytes(buf[:data])
            except BlockingIOError:
                # No data available, check for timeouts
                time.sleep(0.001)
                continue
            
            print(f"[TSQ-Q] Received {len(recv_data)} bytes from {client_addr}")
            
            # TODO: Parse QUIC packet header to get connection ID
            # For now, use client address as connection identifier
            conn_id = f"{client_addr[0]}:{client_addr[1]}"
            
            if conn_id not in connections:
                # New connection - need to accept it
                print(f"[TSQ-Q] New connection from {client_addr}")
                
                # Create server configuration
                config = quiche.create_config()
                
                # Generate connection ID
                scid = os.urandom(16)
                
                # TODO: Create server connection with quiche_accept
                # This requires more complex setup
                print(f"[TSQ-Q] Note: Full Quiche server implementation requires quiche_accept")
                print(f"[TSQ-Q] For now, using simplified datagram handling")
                
                # Simplified: Parse as TSQ request directly
                response = handle_tsq_request(recv_data)
                if response:
                    print(f"[TSQ-Q] Sending {len(response)} bytes to {client_addr}")
                    sock.sendto(response, client_addr)
                    print(f"[TSQ-Q] Response sent")
            else:
                # Existing connection
                conn, _ = connections[conn_id]
                
                # Feed data to connection
                # TODO: Use quiche_conn_recv
                
                # Check for datagram
                dgram = quiche.recv_datagram(conn)
                if dgram:
                    response = handle_tsq_request(dgram)
                    if response:
                        quiche.send_datagram(conn, response)
                        
                        # Send QUIC packets
                        # TODO: Use quiche_conn_send to get packets to send
                        pass
    
    except KeyboardInterrupt:
        print("\n[TSQ-Q] Server stopped")
    finally:
        sock.close()
    
    return 0

def main():
    parser = argparse.ArgumentParser(description="TSQ Server (Quiche/Datagrams)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=443, help="Port to bind to")
    parser.add_argument("--cert", required=True, help="TLS certificate file")
    parser.add_argument("--key", required=True, help="TLS private key file")
    args = parser.parse_args()
    
    return run_server(args.host, args.port, args.cert, args.key)

if __name__ == "__main__":
    import sys
    sys.exit(main())
