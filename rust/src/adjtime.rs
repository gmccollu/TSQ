// TSQ Time Adjustment Tool - Datagrams Version
// Synchronize system clock using TSQ QUIC Datagrams

use std::net::{SocketAddr, ToSocketAddrs, UdpSocket};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use quiche::ConnectionId;
use ring::rand::*;

const MAX_DATAGRAM_SIZE: usize = 1350;
const NTP_EPOCH_OFFSET: u64 = 2208988800;

struct TSQAdjTime {
    servers: Vec<String>,
    port: u16,
    queries: usize,
    max_offset_ms: f64,
    slew_threshold_ms: f64,
    dry_run: bool,
    verbose: bool,
}

#[derive(Debug)]
struct Measurement {
    offset_ms: f64,
    rtt_ms: f64,
}

impl TSQAdjTime {
    fn new(servers: Vec<String>, port: u16, queries: usize, max_offset_ms: f64, 
           slew_threshold_ms: f64, dry_run: bool, verbose: bool) -> Self {
        TSQAdjTime {
            servers,
            port,
            queries,
            max_offset_ms,
            slew_threshold_ms,
            dry_run,
            verbose,
        }
    }

    fn log(&self, level: &str, message: &str) {
        let now = chrono::Local::now();
        println!("[{}] [{}] {}", now.format("%Y-%m-%d %H:%M:%S%.3f"), level, message);
    }

    fn query_server(&self, server: &str) -> Result<Measurement, String> {
        // Bind local socket
        let socket = UdpSocket::bind("0.0.0.0:0")
            .map_err(|e| format!("Failed to bind socket: {}", e))?;
        socket.set_nonblocking(true)
            .map_err(|e| format!("Failed to set nonblocking: {}", e))?;

        // Resolve hostname to IP address
        let peer_addr: SocketAddr = format!("{}:{}", server, self.port)
            .to_socket_addrs()
            .map_err(|e| format!("Failed to resolve hostname: {}", e))?
            .next()
            .ok_or_else(|| format!("No addresses found for {}", server))?;

        // Create QUIC config
        let mut config = quiche::Config::new(quiche::PROTOCOL_VERSION)
            .map_err(|e| format!("Failed to create config: {}", e))?;
        
        config.verify_peer(false);
        config.set_application_protos(&[b"tsq/1"])
            .map_err(|e| format!("Failed to set ALPN: {}", e))?;
        config.set_max_idle_timeout(5000);
        config.set_max_recv_udp_payload_size(MAX_DATAGRAM_SIZE);
        config.set_max_send_udp_payload_size(MAX_DATAGRAM_SIZE);
        config.set_initial_max_data(10);
        config.set_initial_max_stream_data_bidi_local(10);
        config.set_initial_max_stream_data_bidi_remote(10);
        config.set_initial_max_streams_bidi(1);
        config.set_initial_max_streams_uni(1);
        config.enable_dgram(true, 1000, 1000);

        // Generate connection IDs
        let mut scid = [0; quiche::MAX_CONN_ID_LEN];
        SystemRandom::new().fill(&mut scid).unwrap();
        let scid = ConnectionId::from_ref(&scid);

        let local_addr: SocketAddr = socket.local_addr()
            .map_err(|e| format!("Failed to get local addr: {}", e))?;

        // Create connection
        let mut conn = quiche::connect(None, &scid, local_addr, peer_addr, &mut config)
            .map_err(|e| format!("Failed to create connection: {}", e))?;

        let mut out = [0; MAX_DATAGRAM_SIZE];
        let mut buf = [0; 65535];

        // Send initial packet
        let (write, _) = conn.send(&mut out)
            .map_err(|e| format!("Failed to send initial: {}", e))?;
        socket.send_to(&out[..write], peer_addr)
            .map_err(|e| format!("Failed to send to peer: {}", e))?;

        let start = Instant::now();
        let timeout = Duration::from_secs(5);
        let mut t1_ns = 0u128;
        let mut t4_ns = 0u128;
        let mut response_received = false;

        // Main event loop
        while start.elapsed() < timeout {
            // Try to receive
            match socket.recv_from(&mut buf) {
                Ok((len, from)) => {
                    if from == peer_addr {
                        let recv_info = quiche::RecvInfo {
                            to: local_addr,
                            from,
                        };
                        
                        match conn.recv(&mut buf[..len], recv_info) {
                            Ok(_) => {},
                            Err(e) => {
                                if self.verbose {
                                    eprintln!("recv failed: {:?}", e);
                                }
                            }
                        }
                    }
                }
                Err(ref e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                    // No data available
                }
                Err(e) => {
                    return Err(format!("recv_from failed: {}", e));
                }
            }

            // Check if connection is established
            if conn.is_established() && !response_received {
                // Send TSQ request via datagram
                let nonce: [u8; 16] = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                                       0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10];
                let mut request = vec![1u8, 16u8];
                request.extend_from_slice(&nonce);

                t1_ns = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
                
                match conn.dgram_send(&request) {
                    Ok(_) => {
                        if self.verbose {
                            eprintln!("Sent TSQ request");
                        }
                    }
                    Err(e) => {
                        return Err(format!("Failed to send datagram: {}", e));
                    }
                }
            }

            // Check for datagram response
            let mut dgram_buf = [0u8; 1350];
            if let Ok(len) = conn.dgram_recv(&mut dgram_buf) {
                t4_ns = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
                response_received = true;

                // Parse response
                if let Some((offset_ms, rtt_ms)) = self.parse_response(&dgram_buf[..len], t1_ns, t4_ns) {
                    return Ok(Measurement { offset_ms, rtt_ms });
                }
            }

            // Send outgoing packets
            loop {
                match conn.send(&mut out) {
                    Ok((write, _)) => {
                        socket.send_to(&out[..write], peer_addr).ok();
                    }
                    Err(quiche::Error::Done) => break,
                    Err(e) => {
                        return Err(format!("send failed: {:?}", e));
                    }
                }
            }

            std::thread::sleep(Duration::from_millis(1));
        }

