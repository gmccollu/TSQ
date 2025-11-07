# Building TSQ for Linux

## Problem

The binaries were compiled for macOS (ARM64) but your servers are Linux (x86_64).

## Solution: Build on Linux Server

### Step 1: Copy Source to Linux Server

```bash
cd /Users/garrettmccollum/Desktop/TSQ
tar czf tsq-rust-src.tar.gz rust/
scp tsq-rust-src.tar.gz cisco@172.18.124.203:/home/cisco/
```

### Step 2: SSH to Server and Build

```bash
ssh cisco@172.18.124.203
```

Then on the server:

```bash
cd /home/cisco
tar xzf tsq-rust-src.tar.gz
cd rust

# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env

# Build
cargo build --release

# Verify binaries
ls -lh target/release/tsq-server target/release/tsq-client
```

### Step 3: Copy Binaries to Other Servers

Still on the Linux server:

```bash
# Copy to server2
scp target/release/tsq-server cisco@172.18.124.204:/home/cisco/tsq-server-dg

# Copy to client
scp target/release/tsq-client cisco@172.18.124.206:/home/cisco/tsq-client-dg

# Copy to local server
cp target/release/tsq-server /home/cisco/tsq-server-dg
```

### Step 4: Test

From your Mac:

```bash
python3 run_datagram_test.py
```

---

## Alternative: Quick Commands

Copy and paste these commands:

```bash
# On your Mac
cd /Users/garrettmccollum/Desktop/TSQ
tar czf tsq-rust-src.tar.gz rust/
scp tsq-rust-src.tar.gz cisco@172.18.124.203:/home/cisco/

# SSH to server
ssh cisco@172.18.124.203

# On the server (paste all at once)
cd /home/cisco && \
tar xzf tsq-rust-src.tar.gz && \
cd rust && \
(command -v cargo || (curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && source $HOME/.cargo/env)) && \
source $HOME/.cargo/env && \
cargo build --release && \
cp target/release/tsq-server /home/cisco/tsq-server-dg && \
scp target/release/tsq-server cisco@172.18.124.204:/home/cisco/tsq-server-dg && \
scp target/release/tsq-client cisco@172.18.124.206:/home/cisco/tsq-client-dg && \
echo "✓ Build and deployment complete!"
```

---

## Expected Output

When building:
```
   Compiling tsq-quiche v0.1.0 (/home/cisco/rust)
    Finished `release` profile [optimized] target(s) in 45.2s
```

Binaries should be ~5-10 MB each:
```
-rwxr-xr-x 1 cisco cisco 8.2M Nov  5 14:30 tsq-server
-rwxr-xr-x 1 cisco cisco 7.8M Nov  5 14:30 tsq-client
```

---

## Troubleshooting

### "cargo: command not found"
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
```

### "linker 'cc' not found"
```bash
sudo yum install gcc  # CentOS/RHEL
# or
sudo apt install build-essential  # Ubuntu/Debian
```

### Build takes too long
This is normal - first build can take 5-10 minutes. Subsequent builds are faster.

---

## After Building

Test with:
```bash
# From your Mac
python3 run_datagram_test.py
```

You should see:
```
[TSQ-Q] Connected to 14.38.117.100:443
[TSQ-Q] RTT=1.234 ms  offset=1289.123 ms
```
