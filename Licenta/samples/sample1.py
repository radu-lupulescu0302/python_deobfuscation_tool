import base64
import zlib

# === Simple cases ===
payload1 = base64.b64decode(b'cHJpbnQoIkhlbGxvIGZyb20gYmFzZTY0ISIp')

# === Nested base64 + zlib (valid data) ===
compressed = base64.b64decode(b'eJwLycjNyclJLAkKLS4pLS1OLsosKskvSikq0gIAfQ4P9Q==')
data = zlib.decompress(compressed)
exec(data)

# === XOR Lambda (common pattern) ===
obf = lambda x: ''.join(chr(ord(c) ^ 66) for c in x)
encoded = 'Qf`j`b`c`d'
dec = obf(encoded)
exec(dec)

print("=== Original script finished ===")