#!/bin/bash
# Install Quiche for TSQ Datagram Support

set -e

echo "============================================================"
echo "Installing Quiche for TSQ Datagram Support"
echo "============================================================"
echo

# Check if Rust is installed
if ! command -v cargo &> /dev/null; then
    echo "Rust not found. Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
    echo "✓ Rust installed"
else
    echo "✓ Rust already installed"
fi

# Install build dependencies
echo
echo "Installing build dependencies..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt-get update
    sudo apt-get install -y build-essential cmake libssl-dev pkg-config git
elif [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Please install Homebrew first."
        exit 1
    fi
    brew install cmake openssl pkg-config git
fi
echo "✓ Build dependencies installed"

# Clone and build quiche
echo
echo "Cloning and building quiche..."
cd ~
if [ -d "quiche" ]; then
    echo "Quiche directory already exists, updating..."
    cd quiche
    git pull
else
    git clone --recursive https://github.com/cloudflare/quiche
    cd quiche
fi

echo "Building quiche (this may take a few minutes)..."
cargo build --release --features ffi,pkg-config-meta,qlog

echo "✓ Quiche built successfully"

# Create symlink to library
echo
echo "Creating library symlink..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    LIB_NAME="libquiche.so"
    sudo ln -sf ~/quiche/target/release/$LIB_NAME /usr/local/lib/$LIB_NAME
    sudo ldconfig
elif [[ "$OSTYPE" == "darwin"* ]]; then
    LIB_NAME="libquiche.dylib"
    sudo ln -sf ~/quiche/target/release/$LIB_NAME /usr/local/lib/$LIB_NAME
fi
echo "✓ Library symlink created"

# Test
echo
echo "Testing quiche installation..."
cd ~/quiche
cargo test --release --features ffi

echo
echo "============================================================"
echo "✓ Quiche installation complete!"
echo "============================================================"
echo
echo "Library location: ~/quiche/target/release/$LIB_NAME"
echo "Symlink: /usr/local/lib/$LIB_NAME"
echo
echo "You can now use TSQ with QUIC datagrams!"
echo "Test with: python3 quiche_wrapper.py"
