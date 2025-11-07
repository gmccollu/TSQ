#!/bin/bash
# Build TSQ Rust binaries

set -e

echo "Building TSQ with Quiche datagrams..."
echo

cd "$(dirname "$0")"

# Check if Rust is installed
if ! command -v cargo &> /dev/null; then
    echo "Error: Rust not found. Please install Rust first:"
    echo "  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi

# Build in release mode
echo "Building server..."
cargo build --release --bin tsq-server

echo "Building client..."
cargo build --release --bin tsq-client

echo
echo "✓ Build complete!"
echo
echo "Binaries:"
echo "  Server: target/release/tsq-server"
echo "  Client: target/release/tsq-client"
echo
echo "Usage:"
echo "  Server: ./target/release/tsq-server --listen 0.0.0.0:443 --cert cert.pem --key key.pem"
echo "  Client: ./target/release/tsq-client SERVER --port 443 --count 3 --insecure"
