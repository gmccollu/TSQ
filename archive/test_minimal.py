#!/usr/bin/env python3
"""
Minimal test to see if aioquic bidirectional streams work at all
"""
import asyncio
from aioquic.asyncio import serve
from aioquic.asyncio.client import connect
from aioquic.quic.configuration import QuicConfiguration

ALPN = ["test"]

async def handle_stream(reader, writer):
    """Server: read request, send response"""
    print("[SERVER] Stream opened")
    data = await reader.read(100)
    print(f"[SERVER] Received: {data}")
    
    response = b"HELLO FROM SERVER"
    writer.write(response)
    await writer.drain()
    print(f"[SERVER] Sent: {response}")
    
    # Keep stream open
    await asyncio.sleep(5)
    print("[SERVER] Closing")

def stream_handler(reader, writer):
    asyncio.create_task(handle_stream(reader, writer))

async def run_server():
    cfg = QuicConfiguration(is_client=False, alpn_protocols=ALPN)
    cfg.load_cert_chain("server.crt", "server.key")
    
    server = await serve("0.0.0.0", 4433, configuration=cfg, stream_handler=stream_handler)
    print("[SERVER] Listening on 0.0.0.0:4433")
    
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        pass

async def run_client():
    cfg = QuicConfiguration(is_client=True, alpn_protocols=ALPN)
    cfg.verify_mode = False
    
    # Connect to server1's public IP
    server_ip = "14.38.117.100"
    async with connect(server_ip, 4433, configuration=cfg) as client:
        print("[CLIENT] Connected")
        
        reader, writer = await client.create_stream()
        print("[CLIENT] Created stream")
        
        # Send request
        writer.write(b"HELLO FROM CLIENT")
        await writer.drain()
        print("[CLIENT] Sent request")
        
        # Wait a bit
        await asyncio.sleep(1)
        
        # Read response
        print("[CLIENT] Reading response...")
        response = await reader.read(100)
        print(f"[CLIENT] Received: {response}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        asyncio.run(run_server())
    else:
        asyncio.run(run_client())
