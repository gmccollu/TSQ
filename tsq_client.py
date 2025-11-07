#!/usr/bin/env python3
"""TSQ Client - Version 2024-11-05-12:18"""
import argparse
import asyncio
import os
import random
import struct
import time
from typing import Tuple

from aioquic.asyncio.client import connect
from aioquic.quic.configuration import QuicConfiguration

VERSION = "2024-11-05-12:18"
ALPN = ["tsq/1"]
T_NONCE = 1
T_RECV_TS = 2
T_SEND_TS = 3

def tlv_pack(t: int, v: bytes) -> bytes:
    """Pack a TLV with 1-byte length field."""
    if len(v) > 255:
        raise ValueError("TLV value too long (max 255 bytes)")
    return struct.pack("!BB", t, len(v)) + v

def tlv_unpack(data: bytes) -> Tuple[int, bytes, int]:
    """Unpack a single TLV from data. Returns (type, value, bytes_consumed)."""
    if len(data) < 2:
        raise ValueError("TLV too short")
    t = data[0]
    l = data[1]
    if len(data) < 2 + l:
        raise ValueError("TLV length mismatch")
    v = data[2:2+l]
    return t, v, 2 + l

def parse_tlvs(data: bytes) -> list:
    """Parse all TLVs from data. Returns list of (type, value) tuples."""
    tlvs = []
    offset = 0
    while offset < len(data):
        t, v, consumed = tlv_unpack(data[offset:])
        tlvs.append((t, v))
        offset += consumed
    return tlvs

def ntp_to_ns(ntp_bytes: bytes) -> int:
    """Convert NTP timestamp (8 bytes) to nanoseconds since Unix epoch."""
    NTP_EPOCH_OFFSET = 2208988800
    ntp_seconds, ntp_fraction = struct.unpack("!II", ntp_bytes)
    unix_seconds = ntp_seconds - NTP_EPOCH_OFFSET
    nanos = int((ntp_fraction * 1_000_000_000) / 2**32)
    return unix_seconds * 1_000_000_000 + nanos

def compute_metrics(t1: int, t2: int, t3: int, t4: int) -> Tuple[float, float]:
    """
    Classic NTP-like formulas (all ns):
      RTT    = (t4 - t1) - (t3 - t2)
      offset = ((t2 - t1) + (t3 - t4)) / 2
    Returns (rtt_ms, offset_ms)
    """
    rtt_ns    = (t4 - t1) - (t3 - t2)
    offset_ns = ((t2 - t1) + (t3 - t4)) // 2
    return rtt_ns / 1e6, offset_ns / 1e6

async def one_probe(proto, server_name: str, payload_size_pad: int = 0):
    # create a bidirectional stream
    reader, writer = await proto.create_stream(is_unidirectional=False)
    
    # Stream created
    
    # Generate 16-byte nonce (per spec)
    nonce = os.urandom(16)
    
    # Build request: Nonce TLV (Type 1, 16 bytes)
    request = tlv_pack(T_NONCE, nonce)
    
    # TODO: Add optional TLVs (Precision Mode, Signature Request, Padding)
    if payload_size_pad > 0:
        padding = b'\x00' * payload_size_pad
        request += tlv_pack(254, padding)  # Type 254 = Padding
    
    # Send request to server
    print(f"[TSQ] Sending {len(request)} bytes")
    writer.write(request)
    
    # Record T1 RIGHT BEFORE drain (actual send time)
    t1 = time.time_ns()
    await writer.drain()
    print("[TSQ] Request sent")

    try:
        # Read response
        print("[TSQ] Reading response...")
        response_data = await asyncio.wait_for(reader.read(100), timeout=3.0)
        
        # Record T4 IMMEDIATELY when data arrives
        t4 = time.time_ns()
        print(f"[TSQ] Received {len(response_data)} bytes")
        
        if len(response_data) == 0:
            raise EOFError("No data received")
        
        # Parse TLVs from response
        tlvs = parse_tlvs(response_data)
        
        # Extract required TLVs
        nonce_echo = None
        t2_ntp = None
        t3_ntp = None
        
        for tlv_type, tlv_value in tlvs:
            if tlv_type == T_NONCE:
                nonce_echo = tlv_value
            elif tlv_type == T_RECV_TS:
                t2_ntp = tlv_value
            elif tlv_type == T_SEND_TS:
                t3_ntp = tlv_value
        
        # Validate response
        if nonce_echo != nonce:
            raise RuntimeError(f"Nonce mismatch: sent {nonce.hex()}, got {nonce_echo.hex() if nonce_echo else 'None'}")
        
        if not t2_ntp or not t3_ntp:
            raise RuntimeError("Missing timestamp TLVs in response")
        
        if len(t2_ntp) != 8 or len(t3_ntp) != 8:
            raise RuntimeError("Invalid timestamp length")
        
        # Convert NTP timestamps to nanoseconds
        t2 = ntp_to_ns(t2_ntp)
        t3 = ntp_to_ns(t3_ntp)
        
        # Compute metrics using T1, T2, T3, T4
        rtt_ms, offset_ms = compute_metrics(t1, t2, t3, t4)
        
        # Debug: show all timestamps
        print(f"[TSQ] T1 (client send):    {t1}")
        print(f"[TSQ] T2 (server receive): {t2}")
        print(f"[TSQ] T3 (server send):    {t3}")
        print(f"[TSQ] T4 (client receive): {t4}")
        print(f"[TSQ] T2-T1 (forward):     {(t2-t1)/1e6:.3f} ms")
        print(f"[TSQ] T4-T3 (return):      {(t4-t3)/1e6:.3f} ms")
        print(f"[TSQ] RTT={rtt_ms:8.3f} ms  offset={offset_ms:8.3f} ms")
        
        # Close the stream (don't wait - let it close in background)
        writer.close()
        
        return rtt_ms, offset_ms, (t1, t2, t3, t4)

    except asyncio.TimeoutError:
        print("[TSQ] Timeout waiting for response.")
    except EOFError as e:
        print(f"[TSQ] EOF: {e}")
    except asyncio.IncompleteReadError:
        print("[TSQ] Incomplete read from server.")
    except Exception as e:
        print(f"[TSQ] Error: {e}")
    finally:
        # Ensure stream is closed even on error
        if not writer.is_closing():
            writer.close()


