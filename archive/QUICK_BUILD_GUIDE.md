# Quick Build Guide for Linux

## The Issue
Your Mac is ARM64 (Apple Silicon) but your servers are x86_64 Linux. We need to build ON the Linux server.

## Quick Solution (5 minutes)

### Step 1: Copy source and SSH to server

```bash
cd /Users/garrettmccollum/Desktop/TSQ
tar czf /tmp/tsq-src.tar.gz rust/
scp /tmp/tsq-src.tar.gz cisco@172.18.124.203:/home/cisco/
ssh cisco@172.18.124.203
```

Password: `cisco123`

### Step 2: Build on the server (paste this entire block)

```bash
cd /home/cisco && \
rm -rf rust && \
tar xzf tsq-src.tar.gz && \
cd rust && \
if ! command -v cargo &> /dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  source $HOME/.cargo/env
fi && \
source $HOME/.cargo/env 2>/dev/null || true && \
cargo build --release && \
cp target/release/tsq-server /home/cisco/tsq-server-dg && \
cp target/release/tsq-client /home/cisco/tsq-client-dg && \
chmod +x /home/cisco/tsq-server-dg /home/cisco/tsq-client-dg && \
ls -lh /home/cisco/tsq-server-dg /home/cisco/tsq-client-dg && \
echo "✓ Build complete!"
```

This will:
- Extract source
- Install Rust if needed
- Build the binaries
- Copy to /home/cisco/
- Show file sizes

**Expected**: Takes 5-10 minutes, binaries should be ~2-8MB each

### Step 3: Deploy to other servers

Still on server1 (172.18.124.203):

```bash
scp /home/cisco/tsq-server-dg cisco@172.18.124.204:/home/cisco/
scp /home/cisco/tsq-client-dg cisco@172.18.124.206:/home/cisco/
```

### Step 4: Test

Exit back to your Mac and run:

```bash
python3 run_datagram_test.py
```

---

## If Rust Install Fails

The server might not have `curl`. Try `wget` instead:

```bash
wget -O - https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
cd /home/cisco/rust
cargo build --release
```

---

## Expected Output

When it works, you'll see:

```
[TSQ-Q] Connected to 14.38.117.100:443
[TSQ-Q] Probe #1 to 14.38.117.100
[TSQ-Q] Sent 18 bytes
[TSQ-Q] Received 38 bytes
[TSQ-Q] RTT=1.234 ms  offset=1289.123 ms
```

---

## One-Liner (if you want to try again)

From your Mac:

```bash
cd /Users/garrettmccollum/Desktop/TSQ && \
tar czf /tmp/tsq-src.tar.gz rust/ && \
scp /tmp/tsq-src.tar.gz cisco@172.18.124.203:/home/cisco/ && \
echo "Now SSH to 172.18.124.203 and run the build commands"
```
