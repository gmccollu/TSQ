#!/bin/bash
# Build TSQ on Linux server - paste this into SSH session

set -e

echo "Installing Rust and building TSQ..."
echo

# Install Rust via apt (faster than rustup)
if ! command -v cargo &> /dev/null; then
    echo "Installing Rust..."
    sudo apt update
    sudo apt install -y cargo rustc
    echo "✓ Rust installed"
fi

# Navigate and extract
cd /home/cisco
rm -rf rust
tar xzf tsq-src.tar.gz
cd rust

echo
echo "Building TSQ (this will take 5-10 minutes)..."
cargo build --release

echo
echo "Copying binaries..."
cp target/release/tsq-server /home/cisco/tsq-server-dg
cp target/release/tsq-client /home/cisco/tsq-client-dg
chmod +x /home/cisco/tsq-server-dg /home/cisco/tsq-client-dg

echo
echo "Deploying to other servers..."
scp /home/cisco/tsq-server-dg cisco@172.18.124.204:/home/cisco/
scp /home/cisco/tsq-client-dg cisco@172.18.124.206:/home/cisco/

echo
echo "✓ Build complete!"
ls -lh /home/cisco/tsq-server-dg /home/cisco/tsq-client-dg
