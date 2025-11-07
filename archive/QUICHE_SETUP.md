# Setting Up Quiche for TSQ Datagram Implementation

## Overview

Quiche is Cloudflare's QUIC implementation with excellent datagram support. We'll use it for the TSQ datagram version while keeping the aioquic streams version as-is.

## Installation Steps

### 1. Install Rust (if not already installed)

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### 2. Install Build Dependencies

**On Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake libssl-dev pkg-config
```

**On macOS:**
```bash
brew install cmake openssl pkg-config
```

### 3. Clone and Build Quiche

```bash
cd ~
git clone --recursive https://github.com/cloudflare/quiche
cd quiche
cargo build --release --features ffi,pkg-config-meta,qlog
```

### 4. Install Python Bindings (if available)

```bash
# Check if Python bindings exist
cd ~/quiche
ls -la bindings/python/

# If they exist:
cd bindings/python
pip install -e .
```

**Note**: Quiche's Python bindings may be limited. We might need to use the C FFI directly via ctypes.

## Alternative: Use Quiche via ctypes

If Python bindings aren't available, we can use quiche's C API directly from Python using ctypes. This is what we'll implement.

## Files Structure

```
TSQ/
├── tsq_server.py              # Streams version (working) ✓
├── tsq_client.py              # Streams version (working) ✓
├── tsq_server_quiche.py       # Datagram version (new)
├── tsq_client_quiche.py       # Datagram version (new)
└── quiche_wrapper.py          # Python wrapper for quiche C API
```

## Testing

Once installed, test with:
```bash
python3 tsq_test_runner.py deploy
python3 tsq_test_runner.py test_quiche
```

## Next Steps

1. Install Rust and build quiche (on all test machines)
2. Deploy quiche-based TSQ implementation
3. Compare streams vs datagrams performance
