# Installing TSQ as Systemd Services

This guide explains how to set up TSQ servers to run automatically on boot and restart on failure.

## Prerequisites

- TSQ binaries and scripts installed on the server
- Let's Encrypt certificate configured
- Root/sudo access

## Installation Steps

### 1. Copy Service Files

```bash
# Copy service files to systemd directory
sudo cp tsq-datagram.service /etc/systemd/system/
sudo cp tsq-stream.service /etc/systemd/system/

# Set correct permissions
sudo chmod 644 /etc/systemd/system/tsq-datagram.service
sudo chmod 644 /etc/systemd/system/tsq-stream.service
```

### 2. Reload Systemd

```bash
sudo systemctl daemon-reload
```

### 3. Enable Services (Auto-Start on Boot)

```bash
sudo systemctl enable tsq-datagram
sudo systemctl enable tsq-stream
```

### 4. Start Services

```bash
sudo systemctl start tsq-datagram
sudo systemctl start tsq-stream
```

### 5. Verify Services are Running

```bash
sudo systemctl status tsq-datagram
sudo systemctl status tsq-stream
```

You should see `Active: active (running)` for both services.

## Management Commands

### Check Status
```bash
sudo systemctl status tsq-datagram
sudo systemctl status tsq-stream
```

### View Logs
```bash
# View recent logs
sudo journalctl -u tsq-datagram -n 50
sudo journalctl -u tsq-stream -n 50

# Follow logs in real-time
sudo journalctl -u tsq-datagram -u tsq-stream -f
```

### Restart Services
```bash
sudo systemctl restart tsq-datagram
sudo systemctl restart tsq-stream
```

### Stop Services
```bash
sudo systemctl stop tsq-datagram
sudo systemctl stop tsq-stream
```

### Disable Auto-Start
```bash
sudo systemctl disable tsq-datagram
sudo systemctl disable tsq-stream
```

## Troubleshooting

### Service Won't Start

1. Check the logs:
```bash
sudo journalctl -u tsq-datagram -n 100
sudo journalctl -u tsq-stream -n 100
```

2. Verify binary paths:
```bash
ls -la /usr/local/bin/tsq-datagram-server
ls -la /opt/tsq/tsq-stream-server.py
ls -la /opt/tsq/venv/bin/python3
```

3. Verify certificate paths:
```bash
sudo ls -la /etc/letsencrypt/live/tsq.gmccollu.com/
```

4. Check if ports are already in use:
```bash
sudo netstat -ulpn | grep -E '443|8443'
```

### Certificate Renewal

Let's Encrypt certificates auto-renew via certbot. After renewal, restart services:

```bash
sudo systemctl restart tsq-datagram tsq-stream
```

You can automate this by creating a certbot renewal hook:

```bash
# Create hook script
sudo nano /etc/letsencrypt/renewal-hooks/post/restart-tsq.sh
```

Add:
```bash
#!/bin/bash
systemctl restart tsq-datagram tsq-stream
```

Make executable:
```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/post/restart-tsq.sh
```

## Service Features

- **Auto-start on boot**: Services start automatically when server boots
- **Auto-restart on failure**: If a service crashes, systemd restarts it after 10 seconds
- **Logging**: All output goes to systemd journal (view with `journalctl`)
- **Resource management**: Systemd manages process lifecycle

## Uninstall

To remove the services:

```bash
# Stop and disable services
sudo systemctl stop tsq-datagram tsq-stream
sudo systemctl disable tsq-datagram tsq-stream

# Remove service files
sudo rm /etc/systemd/system/tsq-datagram.service
sudo rm /etc/systemd/system/tsq-stream.service

# Reload systemd
sudo systemctl daemon-reload
```
