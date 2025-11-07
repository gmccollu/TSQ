# TSQ - Time Synchronization over QUIC

**Secure, encrypted time synchronization using QUIC protocol**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Rust](https://img.shields.io/badge/rust-1.70+-orange.svg)](https://www.rust-lang.org/)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![IETF Draft](https://img.shields.io/badge/IETF-Draft-blue.svg)](https://datatracker.ietf.org/doc/html/draft-mccollum-ntp-tsq-01)

**📄 IETF Internet-Draft:** [draft-mccollum-ntp-tsq-01](https://datatracker.ietf.org/doc/html/draft-mccollum-ntp-tsq-01)

---

## Overview

TSQ provides two complete implementations of secure time synchronization:

- **TSQ Datagrams** (Rust/Quiche) - Ultra-fast, using QUIC unreliable datagrams
- **TSQ Streams** (Python/aioquic) - Reliable, using QUIC streams

Both implementations provide **TLS 1.3 encrypted time synchronization**, addressing NTP's lack of encryption while maintaining high performance.

### Key Features

✅ **Encrypted** - Full TLS 1.3 encryption (NTP has none)  
✅ **Fast** - Datagrams: 0.9ms RTT, Streams: 1.3ms RTT  
✅ **Accurate** - Sub-millisecond time synchronization  
✅ **Secure** - Certificate-based authentication  
✅ **Production-ready** - Validated against NTP  

---

## Quick Start

### Prerequisites

**Supported Platforms:**
- ✅ **Linux** - Full support (query + clock adjustment)
- ✅ **macOS** - Full support (query + clock adjustment)
- ⚠️ **Windows** - Query only (clock adjustment not yet supported)

**For Python Streams:**
```bash
python3 -m venv tsq-venv
source tsq-venv/bin/activate  # On Windows: tsq-venv\Scripts\activate
pip install aioquic cryptography
```

**For Rust Datagrams:**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### Build

**Rust Datagrams:**
```bash
cd rust
cargo build --release
```

Binaries will be in `rust/target/release/`:
- `tsq-datagram-server`
- `tsq-datagram-client`
- `tsq-datagram-adjtime`

---

## Public Test Server

A public TSQ server is available for testing and evaluation:

**Server:** `tsq.gmccollu.com` (3.15.157.117)

### Test with Datagrams (Rust):
```bash
# Query only (no clock adjustment)
./rust/target/release/tsq-datagram-client tsq.gmccollu.com --port 443

# Sync clock (requires sudo)
sudo ./rust/target/release/tsq-datagram-adjtime tsq.gmccollu.com --port 443
```

### Test with Streams (Python):
```bash
# Sync clock (requires sudo)
sudo python3 tsq-stream-client.py tsq.gmccollu.com --port 8443
```

**Notes:**
- Uses a valid Let's Encrypt certificate (no `--insecure` flag needed)
- Datagrams on UDP port 443
- Streams on UDP port 8443
- This is a test server - do not use for production time synchronization
- Server may be restarted or reconfigured without notice

---

## Usage

### TSQ Datagrams (Rust)

**Two client tools are provided:**

| Tool | Purpose | Adjusts Clock? | Requires sudo? |
|------|---------|----------------|----------------|
| `tsq-datagram-client` | Query and measure only | ❌ No | ❌ No |
| `tsq-datagram-adjtime` | Query and adjust clock | ✅ Yes | ✅ Yes |

**Why two tools?**
- **`client`** is for testing, monitoring, and verification without touching the system clock
- **`adjtime`** is for actual time synchronization when you want to correct the clock

#### Server
```bash
sudo ./rust/target/release/tsq-datagram-server \
  --listen 0.0.0.0:443 \
  --cert /path/to/server.crt \
  --key /path/to/server.key
```

**Options:**
- `--listen <IP:PORT>` - Address to listen on (default: 0.0.0.0:443)
- `--cert <FILE>` - TLS certificate file (required)
- `--key <FILE>` - TLS private key file (required)

#### Client (Query Only)

**Purpose:** Query servers to measure time offset and RTT. Does **not** adjust the system clock.

```bash
./rust/target/release/tsq-datagram-client \
  SERVER_IP [SERVER_IP...] \
  --port 443 \
  --count 3 \
  --insecure
```

**Options:**
- `SERVER_IP` - One or more server IP addresses (required)
- `--port <PORT>` - Server port (default: 443, range: 1-65535)
- `--count <N>` - Number of probes per server (default: 3, range: 1-100)
- `--insecure` - Skip certificate verification (testing only)

**Use cases:**
- Testing and verification
- Monitoring time offset without changing the clock
- Benchmarking RTT performance

**Example:**
```bash
# Query two servers with 5 probes each
./rust/target/release/tsq-datagram-client 192.168.1.100 192.168.1.101 --count 5 --insecure
```

#### Clock Adjustment (Query + Adjust)

**Purpose:** Query servers **and** adjust the system clock based on the measured offset. Requires `sudo`.
```bash
sudo ./rust/target/release/tsq-datagram-adjtime \
  SERVER_IP [SERVER_IP...] \
  --max-offset 1000 \
  --slew-threshold 500 \
  --insecure
```

**Options:**
- `SERVER_IP` - One or more server IP addresses (required)
- `--port <PORT>` - Server port (default: 443)
- `--queries <N>` - Queries per server (default: 5)
- `--max-offset <MS>` - Maximum allowed offset (default: 1000ms)
- `--slew-threshold <MS>` - Threshold for slew vs step (default: 500ms)
- `--insecure` - Skip certificate verification (testing only)
- `--dry-run` - Don't actually adjust clock
- `--verbose` - Verbose output

**Examples:**
```bash
# Test sync without adjusting clock
./rust/target/release/tsq-datagram-adjtime 192.168.1.100 --insecure --dry-run

# Actually sync clock (requires sudo)
sudo ./rust/target/release/tsq-datagram-adjtime 192.168.1.100 192.168.1.101 --insecure

# Use conservative threshold for production
sudo ./rust/target/release/tsq-datagram-adjtime 192.168.1.100 --slew-threshold 1000 --insecure
```

---

### TSQ Streams (Python)

#### Server
```bash
sudo python3 tsq-stream-server.py \
  --host 0.0.0.0 \
  --port 443 \
  --cert /path/to/server.crt \
  --key /path/to/server.key
```

**Options:**
- `--host <IP>` - IP address to bind to (default: 0.0.0.0)
- `--port <PORT>` - Port to listen on (default: 443)
- `--cert <FILE>` - TLS certificate file (required)
- `--key <FILE>` - TLS private key file (required)

#### Client
```bash
python3 tsq-stream-client.py \
  SERVER_IP [SERVER_IP...] \
  --port 443 \
  --queries 5 \
  --insecure \
  --dry-run
```

**Options:**
- `SERVER_IP` - One or more server IP addresses (required)
- `--port <PORT>` - Server port (default: 443, range: 1-65535)
- `--queries <N>` - Queries per server (default: 5, range: 1-100)
- `--max-offset <MS>` - Maximum allowed offset (default: 1000ms)
- `--slew-threshold <MS>` - Threshold for slew vs step (default: 500ms)
- `--insecure` - Skip certificate verification (testing only)
- `--dry-run` - Don't actually adjust clock
- `--verbose` - Verbose output

**Example:**
```bash
# Test sync without adjusting clock
python3 tsq-stream-client.py 192.168.1.100 --insecure --dry-run --verbose

# Actually sync clock (requires sudo)
sudo python3 tsq-stream-client.py 192.168.1.100 192.168.1.101 --insecure
```

---

## Important Caveats

### ⚠️ One-Shot Client Synchronization (Not a Client Daemon)

**TSQ clients currently provide one-shot synchronization similar to `ntpdate`, not continuous synchronization like `ntpd`.**

#### What This Means:

**TSQ Servers:**
- ✅ Run continuously in the background (like `ntpd` server)
- ✅ Always available to respond to client requests
- ✅ Can be run as systemd service or daemon

**TSQ Clients:**
- ❌ Run once, adjust the clock, and exit
- ❌ Do **not** run continuously in the background
- ❌ Do **not** automatically maintain clock discipline over time
- ❌ Must be manually run or scheduled

#### Comparison with NTP:

| Feature | NTP Server | TSQ Server | NTP Client Daemon | TSQ Client |
|---------|------------|------------|-------------------|------------|
| **Runs continuously** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Background daemon** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Automatic sync** | N/A | N/A | ✅ Yes | ❌ No |
| **Clock discipline** | N/A | N/A | ✅ Yes | ❌ No |
| **Set and forget** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |

#### Usage Patterns:

**1. Manual Synchronization:**
```bash
# Run when needed
sudo tsq-stream-client.py SERVER --insecure
```

**2. Scheduled with Cron:**
```bash
# Add to /etc/cron.d/tsq-sync
# Sync every 5 minutes
*/5 * * * * root /usr/local/bin/tsq-stream-client.py SERVER --insecure >> /var/log/tsq.log 2>&1
```

**3. Scheduled with Systemd Timer:**
```bash
# /etc/systemd/system/tsq-sync.timer
[Unit]
Description=TSQ Time Sync Timer

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

**4. Use Alongside NTP:**
```bash
# Use NTP daemon for continuous discipline
# Use TSQ for initial sync or verification
sudo tsq-stream-client.py SERVER --insecure
sudo systemctl start ntpd
```

#### Future Development:

A TSQ daemon mode (similar to `ntpd`) is planned for future releases. This would provide:
- Continuous background operation
- Automatic periodic synchronization
- Clock discipline and drift correction
- Systemd integration
- Logging and monitoring

**For now, TSQ is best suited for:**
- Initial clock synchronization
- Scheduled periodic sync (via cron/systemd)
- Verification and testing
- One-time corrections

---

### ⚠️ Port Conflicts

**You cannot run both Datagram and Stream servers on the same port simultaneously.**

Both implementations bind to the same port (typically 443). To test both:

1. **Test Datagrams first:**
   ```bash
   # Start datagram server
   sudo ./rust/target/release/tsq-datagram-server --listen 0.0.0.0:443 --cert cert.crt --key key.key
   
   # Test
   ./rust/target/release/tsq-datagram-client SERVER_IP --insecure
   
   # Kill server
   sudo pkill tsq-datagram-server
   ```

2. **Then test Streams:**
   ```bash
   # Start stream server
   sudo python3 tsq-stream-server.py --host 0.0.0.0 --port 443 --cert cert.crt --key key.key
   
   # Test
   python3 tsq-stream-client.py SERVER_IP --insecure --dry-run
   
   # Kill server
   sudo pkill -f tsq-stream-server
   ```

3. **Or use different ports:**
   ```bash
   # Datagrams on 443
   sudo ./rust/target/release/tsq-datagram-server --listen 0.0.0.0:443 --cert cert.crt --key key.key
   
   # Streams on 8443
   sudo python3 tsq-stream-server.py --host 0.0.0.0 --port 8443 --cert cert.crt --key key.key
   ```

### ⚠️ Certificate Verification

The `--insecure` flag **disables certificate verification** and should **only be used for testing**.

**Security Warning:** When using `--insecure`, the connection is vulnerable to man-in-the-middle attacks.

For production use:
1. Use proper certificates from a trusted CA
2. Remove the `--insecure` flag
3. Ensure certificates have proper Subject Alternative Names (SANs)

### ⚠️ Privileged Ports

Port 443 requires root/administrator privileges:
- **Linux/Mac:** Use `sudo`
- **Windows:** Run as Administrator

### ⚠️ Clock Adjustment

Adjusting the system clock requires elevated privileges:
- **Linux:** `sudo` required
- **macOS:** `sudo` required  
- **Windows:** Administrator required

#### Platform Support

**Clock adjustment is currently supported on Linux and macOS:**

| Platform | Support | Method | Notes |
|----------|---------|--------|-------|
| **Linux** | ✅ Full | `adjtimex()` | Supports both slew and step adjustment |
| **macOS** | ✅ Partial | `adjtime()` | Only gradual adjustment (slew) |
| **Windows** | ❌ Not yet | - | Planned for future release |
| **BSD** | ⚠️ Untested | `adjtime()` | Should work like macOS |

**Linux Features:**
- ✅ Gradual adjustment (slew) for small offsets
- ✅ Immediate adjustment (step) for large offsets
- ✅ Configurable slew threshold (default: 500ms)
- ✅ Full control over adjustment behavior

**macOS Limitations:**
- ⚠️ Only gradual adjustment (slew) available
- ⚠️ Fixed slew rate (~500 ppm, ~43 seconds per day)
- ⚠️ Slew threshold parameter ignored
- ⚠️ Large offsets still adjusted gradually (may take time)
- ℹ️ For large offsets (>1 second), consider using system tools

**Query-only mode works on all platforms:**
```bash
# Measure offset without adjusting clock (works everywhere)
./rust/target/release/tsq-datagram-client tsq.gmccollu.com --port 443
python3 tsq-stream-client.py tsq.gmccollu.com --port 8443 --dry-run
```

#### Clock Adjustment Methods

TSQ uses two methods to adjust the system clock:

**Slew (Gradual Adjustment):**
- Used for small offsets (< 500ms by default)
- Adjusts clock slowly to avoid breaking time-sensitive applications
- Takes approximately 16-17 minutes to correct a 500ms offset
- Safer for production systems

**Step (Immediate Jump):**
- Used for large offsets (> 500ms by default)
- Immediately sets clock to correct time
- Can break applications expecting monotonic time
- Necessary for large corrections

**Configurable Threshold:**
```bash
# Use more conservative 1-second threshold (like chrony)
sudo tsq-stream-client.py SERVER --slew-threshold 1000

# Use aggressive 128ms threshold (like NTP)
sudo tsq-stream-client.py SERVER --slew-threshold 128
```

**Recommendation:** The default 500ms threshold balances correction speed with application safety. For critical production systems, consider using 1000ms (1 second).

---

## Generating Certificates

### Self-Signed Certificate (Testing Only)

```bash
# Generate certificate with SAN
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout server.key -out server.crt -days 365 \
  -subj "/CN=YOUR_SERVER_IP" \
  -addext "subjectAltName=IP:YOUR_SERVER_IP"
```

**Example:**
```bash
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout server.key -out server.crt -days 365 \
  -subj "/CN=192.168.1.100" \
  -addext "subjectAltName=IP:192.168.1.100"
```

### Production Certificates

For production, use certificates from a trusted Certificate Authority (CA) like:
- Let's Encrypt (free)
- DigiCert
- Sectigo

---

## Performance

### Benchmark Results

| Protocol | RTT | Sync Duration | Encryption |
|----------|-----|---------------|------------|
| NTP | N/A | 6.30s | ❌ None |
| TSQ Streams | 1.3ms | 2.7s | ✅ TLS 1.3 |
| TSQ Datagrams | 0.9ms | 2.1s | ✅ TLS 1.3 |

**Note:** "Sync Duration" measures the time to connect, query servers (5 samples), and calculate the time offset. It does **not** include the actual clock adjustment, which happens after measurement and can be either instantaneous (step) or gradual (slew) depending on the offset size.

**Key Findings:**
- TSQ Streams: **57% faster** than NTP (2.7s vs 6.3s)
- TSQ Datagrams: **67% faster** than NTP (2.1s vs 6.3s)
- TSQ Datagrams: **31% faster** than Streams (2.1s vs 2.7s)
- TSQ Datagrams: **44% faster RTT** than Streams (0.9ms vs 1.3ms)
- Both provide full TLS 1.3 encryption

---

## Architecture

### TSQ Datagrams (Rust)

Uses QUIC **unreliable datagrams** for minimal latency:
- Single datagram request/response
- No connection overhead after initial handshake
- Ideal for high-frequency time queries
- Built with Quiche (Cloudflare's QUIC library)

### TSQ Streams (Python)

Uses QUIC **reliable streams** for guaranteed delivery:
- Stream-based request/response
- Reliable delivery with retransmission
- Better for unstable networks
- Built with aioquic

---

## Project Structure

```
TSQ/
├── README.md                          # This file
├── LICENSE                            # License file
├── FILE_NAMING_CONVENTION.md          # Naming documentation
│
├── rust/                              # Rust Datagrams implementation
│   ├── Cargo.toml                     # Rust dependencies
│   ├── src/
│   │   ├── server.rs                  # Datagram server
│   │   ├── client.rs                  # Datagram client
│   │   └── adjtime.rs                 # Clock adjustment
│   └── target/release/
│       ├── tsq-datagram-server        # Server binary
│       ├── tsq-datagram-client        # Client binary
│       └── tsq-datagram-adjtime       # Adjtime binary
│
├── tsq-stream-server.py               # Python Streams server
├── tsq-stream-client.py               # Python Streams client
│
└── docs/                              # Additional documentation
    ├── BENCHMARK_RESULTS.md
    └── IETF_DRAFT.md
```

---

## Error Handling

Both implementations include comprehensive error handling:

✅ **Input validation** - Port numbers, counts, server addresses  
✅ **Clear error messages** - Helpful feedback for users  
✅ **No crashes** - Graceful error handling throughout  
✅ **Security warnings** - Alerts when using insecure mode  

**Example error messages:**
```bash
# Invalid port
Error: Port must be between 1 and 65535

# Invalid count
Error: Count must be between 1 and 100

# Missing server
Error: At least one server must be specified
```

---

## Troubleshooting

### Server won't start

**Problem:** `Address already in use`

**Solution:** Another process is using the port
```bash
# Find what's using port 443
sudo lsof -i :443

# Kill the process
sudo pkill -9 <process-name>
```

### Client can't connect

**Problem:** `Connection refused`

**Solution:** 
1. Verify server is running: `sudo lsof -i :443`
2. Check firewall rules
3. Verify correct IP address

### TLS handshake fails

**Problem:** `TlsFail` or certificate errors

**Solution:**
1. Use `--insecure` for testing with self-signed certs
2. Verify certificate has Subject Alternative Name (SAN)
3. Check certificate matches server IP

### Clock adjustment fails

**Problem:** Permission denied

**Solution:** Run with `sudo` (Linux/Mac) or as Administrator (Windows)

---

## Server Logging

### Usage Tracking

TSQ servers log all client requests for monitoring and analysis:

**Log Format:**
```
[TSQ-LOG] 2025-11-07 18:30:45.123 UTC client=203.0.113.42 protocol=datagram status=SUCCESS processing_time=0.123ms
[TSQ-LOG] 2025-11-07 18:30:46.456 UTC client=198.51.100.10 protocol=stream status=SUCCESS processing_time=0.234ms
[TSQ-LOG] 2025-11-07 18:30:47.789 UTC client=192.0.2.5 protocol=datagram status=FAILED error="Invalid request" processing_time=N/A
```

**Logged Information:**
- Timestamp (UTC)
- Client IP address
- Protocol (datagram or stream)
- Status (SUCCESS or FAILED)
- Processing time
- Error message (if failed)

### Viewing Logs

**On systemd systems:**
```bash
# View recent logs
sudo journalctl -u tsq-datagram -u tsq-stream -n 100

# Follow logs in real-time
sudo journalctl -u tsq-datagram -u tsq-stream -f

# Filter for specific client
sudo journalctl -u tsq-datagram -u tsq-stream | grep "client=203.0.113.42"

# Show only failures
sudo journalctl -u tsq-datagram -u tsq-stream | grep "status=FAILED"
```

### Log Analysis

Use the included `analyze-logs.sh` script to generate usage statistics:

```bash
./analyze-logs.sh
```

**Output includes:**
- Total requests and success rate
- Requests by protocol (datagram vs stream)
- Unique client count
- Top clients by request volume
- Average processing time
- Daily activity breakdown
- Common error types

### Logging Limitations

**Datagram Server (Rust):**
- ✅ Logs client IP addresses
- ✅ Full per-session tracking
- ✅ Query count and duration

**Stream Server (Python):**
- ⚠️ **Cannot log client IP addresses** due to `aioquic` library limitation
- ✅ Logs session statistics (query count, duration, status)
- ✅ Still provides valuable usage data

**Note:** The `aioquic` library does not expose peer addresses through its stream handler interface. Stream server logs show aggregate statistics without client IPs. Datagram server provides full IP tracking.

### Privacy Considerations

**What we log:**
- ✅ Client IP addresses (datagrams only)
- ✅ Request timestamps
- ✅ Success/failure status
- ✅ Performance metrics
- ✅ Session statistics

**What we DON'T log:**
- ❌ No personally identifiable information
- ❌ No time offset values
- ❌ No certificate details
- ❌ No payload contents

**Note:** Logs are stored in systemd journal and rotated automatically. Consider anonymizing or aggregating IP addresses for long-term storage if privacy is a concern.

---

## Security Considerations

### Certificate Verification

**Always use proper certificate verification in production:**
- Obtain certificates from trusted CA
- Never use `--insecure` in production
- Ensure certificates have proper SANs

### Firewall Rules

Configure firewall to allow TSQ traffic:
```bash
# Linux (iptables)
sudo iptables -A INPUT -p udp --dport 443 -j ACCEPT

# Linux (firewalld)
sudo firewall-cmd --add-port=443/udp --permanent
sudo firewall-cmd --reload
```

### Time Security

- Use multiple time servers for redundancy
- Monitor for large time offsets (potential attacks)
- Use `--max-offset` to limit acceptable adjustments

---

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## License

MIT License - see LICENSE file for details

---

## Citation

If you use TSQ in research, please cite:

```
McCollum, G. (2025). TSQ: Time Synchronization over QUIC.
GitHub repository: https://github.com/gmccollu/TSQ
IETF Draft: https://datatracker.ietf.org/doc/html/draft-mccollum-ntp-tsq-01
```

---

## Contact

**Garrett McCollum**  
Email: gmccollu@cisco.com  
GitHub: @gmccollu

---

## Acknowledgments

- Protocol specification: [IETF draft-mccollum-ntp-tsq-01](https://datatracker.ietf.org/doc/html/draft-mccollum-ntp-tsq-01)
- Built with [Quiche](https://github.com/cloudflare/quiche) (Rust QUIC)
- Built with [aioquic](https://github.com/aiortc/aioquic) (Python QUIC)
- Inspired by NTP and NTS protocols

---

## Version History

### v0.1.0-beta (2025-11-06)
- Initial public release
- Rust Datagrams implementation
- Python Streams implementation
- Comprehensive error handling
- Input validation
- Security warnings
- Full documentation
