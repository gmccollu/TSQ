#!/usr/bin/env python3
"""
Setup NTP (chrony) service on TSQ servers
"""
import paramiko
import time

SERVERS = {
    'server1': {
        'host': '172.18.124.203',
        'username': 'cisco',
        'password': 'cisco123'
    },
    'server2': {
        'host': '172.18.124.204',
        'username': 'cisco',
        'password': 'cisco123'
    }
}

def setup_ntp_on_server(name, config):
    """Install and configure chrony on a server"""
    print(f"\n{'='*60}")
    print(f"Setting up NTP on {name} ({config['host']})")
    print('='*60)
    
    try:
        # Connect via SSH
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=config['host'],
            username=config['username'],
            password=config['password']
        )
        
        print(f"✓ Connected to {name}")
        
        # Check if chrony is installed
        print("Checking for chrony...")
        stdin, stdout, stderr = client.exec_command('which chronyd')
        chrony_path = stdout.read().decode().strip()
        
        if not chrony_path:
            print("  chrony not found, installing...")
            # Install chrony (Ubuntu/Debian)
            stdin, stdout, stderr = client.exec_command('sudo apt-get update && sudo apt-get install -y chrony')
            stdout.channel.recv_exit_status()  # Wait for completion
            print("  ✓ chrony installed")
        else:
            print(f"  ✓ chrony already installed at {chrony_path}")
        
        # Configure chrony to use public NTP servers
        print("Configuring chrony...")
        chrony_conf = """# Use public NTP servers
pool pool.ntp.org iburst
pool time.google.com iburst

# Allow NTP client access from local network
allow 172.18.124.0/24
allow 0.0.0.0/0

# Serve time even if not synchronized to a time source
local stratum 10

# Record the rate at which the system clock gains/losses time
driftfile /var/lib/chrony/drift

# Enable kernel synchronization of the real-time clock (RTC)
rtcsync

# Make steps larger than 1 second
makestep 1 3

# Log files
logdir /var/log/chrony
"""
        
        # Write config file
        stdin, stdout, stderr = client.exec_command('sudo tee /etc/chrony/chrony.conf > /dev/null')
        stdin.write(chrony_conf)
        stdin.channel.shutdown_write()
        stdout.channel.recv_exit_status()
        print("  ✓ Configuration written")
        
        # Restart chrony service
        print("Restarting chrony service...")
        stdin, stdout, stderr = client.exec_command('sudo systemctl restart chrony')
        stdout.channel.recv_exit_status()
        print("  ✓ chrony restarted")
        
        # Enable chrony to start on boot
        stdin, stdout, stderr = client.exec_command('sudo systemctl enable chrony')
        stdout.channel.recv_exit_status()
        print("  ✓ chrony enabled on boot")
        
        # Wait a moment for chrony to sync
        print("Waiting for chrony to sync...")
        time.sleep(3)
        
        # Check chrony status
        stdin, stdout, stderr = client.exec_command('chronyc tracking')
        tracking = stdout.read().decode()
        print("\nChrony status:")
        print(tracking)
        
        # Check sources
        stdin, stdout, stderr = client.exec_command('chronyc sources')
        sources = stdout.read().decode()
        print("\nNTP sources:")
        print(sources)
        
        # Open firewall for NTP (port 123 UDP)
        print("\nOpening firewall for NTP (port 123/udp)...")
        stdin, stdout, stderr = client.exec_command('sudo ufw allow 123/udp')
        stdout.channel.recv_exit_status()
        print("  ✓ Firewall rule added")
        
        client.close()
        print(f"\n✓ {name} setup complete!")
        return True
        
    except Exception as e:
        print(f"\n✗ Error setting up {name}: {e}")
        return False

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║              NTP Server Setup for TSQ                      ║
╚════════════════════════════════════════════════════════════╝

This script will:
1. Install chrony (NTP service) on both servers
2. Configure them to sync with public NTP servers
3. Allow NTP queries from clients
4. Open firewall port 123/udp

""")
    
    input("Press Enter to continue...")
    
    results = {}
    for name, config in SERVERS.items():
        results[name] = setup_ntp_on_server(name, config)
    
    print("\n" + "="*60)
    print("SETUP SUMMARY")
    print("="*60)
    for name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{name}: {status}")
    
    if all(results.values()):
        print("\n✓ All servers configured successfully!")
        print("\nYou can now run: python tsq_test_runner.py compare")
    else:
        print("\n✗ Some servers failed to configure")

if __name__ == "__main__":
    main()
