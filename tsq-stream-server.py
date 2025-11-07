#!/usr/bin/env python3
"""TSQ Server - Version 2024-11-05-12:18"""
import asyncio
import struct
import time
import argparse
import sys
from datetime import datetime, timezone
from aioquic.asyncio import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent, StreamDataReceived
import socket

# Force unbuffered output for systemd
sys.stdout.reconfigure(line_buffering=True)

VERSION = "2024-11-05-12:18"
ALPN = ["tsq/1"]

# TLV: 1 byte Type, 1 byte Length (per draft-mccollum-ntp-tsq-01), then Value
# Types:
#   1 = Nonce (16 bytes)
#   2 = Receive Timestamp (8 bytes, NTP format)
#   3 = Send Timestamp (8 bytes, NTP format)

T_NONCE = 1
T_RECV_TS = 2
T_SEND_TS = 3

def tlv_unpack(data: bytes):
    """Unpack a single TLV from data. Returns (type, value, bytes_consumed)."""
    if len(data) < 2:
        raise ValueError("TLV too short")
    t = data[0]
    l = data[1]
    if len(data) < 2 + l:
        raise ValueError("TLV length mismatch")
    v = data[2:2+l]
    return t, v, 2 + l

def tlv_pack(t: int, v: bytes) -> bytes:
    """Pack a TLV with 1-byte length field."""
    if len(v) > 255:
        raise ValueError("TLV value too long (max 255 bytes)")
    return struct.pack("!BB", t, len(v)) + v

def parse_tlvs(data: bytes) -> list:
    """Parse all TLVs from data. Returns list of (type, value) tuples."""
    tlvs = []
    offset = 0
    while offset < len(data):
        t, v, consumed = tlv_unpack(data[offset:])
        tlvs.append((t, v))
        offset += consumed
    return tlvs

def log_session(client_ip: str, query_count: int, duration_ms: float):
    """Log client session with timestamp, IP, query count, and duration"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"
    print(f"[TSQ-LOG] {timestamp} client={client_ip} protocol=stream queries={query_count} duration={duration_ms:.1f}ms")

def log_request(client_ip: str, status: str, error: str):
    """Log failed request"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"
    print(f"[TSQ-LOG] {timestamp} client={client_ip} protocol=stream status={status} error=\"{error}\"")

async def handle_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    # Get client address from stored peer addresses
    writer_id = id(writer)
    client_ip = peer_addresses.get(writer_id, 'unknown')
    
    print(f"[TSQ] New stream connection from {client_ip}")
    
    session_start = time.time()
    query_count = 0
    
    try:
        # Read request
        request_data = await reader.read(1024)
        t1_recv = time.time_ns()
        
        # Parse nonce
        if len(request_data) < 18:
            log_request(client_ip, "FAILED", "Request too short")
            return
        nonce = request_data[2:18]
        query_count += 1
        
        # Convert nanosecond timestamps to NTP format
        NTP_EPOCH_OFFSET = 2208988800
        
        def ns_to_ntp(ns_timestamp):
            seconds = ns_timestamp // 1_000_000_000
            nanos = ns_timestamp % 1_000_000_000
            ntp_seconds = seconds + NTP_EPOCH_OFFSET
            ntp_fraction = int((nanos * 2**32) / 1_000_000_000)
            return struct.pack("!II", ntp_seconds, ntp_fraction)
        
        # Convert T2 (receive timestamp)
        ntp_t1 = ns_to_ntp(t1_recv)
        
        # Build response (without T3 yet)
        response = b""
        response += tlv_pack(T_NONCE, nonce)
        response += tlv_pack(T_RECV_TS, ntp_t1)
        
        # Record T3 RIGHT BEFORE sending
        t2_send = time.time_ns()
        ntp_t2 = ns_to_ntp(t2_send)
        response += tlv_pack(T_SEND_TS, ntp_t2)
        
        # Send response immediately
        writer.write(response)
        await writer.drain()
        
        # Keep open
        await asyncio.sleep(5)
        
    except Exception as e:
        print(f"[TSQ] Error handling stream: {e}")
    finally:
        # Always log session summary when closing
        print(f"[TSQ] Closing connection from {client_ip}, queries={query_count}")
        session_duration = (time.time() - session_start) * 1000.0  # Convert to ms
        if query_count > 0:
            log_session(client_ip, query_count, session_duration)
        else:
            print(f"[TSQ] No queries processed for {client_ip}")
        
        # Clean up stored peer address
        peer_addresses.pop(writer_id, None)
        
        # Close writer
        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"[TSQ] Error closing writer: {e}")




# Keep track of active stream tasks
active_tasks = set()

def stream_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    # aioquic calls this synchronously, so we spawn our async handler
    # Try to get the actual peer address from the transport
    transport = writer.transport
    if hasattr(transport, '_transport') and hasattr(transport._transport, '_addr'):
        # aioquic wraps the transport, dig into it
        peer_addr = transport._transport._addr
        print(f"[TSQ-DEBUG] Got peer address from transport: {peer_addr}")
    
    task = asyncio.create_task(handle_stream(reader, writer))
    active_tasks.add(task)
    task.add_done_callback(active_tasks.discard)


# Store peer addresses globally (keyed by stream ID)
peer_addresses = {}

# Custom protocol to track peer addresses
class TSQProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._peer_addr = None
    
    def connection_made(self, transport):
        super().connection_made(transport)
        # Get peer address from transport
        self._peer_addr = transport.get_extra_info('peername')
        if self._peer_addr:
            print(f"[TSQ] New QUIC connection from {self._peer_addr[0]}")
    
    def quic_event_received(self, event: QuicEvent):
        if isinstance(event, StreamDataReceived):
            # Store peer address for this stream
            if self._peer_addr:
                peer_addresses[event.stream_id] = self._peer_addr[0]
        
        super().quic_event_received(event)

async def main():
    ap = argparse.ArgumentParser(description="TSQ QUIC Server")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=443)
    ap.add_argument("--cert", default="server.crt")
    ap.add_argument("--key", default="server.key")
    args = ap.parse_args()

    cfg = QuicConfiguration(is_client=False, alpn_protocols=ALPN)
    cfg.load_cert_chain(args.cert, args.key)

    print(f"[TSQ] Server Version {VERSION}")
    print(f"[TSQ] Server listening on {args.host}:{args.port} (UDP/QUIC)")
    
    # Use aioquic's serve with our custom protocol
    from aioquic.asyncio.server import serve as aioquic_serve
    
    server = await aioquic_serve(
        args.host,
        args.port,
        configuration=cfg,
        create_protocol=TSQProtocol,
        stream_handler=stream_handler,
    )
    
    print(f"[TSQ] Server ready")
    try:
        await asyncio.Future()  # Run forever until Ctrl+C
    except KeyboardInterrupt:
        print("\n[TSQ] Server stopped.")
    finally:
        server.close()
        await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())