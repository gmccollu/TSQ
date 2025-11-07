#!/usr/bin/env python3
"""Start TSQ stream servers in background"""
import paramiko
import time

SERVERS = ['172.18.124.203', '172.18.124.204']
USER = 'cisco'
PASSWORD = 'cisco123'

print("Starting TSQ stream servers...")
print()

for server in SERVERS:
    print(f"Starting server on {server}...")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=server, username=USER, password=PASSWORD)
    
    # Start server in background with nohup
    cmd = "cd /home/cisco/tsq-certs && nohup bash -c 'source ~/tsq-venv/bin/activate && python tsq_server.py --host 0.0.0.0 --port 443 --cert server.crt --key server.key' > /tmp/tsq-stream.log 2>&1 &"
    
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.read()
    
    ssh.close()
    print(f"  ✓ {server} started")

print()
print("Waiting 3 seconds for servers to initialize...")
time.sleep(3)

print()
print("✓ Stream servers ready!")
print()
print("Now run: python3 compare_all_three.py")
