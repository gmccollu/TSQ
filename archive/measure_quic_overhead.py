#!/usr/bin/env python3
"""
Measure QUIC processing overhead by comparing loopback timing
"""
import asyncio
import time
import os
import struct
from aioquic.asyncio import serve
from aioquic.asyncio.client import connect
from aioquic.quic.configuration import QuicConfiguration

async def measure_overhead():
    """Measure time between timestamp and actual transmission"""
    
    # Simple echo server
    async def handle_stream(reader, writer):
        data = await reader.read(1024)
        t_server = time.time_ns()
        
        # Immediately echo back with timestamp
        response = struct.pack("!Q", t_server) + data
        writer.write(response)
        await writer.drain()
        await asyncio.sleep(1)
    
    def stream_handler(reader, writer):
        asyncio.create_task(handle_stream(reader, writer))
    
    # Start server
    cfg_server = QuicConfiguration(is_client=False, alpn_protocols=["test"])
    cfg_server.load_cert_chain("server.crt", "server.key")
    
    server = await serve("127.0.0.1", 4433, configuration=cfg_server, stream_handler=stream_handler)
    
    await asyncio.sleep(0.5)
    
    # Connect client
    cfg_client = QuicConfiguration(is_client=True, alpn_protocols=["test"])
    cfg_client.verify_mode = False
    
    measurements = []
    
    async with connect("127.0.0.1", 4433, configuration=cfg_client) as client:
        for i in range(10):
            reader, writer = await client.create_stream()
            
            # Send with timestamp
            t1 = time.time_ns()
            writer.write(b"PING")
            await writer.drain()
            
            # Receive
            response = await reader.read(100)
            t4 = time.time_ns()
            
            # Extract server timestamp
            t_server = struct.unpack("!Q", response[:8])[0]
            
            # Calculate one-way delays
            # Assuming symmetric path on loopback
            rtt = t4 - t1
            
            # The server timestamp should be roughly at (t1 + t4) / 2
            # Any deviation is processing overhead
            expected_server_time = (t1 + t4) // 2
            overhead = t_server - expected_server_time
            
            measurements.append({
                'rtt_ns': rtt,
                'overhead_ns': overhead
            })
            
            await asyncio.sleep(0.1)
    
    server.close()
    
    # Analyze
    avg_rtt = sum(m['rtt_ns'] for m in measurements) / len(measurements)
    avg_overhead = sum(m['overhead_ns'] for m in measurements) / len(measurements)
    
    print("="*70)
    print("QUIC Processing Overhead Measurement (Loopback)")
    print("="*70)
    print(f"\nAverage RTT: {avg_rtt/1e6:.3f} ms")
    print(f"Average processing overhead: {avg_overhead/1e6:.3f} ms")
    print(f"\nThis overhead occurs between recording timestamp and actual transmission")
    print(f"on the wire. This explains the systematic difference between NTP and TSQ.")

if __name__ == "__main__":
    import sys
    
    print("""
╔════════════════════════════════════════════════════════════╗
║           QUIC Processing Overhead Measurement             ║
╚════════════════════════════════════════════════════════════╝

This test measures the time between recording a timestamp and
actual packet transmission by doing loopback tests.

""")
    
    try:
        asyncio.run(measure_overhead())
    except FileNotFoundError:
        print("\n✗ Error: server.crt/server.key not found")
        print("Run this from: cd /home/cisco/tsq-certs && python measure_quic_overhead.py")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
