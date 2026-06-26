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
XOR_PAYLOAD = f'print("Hello, XOR key={7} decoded!")'
hex_enc = 'print("Hello from hex encoding!")'.encode().hex()
rot_enc = codecs.encode('print("Hello from ROT-13!")', 'rot_13')
xor_enc = ''.join((chr(ord(c) ^ 7) for c in XOR_PAYLOAD))
b64_enc = base64.b64encode(b'print("Hello from base64!")').decode()
sample = f"""import base64\nimport codecs\n\n# === hex-encoded exec ===\nraw = bytes.fromhex({hex_enc!r})\nexec(raw)\n\n# === ROT-13 via codecs ===\nrot = codecs.decode({rot_enc!r}, 'rot_13')\nexec(rot)\n\n# === XOR cipher — key={7}, lambda named 'cipher' (not 'obf') ===\ncipher = lambda s: ''.join(chr(ord(c) ^ {7}) for c in s)\nsecret = {xor_enc!r}\ndecoded = cipher(secret)\nexec(decoded)\n\n# === Inline join-XOR — no named lambda, key={3} ===\nresult = ''.join(chr(ord(c) ^ {3}) for c in {'sqjmw+2#(#2*'!r})\nexec(result)\n\n# === base64 ===\nb64 = base64.b64decode({b64_enc!r})\nexec(b64)\n\n# === Arithmetic dead variable — gets folded to a constant then removed ===\nunused = (3 * 10) + (2 ** 4) - (100 // 5)\n\nprint("=== sample2 finished ===")\n"""
os.makedirs(os.path.dirname(os.path.abspath(__file__)) or '.', exist_ok=True)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample2.py')
with open(out, 'w', encoding='utf-8') as f:
    f.write(sample)
print(f'Written: {out}')