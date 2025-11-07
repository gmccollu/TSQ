#!/usr/bin/env python3
"""Copy the Linux client binary from server1 to client via SFTP"""
import paramiko
import os

SERVER = '172.18.124.203'
CLIENT = '172.18.124.206'
USER = 'cisco'
PASSWORD = 'cisco123'

print("Step 1: Downloading client binary from server1...")

# Connect to server1 and download
ssh1 = paramiko.SSHClient()
ssh1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh1.connect(hostname=SERVER, username=USER, password=PASSWORD)

sftp1 = ssh1.open_sftp()
sftp1.get('/home/cisco/tsq-client-dg', '/tmp/tsq-client-dg-linux')
sftp1.close()
ssh1.close()

print("✓ Downloaded to /tmp/tsq-client-dg-linux")

print("\nStep 2: Uploading to client...")

# Connect to client and upload
ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh2.connect(hostname=CLIENT, username=USER, password=PASSWORD)

sftp2 = ssh2.open_sftp()
sftp2.put('/tmp/tsq-client-dg-linux', '/home/cisco/tsq-client-dg')
sftp2.chmod('/home/cisco/tsq-client-dg', 0o755)
sftp2.close()

print("✓ Uploaded to client")

print("\nStep 3: Verifying...")

stdin, stdout, stderr = ssh2.exec_command("file /home/cisco/tsq-client-dg")
result = stdout.read().decode()
print(result)

if "ELF 64-bit" in result:
    print("\n✓✓✓ SUCCESS! Correct Linux binary installed!")
else:
    print("\n✗ Still wrong binary")

ssh2.close()

# Cleanup
os.remove('/tmp/tsq-client-dg-linux')
