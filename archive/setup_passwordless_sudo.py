#!/usr/bin/env python3
"""
Setup passwordless sudo for cisco user (needed for NTP setup)
"""
import paramiko

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

def setup_passwordless_sudo(name, config):
    print(f"\n{'='*60}")
    print(f"Setting up passwordless sudo on {name}")
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
        
        # Check current sudo status
        print("\nChecking sudo status...")
        stdin, stdout, stderr = client.exec_command('sudo -n true 2>&1')
        output = stdout.read().decode()
        
        if 'password is required' in output:
            print("  Passwordless sudo is NOT configured")
            print("  Attempting to configure it automatically...")
            
            # Use echo with password piped to sudo
            cmd = f"echo '{config['password']}' | sudo -S sh -c \"echo 'cisco ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/cisco && chmod 440 /etc/sudoers.d/cisco\""
            stdin, stdout, stderr = client.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                print("  ✓ Passwordless sudo configured successfully!")
                return True
            else:
                print(f"  ✗ Failed to configure passwordless sudo")
                err = stderr.read().decode()
                print(f"  Error: {err}")
                return False
        else:
            print("  ✓ Passwordless sudo is already configured!")
            return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        client.close()

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║         Check/Setup Passwordless Sudo                      ║
╚════════════════════════════════════════════════════════════╝

This script checks if the cisco user has passwordless sudo access,
which is required for installing and configuring NTP service.
""")
    
    results = {}
    for name, config in SERVERS.items():
        results[name] = setup_passwordless_sudo(name, config)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if all(results.values()):
        print("✓ All servers have passwordless sudo configured!")
        print("\nYou can now run: python fix_ntp_servers.py")
    else:
        print("✗ Some servers need passwordless sudo configuration")
        print("\nManual steps required (run on each server):")
        print("  ssh cisco@<server-ip>")
        print("  echo 'cisco123' | sudo -S sh -c \"echo 'cisco ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/cisco\"")
        print("  sudo chmod 440 /etc/sudoers.d/cisco")

if __name__ == "__main__":
    main()
