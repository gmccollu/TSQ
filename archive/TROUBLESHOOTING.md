# TSQ QUIC Stream Issue

## Problem
Client sends request on QUIC stream ID 0, server receives it and writes 38-byte response to the same stream, but client reads 0 bytes (EOF).

## What We've Confirmed
1. ✅ Both client and server are using stream ID 0 (same stream)
2. ✅ Server successfully writes 38 bytes to writer buffer
3. ✅ Server calls `writer.drain()` multiple times
4. ✅ Server calls `protocol.transmit()` to force QUIC transmission
5. ✅ QUIC connection state is CONNECTED
6. ✅ Server keeps stream open for 10+ seconds
7. ✅ Client waits 0.5 seconds before reading
8. ❌ Client receives 0 bytes when calling `reader.read()`

## Hypothesis
This appears to be an aioquic library issue or a fundamental misunderstanding of how QUIC bidirectional streams work in aioquic.

## Next Steps
1. Try using aioquic's lower-level API instead of StreamReader/StreamWriter
2. Check if we need to handle stream data differently
3. Consider filing a bug report with aioquic project
4. Try alternative QUIC library (e.g., quic-go with Python bindings)

## Workaround Idea
Instead of using bidirectional streams, try:
- Client opens stream, sends request
- Server opens NEW stream back to client, sends response
- This mimics HTTP/3 request-response pattern
