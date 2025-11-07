#!/usr/bin/env python3
"""Test individual queries to debug"""
import paramiko

CLIENT = '172.18.124.206'
USER = 'cisco'
PASSWORD = 'cisco123'

def test_command(desc, cmd):
    print(f"\n{desc}")
    print(f"Command: {cmd}")
    print("-" * 60)
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=CLIENT, username=USER, password=PASSWORD, timeout=10)
        
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        print(f"Output: {repr(output)}")
        if error:
            print(f"Error: {repr(error)}")
        
        ssh.close()
    except Exception as e:
        print(f"Exception: {e}")

# Test NTP
test_command("Test NTP query", "chronyc -h 14.38.117.100 tracking")

# Test TSQ Streams
test_command("Test TSQ Streams", 
             "cd /home/cisco && source ~/tsq-venv/bin/activate && python tsq_client.py 14.38.117.100 --port 443 --insecure --count 1")

# Test TSQ Datagrams
test_command("Test TSQ Datagrams",
             "/home/cisco/tsq-client-dg 14.38.117.100 --port 443 --count 1 --insecure")
