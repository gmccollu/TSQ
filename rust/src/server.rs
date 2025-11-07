// TSQ Server - QUIC Datagrams with Quiche
// Minimal implementation focused on datagram-based time synchronization

use std::net;
use std::collections::HashMap;
use ring::rand::SecureRandom;

// Track connection statistics
struct ConnectionStats {
    query_count: usize,
    first_query: std::time::Instant,
}

const MAX_DATAGRAM_SIZE: usize = 1350;
const LOCAL_CONN_ID_LEN: usize = 16;
const MAX_IDLE_TIMEOUT_MS: u64 = 30000;
const DGRAM_QUEUE_SIZE: usize = 1000;
const MAX_CLIENTS: usize = 1000;

// TLV Types
const T_NONCE: u8 = 1;
const T_RECV_TS: u8 = 2;
const T_SEND_TS: u8 = 3;

fn main() {
    let mut args = std::env::args();
    args.next(); // Skip program name
    
    let mut listen = "0.0.0.0:443".to_string();
    let mut cert = String::new();
    let mut key = String::new();
    
    // Parse arguments
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--listen" => listen = args.next().expect("Missing --listen value"),
            "--cert" => cert = args.next().expect("Missing --cert value"),
            "--key" => key = args.next().expect("Missing --key value"),
            _ => {}
        }
    }
    
    if cert.is_empty() || key.is_empty() {
        eprintln!("Usage: tsq-server --listen ADDR --cert CERT --key KEY");
        std::process::exit(1);
    }
    
    println!("[TSQ-Q] Starting TSQ server (Quiche/Datagrams)");
    println!("[TSQ-Q] Listening on {}", listen);
    println!("[TSQ-Q] Certificate: {}", cert);
    
    // Create QUIC config
    let mut config = quiche::Config::new(quiche::PROTOCOL_VERSION).unwrap();
    
    config.load_cert_chain_from_pem_file(&cert)
        .expect("Failed to load certificate");
    config.load_priv_key_from_pem_file(&key)
        .expect("Failed to load private key");
    
    config.set_application_protos(&[b"tsq/1"])
        .expect("Failed to set ALPN");
    
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
    
    // Create UDP socket
    let socket = net::UdpSocket::bind(&listen)
        .expect("Failed to bind socket");
    
    println!("[TSQ-Q] Server ready");
    
    let mut buf = [0; 65535];
    let mut out = [0; MAX_DATAGRAM_SIZE];
    
    let mut clients: HashMap<quiche::ConnectionId<'static>, quiche::Connection> = HashMap::new();
    let mut client_addrs: HashMap<quiche::ConnectionId<'static>, net::SocketAddr> = HashMap::new();
    let mut client_stats: HashMap<quiche::ConnectionId<'static>, ConnectionStats> = HashMap::new();
    
    let local_addr = socket.local_addr().unwrap();
    
    loop {
        // Read from socket
        let (len, from) = match socket.recv_from(&mut buf) {
            Ok(v) => v,
            Err(e) => {
                eprintln!("[TSQ-Q] recv_from error: {}", e);
                continue;
            }
        };
        
        let pkt_buf = &mut buf[..len];
        
        // Parse QUIC packet header to get connection ID
        let hdr = match quiche::Header::from_slice(pkt_buf, LOCAL_CONN_ID_LEN) {
            Ok(v) => v,
            Err(e) => {
                eprintln!("[TSQ-Q] Failed to parse header: {}", e);
                continue;
            }
        };
        
        let conn_id = hdr.dcid.into_owned();
        
        // Check if this is an existing connection
        let conn = if !clients.contains_key(&conn_id) {
            // New connection
            if hdr.ty != quiche::Type::Initial {
                eprintln!("[TSQ-Q] Packet is not Initial");
                continue;
            }
            
            // Generate new connection ID
            let mut scid_bytes = [0; LOCAL_CONN_ID_LEN];
            if let Err(e) = ring::rand::SystemRandom::new().fill(&mut scid_bytes) {
                eprintln!("[TSQ-Q] Failed to generate connection ID: {:?}", e);
                continue;
            }
            let scid = quiche::ConnectionId::from_ref(&scid_bytes).into_owned();
            
            println!("[TSQ-Q] New connection from {}", from);
            
            // Create connection
            let conn = quiche::accept(
                &scid,
                None,
                local_addr,
                from,
                &mut config,
            ).expect("Failed to create connection");
            
            clients.insert(scid.clone(), conn);
            client_addrs.insert(scid.clone(), from);
            
            clients.get_mut(&scid).unwrap()
        } else {
            clients.get_mut(&conn_id).unwrap()
        };
        
        // Process packet
        let recv_info = quiche::RecvInfo {
            to: local_addr,
            from,
        };
        
        match conn.recv(pkt_buf, recv_info) {
            Ok(_) => {},
            Err(e) => {
                eprintln!("[TSQ-Q] recv failed: {:?}", e);
                continue;
            }
        }
        
        // Check if connection is established
        if conn.is_established() {
            // Check for datagram
            while let Ok(len) = conn.dgram_recv(&mut buf) {
                if len > buf.len() {
                    eprintln!("[TSQ-Q] Datagram too large: {} bytes", len);
                    log_request(&from, "FAILED", "Datagram too large", None, None);
                    continue;
                }
                let dgram = &buf[..len];
                
                // Process TSQ request
                match handle_tsq_request(dgram) {
                    Some((response, _t2, _t3)) => {
                        // Track query count
                        let stats = client_stats.entry(conn_id.clone()).or_insert(ConnectionStats {
                            query_count: 0,
                            first_query: std::time::Instant::now(),
                        });
                        stats.query_count += 1;
                        
                        // Send response datagram
                        match conn.dgram_send(&response) {
                            Ok(_) => {},
                            Err(e) => {
                                eprintln!("[TSQ-Q] dgram_send failed: {:?}", e);
                            }
                        }
                    },
                    None => {
                        eprintln!("[TSQ-Q] Invalid TSQ request");
                    }
                }
            }
        }
        
        // Send packets
        loop {
            let (write, send_info) = match conn.send(&mut out) {
                Ok(v) => v,
                Err(quiche::Error::Done) => break,
                Err(e) => {
                    eprintln!("[TSQ-Q] send failed: {:?}", e);
                    break;
                }
            };
            
            match socket.send_to(&out[..write], send_info.to) {
                Ok(_) => {},
                Err(e) => eprintln!("[TSQ-Q] send_to failed: {}", e),
            }
        }
        
        // Periodic cleanup of closed connections
        if clients.len() > MAX_CLIENTS {
            let before = clients.len();
            
            // Log stats for closed connections before removing them
            let closed_ids: Vec<_> = clients.iter()
                .filter(|(_, conn)| conn.is_closed() || conn.is_timed_out())
                .map(|(id, _)| id.clone())
                .collect();
            
            for conn_id in &closed_ids {
                if let Some(addr) = client_addrs.get(conn_id) {
                    if let Some(stats) = client_stats.get(conn_id) {
                        let duration = stats.first_query.elapsed();
                        log_session(addr, stats.query_count, duration.as_secs_f64() * 1000.0);
                    }
                }
            }
            
            clients.retain(|_, conn| !conn.is_closed() && !conn.is_timed_out());
            client_addrs.retain(|id, _| clients.contains_key(id));
            client_stats.retain(|id, _| clients.contains_key(id));
            
            let after = clients.len();
            if before != after {
                println!("[TSQ-Q] Cleaned up {} closed connections", before - after);
            }
        }
    }
}

