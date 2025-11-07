#!/bin/bash
# Test TSQ Datagrams locally

set -e

cd "$(dirname "$0")"

echo "============================================================"
echo "Testing TSQ Datagrams Locally"
echo "============================================================"
echo

# Check if binaries exist
if [ ! -f "rust/target/release/tsq-server" ]; then
    echo "Error: Server binary not found. Run: cd rust && ./build.sh"
    exit 1
fi

if [ ! -f "rust/target/release/tsq-client" ]; then
    echo "Error: Client binary not found. Run: cd rust && ./build.sh"
    exit 1
fi

# Generate self-signed certificate for testing
echo "Generating test certificate..."
mkdir -p test-certs
cd test-certs

if [ ! -f "server.crt" ]; then
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout server.key \
        -out server.crt \
        -days 365 \
        -subj "/CN=localhost"
    echo "✓ Certificate generated"
else
    echo "✓ Using existing certificate"
fi

cd ..

# Start server in background
echo
echo "Starting TSQ datagram server on localhost:4433..."
./rust/target/release/tsq-server \
    --listen 127.0.0.1:4433 \
    --cert test-certs/server.crt \
    --key test-certs/server.key &

SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
sleep 2

# Run client
echo
echo "Running TSQ datagram client..."
echo "============================================================"
./rust/target/release/tsq-client \
    127.0.0.1 \
    --port 4433 \
    --count 3 \
    --insecure

echo "============================================================"
echo

# Kill server
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null || true

echo
echo "✓ Local test complete!"
