#!/usr/bin/env python3
"""Install chrony on the client for NTP queries"""
import paramiko

CLIENT = '172.18.124.206'
USER = 'cisco'
PASSWORD = 'cisco123'

print("Installing chrony on client...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=CLIENT, username=USER, password=PASSWORD)

# Install chrony
cmd = "sudo apt update && sudo apt install -y chrony"
stdin, stdout, stderr = ssh.exec_command(cmd)

for line in stdout:
    print(line.rstrip())

ssh.close()

print("\n✓ Chrony installed on client")
print("\nNow you can run: python3 compare_all_three.py")
