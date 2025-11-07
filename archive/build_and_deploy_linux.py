#!/usr/bin/env python3
"""
Build TSQ on Linux server and deploy to all hosts
"""
import paramiko
import tarfile
import os
import time

SERVER_BUILD = '172.18.124.203'
SERVER2 = '172.18.124.204'
CLIENT = '172.18.124.206'
USER = 'cisco'
PASSWORD = 'cisco123'

def run_ssh_command(host, command, show_output=True):
    """Run command via SSH and return output"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=USER, password=PASSWORD)
    
    stdin, stdout, stderr = ssh.exec_command(command)
    
    output = []
    for line in stdout:
        line = line.rstrip()
        if show_output:
            print(f"  {line}")
        output.append(line)
    
    for line in stderr:
        line = line.rstrip()
        if show_output and line:
            print(f"  [stderr] {line}")
    
    exit_status = stdout.channel.recv_exit_status()
    ssh.close()
    
    return exit_status, output

def copy_file(local_path, host, remote_path):
    """Copy file via SFTP"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=USER, password=PASSWORD)
    
    sftp = ssh.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.close()
    ssh.close()

def main():
    print("="*60)
    print("Building TSQ for Linux")
    print("="*60)
    print()
    
    # Step 1: Create tarball
    print("Step 1: Creating source tarball...")
    os.chdir('/Users/garrettmccollum/Desktop/TSQ')
    
    tar_path = '/tmp/tsq-rust-src.tar.gz'
    with tarfile.open(tar_path, 'w:gz') as tar:
        tar.add('rust/', arcname='rust/')
    print(f"  ✓ Created {tar_path}")
    print()
    
    # Step 2: Copy to build server
    print(f"Step 2: Copying source to {SERVER_BUILD}...")
    copy_file(tar_path, SERVER_BUILD, '/home/cisco/tsq-rust-src.tar.gz')
    print("  ✓ Source copied")
    print()
    
    # Step 3: Extract and build
    print(f"Step 3: Building on {SERVER_BUILD}...")
    print("  (This may take 5-10 minutes on first build)")
    
    build_commands = """
cd /home/cisco
rm -rf rust
tar xzf tsq-rust-src.tar.gz
cd rust

# Install Rust if needed
if ! command -v cargo &> /dev/null; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
fi

# Source cargo env
source $HOME/.cargo/env

# Build
echo "Building TSQ..."
cargo build --release 2>&1 | tail -20

# Verify
ls -lh target/release/tsq-server target/release/tsq-client
"""
    
    status, output = run_ssh_command(SERVER_BUILD, build_commands, show_output=True)
    
    if status != 0:
        print(f"\n✗ Build failed with status {status}")
        return
    
    print("  ✓ Build complete")
    print()
    
    # Step 4: Deploy binaries
    print("Step 4: Deploying binaries...")
    
    # Copy server binary to server2
    print(f"  → Deploying server to {SERVER2}...")
    deploy_cmd = f"sshpass -p '{PASSWORD}' scp -o StrictHostKeyChecking=no /home/cisco/rust/target/release/tsq-server {USER}@{SERVER2}:/home/cisco/tsq-server-dg"
    run_ssh_command(SERVER_BUILD, deploy_cmd, show_output=False)
    
    # Copy client binary to client
    print(f"  → Deploying client to {CLIENT}...")
    deploy_cmd = f"sshpass -p '{PASSWORD}' scp -o StrictHostKeyChecking=no /home/cisco/rust/target/release/tsq-client {USER}@{CLIENT}:/home/cisco/tsq-client-dg"
    run_ssh_command(SERVER_BUILD, deploy_cmd, show_output=False)
    
    # Copy server binary locally
    print(f"  → Deploying server to {SERVER_BUILD}...")
    run_ssh_command(SERVER_BUILD, "cp /home/cisco/rust/target/release/tsq-server /home/cisco/tsq-server-dg", show_output=False)
    
    print("  ✓ Deployment complete")
    print()
    
    # Step 5: Verify
    print("Step 5: Verifying deployment...")
    for host, binary in [(SERVER_BUILD, 'tsq-server-dg'), (SERVER2, 'tsq-server-dg'), (CLIENT, 'tsq-client-dg')]:
        status, output = run_ssh_command(host, f"ls -lh /home/cisco/{binary}", show_output=False)
        if status == 0:
            print(f"  ✓ {host}: {binary} deployed")
        else:
            print(f"  ✗ {host}: {binary} NOT found")
    
    print()
    print("="*60)
    print("✓ BUILD AND DEPLOYMENT COMPLETE!")
    print("="*60)
    print()
    print("Ready to test with:")
    print("  python3 run_datagram_test.py")
    print()

if __name__ == "__main__":
    main()
