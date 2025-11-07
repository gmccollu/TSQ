#!/bin/bash
# Deploy TSQ Datagrams to test environment

set -e

cd "$(dirname "$0")"

echo "============================================================"
echo "Deploying TSQ Datagrams to Test Environment"
echo "============================================================"
echo

# Check if binaries exist
if [ ! -f "rust/target/release/tsq-server" ]; then
    echo "Error: Server binary not found. Building..."
    cd rust && ./build.sh && cd ..
fi

# Server IPs
SERVER1="172.18.124.203"
SERVER2="172.18.124.204"
CLIENT="172.18.124.206"
USER="cisco"

echo "Deploying to servers..."
echo

# Deploy server binary
echo "→ Copying server binary to $SERVER1..."
scp rust/target/release/tsq-server ${USER}@${SERVER1}:/home/cisco/tsq-server-dg

echo "→ Copying server binary to $SERVER2..."
scp rust/target/release/tsq-server ${USER}@${SERVER2}:/home/cisco/tsq-server-dg

# Deploy client binary
echo "→ Copying client binary to $CLIENT..."
scp rust/target/release/tsq-client ${USER}@${CLIENT}:/home/cisco/tsq-client-dg

echo
echo "✓ Deployment complete!"
echo
echo "To run:"
echo
echo "# On servers (in separate terminals):"
echo "  ssh ${USER}@${SERVER1}"
echo "  cd /home/cisco/tsq-certs"
echo "  ../tsq-server-dg --listen 0.0.0.0:443 --cert server.crt --key server.key"
echo
echo "  ssh ${USER}@${SERVER2}"
echo "  cd /home/cisco/tsq-certs"
echo "  ../tsq-server-dg --listen 0.0.0.0:443 --cert server.crt --key server.key"
echo
echo "# On client:"
echo "  ssh ${USER}@${CLIENT}"
echo "  ./tsq-client-dg 14.38.117.100 14.38.117.200 --port 443 --count 3 --insecure"
