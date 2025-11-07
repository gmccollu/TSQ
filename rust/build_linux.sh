#!/bin/bash
# Build TSQ for Linux x86_64

set -e

echo "Building TSQ for Linux x86_64..."
echo

cd "$(dirname "$0")"

# Check if Rust is installed
if ! command -v cargo &> /dev/null; then
    echo "Error: Rust not found."
    exit 1
fi

# Add Linux target if not already added
echo "Adding x86_64-unknown-linux-gnu target..."
rustup target add x86_64-unknown-linux-gnu

# Install cross-compilation toolchain
if ! command -v x86_64-linux-gnu-gcc &> /dev/null; then
    echo
    echo "Note: Cross-compilation toolchain not found."
    echo "Installing via Homebrew..."
    brew install FiloSottile/musl-cross/musl-cross
fi

# Try to build with cross
if ! command -v cross &> /dev/null; then
    echo
    echo "Installing 'cross' for easier cross-compilation..."
    cargo install cross --git https://github.com/cross-rs/cross
fi

echo
echo "Building for Linux x86_64..."
cross build --release --target x86_64-unknown-linux-gnu

echo
echo "✓ Build complete!"
echo
echo "Binaries:"
echo "  Server: target/x86_64-unknown-linux-gnu/release/tsq-server"
echo "  Client: target/x86_64-unknown-linux-gnu/release/tsq-client"