fn handle_tsq_request(data: &[u8]) -> Option<(Vec<u8>, u64, u64)> {
    // Record receive timestamp
    let t2_recv = match std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH) {
        Ok(d) => d.as_nanos() as u64,
        Err(e) => {
            eprintln!("[TSQ-Q] System time error: {}", e);
            return None;
        }
    };
    
    // Parse request (expecting Type 1, Length 16, Nonce 16 bytes)
    if data.len() < 18 {
        eprintln!("[TSQ-Q] Request too short");
        return None;
    }
    
    if data[0] != T_NONCE || data[1] != 16 {
        eprintln!("[TSQ-Q] Invalid request format");
        return None;
    }
    
    let nonce = &data[2..18];
    
    // Build response
    let mut response = Vec::new();
    
    // Echo nonce
    response.push(T_NONCE);
    response.push(16);
    response.extend_from_slice(nonce);
    
    // Add T2 (receive timestamp)
    response.push(T_RECV_TS);
    response.push(8);
    response.extend_from_slice(&ns_to_ntp(t2_recv));
    
    // Record T3 (send timestamp) right before returning
    let t3_send = match std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH) {
        Ok(d) => d.as_nanos() as u64,
        Err(e) => {
            eprintln!("[TSQ-Q] System time error: {}", e);
            return None;
        }
    };
    
    response.push(T_SEND_TS);
    response.push(8);
    response.extend_from_slice(&ns_to_ntp(t3_send));
    
    Some((response, t2_recv, t3_send))
}

fn ns_to_ntp(ns: u64) -> [u8; 8] {
    const NTP_EPOCH_OFFSET: u64 = 2208988800;
    
    let seconds = ns / 1_000_000_000;
    let nanos = ns % 1_000_000_000;
    
    let ntp_seconds = (seconds + NTP_EPOCH_OFFSET) as u32;
    let ntp_fraction = ((nanos as u64 * (1u64 << 32)) / 1_000_000_000) as u32;
    
    let mut result = [0u8; 8];
    result[0..4].copy_from_slice(&ntp_seconds.to_be_bytes());
    result[4..8].copy_from_slice(&ntp_fraction.to_be_bytes());
    result
}

fn log_session(peer: &net::SocketAddr, query_count: usize, duration_ms: f64) {
    let timestamp = chrono::Utc::now().format("%Y-%m-%d %H:%M:%S%.3f UTC");
    println!("[TSQ-LOG] {} client={} protocol=datagram queries={} duration={:.1}ms", 
             timestamp, peer.ip(), query_count, duration_ms);
}

fn log_request(peer: &net::SocketAddr, status: &str, error: &str, _processing_time_ms: Option<f64>, _offset_ms: Option<f64>) {
    let timestamp = chrono::Utc::now().format("%Y-%m-%d %H:%M:%S%.3f UTC");
    println!("[TSQ-LOG] {} client={} protocol=datagram status={} error=\"{}\"", 
             timestamp, peer.ip(), status, error);
}
