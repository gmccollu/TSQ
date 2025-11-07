# How to Run TSQ Datagrams

## Quick Start

### Option 1: Test Locally (Recommended First)

Test on your Mac to verify everything works:

```bash
cd /Users/garrettmccollum/Desktop/TSQ
./test_datagrams_local.sh
```

This will:
1. Generate a test certificate
2. Start server on localhost:4433
3. Run client with 3 probes
4. Show results
5. Clean up

**Expected output**:
```
[TSQ-Q] T1 (client send):    ...
[TSQ-Q] T2 (server receive): ...
[TSQ-Q] T3 (server send):    ...
[TSQ-Q] T4 (client receive): ...
[TSQ-Q] RTT=X.XXX ms  offset=X.XXX ms
```

---

### Option 2: Deploy to Test Environment

Deploy to your test servers and client:

```bash
cd /Users/garrettmccollum/Desktop/TSQ

# Deploy binaries
./deploy_datagrams.sh

# Run automated test
python3 run_datagram_test.py
```

---

### Option 3: Manual Deployment and Testing

#### Step 1: Deploy Binaries

```bash
cd /Users/garrettmccollum/Desktop/TSQ

# Copy to servers
scp rust/target/release/tsq-server cisco@172.18.124.203:/home/cisco/tsq-server-dg
scp rust/target/release/tsq-server cisco@172.18.124.204:/home/cisco/tsq-server-dg

# Copy to client
scp rust/target/release/tsq-client cisco@172.18.124.206:/home/cisco/tsq-client-dg
```

#### Step 2: Start Servers

**Terminal 1 - Server 1:**
```bash
ssh cisco@172.18.124.203
cd /home/cisco/tsq-certs
../tsq-server-dg --listen 0.0.0.0:443 --cert server.crt --key server.key
```

**Terminal 2 - Server 2:**
```bash
ssh cisco@172.18.124.204
cd /home/cisco/tsq-certs
../tsq-server-dg --listen 0.0.0.0:443 --cert server.crt --key server.key
```

#### Step 3: Run Client

**Terminal 3 - Client:**
```bash
ssh cisco@172.18.124.206
./tsq-client-dg 14.38.117.100 14.38.117.200 --port 443 --count 3 --insecure
```

---

## Expected Results

### Datagram Output

```
[TSQ-Q] Client Version (Datagram)
[TSQ-Q] Hosts to probe: ['14.38.117.100', '14.38.117.200']

[TSQ-Q] ===== Host 1/2: 14.38.117.100 =====
[TSQ-Q] Connecting to 14.38.117.100:443...
[TSQ-Q] Connected to 14.38.117.100:443
[TSQ-Q] Probe #1 to 14.38.117.100
[TSQ-Q] Sent 18 bytes
[TSQ-Q] Received 38 bytes
[TSQ-Q] T1 (client send):    1762367291685778266
[TSQ-Q] T2 (server receive): 1762367292975619678
[TSQ-Q] T3 (server send):    1762367292975658469
[TSQ-Q] T4 (client receive): 1762367291687111771
[TSQ-Q] RTT=1.234 ms  offset=1289.123 ms
[TSQ-Q] Probe #1 complete
...
[TSQ-Q] Average: RTT=1.234 ms, Offset=1289.123 ms
```

### Key Metrics to Compare

| Metric | Streams (Python) | Datagrams (Rust) | Improvement |
|--------|------------------|------------------|-------------|
| RTT | ~2ms | ~1ms | ~50% faster |
| Accuracy | 0.066-0.256ms | Similar | Same |
| Encryption | Full (TLS 1.3) | Full (TLS 1.3) | Same |
| Reliability | Guaranteed | Best-effort | Trade-off |

---

## Troubleshooting

### "Binary not found"
```bash
cd /Users/garrettmccollum/Desktop/TSQ/rust
./build.sh
```

### "Connection refused"
- Check servers are running
- Verify firewall allows port 443
- Check certificates exist in `/home/cisco/tsq-certs/`

### "No response received"
- Datagrams can be lost (this is normal)
- Try increasing `--count` to 5 or 10
- Check network connectivity

---

## Comparison Commands

Run both versions side-by-side:

```bash
# Streams version (Python)
python3 tsq_test_runner.py test

# Datagrams version (Rust)
python3 run_datagram_test.py

# Compare results!
```

---

## Files

- `test_datagrams_local.sh` - Local testing script
- `deploy_datagrams.sh` - Deploy to test environment
- `run_datagram_test.py` - Automated test runner
- `rust/target/release/tsq-server` - Server binary
- `rust/target/release/tsq-client` - Client binary

---

## Next Steps

1. ✅ Test locally first
2. ✅ Deploy to test environment
3. ✅ Compare with streams version
4. ✅ Measure latency improvement
5. ✅ Validate accuracy

**Ready to test!** Start with `./test_datagrams_local.sh`