        Err("Timeout waiting for response".to_string())
    }

    fn parse_response(&self, data: &[u8], t1_ns: u128, t4_ns: u128) -> Option<(f64, f64)> {
        let mut offset = 0;
        let mut t2_ntp: Option<(u32, u32)> = None;
        let mut t3_ntp: Option<(u32, u32)> = None;

        while offset + 2 <= data.len() {
            let tlv_type = data[offset];
            let tlv_len = data[offset + 1] as usize;
            
            if offset + 2 + tlv_len > data.len() {
                break;
            }

            let tlv_val = &data[offset + 2..offset + 2 + tlv_len];

            if tlv_type == 2 && tlv_len == 8 {
                let seconds = u32::from_be_bytes([tlv_val[0], tlv_val[1], tlv_val[2], tlv_val[3]]);
                let fraction = u32::from_be_bytes([tlv_val[4], tlv_val[5], tlv_val[6], tlv_val[7]]);
                t2_ntp = Some((seconds, fraction));
            } else if tlv_type == 3 && tlv_len == 8 {
                let seconds = u32::from_be_bytes([tlv_val[0], tlv_val[1], tlv_val[2], tlv_val[3]]);
                let fraction = u32::from_be_bytes([tlv_val[4], tlv_val[5], tlv_val[6], tlv_val[7]]);
                t3_ntp = Some((seconds, fraction));
            }

            offset += 2 + tlv_len;
        }

        if let (Some((t2_sec, t2_frac)), Some((t3_sec, t3_frac))) = (t2_ntp, t3_ntp) {
            // Convert NTP timestamps to nanoseconds
            let t2_ns = ((t2_sec as u64 - NTP_EPOCH_OFFSET) as u128) * 1_000_000_000
                + ((t2_frac as u128 * 1_000_000_000) / (1u128 << 32));
            let t3_ns = ((t3_sec as u64 - NTP_EPOCH_OFFSET) as u128) * 1_000_000_000
                + ((t3_frac as u128 * 1_000_000_000) / (1u128 << 32));

            let rtt_ns = (t4_ns - t1_ns) as i128 - (t3_ns as i128 - t2_ns as i128);
            let offset_ns = ((t2_ns as i128 - t1_ns as i128) + (t3_ns as i128 - t4_ns as i128)) / 2;

            let rtt_ms = rtt_ns as f64 / 1_000_000.0;
            let offset_ms = offset_ns as f64 / 1_000_000.0;

            return Some((offset_ms, rtt_ms));
        }

        None
    }

    fn measure_offsets(&self) -> Result<Vec<Measurement>, String> {
        self.log("INFO", &format!("Querying {} server(s), {} times each...", 
                                  self.servers.len(), self.queries));
        
        let mut measurements = Vec::new();

        for query_num in 0..self.queries {
            if self.verbose {
                self.log("INFO", &format!("Query round {}/{}", query_num + 1, self.queries));
            }

            for server in &self.servers {
                match self.query_server(server) {
                    Ok(m) => {
                        if self.verbose {
                            self.log("INFO", &format!("  {}: offset={:.3}ms, rtt={:.3}ms", 
                                                     server, m.offset_ms, m.rtt_ms));
                        }
                        measurements.push(m);
                    }
                    Err(e) => {
                        self.log("WARN", &format!("  {}: FAILED - {}", server, e));
                    }
                }
            }

            if query_num < self.queries - 1 {
                std::thread::sleep(Duration::from_millis(500));
            }
        }

        if measurements.is_empty() {
            return Err("No valid measurements received".to_string());
        }

        Ok(measurements)
    }

    fn calculate_adjustment(&self, measurements: &[Measurement]) -> Result<(f64, f64), String> {
        let mut offsets: Vec<f64> = measurements.iter().map(|m| m.offset_ms).collect();
        let rtts: Vec<f64> = measurements.iter().map(|m| m.rtt_ms).collect();

        offsets.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let median_offset = if offsets.len() % 2 == 0 {
            (offsets[offsets.len() / 2 - 1] + offsets[offsets.len() / 2]) / 2.0
        } else {
            offsets[offsets.len() / 2]
        };

        let mean_offset: f64 = offsets.iter().sum::<f64>() / offsets.len() as f64;
        let variance: f64 = offsets.iter()
            .map(|x| (x - mean_offset).powi(2))
            .sum::<f64>() / offsets.len() as f64;
        let stdev_offset = variance.sqrt();

        let mut sorted_rtts = rtts.clone();
        sorted_rtts.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let median_rtt = if sorted_rtts.len() % 2 == 0 {
            (sorted_rtts[sorted_rtts.len() / 2 - 1] + sorted_rtts[sorted_rtts.len() / 2]) / 2.0
        } else {
            sorted_rtts[sorted_rtts.len() / 2]
        };

        self.log("INFO", "");
        self.log("INFO", &format!("Measurements: {} samples", measurements.len()));
        self.log("INFO", &format!("  Offset: median={:.3}ms, stdev={:.3}ms", 
                                  median_offset, stdev_offset));
        self.log("INFO", &format!("  RTT: median={:.3}ms", median_rtt));

        if median_offset.abs() > self.max_offset_ms {
            return Err(format!("Offset too large: {:.3}ms (max: {}ms)", 
                              median_offset, self.max_offset_ms));
        }

        Ok((median_offset, stdev_offset))
    }

    fn adjust_clock(&self, offset_ms: f64) -> Result<(), String> {
        if self.dry_run {
            self.log("INFO", &format!("DRY RUN: Would adjust clock by {:.3}ms", offset_ms));
            return Ok(());
        }

        // Check if we're root
        unsafe {
            if libc::geteuid() != 0 {
                return Err("Must run as root to adjust system clock".to_string());
            }
        }

        if offset_ms.abs() <= self.slew_threshold_ms {
            // Slew (gradual adjustment)
            self.log("INFO", &format!("Slewing clock by {:.3}ms (gradual adjustment)", offset_ms));
            
            #[cfg(target_os = "linux")]
            unsafe {
                let mut tx: libc::timex = std::mem::zeroed();
                tx.modes = 0x0001 | 0x1000; // ADJ_OFFSET | ADJ_MICRO
                tx.offset = (offset_ms * 1000.0) as libc::c_long; // Convert to microseconds

                // Use syscall directly on Linux
                let result = libc::syscall(libc::SYS_adjtimex, &mut tx as *mut libc::timex);
                if result == -1 {
                    return Err("Failed to adjust clock via adjtimex".to_string());
                }
            }

            #[cfg(target_os = "macos")]
            unsafe {
                // macOS uses adjtime() which takes a timeval for the delta
                let offset_sec = (offset_ms / 1000.0) as libc::time_t;
                let offset_usec = ((offset_ms % 1000.0) * 1000.0) as libc::suseconds_t;
                
                let delta = libc::timeval {
                    tv_sec: offset_sec,
                    tv_usec: offset_usec,
                };
                
                let result = libc::adjtime(&delta, std::ptr::null_mut());
                if result != 0 {
                    return Err("Failed to adjust clock via adjtime".to_string());
                }
                
                self.log("INFO", "Note: macOS slew rate is fixed at ~500 ppm");
            }

            #[cfg(not(any(target_os = "linux", target_os = "macos")))]
            {
                return Err("Slew adjustment only supported on Linux and macOS".to_string());
            }

            self.log("INFO", "Clock slewed successfully (will adjust gradually)");
        } else {
            // Step (immediate adjustment)
            self.log("INFO", &format!("Stepping clock by {:.3}ms (immediate adjustment)", offset_ms));
            
            unsafe {
                let mut tv: libc::timeval = std::mem::zeroed();
                libc::gettimeofday(&mut tv, std::ptr::null_mut());
                
                let offset_us = (offset_ms * 1000.0) as i64;
                let mut total_us = tv.tv_usec as i64 + offset_us;
                let mut sec = tv.tv_sec;
                
                // Handle overflow
                while total_us >= 1_000_000 {
                    sec += 1;
                    total_us -= 1_000_000;
                }
                while total_us < 0 {
                    sec -= 1;
                    total_us += 1_000_000;
                }

                tv.tv_sec = sec;
                tv.tv_usec = total_us as _;

                let result = libc::settimeofday(&tv, std::ptr::null());
                if result != 0 {
                    return Err("Failed to step clock via settimeofday".to_string());
                }
            }

            self.log("INFO", "Clock stepped successfully");
        }

        Ok(())
    }

    fn sync(&self) -> Result<(), String> {
        let start = Instant::now();
        
        self.log("INFO", "======================================================================");
        self.log("INFO", "TSQ Time Synchronization Starting (Datagrams)");
        self.log("INFO", "======================================================================");
        self.log("INFO", &format!("Servers: {}", self.servers.join(", ")));
        self.log("INFO", &format!("Port: {}", self.port));
        self.log("INFO", &format!("Queries per server: {}", self.queries));
        self.log("INFO", &format!("Max offset: {}ms", self.max_offset_ms));
        self.log("INFO", &format!("Slew threshold: {}ms", self.slew_threshold_ms));
        if self.dry_run {
            self.log("WARN", "DRY RUN MODE - No actual clock adjustment");
        }
        self.log("INFO", "");

        // Measure offsets
        let measurements = self.measure_offsets()?;

        // Calculate adjustment
        let (offset_ms, stdev_ms) = self.calculate_adjustment(&measurements)?;

        self.log("INFO", "");
        self.log("INFO", &format!("Calculated adjustment: {:.3}ms ± {:.3}ms", 
                                  offset_ms, stdev_ms));

        // Apply adjustment
        self.adjust_clock(offset_ms)?;

        let duration = start.elapsed().as_secs_f64() * 1000.0;

        self.log("INFO", "");
        self.log("INFO", "======================================================================");
        self.log("SUCCESS", "TSQ Time Synchronization COMPLETED");
        self.log("INFO", &format!("Total sync duration: {:.1}ms", duration));
        self.log("INFO", "======================================================================");

        Ok(())
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    
    if args.len() < 2 {
        eprintln!("Usage: {} <server1> [server2 ...] [options]", args[0]);
        eprintln!();
        eprintln!("Options:");
        eprintln!("  --port <port>           Server port (default: 443)");
        eprintln!("  --queries <n>           Queries per server (default: 5)");
        eprintln!("  --max-offset <ms>       Maximum allowed offset (default: 1000)");
        eprintln!("  --slew-threshold <ms>   Threshold for slew vs step (default: 500)");
        eprintln!("  --dry-run               Don't actually adjust clock");
        eprintln!("  --verbose               Verbose output");
        std::process::exit(1);
    }

    let mut servers = Vec::new();
    let mut port = 443u16;
    let mut queries = 5usize;
    let mut max_offset_ms = 1000.0f64;
    let mut slew_threshold_ms = 500.0f64;
    let mut dry_run = false;
    let mut verbose = false;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--port" => {
                i += 1;
                port = args[i].parse().expect("Invalid port");
            }
            "--queries" => {
                i += 1;
                queries = args[i].parse().expect("Invalid queries");
            }
            "--max-offset" => {
                i += 1;
                max_offset_ms = args[i].parse().expect("Invalid max-offset");
            }
            "--slew-threshold" => {
                i += 1;
                slew_threshold_ms = args[i].parse().expect("Invalid slew-threshold");
            }
            "--dry-run" => {
                dry_run = true;
            }
            "--verbose" | "-v" => {
                verbose = true;
            }
            arg if !arg.starts_with("--") => {
                servers.push(arg.to_string());
            }
            _ => {
                eprintln!("Unknown option: {}", args[i]);
                std::process::exit(1);
            }
        }
        i += 1;
    }

    if servers.is_empty() {
        eprintln!("Error: No servers specified");
        std::process::exit(1);
    }

    let adjtime = TSQAdjTime::new(servers, port, queries, max_offset_ms, 
                                   slew_threshold_ms, dry_run, verbose);

    match adjtime.sync() {
        Ok(_) => std::process::exit(0),
        Err(e) => {
            eprintln!("[ERROR] TSQ Time Synchronization FAILED: {}", e);
            std::process::exit(1);
        }
    }
}
