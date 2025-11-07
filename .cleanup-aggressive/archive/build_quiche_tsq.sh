#!/bin/bash
# Build custom TSQ server/client using Quiche

set -e

echo "Building TSQ with Quiche datagrams..."

# Check if quiche is installed
if [ ! -d "$HOME/quiche" ]; then
    echo "Error: Quiche not found. Please run ./install_quiche.sh first"
    exit 1
fi

cd ~/quiche

# Create TSQ examples directory
mkdir -p examples/tsq

# Copy and modify the server example
cat > examples/tsq/server.rs << 'EOF'
// TSQ Server with Quiche Datagrams
use std::net;
use std::collections::HashMap;

const MAX_DATAGRAM_SIZE: usize = 1350;
const TSQ_ALPN: &[u8] = b"tsq/1";

fn main() {
    let mut args = std::env::args();
    let cmd = &args.next().unwrap();
    
    if args.len() != 4 {
        println!("Usage: {} --listen ADDR --cert CERT --key KEY", cmd);
        return;
    }
    
    // Parse arguments
    let mut listen_addr = String::new();
    let mut cert_path = String::new();
    let mut key_path = String::new();
    
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--listen" => listen_addr = args.next().unwrap(),
            "--cert" => cert_path = args.next().unwrap(),
            "--key" => key_path = args.next().unwrap(),
            _ => {}
        }
    }
    
    println!("[TSQ-Q] Starting TSQ server (Quiche/Datagrams)");
    println!("[TSQ-Q] Listening on {}", listen_addr);
    
    // Create socket
    let socket = net::UdpSocket::bind(&listen_addr).unwrap();
    
    // Create config
    let mut config = quiche::Config::new(quiche::PROTOCOL_VERSION).unwrap();
    config.load_cert_chain_from_pem_file(&cert_path).unwrap();
    config.load_priv_key_from_pem_file(&key_path).unwrap();
    config.set_application_protos(&[TSQ_ALPN]).unwrap();
    config.set_max_idle_timeout(30000);
    config.set_max_recv_udp_payload_size(MAX_DATAGRAM_SIZE);
    config.set_initial_max_data(10_000_000);
    config.set_initial_max_stream_data_bidi_local(1_000_000);
    config.set_initial_max_stream_data_bidi_remote(1_000_000);
    config.set_initial_max_streams_bidi(100);
    config.enable_dgram(true, 1000, 1000);
    
    let mut buf = [0; 65535];
    let mut out = [0; MAX_DATAGRAM_SIZE];
    
    let mut clients = HashMap::new();
    
    println!("[TSQ-Q] Server ready");
    
    loop {
        let (len, from) = socket.recv_from(&mut buf).unwrap();
        
        println!("[TSQ-Q] Received {} bytes from {}", len, from);
        
        // TODO: Parse QUIC header and handle connection
        // For now, this is a placeholder showing the structure
        
        // Handle TSQ datagram request
        if len >= 18 {
            // Simple TSQ response (placeholder)
            println!("[TSQ-Q] Processing TSQ request");
        }
    }
}
EOF

# Copy and modify the client example  
cat > examples/tsq/client.rs << 'EOF'
// TSQ Client with Quiche Datagrams
use std::net;

const MAX_DATAGRAM_SIZE: usize = 1350;
const TSQ_ALPN: &[u8] = b"tsq/1";

fn main() {
    let args: Vec<String> = std::env::args().collect();
    
    if args.len() < 2 {
        println!("Usage: {} SERVER:PORT", args[0]);
        return;
    }
    
    let server_addr = &args[1];
    
    println!("[TSQ-Q] Connecting to {}", server_addr);
    
    // Create socket
    let socket = net::UdpSocket::bind("0.0.0.0:0").unwrap();
    socket.connect(server_addr).unwrap();
    
    // Create config
    let mut config = quiche::Config::new(quiche::PROTOCOL_VERSION).unwrap();
    config.set_application_protos(&[TSQ_ALPN]).unwrap();
    config.verify_peer(false);
    config.enable_dgram(true, 1000, 1000);
    
    println!("[TSQ-Q] Configuration created");
    
    // TODO: Create connection and send TSQ request
    // This is a placeholder showing the structure
}
EOF

echo "✓ TSQ Rust examples created"
echo
echo "Note: Full implementation requires completing the Rust code"
echo "This provides the structure for a proper Quiche-based TSQ implementation"
echo
echo "To build:"
echo "  cd ~/quiche"
echo "  cargo build --release --example tsq-server"
echo "  cargo build --release --example tsq-client"
