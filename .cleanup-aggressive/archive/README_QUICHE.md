# TSQ with Quiche - QUIC Datagrams Implementation

## Overview

This adds QUIC Datagram support to TSQ using Cloudflare's Quiche library, while keeping the working QUIC Streams implementation intact.

## Current Status

### ✅ QUIC Streams (aioquic) - PRODUCTION READY
- **Files**: `tsq_server.py`, `tsq_client.py`
- **Status**: Fully working and validated
- **Accuracy**: Matches NTP within 0.066-0.256ms
- **RTT**: ~2ms
- **Command**: `python3 tsq_test_runner.py test`

### 🚧 QUIC Datagrams (quiche) - IN PROGRESS
- **Files**: `tsq_server_quiche.py`, `tsq_client_quiche.py` (to be created)
- **Status**: Infrastructure ready, implementation pending
- **Expected improvement**: 0.5-1ms lower latency
- **Command**: `python3 tsq_test_runner.py test_quiche` (once implemented)

## Installation Steps

### 1. Install Quiche

Run the installation script on each machine (servers and client):

```bash
cd /Users/garrettmccollum/Desktop/TSQ
./install_quiche.sh
```

This will:
- Install Rust (if needed)
- Install build dependencies
- Clone and build Quiche
- Create library symlinks

**Time required**: 5-10 minutes per machine

### 2. Verify Installation

```bash
python3 quiche_wrapper.py
```

You should see:
```
✓ Quiche library loaded successfully
  Library path: /usr/local/lib/libquiche.so
```

### 3. Deploy to Test Machines

Once quiche is installed on all machines, the test runner will deploy the quiche-based TSQ files automatically.

## Next Steps

1. **Install quiche on all test machines**:
   ```bash
   # On your Mac
   ./install_quiche.sh
   
   # On each server (via SSH)
   ssh cisco@172.18.124.203 'bash -s' < install_quiche.sh
   ssh cisco@172.18.124.204 'bash -s' < install_quiche.sh
   ssh cisco@172.18.124.206 'bash -s' < install_quiche.sh
   ```

2. **Implement quiche-based TSQ** (next task):
   - Create `tsq_server_quiche.py`
   - Create `tsq_client_quiche.py`
   - Add to test runner

3. **Compare performance**:
   - Run streams version: `python3 tsq_test_runner.py test`
   - Run datagram version: `python3 tsq_test_runner.py test_quiche`
   - Compare RTT and accuracy

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    TSQ Implementation                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  QUIC Streams (aioquic)          QUIC Datagrams (quiche)│
│  ✓ Production Ready              🚧 In Progress         │
│  ✓ ~2ms RTT                      Expected: ~1ms RTT     │
│  ✓ Reliable                      Unreliable (faster)    │
│                                                          │
│  tsq_server.py                   tsq_server_quiche.py   │
│  tsq_client.py                   tsq_client_quiche.py   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Files

- `QUICHE_SETUP.md` - Detailed setup instructions
- `install_quiche.sh` - Automated installation script
- `quiche_wrapper.py` - Python wrapper for Quiche C API
- `tsq_server_quiche.py` - TSQ server using Quiche datagrams (to be created)
- `tsq_client_quiche.py` - TSQ client using Quiche datagrams (to be created)

## Benefits of Quiche Datagrams

1. **Lower latency**: No retransmission overhead
2. **More like NTP**: Unreliable datagrams (like UDP)
3. **Production-ready**: Used by Cloudflare at scale
4. **Better API**: Explicit datagram support

## Trade-offs

- **Complexity**: Requires Rust toolchain and C FFI
- **Reliability**: Datagrams can be lost (but that's acceptable for time sync)
- **Maintenance**: Two implementations to maintain

## Recommendation

- **Use Streams version for production** (already validated)
- **Use Datagrams version for research/comparison**
- Both implementations will coexist peacefully

---

Ready to proceed? Run `./install_quiche.sh` to get started!
