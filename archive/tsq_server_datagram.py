#!/usr/bin/env python3
"""
TSQ Server - QUIC Datagram Version
Uses unreliable QUIC datagrams instead of streams for lower latency
"""
import argparse
import asyncio
import struct
import time
from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import DatagramFrameReceived, QuicEvent

# TLV Types (from draft-mccollum-ntp-tsq-01)
T_NONCE = 1      # Nonce (16 bytes)
T_RECV_TS = 2    # Receive Timestamp (8 bytes, NTP format)
T_SEND_TS = 3    # Send Timestamp (8 bytes, NTP format)

def tlv_pack(tlv_type: int, value: bytes) -> bytes:
    """Pack a TLV with 1-byte length field"""
    return struct.pack("!BB", tlv_type, len(value)) + value

class TSQDatagramProtocol(QuicConnectionProtocol):
    """QUIC protocol handler for datagram-based TSQ"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def quic_event_received(self, event: QuicEvent):
        """Handle QUIC events"""
        if isinstance(event, DatagramFrameReceived):
            self.handle_datagram(event.data)
    
    def handle_datagram(self, request_data: bytes):
        """Handle a TSQ request datagram"""
        # Record receive time immediately
        t2_recv = time.time_ns()
        
        print(f"[TSQ-DG] Received {len(request_data)} bytes")
        
        # Parse nonce (Type 1, Length 16, Value 16 bytes)
        if len(request_data) < 18:
            print(f"[TSQ-DG] Invalid request (too short)")
            return
        
        # Extract nonce
        nonce = request_data[2:18]
        
        # Convert nanosecond timestamps to NTP format
        NTP_EPOCH_OFFSET = 2208988800
        
        def ns_to_ntp(ns_timestamp):
            seconds = ns_timestamp // 1_000_000_000
            nanos = ns_timestamp % 1_000_000_000
            ntp_seconds = seconds + NTP_EPOCH_OFFSET
            ntp_fraction = int((nanos * 2**32) / 1_000_000_000)
            return struct.pack("!II", ntp_seconds, ntp_fraction)
        
        # Convert T2 (receive timestamp)
        ntp_t2 = ns_to_ntp(t2_recv)
        
        # Build response (without T3 yet)
        response = b""
        response += tlv_pack(T_NONCE, nonce)
        response += tlv_pack(T_RECV_TS, ntp_t2)
        
        # Record T3 RIGHT BEFORE sending
        t3_send = time.time_ns()
        ntp_t3 = ns_to_ntp(t3_send)
        response += tlv_pack(T_SEND_TS, ntp_t3)
        
        # Send response datagram
        print(f"[TSQ-DG] Sending {len(response)} bytes")
        self._quic.send_datagram_frame(response)
        self.transmit()  # Trigger transmission
        print(f"[TSQ-DG] Response sent")

async def main():
    parser = argparse.ArgumentParser(description="TSQ Server (QUIC Datagram)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=443, help="Port to bind to")
    parser.add_argument("--cert", required=True, help="TLS certificate file")
    parser.add_argument("--key", required=True, help="TLS private key file")
    args = parser.parse_args()
    
    # Configure QUIC
    configuration = QuicConfiguration(
        alpn_protocols=["tsq/1"],
        is_client=False,
        max_datagram_frame_size=65536,  # Enable datagrams
    )
    
    # Load TLS certificate
    configuration.load_cert_chain(args.cert, args.key)
    
    print(f"[TSQ-DG] Starting server on {args.host}:{args.port}")
    print(f"[TSQ-DG] Using QUIC datagrams (unreliable)")
    print(f"[TSQ-DG] Certificate: {args.cert}")
    
    # Start server
    server = await serve(
        args.host,
        args.port,
        configuration=configuration,
        create_protocol=TSQDatagramProtocol,
    )
    
    print(f"[TSQ-DG] Server ready")
    
    # Run forever
    await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[TSQ-DG] Server stopped")
