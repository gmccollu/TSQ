# TSQ Documentation Index

Complete documentation for TSQ (Time Synchronization over QUIC) implementation and benchmarks.

---

## Quick Start

**Want to sync your clock?**
- Streams: `python3 run_tsq_sync.py --live`
- Datagrams: `sudo ./tsq-adjtime-dg SERVER1 SERVER2`

**Want to see the comparison?**
- `python3 test_ntp_sync.py --compare`

---

## Core Documentation

### 1. README.md
**Main project overview**
- Quick start guide
- Core files listing
- Performance results summary
- Setup instructions
- Usage examples

### 2. TSQ_CLOCK_SYNC_COMPLETE.md
**Complete implementation details**
- Architecture overview
- Performance comparison (NTP vs Streams vs Datagrams)
- Usage guide with all options
- Clock adjustment methods (slew vs step)
- Safety features
- Comparison with NTP

### 3. BENCHMARK_RESULTS.md
**Detailed benchmark analysis**
- Test environment
- Complete benchmark results
- Performance analysis
- Security comparison
- Use case recommendations
- Reproducibility instructions

### 4. SESSION_SUMMARY.md
**Development session overview**
- What was accomplished
- Technical highlights
- Historic achievements
- Lessons learned
- Statistics

### 5. FINAL_COMPARISON.txt
**Visual comparison chart**
- Side-by-side comparison
- Visual bar charts
- Key achievements
- Quick reference

---

## Implementation Files

### Python (Streams)
- `tsq_server.py` - Server implementation
- `tsq_client.py` - Client implementation
- `tsq_adjtime.py` - Clock sync tool
- `run_tsq_sync.py` - Remote sync wrapper

### Rust (Datagrams)
- `rust/src/server.rs` - Server implementation
- `rust/src/client.rs` - Client implementation
- `rust/src/adjtime.rs` - Clock sync tool
- `rust/Cargo.toml` - Dependencies

---

## Testing & Utilities

### Testing Scripts
- `compare_all.py` - Complete comparison (NTP vs Streams vs Datagrams)
- `test_ntp_sync.py` - NTP sync testing and comparison
- `tsq_test_runner.py` - Test automation for streams
- `test_adjtime.py` - Clock sync testing

### Utilities
- `kill_servers.py` - Stop all TSQ servers
- `check_status.py` - Check server status
- `deploy_adjtime_dg.py` - Deploy datagram binaries

---

## IETF Drafts

### Specifications
- `draft-mccollum-ntp-tsq-01.xml` - Latest IETF draft (XML)
- `draft-mccollum-ntp-tsq-01.txt` - Latest IETF draft (text)
- `draft-mccollum-ntp-tsq-01.html` - Latest IETF draft (HTML)

---

## Key Results Summary

### Performance
- **TSQ Datagrams**: 67% faster than NTP (2.06s vs 6.30s)
- **TSQ Streams**: 48% faster than NTP (3.27s vs 6.30s)
- **Datagrams RTT**: 0.009ms (149x faster than streams)

### Security
- ✅ Full TLS 1.3 encryption (NTP has none)
- ✅ Server authentication
- ✅ Forward secrecy

### Accuracy
- ✅ Sub-2ms accuracy (comparable to NTP)
- ✅ Outlier rejection (10 queries vs NTP's ~4)

---

## File Organization

```
TSQ/
├── README.md                           # Main overview
├── TSQ_CLOCK_SYNC_COMPLETE.md         # Complete implementation guide
├── BENCHMARK_RESULTS.md                # Detailed benchmarks
├── SESSION_SUMMARY.md                  # Development session summary
├── FINAL_COMPARISON.txt                # Visual comparison
├── DOCUMENTATION_INDEX.md              # This file
│
├── Implementation/
│   ├── tsq_server.py                   # Streams server
│   ├── tsq_client.py                   # Streams client
│   ├── tsq_adjtime.py                  # Streams clock sync
│   └── rust/
│       ├── src/
│       │   ├── server.rs               # Datagrams server
│       │   ├── client.rs               # Datagrams client
│       │   └── adjtime.rs              # Datagrams clock sync
│       └── Cargo.toml
│
├── Testing/
│   ├── compare_all.py                  # Complete comparison
│   ├── test_ntp_sync.py                # NTP testing
│   ├── tsq_test_runner.py              # Test automation
│   └── test_adjtime.py                 # Clock sync testing
│
├── Utilities/
│   ├── run_tsq_sync.py                 # Remote sync wrapper
│   ├── kill_servers.py                 # Stop servers
│   ├── check_status.py                 # Check status
│   └── deploy_adjtime_dg.py            # Deploy binaries
│
└── Specifications/
    ├── draft-mccollum-ntp-tsq-01.xml
    ├── draft-mccollum-ntp-tsq-01.txt
    └── draft-mccollum-ntp-tsq-01.html
```

---

## Reading Order

### For Quick Overview
1. README.md
2. FINAL_COMPARISON.txt
3. BENCHMARK_RESULTS.md

### For Implementation Details
1. TSQ_CLOCK_SYNC_COMPLETE.md
2. Source code (Python or Rust)
3. IETF draft specification

### For Development Context
1. SESSION_SUMMARY.md
2. TSQ_CLOCK_SYNC_COMPLETE.md

---

## Key Achievements

✅ **First successful clock sync using QUIC datagrams**
✅ **Faster than NTP** (48-67% improvement)
✅ **Full TLS 1.3 encryption** (NTP has none)
✅ **Sub-2ms accuracy** (comparable to NTP)
✅ **Production-ready** implementations in Python and Rust

---

## Contact & Contributions

**Author:** Garrett McCollum
**Date:** November 6, 2025
**Status:** ✅ Complete and Working

For questions or contributions, refer to the IETF draft or source code.

---

## Version History

- **v1.0** (Nov 6, 2025) - Initial release
  - TSQ Streams implementation (Python)
  - TSQ Datagrams implementation (Rust)
  - Clock synchronization tools
  - Complete benchmarks vs NTP
  - Full documentation

---

**Last Updated:** November 6, 2025
