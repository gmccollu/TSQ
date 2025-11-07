// TSQ Client - QUIC Datagrams with Quiche
// Minimal implementation focused on datagram-based time synchronization

use std::net;
use ring::rand::SecureRandom;

const MAX_DATAGRAM_SIZE: usize = 1350;
const LOCAL_CONN_ID_LEN: usize = 16;
const MAX_IDLE_TIMEOUT_MS: u64 = 30000;
const DGRAM_QUEUE_SIZE: usize = 1000;
const CONNECTION_TIMEOUT_SECS: u64 = 5;
const PROBE_TIMEOUT_SECS: u64 = 3;
const MAX_PROBES: usize = 100;

// TLV Types
const T_NONCE: u8 = 1;
const T_RECV_TS: u8 = 2;
const T_SEND_TS: u8 = 3;

fn main() {
    let mut args = std::env::args();
    args.next(); // Skip program name
    
    let mut servers = Vec::new();
    let mut port = 443;
    let mut count = 3;
    let mut insecure = false;
    
    // Parse arguments
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--port" => {
                port = match args.next() {
                    Some(v) => match v.parse() {
                        Ok(p) => p,
                        Err(_) => {
                            eprintln!("Error: Invalid port number");
                            std::process::exit(1);
                        }
                    },
                    None => {
                        eprintln!("Error: Missing port value");
                        std::process::exit(1);
                    }
                };
            }
            "--count" => {
                count = match args.next() {
                    Some(v) => match v.parse() {
                        Ok(c) => c,
                        Err(_) => {
                            eprintln!("Error: Invalid count number");
                            std::process::exit(1);
                        }
                    },
                    None => {
                        eprintln!("Error: Missing count value");
                        std::process::exit(1);
                    }
                };
            }
            "--insecure" => insecure = true,
            _ => servers.push(arg),
        }
    }
    
    if servers.is_empty() {
        eprintln!("Usage: tsq-client SERVER [SERVER...] [--port PORT] [--count N] [--insecure]");
        std::process::exit(1);
    }
    
    // Validate inputs
    if port == 0 || port > 65535 {
        eprintln!("Error: Port must be between 1 and 65535");
        std::process::exit(1);
    }
    
    if count == 0 || count > MAX_PROBES {
        eprintln!("Error: Count must be between 1 and {}", MAX_PROBES);
        std::process::exit(1);
    }
    
    if servers.iter().any(|s| s.is_empty()) {
        eprintln!("Error: Server address cannot be empty");
        std::process::exit(1);
    }
    
    println!("[TSQ-Q] Client Version (Datagram)");
    println!("[TSQ-Q] Hosts to probe: {:?}", servers);
    println!();
    
    for (idx, server) in servers.iter().enumerate() {
        println!("[TSQ-Q] ===== Host {}/{}: {} =====", idx + 1, servers.len(), server);
        
        let server_addr = format!("{}:{}", server, port);
        
        match run_probes(&server_addr, server, count, insecure) {
            Ok(results) => {
                if !results.is_empty() {
                    let avg_rtt: f64 = results.iter().map(|(r, _)| r).sum::<f64>() / results.len() as f64;
                    let avg_offset: f64 = results.iter().map(|(_, o)| o).sum::<f64>() / results.len() as f64;
                    
                    println!();
                    println!("[TSQ-Q] Average: RTT={:.3} ms, Offset={:.3} ms", avg_rtt, avg_offset);
                } else {
                    println!();
                    println!("[TSQ-Q] No successful probes");
                }
            }
            Err(e) => eprintln!("[TSQ-Q] Error: {}", e),
        }
        
        println!();
    }
}

