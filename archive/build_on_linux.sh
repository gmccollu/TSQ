#!/bin/bash
# Build TSQ on Linux server

set -e

echo "============================================================"
echo "Building TSQ on Linux Server"
echo "============================================================"
echo

SERVER="172.18.124.203"
USER="cisco"
PASSWORD="cisco123"

echo "This script will:"
echo "1. Copy Rust source code to Linux server"
echo "2. Install Rust on the server (if needed)"
echo "3. Build the binaries on Linux"
echo "4. Copy binaries back to your Mac"
echo "5. Deploy to all servers"
echo

# Create tarball of source
echo "Creating source tarball..."
cd "$(dirname "$0")"
tar czf /tmp/tsq-rust-src.tar.gz rust/

# Copy to server
echo "Copying source to $SERVER..."
scp /tmp/tsq-rust-src.tar.gz ${USER}@${SERVER}:/home/cisco/

# Build on server
echo "Building on Linux server..."
ssh ${USER}@${SERVER} << 'ENDSSH'
cd /home/cisco
tar xzf tsq-rust-src.tar.gz
cd rust

# Install Rust if needed
if ! command -v cargo &> /dev/null; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
fi

# Build
echo "Building TSQ..."
cargo build --release

echo "Build complete!"
ls -lh target/release/tsq-server target/release/tsq-client
ENDSSH

# Copy binaries back
echo
echo "Copying binaries back to Mac..."
scp ${USER}@${SERVER}:/home/cisco/rust/target/release/tsq-server rust/target/release/tsq-server-linux
scp ${USER}@${SERVER}:/home/cisco/rust/target/release/tsq-client rust/target/release/tsq-client-linux

echo
echo "✓ Linux binaries ready!"
echo
echo "Binaries:"
echo "  Server: rust/target/release/tsq-server-linux"
echo "  Client: rust/target/release/tsq-client-linux"
echo
echo "Now deploying to all servers..."
echo

# Deploy to all servers
scp rust/target/release/tsq-server-linux ${USER}@172.18.124.203:/home/cisco/tsq-server-dg
scp rust/target/release/tsq-server-linux ${USER}@172.18.124.204:/home/cisco/tsq-server-dg
scp rust/target/release/tsq-client-linux ${USER}@172.18.124.206:/home/cisco/tsq-client-dg

echo
echo "✓ Deployment complete!"
echo
echo "Ready to test with: python3 run_datagram_test.py"
