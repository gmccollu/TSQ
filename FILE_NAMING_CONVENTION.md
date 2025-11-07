# TSQ File Naming Convention

**Date**: November 6, 2025  
**Status**: ✅ Complete

---

## File Naming Structure

All TSQ files now follow a clear naming convention that indicates:
1. **Protocol type** (datagram vs stream)
2. **Role** (client vs server)
3. **Implementation language** (implied by extension)

---

## Rust Datagrams (QUIC Datagrams)

### Binaries
- **`tsq-datagram-server`** - Datagram server (Rust/Quiche)
- **`tsq-datagram-client`** - Datagram client (Rust/Quiche)
- **`tsq-datagram-adjtime`** - Datagram client with clock adjustment (Rust/Quiche)

### Source Files
- `rust/src/server.rs` → builds `tsq-datagram-server`
- `rust/src/client.rs` → builds `tsq-datagram-client`
- `rust/src/adjtime.rs` → builds `tsq-datagram-adjtime`

### Build
```bash
cd rust
cargo build --release
```

Binaries output to: `rust/target/release/`

---

## Python Streams (QUIC Streams)

### Scripts
- **`tsq-stream-server.py`** - Stream server (Python/aioquic)
- **`tsq-stream-client.py`** - Stream client with clock adjustment (Python/aioquic)

### Usage
```bash
# Server
python3 tsq-stream-server.py --host 0.0.0.0 --port 443 --cert server.crt --key server.key

# Client
python3 tsq-stream-client.py SERVER_IP --insecure --dry-run
```

---

## Quick Reference

| Old Name | New Name | Type |
|----------|----------|------|
| `tsq-server` | `tsq-datagram-server` | Rust binary |
| `tsq-client` | `tsq-datagram-client` | Rust binary |
| `tsq-adjtime` | `tsq-datagram-adjtime` | Rust binary |
| `tsq_server.py` | `tsq-stream-server.py` | Python script |
| `tsq_adjtime.py` | `tsq-stream-client.py` | Python script |

---

## Benefits

✅ **Clear protocol identification** - Immediately know if it's datagram or stream  
✅ **Clear role identification** - Immediately know if it's client or server  
✅ **Consistent naming** - All files follow the same pattern  
✅ **Future-proof** - Easy to add new implementations (e.g., `tsq-hybrid-client`)  

---

## Directory Structure

```
TSQ/
├── rust/
│   ├── src/
│   │   ├── server.rs          # Datagram server source
│   │   ├── client.rs          # Datagram client source
│   │   └── adjtime.rs         # Datagram adjtime source
│   ├── Cargo.toml             # Updated with new binary names
│   └── target/release/
│       ├── tsq-datagram-server
│       ├── tsq-datagram-client
│       └── tsq-datagram-adjtime
├── tsq-stream-server.py       # Stream server
└── tsq-stream-client.py       # Stream client
```

---

## Testing Commands

### Datagram Test
```bash
# Server
./rust/target/release/tsq-datagram-server --listen 0.0.0.0:443 --cert server.crt --key server.key

# Client
./rust/target/release/tsq-datagram-client SERVER_IP --insecure --count 3
```

### Stream Test
```bash
# Server
python3 tsq-stream-server.py --host 0.0.0.0 --port 443 --cert server.crt --key server.key

# Client
python3 tsq-stream-client.py SERVER_IP --insecure --dry-run
```

---

## Notes

- All binaries/scripts have been renamed
- All functionality remains the same
- All code fixes are preserved
- Both implementations tested and working
- Ready for GitHub release with clear naming
