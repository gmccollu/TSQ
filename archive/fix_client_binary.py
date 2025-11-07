#!/usr/bin/env python3
"""Copy the correct Linux binary to the client"""
import paramiko

SERVER = '172.18.124.203'
CLIENT = '172.18.124.206'
USER = 'cisco'
PASSWORD = 'cisco123'

print("Copying Linux client binary from server1 to client...")

# Connect to server1
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=SERVER, username=USER, password=PASSWORD)

# Use scp via SSH command
cmd = f"sshpass -p '{PASSWORD}' scp -o StrictHostKeyChecking=no /home/cisco/tsq-client-dg {USER}@{CLIENT}:/home/cisco/"
stdin, stdout, stderr = ssh.exec_command(cmd)

for line in stdout:
    print(line.rstrip())
for line in stderr:
    print(line.rstrip())

ssh.close()

print("\n✓ Client binary copied")
print("\nVerifying...")

# Verify on client
ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh2.connect(hostname=CLIENT, username=USER, password=PASSWORD)

stdin, stdout, stderr = ssh2.exec_command("file /home/cisco/tsq-client-dg")
result = stdout.read().decode()
print(result)

if "ELF 64-bit" in result:
    print("✓ Correct Linux binary!")
else:
    print("✗ Still wrong binary")

ssh2.close()
