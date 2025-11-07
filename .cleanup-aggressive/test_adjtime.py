#!/usr/bin/env python3
"""
Test tsq_adjtime.py on the Linux client
"""
import paramiko
import sys

CLIENT = '172.18.124.206'
USER = 'cisco'
PASSWORD = 'cisco123'
SERVERS = ['14.38.117.100', '14.38.117.200']

def run_test():
    print("Testing TSQ Time Adjustment on Linux client...")
    print("=" * 70)
    print()
    
    try:
        # Connect to client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {CLIENT}...")
        ssh.connect(hostname=CLIENT, username=USER, password=PASSWORD, timeout=10)
        print("✓ Connected\n")
        
        # Copy the script
        print("Copying tsq_adjtime.py to client...")
        sftp = ssh.open_sftp()
        sftp.put('/Users/garrettmccollum/Desktop/TSQ/tsq_adjtime.py', '/home/cisco/tsq_adjtime.py')
        sftp.close()
        print("✓ Script copied\n")
        
        # Make it executable
        ssh.exec_command("chmod +x /home/cisco/tsq_adjtime.py")
        
        # Run dry-run test
        print("Running DRY RUN test (no actual clock changes)...")
        print("-" * 70)
        
        server_ips = ' '.join(SERVERS)
        cmd = f"cd /home/cisco && source ~/tsq-venv/bin/activate && python3 tsq_adjtime.py {server_ips} --insecure --dry-run --verbose"
        
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
        
        # Read both stdout and stderr
        output = stdout.read().decode()
        errors = stderr.read().decode()
        
        # Print output
        if output:
            print(output)
        
        # Check for errors
        if errors:
            print("\nStderr:")
            print(errors)
        
        exit_code = stdout.channel.recv_exit_status()
        
        print()
        print("=" * 70)
        if exit_code == 0:
            print("✓ DRY RUN TEST PASSED")
            print()
            print("Next steps:")
            print("  1. Review the output above")
            print("  2. If it looks good, run without --dry-run:")
            print(f"     ssh {USER}@{CLIENT}")
            print(f"     cd /home/cisco && source ~/tsq-venv/bin/activate")
            print(f"     sudo python3 tsq_adjtime.py {server_ips} --insecure --verbose")
        else:
            print("✗ TEST FAILED")
            return False
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
