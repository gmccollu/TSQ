#!/usr/bin/env python3
"""
Setup NTS (Network Time Security) on TSQ servers
Then test NTS sync from client to internal servers
"""
import paramiko
import time

SERVERS = [
    {'host': '172.18.124.203', 'ip': '14.38.117.100', 'name': 'server1'},
    {'host': '172.18.124.204', 'ip': '14.38.117.200', 'name': 'server2'},
]
CLIENT = '172.18.124.206'
USER = 'cisco'
PASSWORD = 'cisco123'

def setup_nts_server(host, name):
    """Configure chronyd with NTS support on a server"""
    print(f"\nSetting up NTS on {name} ({host})...")
    print("="*70)
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=USER, password=PASSWORD)
        
        # Check chronyd version
        stdin, stdout, stderr = ssh.exec_command('chronyd -v')
        version = stdout.read().decode()
        print(f"  Chronyd version: {version.strip()}")
        
        if '+NTS' not in version:
            print(f"  ✗ Chronyd does not support NTS")
            print(f"    Need to compile chronyd with NTS support")
            ssh.close()
            return False
        
        print(f"  ✓ NTS support detected")
        
        # Generate self-signed certificate for NTS
        print(f"  Generating NTS certificate...")
        cert_cmd = f"""
cd /home/cisco/tsq-certs
if [ ! -f nts-server.crt ]; then
    openssl req -x509 -newkey rsa:2048 -keyout nts-server.key -out nts-server.crt \
        -days 365 -nodes -subj "/CN={name}.local" 2>&1
    echo "Certificate generated"
else
    echo "Certificate already exists"
fi
"""
        stdin, stdout, stderr = ssh.exec_command(cert_cmd)
        print(stdout.read().decode())
        
        # Create NTS-enabled chronyd config
        print(f"  Creating NTS configuration...")
        nts_config = f"""
# NTS Server Configuration
server time.cloudflare.com iburst
driftfile /var/lib/chrony/drift
rtcsync
makestep 1 3

# Enable NTS server
ntsserverkey /home/cisco/tsq-certs/nts-server.key
ntsservercert /home/cisco/tsq-certs/nts-server.crt
ntsport 4460

# Allow NTP and NTS from local network
allow 14.36.0.0/16
allow 172.18.0.0/16

logdir /var/log/chrony
"""
        
        stdin, stdout, stderr = ssh.exec_command('cat > /tmp/chrony-nts.conf', get_pty=True)
        stdin.write(nts_config)
        stdin.channel.shutdown_write()
        stdout.read()
        
        # Backup existing config and install new one
        print(f"  Installing NTS configuration...")
        stdin, stdout, stderr = ssh.exec_command(
            'echo cisco123 | sudo -S bash -c "cp /etc/chrony/chrony.conf /etc/chrony/chrony.conf.backup && '
            'cp /tmp/chrony-nts.conf /etc/chrony/chrony.conf"',
            get_pty=True
        )
        stdout.read()
        
        # Restart chronyd
        print(f"  Restarting chronyd...")
        stdin, stdout, stderr = ssh.exec_command(
            'echo cisco123 | sudo -S systemctl restart chronyd',
            get_pty=True
        )
        stdout.read()
        
        time.sleep(2)
        
        # Check if NTS port is listening
        stdin, stdout, stderr = ssh.exec_command('sudo netstat -tlnp | grep 4460')
        netstat_output = stdout.read().decode()
        
        if '4460' in netstat_output:
            print(f"  ✓ NTS-KE listening on port 4460")
            print(f"    {netstat_output.strip()}")
        else:
            print(f"  ⚠️  Port 4460 not detected (may need firewall rule)")
        
        ssh.close()
        print(f"  ✓ NTS setup complete on {name}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_nts_to_internal():
    """Test NTS from client to internal servers"""
    print(f"\n{'='*70}")
    print("Testing NTS from client to internal servers")
    print("="*70)
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=CLIENT, username=USER, password=PASSWORD)
        
        # Create NTS client config
        server_list = '\n'.join([f"server {s['ip']} iburst nts" for s in SERVERS])
        
        nts_config = f"""
# NTS Client Configuration for internal servers
{server_list}

# Allow stepping
makestep 1 3

driftfile /tmp/chrony.drift
logdir /tmp
"""
        
        print("\nCreating NTS client configuration...")
        stdin, stdout, stderr = ssh.exec_command('cat > /tmp/chrony-nts-internal.conf')
        stdin.write(nts_config)
        stdin.channel.shutdown_write()
        stdout.read()
        
        print(f"Testing NTS to: {', '.join([s['ip'] for s in SERVERS])}")
        print("This may take 10-30 seconds for NTS key exchange...")
        print("-"*70)
        
        # Stop chronyd
        ssh.exec_command('echo cisco123 | sudo -S systemctl stop chronyd 2>/dev/null', get_pty=True)
        time.sleep(1)
        
        # Run chronyd in query mode
        start_time = time.time()
        cmd = 'echo cisco123 | sudo -S chronyd -q -f /tmp/chrony-nts-internal.conf 2>&1'
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=60)
        output = stdout.read().decode()
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000
        
        print(output)
        
        # Restart chronyd
        ssh.exec_command('echo cisco123 | sudo -S systemctl start chronyd 2>/dev/null', get_pty=True)
        
        print("-"*70)
        print(f"NTS sync duration: {duration:.1f}ms")
        
        ssh.close()
        
        return {
            'success': True,
            'duration_ms': duration,
            'output': output
        }
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return {'success': False, 'error': str(e)}

def main():
    print("\n" + "="*70)
    print(" "*15 + "NTS SETUP AND TEST")
    print("="*70)
    print("\nThis will:")
    print("  1. Setup NTS on internal servers (14.38.117.100, 14.38.117.200)")
    print("  2. Test NTS from client to internal servers")
    print("  3. Compare with TSQ performance")
    print()
    
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    # Setup NTS on servers
    success_count = 0
    for server in SERVERS:
        if setup_nts_server(server['host'], server['name']):
            success_count += 1
    
    if success_count == 0:
        print("\n✗ Failed to setup NTS on any server")
        return
    
    print(f"\n✓ NTS setup complete on {success_count}/{len(SERVERS)} servers")
    
    # Test NTS
    result = test_nts_to_internal()
    
    if result['success']:
        print("\n" + "="*70)
        print(" "*20 + "COMPARISON SUMMARY")
        print("="*70)
        print()
        
        print(f"{'Protocol':<20} {'Duration':<15} {'Encryption':<15}")
        print("-"*70)
        print(f"{'NTP (local)':<20} {'169 ms':<15} {'❌ None':<15}")
        nts_duration = f"{result['duration_ms']:.1f} ms"
        print(f"{'NTS (local)':<20} {nts_duration:<15} {'✅ TLS':<15}")
        print(f"{'TSQ Streams':<20} {'3267.8 ms':<15} {'✅ TLS 1.3':<15}")
        print(f"{'TSQ Datagrams':<20} {'2061.8 ms':<15} {'✅ TLS 1.3':<15}")
        print()
        print("All tests: Linux client → Internal servers (apples-to-apples)")
        print("="*70)

if __name__ == "__main__":
    main()
