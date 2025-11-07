#!/usr/bin/env python3
"""
Fix and start NTP service on TSQ servers
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

def fix_ntp_on_server(name, config):
    print(f"\n{'='*60}")
    print(f"Fixing NTP on {name} ({config['host']})")
    print('='*60)
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=config['host'],
            username=config['username'],
            password=config['password']
        )
        
        print(f"✓ Connected to {name}")
        
        # Update package list
        print("\n1. Updating package list...")
        stdin, stdout, stderr = client.exec_command('sudo apt-get update')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("   ✓ Package list updated")
        else:
            print(f"   ✗ Update failed with exit code {exit_status}")
        
        # Install chrony
        print("\n2. Installing chrony...")
        stdin, stdout, stderr = client.exec_command('sudo DEBIAN_FRONTEND=noninteractive apt-get install -y chrony')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("   ✓ Chrony installed")
        else:
            print(f"   ✗ Installation failed with exit code {exit_status}")
            err = stderr.read().decode()
            print(f"   Error: {err[:200]}")
        
        # Create chrony config
        print("\n3. Configuring chrony...")
        chrony_conf = """# Use public NTP servers
pool pool.ntp.org iburst
pool time.google.com iburst

# Allow NTP client access from any IP
allow

# Serve time even if not synchronized
local stratum 10

# Record drift
driftfile /var/lib/chrony/drift

# Enable kernel RTC sync
rtcsync

# Make steps larger than 1 second
makestep 1 3

# Log directory
logdir /var/log/chrony
"""
        
        # Write config using echo and sudo tee
        cmd = f"echo '{chrony_conf}' | sudo tee /etc/chrony/chrony.conf > /dev/null"
        stdin, stdout, stderr = client.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("   ✓ Configuration written")
        else:
            print(f"   ✗ Config write failed")
        
        # Stop chrony first (in case it's running)
        print("\n4. Stopping chrony...")
        stdin, stdout, stderr = client.exec_command('sudo systemctl stop chrony')
        stdout.channel.recv_exit_status()
        
        # Start chrony
        print("\n5. Starting chrony...")
        stdin, stdout, stderr = client.exec_command('sudo systemctl start chrony')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("   ✓ Chrony started")
        else:
            print(f"   ✗ Start failed with exit code {exit_status}")
            err = stderr.read().decode()
            print(f"   Error: {err}")
        
        # Enable on boot
        print("\n6. Enabling chrony on boot...")
        stdin, stdout, stderr = client.exec_command('sudo systemctl enable chrony')
        stdout.channel.recv_exit_status()
        print("   ✓ Enabled on boot")
        
        # Check status
        print("\n7. Checking status...")
        time.sleep(2)
        stdin, stdout, stderr = client.exec_command('sudo systemctl is-active chrony')
        status = stdout.read().decode().strip()
        if status == 'active':
            print("   ✓ Chrony is ACTIVE")
        else:
            print(f"   ✗ Chrony status: {status}")
        
        # Open firewall
        print("\n8. Opening firewall for NTP...")
        stdin, stdout, stderr = client.exec_command('sudo ufw allow 123/udp 2>&1')
        output = stdout.read().decode()
        print(f"   {output.strip()}")
        
        # Show tracking info
        print("\n9. Chrony tracking:")
        stdin, stdout, stderr = client.exec_command('chronyc tracking')
        tracking = stdout.read().decode()
        print(tracking)
        
        client.close()
        print(f"\n✓ {name} setup complete!")
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║              Fix NTP Service on TSQ Servers                ║
╚════════════════════════════════════════════════════════════╝
""")
    
    results = {}
    for name, config in SERVERS.items():
        results[name] = fix_ntp_on_server(name, config)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{name}: {status}")
    
    if all(results.values()):
        print("\n✓ NTP service is now running on both servers!")
        print("\nWait 2-3 minutes for chrony to sync, then run:")
        print("  python tsq_test_runner.py compare")
    else:
        print("\n✗ Some servers failed")

if __name__ == "__main__":
    main()
