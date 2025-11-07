#!/usr/bin/env python3
"""
Analyze NTP vs TSQ measurements to determine which is more accurate
"""

print("="*70)
print("MEASUREMENT ANALYSIS: NTP vs TSQ")
print("="*70)

# Your measurements
ntp_server1 = 1287.608
ntp_server2 = 1261.322
tsq_server1 = 787.437
tsq_server2 = 761.260

# TSQ also reported RTT
tsq_rtt_server1 = 1001.355  # From your test output
tsq_rtt_server2 = 1001.450

print("\nMeasured Values:")
print("-" * 70)
print(f"{'Metric':<30} {'Server1':>15} {'Server2':>15} {'Difference':>10}")
print("-" * 70)
print(f"{'NTP Offset (ms)':<30} {ntp_server1:>15.3f} {ntp_server2:>15.3f} {abs(ntp_server1-ntp_server2):>10.3f}")
print(f"{'TSQ Offset (ms)':<30} {tsq_server1:>15.3f} {tsq_server2:>15.3f} {abs(tsq_server1-tsq_server2):>10.3f}")
print(f"{'TSQ RTT (ms)':<30} {tsq_rtt_server1:>15.3f} {tsq_rtt_server2:>15.3f} {abs(tsq_rtt_server1-tsq_rtt_server2):>10.3f}")
print("-" * 70)

# Calculate averages
avg_ntp = (ntp_server1 + ntp_server2) / 2
avg_tsq = (tsq_server1 + tsq_server2) / 2
systematic_diff = avg_ntp - avg_tsq

print(f"\n{'Average NTP offset:':<30} {avg_ntp:>15.3f} ms")
print(f"{'Average TSQ offset:':<30} {avg_tsq:>15.3f} ms")
print(f"{'Systematic difference:':<30} {systematic_diff:>15.3f} ms")

print("\n" + "="*70)
print("ANALYSIS")
print("="*70)

print("\n1. CONSISTENCY CHECK:")
print(f"   - Both servers show ~26ms difference (server1 - server2)")
print(f"   - This is consistent in both NTP and TSQ")
print(f"   - ✓ Both protocols are measuring consistently")

print("\n2. SYSTEMATIC OFFSET:")
print(f"   - NTP shows ~500ms higher offset than TSQ")
print(f"   - This is very consistent across both servers")
print(f"   - Suggests a systematic bias in one measurement")

print("\n3. RTT ANALYSIS:")
print(f"   - TSQ RTT is ~1000ms (1 second)")
print(f"   - This is very high for local network communication")
print(f"   - Suggests significant network delay or processing time")

print("\n4. LIKELY EXPLANATION:")
print(f"   The ~1 second RTT in TSQ includes:")
print(f"   - QUIC connection establishment")
print(f"   - TLS handshake overhead")
print(f"   - The 1-second sleep in TSQ client (await asyncio.sleep(1.0))")
print(f"   - Network round-trip time")

print("\n" + "="*70)
print("ROOT CAUSE IDENTIFIED")
print("="*70)
print("\n⚠️  THE TSQ CLIENT HAS A 1-SECOND SLEEP AFTER SENDING THE REQUEST!")
print("\nIn tsq_client.py line ~91:")
print("   await asyncio.sleep(1.0)  # Give server time to process")
print("\nThis artificial delay is being included in the RTT calculation,")
print("which throws off the offset calculation by ~500ms.")

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
print("\n✓ NTP measurement is MORE ACCURATE")
print("\nReasons:")
print("1. NTP doesn't have artificial delays")
print("2. NTP is a mature, well-tested protocol")
print("3. The 1-second sleep in TSQ client is contaminating the measurement")
print("\nRECOMMENDATION:")
print("Remove or significantly reduce the sleep in TSQ client to get")
print("accurate measurements. The sleep was added for debugging but")
print("should not be part of the production timing measurement.")

print("\n" + "="*70)
