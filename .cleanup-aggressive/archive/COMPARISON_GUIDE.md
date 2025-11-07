# How to Compare All Three: NTP vs Streams vs Datagrams

## Quick Steps

### 1. Start Stream Servers (2 terminals)

**Terminal 1 - Server1:**
```bash
ssh cisco@172.18.124.203
cd /home/cisco/tsq-certs
source ~/tsq-venv/bin/activate
python tsq_server.py --host 0.0.0.0 --port 443 --cert server.crt --key server.key
```

**Terminal 2 - Server2:**
```bash
ssh cisco@172.18.124.204
cd /home/cisco/tsq-certs
source ~/tsq-venv/bin/activate
python tsq_server.py --host 0.0.0.0 --port 443 --cert server.crt --key server.key
```

### 2. Run Comparison (from your Mac)

```bash
cd /Users/garrettmccollum/Desktop/TSQ
source tsq-test-venv/bin/activate
python3 compare_all_three.py
```

This will:
- Query NTP on both servers
- Query TSQ Streams on both servers
- Query TSQ Datagrams on both servers
- Show side-by-side comparison

---

## Alternative: Manual Comparison

If the script doesn't work, run these commands manually:

### Query NTP
```bash
ssh cisco@172.18.124.206
chronyc -h 14.38.117.100 tracking | grep "System time"
chronyc -h 14.38.117.200 tracking | grep "System time"
```

### Query TSQ Streams
```bash
ssh cisco@172.18.124.206
source ~/tsq-venv/bin/activate
python tsq_client.py 14.38.117.100 14.38.117.200 --port 443 --insecure --count 3
```

### Query TSQ Datagrams
```bash
ssh cisco@172.18.124.206
./tsq-client-dg 14.38.117.100 14.38.117.200 --port 443 --count 3 --insecure
```

---

## Expected Output Format

```
================================================================================
                    NTP vs TSQ Streams vs TSQ Datagrams
================================================================================

Testing server1 (14.38.117.100)...
--------------------------------------------------------------------------------
  Querying NTP... 1289.386 ms
  Querying TSQ Streams... RTT=2.123 ms, Offset=1289.642 ms
  Querying TSQ Datagrams... RTT=1.060 ms, Offset=1304.777 ms

Testing server2 (14.38.117.200)...
--------------------------------------------------------------------------------
  Querying NTP... 1263.324 ms
  Querying TSQ Streams... RTT=2.045 ms, Offset=1263.389 ms
  Querying TSQ Datagrams... RTT=1.194 ms, Offset=1278.487 ms

================================================================================
                          COMPARISON SUMMARY
================================================================================

Server          Protocol             RTT (ms)     Offset (ms)     vs NTP      
--------------------------------------------------------------------------------
server1         NTP                  N/A              1289.386   --          
                TSQ Streams            2.123          1289.642   +0.256
                TSQ Datagrams          1.060          1304.777   +15.391

server2         NTP                  N/A              1263.324   --          
                TSQ Streams            2.045          1263.389   +0.065
                TSQ Datagrams          1.194          1278.487   +15.163

================================================================================
                        PERFORMANCE COMPARISON
================================================================================

Average RTT:
  TSQ Streams:    2.084 ms
  TSQ Datagrams:  1.127 ms
  Improvement:    45.9% faster

Accuracy (vs NTP):
  server1:
    Streams:   0.256 ms difference
    Datagrams: 15.391 ms difference
  server2:
    Streams:   0.065 ms difference
    Datagrams: 15.163 ms difference
```

---

## Key Takeaways

- **Datagrams are ~46% faster** (1.1ms vs 2.1ms RTT)
- **Streams are more accurate** (0.1-0.3ms vs NTP)
- **Datagrams have larger offset** (~15ms difference vs NTP)
- **Both are encrypted** with TLS 1.3

The offset difference in datagrams might be due to the servers being the Python streams version when we tested!
