#!/usr/bin/env python3
"""
TSQ Client - QUIC Datagram Version (Fixed)
Uses custom protocol to properly handle datagram events
"""
import argparse
import asyncio
import os
import struct
import time
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import DatagramFrameReceived, QuicEvent

# TLV Types
T_NONCE = 1
T_RECV_TS = 2
T_SEND_TS = 3

def tlv_pack(tlv_type: int, value: bytes) -> bytes:
    """Pack a TLV with 1-byte length field"""
    return struct.pack("!BB", tlv_type, len(value)) + value

def parse_tlvs(data: bytes) -> dict:
    """Parse TLVs from response"""
    tlvs = {}
    offset = 0
    while offset < len(data):
        if offset + 2 > len(data):
            break
        tlv_type = data[offset]
        tlv_len = data[offset + 1]
        if offset + 2 + tlv_len > len(data):
            break
        tlv_val = data[offset + 2:offset + 2 + tlv_len]
        tlvs[tlv_type] = tlv_val
        offset += 2 + tlv_len
    return tlvs

def ntp_to_ns(ntp_bytes: bytes) -> int:
    """Convert NTP timestamp to nanoseconds"""
    NTP_EPOCH_OFFSET = 2208988800
    ntp_seconds, ntp_fraction = struct.unpack("!II", ntp_bytes)
    unix_seconds = ntp_seconds - NTP_EPOCH_OFFSET
    nanos = int((ntp_fraction * 1_000_000_000) / 2**32)
    return unix_seconds * 1_000_000_000 + nanos

def compute_metrics(t1: int, t2: int, t3: int, t4: int):
    """Compute RTT and offset"""
    rtt_ns = (t4 - t1) - (t3 - t2)
    offset_ns = ((t2 - t1) + (t3 - t4)) // 2
    return rtt_ns / 1e6, offset_ns / 1e6

class TSQDatagramClient(QuicConnectionProtocol):
    """Custom QUIC client that handles datagrams"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._datagram_received = asyncio.Queue()
    
    def quic_event_received(self, event: QuicEvent):
        """Handle QUIC events"""
        if isinstance(event, DatagramFrameReceived):
            # Put datagram in queue with receive timestamp
            self._datagram_received.put_nowait((event.data, time.time_ns()))
    
    async def wait_for_datagram(self, timeout: float):
        """Wait for a datagram response"""
        try:
            return await asyncio.wait_for(
                self._datagram_received.get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None, None

async def run_tsq_datagram(server: str, port: int, count: int, interval: float, insecure: bool):
    """Run TSQ datagram test"""
    
    # Configure QUIC
    configuration = QuicConfiguration(
        is_client=True,
        alpn_protocols=["tsq/1"],
        max_datagram_frame_size=65536,
    )
    
    if insecure:
        configuration.verify_mode = False
    
    # Import what we need
    from aioquic.quic.connection import QuicConnection
    
    # Create QUIC connection
    quic = QuicConnection(configuration=configuration)
    quic.connect(server, port, now=time.time())
    
    # Create protocol wrapper
    protocol = TSQDatagramClient(quic)
    
    # Create UDP transport
    loop = asyncio.get_event_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: protocol,
        remote_addr=(server, port)
    )
    
    # Set transport on protocol
    protocol.connection_made(transport)
    
    print(f"[TSQ-DG] Connected to {server}:{port}")
    
    # Wait for connection to establish
    await asyncio.sleep(1.0)
    
    results = []
    
    for probe_num in range(1, count + 1):
        print(f"[TSQ-DG] Probe #{probe_num} to {server}")
        
        # Generate nonce and build request
        nonce = os.urandom(16)
        request = tlv_pack(T_NONCE, nonce)
        
        # Send datagram and record T1
        protocol._quic.send_datagram_frame(request)
        t1 = time.time_ns()
        protocol.transmit()
        
        print(f"[TSQ-DG] Sent {len(request)} bytes")
        
        # Wait for response
        response_data, t4 = await protocol.wait_for_datagram(timeout=3.0)
        
        if response_data is None:
            print(f"[TSQ-DG] Timeout waiting for response")
            print(f"[TSQ-DG] Probe #{probe_num} failed")
        else:
            print(f"[TSQ-DG] Received {len(response_data)} bytes")
            
            # Parse response
            tlvs = parse_tlvs(response_data)
            
            if T_RECV_TS in tlvs and T_SEND_TS in tlvs:
                t2 = ntp_to_ns(tlvs[T_RECV_TS])
                t3 = ntp_to_ns(tlvs[T_SEND_TS])
                
                rtt_ms, offset_ms = compute_metrics(t1, t2, t3, t4)
                
                print(f"[TSQ-DG] T1 (client send):    {t1}")
                print(f"[TSQ-DG] T2 (server receive): {t2}")
                print(f"[TSQ-DG] T3 (server send):    {t3}")
                print(f"[TSQ-DG] T4 (client receive): {t4}")
                print(f"[TSQ-DG] RTT={rtt_ms:8.3f} ms  offset={offset_ms:8.3f} ms")
                
                results.append((rtt_ms, offset_ms))
                print(f"[TSQ-DG] Probe #{probe_num} complete")
            else:
                print(f"[TSQ-DG] Invalid response (missing timestamps)")
                print(f"[TSQ-DG] Probe #{probe_num} failed")
        
        # Wait before next probe
        if probe_num < count:
            print(f"[TSQ-DG] Waiting {interval}s before next probe...")
            await asyncio.sleep(interval)
    
    transport.close()
    
    return results

async def main():
    parser = argparse.ArgumentParser(description="TSQ Client (QUIC Datagram - Fixed)")
    parser.add_argument("servers", nargs="+", help="Server IP addresses")
    parser.add_argument("--port", type=int, default=443, help="Server port")
    parser.add_argument("--count", type=int, default=3, help="Number of probes per server")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval between probes")
    parser.add_argument("--insecure", action="store_true", help="Skip certificate verification")
    args = parser.parse_args()
    
    print(f"[TSQ-DG] Client Version (Datagram - Fixed)")
    print(f"[TSQ-DG] Hosts to probe: {args.servers}")
    print()
    
    all_results = []
    
    for idx, server in enumerate(args.servers, 1):
        print(f"[TSQ-DG] ===== Host {idx}/{len(args.servers)}: {server} =====")
        
        results = await run_tsq_datagram(
            server, args.port, args.count, args.interval, args.insecure
        )
        
        if results:
            avg_rtt = sum(r[0] for r in results) / len(results)
            avg_offset = sum(r[1] for r in results) / len(results)
            all_results.append((server, avg_rtt, avg_offset))
        
        print()
    
    # Print summary
    if all_results:
        print("=== TSQ Datagram Summary ===")
        print(f"{'Server':<20} {'RTT (ms)':>10} {'Offset (ms)':>12}")
        print("-" * 44)
        for server, rtt, offset in all_results:
            print(f"{server:<20} {rtt:>10.3f} {offset:>12.3f}")
        print("-" * 44)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[TSQ-DG] Client stopped")