fn run_probes(server_addr: &str, server_name: &str, count: usize, insecure: bool) -> Result<Vec<(f64, f64)>, Box<dyn std::error::Error>> {
    // Create QUIC config
    let mut config = quiche::Config::new(quiche::PROTOCOL_VERSION)?;
    
    config.set_application_protos(&[b"tsq/1"])?;
    config.set_max_idle_timeout(MAX_IDLE_TIMEOUT_MS);
    config.set_max_recv_udp_payload_size(MAX_DATAGRAM_SIZE);
    config.set_initial_max_data(10_000_000);
    config.set_initial_max_stream_data_bidi_local(0);
    config.set_initial_max_stream_data_bidi_remote(0);
    config.set_initial_max_streams_bidi(0);
    config.set_initial_max_streams_uni(0);
    
    // Enable datagrams
    config.enable_dgram(true, DGRAM_QUEUE_SIZE, DGRAM_QUEUE_SIZE);
    config.set_disable_active_migration(true);
    
    if insecure {
        eprintln!("WARNING: Certificate verification disabled!");
        eprintln!("WARNING: Use only for testing. Connection is vulnerable to MITM attacks.");
        config.verify_peer(false);
    }
    
    // Create UDP socket
    let socket = net::UdpSocket::bind("0.0.0.0:0")?;
    socket.connect(server_addr)?;
    
    let local_addr = socket.local_addr()?;
    let peer_addr = socket.peer_addr()?;
    
    // Generate connection ID
    let mut scid = [0; LOCAL_CONN_ID_LEN];
    if let Err(e) = ring::rand::SystemRandom::new().fill(&mut scid) {
        return Err(format!("Failed to generate random bytes: {:?}", e).into());
    }
    let scid = quiche::ConnectionId::from_ref(&scid);
    
    // Create connection
    let mut conn = quiche::connect(
        Some(server_name),
        &scid,
        local_addr,
        peer_addr,
        &mut config,
    )?;
    
    println!("[TSQ-Q] Connecting to {}...", server_addr);
    
    let mut buf = [0; 65535];
    let mut out = [0; MAX_DATAGRAM_SIZE];
    
    // Send initial packet
    let (write, _) = conn.send(&mut out)?;
    socket.send(&out[..write])?;
    
    // Wait for connection to establish
    let mut established = false;
    socket.set_read_timeout(Some(std::time::Duration::from_secs(CONNECTION_TIMEOUT_SECS)))?;
    
    while !established {
        let len = match socket.recv(&mut buf) {
            Ok(v) => v,
            Err(e) => {
                eprintln!("[TSQ-Q] recv error: {}", e);
                break;
            }
        };
        
        let recv_info = quiche::RecvInfo {
            to: local_addr,
            from: peer_addr,
        };
        
        conn.recv(&mut buf[..len], recv_info)?;
        
        if conn.is_established() {
            established = true;
            println!("[TSQ-Q] Connected to {}", server_addr);
        }
        
        // Send any pending packets
        loop {
            let (write, _) = match conn.send(&mut out) {
                Ok(v) => v,
                Err(quiche::Error::Done) => break,
                Err(e) => return Err(e.into()),
            };
            
            socket.send(&out[..write])?;
        }
    }
    
    if !established {
        return Err("Failed to establish connection".into());
    }
    
    // Run probes
    let mut results = Vec::new();
    
    for probe_num in 1..=count {
        println!("[TSQ-Q] Probe #{} to {}", probe_num, server_name);
        
        match run_single_probe(&socket, &mut conn, local_addr, peer_addr, &mut buf, &mut out) {
            Ok((rtt, offset)) => {
                results.push((rtt, offset));
                println!("[TSQ-Q] Probe #{} complete", probe_num);
            }
            Err(e) => {
                eprintln!("[TSQ-Q] Probe #{} failed: {}", probe_num, e);
            }
        }
        
        if probe_num < count {
            println!("[TSQ-Q] Waiting 1s before next probe...");
            std::thread::sleep(std::time::Duration::from_secs(1));
        }
    }
    
    Ok(results)
}

