#!/usr/bin/env python3
"""
TSQ Time Adjustment Tool
Similar to ntpdate but using TSQ (Time Synchronization over QUIC)

Queries TSQ servers, calculates offset, and adjusts system clock.
"""
import asyncio
import struct
import time
import os
import sys
import argparse
import statistics
from datetime import datetime
import ctypes
import ctypes.util
import platform

# aioquic imports
from aioquic.asyncio.client import connect
from aioquic.quic.configuration import QuicConfiguration

# Detect OS
IS_LINUX = platform.system() == 'Linux'
IS_MACOS = platform.system() == 'Darwin'

# Linux timex structure for adjtimex
class Timex(ctypes.Structure):
    _fields_ = [
        ("modes", ctypes.c_uint),
        ("offset", ctypes.c_long),
        ("freq", ctypes.c_long),
        ("maxerror", ctypes.c_long),
        ("esterror", ctypes.c_long),
        ("status", ctypes.c_int),
        ("constant", ctypes.c_long),
        ("precision", ctypes.c_long),
        ("tolerance", ctypes.c_long),
        ("time", ctypes.c_long * 2),
        ("tick", ctypes.c_long),
        ("ppsfreq", ctypes.c_long),
        ("jitter", ctypes.c_long),
        ("shift", ctypes.c_int),
        ("stabil", ctypes.c_long),
        ("jitcnt", ctypes.c_long),
        ("calcnt", ctypes.c_long),
        ("errcnt", ctypes.c_long),
        ("stbcnt", ctypes.c_long),
        ("tai", ctypes.c_int),
        ("_padding", ctypes.c_int * 11),
    ]

# macOS timeval structure for adjtime
class Timeval(ctypes.Structure):
    _fields_ = [
        ("tv_sec", ctypes.c_long),
        ("tv_usec", ctypes.c_long),
    ]

# adjtimex modes
ADJ_OFFSET = 0x0001
ADJ_FREQUENCY = 0x0002
ADJ_MAXERROR = 0x0004
ADJ_ESTERROR = 0x0008
ADJ_STATUS = 0x0010
ADJ_TIMECONST = 0x0020
ADJ_SETOFFSET = 0x0100
ADJ_MICRO = 0x1000
ADJ_NANO = 0x2000

