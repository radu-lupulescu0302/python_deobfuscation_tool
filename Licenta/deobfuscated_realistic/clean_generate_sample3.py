"""
Run this once to produce samples/sample3.py — a test for the *dynamic* phase.

Every pattern here survives the static phase unchanged because:

  Pattern 1 — map(chr, list)
    Static XorArithmeticTransformer only resolves ''.join(GeneratorExp/ListComp).
    map() is a Call node, not a comprehension, so it is ignored statically.

  Pattern 2 — sum()-derived XOR key
    The XOR lambda extractor looks for a Constant int on either side of BitXor.
    Here the key is Name('xor_key'), not a constant, so the lambda is never
    registered and the call is never resolved.

  Pattern 3 — bytes([list-of-ints]).decode()
    EncodingsTransformer handles bytes.fromhex(str) and b'...'.decode().
    bytes([int, int, ...]) is a constructor call with a List arg — not matched.

All three reach the dynamic phase, where the sandbox executes the minimal slice
that computes each variable, extracts the string, and inlines the payload.
"""
import os
SUM_KEY = sum([3, 4])
SUM_PAYLOAD = f'print("Hello, XOR key derived from sum()!")'
map_ints = list('print("Hello from map(chr, ...)")'.encode())
sum_enc = ''.join((chr(ord(c) ^ SUM_KEY) for c in SUM_PAYLOAD))
bytes_ints = list('print("Hello from bytes([...]).decode()")'.encode())
sample = f"""# sample3.py — dynamic-phase test\n# All three exec() calls survive static analysis and are resolved at runtime.\n\n# === Pattern 1: map(chr, list-of-ints) ===\n# Static XorArithmeticTransformer only handles GeneratorExp/ListComp inside\n# ''.join(...), not map().  The dynamic phase executes the slice and extracts\n# payload1.\npayload1 = ''.join(map(chr, {map_ints!r}))\nexec(payload1)\n\n# === Pattern 2: XOR key derived from sum() ===\n# Static transformer cannot extract the XOR key because it is Name('xor_key'),\n# not a Constant.  The sandbox executes the full three-line slice and returns\n# the decoded string.\nxor_key = sum([3, 4])\ncipher = lambda s: ''.join(chr(ord(c) ^ xor_key) for c in s)\npayload2 = cipher({sum_enc!r})\nexec(payload2)\n\n# === Pattern 3: bytes([list-of-ints]).decode() ===\n# EncodingsTransformer handles bytes.fromhex() and b'...'.decode() but not\n# the bytes([int,...]) constructor form.  The sandbox handles it trivially.\npayload3 = bytes({bytes_ints!r}).decode()\nexec(payload3)\n\nprint("=== sample3 finished ===")\n"""
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample3.py')
with open(out, 'w', encoding='utf-8') as f:
    f.write(sample)
print(f'Written: {out}')