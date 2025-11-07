#!/bin/bash
# TSQ Systemd Service Setup Script

set -e

echo "=========================================="
echo "TSQ Systemd Service Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Check if service files exist
if [ ! -f "tsq-datagram.service" ] || [ ! -f "tsq-stream.service" ]; then
    echo "ERROR: Service files not found in current directory"
    echo "Please run this script from the systemd/ directory"
    exit 1
fi

echo "Step 1: Copying service files..."
cp tsq-datagram.service /etc/systemd/system/
cp tsq-stream.service /etc/systemd/system/
chmod 644 /etc/systemd/system/tsq-datagram.service
chmod 644 /etc/systemd/system/tsq-stream.service
echo "✓ Service files copied"
echo ""

echo "Step 2: Reloading systemd..."
systemctl daemon-reload
echo "✓ Systemd reloaded"
echo ""

echo "Step 3: Enabling services (auto-start on boot)..."
systemctl enable tsq-datagram
systemctl enable tsq-stream
echo "✓ Services enabled"
echo ""

echo "Step 4: Starting services..."
systemctl start tsq-datagram
systemctl start tsq-stream
echo "✓ Services started"
echo ""

echo "Step 5: Checking status..."
echo ""
echo "--- TSQ Datagram Server ---"
systemctl status tsq-datagram --no-pager -l
echo ""
echo "--- TSQ Stream Server ---"
systemctl status tsq-stream --no-pager -l
echo ""

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Services are now running and will auto-start on boot."
echo ""
echo "Useful commands:"
echo "  sudo systemctl status tsq-datagram tsq-stream"
echo "  sudo journalctl -u tsq-datagram -u tsq-stream -f"
echo "  sudo systemctl restart tsq-datagram tsq-stream"
echo ""