class TSQAdjTime:
    def __init__(self, servers, port=443, insecure=False, queries=5, max_offset_ms=1000, 
                 slew_threshold_ms=128, dry_run=False, verbose=False):
        self.servers = servers
        self.port = port
        self.insecure = insecure
        self.queries = queries
        self.max_offset_ms = max_offset_ms
        self.slew_threshold_ms = slew_threshold_ms
        self.dry_run = dry_run
        self.verbose = verbose
        self.start_time = None
        self.end_time = None
        
    def log(self, message, level="INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{level}] {message}")
    
    async def query_tsq_server(self, server_ip):
        """Query a single TSQ server"""
        try:
            cfg = QuicConfiguration(is_client=True, alpn_protocols=["tsq/1"])
            if self.insecure:
                cfg.verify_mode = False
            
            async with connect(server_ip, self.port, configuration=cfg) as client:
                nonce = os.urandom(16)
                request = struct.pack("!BB", 1, 16) + nonce
                
                reader, writer = await client.create_stream()
                writer.write(request)
                t1 = time.time_ns()
                await writer.drain()
                
                response_data = await asyncio.wait_for(reader.read(100), timeout=3.0)
                t4 = time.time_ns()
                
                if len(response_data) == 0:
                    return None, None
                
                # Parse TLV response
                offset = 0
                t2_ntp = None
                t3_ntp = None
                
                while offset < len(response_data):
                    if offset + 2 > len(response_data):
                        break
                    tlv_type = response_data[offset]
                    tlv_len = response_data[offset + 1]
                    tlv_val = response_data[offset + 2:offset + 2 + tlv_len]
                    
                    if tlv_type == 2:
                        t2_ntp = tlv_val
                    elif tlv_type == 3:
                        t3_ntp = tlv_val
                    
                    offset += 2 + tlv_len
                
                if not t2_ntp or not t3_ntp:
                    return None, None
                
                # Convert NTP timestamps to nanoseconds
                NTP_EPOCH_OFFSET = 2208988800
                ntp_seconds, ntp_fraction = struct.unpack("!II", t2_ntp)
                t2 = (ntp_seconds - NTP_EPOCH_OFFSET) * 1_000_000_000 + int((ntp_fraction * 1_000_000_000) / 2**32)
                
                ntp_seconds, ntp_fraction = struct.unpack("!II", t3_ntp)
                t3 = (ntp_seconds - NTP_EPOCH_OFFSET) * 1_000_000_000 + int((ntp_fraction * 1_000_000_000) / 2**32)
                
                # Calculate offset and RTT
                rtt_ns = (t4 - t1) - (t3 - t2)
                offset_ns = ((t2 - t1) + (t3 - t4)) // 2
                
                writer.close()
                return offset_ns / 1e6, rtt_ns / 1e6  # Convert to ms
                
        except Exception as e:
            if self.verbose:
                self.log(f"Error querying {server_ip}: {e}", "ERROR")
            return None, None
    
    async def measure_offsets(self):
        """Query all servers multiple times and collect offsets"""
        self.log(f"Querying {len(self.servers)} server(s), {self.queries} times each...")
        
        all_offsets = []
        all_rtts = []
        
        for query_num in range(self.queries):
            if self.verbose:
                self.log(f"Query round {query_num + 1}/{self.queries}")
            
            for server in self.servers:
                offset, rtt = await self.query_tsq_server(server)
                if offset is not None:
                    all_offsets.append(offset)
                    all_rtts.append(rtt)
                    if self.verbose:
                        self.log(f"  {server}: offset={offset:.3f}ms, rtt={rtt:.3f}ms")
                else:
                    self.log(f"  {server}: FAILED", "WARN")
            
            # Small delay between rounds
            if query_num < self.queries - 1:
                await asyncio.sleep(0.5)
        
        return all_offsets, all_rtts
    
    def calculate_adjustment(self, offsets, rtts):
        """Calculate the time adjustment to apply"""
        if not offsets:
            raise ValueError("No valid measurements received")
        
        # Use median to reject outliers
        median_offset = statistics.median(offsets)
        stdev_offset = statistics.stdev(offsets) if len(offsets) > 1 else 0
        median_rtt = statistics.median(rtts)
        
        self.log(f"Measurements: {len(offsets)} samples")
        self.log(f"  Offset: median={median_offset:.3f}ms, stdev={stdev_offset:.3f}ms")
        self.log(f"  RTT: median={median_rtt:.3f}ms")
        
        # Check if offset is within acceptable range
        if abs(median_offset) > self.max_offset_ms:
            raise ValueError(f"Offset too large: {median_offset:.3f}ms (max: {self.max_offset_ms}ms)")
        
        return median_offset, stdev_offset
    
    def adjust_clock(self, offset_ms):
        """Adjust system clock by offset_ms milliseconds"""
        if self.dry_run:
            self.log(f"DRY RUN: Would adjust clock by {offset_ms:.3f}ms")
            return True
        
        try:
            if IS_LINUX:
                return self._adjust_clock_linux(offset_ms)
            elif IS_MACOS:
                return self._adjust_clock_macos(offset_ms)
            else:
                self.log(f"Unsupported OS: {platform.system()}", "ERROR")
                self.log("Clock adjustment only supported on Linux and macOS", "ERROR")
                return False
        except Exception as e:
            self.log(f"Error adjusting clock: {e}", "ERROR")
            return False
    
    def _adjust_clock_linux(self, offset_ms):
        """Adjust clock on Linux using adjtimex"""
        # Convert ms to microseconds for adjtimex
        offset_us = int(offset_ms * 1000)
        
        # Determine if we should slew or step
        if abs(offset_ms) <= self.slew_threshold_ms:
            # Slew (gradual adjustment)
            self.log(f"Slewing clock by {offset_ms:.3f}ms (gradual adjustment)")
            
            libc = ctypes.CDLL(ctypes.util.find_library("c"))
            tx = Timex()
            tx.modes = ADJ_OFFSET | ADJ_MICRO
            tx.offset = offset_us
            
            result = libc.adjtimex(ctypes.byref(tx))
            if result == -1:
                self.log("Failed to adjust clock via adjtimex", "ERROR")
                return False
            
            self.log(f"Clock slewed successfully (will adjust gradually)")
            
        else:
            # Step (immediate adjustment)
            self.log(f"Stepping clock by {offset_ms:.3f}ms (immediate adjustment)")
            
            # Use settimeofday for immediate step
            import subprocess
            offset_sec = offset_ms / 1000.0
            result = subprocess.run(
                ["date", "-s", f"@{time.time() + offset_sec}"],
                capture_output=True
            )
            
            if result.returncode != 0:
                self.log(f"Failed to step clock: {result.stderr.decode()}", "ERROR")
                return False
            
            self.log(f"Clock stepped successfully")
        
        return True
    
    def _adjust_clock_macos(self, offset_ms):
        """Adjust clock on macOS using adjtime"""
        # macOS only supports slew (gradual adjustment)
        # The slew_threshold parameter is ignored on macOS
        
        if abs(offset_ms) > self.slew_threshold_ms:
            self.log(f"Note: macOS only supports gradual adjustment (slew)", "WARN")
            self.log(f"Large offset of {offset_ms:.3f}ms will be adjusted gradually", "WARN")
        
        self.log(f"Slewing clock by {offset_ms:.3f}ms (gradual adjustment)")
        
        # Convert ms to seconds and microseconds
        offset_sec = int(offset_ms / 1000)
        offset_usec = int((offset_ms % 1000) * 1000)
        
        libc = ctypes.CDLL(ctypes.util.find_library("c"))
        
        # Create delta timeval
        delta = Timeval()
        delta.tv_sec = offset_sec
        delta.tv_usec = offset_usec
        
        # Create olddelta timeval (we don't use it but adjtime requires it)
        olddelta = Timeval()
        
        # Call adjtime
        result = libc.adjtime(ctypes.byref(delta), ctypes.byref(olddelta))
        if result == -1:
            self.log("Failed to adjust clock via adjtime", "ERROR")
            return False
        
        self.log(f"Clock slewed successfully (will adjust gradually)")
        self.log(f"Note: macOS slew rate is fixed at ~500 ppm", "INFO")
        
        return True
    
    async def sync(self):
        """Main synchronization routine"""
        self.start_time = time.time()
        self.log("="*70)
        self.log("TSQ Time Synchronization Starting")
        self.log("="*70)
        self.log(f"Servers: {', '.join(self.servers)}")
        self.log(f"Port: {self.port}")
        self.log(f"Queries per server: {self.queries}")
        self.log(f"Max offset: {self.max_offset_ms}ms")
        self.log(f"Slew threshold: {self.slew_threshold_ms}ms")
        if self.dry_run:
            self.log("DRY RUN MODE - No actual clock adjustment", "WARN")
        self.log("")
        
        try:
            # Measure offsets
            offsets, rtts = await self.measure_offsets()
            
            if not offsets:
                self.log("No valid measurements received", "ERROR")
                return False
            
            self.log("")
            
            # Calculate adjustment
            offset_ms, stdev_ms = self.calculate_adjustment(offsets, rtts)
            
            self.log("")
            self.log(f"Calculated adjustment: {offset_ms:.3f}ms ± {stdev_ms:.3f}ms")
            
            # Apply adjustment
            success = self.adjust_clock(offset_ms)
            
            self.end_time = time.time()
            duration = (self.end_time - self.start_time) * 1000
            
            self.log("")
            self.log("="*70)
            if success:
                self.log("TSQ Time Synchronization COMPLETED", "SUCCESS")
            else:
                self.log("TSQ Time Synchronization FAILED", "ERROR")
            self.log(f"Total sync duration: {duration:.1f}ms")
            self.log("="*70)
            
            return success
            
        except Exception as e:
            self.end_time = time.time()
            duration = (self.end_time - self.start_time) * 1000
            
            self.log("")
            self.log("="*70)
            self.log(f"TSQ Time Synchronization FAILED: {e}", "ERROR")
            self.log(f"Total sync duration: {duration:.1f}ms")
            self.log("="*70)
            return False

