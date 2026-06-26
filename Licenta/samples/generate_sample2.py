#!/usr/bin/env python3
"""
Run this once to produce samples/sample2.py — a generalised test for the
deobfuscator.  Covers:
  1. bytes.fromhex  -> exec
  2. codecs rot-13  -> exec
  3. XOR lambda (key != 66, name != obf/dec)  -> exec
  4. Inline join-XOR (no lambda)  -> exec
  5. base64.b64decode  -> exec
  6. Arithmetic constant folding  -> dead variable (should be removed)
  7. Dead imports  (should be removed)
  8. Dead intermediate variables  (should be removed)
"""
import base64
import codecs
import os

# ── Plaintext payloads ────────────────────────────────────────────────────────
HEX_PAYLOAD    = 'print("Hello from hex encoding!")'
ROT_PAYLOAD    = 'print("Hello from ROT-13!")'
XOR_KEY        = 7
XOR_PAYLOAD    = f'print("Hello, XOR key={XOR_KEY} decoded!")'
INLINE_KEY     = 3
INLINE_PAYLOAD = 'print(1 + 1)'
B64_PAYLOAD    = b'print("Hello from base64!")'

# ── Encode each one ───────────────────────────────────────────────────────────
hex_enc    = HEX_PAYLOAD.encode().hex()
rot_enc    = codecs.encode(ROT_PAYLOAD, 'rot_13')
xor_enc    = ''.join(chr(ord(c) ^ XOR_KEY)   for c in XOR_PAYLOAD)
inline_enc = ''.join(chr(ord(c) ^ INLINE_KEY) for c in INLINE_PAYLOAD)
b64_enc    = base64.b64encode(B64_PAYLOAD).decode()

sample = f"""\
import base64
import codecs

# === hex-encoded exec ===
raw = bytes.fromhex({hex_enc!r})
exec(raw)

# === ROT-13 via codecs ===
rot = codecs.decode({rot_enc!r}, 'rot_13')
exec(rot)

# === XOR cipher — key={XOR_KEY}, lambda named 'cipher' (not 'obf') ===
cipher = lambda s: ''.join(chr(ord(c) ^ {XOR_KEY}) for c in s)
secret = {xor_enc!r}
decoded = cipher(secret)
exec(decoded)

# === Inline join-XOR — no named lambda, key={INLINE_KEY} ===
result = ''.join(chr(ord(c) ^ {INLINE_KEY}) for c in {inline_enc!r})
exec(result)

# === base64 ===
b64 = base64.b64decode({b64_enc!r})
exec(b64)

# === Arithmetic dead variable — gets folded to a constant then removed ===
unused = (3 * 10) + (2 ** 4) - (100 // 5)

print("=== sample2 finished ===")
"""

os.makedirs(os.path.dirname(os.path.abspath(__file__)) or '.', exist_ok=True)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample2.py')
with open(out, 'w', encoding='utf-8') as f:
    f.write(sample)
print(f"Written: {out}")