async def run_client(hosts, port: int, count: int, interval: float, insecure: bool, pad: int):
    results = []

    for idx, host in enumerate(hosts, start=1):
        print(f"\n[TSQ] ===== Host {idx}/{len(hosts)}: {host} =====")
        cfg = QuicConfiguration(is_client=True, alpn_protocols=ALPN)
        if insecure:
            cfg.verify_mode = False
        cfg.server_name = host

        print(f"[TSQ] Preparing to connect to {host}:{port}")

        try:
            # Use async with like the working simple test
            async with connect(host, port, configuration=cfg) as client:
                print(f"[TSQ] Connected to {host}:{port} over QUIC")

                for i in range(1, count + 1):
                    print(f"[TSQ] Probe #{i} to {host}")
                    try:
                        rtt_ms, offset_ms, stamps = await one_probe(client, host, payload_size_pad=pad)
                        results.append((host, rtt_ms, offset_ms))
                        print(f"[TSQ] Probe #{i} complete")
                    except Exception as e:
                        import traceback
                        print(f"[TSQ] {host} probe #{i} raised: {e}")
                        traceback.print_exc()
                    
                    if i < count:
                        print(f"[TSQ] Waiting {interval}s before next probe...")
                        await asyncio.sleep(interval)
                        print(f"[TSQ] Starting next probe")
                
                print(f"[TSQ] Completed all {count} probes to {host}")

        except Exception as e:
            print(f"[TSQ] Connection to {host}:{port} failed: {e!r}")

    # --- Summary ---
    if results:
        print("\n=== TSQ Multi-Server Summary ===")
        print(f"{'Server':<18} {'RTT (ms)':>10} {'Offset (ms)':>12}")
        print("-" * 42)
        summary = {}
        for host, rtt, offset in results:
            summary.setdefault(host, {"r": [], "o": []})
            summary[host]["r"].append(rtt)
            summary[host]["o"].append(offset)
        for host, vals in summary.items():
            avg_r = sum(vals["r"]) / len(vals["r"])
            avg_o = sum(vals["o"]) / len(vals["o"])
            print(f"{host:<18} {avg_r:10.3f} {avg_o:12.3f}")
        print("-" * 42)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="TSQ QUIC Client")
    ap.add_argument(
        "hosts",
        nargs="+",
        help="One or more TSQ server IPs or hostnames separated by spaces (e.g. '14.38.117.100 14.38.117.200')"
    )
    ap.add_argument("--port", type=int, default=443, help="Server port (default: 443)")
    ap.add_argument("--count", type=int, default=10, help="Number of probes per server")
    ap.add_argument("--interval", type=float, default=1.0, help="Seconds between probes")
    ap.add_argument("--insecure", action="store_true", help="Skip certificate verification")
    ap.add_argument("--pad", type=int, default=0, help="Extra bytes to pad request value")

    args = ap.parse_args()

    # Debug: print which hosts were parsed
    print(f"[TSQ] Client Version {VERSION}")
    print(f"[TSQ] Hosts to probe: {args.hosts}")

    asyncio.run(
        run_client(
            args.hosts,
            args.port,
            args.count,
            args.interval,
            args.insecure,
            args.pad,
        )
    )