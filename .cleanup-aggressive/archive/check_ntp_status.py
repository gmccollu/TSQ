#!/usr/bin/env python3
"""
Check NTP status on TSQ servers
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

def check_server(name, config):
    print(f"\n{'='*60}")
    print(f"Checking {name} ({config['host']})")
    print('='*60)
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=config['host'],
            username=config['username'],
            password=config['password']
        )
        
        # Check if chrony is running
        print("\n1. Chrony service status:")
        stdin, stdout, stderr = client.exec_command('sudo systemctl status chrony')
        output = stdout.read().decode()
        if 'active (running)' in output:
            print("   ✓ Chrony is RUNNING")
        else:
            print("   ✗ Chrony is NOT running")
            print(output[:200])
        
        # Check tracking
        print("\n2. Chrony tracking (sync status):")
        stdin, stdout, stderr = client.exec_command('chronyc tracking')
        tracking = stdout.read().decode()
        print(tracking)
        
        # Check sources
        print("\n3. NTP sources:")
        stdin, stdout, stderr = client.exec_command('chronyc sources')
        sources = stdout.read().decode()
        print(sources)
        
        # Check if port 123 is listening
        print("\n4. Port 123 status:")
        stdin, stdout, stderr = client.exec_command('sudo netstat -ulnp | grep :123 || sudo ss -ulnp | grep :123')
        port_status = stdout.read().decode()
        if port_status:
            print("   ✓ Port 123 is LISTENING")
            print(port_status)
        else:
            print("   ✗ Port 123 is NOT listening")
        
        # Check firewall
        print("\n5. Firewall status for port 123:")
        stdin, stdout, stderr = client.exec_command('sudo ufw status | grep 123')
        fw_status = stdout.read().decode()
        if fw_status:
            print(fw_status)
        else:
            print("   No specific rule found (may be using default policy)")
        
        client.close()
        
    except Exception as e:
        print(f"   ✗ Error: {e}")

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║              NTP Status Check                              ║
╚════════════════════════════════════════════════════════════╝
""")
    
    for name, config in SERVERS.items():
        check_server(name, config)
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("="*60)
    print("- If chrony is running but not synced, wait 2-5 minutes")
    print("- Look for '*' or '+' in sources output (indicates good sync)")
    print("- If port 123 is not listening, chrony may not be configured correctly")
    print("- Try running: python tsq_test_runner.py compare")

if __name__ == "__main__":
    main()
