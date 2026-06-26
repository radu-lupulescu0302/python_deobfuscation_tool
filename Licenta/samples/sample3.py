# sample3.py — dynamic-phase test
# All three exec() calls survive static analysis and are resolved at runtime.

# === Pattern 1: map(chr, list-of-ints) ===
# Static XorArithmeticTransformer only handles GeneratorExp/ListComp inside
# ''.join(...), not map().  The dynamic phase executes the slice and extracts
# payload1.
payload1 = ''.join(map(chr, [112, 114, 105, 110, 116, 40, 34, 72, 101, 108, 108, 111, 32, 102, 114, 111, 109, 32, 109, 97, 112, 40, 99, 104, 114, 44, 32, 46, 46, 46, 41, 34, 41]))
exec(payload1)

# === Pattern 2: XOR key derived from sum() ===
# Static transformer cannot extract the XOR key because it is Name('xor_key'),
# not a Constant.  The sandbox executes the full three-line slice and returns
# the decoded string.
xor_key = sum([3, 4])
cipher = lambda s: ''.join(chr(ord(c) ^ xor_key) for c in s)
payload2 = cipher("wunis/%Obkkh+'_HU'lb~'cbunqbc'auhj'trj/.&%.")
exec(payload2)

# === Pattern 3: bytes([list-of-ints]).decode() ===
# EncodingsTransformer handles bytes.fromhex() and b'...'.decode() but not
# the bytes([int,...]) constructor form.  The sandbox handles it trivially.
payload3 = bytes([112, 114, 105, 110, 116, 40, 34, 72, 101, 108, 108, 111, 32, 102, 114, 111, 109, 32, 98, 121, 116, 101, 115, 40, 91, 46, 46, 46, 93, 41, 46, 100, 101, 99, 111, 100, 101, 40, 41, 34, 41]).decode()
exec(payload3)

print("=== sample3 finished ===")