async def main():
    parser = argparse.ArgumentParser(
        description="TSQ Time Adjustment Tool - Synchronize system clock using TSQ"
    )
    parser.add_argument("servers", nargs="+", help="TSQ server IP addresses")
    parser.add_argument("--port", type=int, default=443, help="Server port (default: 443)")
    parser.add_argument("--insecure", action="store_true", help="Skip certificate verification")
    parser.add_argument("--queries", type=int, default=5, help="Queries per server (default: 5)")
    parser.add_argument("--max-offset", type=float, default=1000, 
                        help="Maximum allowed offset in ms (default: 1000)")
    parser.add_argument("--slew-threshold", type=float, default=500,
                        help="Threshold for slew vs step in ms (default: 500)")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually adjust clock")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.port < 1 or args.port > 65535:
        print("Error: Port must be between 1 and 65535", file=sys.stderr)
        sys.exit(1)
    
    if args.queries < 1 or args.queries > 100:
        print("Error: Queries must be between 1 and 100", file=sys.stderr)
        sys.exit(1)
    
    if not args.servers:
        print("Error: At least one server must be specified", file=sys.stderr)
        sys.exit(1)
    
    # Warn about insecure mode
    if args.insecure:
        print("WARNING: Certificate verification disabled!", file=sys.stderr)
        print("WARNING: Use only for testing. Connection is vulnerable to MITM attacks.", file=sys.stderr)
        print(file=sys.stderr)
    
    adjtime = TSQAdjTime(
        servers=args.servers,
        port=args.port,
        insecure=args.insecure,
        queries=args.queries,
        max_offset_ms=args.max_offset,
        slew_threshold_ms=args.slew_threshold,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    success = await adjtime.sync()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