fn run_single_probe(
    socket: &net::UdpSocket,
    conn: &mut quiche::Connection,
    local_addr: net::SocketAddr,
    peer_addr: net::SocketAddr,
    buf: &mut [u8],
    out: &mut [u8],
) -> Result<(f64, f64), Box<dyn std::error::Error>> {
    // Generate nonce
    let mut nonce = [0u8; 16];
    if let Err(e) = ring::rand::SystemRandom::new().fill(&mut nonce) {
        return Err(format!("Failed to generate nonce: {:?}", e).into());
    }
    
    // Build request
    let mut request = Vec::new();
    request.push(T_NONCE);
    request.push(16);
    request.extend_from_slice(&nonce);
    
    // Send datagram and record T1
    conn.dgram_send(&request)?;
    let t1 = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)?
        .as_nanos() as u64;
    
    println!("[TSQ-Q] Sent {} bytes", request.len());
    
    // Send QUIC packets
    loop {
        let (write, _) = match conn.send(out) {
            Ok(v) => v,
            Err(quiche::Error::Done) => break,
            Err(e) => return Err(e.into()),
        };
        
        socket.send(&out[..write])?;
    }
    
    // Wait for response
    socket.set_read_timeout(Some(std::time::Duration::from_secs(PROBE_TIMEOUT_SECS)))?;
    
    let mut response_data = None;
    let mut t4 = 0u64;
    
    for _ in 0..10 {
        let len = socket.recv(buf)?;
        
        let recv_info = quiche::RecvInfo {
            to: local_addr,
            from: peer_addr,
        };
        
        conn.recv(&mut buf[..len], recv_info)?;
        
        // Check for datagram
        let mut dgram_buf = [0u8; 65535];
        while let Ok(len) = conn.dgram_recv(&mut dgram_buf) {
            t4 = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)?
                .as_nanos() as u64;
            
            response_data = Some(dgram_buf[..len].to_vec());
            println!("[TSQ-Q] Received {} bytes", len);
            break;
        }
        
        if response_data.is_some() {
            break;
        }
        
        // Send any pending packets
        loop {
            let (write, _) = match conn.send(out) {
                Ok(v) => v,
                Err(quiche::Error::Done) => break,
                Err(e) => return Err(e.into()),
            };
            
            socket.send(&out[..write])?;
        }
    }
    
    let response = response_data.ok_or("No response received")?;
    
    // Parse response
    let (t2, t3) = parse_response(&response)?;
    
    // Calculate metrics
    let rtt_ns = (t4 as i64 - t1 as i64) - (t3 as i64 - t2 as i64);
    let offset_ns = ((t2 as i64 - t1 as i64) + (t3 as i64 - t4 as i64)) / 2;
    
    let rtt_ms = rtt_ns as f64 / 1_000_000.0;
    let offset_ms = offset_ns as f64 / 1_000_000.0;
    
    println!("[TSQ-Q] T1 (client send):    {}", t1);
    println!("[TSQ-Q] T2 (server receive): {}", t2);
    println!("[TSQ-Q] T3 (server send):    {}", t3);
    println!("[TSQ-Q] T4 (client receive): {}", t4);
    println!("[TSQ-Q] RTT={:.3} ms  offset={:.3} ms", rtt_ms, offset_ms);
    
    Ok((rtt_ms, offset_ms))
}

fn parse_response(data: &[u8]) -> Result<(u64, u64), Box<dyn std::error::Error>> {
    let mut offset = 0;
    let mut t2 = None;
    let mut t3 = None;
    
    while offset < data.len() {
        if offset + 2 > data.len() {
            break;
        }
        
        let tlv_type = data[offset];
        let tlv_len = data[offset + 1] as usize;
        
        if offset + 2 + tlv_len > data.len() {
            break;
        }
        
        let tlv_val = &data[offset + 2..offset + 2 + tlv_len];
        
        match tlv_type {
            T_RECV_TS if tlv_len == 8 => t2 = Some(ntp_to_ns(tlv_val)),
            T_SEND_TS if tlv_len == 8 => t3 = Some(ntp_to_ns(tlv_val)),
            _ => {}
        }
        
        offset += 2 + tlv_len;
    }
    
    Ok((
        t2.ok_or("Missing T2")?,
        t3.ok_or("Missing T3")?,
    ))
}

fn ntp_to_ns(data: &[u8]) -> u64 {
    const NTP_EPOCH_OFFSET: u64 = 2208988800;
    
    let ntp_seconds = u32::from_be_bytes([data[0], data[1], data[2], data[3]]) as u64;
    let ntp_fraction = u32::from_be_bytes([data[4], data[5], data[6], data[7]]) as u64;
    
    let unix_seconds = ntp_seconds - NTP_EPOCH_OFFSET;
    let nanos = (ntp_fraction * 1_000_000_000) / (1u64 << 32);
    
    unix_seconds * 1_000_000_000 + nanos
}
