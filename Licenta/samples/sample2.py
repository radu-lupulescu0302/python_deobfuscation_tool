import base64
import codecs

# === hex-encoded exec ===
raw = bytes.fromhex('7072696e74282248656c6c6f2066726f6d2068657820656e636f64696e67212229')
exec(raw)

# === ROT-13 via codecs ===
rot = codecs.decode('cevag("Uryyb sebz EBG-13!")', 'rot_13')
exec(rot)

# === XOR cipher — key=7, lambda named 'cipher' (not 'obf') ===
cipher = lambda s: ''.join(chr(ord(c) ^ 7) for c in s)
secret = "wunis/%Obkkh+'_HU'lb~:0'cbdhcbc&%."
decoded = cipher(secret)
exec(decoded)

# === Inline join-XOR — no named lambda, key=3 ===
result = ''.join(chr(ord(c) ^ 3) for c in 'sqjmw+2#(#2*')
exec(result)

# === base64 ===
b64 = base64.b64decode('cHJpbnQoIkhlbGxvIGZyb20gYmFzZTY0ISIp')
exec(b64)

# === Arithmetic dead variable — gets folded to a constant then removed ===
unused = (3 * 10) + (2 ** 4) - (100 // 5)

print("=== sample2 finished ===")
