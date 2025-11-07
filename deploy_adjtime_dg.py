#!/usr/bin/env python3
"""
Build and deploy TSQ datagram adjtime to Linux servers
"""
import paramiko
import sys

SERVERS = [
    {'host': '172.18.124.203', 'name': 'server1'},
    {'host': '172.18.124.204', 'name': 'server2'},
]
CLIENT = '172.18.124.206'
USER = 'cisco'
PASSWORD = 'cisco123'

def build_on_server(host, name):
    """Build tsq-adjtime on a Linux server"""
    print(f"\nBuilding on {name} ({host})...")
    print("=" * 70)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=USER, password=PASSWORD)
    
    # Build
    print("  Building tsq-adjtime...")
    cmd = "cd /home/cisco/TSQ/rust && cargo build --release --bin tsq-adjtime 2>&1 | tail -5"
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
    output = stdout.read().decode()
    print(output)
    
    # Check if binary exists
    stdin, stdout, stderr = ssh.exec_command("ls -lh /home/cisco/TSQ/rust/target/release/tsq-adjtime")
    output = stdout.read().decode()
    
    if "tsq-adjtime" in output:
        print(f"  ✓ Built successfully on {name}")
        print(f"    {output.strip()}")
        ssh.close()
        return True
    else:
        print(f"  ✗ Build failed on {name}")
        ssh.close()
        return False

def copy_to_client():
    """Copy binary from server1 to client"""
    print(f"\nCopying binary to client...")
    print("=" * 70)
    
    # Connect to server1
    ssh1 = paramiko.SSHClient()
    ssh1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh1.connect(hostname=SERVERS[0]['host'], username=USER, password=PASSWORD)
    
    # Connect to client
    ssh2 = paramiko.SSHClient()
    ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh2.connect(hostname=CLIENT, username=USER, password=PASSWORD)
    
    # Read binary from server1
    sftp1 = ssh1.open_sftp()
    with sftp1.file('/home/cisco/TSQ/rust/target/release/tsq-adjtime', 'rb') as f:
        binary_data = f.read()
    sftp1.close()
    
    # Write to client
    sftp2 = ssh2.open_sftp()
    with sftp2.file('/home/cisco/tsq-adjtime-dg', 'wb') as f:
        f.write(binary_data)
    sftp2.close()
    
    # Make executable
    ssh2.exec_command("chmod +x /home/cisco/tsq-adjtime-dg")
    
    # Verify
    stdin, stdout, stderr = ssh2.exec_command("ls -lh /home/cisco/tsq-adjtime-dg")
    output = stdout.read().decode()
    
    ssh1.close()
    ssh2.close()
    
    if "tsq-adjtime-dg" in output:
        print(f"  ✓ Copied to client")
        print(f"    {output.strip()}")
        return True
    else:
        print(f"  ✗ Copy failed")
        return False

def main():
    print("\n" + "=" * 70)
    print("TSQ Datagram Adjtime - Build and Deploy")
    print("=" * 70)
    
    # Build on server1 (we only need one)
    if not build_on_server(SERVERS[0]['host'], SERVERS[0]['name']):
        print("\n✗ Build failed")
        sys.exit(1)
    
    # Copy to client
    if not copy_to_client():
        print("\n✗ Deployment failed")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("✓ Deployment complete!")
    print("=" * 70)
    print("\nBinary location:")
    print(f"  Client: /home/cisco/tsq-adjtime-dg")
    print("\nUsage:")
    print(f"  ssh {USER}@{CLIENT}")
    print(f"  sudo ./tsq-adjtime-dg 14.38.117.100 14.38.117.200 --dry-run --verbose")
    print()

if __name__ == "__main__":
    main()
